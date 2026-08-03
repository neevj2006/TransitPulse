"""Add reproducible reliability aggregation records.

Revision ID: 20260803_0012
Revises: 20260726_0011
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260803_0012"
down_revision: str | Sequence[str] | None = "20260726_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""CREATE TABLE reliability_aggregation_jobs (
    job_id uuid PRIMARY KEY, metric_version text NOT NULL, started_at timestamptz NOT NULL,
    finished_at timestamptz, status text NOT NULL, input_observation_count integer,
    error_code text)""")
    op.execute("""CREATE TABLE reliability_aggregates (
    metric_version text NOT NULL, route_id text, direction_id smallint, stop_id text,
    service_date date NOT NULL, weekday smallint NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    hour smallint NOT NULL CHECK (hour BETWEEN 0 AND 23), sample_size integer NOT NULL,
    coverage double precision NOT NULL CHECK (coverage BETWEEN 0 AND 1),
    median_delay_seconds double precision, p75_delay_seconds double precision,
    p90_delay_seconds double precision, p95_delay_seconds double precision,
    on_time_percentage double precision CHECK (on_time_percentage BETWEEN 0 AND 1),
    source_first_at timestamptz NOT NULL, source_last_at timestamptz NOT NULL,
    PRIMARY KEY (metric_version, route_id, direction_id, stop_id, service_date, weekday, hour))""")
    op.execute(
        "CREATE INDEX reliability_aggregates_route_time "
        "ON reliability_aggregates (route_id, service_date DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS reliability_aggregates, reliability_aggregation_jobs")
