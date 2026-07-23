import asyncio

import structlog
import uvicorn
from alembic.config import main as alembic_main
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine

from transitpulse.cache import RedisStateStore
from transitpulse.config import get_settings
from transitpulse.history import RealtimeHistoryStore
from transitpulse.logging import configure_logging
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
        run_realtime_worker(
            settings.raw_snapshot_path,
            settings.vehicle_positions_url,
            settings.trip_updates_url,
            settings.alerts_url,
            cache,
            history,
            settings.raw_snapshot_retention_hours,
        )
    )
