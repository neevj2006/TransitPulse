import asyncio
from datetime import datetime

import httpx
import structlog
import uvicorn
from alembic.config import main as alembic_main
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine

from transitpulse.cache import RedisStateStore
from transitpulse.config import Settings, get_settings
from transitpulse.history import RealtimeHistoryStore
from transitpulse.logging import configure_logging
from transitpulse.schedule.importer import download_archive, import_archive
from transitpulse.schedule.persistence import persist_and_activate
from transitpulse.schedule.repository import load_active_schedule
from transitpulse.worker import run_worker as run_realtime_worker


def run_api() -> None:
    uvicorn.run("transitpulse.main:app", host="127.0.0.1", port=8000, factory=False)


def run_migrations() -> None:
    alembic_main(argv=["upgrade", "head"])


def run_worker() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    structlog.get_logger().info("worker_started", environment=settings.environment)
    cache = (
        RedisStateStore(
            Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
                str(settings.redis_url), decode_responses=True
            )
        )
        if settings.redis_url
        else None
    )
    history = (
        RealtimeHistoryStore(create_async_engine(settings.database_url))
        if settings.database_url
        else None
    )
    asyncio.run(
        _run_configured_worker(
            settings,
            cache,
            history,
        )
    )


async def _run_configured_worker(
    settings: Settings,
    cache: RedisStateStore | None,
    history: RealtimeHistoryStore | None,
) -> None:
    database_url = settings.database_url
    engine = create_async_engine(database_url) if database_url else None
    try:
        schedule = await load_active_schedule(engine) if engine else None
        previous_schedule = await load_active_schedule(engine, "SUPERSEDED") if engine else None
        await run_realtime_worker(
            settings.raw_snapshot_path,
            settings.vehicle_positions_url,
            settings.trip_updates_url,
            settings.alerts_url,
            cache,
            history,
            settings.raw_snapshot_retention_hours,
            settings.detailed_history_retention_days,
            schedule,
            previous_schedule,
        )
    finally:
        if engine:
            await engine.dispose()


async def import_static_feed() -> str:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("TP_DATABASE_URL is required to import a static feed")
    configure_logging(settings.log_level)
    engine = create_async_engine(settings.database_url)
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            archive = await download_archive(settings.static_gtfs_url, client)
        imported = import_archive(archive.payload)
        version_id = await persist_and_activate(
            engine,
            imported,
            source_url=archive.source_url,
            retrieved_at=datetime.fromisoformat(archive.retrieved_at),
        )
        structlog.get_logger().info(
            "static_feed_imported",
            feed_version_id=version_id,
            checksum=archive.checksum,
            source_url=archive.source_url,
            import_statistics=imported.import_statistics(),
            warnings=imported.warnings,
        )
        return version_id
    finally:
        await engine.dispose()


def run_static_import() -> None:
    asyncio.run(import_static_feed())
