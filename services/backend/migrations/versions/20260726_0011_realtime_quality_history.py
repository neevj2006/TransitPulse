"""Add durable realtime quality and trip-change evidence.

Revision ID: 20260726_0011
Revises: 20260726_0010
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260726_0011"
down_revision: str | Sequence[str] | None = "20260726_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE realtime_quality_events (
        event_id uuid PRIMARY KEY, source_id text NOT NULL, entity_type text NOT NULL,
        entity_id text, route_id text, observed_at timestamptz NOT NULL,
        signal text NOT NULL, reconciliation_state text, confidence text,
        reason text, detail jsonb NOT NULL DEFAULT '{}'::jsonb)"""
    )
    op.execute(
        "CREATE INDEX realtime_quality_source_time "
        "ON realtime_quality_events (source_id, observed_at DESC)"
    )
    op.execute(
        """CREATE TABLE trip_update_observations (
        observation_id uuid PRIMARY KEY, route_id text, trip_id text NOT NULL,
        observed_at timestamptz, retrieved_at timestamptz NOT NULL,
        trip_relationship text NOT NULL, stop_id text, stop_relationship text,
        arrival_time timestamptz, departure_time timestamptz,
        arrival_delay_seconds integer, departure_delay_seconds integer,
        checksum text NOT NULL UNIQUE)"""
    )
    op.execute(
        "CREATE INDEX trip_update_route_time "
        "ON trip_update_observations (route_id, retrieved_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS trip_update_observations, realtime_quality_events")
