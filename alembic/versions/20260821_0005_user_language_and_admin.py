"""Add client language and delegated admin role.

Revision ID: 20260821_0005
Revises: 20260821_0004
"""

import sqlalchemy as sa

from alembic import op

revision = "20260821_0005"
down_revision = "20260821_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("language", sa.String(length=5), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")
    op.drop_column("users", "language")
