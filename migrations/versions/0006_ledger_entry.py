"""ledger_entry table

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-20
"""
from alembic import op

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE ledger_entry (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            booking_id BIGINT UNSIGNED NOT NULL,
            account_id BIGINT UNSIGNED NOT NULL,
            amount BIGINT NOT NULL,
            balance_after BIGINT NOT NULL,

            PRIMARY KEY (id),
            UNIQUE KEY uq_ledger_entry_booking_account (booking_id, account_id),
            KEY ix_ledger_entry_account (account_id, id),

            CONSTRAINT fk_ledger_entry_booking FOREIGN KEY (booking_id)
                REFERENCES booking (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
            CONSTRAINT fk_ledger_entry_account FOREIGN KEY (account_id)
                REFERENCES account (id) ON DELETE RESTRICT ON UPDATE RESTRICT,

            CONSTRAINT ck_ledger_entry_amount CHECK (amount <> 0)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """)

    op.execute("GRANT SELECT, INSERT ON ledger_entry TO 'acksec_app'@'%'")


def downgrade():
    op.execute("REVOKE SELECT, INSERT ON ledger_entry FROM 'acksec_app'@'%'")
    op.execute("DROP TABLE ledger_entry")
