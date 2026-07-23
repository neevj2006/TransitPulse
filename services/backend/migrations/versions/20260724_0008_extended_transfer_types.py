# ruff: noqa: E501
"""Allow current GTFS extended transfer types.

Revision ID: 20260724_0008
Revises: 20260724_0007
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260724_0008"
down_revision: str | Sequence[str] | None = "20260724_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE transfers DROP CONSTRAINT transfers_transfer_type_check")
    op.execute(
        "ALTER TABLE transfers ADD CONSTRAINT transfers_transfer_type_check CHECK (transfer_type BETWEEN 0 AND 5)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE transfers DROP CONSTRAINT transfers_transfer_type_check")
    op.execute(
        "ALTER TABLE transfers ADD CONSTRAINT transfers_transfer_type_check CHECK (transfer_type BETWEEN 0 AND 3)"
    )
