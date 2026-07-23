from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from transitpulse.cache import RedisProbe
from transitpulse.config import Settings, get_settings
from transitpulse.db import DatabaseProbe
from transitpulse.health import Probe, router
from transitpulse.live_api import router as live_router
from transitpulse.logging import configure_logging
from transitpulse.realtime import CurrentState
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
    app.state.current_state = CurrentState()

    @app.middleware("http")  # pyright: ignore[reportUnusedFunction]
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        try:
            response = await call_next(request)
        except Exception:
            response = JSONResponse(
                {
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected service error.",
                    "request_id": request_id,
                },
                status_code=500,
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = (
            "no-store" if request.url.path.startswith("/api/v1/live") else "public, max-age=60"
        )
        return response

    _ = request_context

    app.include_router(router)
    app.include_router(schedule_router)
    app.include_router(live_router)
    return app
