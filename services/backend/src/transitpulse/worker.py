import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx
import structlog

from transitpulse.cache import RedisStateStore
from transitpulse.events import EventBroker
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

logger = structlog.get_logger()


class RealtimeProjector:
    """Applies validated feed entities to bounded current state and optional Redis."""

    def __init__(
        self, state: CurrentState, broker: EventBroker, cache: RedisStateStore | None = None
    ) -> None:
        self.state, self.broker, self.cache = state, broker, cache

    async def project(
        self, source_id: str, values: list[Vehicle] | list[TripUpdate] | list[Alert]
    ) -> None:
        if source_id.endswith("vehicles"):
            changed = self.state.update_vehicles(values)  # type: ignore[arg-type]
            for item in changed:
                if self.cache:
                    await self.cache.put_vehicle(item)
                self.broker.publish(
                    "vehicle.changed", json.dumps({"vehicle_id": item.vehicle_id}), item.route_id
                )
        elif source_id.endswith("trip-updates"):
            self.state.update_trip_updates(values)  # type: ignore[arg-type]
            if self.cache:
                await self.cache.put_trip_updates(values)  # type: ignore[arg-type]
        else:
            self.state.update_alerts(values)  # type: ignore[arg-type]
            if self.cache:
                await self.cache.put_alerts(values)  # type: ignore[arg-type]
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
            if payload:
                try:
                    parsed = parser(payload)
                    await projector.project(poller.config.source_id, parsed)
                    logger.info(
                        "feed_processed",
                        source_id=poller.config.source_id,
                        outcome=result.outcome,
                        entities=len(parsed),
                    )
                except Exception:
                    logger.exception("feed_parse_failed", source_id=poller.config.source_id)
            try:
                await asyncio.wait_for(stop.wait(), timeout=poller.next_delay())
            except TimeoutError:
                pass


async def run_worker(
    raw_path: Path,
    vehicle_url: str,
    trip_url: str,
    alert_url: str,
    cache: RedisStateStore | None = None,
) -> None:
    stop = asyncio.Event()
    pollers = build_pollers(raw_path, vehicle_url, trip_url, alert_url)
    projector = RealtimeProjector(CurrentState(), EventBroker(), cache)
    try:
        await asyncio.gather(
            run_poller(pollers["mbta-vehicles"], parse_vehicle_positions, stop, projector),
            run_poller(pollers["mbta-trip-updates"], parse_trip_updates, stop, projector),
            run_poller(pollers["mbta-alerts"], parse_alerts, stop, projector),
        )
    finally:
        if cache:
            await cache.close()
