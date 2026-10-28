"""unsettled card photos

Revision ID: a7d3f1c2e9b4
Revises: 6e1c2a9f4b73
Create Date: 2026-10-28 15:10:00.000000
"""

from __future__ import annotations

from alembic import op

revision: str = "a7d3f1c2e9b4"
down_revision: str | None = "6e1c2a9f4b73"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A card photo analysed before the mark's crop existed still has that crop to come: the server's
    # catch-up queues it, and until then the thumbnail must not be cached for a year.
    op.execute(
        "UPDATE images SET analysed_at = NULL WHERE observation_id IS NOT NULL"
        " AND EXISTS (SELECT 1 FROM scale_references s WHERE s.image_id = images.id AND s.kind = 'card')"
        " AND NOT EXISTS (SELECT 1 FROM renditions r WHERE r.image_id = images.id AND r.kind = 'mark')"
    )


def downgrade() -> None:
    op.execute("UPDATE images SET analysed_at = quality_checked_at WHERE analysed_at IS NULL")
