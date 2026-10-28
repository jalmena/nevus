"""image analysed_at

Revision ID: 6e1c2a9f4b73
Revises: 3d50b810bc42
Create Date: 2026-10-28 13:40:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "6e1c2a9f4b73"
down_revision: str | None = "3d50b810bc42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("images", schema=None) as batch_op:
        batch_op.add_column(sa.Column("analysed_at", sa.DateTime(timezone=True), nullable=True))
    # Photos analysed before this column existed are settled: their jobs ran long ago.
    op.execute("UPDATE images SET analysed_at = quality_checked_at WHERE quality_checked_at IS NOT NULL")


def downgrade() -> None:
    with op.batch_alter_table("images", schema=None) as batch_op:
        batch_op.drop_column("analysed_at")
