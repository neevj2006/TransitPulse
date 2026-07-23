# ruff: noqa: E501
"""Add versioned agency, service exception, and transfer records.

Revision ID: 20260724_0005
Revises: 20260724_0004
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260724_0005"
down_revision: str | Sequence[str] | None = "20260724_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE agencies (feed_version_id uuid REFERENCES static_feed_versions ON DELETE CASCADE, agency_id text NOT NULL, name text NOT NULL, timezone text NOT NULL, PRIMARY KEY (feed_version_id, agency_id))"
    )
    op.execute(
        "CREATE TABLE service_exceptions (feed_version_id uuid NOT NULL, service_id text NOT NULL, service_date date NOT NULL, is_added boolean NOT NULL, PRIMARY KEY (feed_version_id, service_id, service_date), FOREIGN KEY (feed_version_id, service_id) REFERENCES services(feed_version_id, service_id))"
    )
    op.execute(
        "CREATE TABLE transfers (feed_version_id uuid NOT NULL, from_stop_id text NOT NULL, to_stop_id text NOT NULL, transfer_type integer NOT NULL CHECK (transfer_type BETWEEN 0 AND 3), minimum_transfer_seconds integer CHECK (minimum_transfer_seconds >= 0), PRIMARY KEY (feed_version_id, from_stop_id, to_stop_id), FOREIGN KEY (feed_version_id, from_stop_id) REFERENCES stops(feed_version_id, stop_id), FOREIGN KEY (feed_version_id, to_stop_id) REFERENCES stops(feed_version_id, stop_id))"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS transfers, service_exceptions, agencies")
