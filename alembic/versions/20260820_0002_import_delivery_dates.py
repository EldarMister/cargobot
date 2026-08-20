"""Store delivery dates selected for each Excel import.

Revision ID: 20260820_0002
Revises: 20260820_0001
"""

import sqlalchemy as sa

from alembic import op

revision = "20260820_0002"
down_revision = "20260820_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("imports", sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("imports", sa.Column("expected_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("imports", "expected_at")
    op.drop_column("imports", "sent_at")
