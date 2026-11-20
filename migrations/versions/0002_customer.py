"""customer table

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-18
"""
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(r"""
        CREATE TABLE customer (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            email VARCHAR(254) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            birth_date DATE NOT NULL,
            street VARCHAR(150) NOT NULL,
            zip CHAR(4) NOT NULL,
            city VARCHAR(100) NOT NULL,
            phone VARCHAR(16) NOT NULL,
            totp_secret VARBINARY(255) NULL,
            totp_last_step BIGINT NULL,
            is_locked BOOLEAN NOT NULL DEFAULT FALSE,
            failed_logins SMALLINT UNSIGNED NOT NULL DEFAULT 0,
            login_blocked_until DATETIME NULL,
            must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
            password_expires_at DATETIME NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (id),
            UNIQUE KEY uq_customer_email (email),

            CONSTRAINT ck_customer_email CHECK (email LIKE '%_@_%'),
            CONSTRAINT ck_customer_first_name CHECK (CHAR_LENGTH(TRIM(first_name)) > 0),
            CONSTRAINT ck_customer_last_name CHECK (CHAR_LENGTH(TRIM(last_name)) > 0),
            CONSTRAINT ck_customer_street CHECK (CHAR_LENGTH(TRIM(street)) > 0),
            CONSTRAINT ck_customer_city CHECK (CHAR_LENGTH(TRIM(city)) > 0),
            CONSTRAINT ck_customer_birth_date CHECK (birth_date >= '1900-01-01'),
            CONSTRAINT ck_customer_zip CHECK (REGEXP_LIKE(zip, '^[1-9][0-9]{3}$')),
            CONSTRAINT ck_customer_phone CHECK (REGEXP_LIKE(phone, '^\\+41[0-9]{9}$')),
            CONSTRAINT ck_customer_password_expiry
                CHECK (password_expires_at IS NULL OR must_change_password = TRUE)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """)

    op.execute("GRANT SELECT, INSERT, UPDATE ON customer TO 'acksec_app'@'%'")

def downgrade():
    op.execute("REVOKE SELECT, INSERT, UPDATE ON customer FROM 'acksec_app'@'%'")
    op.execute("DROP TABLE customer")
