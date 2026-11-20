import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

INSERT = text("""
    INSERT INTO ledger_entry (booking_id, account_id, amount, balance_after)
    VALUES (:booking_id, :account_id, :amount, :balance_after)
""")


@pytest.fixture
def booking_id(db):
    with db.begin() as conn:
        return conn.execute(text("""
            INSERT INTO booking (type, reference, recipient_name, idempotency_key)
            VALUES ('transfer', 'K7M2Q9X4B8T3', 'Laura Meier', '3f9c1d0a7b2e4c6d8e0f1a2b3c4d5e6f')
        """)).lastrowid


def entry(booking_id, account_id, amount, balance_after=0):
    return {"booking_id": booking_id, "account_id": account_id,
            "amount": amount, "balance_after": balance_after}


def insert(engine, row):
    with engine.begin() as conn:
        conn.execute(INSERT, row)


def test_debit_and_credit_for_one_booking(db, booking_id, two_accounts):
    source, target = two_accounts
    insert(db, entry(booking_id, source, -5000, 0))
    insert(db, entry(booking_id, target, 5000, 5000))
    with db.connect() as conn:
        total = conn.execute(text(
            "SELECT SUM(amount) FROM ledger_entry WHERE booking_id = :id"
        ), {"id": booking_id}).scalar()
    assert total == 0


def test_zero_amount_is_rejected(db, booking_id, two_accounts):
    with pytest.raises(DBAPIError, match="ck_ledger_entry_amount"):
        insert(db, entry(booking_id, two_accounts[0], 0))


def test_account_cannot_appear_twice_in_one_booking(db, booking_id, two_accounts):
    insert(db, entry(booking_id, two_accounts[0], -100))
    with pytest.raises(DBAPIError, match="uq_ledger_entry_booking_account"):
        insert(db, entry(booking_id, two_accounts[0], 100))


def test_unknown_booking_is_rejected(db, two_accounts):
    with pytest.raises(DBAPIError, match="fk_ledger_entry_booking"):
        insert(db, entry(999999, two_accounts[0], 100))


def test_unknown_account_is_rejected(db, booking_id):
    with pytest.raises(DBAPIError, match="fk_ledger_entry_account"):
        insert(db, entry(booking_id, 999999, 100))


def test_booking_with_entries_cannot_be_deleted(db, migrate_engine, booking_id, two_accounts):
    insert(db, entry(booking_id, two_accounts[0], -100))
    with pytest.raises(DBAPIError, match="fk_ledger_entry_booking"):
        with migrate_engine.begin() as conn:
            conn.execute(text("DELETE FROM booking WHERE id = :id"), {"id": booking_id})


@pytest.mark.parametrize("statement", [
    "UPDATE ledger_entry SET amount = 1000000",
    "DELETE FROM ledger_entry",
])
def test_ledger_entries_are_immutable_for_the_app(db, booking_id, two_accounts, statement):
    insert(db, entry(booking_id, two_accounts[0], -100))
    with pytest.raises(DBAPIError, match="command denied"):
        with db.begin() as conn:
            conn.execute(text(statement))
