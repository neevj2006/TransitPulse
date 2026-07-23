"""Add realtime evidence and poll history.

Revision ID: 20260724_0003
Revises: 20260724_0002
"""

# ruff: noqa: E501
from collections.abc import Sequence

from alembic import op

revision: str = "20260724_0003"
down_revision: str | Sequence[str] | None = "20260724_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE feed_polls (poll_id uuid PRIMARY KEY, source_id text NOT NULL, started_at timestamptz NOT NULL, completed_at timestamptz NOT NULL, outcome text NOT NULL, status_code integer, payload_checksum text, bytes_received integer NOT NULL, error_code text)"""
    )
    op.execute("CREATE INDEX feed_polls_source_started ON feed_polls (source_id, started_at DESC)")
    op.execute(
        """CREATE TABLE vehicle_observations (observation_id uuid PRIMARY KEY, route_id text, vehicle_id text NOT NULL, trip_id text, observed_at timestamptz, retrieved_at timestamptz NOT NULL, latitude double precision NOT NULL, longitude double precision NOT NULL, checksum text NOT NULL UNIQUE)"""
    )
    op.execute(
        "CREATE INDEX vehicle_observations_route_time ON vehicle_observations (route_id, retrieved_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vehicle_observations, feed_polls")
