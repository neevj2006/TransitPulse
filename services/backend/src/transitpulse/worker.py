import asyncio
import json
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import httpx
import structlog

from transitpulse.cache import RedisStateStore
from transitpulse.events import EventBroker
from transitpulse.history import RealtimeHistoryStore
from transitpulse.polling import FeedConfig, FeedPoller, RawSnapshotStore
from transitpulse.realtime import (
    Alert,
    CurrentState,
    TripUpdate,
    Vehicle,
    parse_alerts,
    parse_trip_updates,
    parse_vehicle_positions,
)
from transitpulse.reconciliation import reconcile_trip_update, reconcile_vehicle
from transitpulse.schedule.models import Schedule

logger = structlog.get_logger()


class RealtimeProjector:
    """Applies validated feed entities to bounded current state and optional Redis."""

    def __init__(
        self,
        state: CurrentState,
        broker: EventBroker,
        cache: RedisStateStore | None = None,
        history: RealtimeHistoryStore | None = None,
        schedule: Schedule | None = None,
    ) -> None:
        self.state, self.broker, self.cache, self.history, self.schedule = (
            state,
            broker,
            cache,
            history,
            schedule,
        )
        self.diagnostics: dict[str, dict[str, int]] = {}

    def count_diagnostic(self, source_id: str, key: str, amount: int = 1) -> None:
        self.diagnostics.setdefault(source_id, {})[key] = (
            self.diagnostics.setdefault(source_id, {}).get(key, 0) + amount
        )

    async def project(
        self,
        source_id: str,
        values: list[Vehicle] | list[TripUpdate] | list[Alert],
        retrieved_at: datetime | None = None,
    ) -> None:
        if source_id.endswith("vehicles"):
            observed_at = retrieved_at or datetime.now(UTC)
            vehicles = [
                replace(item, retrieved_at=observed_at) for item in cast(list[Vehicle], values)
            ]
            accepted = len(vehicles)
            vehicles = [
                item
                for item in vehicles
                if self.schedule is None
                or reconcile_vehicle(item, self.schedule).state != "UNRECONCILED"
            ]
            self.count_diagnostic(source_id, "accepted", len(vehicles))
            self.count_diagnostic(source_id, "unreconciled", accepted - len(vehicles))
            changed = self.state.update_vehicles(vehicles)
            for item in changed:
                if self.cache:
                    await self.cache.put_vehicle(item)
                self.broker.publish(
                    "vehicle.changed", json.dumps({"vehicle_id": item.vehicle_id}), item.route_id
                )
                if self.cache:
                    await self.cache.publish_event(
                        "vehicle.changed",
                        json.dumps({"schema_version": "1.0.0", "vehicle_id": item.vehicle_id}),
                        item.route_id,
                    )
            if self.history:
                await self.history.record_vehicles(changed, observed_at)
        elif source_id.endswith("trip-updates"):
            updates = [
                replace(item, retrieved_at=retrieved_at or datetime.now(UTC))
                for item in cast(list[TripUpdate], values)
            ]
            accepted = len(updates)
            updates = [
                item
                for item in updates
                if self.schedule is None
                or reconcile_trip_update(item, self.schedule).state != "UNRECONCILED"
            ]
            self.count_diagnostic(source_id, "accepted", len(updates))
            self.count_diagnostic(source_id, "unreconciled", accepted - len(updates))
            self.state.update_trip_updates(updates)
            if self.cache:
                await self.cache.put_trip_updates(updates)
            for item in updates:
                self.broker.publish(
                    "arrival.changed", json.dumps({"trip_id": item.trip_id}), item.route_id
                )
                if self.cache:
                    await self.cache.publish_event(
                        "arrival.changed",
                        json.dumps({"schema_version": "1.0.0", "trip_id": item.trip_id}),
                        item.route_id,
                    )
        else:
            alerts = [
                replace(item, retrieved_at=retrieved_at or datetime.now(UTC))
                for item in cast(list[Alert], values)
            ]
            self.count_diagnostic(source_id, "accepted", len(alerts))
            self.state.update_alerts(alerts)
            if self.cache:
                await self.cache.put_alerts(alerts)
            for item in alerts:
                routes = item.route_ids or (None,)
                for route_id in routes:
                    self.broker.publish(
                        "alert.changed", json.dumps({"alert_id": item.entity_id}), route_id
                    )
                    if self.cache:
                        await self.cache.publish_event(
                            "alert.changed",
                            json.dumps({"schema_version": "1.0.0", "alert_id": item.entity_id}),
                            route_id,
                        )
        self.state.expire(datetime.now(UTC))


