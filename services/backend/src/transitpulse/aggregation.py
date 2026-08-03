"""Idempotent aggregation of retained trip-update observations."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from transitpulse.reliability import METRIC_VERSION


class ReliabilityAggregationStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def aggregate(self, metric_version: str = METRIC_VERSION) -> UUID:
        """Replace one metric-version's rows atomically from retained evidence."""
        job_id = uuid4()
        started_at = datetime.now(UTC)
        try:
            async with self.engine.begin() as connection:
                await connection.execute(
                    text("""INSERT INTO reliability_aggregation_jobs
                    (job_id, metric_version, started_at, status)
                    VALUES (:job_id, :metric_version, :started_at, 'RUNNING')"""),
                    {
                        "job_id": job_id,
                        "metric_version": metric_version,
                        "started_at": started_at,
                    },
                )
                await connection.execute(
                    text(
                        "DELETE FROM reliability_aggregates WHERE metric_version = :metric_version"
                    ),
                    {"metric_version": metric_version},
                )
                await connection.execute(
                    text("""INSERT INTO reliability_aggregates (
                    metric_version, route_id, direction_id, stop_id, service_date, weekday, hour,
                    sample_size, coverage, median_delay_seconds, p75_delay_seconds,
                    p90_delay_seconds, p95_delay_seconds, on_time_percentage, source_first_at,
                    source_last_at)
                    SELECT :metric_version, route_id, direction_id, COALESCE(stop_id, ''),
                    (retrieved_at AT TIME ZONE 'America/New_York')::date,
                    EXTRACT(ISODOW FROM retrieved_at AT TIME ZONE 'America/New_York')::smallint,
                    EXTRACT(HOUR FROM retrieved_at AT TIME ZONE 'America/New_York')::smallint,
                    count(delay), count(delay)::double precision / NULLIF(count(*), 0),
                    percentile_cont(0.5) WITHIN GROUP (ORDER BY delay),
                    percentile_cont(0.75) WITHIN GROUP (ORDER BY delay),
                    percentile_cont(0.9) WITHIN GROUP (ORDER BY delay),
                    percentile_cont(0.95) WITHIN GROUP (ORDER BY delay),
                    avg(CASE WHEN delay <= CASE WHEN route_type IN (2, 4, 5, 6, 7, 12)
                    THEN 360 ELSE 300 END THEN 1.0 ELSE 0.0 END),
                    min(retrieved_at), max(retrieved_at)
                    FROM (
                      SELECT observations.route_id,
                      COALESCE(trips.direction_id, -1) AS direction_id,
                      routes.route_type, observations.stop_id, observations.retrieved_at,
                      COALESCE(observations.arrival_delay_seconds,
                      observations.departure_delay_seconds) AS delay
                      FROM trip_update_observations observations
                      LEFT JOIN static_feed_versions feeds ON feeds.import_status = 'ACTIVE'
                      LEFT JOIN trips ON trips.feed_version_id = feeds.feed_version_id
                      AND trips.trip_id = observations.trip_id
                      LEFT JOIN routes ON routes.feed_version_id = feeds.feed_version_id
                      AND routes.route_id = observations.route_id
                      WHERE stop_relationship IS DISTINCT FROM 'SKIPPED'
                        AND trip_relationship IS DISTINCT FROM 'CANCELED'
                    ) evidence
                    GROUP BY route_id, direction_id, route_type, COALESCE(stop_id, ''),
                    (retrieved_at AT TIME ZONE 'America/New_York')::date,
                    EXTRACT(ISODOW FROM retrieved_at AT TIME ZONE 'America/New_York'),
                    EXTRACT(HOUR FROM retrieved_at AT TIME ZONE 'America/New_York')"""),
                    {"metric_version": metric_version},
                )
                await connection.execute(
                    text("""UPDATE reliability_aggregation_jobs SET status = 'SUCCEEDED',
                    finished_at = :finished_at, input_observation_count =
                    (SELECT count(*) FROM trip_update_observations)
                    WHERE job_id = :job_id"""),
                    {"job_id": job_id, "finished_at": datetime.now(UTC)},
                )
        except Exception as error:
            # The aggregation transaction has rolled back, so persist a separate,
            # safe audit row without retaining exception text or external data.
            async with self.engine.begin() as connection:
                await connection.execute(
                    text("""INSERT INTO reliability_aggregation_jobs
                    (job_id, metric_version, started_at, finished_at, status, error_code)
                    VALUES (:job_id, :metric_version, :started_at, :finished_at,
                    'FAILED', :error_code)"""),
                    {
                        "job_id": job_id,
                        "metric_version": metric_version,
                        "started_at": started_at,
                        "finished_at": datetime.now(UTC),
                        "error_code": type(error).__name__,
                    },
                )
            raise
        return job_id
