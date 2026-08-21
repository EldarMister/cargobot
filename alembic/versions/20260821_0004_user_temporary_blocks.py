"""Add temporary client blocks.

Revision ID: 20260821_0004
Revises: 20260821_0003
"""

import sqlalchemy as sa

from alembic import op

revision = "20260821_0004"
down_revision = "20260821_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "imports",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("imports", "updated_at")
    op.drop_column("users", "blocked_until")
