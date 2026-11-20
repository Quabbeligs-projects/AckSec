"""audit_log table

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-20
"""
from alembic import op

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE audit_log (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            actor_type ENUM('customer', 'employee', 'system', 'anonymous') NOT NULL,
            actor_customer_id BIGINT UNSIGNED NULL,
            actor_employee_id BIGINT UNSIGNED NULL,
            action VARCHAR(50) NOT NULL,
            subject_customer_id BIGINT UNSIGNED NULL,
            subject_account_id BIGINT UNSIGNED NULL,
            reason VARCHAR(500) NULL,
            ip_address VARCHAR(45) NULL,
            details JSON NULL,

            PRIMARY KEY (id),
            KEY ix_audit_log_actor_customer (actor_customer_id, id),
            KEY ix_audit_log_actor_employee (actor_employee_id, id),
            KEY ix_audit_log_subject_customer (subject_customer_id, id),
            KEY ix_audit_log_subject_account (subject_account_id, id),
            KEY ix_audit_log_action (action, id),
            KEY ix_audit_log_created_at (created_at),

            CONSTRAINT fk_audit_log_actor_customer FOREIGN KEY (actor_customer_id)
                REFERENCES customer (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
            CONSTRAINT fk_audit_log_actor_employee FOREIGN KEY (actor_employee_id)
                REFERENCES employee (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
            CONSTRAINT fk_audit_log_subject_customer FOREIGN KEY (subject_customer_id)
                REFERENCES customer (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
            CONSTRAINT fk_audit_log_subject_account FOREIGN KEY (subject_account_id)
                REFERENCES account (id) ON DELETE RESTRICT ON UPDATE RESTRICT,

            CONSTRAINT ck_audit_log_actor CHECK (
                (actor_type = 'customer'
                    AND actor_customer_id IS NOT NULL AND actor_employee_id IS NULL)
                OR (actor_type = 'employee'
                    AND actor_employee_id IS NOT NULL AND actor_customer_id IS NULL)
                OR (actor_type IN ('system', 'anonymous')
                    AND actor_customer_id IS NULL AND actor_employee_id IS NULL)
            ),
            CONSTRAINT ck_audit_log_action CHECK (REGEXP_LIKE(action, '^[a-z][a-z_]*[a-z]$', 'c')),
            CONSTRAINT ck_audit_log_reason CHECK (reason IS NULL OR CHAR_LENGTH(TRIM(reason)) > 0),
            CONSTRAINT ck_audit_log_details CHECK (details IS NULL OR JSON_TYPE(details) = 'OBJECT')
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """)

    op.execute("GRANT SELECT, INSERT ON audit_log TO 'acksec_app'@'%'")


def downgrade():
    op.execute("REVOKE SELECT, INSERT ON audit_log FROM 'acksec_app'@'%'")
    op.execute("DROP TABLE audit_log")
