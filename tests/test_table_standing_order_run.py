import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

INSERT = text("""
    INSERT INTO standing_order_run (standing_order_id, due_date, status, failure_reason, booking_id)
    VALUES (:standing_order_id, :due_date, :status, :failure_reason, :booking_id)
""")


@pytest.fixture
def order_id(db, two_accounts):
    with db.begin() as conn:
        return conn.execute(text("""
            INSERT INTO standing_order
                (from_account_id, to_account_id, recipient_name, amount, frequency, first_run, next_run)
            VALUES (:source, :target, 'Immobilien Huber AG', 185000, 'monthly', '2026-12-01', '2026-12-01')
        """), {"source": two_accounts[0], "target": two_accounts[1]}).lastrowid


def new_booking(engine, reference):
    with engine.begin() as conn:
        return conn.execute(text("""
            INSERT INTO booking (type, reference, recipient_name)
            VALUES ('standing_order', :reference, 'Immobilien Huber AG')
        """), {"reference": reference}).lastrowid


def run(order_id, **changes):
    row = {"standing_order_id": order_id, "due_date": "2026-12-01",
           "status": "failed", "failure_reason": "insufficient_funds", "booking_id": None}
    row.update(changes)
    return row


def insert(engine, row):
    with engine.begin() as conn:
        conn.execute(INSERT, row)


def test_successful_and_failed_runs(db, order_id):
    booking_id = new_booking(db, "S8D2A5U3F6R1")
    insert(db, run(order_id, due_date="2026-12-01", status="done", failure_reason=None, booking_id=booking_id))
    insert(db, run(order_id, due_date="2027-01-01"))


def test_same_due_date_cannot_run_twice(db, order_id):
    insert(db, run(order_id))
    with pytest.raises(DBAPIError, match="uq_standing_order_run_due"):
        insert(db, run(order_id, failure_reason="daily_limit"))


def test_whole_transaction_is_rolled_back_on_a_double_run(db, order_id):
    insert(db, run(order_id))
    with pytest.raises(DBAPIError, match="uq_standing_order_run_due"):
        with db.begin() as conn:
            booking_id = conn.execute(text("""
                INSERT INTO booking (type, reference, recipient_name)
                VALUES ('standing_order', 'R0LLBACKTEST', 'Immobilien Huber AG')
            """)).lastrowid
            conn.execute(INSERT, run(order_id, status="done", failure_reason=None, booking_id=booking_id))
    with db.connect() as conn:
        left_over = conn.execute(text("SELECT COUNT(*) FROM booking WHERE reference = 'R0LLBACKTEST'")).scalar()
    assert left_over == 0


def test_booking_belongs_to_one_run_only(db, order_id):
    booking_id = new_booking(db, "S8D2A5U3F6R1")
    insert(db, run(order_id, status="done", failure_reason=None, booking_id=booking_id))
    with pytest.raises(DBAPIError, match="uq_standing_order_run_booking"):
        insert(db, run(order_id, due_date="2027-01-01", status="done", failure_reason=None, booking_id=booking_id))


@pytest.mark.parametrize("changes", [
    {"status": "done", "failure_reason": None, "booking_id": None},
    {"status": "failed", "failure_reason": None},
])
def test_result_must_be_consistent(db, order_id, changes):
    with pytest.raises(DBAPIError, match="ck_standing_order_run_result"):
        insert(db, run(order_id, **changes))


def test_done_with_reason_is_rejected(db, order_id):
    booking_id = new_booking(db, "S8D2A5U3F6R1")
    with pytest.raises(DBAPIError, match="ck_standing_order_run_result"):
        insert(db, run(order_id, status="done", booking_id=booking_id))


def test_unknown_order_is_rejected(db):
    with pytest.raises(DBAPIError, match="fk_standing_order_run_order"):
        insert(db, run(999999))


@pytest.mark.parametrize("statement", [
    "UPDATE standing_order_run SET failure_reason = 'daily_limit'",
    "DELETE FROM standing_order_run",
])
def test_run_history_is_immutable_for_the_app(db, order_id, statement):
    insert(db, run(order_id))
    with pytest.raises(DBAPIError, match="command denied"):
        with db.begin() as conn:
            conn.execute(text(statement))
