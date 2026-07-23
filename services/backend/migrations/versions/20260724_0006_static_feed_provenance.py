"""Add static feed source provenance.

Revision ID: 20260724_0006
Revises: 20260724_0005
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260724_0006"
down_revision: str | Sequence[str] | None = "20260724_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE static_feed_versions ADD COLUMN source_url text")
    op.execute("ALTER TABLE static_feed_versions ADD COLUMN feed_label text")


def downgrade() -> None:
    op.execute("ALTER TABLE static_feed_versions DROP COLUMN IF EXISTS feed_label")
    op.execute("ALTER TABLE static_feed_versions DROP COLUMN IF EXISTS source_url")
