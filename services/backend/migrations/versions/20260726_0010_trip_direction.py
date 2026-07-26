"""Persist scheduled trip direction identifiers.

Revision ID: 20260726_0010
Revises: 20260724_0009
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260726_0010"
down_revision: str | Sequence[str] | None = "20260724_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE trips ADD COLUMN direction_id smallint "
        "CHECK (direction_id IS NULL OR direction_id IN (0, 1))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE trips DROP COLUMN direction_id")
