"""account table and the bank's cash account

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-20
"""
from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE account (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            customer_id BIGINT UNSIGNED NULL,
            iban CHAR(21) NOT NULL,
            type ENUM('private', 'savings', 'cash') NOT NULL,
            name VARCHAR(50) NULL,
            status ENUM('open', 'locked', 'closed') NOT NULL DEFAULT 'open',
            balance BIGINT NOT NULL DEFAULT 0,
            opened_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            closed_at DATETIME NULL,

            PRIMARY KEY (id),
            UNIQUE KEY uq_account_iban (iban),
            UNIQUE KEY uq_account_single_cash ((CASE WHEN type = 'cash' THEN 1 END)),
            KEY ix_account_customer (customer_id),

            CONSTRAINT fk_account_customer FOREIGN KEY (customer_id)
                REFERENCES customer (id) ON DELETE RESTRICT ON UPDATE RESTRICT,

            CONSTRAINT ck_account_iban CHECK (REGEXP_LIKE(iban, '^CH[0-9]{7}[0-9A-Z]{12}$', 'c')),
            CONSTRAINT ck_account_name CHECK (name IS NULL OR CHAR_LENGTH(TRIM(name)) > 0),
            CONSTRAINT ck_account_owner CHECK ((type = 'cash') = (customer_id IS NULL)),
            CONSTRAINT ck_account_balance CHECK (type = 'cash' OR balance >= 0),
            CONSTRAINT ck_account_closed_empty CHECK (status <> 'closed' OR balance = 0),
            CONSTRAINT ck_account_closed_at CHECK ((status = 'closed') = (closed_at IS NOT NULL))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """)

    op.execute("""
        INSERT INTO account (customer_id, iban, type, name)
        VALUES (NULL, 'CH4299999000000000001', 'cash', 'Kasse')
    """)

    op.execute("GRANT SELECT, INSERT ON account TO 'acksec_app'@'%'")
    op.execute("GRANT UPDATE (balance, status, name, closed_at) ON account TO 'acksec_app'@'%'")


def downgrade():
    op.execute("REVOKE UPDATE (balance, status, name, closed_at) ON account FROM 'acksec_app'@'%'")
    op.execute("REVOKE SELECT, INSERT ON account FROM 'acksec_app'@'%'")
    op.execute("DROP TABLE account")
