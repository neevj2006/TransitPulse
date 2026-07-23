# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportOperatorIssue=false
import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from transitpulse.cache import RedisStateStore
from transitpulse.events import EventBroker
from transitpulse.realtime import CurrentState

router = APIRouter(prefix="/api/v1/live", tags=["realtime"])


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    pollers = getattr(request.app.state, "pollers", {})
    now = datetime.now(UTC)
    cache: RedisStateStore | None = request.app.state.redis_state_store
    source_ids = ("mbta-vehicles", "mbta-trip-updates", "mbta-alerts")
    if cache:
        values = [await cache.source_health(source_id) for source_id in source_ids]
        return {
            "schema_version": "1.0.0",
            "data": [value for value in values if value],
            "meta": {"request_id": str(uuid4()), "generated_at": now},
        }
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
        cache: RedisStateStore | None = request.app.state.redis_state_store
        last_event = int(request.headers.get("last-event-id", "0"))
        heartbeat_at = asyncio.get_running_loop().time()

        def heartbeat() -> str:
            return f'event: heartbeat\nid: {last_event}\ndata: {{"schema_version":"1.0.0"}}\n\n'

        while not await request.is_disconnected():
            replay = (
                await cache.events_since(last_event, route_id, stop_id)
                if cache
                else broker.since(last_event, route_id, stop_id)
            )
            for item in replay:
                yield f"event: {item.kind}\nid: {item.event_id}\ndata: {item.payload}\n\n"
                last_event = item.event_id
            if asyncio.get_running_loop().time() - heartbeat_at >= 20:
                yield heartbeat()
                heartbeat_at = asyncio.get_running_loop().time()
            if cache:
                await asyncio.sleep(1)
            else:
                broker.changed.clear()
                try:
                    await asyncio.wait_for(broker.changed.wait(), timeout=20)
                except TimeoutError:
                    yield heartbeat()

    return StreamingResponse(
        heartbeat(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/routes/{route_id}/vehicles")
async def vehicles(
    request: Request,
    route_id: str,
    min_latitude: float | None = Query(None, ge=-90, le=90),
    max_latitude: float | None = Query(None, ge=-90, le=90),
    min_longitude: float | None = Query(None, ge=-180, le=180),
    max_longitude: float | None = Query(None, ge=-180, le=180),
) -> dict[str, object]:
    state: CurrentState = request.app.state.current_state
    now = datetime.now(UTC)
    cache: RedisStateStore | None = request.app.state.redis_state_store
    source_vehicles = (
        await cache.route_vehicles(route_id) if cache else state.route_vehicles(route_id)
    )
    bounds = (min_latitude, max_latitude, min_longitude, max_longitude)
    if any(value is not None for value in bounds) and any(value is None for value in bounds):
        raise HTTPException(
            422,
            detail={"code": "INVALID_BOUNDS", "message": "All bounding-box fields are required."},
        )
    if min_latitude is not None and (min_latitude > max_latitude or min_longitude > max_longitude):
        raise HTTPException(
            422, detail={"code": "INVALID_BOUNDS", "message": "Bounding-box ranges are invalid."}
        )
    values: list[dict[str, object]] = []
    for vehicle in source_vehicles:
        if (
            min_latitude is not None
            and max_latitude is not None
            and min_longitude is not None
            and max_longitude is not None
            and not (
                min_latitude <= vehicle.latitude <= max_latitude
                and min_longitude <= vehicle.longitude <= max_longitude
            )
        ):
            continue
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


@router.get("/trips/{trip_id}")
async def trip_progress(request: Request, trip_id: str) -> dict[str, object]:
    state: CurrentState = request.app.state.current_state
    cache: RedisStateStore | None = request.app.state.redis_state_store
    item = await cache.trip_update(trip_id) if cache else state.trip_updates.get(trip_id)
    if not item:
        raise HTTPException(
            404,
            detail={
                "code": "TRIP_LIVE_DATA_UNAVAILABLE",
                "message": "Live trip data is unavailable.",
            },
        )
    if isinstance(item, dict):
        data = item
    else:
        data = {
            "trip_id": item.trip_id,
            "route_id": item.route_id,
            "vehicle_id": item.vehicle_id,
            "source_timestamp": item.timestamp,
            "relationship": item.relationship,
            "predictions": item.predictions,
        }
    return {
        "schema_version": "1.0.0",
        "data": data,
        "meta": {"request_id": str(uuid4()), "generated_at": datetime.now(UTC)},
    }


@router.get("/stops/{stop_id}/arrivals")
async def arrivals(request: Request, stop_id: str) -> dict[str, object]:
    state: CurrentState = request.app.state.current_state
    now = datetime.now(UTC)
    values: list[dict[str, object]] = []
    cache: RedisStateStore | None = request.app.state.redis_state_store
    updates = await cache.stop_trip_updates(stop_id) if cache else list(state.trip_updates.values())
    for item in updates:
        predictions = item["predictions"] if isinstance(item, dict) else item.predictions
        for prediction in predictions:
            prediction_stop = (
                prediction["stop_id"] if isinstance(prediction, dict) else prediction.stop_id
            )
            if prediction_stop != stop_id:
                continue
            arrival_time = (
                prediction.get("arrival_time")
                if isinstance(prediction, dict)
                else prediction.arrival_time
            )
            departure_time = (
                prediction.get("departure_time")
                if isinstance(prediction, dict)
                else prediction.departure_time
            )
            timestamp = item.get("timestamp") if isinstance(item, dict) else item.timestamp
            predicted_time = arrival_time or departure_time
            age = (
                int((now - datetime.fromisoformat(timestamp)).total_seconds())
                if isinstance(timestamp, str)
                else int((now - timestamp).total_seconds())
                if timestamp
                else None
            )
            values.append(
                {
                    "trip_id": item["trip_id"] if isinstance(item, dict) else item.trip_id,
                    "route_id": item.get("route_id") if isinstance(item, dict) else item.route_id,
                    "stop_id": prediction_stop,
                    "agency_prediction": {
                        "kind": "agency_predicted",
                        "arrival_time": arrival_time,
                        "departure_time": departure_time,
                        "relationship": prediction.get("relationship")
                        if isinstance(prediction, dict)
                        else prediction.relationship,
                    },
                    "source_timestamp": timestamp,
                    "freshness": {
                        "state": "HEALTHY" if age is not None and age <= 90 else "STALE",
                        "age_seconds": age,
                    },
                    "scheduled_fallback": None,
                    "sort_timestamp": predicted_time or now,
                }
            )
    values.sort(key=lambda value: str(value.pop("sort_timestamp")))
    return {
        "schema_version": "1.0.0",
        "data": values[:100],
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
    cache: RedisStateStore | None = request.app.state.redis_state_store
    values = (
        await cache.alerts(route_id, stop_id)
        if cache
        else [
            item
            for item in state.alerts.values()
            if (not route_id or route_id in item.route_ids)
            and (not stop_id or stop_id in item.stop_ids)
        ]
    )
    return {
        "schema_version": "1.0.0",
        "data": [
            item
            if isinstance(item, dict)
            else {
                "alert_id": item.entity_id,
                "header": item.header,
                "route_ids": item.route_ids,
                "stop_ids": item.stop_ids,
            }
            for item in values[:100]
        ],
        "meta": {"request_id": str(uuid4())},
    }
