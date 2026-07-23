from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from transitpulse.cache import RedisProbe
from transitpulse.config import Settings, get_settings
from transitpulse.db import DatabaseProbe
from transitpulse.health import Probe, router
from transitpulse.logging import configure_logging
from transitpulse.schedule.api import router as schedule_router

logger = structlog.get_logger()


def build_probes(settings: Settings) -> list[Probe]:
    probes: list[Probe] = []
    if settings.database_url:
        probes.append(DatabaseProbe(settings.database_url))
    if settings.redis_url:
        probes.append(RedisProbe(str(settings.redis_url)))
    return probes


def create_app(
    settings: Settings | None = None,
    probes: list[Probe] | None = None,
) -> FastAPI:
    application_settings = settings or get_settings()
    configure_logging(application_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        logger.info("application_started", environment=application_settings.environment)
        yield
        for probe in app.state.probes:
            await probe.close()
        logger.info("application_stopped")

    app = FastAPI(
        title="TransitPulse API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = application_settings
    app.state.probes = probes if probes is not None else build_probes(application_settings)
    app.include_router(router)
    app.include_router(schedule_router)
    return app
