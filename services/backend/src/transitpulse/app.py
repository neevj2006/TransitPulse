import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import monotonic
from typing import cast
from uuid import uuid4

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from transitpulse.cache import RedisProbe, RedisStateStore
from transitpulse.config import Settings, get_settings
from transitpulse.db import DatabaseProbe
from transitpulse.events import EventBroker
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
        if app.state.redis_state_store:
            await app.state.redis_state_store.close()
        logger.info("application_stopped")

    app = FastAPI(
        title="TransitPulse API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = application_settings
    app.state.probes = probes if probes is not None else build_probes(application_settings)
    app.state.current_state = CurrentState()
    app.state.pollers = {}
    app.state.event_broker = EventBroker()
    app.state.redis_state_store = (
        RedisStateStore(
            Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
                str(application_settings.redis_url), decode_responses=True
            )
        )
        if application_settings.redis_url
        else None
    )
    app.state.request_windows = {}
    app.state.sse_connections = 0
    app.state.sse_lock = asyncio.Lock()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(application_settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type", "Last-Event-ID", "X-Request-ID"],
        max_age=600,
    )

    @app.exception_handler(HTTPException)
    async def http_problem(  # pyright: ignore[reportUnusedFunction]
        request: Request, error: HTTPException
    ) -> JSONResponse:
        detail = cast(dict[str, str], error.detail) if isinstance(error.detail, dict) else {}
        return JSONResponse(
            {
                "code": detail.get("code", "HTTP_ERROR"),
                "message": detail.get("message", "Request could not be completed."),
                "request_id": getattr(request.state, "request_id", None),
            },
            status_code=error.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_problem(  # pyright: ignore[reportUnusedFunction]
        request: Request, _: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            {
                "code": "INVALID_REQUEST",
                "message": "One or more request parameters are invalid.",
                "request_id": getattr(request.state, "request_id", None),
            },
            status_code=422,
        )

    @app.middleware("http")  # pyright: ignore[reportUnusedFunction]
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        client = request.client.host if request.client else "unknown"
        now = monotonic()
        window = [
            moment
            for moment in request.app.state.request_windows.get(client, [])
            if now - moment < 60
        ]
        if len(window) >= 120:
            return JSONResponse(
                {"code": "RATE_LIMITED", "message": "Too many requests.", "request_id": request_id},
                status_code=429,
                headers={"Retry-After": "60", "X-Request-ID": request_id},
            )
        request.app.state.request_windows[client] = [*window, now]
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
