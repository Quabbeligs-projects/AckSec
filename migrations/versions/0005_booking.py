"""booking table

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-20
"""
from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE booking (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            type ENUM('transfer', 'standing_order', 'cash_deposit') NOT NULL,
            reference CHAR(12) NOT NULL,
            message VARCHAR(140) NULL,
            recipient_name VARCHAR(70) NULL,
            employee_id BIGINT UNSIGNED NULL,
            idempotency_key CHAR(32) NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (id),
            UNIQUE KEY uq_booking_reference (reference),
            UNIQUE KEY uq_booking_idempotency_key (idempotency_key),
            KEY ix_booking_employee (employee_id),

            CONSTRAINT fk_booking_employee FOREIGN KEY (employee_id)
                REFERENCES employee (id) ON DELETE RESTRICT ON UPDATE RESTRICT,

            CONSTRAINT ck_booking_reference CHECK (REGEXP_LIKE(reference, '^[0-9A-Z]{12}$', 'c')),
            CONSTRAINT ck_booking_idempotency_key
                CHECK (idempotency_key IS NULL OR REGEXP_LIKE(idempotency_key, '^[0-9a-f]{32}$', 'c')),
            CONSTRAINT ck_booking_message CHECK (message IS NULL OR CHAR_LENGTH(TRIM(message)) > 0),
            CONSTRAINT ck_booking_deposit_employee CHECK ((type = 'cash_deposit') = (employee_id IS NOT NULL)),
            CONSTRAINT ck_booking_transfer_key CHECK ((type = 'transfer') = (idempotency_key IS NOT NULL)),
            CONSTRAINT ck_booking_recipient CHECK (
                (type = 'cash_deposit' AND recipient_name IS NULL)
                OR (type <> 'cash_deposit' AND recipient_name IS NOT NULL
                    AND CHAR_LENGTH(TRIM(recipient_name)) > 0)
            )
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """)

    op.execute("GRANT SELECT, INSERT ON booking TO 'acksec_app'@'%'")


def downgrade():
    op.execute("REVOKE SELECT, INSERT ON booking FROM 'acksec_app'@'%'")
    op.execute("DROP TABLE booking")
