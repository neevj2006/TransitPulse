from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from transitpulse.events import EventBroker
from transitpulse.realtime import CurrentState

router = APIRouter(prefix="/api/v1/live", tags=["realtime"])


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    pollers = getattr(request.app.state, "pollers", {})
    now = datetime.now(UTC)
    return {
        "schema_version": "1.0.0",
        "data": [
            {
                "source_id": source_id,
                "state": poller.health.state(now),
                "last_success_at": poller.health.last_success_at,
                "consecutive_failures": poller.health.failures,
            }
            for source_id, poller in pollers.items()
        ],
        "meta": {"request_id": str(uuid4()), "generated_at": now},
    }


@router.get("/events")
async def events(
    request: Request, route_id: str | None = None, stop_id: str | None = None
) -> StreamingResponse:
    async def heartbeat():
        broker: EventBroker = request.app.state.event_broker
        last_event = int(request.headers.get("last-event-id", "0"))
        for item in broker.since(last_event, route_id, stop_id):
            yield f"event: {item.kind}\nid: {item.event_id}\ndata: {item.payload}\n\n"
            last_event = item.event_id
        yield f'event: heartbeat\nid: {last_event}\ndata: {{"schema_version":"1.0.0"}}\n\n'

    return StreamingResponse(
        heartbeat(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/routes/{route_id}/vehicles")
async def vehicles(request: Request, route_id: str) -> dict[str, object]:
    state: CurrentState = request.app.state.current_state
    now = datetime.now(UTC)
    values: list[dict[str, object]] = []
    for vehicle in state.route_vehicles(route_id):
        age = (
            int((now - vehicle.source_timestamp).total_seconds())
            if vehicle.source_timestamp
            else None
        )
        values.append(
            {
                "vehicle_id": vehicle.vehicle_id,
                "route_id": vehicle.route_id,
                "trip_id": vehicle.trip_id,
                "latitude": vehicle.latitude,
                "longitude": vehicle.longitude,
                "source_timestamp": vehicle.source_timestamp,
                "freshness": {
                    "state": "HEALTHY" if age is not None and age <= 90 else "STALE",
                    "age_seconds": age,
                },
            }
        )
    return {
        "schema_version": "1.0.0",
        "data": values,
        "meta": {"request_id": str(uuid4()), "generated_at": now},
    }


@router.get("/stops/{stop_id}/arrivals")
async def arrivals(request: Request, stop_id: str) -> dict[str, object]:
    state: CurrentState = request.app.state.current_state
    values = [item for item in state.trip_updates.values() if item.route_id]
    now = datetime.now(UTC)
    return {
        "schema_version": "1.0.0",
        "data": [
            {
                "trip_id": item.trip_id,
                "route_id": item.route_id,
                "agency_prediction": None,
                "scheduled_fallback": {
                    "kind": "scheduled_fallback",
                    "reason": "LIVE_PREDICTION_UNAVAILABLE",
                },
            }
            for item in values[:100]
        ],
        "meta": {
            "request_id": str(uuid4()),
            "stop_id": stop_id,
            "generated_at": now,
            "freshness": "UNKNOWN",
        },
    }


@router.get("/alerts")
async def alerts(
    request: Request, route_id: str | None = None, stop_id: str | None = None
) -> dict[str, object]:
    state: CurrentState = request.app.state.current_state
    values = [
        item
        for item in state.alerts.values()
        if (not route_id or route_id in item.route_ids)
        and (not stop_id or stop_id in item.stop_ids)
    ]
    return {
        "schema_version": "1.0.0",
        "data": [
            {
                "alert_id": item.entity_id,
                "header": item.header,
                "route_ids": item.route_ids,
                "stop_ids": item.stop_ids,
            }
            for item in values[:100]
        ],
        "meta": {"request_id": str(uuid4())},
    }
