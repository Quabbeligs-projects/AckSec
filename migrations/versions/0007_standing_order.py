"""standing_order table

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-20
"""
from alembic import op

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE standing_order (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            from_account_id BIGINT UNSIGNED NOT NULL,
            to_account_id BIGINT UNSIGNED NOT NULL,
            recipient_name VARCHAR(70) NOT NULL,
            amount BIGINT NOT NULL,
            message VARCHAR(140) NULL,
            frequency ENUM('weekly', 'monthly', 'quarterly', 'yearly') NOT NULL,
            first_run DATE NOT NULL,
            end_date DATE NULL,
            next_run DATE NULL,
            status ENUM('active', 'ended', 'deleted') NOT NULL DEFAULT 'active',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

            PRIMARY KEY (id),
            KEY ix_standing_order_from_account (from_account_id),
            KEY ix_standing_order_to_account (to_account_id),
            KEY ix_standing_order_due (status, next_run),

            CONSTRAINT fk_standing_order_from_account FOREIGN KEY (from_account_id)
                REFERENCES account (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
            CONSTRAINT fk_standing_order_to_account FOREIGN KEY (to_account_id)
                REFERENCES account (id) ON DELETE RESTRICT ON UPDATE RESTRICT,

            CONSTRAINT ck_standing_order_accounts CHECK (from_account_id <> to_account_id),
            CONSTRAINT ck_standing_order_amount CHECK (amount > 0),
            CONSTRAINT ck_standing_order_recipient CHECK (CHAR_LENGTH(TRIM(recipient_name)) > 0),
            CONSTRAINT ck_standing_order_message CHECK (message IS NULL OR CHAR_LENGTH(TRIM(message)) > 0),
            CONSTRAINT ck_standing_order_end_date CHECK (end_date IS NULL OR end_date >= first_run),
            CONSTRAINT ck_standing_order_next_run CHECK (next_run IS NULL OR next_run >= first_run),
            CONSTRAINT ck_standing_order_active CHECK ((status = 'active') = (next_run IS NOT NULL))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """)

    op.execute("GRANT SELECT, INSERT ON standing_order TO 'acksec_app'@'%'")
    op.execute("""
        GRANT UPDATE (to_account_id, recipient_name, amount, message, frequency,
                      first_run, end_date, next_run, status)
        ON standing_order TO 'acksec_app'@'%'
    """)


def downgrade():
    op.execute("""
        REVOKE UPDATE (to_account_id, recipient_name, amount, message, frequency,
                       first_run, end_date, next_run, status)
        ON standing_order FROM 'acksec_app'@'%'
    """)
    op.execute("REVOKE SELECT, INSERT ON standing_order FROM 'acksec_app'@'%'")
    op.execute("DROP TABLE standing_order")
