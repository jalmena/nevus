"""person anatomy

Revision ID: c5d9f3a2b1e0
Revises: b4c8e2f19d07
Create Date: 2026-10-30 21:00:00.000000

The anatomy a person's body map draws, each part on its own so that every body can be drawn: the chest (breasts or
unset) and the genitals (vulva, penis or unset). Unset draws neither.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "c5d9f3a2b1e0"
down_revision: str | None = "b4c8e2f19d07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("persons", schema=None) as batch_op:
        batch_op.add_column(sa.Column("chest", sa.String(length=8), nullable=True))
        batch_op.add_column(sa.Column("genitals", sa.String(length=8), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("persons", schema=None) as batch_op:
        batch_op.drop_column("genitals")
        batch_op.drop_column("chest")
