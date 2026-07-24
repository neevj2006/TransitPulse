# ruff: noqa: E501
"""Durable, rebuildable records for selected realtime observations."""

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from transitpulse.polling import PollResult
from transitpulse.realtime import Vehicle

DETAILED_ROUTES = frozenset({"Red", "Orange", "Green-B"})


class RealtimeHistoryStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def close(self) -> None:
        await self.engine.dispose()

    async def record_poll(self, result: PollResult) -> None:
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    """INSERT INTO feed_polls (poll_id, source_id, started_at, completed_at, outcome, status_code, payload_checksum, bytes_received, error_code)
                    VALUES (:poll_id, :source_id, :started_at, :completed_at, :outcome, :status_code, :payload_checksum, :bytes_received, :error_code)"""
                ),
                {
                    "poll_id": uuid4(),
                    "source_id": result.source_id,
                    "started_at": result.started_at,
                    "completed_at": result.completed_at,
                    "outcome": result.outcome,
                    "status_code": result.status_code,
                    "payload_checksum": result.checksum,
                    "bytes_received": result.bytes_received,
                    "error_code": result.error_code,
                },
            )

    async def record_vehicles(self, values: list[Vehicle], retrieved_at: datetime) -> None:
        selected = [item for item in values if item.route_id in DETAILED_ROUTES]
        if not selected:
            return
        rows: list[dict[str, object]] = []
        for item in selected:
            fingerprint = "|".join(
                [
                    item.vehicle_id,
                    item.route_id or "",
                    str(item.latitude),
                    str(item.longitude),
                    str(item.source_timestamp),
                ]
            )
            rows.append(
                {
                    "observation_id": uuid4(),
                    "route_id": item.route_id,
                    "vehicle_id": item.vehicle_id,
                    "trip_id": item.trip_id,
                    "observed_at": item.source_timestamp,
                    "retrieved_at": retrieved_at,
                    "latitude": item.latitude,
                    "longitude": item.longitude,
                    "checksum": hashlib.sha256(fingerprint.encode()).hexdigest(),
                }
            )
        async with self.engine.begin() as connection:
            month_start = retrieved_at.astimezone(UTC).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            partition = f"vehicle_observations_{month_start:%Y_%m}"
            await connection.execute(
                text(
                    f"CREATE TABLE IF NOT EXISTS {partition} PARTITION OF vehicle_observations "
                    f"FOR VALUES FROM ('{month_start.isoformat()}') TO ('{month_end.isoformat()}')"
                )
            )
            accepted: list[dict[str, object]] = []
            for row in rows:
                inserted = await connection.execute(
                    text(
                        "INSERT INTO vehicle_observation_dedup (checksum, recorded_at) "
                        "VALUES (:checksum, :retrieved_at) ON CONFLICT DO NOTHING RETURNING checksum"
                    ),
                    row,
                )
                if inserted.scalar_one_or_none():
                    accepted.append(row)
            if not accepted:
                return
            await connection.execute(
                text(
                    """INSERT INTO vehicle_observations (observation_id, route_id, vehicle_id, trip_id, observed_at, retrieved_at, latitude, longitude, checksum)
                    VALUES (:observation_id, :route_id, :vehicle_id, :trip_id, :observed_at, :retrieved_at, :latitude, :longitude, :checksum)"""
                ),
                accepted,
            )

    async def prune_observations(self, before: datetime) -> int:
        async with self.engine.begin() as connection:
            result = await connection.execute(
                text("DELETE FROM vehicle_observations WHERE retrieved_at < :before"),
                {"before": before},
            )
            await connection.execute(
                text(
                    "DELETE FROM vehicle_observation_dedup WHERE recorded_at < :before "
                    "AND NOT EXISTS (SELECT 1 FROM vehicle_observations "
                    "WHERE vehicle_observations.checksum = vehicle_observation_dedup.checksum)"
                ),
                {"before": before},
            )
        return result.rowcount or 0
