import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

CASH_IBAN = "CH4299999000000000001"

INSERT_ACCOUNT = text("""
    INSERT INTO account (customer_id, iban, type, name, status, balance, closed_at)
    VALUES (:customer_id, :iban, :type, :name, :status, :balance, :closed_at)
""")


def account(owner_id, **changes):
    row = {
        "customer_id": owner_id,
        "iban": "CH9300762011623852957",
        "type": "private",
        "name": "Alltag",
        "status": "open",
        "balance": 0,
        "closed_at": None,
    }
    row.update(changes)
    return row


def insert(engine, row):
    with engine.begin() as conn:
        return conn.execute(INSERT_ACCOUNT, row).lastrowid


def test_migration_creates_exactly_one_cash_account(db):
    with db.connect() as conn:
        rows = conn.execute(text("SELECT iban, customer_id, balance FROM account WHERE type = 'cash'")).all()
    assert len(rows) == 1
    assert rows[0].iban == CASH_IBAN
    assert rows[0].customer_id is None
    assert rows[0].balance == 0


def test_new_account_is_open_and_empty(db, customer_id):
    with db.begin() as conn:
        conn.execute(text(
            "INSERT INTO account (customer_id, iban, type) VALUES (:customer_id, :iban, 'private')"
        ), {"customer_id": customer_id, "iban": "CH9300762011623852957"})
        row = conn.execute(text("SELECT status, balance, closed_at FROM account WHERE iban = :iban"),
                           {"iban": "CH9300762011623852957"}).one()
    assert row.status == "open"
    assert row.balance == 0
    assert row.closed_at is None


def test_iban_is_unique(db, customer_id):
    insert(db, account(customer_id))
    with pytest.raises(DBAPIError, match="uq_account_iban"):
        insert(db, account(customer_id, name="Ferien"))


def test_unknown_customer_is_rejected(db):
    with pytest.raises(DBAPIError, match="fk_account_customer"):
        insert(db, account(999999))


@pytest.mark.parametrize("changes, constraint", [
    ({"iban": "DE8937040044053201300"}, "ck_account_iban"),
    ({"iban": "CH93 0076 2011 6238 5"}, "ck_account_iban"),
    ({"iban": "ch9300762011623852957"}, "ck_account_iban"),
    ({"name": "   "}, "ck_account_name"),
    ({"customer_id": None}, "ck_account_owner"),
    ({"balance": -1}, "ck_account_balance"),
    ({"status": "closed", "balance": 500, "closed_at": "2026-11-20 10:00:00"}, "ck_account_closed_empty"),
    ({"status": "closed", "balance": 0, "closed_at": None}, "ck_account_closed_at"),
    ({"status": "open", "closed_at": "2026-11-20 10:00:00"}, "ck_account_closed_at"),
])
def test_check_constraints_reject_bad_rows(db, customer_id, changes, constraint):
    with pytest.raises(DBAPIError, match=constraint):
        insert(db, account(customer_id, **changes))


def test_closed_empty_account_is_allowed(db, customer_id):
    insert(db, account(customer_id, status="closed", balance=0, closed_at="2026-11-20 10:00:00"))


def test_cash_account_must_not_have_an_owner(db, customer_id):
    with pytest.raises(DBAPIError, match="ck_account_owner"):
        insert(db, account(customer_id, type="cash", iban="CH5699999000000000002"))


def test_there_can_only_be_one_cash_account(db):
    with pytest.raises(DBAPIError, match="uq_account_single_cash"):
        insert(db, account(None, type="cash", iban="CH5699999000000000002", name="Kasse 2"))


def test_cash_account_may_go_negative(db):
    with db.begin() as conn:
        conn.execute(text("UPDATE account SET balance = -50000 WHERE type = 'cash'"))


def test_overdraft_is_rejected_on_update(db, customer_id):
    account_id = insert(db, account(customer_id, balance=1000))
    with pytest.raises(DBAPIError, match="ck_account_balance"):
        with db.begin() as conn:
            conn.execute(text("UPDATE account SET balance = balance - 1001 WHERE id = :id"), {"id": account_id})


def test_customer_with_accounts_cannot_be_deleted(db, migrate_engine, customer_id):
    insert(db, account(customer_id))
    with pytest.raises(DBAPIError, match="fk_account_customer"):
        with migrate_engine.begin() as conn:
            conn.execute(text("DELETE FROM customer WHERE id = :id"), {"id": customer_id})


def test_app_user_can_update_allowed_columns(db, customer_id):
    account_id = insert(db, account(customer_id))
    with db.begin() as conn:
        conn.execute(text(
            "UPDATE account SET balance = 500, name = 'Neu', status = 'locked' WHERE id = :id"
        ), {"id": account_id})


@pytest.mark.parametrize("column, value", [
    ("customer_id", None),
    ("iban", "CH5699999000000000002"),
    ("type", "savings"),
])
def test_app_user_cannot_change_owner_iban_or_type(db, customer_id, column, value):
    account_id = insert(db, account(customer_id))
    with pytest.raises(DBAPIError, match="UPDATE command denied"):
        with db.begin() as conn:
            conn.execute(text(f"UPDATE account SET {column} = :value WHERE id = :id"),
                         {"value": value, "id": account_id})


def test_app_user_cannot_delete_accounts(db, customer_id):
    insert(db, account(customer_id))
    with pytest.raises(DBAPIError, match="DELETE command denied"):
        with db.begin() as conn:
            conn.execute(text("DELETE FROM account WHERE type <> 'cash'"))
