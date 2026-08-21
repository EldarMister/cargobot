"""Store one-time delivery reminder timestamps.

Revision ID: 20260821_0003
Revises: 20260820_0002
"""

import sqlalchemy as sa

from alembic import op

revision = "20260821_0003"
down_revision = "20260820_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "parcels",
        sa.Column("approaching_notified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "parcels",
        sa.Column("due_notified_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("parcels", "due_notified_at")
    op.drop_column("parcels", "approaching_notified_at")
