from datetime import date
from math import asin, cos, radians, sin, sqrt
from typing import cast
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from transitpulse.schedule.models import Schedule

router = APIRouter(prefix="/api/v1", tags=["schedule"])


class Envelope(BaseModel):
    schema_version: str = "1.0.0"
    data: object
    meta: dict[str, object]


def _schedule(request: Request) -> Schedule:
    schedule = getattr(request.app.state, "schedule", None)
    if schedule is None:
        raise HTTPException(
            503,
            detail={"code": "SCHEDULE_UNAVAILABLE", "message": "A schedule has not been imported."},
        )
    return schedule


def _result(data: object, schedule: Schedule) -> Envelope:
    return Envelope(
        data=data,
        meta={"request_id": str(uuid4()), "agency_id": "mbta", "feed_version_id": schedule.version},
    )


def _arrival_seconds(item: dict[str, object]) -> int:
    scheduled = item.get("scheduled")
    if not isinstance(scheduled, dict):
        return 0
    seconds = cast(dict[str, object], scheduled).get("gtfs_seconds")
    return seconds if isinstance(seconds, int) else 0


def _distance_metres(latitude: float, longitude: float, stop_lat: float, stop_lon: float) -> int:
    latitude_delta = radians(stop_lat - latitude)
    longitude_delta = radians(stop_lon - longitude)
    a = (
        sin(latitude_delta / 2) ** 2
        + cos(radians(latitude)) * cos(radians(stop_lat)) * sin(longitude_delta / 2) ** 2
    )
    return round(6_371_000 * 2 * asin(sqrt(a)))


@router.get("/routes", response_model=Envelope)
async def routes(
    request: Request, q: str | None = None, limit: int = Query(50, ge=1, le=100)
) -> Envelope:
    schedule = _schedule(request)
    needle = q.casefold() if q else ""
    matches = [
        route
        for route in schedule.routes.values()
        if needle
        in " ".join(filter(None, (route.route_id, route.short_name, route.long_name))).casefold()
    ]
    matches.sort(key=lambda route: (route.short_name or route.route_id, route.route_id))
    return _result([route.__dict__ for route in matches[:limit]], schedule)


@router.get("/routes/{route_id}", response_model=Envelope)
async def route(request: Request, route_id: str) -> Envelope:
    schedule = _schedule(request)
    item = schedule.routes.get(route_id)
    if not item:
        raise HTTPException(
            404, detail={"code": "ROUTE_NOT_FOUND", "message": "Route was not found."}
        )
    trips = [trip.__dict__ for trip in schedule.trips.values() if trip.route_id == route_id]
    return _result({"route": item.__dict__, "trips": trips}, schedule)


@router.get("/stops", response_model=Envelope)
async def stops(
    request: Request,
    q: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    limit: int = Query(50, ge=1, le=100),
) -> Envelope:
    schedule = _schedule(request)
    needle = q.casefold() if q else ""
    items = [
        stop
        for stop in schedule.stops.values()
        if needle in f"{stop.stop_id} {stop.name}".casefold()
    ]
    if latitude is not None and longitude is not None:
        items.sort(
            key=lambda stop: (
                abs((stop.latitude or latitude) - latitude)
                + abs((stop.longitude or longitude) - longitude)
            )
        )
    else:
        items.sort(key=lambda stop: (stop.name, stop.stop_id))
    return _result([stop.__dict__ for stop in items[:limit]], schedule)


@router.get("/stops/nearby", response_model=Envelope)
async def nearby_stops(
    request: Request,
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    radius_metres: int = Query(750, ge=1, le=10_000),
    limit: int = Query(20, ge=1, le=100),
) -> Envelope:
    schedule = _schedule(request)
    items = [
        (stop, _distance_metres(latitude, longitude, stop.latitude, stop.longitude))
        for stop in schedule.stops.values()
        if stop.latitude is not None and stop.longitude is not None
    ]
    items.sort(key=lambda item: (item[1], item[0].name, item[0].stop_id))
    return _result(
        [
            {**stop.__dict__, "distance_metres": distance}
            for stop, distance in items
            if distance <= radius_metres
        ][:limit],
        schedule,
    )


@router.get("/stops/{stop_id}", response_model=Envelope)
async def stop(request: Request, stop_id: str) -> Envelope:
    schedule = _schedule(request)
    item = schedule.stops.get(stop_id)
    if not item:
        raise HTTPException(
            404, detail={"code": "STOP_NOT_FOUND", "message": "Stop was not found."}
        )
    route_ids = sorted(
        {
            schedule.trips[time.trip_id].route_id
            for time in schedule.stop_times
            if time.stop_id == stop_id
        }
    )
    return _result({"stop": item.__dict__, "route_ids": route_ids}, schedule)


@router.get("/stops/{stop_id}/arrivals", response_model=Envelope)
async def arrivals(request: Request, stop_id: str, service_date: date) -> Envelope:
    schedule = _schedule(request)
    if stop_id not in schedule.stops:
        raise HTTPException(
            404, detail={"code": "STOP_NOT_FOUND", "message": "Stop was not found."}
        )
    active = schedule.active_service_ids(service_date)
    result: list[dict[str, object]] = []
    for value in schedule.stop_times:
        trip = schedule.trips[value.trip_id]
        if value.stop_id == stop_id and trip.service_id in active:
            result.append(
                {
                    "trip_id": value.trip_id,
                    "route_id": trip.route_id,
                    "headsign": trip.headsign,
                    "stop_sequence": value.sequence,
                    "scheduled": {
                        "kind": "scheduled",
                        "service_date": service_date.isoformat(),
                        "gtfs_seconds": value.arrival_seconds or value.departure_seconds,
                    },
                }
            )
    result.sort(key=_arrival_seconds)
    return _result(result[:200], schedule)


@router.get("/routes/{route_id}/shape", response_model=Envelope)
async def shape(request: Request, route_id: str) -> Envelope:
    schedule = _schedule(request)
    if route_id not in schedule.routes:
        raise HTTPException(
            404, detail={"code": "ROUTE_NOT_FOUND", "message": "Route was not found."}
        )
    shape_ids = {
        trip.shape_id
        for trip in schedule.trips.values()
        if trip.route_id == route_id and trip.shape_id
    }
    return _result(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"shape_id": shape_id},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [longitude, latitude]
                            for _, latitude, longitude in schedule.shapes.get(shape_id, [])
                        ],
                    },
                }
                for shape_id in sorted(shape_ids)
            ],
        },
        schedule,
    )
