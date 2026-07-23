from redis.asyncio import Redis


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
