"""Initial Cargo Express schema.

Revision ID: 20260820_0001
Revises:
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260820_0001"
down_revision = None
branch_labels = None
depends_on = None


PARCEL_STATUSES = (
    "CHINA_WAREHOUSE",
    "PREPARING",
    "IN_TRANSIT",
    "ARRIVED_COUNTRY",
    "LOCAL_WAREHOUSE",
    "READY_FOR_PICKUP",
    "DELIVERED",
    "CANCELLED",
)
IMPORT_RESULTS = ("CREATED", "UPDATED", "UNCHANGED", "SKIPPED", "ERROR")


def upgrade() -> None:
    parcel_status = postgresql.ENUM(*PARCEL_STATUSES, name="parcel_status", create_type=False)
    import_result = postgresql.ENUM(*IMPORT_RESULTS, name="import_row_result", create_type=False)
    parcel_status.create(op.get_bind(), checkfirst=True)
    import_result.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("client_code", sa.String(32), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
        sa.UniqueConstraint("client_code", name="uq_users_client_code"),
    )
    op.create_index("ix_users_full_name", "users", ["full_name"])
    op.create_index("ix_users_phone", "users", ["phone"])

    op.create_table(
        "imports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("selected_status", parcel_status, nullable=False),
        sa.Column("uploaded_by", sa.BigInteger(), nullable=False),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("valid_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "parcels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tracking_number", sa.String(128), nullable=False),
        sa.Column("client_code", sa.String(32), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("import_id", sa.Integer(), sa.ForeignKey("imports.id", ondelete="SET NULL")),
        sa.Column("status", parcel_status, nullable=False),
        sa.Column("china_received_at", sa.DateTime(timezone=True)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("expected_at", sa.DateTime(timezone=True)),
        sa.Column("arrived_at", sa.DateTime(timezone=True)),
        sa.Column("ready_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tracking_number", name="uq_parcels_tracking_number"),
    )
    op.create_index("ix_parcels_client_code", "parcels", ["client_code"])

    op.create_table(
        "parcel_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parcel_id", sa.Integer(), sa.ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("old_status", parcel_status),
        sa.Column("new_status", parcel_status, nullable=False),
        sa.Column("changed_by", sa.BigInteger()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_parcel_status_history_parcel_id", "parcel_status_history", ["parcel_id"])

    op.create_table(
        "import_rows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_id", sa.Integer(), sa.ForeignKey("imports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("sheet_name", sa.String(255), nullable=False),
        sa.Column("tracking_number", sa.String(128)),
        sa.Column("client_code", sa.String(32)),
        sa.Column("result", import_result, nullable=False),
        sa.Column("error", sa.Text()),
    )
    op.create_index("ix_import_rows_import_id", "import_rows", ["import_id"])

    op.create_table(
        "settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), server_default="", nullable=False),
    )
    op.bulk_insert(
        sa.table("settings", sa.column("key", sa.String), sa.column("value", sa.Text)),
        [
            {"key": "warehouse_receiver", "value": ""},
            {"key": "warehouse_phone", "value": ""},
            {"key": "warehouse_address", "value": ""},
            {"key": "warehouse_name", "value": ""},
            {"key": "support_username", "value": ""},
        ],
    )


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_table("import_rows")
    op.drop_table("parcel_status_history")
    op.drop_table("parcels")
    op.drop_table("imports")
    op.drop_table("users")
    postgresql.ENUM(*IMPORT_RESULTS, name="import_row_result").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(*PARCEL_STATUSES, name="parcel_status").drop(op.get_bind(), checkfirst=True)
