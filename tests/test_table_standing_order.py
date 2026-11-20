from datetime import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

INSERT = text("""
    INSERT INTO standing_order
        (from_account_id, to_account_id, recipient_name, amount, message,
         frequency, first_run, end_date, next_run, status)
    VALUES
        (:from_account_id, :to_account_id, :recipient_name, :amount, :message,
         :frequency, :first_run, :end_date, :next_run, :status)
""")


def order(accounts, **changes):
    source, target = accounts
    row = {
        "from_account_id": source,
        "to_account_id": target,
        "recipient_name": "Immobilien Huber AG",
        "amount": 185000,
        "message": "Miete",
        "frequency": "monthly",
        "first_run": "2026-12-01",
        "end_date": None,
        "next_run": "2026-12-01",
        "status": "active",
    }
    row.update(changes)
    return row


def insert(engine, row):
    with engine.begin() as conn:
        return conn.execute(INSERT, row).lastrowid


def test_valid_standing_order(db, two_accounts):
    order_id = insert(db, order(two_accounts))
    with db.connect() as conn:
        row = conn.execute(text("SELECT status, created_at FROM standing_order WHERE id = :id"),
                           {"id": order_id}).one()
    assert row.status == "active"
    assert row.created_at is not None


def test_unknown_account_is_rejected(db, two_accounts):
    with pytest.raises(DBAPIError, match="fk_standing_order_to_account"):
        insert(db, order(two_accounts, to_account_id=999999))


@pytest.mark.parametrize("changes, constraint", [
    ({"amount": 0}, "ck_standing_order_amount"),
    ({"amount": -100}, "ck_standing_order_amount"),
    ({"recipient_name": "  "}, "ck_standing_order_recipient"),
    ({"message": ""}, "ck_standing_order_message"),
    ({"end_date": "2026-11-30"}, "ck_standing_order_end_date"),
    ({"next_run": "2026-11-15"}, "ck_standing_order_next_run"),
    ({"next_run": None}, "ck_standing_order_active"),
    ({"status": "ended"}, "ck_standing_order_active"),
    ({"status": "deleted"}, "ck_standing_order_active"),
])
def test_check_constraints_reject_bad_rows(db, two_accounts, changes, constraint):
    with pytest.raises(DBAPIError, match=constraint):
        insert(db, order(two_accounts, **changes))


def test_order_to_the_same_account_is_rejected(db, two_accounts):
    same = (two_accounts[0], two_accounts[0])
    with pytest.raises(DBAPIError, match="ck_standing_order_accounts"):
        insert(db, order(same))


def test_ended_order_without_next_run(db, two_accounts):
    insert(db, order(two_accounts, status="ended", next_run=None))


def test_app_can_change_and_delete_an_order_by_status(db, two_accounts):
    order_id = insert(db, order(two_accounts))
    with db.begin() as conn:
        conn.execute(text("""
            UPDATE standing_order
            SET amount = 190000, message = 'Miete neu', frequency = 'quarterly', end_date = '2027-12-01'
            WHERE id = :id
        """), {"id": order_id})
        conn.execute(text(
            "UPDATE standing_order SET status = 'deleted', next_run = NULL WHERE id = :id"
        ), {"id": order_id})


def test_updated_at_moves_without_update_right_on_it(db, two_accounts, migrate_engine):
    # the app has no UPDATE right on updated_at, mysql has to set it on its own
    order_id = insert(db, order(two_accounts))
    with migrate_engine.begin() as conn:
        conn.execute(text("UPDATE standing_order SET updated_at = '2026-01-01 00:00:00' WHERE id = :id"),
                     {"id": order_id})
    with db.begin() as conn:
        conn.execute(text("UPDATE standing_order SET amount = 1 WHERE id = :id"), {"id": order_id})
        updated_at = conn.execute(text("SELECT updated_at FROM standing_order WHERE id = :id"),
                                  {"id": order_id}).scalar()
    assert updated_at > datetime(2026, 1, 1)


def test_debit_account_cannot_be_changed(db, two_accounts):
    order_id = insert(db, order(two_accounts))
    with pytest.raises(DBAPIError, match="UPDATE command denied"):
        with db.begin() as conn:
            conn.execute(text("UPDATE standing_order SET from_account_id = :other WHERE id = :id"),
                         {"other": two_accounts[1], "id": order_id})


def test_app_user_cannot_delete_orders(db, two_accounts):
    insert(db, order(two_accounts))
    with pytest.raises(DBAPIError, match="DELETE command denied"):
        with db.begin() as conn:
            conn.execute(text("DELETE FROM standing_order"))
