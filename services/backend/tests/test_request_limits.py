from collections.abc import AsyncGenerator
from typing import cast

import pytest
from fastapi import HTTPException, Request
from httpx import ASGITransport, AsyncClient
from starlette.types import ASGIApp, Message
from uvicorn._types import ASGI3Application
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from transitpulse.app import create_app
from transitpulse.config import Settings
from transitpulse.live_api import events


async def test_forwarded_clients_have_independent_limits_only_from_trusted_proxy() -> None:
    app = create_app(Settings(environment="test", database_url=None, redis_url=None), probes=[])
    proxy = cast(
        ASGIApp, ProxyHeadersMiddleware(cast(ASGI3Application, app), trusted_hosts=["172.30.0.2"])
    )
    async with AsyncClient(
        transport=ASGITransport(app=proxy, client=("172.30.0.2", 1234)), base_url="http://test"
    ) as client:
        for _ in range(120):
            assert (
                await client.get("/health/live", headers={"X-Forwarded-For": "192.0.2.1"})
            ).status_code == 200
        assert (
            await client.get("/health/live", headers={"X-Forwarded-For": "192.0.2.1"})
        ).status_code == 429
        assert (
            await client.get("/health/live", headers={"X-Forwarded-For": "192.0.2.2"})
        ).status_code == 200
    async with AsyncClient(
        transport=ASGITransport(app=proxy, client=("192.0.2.1", 1234)), base_url="http://test"
    ) as client:
        assert (
            await client.get("/health/live", headers={"X-Forwarded-For": "192.0.2.99"})
        ).status_code == 429


async def test_extension_methods_share_one_metric_series() -> None:
    app = create_app(Settings(environment="test", database_url=None, redis_url=None), probes=[])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for i in range(50):
            await client.request(f"EXTENSION{i}", "/health/live")
    rendered = app.state.metrics.render()
    assert "EXTENSION" not in rendered
    assert 'method="OTHER"' in rendered
    assert len(app.state.metrics._histograms) == 1


async def test_stream_quota_is_per_client_and_released_on_close() -> None:
    app = create_app(Settings(environment="test", database_url=None, redis_url=None), probes=[])
    app.state.event_broker.publish("update", "{}")

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    def request(host: str) -> Request:
        return Request({"type": "http", "app": app, "headers": [], "client": (host, 1234)}, receive)

    streams: list[AsyncGenerator[str | bytes, None]] = []
    try:
        for _ in range(3):
            response = await events(request("192.0.2.1"))
            stream = cast(AsyncGenerator[str | bytes, None], response.body_iterator)
            await anext(stream)
            streams.append(stream)
        with pytest.raises(HTTPException) as error:
            await events(request("192.0.2.1"))
        assert error.value.status_code == 429
        response = await events(request("192.0.2.2"))
        stream = cast(AsyncGenerator[str | bytes, None], response.body_iterator)
        await anext(stream)
        streams.append(stream)
        assert app.state.sse_connections == 4
    finally:
        for stream in streams:
            await stream.aclose()
    assert app.state.sse_connections == 0
    assert app.state.sse_clients == {}
