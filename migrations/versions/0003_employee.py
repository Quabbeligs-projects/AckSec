"""employee table

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-20
"""
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE employee (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            email VARCHAR(254) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            totp_secret VARBINARY(255) NULL,
            totp_last_step BIGINT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            failed_logins SMALLINT UNSIGNED NOT NULL DEFAULT 0,
            login_blocked_until DATETIME NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (id),
            UNIQUE KEY uq_employee_email (email),

            CONSTRAINT ck_employee_email CHECK (email LIKE '%_@_%'),
            CONSTRAINT ck_employee_first_name CHECK (CHAR_LENGTH(TRIM(first_name)) > 0),
            CONSTRAINT ck_employee_last_name CHECK (CHAR_LENGTH(TRIM(last_name)) > 0)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """)

    op.execute("GRANT SELECT ON employee TO 'acksec_app'@'%'")
    op.execute("""
        GRANT UPDATE (failed_logins, login_blocked_until, totp_secret, totp_last_step)
        ON employee TO 'acksec_app'@'%'
    """)


def downgrade():
    op.execute("""
        REVOKE UPDATE (failed_logins, login_blocked_until, totp_secret, totp_last_step)
        ON employee FROM 'acksec_app'@'%'
    """)
    op.execute("REVOKE SELECT ON employee FROM 'acksec_app'@'%'")
    op.execute("DROP TABLE employee")
