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
from transitpulse.diagnostics import vehicle_quality
from transitpulse.events import EventBroker
from transitpulse.history import RealtimeHistoryStore
from transitpulse.polling import FeedConfig, FeedPoller, RawSnapshotStore
from transitpulse.realtime import (
    Alert,
    CurrentState,
    EntityCounts,
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
        previous_schedule: Schedule | None = None,
    ) -> None:
        self.state, self.broker, self.cache, self.history, self.schedule = (
            state,
            broker,
            cache,
            history,
            schedule,
        )
        self.previous_schedule = previous_schedule
        self.diagnostics: dict[str, dict[str, int]] = {}
        self.last_entity_counts: dict[str, int] = {}

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
        previous_count = self.last_entity_counts.get(source_id)
        self.last_entity_counts[source_id] = len(values)
        if previous_count is not None and len(values) < previous_count:
            self.count_diagnostic(source_id, "missing_entity_count_changes")
            if self.history:
                await self.history.record_quality(
                    source_id,
                    "feed",
                    None,
                    None,
                    "MISSING_ENTITY_COUNT_CHANGE",
                    retrieved_at or datetime.now(UTC),
                    detail={"previous_count": previous_count, "current_count": len(values)},
                )
        if source_id.endswith("vehicles"):
            observed_at = retrieved_at or datetime.now(UTC)
            vehicles = [
                replace(item, retrieved_at=observed_at) for item in cast(list[Vehicle], values)
            ]
            accepted = len(vehicles)
            reconciled = [
                (
                    item,
                    reconcile_vehicle(item, self.schedule, self.previous_schedule),
                )
                if self.schedule or self.previous_schedule
                else (item, None)
                for item in vehicles
            ]
            reconciliation_summary: dict[str, int] = {}
            for _, reconciliation in reconciled:
                if reconciliation:
                    for summary_key in (
                        f"state:{reconciliation.state}",
                        f"confidence:{reconciliation.confidence}",
                        f"reason:{reconciliation.reason or 'NONE'}",
                    ):
                        reconciliation_summary[summary_key] = (
                            reconciliation_summary.get(summary_key, 0) + 1
                        )
                    self.count_diagnostic(
                        source_id, f"reconciliation_{reconciliation.state.lower()}"
                    )
                    self.count_diagnostic(
                        source_id, f"confidence_{reconciliation.confidence.lower()}"
                    )
                    if reconciliation.reason:
                        self.count_diagnostic(source_id, reconciliation.reason.lower())
            if self.history and reconciliation_summary:
                await self.history.record_quality(
                    source_id,
                    "feed",
                    None,
                    None,
                    "RECONCILIATION_SUMMARY",
                    observed_at,
                    detail=reconciliation_summary,
                )
            vehicles = [
                item
                for item, reconciliation in reconciled
                if not reconciliation or reconciliation.state != "UNRECONCILED"
            ]
            self.count_diagnostic(source_id, "accepted", len(vehicles))
            self.count_diagnostic(source_id, "unreconciled", accepted - len(vehicles))
            previous_values = {
                item.vehicle_id: self.state.vehicles.get(item.vehicle_id) for item in vehicles
            }
            changed = self.state.update_vehicles(vehicles)
            self.count_diagnostic(source_id, "duplicates", len(vehicles) - len(changed))
            for item in changed:
                previous = previous_values[item.vehicle_id]
                if previous and previous != item:
                    for signal in vehicle_quality(previous, item):
                        self.count_diagnostic(source_id, signal.lower())
                        if self.history:
                            await self.history.record_quality(
                                source_id,
                                "vehicle",
                                item.vehicle_id,
                                item.route_id,
                                signal,
                                observed_at,
                            )
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
            reconciled = [
                (
                    item,
                    reconcile_trip_update(item, self.schedule, self.previous_schedule),
                )
                if self.schedule or self.previous_schedule
                else (item, None)
                for item in updates
            ]
            reconciliation_summary = {}
            for _, reconciliation in reconciled:
                if reconciliation:
                    for summary_key in (
                        f"state:{reconciliation.state}",
                        f"confidence:{reconciliation.confidence}",
                        f"reason:{reconciliation.reason or 'NONE'}",
                    ):
                        reconciliation_summary[summary_key] = (
                            reconciliation_summary.get(summary_key, 0) + 1
                        )
                    self.count_diagnostic(
                        source_id, f"reconciliation_{reconciliation.state.lower()}"
                    )
                    self.count_diagnostic(
                        source_id, f"confidence_{reconciliation.confidence.lower()}"
                    )
                    if reconciliation.reason:
                        self.count_diagnostic(source_id, reconciliation.reason.lower())
            if self.history and reconciliation_summary:
                await self.history.record_quality(
                    source_id,
                    "feed",
                    None,
                    None,
                    "RECONCILIATION_SUMMARY",
                    retrieved_at or datetime.now(UTC),
                    detail=reconciliation_summary,
                )
            updates = [
                item
                for item, reconciliation in reconciled
                if not reconciliation or reconciliation.state != "UNRECONCILED"
            ]
            self.count_diagnostic(source_id, "accepted", len(updates))
            self.count_diagnostic(source_id, "unreconciled", accepted - len(updates))
            changed_updates = self.state.update_trip_updates(updates)
            self.count_diagnostic(source_id, "duplicates", len(updates) - len(changed_updates))
            if self.cache:
                await self.cache.put_trip_updates(changed_updates)
            for item in changed_updates:
                self.broker.publish(
                    "arrival.changed", json.dumps({"trip_id": item.trip_id}), item.route_id
                )
                if self.cache:
                    await self.cache.publish_event(
                        "arrival.changed",
                        json.dumps({"schema_version": "1.0.0", "trip_id": item.trip_id}),
                        item.route_id,
                    )
            if self.history:
                await self.history.record_trip_updates(
                    changed_updates, retrieved_at or datetime.now(UTC)
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
    parser: Callable[..., list[Vehicle] | list[TripUpdate] | list[Alert]],
    stop: asyncio.Event,
    projector: RealtimeProjector,
) -> None:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        while not stop.is_set():
            result, payload = await poller.poll(client)
            logger.info(
                "feed_poll_completed",
                source_id=result.source_id,
                outcome=result.outcome,
                status_code=result.status_code,
                bytes_received=result.bytes_received,
                error_code=result.error_code,
                duration_ms=round(
                    (result.completed_at - result.started_at).total_seconds() * 1000, 2
                ),
                feed_age_seconds=(datetime.now(UTC) - poller.health.last_success_at).total_seconds()
                if poller.health.last_success_at
                else None,
            )
            if projector.cache:
                try:
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
                except Exception:
                    projector.count_diagnostic(poller.config.source_id, "redis_errors")
                    logger.exception(
                        "source_health_cache_failed", source_id=poller.config.source_id
                    )
            if projector.history:
                try:
                    await projector.history.record_poll(result)
                except Exception:
                    projector.count_diagnostic(poller.config.source_id, "postgresql_errors")
                    logger.exception("poll_history_failed", source_id=poller.config.source_id)
            if result.outcome not in {"SUCCESS", "NOT_MODIFIED"}:
                projector.count_diagnostic(poller.config.source_id, "feed_outages")
            if payload:
                try:
                    entity_counts = EntityCounts()
                    parsed = parser(payload, entity_counts)
                except Exception:
                    projector.count_diagnostic(poller.config.source_id, "parser_errors")
                    logger.exception("feed_parse_failed", source_id=poller.config.source_id)
                else:
                    for key, amount in entity_counts.as_dict().items():
                        if amount:
                            projector.count_diagnostic(poller.config.source_id, key, amount)
                    try:
                        await projector.project(
                            poller.config.source_id, parsed, result.completed_at
                        )
                    except Exception:
                        projector.count_diagnostic(poller.config.source_id, "projection_errors")
                        logger.exception(
                            "feed_projection_failed", source_id=poller.config.source_id
                        )
                    if projector.cache:
                        try:
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
                        except Exception:
                            projector.count_diagnostic(poller.config.source_id, "redis_errors")
                            logger.exception(
                                "diagnostic_cache_failed",
                                source_id=poller.config.source_id,
                            )
                    logger.info(
                        "feed_processed",
                        source_id=poller.config.source_id,
                        outcome=result.outcome,
                        entities=len(parsed),
                    )
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
    previous_schedule: Schedule | None = None,
) -> None:
    stop = asyncio.Event()
    pollers = build_pollers(raw_path, vehicle_url, trip_url, alert_url)
    projector = RealtimeProjector(
        CurrentState(), EventBroker(), cache, history, schedule, previous_schedule
    )
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
