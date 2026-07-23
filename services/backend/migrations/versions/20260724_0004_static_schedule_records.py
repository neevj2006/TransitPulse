"""Add versioned static schedule records.

Revision ID: 20260724_0004
Revises: 20260724_0003
"""

# ruff: noqa: E501
from collections.abc import Sequence

from alembic import op

revision: str = "20260724_0004"
down_revision: str | Sequence[str] | None = "20260724_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE services (feed_version_id uuid REFERENCES static_feed_versions ON DELETE CASCADE, service_id text NOT NULL, monday boolean NOT NULL, tuesday boolean NOT NULL, wednesday boolean NOT NULL, thursday boolean NOT NULL, friday boolean NOT NULL, saturday boolean NOT NULL, sunday boolean NOT NULL, start_date date NOT NULL, end_date date NOT NULL, PRIMARY KEY (feed_version_id, service_id))"
    )
    op.execute(
        "CREATE TABLE trips (feed_version_id uuid REFERENCES static_feed_versions ON DELETE CASCADE, trip_id text NOT NULL, route_id text NOT NULL, service_id text NOT NULL, shape_id text, headsign text, PRIMARY KEY (feed_version_id, trip_id), FOREIGN KEY (feed_version_id, route_id) REFERENCES routes(feed_version_id, route_id), FOREIGN KEY (feed_version_id, service_id) REFERENCES services(feed_version_id, service_id))"
    )
    op.execute(
        "CREATE TABLE stop_times (feed_version_id uuid NOT NULL, trip_id text NOT NULL, stop_sequence integer NOT NULL CHECK (stop_sequence > 0), stop_id text NOT NULL, arrival_seconds integer CHECK (arrival_seconds BETWEEN 0 AND 172799), departure_seconds integer CHECK (departure_seconds BETWEEN 0 AND 172799), PRIMARY KEY (feed_version_id, trip_id, stop_sequence), FOREIGN KEY (feed_version_id, trip_id) REFERENCES trips(feed_version_id, trip_id), FOREIGN KEY (feed_version_id, stop_id) REFERENCES stops(feed_version_id, stop_id))"
    )
    op.execute(
        "CREATE INDEX stop_times_stop_arrival ON stop_times (feed_version_id, stop_id, arrival_seconds)"
    )
    op.execute(
        "CREATE TABLE shape_points (feed_version_id uuid REFERENCES static_feed_versions ON DELETE CASCADE, shape_id text NOT NULL, sequence integer NOT NULL, latitude double precision NOT NULL, longitude double precision NOT NULL, PRIMARY KEY (feed_version_id, shape_id, sequence), CHECK (latitude BETWEEN -90 AND 90), CHECK (longitude BETWEEN -180 AND 180))"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS shape_points, stop_times, trips, services")
