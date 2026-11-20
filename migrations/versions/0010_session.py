"""session table

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-20
"""
from alembic import op

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE session (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            token_hash VARBINARY(32) NOT NULL,
            customer_id BIGINT UNSIGNED NULL,
            employee_id BIGINT UNSIGNED NULL,
            data JSON NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (id),
            UNIQUE KEY uq_session_token_hash (token_hash),
            KEY ix_session_customer (customer_id),
            KEY ix_session_employee (employee_id),
            KEY ix_session_last_seen (last_seen_at),

            CONSTRAINT fk_session_customer FOREIGN KEY (customer_id)
                REFERENCES customer (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
            CONSTRAINT fk_session_employee FOREIGN KEY (employee_id)
                REFERENCES employee (id) ON DELETE RESTRICT ON UPDATE RESTRICT,

            CONSTRAINT ck_session_token_hash CHECK (LENGTH(token_hash) = 32),
            CONSTRAINT ck_session_owner CHECK (customer_id IS NULL OR employee_id IS NULL),
            CONSTRAINT ck_session_data CHECK (JSON_TYPE(data) = 'OBJECT'),
            CONSTRAINT ck_session_times CHECK (last_seen_at >= created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """)

    # the first table where the app may DELETE: logout, ending all sessions of a 
    # person and expired sessions are all deletes.
    # UPDATE only on data and last_seen_at: at login the old session is deleted and a
    # new one created, so a session never changes owner
    op.execute("GRANT SELECT, INSERT, DELETE ON session TO 'acksec_app'@'%'")
    op.execute("GRANT UPDATE (data, last_seen_at) ON session TO 'acksec_app'@'%'")


def downgrade():
    op.execute("REVOKE UPDATE (data, last_seen_at) ON session FROM 'acksec_app'@'%'")
    op.execute("REVOKE SELECT, INSERT, DELETE ON session FROM 'acksec_app'@'%'")
    op.execute("DROP TABLE session")
