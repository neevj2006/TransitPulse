import json
from datetime import UTC, datetime
from typing import cast

from redis.asyncio import Redis

from transitpulse.events import LiveEvent
from transitpulse.realtime import Alert, TripUpdate, Vehicle


class RedisProbe:
    name = "valkey"

    def __init__(self, url: str) -> None:
        self.client: Redis = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
            url,
            decode_responses=True,
        )

    async def check(self) -> None:
        await self.client.ping()  # pyright: ignore[reportUnknownMemberType]

    async def close(self) -> None:
        await self.client.aclose()


class RedisStateStore:
    """Rebuildable, TTL-bound current-state projection."""

    def __init__(self, client: Redis) -> None:
        self.client = client

    async def close(self) -> None:
        await self.client.aclose()

    async def put_vehicle(self, vehicle: Vehicle, ttl_seconds: int = 180) -> bool:
        key = f"tp:v1:{{mbta}}:vehicle:{vehicle.vehicle_id}"
        timestamp = vehicle.source_timestamp.isoformat() if vehicle.source_timestamp else ""
        existing = await self.client.get(key)  # pyright: ignore[reportUnknownMemberType]
        if existing:
            existing_timestamp = json.loads(existing).get("source_timestamp", "")
            if existing_timestamp and timestamp and timestamp < existing_timestamp:
                return False
        payload = json.dumps(
            {
                "schema_version": 1,
                "vehicle_id": vehicle.vehicle_id,
                "route_id": vehicle.route_id,
                "trip_id": vehicle.trip_id,
                "latitude": vehicle.latitude,
                "longitude": vehicle.longitude,
                "source_timestamp": timestamp,
                "retrieved_at": datetime.now(UTC).isoformat(),
            }
        )
        async with self.client.pipeline(transaction=True) as pipe:  # pyright: ignore[reportUnknownMemberType]
            pipe.set(key, payload, ex=ttl_seconds)
            if vehicle.route_id:
                pipe.zadd(
                    f"tp:v1:{{mbta}}:route:{vehicle.route_id}:vehicles",
                    {vehicle.vehicle_id: datetime.now(UTC).timestamp()},
                )
                pipe.expire(f"tp:v1:{{mbta}}:route:{vehicle.route_id}:vehicles", ttl_seconds + 30)
            await pipe.execute()
        return True

    async def route_vehicles(self, route_id: str) -> list[Vehicle]:
        index_key = f"tp:v1:{{mbta}}:route:{route_id}:vehicles"
        vehicle_ids = await self.client.zrange(index_key, 0, -1)  # pyright: ignore[reportUnknownMemberType]
        values: list[Vehicle] = []
        for vehicle_id in vehicle_ids:
            raw = await self.client.get(f"tp:v1:{{mbta}}:vehicle:{vehicle_id}")  # pyright: ignore[reportUnknownMemberType]
            if not raw:
                continue
            item = json.loads(raw)
            timestamp = item.get("source_timestamp")
            values.append(
                Vehicle(
                    str(vehicle_id),
                    str(item["vehicle_id"]),
                    item.get("route_id"),
                    item.get("trip_id"),
                    float(item["latitude"]),
                    float(item["longitude"]),
                    datetime.fromisoformat(timestamp) if timestamp else None,
                )
            )
        return values

    async def put_trip_updates(self, values: list[TripUpdate], ttl_seconds: int = 180) -> None:
        for item in values:
            await self.client.set(  # pyright: ignore[reportUnknownMemberType]
                f"tp:v1:{{mbta}}:trip:{item.trip_id}",
                json.dumps(
                    {
                        "route_id": item.route_id,
                        "timestamp": item.timestamp.isoformat() if item.timestamp else None,
                    }
                ),
                ex=ttl_seconds,
            )

    async def put_alerts(self, values: list[Alert], ttl_seconds: int = 600) -> None:
        for item in values:
            await self.client.set(  # pyright: ignore[reportUnknownMemberType]
                f"tp:v1:{{mbta}}:alert:{item.entity_id}",
                json.dumps(
                    {"header": item.header, "route_ids": item.route_ids, "stop_ids": item.stop_ids}
                ),
                ex=ttl_seconds,
            )

    async def put_source_health(self, source_id: str, payload: dict[str, object]) -> None:
        await self.client.set(  # pyright: ignore[reportUnknownMemberType]
            f"tp:v1:{{mbta}}:source:{source_id}:health", json.dumps(payload, default=str), ex=300
        )

    async def source_health(self, source_id: str) -> dict[str, object] | None:
        raw = await self.client.get(  # pyright: ignore[reportUnknownMemberType]
            f"tp:v1:{{mbta}}:source:{source_id}:health"
        )
        return json.loads(raw) if raw else None

    async def publish_event(
        self, kind: str, payload: str, route_id: str | None = None, stop_id: str | None = None
    ) -> LiveEvent:
        event_id = int(
            await self.client.incr("tp:v1:{mbta}:events:next-id")  # pyright: ignore[reportUnknownMemberType]
        )
        event = LiveEvent(event_id, kind, route_id, stop_id, payload)
        encoded = json.dumps(event.__dict__)
        async with self.client.pipeline(transaction=True) as pipe:  # pyright: ignore[reportUnknownMemberType]
            pipe.rpush("tp:v1:{mbta}:events", encoded)
            pipe.ltrim("tp:v1:{mbta}:events", -100, -1)
            pipe.expire("tp:v1:{mbta}:events", 300)
            await pipe.execute()
        return event

    async def events_since(
        self, event_id: int, route_id: str | None, stop_id: str | None
    ) -> list[LiveEvent]:
        raw_events = cast(
            list[str],
            await self.client.execute_command(  # pyright: ignore[reportUnknownMemberType, reportGeneralTypeIssues]
                "LRANGE", "tp:v1:{mbta}:events", 0, -1
            ),
        )
        events = [LiveEvent(**json.loads(raw)) for raw in raw_events]
        return [
            event
            for event in events
            if event.event_id > event_id
            and (not route_id or event.route_id == route_id)
            and (not stop_id or event.stop_id == stop_id)
        ]
