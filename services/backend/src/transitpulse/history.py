# ruff: noqa: E501
"""Durable, rebuildable records for selected realtime observations."""

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from transitpulse.polling import PollResult
from transitpulse.realtime import TripUpdate, Vehicle

DETAILED_ROUTES = frozenset({"Red", "Orange", "Green-B"})


def expired_partition_names(names: list[str], before: datetime) -> list[str]:
    """Return generated monthly partition names wholly before the retention boundary."""
    cutoff = before.astimezone(UTC)
    expired: list[str] = []
    for name in names:
        match = re.fullmatch(r"vehicle_observations_(\d{4})_(\d{2})", name)
        if not match:
            continue
        year, month = map(int, match.groups())
        month_start = datetime(year, month, 1, tzinfo=UTC)
        month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        if month_end <= cutoff:
            expired.append(name)
    return expired


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
            if result.outcome not in {"SUCCESS", "NOT_MODIFIED"}:
                await connection.execute(
                    text(
                        """INSERT INTO realtime_quality_events
                        (event_id, source_id, entity_type, observed_at, signal, detail)
                        VALUES (:id, :source, 'feed', :observed, 'FEED_GAP',
                        CAST(:detail AS jsonb))"""
                    ),
                    {
                        "id": uuid4(),
                        "source": result.source_id,
                        "observed": result.completed_at,
                        "detail": json.dumps(
                            {"outcome": result.outcome, "error_code": result.error_code}
                        ),
                    },
                )

    async def record_quality(
        self,
        source_id: str,
        entity_type: str,
        entity_id: str | None,
        route_id: str | None,
        signal: str,
        observed_at: datetime,
        reconciliation_state: str | None = None,
        confidence: str | None = None,
        reason: str | None = None,
        detail: Mapping[str, object] | None = None,
    ) -> None:
        if entity_type != "feed" and route_id not in DETAILED_ROUTES:
            return
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    """INSERT INTO realtime_quality_events
                    (event_id, source_id, entity_type, entity_id, route_id, observed_at,
                    signal, reconciliation_state, confidence, reason, detail)
                    VALUES (:id, :source, :entity_type, :entity_id, :route, :observed,
                    :signal, :state, :confidence, :reason, CAST(:detail AS jsonb))"""
                ),
                {
                    "id": uuid4(),
                    "source": source_id,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "route": route_id,
                    "observed": observed_at,
                    "signal": signal,
                    "state": reconciliation_state,
                    "confidence": confidence,
                    "reason": reason,
                    "detail": json.dumps(detail or {}),
                },
            )

    async def record_trip_updates(self, values: list[TripUpdate], retrieved_at: datetime) -> None:
        rows: list[dict[str, object]] = []
        for item in values:
            if item.route_id not in DETAILED_ROUTES:
                continue
            predictions = item.predictions or (None,)
            for prediction in predictions:
                fingerprint = "|".join(
                    [
                        item.trip_id,
                        item.relationship,
                        prediction.stop_id if prediction else "",
                        prediction.relationship if prediction else "",
                        str(prediction.arrival_time if prediction else None),
                        str(prediction.departure_time if prediction else None),
                        str(prediction.arrival_delay_seconds if prediction else None),
                        str(prediction.departure_delay_seconds if prediction else None),
                    ]
                )
                rows.append(
                    {
                        "id": uuid4(),
                        "route": item.route_id,
                        "trip": item.trip_id,
                        "observed": item.timestamp,
                        "retrieved": retrieved_at,
                        "relationship": item.relationship,
                        "stop": prediction.stop_id if prediction else None,
                        "stop_relationship": prediction.relationship if prediction else None,
                        "arrival": prediction.arrival_time if prediction else None,
                        "departure": prediction.departure_time if prediction else None,
                        "arrival_delay": (prediction.arrival_delay_seconds if prediction else None),
                        "departure_delay": (
                            prediction.departure_delay_seconds if prediction else None
                        ),
                        "checksum": hashlib.sha256(fingerprint.encode()).hexdigest(),
                    }
                )
        if not rows:
            return
        async with self.engine.begin() as connection:
            for row in rows:
                await connection.execute(
                    text(
                        """INSERT INTO trip_update_observations
                        (observation_id, route_id, trip_id, observed_at, retrieved_at,
                        trip_relationship, stop_id, stop_relationship, arrival_time,
                        departure_time, arrival_delay_seconds, departure_delay_seconds,
                        checksum)
                        VALUES (:id, :route, :trip, :observed, :retrieved,
                        :relationship, :stop, :stop_relationship, :arrival, :departure,
                        :arrival_delay, :departure_delay, :checksum)
                        ON CONFLICT (checksum) DO NOTHING"""
                    ),
                    row,
                )

    async def measure_usage(self) -> dict[str, int | float | None]:
        async with self.engine.connect() as connection:
            result = (
                (
                    await connection.execute(
                        text(
                            """WITH observations AS (
                        SELECT retrieved_at FROM vehicle_observations
                        UNION ALL
                        SELECT retrieved_at FROM trip_update_observations)
                        SELECT count(*) AS observations,
                        min(retrieved_at) AS first_at, max(retrieved_at) AS last_at,
                        pg_total_relation_size('vehicle_observations') +
                        pg_total_relation_size('trip_update_observations') +
                        pg_total_relation_size('realtime_quality_events') AS bytes
                        FROM observations"""
                        )
                    )
                )
                .mappings()
                .one()
            )
        elapsed_days = (
            max((result["last_at"] - result["first_at"]).total_seconds() / 86400, 1)
            if result["first_at"] and result["last_at"]
            else None
        )
        return {
            "observations": int(result["observations"]),
            "storage_bytes": int(result["bytes"]),
            "observed_days": elapsed_days,
            "estimated_daily_bytes": (
                int(result["bytes"] / elapsed_days) if elapsed_days else None
            ),
        }

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
            partitions = await connection.execute(
                text(
                    "SELECT child.relname FROM pg_inherits "
                    "JOIN pg_class parent ON pg_inherits.inhparent = parent.oid "
                    "JOIN pg_class child ON pg_inherits.inhrelid = child.oid "
                    "WHERE parent.relname = 'vehicle_observations'"
                )
            )
            for partition in expired_partition_names(
                [str(row.relname) for row in partitions], before
            ):
                await connection.execute(text(f"DROP TABLE {partition}"))
            vehicle_result = await connection.execute(
                text("DELETE FROM vehicle_observations WHERE retrieved_at < :before"),
                {"before": before},
            )
            trip_result = await connection.execute(
                text("DELETE FROM trip_update_observations WHERE retrieved_at < :before"),
                {"before": before},
            )
            quality_result = await connection.execute(
                text("DELETE FROM realtime_quality_events WHERE observed_at < :before"),
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
        return sum(result.rowcount or 0 for result in (vehicle_result, trip_result, quality_result))
