"""Keep Excel upload revisions under a stable import batch.

Revision ID: 20260821_0006
Revises: 20260821_0005
"""

import sqlalchemy as sa

from alembic import op

revision = "20260821_0006"
down_revision = "20260821_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_revisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("import_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("uploaded_by", sa.BigInteger(), nullable=False),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("valid_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["import_id"], ["imports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_revisions_import_id", "import_revisions", ["import_id"])
    op.create_index("ix_import_revisions_file_hash", "import_revisions", ["file_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_import_revisions_file_hash", table_name="import_revisions")
    op.drop_index("ix_import_revisions_import_id", table_name="import_revisions")
    op.drop_table("import_revisions")
