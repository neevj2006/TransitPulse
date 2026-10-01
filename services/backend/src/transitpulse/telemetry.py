"""Measure SQL execution without recording statements or parameter values."""

from time import monotonic

from sqlalchemy import event
from sqlalchemy.engine import Connection, ExecutionContext
from sqlalchemy.ext.asyncio import AsyncEngine

from transitpulse.metrics import Metrics


def instrument_database(engine: AsyncEngine, metrics: Metrics) -> None:
    def before(
        connection: Connection,
        _cursor: object,
        _statement: str,
        _parameters: object,
        _context: ExecutionContext,
        _many: bool,
    ) -> None:
        connection.info["tp_query_started"] = monotonic()

    def after(
        connection: Connection,
        _cursor: object,
        _statement: str,
        _parameters: object,
        _context: ExecutionContext,
        _many: bool,
    ) -> None:
        started = connection.info.pop("tp_query_started", None)
        if isinstance(started, float):
            metrics.observe("transitpulse_database_query_duration_seconds", monotonic() - started)

    event.listen(engine.sync_engine, "before_cursor_execute", before)
    event.listen(engine.sync_engine, "after_cursor_execute", after)