def build_pollers(
    raw_path: Path, vehicle_url: str, trip_url: str, alert_url: str
) -> dict[str, FeedPoller]:
    store = RawSnapshotStore(raw_path)
    return {
        "mbta-vehicles": FeedPoller(FeedConfig("mbta-vehicles", vehicle_url), store),
        "mbta-trip-updates": FeedPoller(FeedConfig("mbta-trip-updates", trip_url), store),
        "mbta-alerts": FeedPoller(FeedConfig("mbta-alerts", alert_url), store),
    }


async def run_poller(
    poller: FeedPoller,
    parser: Callable[[bytes], list[Vehicle] | list[TripUpdate] | list[Alert]],
    stop: asyncio.Event,
    projector: RealtimeProjector,
) -> None:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        while not stop.is_set():
            result, payload = await poller.poll(client)
            if projector.cache:
                now = datetime.now(UTC)
                await projector.cache.put_source_health(
                    poller.config.source_id,
                    {
                        "source_id": poller.config.source_id,
                        "state": poller.health.state(now),
                        "last_success_at": poller.health.last_success_at,
                        "consecutive_failures": poller.health.failures,
                        "last_outcome": result.outcome,
                        "updated_at": now,
                    },
                )
            if projector.history:
                await projector.history.record_poll(result)
            if payload:
                try:
                    parsed = parser(payload)
                    await projector.project(poller.config.source_id, parsed, result.completed_at)
                    if projector.cache:
                        now = datetime.now(UTC)
                        await projector.cache.put_source_health(
                            poller.config.source_id,
                            {
                                "source_id": poller.config.source_id,
                                "state": poller.health.state(now),
                                "last_success_at": poller.health.last_success_at,
                                "consecutive_failures": poller.health.failures,
                                "last_outcome": result.outcome,
                                "diagnostics": projector.diagnostics.get(
                                    poller.config.source_id, {}
                                ),
                                "updated_at": now,
                            },
                        )
                    logger.info(
                        "feed_processed",
                        source_id=poller.config.source_id,
                        outcome=result.outcome,
                        entities=len(parsed),
                    )
                except Exception:
                    projector.count_diagnostic(poller.config.source_id, "parser_errors")
                    logger.exception("feed_parse_failed", source_id=poller.config.source_id)
            try:
                await asyncio.wait_for(stop.wait(), timeout=poller.next_delay())
            except TimeoutError:
                pass


async def prune_raw_snapshots(
    store: RawSnapshotStore, retention_hours: int, stop: asyncio.Event
) -> None:
    while not stop.is_set():
        removed = store.prune(datetime.now(UTC) - timedelta(hours=retention_hours))
        if removed:
            logger.info("raw_snapshots_pruned", count=removed)
        try:
            await asyncio.wait_for(stop.wait(), timeout=3600)
        except TimeoutError:
            pass


async def prune_history(
    history: RealtimeHistoryStore, retention_days: int, stop: asyncio.Event
) -> None:
    while not stop.is_set():
        removed = await history.prune_observations(
            datetime.now(UTC) - timedelta(days=retention_days)
        )
        if removed:
            logger.info("realtime_history_pruned", count=removed)
        try:
            await asyncio.wait_for(stop.wait(), timeout=3600)
        except TimeoutError:
            pass


async def run_worker(
    raw_path: Path,
    vehicle_url: str,
    trip_url: str,
    alert_url: str,
    cache: RedisStateStore | None = None,
    history: RealtimeHistoryStore | None = None,
    raw_retention_hours: int = 6,
    detailed_history_retention_days: int = 14,
    schedule: Schedule | None = None,
) -> None:
    stop = asyncio.Event()
    pollers = build_pollers(raw_path, vehicle_url, trip_url, alert_url)
    projector = RealtimeProjector(CurrentState(), EventBroker(), cache, history, schedule)
    try:
        await asyncio.gather(
            run_poller(pollers["mbta-vehicles"], parse_vehicle_positions, stop, projector),
            run_poller(pollers["mbta-trip-updates"], parse_trip_updates, stop, projector),
            run_poller(pollers["mbta-alerts"], parse_alerts, stop, projector),
            prune_raw_snapshots(next(iter(pollers.values())).raw_store, raw_retention_hours, stop),
            *([prune_history(history, detailed_history_retention_days, stop)] if history else []),
        )
    finally:
        if cache:
            await cache.close()
        if history:
            await history.close()
