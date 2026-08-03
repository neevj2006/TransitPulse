"""Read-only empirical connection-risk API."""

from datetime import UTC, datetime, timedelta
from time import monotonic
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import text

from transitpulse.connection_risk import CALCULATION_VERSION, calculate_connection_risk

router = APIRouter(prefix="/api/v1/transfer-risk", tags=["transfer-risk"])


def default_walking_seconds(request: Request, from_stop: str, to_stop: str) -> int:
    schedule = getattr(request.app.state, "schedule", None)
    if schedule:
        matches = [
            transfer.minimum_transfer_seconds
            for transfer in schedule.transfers
            if transfer.from_stop_id == from_stop
            and transfer.to_stop_id == to_stop
            and transfer.minimum_transfer_seconds is not None
        ]
        if matches:
            return max(matches)
    return 0 if from_stop == to_stop else 180


@router.get("")
async def transfer_risk(
    request: Request,
    arriving_route_id: str,
    arriving_stop_id: str,
    connecting_route_id: str,
    connecting_stop_id: str,
    planned_arrival: datetime,
    planned_departure: datetime,
    walking_seconds: int | None = Query(None, ge=0, le=3600),
) -> dict[str, object]:
    if planned_arrival.tzinfo is None or planned_departure.tzinfo is None:
        raise HTTPException(
            422, detail={"code": "INVALID_REQUEST", "message": "Planned times need time zones."}
        )
    if planned_departure <= planned_arrival:
        raise HTTPException(
            422, detail={"code": "INVALID_REQUEST", "message": "Departure must follow arrival."}
        )
    engine = request.app.state.schedule_engine
    if not engine:
        raise HTTPException(
            503,
            detail={"code": "HISTORY_UNAVAILABLE", "message": "Historical data is unavailable."},
        )
    resolved_walking = (
        walking_seconds
        if walking_seconds is not None
        else default_walking_seconds(request, arriving_stop_id, connecting_stop_id)
    )
    cutoff = min(planned_arrival.astimezone(UTC), datetime.now(UTC))
    cache_key = (
        arriving_route_id,
        arriving_stop_id,
        connecting_route_id,
        connecting_stop_id,
        planned_arrival.isoformat(),
        planned_departure.isoformat(),
        resolved_walking,
        cutoff.replace(second=0, microsecond=0).isoformat(),
    )
    cached = request.app.state.transfer_risk_cache.get(cache_key)
    if cached and cached[0] > monotonic():
        return cached[1]
    query = text("""SELECT arrival_delay_seconds AS delay, observed_at
        FROM trip_update_observations
        WHERE route_id = :route_id AND stop_id = :stop_id AND observed_at < :cutoff
          AND arrival_delay_seconds IS NOT NULL
        ORDER BY observed_at DESC LIMIT 100""")
    departure_query = text("""SELECT departure_delay_seconds AS delay, observed_at
        FROM trip_update_observations
        WHERE route_id = :route_id AND stop_id = :stop_id AND observed_at < :cutoff
          AND departure_delay_seconds IS NOT NULL
        ORDER BY observed_at DESC LIMIT 100""")
    async with engine.connect() as connection:
        arrivals = (
            (
                await connection.execute(
                    query,
                    {"route_id": arriving_route_id, "stop_id": arriving_stop_id, "cutoff": cutoff},
                )
            )
            .mappings()
            .all()
        )
        departures = (
            (
                await connection.execute(
                    departure_query,
                    {
                        "route_id": connecting_route_id,
                        "stop_id": connecting_stop_id,
                        "cutoff": cutoff,
                    },
                )
            )
            .mappings()
            .all()
        )
    all_times = [row["observed_at"] for row in [*arrivals, *departures]]
    result = calculate_connection_risk(
        planned_arrival=planned_arrival,
        planned_departure=planned_departure,
        walking_seconds=resolved_walking,
        arrival_delays=[int(row["delay"]) for row in arrivals],
        departure_delays=[int(row["delay"]) for row in departures],
        source_first_at=min(all_times) if all_times else None,
        source_last_at=max(all_times) if all_times else None,
    )
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "data": {
            "sufficient_data": result.sufficient_data,
            "missed_transfer_probability": result.missed_transfer_probability,
            "risk_band": result.risk_band,
            "planned_buffer_seconds": result.planned_buffer_seconds,
            "walking_seconds": resolved_walking,
            "walking_time_source": "user" if walking_seconds is not None else "schedule-or-default",
            "sample_size": result.sample_size,
            "arrival_sample_size": result.arrival_sample_size,
            "departure_sample_size": result.departure_sample_size,
            "source_first_at": result.source_first_at,
            "source_last_at": result.source_last_at,
            "history_stale": bool(
                result.source_last_at
                and datetime.now(UTC) - result.source_last_at > timedelta(days=7)
            ),
            "assumptions": result.assumptions,
        },
        "meta": {
            "request_id": str(uuid4()),
            "generated_at": datetime.now(UTC),
            "calculation_version": CALCULATION_VERSION,
        },
    }
    # The key includes every input and a minute-bucketed as-of cutoff. This
    # makes the short cache safe while avoiding needless duplicate DB queries.
    request.app.state.transfer_risk_cache[cache_key] = (monotonic() + 60, payload)
    return payload
