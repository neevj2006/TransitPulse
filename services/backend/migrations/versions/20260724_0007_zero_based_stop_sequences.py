# ruff: noqa: E501
"""Allow official GTFS zero-based stop sequences.

Revision ID: 20260724_0007
Revises: 20260724_0006
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260724_0007"
down_revision: str | Sequence[str] | None = "20260724_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE stop_times DROP CONSTRAINT stop_times_stop_sequence_check")
    op.execute(
        "ALTER TABLE stop_times ADD CONSTRAINT stop_times_stop_sequence_check CHECK (stop_sequence >= 0)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE stop_times DROP CONSTRAINT stop_times_stop_sequence_check")
    op.execute(
        "ALTER TABLE stop_times ADD CONSTRAINT stop_times_stop_sequence_check CHECK (stop_sequence > 0)"
    )
