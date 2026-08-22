"""Migrate all client codes to the H-801 sequence.

Revision ID: 20260822_0007
Revises: 20260821_0006
"""

from alembic import op

revision = "20260822_0007"
down_revision = "20260821_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TEMPORARY TABLE client_code_migration (
            old_code varchar(32) PRIMARY KEY,
            new_code varchar(32) UNIQUE NOT NULL
        ) ON COMMIT DROP;

        INSERT INTO client_code_migration (old_code, new_code)
        SELECT old_code, 'H-' || (800 + ROW_NUMBER() OVER (
            ORDER BY
                CASE
                    WHEN old_code ~ '^[Jj]-[0-9]+$'
                    THEN substring(old_code from '[0-9]+$')::bigint
                    ELSE 9223372036854775807
                END,
                old_code
        ))::text
        FROM (
            SELECT client_code AS old_code FROM users
            UNION
            SELECT client_code FROM parcels
            UNION
            SELECT client_code FROM import_rows WHERE client_code IS NOT NULL
        ) codes;

        UPDATE users AS target
        SET client_code = mapping.new_code
        FROM client_code_migration AS mapping
        WHERE target.client_code = mapping.old_code;

        UPDATE parcels AS target
        SET client_code = mapping.new_code
        FROM client_code_migration AS mapping
        WHERE target.client_code = mapping.old_code;

        UPDATE import_rows AS target
        SET client_code = mapping.new_code
        FROM client_code_migration AS mapping
        WHERE target.client_code = mapping.old_code;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET client_code = 'J-' || lpad((substring(client_code from '[0-9]+$')::integer - 800)::text, 4, '0')
        WHERE client_code ~ '^H-[0-9]+$';

        UPDATE parcels
        SET client_code = 'J-' || lpad((substring(client_code from '[0-9]+$')::integer - 800)::text, 4, '0')
        WHERE client_code ~ '^H-[0-9]+$';

        UPDATE import_rows
        SET client_code = 'J-' || lpad((substring(client_code from '[0-9]+$')::integer - 800)::text, 4, '0')
        WHERE client_code ~ '^H-[0-9]+$';
        """
    )
