import json
from datetime import UTC, datetime

from redis.asyncio import Redis

from transitpulse.realtime import Vehicle


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
