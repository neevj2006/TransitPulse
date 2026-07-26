# pyright: reportUnknownVariableType=false, reportGeneralTypeIssues=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportOperatorIssue=false
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
                "retrieved_at": (vehicle.retrieved_at or datetime.now(UTC)).isoformat(),
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
                    datetime.fromisoformat(item["retrieved_at"])
                    if item.get("retrieved_at")
                    else None,
                )
            )
        return values

    async def put_trip_updates(self, values: list[TripUpdate], ttl_seconds: int = 180) -> None:
        for item in values:
            key = f"tp:v1:{{mbta}}:trip:{item.trip_id}"
            existing = await self.client.get(key)  # pyright: ignore[reportUnknownMemberType]
            if existing and item.timestamp:
                existing_timestamp = json.loads(existing).get("timestamp")
                if existing_timestamp and item.timestamp.isoformat() < existing_timestamp:
                    continue
            payload = {
                "trip_id": item.trip_id,
                "route_id": item.route_id,
                "timestamp": item.timestamp.isoformat() if item.timestamp else None,
                "source_timestamp": item.timestamp.isoformat() if item.timestamp else None,
                "retrieved_at": item.retrieved_at.isoformat() if item.retrieved_at else None,
                "predictions": [
                    {
                        "stop_id": prediction.stop_id,
                        "arrival_time": prediction.arrival_time.isoformat()
                        if prediction.arrival_time
                        else None,
                        "departure_time": prediction.departure_time.isoformat()
                        if prediction.departure_time
                        else None,
                        "relationship": prediction.relationship,
                        "arrival_delay_seconds": prediction.arrival_delay_seconds,
                        "departure_delay_seconds": prediction.departure_delay_seconds,
                    }
                    for prediction in item.predictions
                ],
            }
            async with self.client.pipeline(transaction=True) as pipe:  # pyright: ignore[reportUnknownMemberType]
                pipe.set(key, json.dumps(payload), ex=ttl_seconds)
                for prediction in item.predictions:
                    index = f"tp:v1:{{mbta}}:stop:{prediction.stop_id}:trips"
                    pipe.sadd(index, item.trip_id)
                    pipe.expire(index, ttl_seconds + 30)
                await pipe.execute()

    async def stop_trip_updates(self, stop_id: str) -> list[dict[str, object]]:
        trip_ids = await self.client.smembers(  # pyright: ignore[reportUnknownMemberType]
            f"tp:v1:{{mbta}}:stop:{stop_id}:trips"
        )
        values: list[dict[str, object]] = []
        for trip_id in trip_ids:
            raw = await self.client.get(f"tp:v1:{{mbta}}:trip:{trip_id}")  # pyright: ignore[reportUnknownMemberType]
            if raw:
                values.append(cast(dict[str, object], json.loads(raw)))
        return values

    async def trip_update(self, trip_id: str) -> dict[str, object] | None:
        raw = await self.client.get(f"tp:v1:{{mbta}}:trip:{trip_id}")  # pyright: ignore[reportUnknownMemberType]
        return cast(dict[str, object], json.loads(raw)) if raw else None

    async def put_alerts(self, values: list[Alert], ttl_seconds: int = 600) -> None:
        for item in values:
            payload = {
                "alert_id": item.entity_id,
                "header": item.header,
                "route_ids": item.route_ids,
                "stop_ids": item.stop_ids,
                "retrieved_at": item.retrieved_at.isoformat() if item.retrieved_at else None,
                "source_timestamp": (
                    item.source_timestamp.isoformat() if item.source_timestamp else None
                ),
            }
            async with self.client.pipeline(transaction=True) as pipe:  # pyright: ignore[reportUnknownMemberType]
                pipe.set(
                    f"tp:v1:{{mbta}}:alert:{item.entity_id}", json.dumps(payload), ex=ttl_seconds
                )
                for index in (
                    "tp:v1:{mbta}:alerts",
                    *(f"tp:v1:{{mbta}}:route:{route}:alerts" for route in item.route_ids),
                    *(f"tp:v1:{{mbta}}:stop:{stop}:alerts" for stop in item.stop_ids),
                ):
                    pipe.sadd(index, item.entity_id)
                    pipe.expire(index, ttl_seconds + 30)
                await pipe.execute()

    async def alerts(self, route_id: str | None, stop_id: str | None) -> list[dict[str, object]]:
        index = (
            f"tp:v1:{{mbta}}:route:{route_id}:alerts"
            if route_id
            else f"tp:v1:{{mbta}}:stop:{stop_id}:alerts"
            if stop_id
            else "tp:v1:{mbta}:alerts"
        )
        alert_ids = await self.client.smembers(index)  # pyright: ignore[reportUnknownMemberType]
        values: list[dict[str, object]] = []
        for alert_id in alert_ids:
            raw = await self.client.get(f"tp:v1:{{mbta}}:alert:{alert_id}")  # pyright: ignore[reportUnknownMemberType]
            if raw:
                item = cast(dict[str, object], json.loads(raw))
                if (not stop_id or stop_id in item.get("stop_ids", [])) and (
                    not route_id or route_id in item.get("route_ids", [])
                ):
                    values.append(item)
        return values

    async def put_source_health(self, source_id: str, payload: dict[str, object]) -> None:
        await self.client.set(  # pyright: ignore[reportUnknownMemberType]
            f"tp:v1:{{mbta}}:source:{source_id}:health", json.dumps(payload, default=str), ex=300
        )

    async def source_health(self, source_id: str) -> dict[str, object] | None:
        raw = await self.client.get(  # pyright: ignore[reportUnknownMemberType]
            f"tp:v1:{{mbta}}:source:{source_id}:health"
        )
        return json.loads(raw) if raw else None

    async def telemetry(self) -> dict[str, int | None]:
        """Return bounded operational measurements without exposing Redis internals."""
        memory = await self.client.info("memory")  # pyright: ignore[reportUnknownMemberType]
        stats = await self.client.info("stats")  # pyright: ignore[reportUnknownMemberType]
        key_count = await self.client.dbsize()  # pyright: ignore[reportUnknownMemberType]
        hits = int(stats.get("keyspace_hits", 0))
        misses = int(stats.get("keyspace_misses", 0))
        return {
            "key_count": int(key_count),
            "memory_bytes": int(memory.get("used_memory", 0)),
            "evicted_keys": int(stats.get("evicted_keys", 0)),
            "commands_processed": int(stats.get("total_commands_processed", 0)),
            "keyspace_hits": hits,
            "keyspace_misses": misses,
            "hit_rate_percent": round((hits / (hits + misses)) * 100) if hits + misses else None,
        }

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
