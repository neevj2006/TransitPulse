# ruff: noqa: E501
"""Create immutable static GTFS version tables.

Revision ID: 20260724_0002
Revises: 20260724_0001
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260724_0002"
down_revision: str | Sequence[str] | None = "20260724_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    statements = [
        """CREATE TABLE static_feed_versions (
      feed_version_id uuid PRIMARY KEY, agency_id text NOT NULL,
      payload_checksum text NOT NULL, retrieved_at timestamptz NOT NULL,
      import_status text NOT NULL CHECK (import_status IN ('PENDING','ACTIVE','SUPERSEDED','REJECTED')),
      UNIQUE (agency_id, payload_checksum)
    )""",
        """CREATE UNIQUE INDEX one_active_static_feed_per_agency
        ON static_feed_versions (agency_id) WHERE import_status = 'ACTIVE'""",
        """CREATE TABLE routes (
      feed_version_id uuid REFERENCES static_feed_versions ON DELETE CASCADE,
      route_id text NOT NULL, short_name text, long_name text, route_type integer NOT NULL,
      source_color text, PRIMARY KEY (feed_version_id, route_id)
    )""",
        """CREATE TABLE stops (
      feed_version_id uuid REFERENCES static_feed_versions ON DELETE CASCADE,
      stop_id text NOT NULL, name text NOT NULL, latitude double precision, longitude double precision,
      position geometry(Point, 4326), PRIMARY KEY (feed_version_id, stop_id),
      CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
      CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
    )""",
        "CREATE INDEX stops_position_gist ON stops USING gist (position)",
    ]
    for statement in statements:
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS stops, routes, static_feed_versions CASCADE")
