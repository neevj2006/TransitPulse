"""Read-only, evidence-labelled reliability aggregates."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import text

router = APIRouter(prefix="/api/v1/reliability", tags=["reliability"])


@router.get("")
async def reliability(
    request: Request,
    route_id: str | None = None,
    direction_id: int | None = Query(None, ge=0, le=1),
    stop_id: str | None = None,
    weekday: int | None = Query(None, ge=1, le=7),
    hour: int | None = Query(None, ge=0, le=23),
) -> dict[str, object]:
    engine = request.app.state.schedule_engine
    if not engine:
        raise HTTPException(
            503,
            detail={
                "code": "HISTORY_UNAVAILABLE",
                "message": "Historical data is unavailable.",
            },
        )
    clauses = ["metric_version = (SELECT max(metric_version) FROM reliability_aggregates)"]
    parameters: dict[str, object] = {}
    filters = (
        ("route_id", route_id),
        ("direction_id", direction_id),
        ("stop_id", stop_id),
        ("weekday", weekday),
        ("hour", hour),
    )
    for column, value in filters:
        if value is not None:
            clauses.append(f"{column} = :{column}")
            parameters[column] = value
    where = " AND ".join(clauses)
    async with engine.connect() as connection:
        result = await connection.execute(
            text(f"""SELECT * FROM reliability_aggregates
        WHERE {where} ORDER BY service_date DESC, hour"""),
            parameters,
        )
        rows = [dict(row) for row in result.mappings()]
    return {
        "schema_version": "1.0.0",
        "data": rows,
        "meta": {
            "request_id": str(uuid4()),
            "generated_at": datetime.now(UTC),
            "metric_definition": "2026-08-03.1",
            "minimum_sample_size": 20,
            "minimum_coverage": 0.8,
        },
    }
