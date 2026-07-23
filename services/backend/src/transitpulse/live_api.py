from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from transitpulse.realtime import CurrentState

router = APIRouter(prefix="/api/v1/live", tags=["realtime"])


@router.get("/events")
async def events() -> StreamingResponse:
    async def heartbeat():
        yield 'event: heartbeat\nid: 1\ndata: {"schema_version":"1.0.0"}\n\n'

    return StreamingResponse(heartbeat(), media_type="text/event-stream")


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
