"""standing_order_run table

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-20
"""
from alembic import op

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE standing_order_run (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            standing_order_id BIGINT UNSIGNED NOT NULL,
            due_date DATE NOT NULL,
            status ENUM('done', 'failed') NOT NULL,
            failure_reason ENUM('insufficient_funds', 'daily_limit', 'account_unavailable') NULL,
            booking_id BIGINT UNSIGNED NULL,
            executed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (id),
            UNIQUE KEY uq_standing_order_run_due (standing_order_id, due_date),
            UNIQUE KEY uq_standing_order_run_booking (booking_id),

            CONSTRAINT fk_standing_order_run_order FOREIGN KEY (standing_order_id)
                REFERENCES standing_order (id) ON DELETE RESTRICT ON UPDATE RESTRICT,
            CONSTRAINT fk_standing_order_run_booking FOREIGN KEY (booking_id)
                REFERENCES booking (id) ON DELETE RESTRICT ON UPDATE RESTRICT,

            CONSTRAINT ck_standing_order_run_result CHECK (
                (status = 'done' AND booking_id IS NOT NULL AND failure_reason IS NULL)
                OR (status = 'failed' AND booking_id IS NULL AND failure_reason IS NOT NULL)
            )
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """)

    op.execute("GRANT SELECT, INSERT ON standing_order_run TO 'acksec_app'@'%'")


def downgrade():
    op.execute("REVOKE SELECT, INSERT ON standing_order_run FROM 'acksec_app'@'%'")
    op.execute("DROP TABLE standing_order_run")
