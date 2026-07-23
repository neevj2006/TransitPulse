"""Create the foundation schema marker.

Revision ID: 20260724_0001
Revises:
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260724_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")


def downgrade() -> None:
    pass
