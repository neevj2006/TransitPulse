import asyncio
from collections.abc import Callable, Sized
from pathlib import Path

import httpx
import structlog

from transitpulse.polling import FeedConfig, FeedPoller, RawSnapshotStore
from transitpulse.realtime import parse_alerts, parse_trip_updates, parse_vehicle_positions

logger = structlog.get_logger()


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
    poller: FeedPoller, parser: Callable[[bytes], Sized], stop: asyncio.Event
) -> None:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        while not stop.is_set():
            result, payload = await poller.poll(client)
            if payload:
                try:
                    parsed = parser(payload)
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


async def run_worker(raw_path: Path, vehicle_url: str, trip_url: str, alert_url: str) -> None:
    stop = asyncio.Event()
    pollers = build_pollers(raw_path, vehicle_url, trip_url, alert_url)
    await asyncio.gather(
        run_poller(pollers["mbta-vehicles"], parse_vehicle_positions, stop),
        run_poller(pollers["mbta-trip-updates"], parse_trip_updates, stop),
        run_poller(pollers["mbta-alerts"], parse_alerts, stop),
    )
