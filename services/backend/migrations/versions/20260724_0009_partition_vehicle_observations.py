# ruff: noqa: E501
"""Partition selected realtime observations by retrieval month.

Revision ID: 20260724_0009
Revises: 20260724_0008
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260724_0009"
down_revision: str | Sequence[str] | None = "20260724_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE vehicle_observations RENAME TO vehicle_observations_legacy")
    op.execute(
        "ALTER INDEX vehicle_observations_route_time RENAME TO vehicle_observations_legacy_route_time"
    )
    op.execute(
        "CREATE TABLE vehicle_observation_dedup (checksum text PRIMARY KEY, recorded_at timestamptz NOT NULL)"
    )
    op.execute(
        "INSERT INTO vehicle_observation_dedup (checksum, recorded_at) SELECT checksum, retrieved_at FROM vehicle_observations_legacy ON CONFLICT DO NOTHING"
    )
    op.execute(
        "CREATE TABLE vehicle_observations (observation_id uuid NOT NULL, route_id text, vehicle_id text NOT NULL, trip_id text, observed_at timestamptz, retrieved_at timestamptz NOT NULL, latitude double precision NOT NULL, longitude double precision NOT NULL, checksum text NOT NULL, PRIMARY KEY (observation_id, retrieved_at)) PARTITION BY RANGE (retrieved_at)"
    )
    op.execute(
        "CREATE INDEX vehicle_observations_route_time ON vehicle_observations (route_id, retrieved_at DESC)"
    )
    op.execute(
        """DO $$
        DECLARE month_start timestamptz;
        BEGIN
          FOR month_start IN SELECT date_trunc('month', retrieved_at) FROM vehicle_observations_legacy GROUP BY 1 LOOP
            EXECUTE format('CREATE TABLE vehicle_observations_%s PARTITION OF vehicle_observations FOR VALUES FROM (%L) TO (%L)', to_char(month_start, 'YYYY_MM'), month_start, month_start + interval '1 month');
          END LOOP;
        END $$"""
    )
    op.execute("INSERT INTO vehicle_observations SELECT * FROM vehicle_observations_legacy")
    op.execute("DROP TABLE vehicle_observations_legacy")


def downgrade() -> None:
    op.execute("DROP TABLE vehicle_observations, vehicle_observation_dedup")
    op.execute(
        "CREATE TABLE vehicle_observations (observation_id uuid PRIMARY KEY, route_id text, vehicle_id text NOT NULL, trip_id text, observed_at timestamptz, retrieved_at timestamptz NOT NULL, latitude double precision NOT NULL, longitude double precision NOT NULL, checksum text NOT NULL UNIQUE)"
    )
    op.execute(
        "CREATE INDEX vehicle_observations_route_time ON vehicle_observations (route_id, retrieved_at DESC)"
    )
