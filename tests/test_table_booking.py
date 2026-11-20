import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

INSERT = text("""
    INSERT INTO booking (type, reference, message, recipient_name, employee_id, idempotency_key)
    VALUES (:type, :reference, :message, :recipient_name, :employee_id, :idempotency_key)
""")


def transfer(**changes):
    row = {
        "type": "transfer",
        "reference": "K7M2Q9X4B8T3",
        "message": "WG-Einkauf",
        "recipient_name": "Sara Brunner",
        "employee_id": None,
        "idempotency_key": "3f9c1d0a7b2e4c6d8e0f1a2b3c4d5e6f",
    }
    row.update(changes)
    return row


def deposit(employee_id, **changes):
    row = {
        "type": "cash_deposit",
        "reference": "D4P9S1T7C2A8",
        "message": None,
        "recipient_name": None,
        "employee_id": employee_id,
        "idempotency_key": None,
    }
    row.update(changes)
    return row


def insert(engine, row):
    with engine.begin() as conn:
        return conn.execute(INSERT, row).lastrowid


def test_valid_bookings_of_every_type(db, employee_id):
    insert(db, transfer())
    insert(db, transfer(type="standing_order", reference="S8D2A5U3F6R1", idempotency_key=None))
    insert(db, deposit(employee_id))


def test_reference_is_unique(db):
    insert(db, transfer())
    with pytest.raises(DBAPIError, match="uq_booking_reference"):
        insert(db, transfer(idempotency_key="0" * 32))


def test_same_transfer_cannot_be_booked_twice(db):
    insert(db, transfer())
    with pytest.raises(DBAPIError, match="uq_booking_idempotency_key"):
        insert(db, transfer(reference="Z9Y8X7W6V5U4"))


def test_deposit_needs_an_existing_employee(db):
    with pytest.raises(DBAPIError, match="fk_booking_employee"):
        insert(db, deposit(999999))


@pytest.mark.parametrize("changes, constraint", [
    ({"reference": "k7m2q9x4b8t3"}, "ck_booking_reference"),
    ({"reference": "K7M2-9X4B8T3"}, "ck_booking_reference"),
    ({"idempotency_key": "3F9C1D0A7B2E4C6D8E0F1A2B3C4D5E6F"}, "ck_booking_idempotency_key"),
    ({"idempotency_key": "not-hex-not-hex-not-hex-not-hex!"}, "ck_booking_idempotency_key"),
    ({"message": "   "}, "ck_booking_message"),
    ({"recipient_name": None}, "ck_booking_recipient"),
    ({"recipient_name": "  "}, "ck_booking_recipient"),
    ({"idempotency_key": None}, "ck_booking_transfer_key"),
    ({"type": "standing_order"}, "ck_booking_transfer_key"),
])
def test_check_constraints_on_transfers(db, changes, constraint):
    with pytest.raises(DBAPIError, match=constraint):
        insert(db, transfer(**changes))


def test_transfer_must_not_name_an_employee(db, employee_id):
    with pytest.raises(DBAPIError, match="ck_booking_deposit_employee"):
        insert(db, transfer(employee_id=employee_id))


def test_deposit_without_employee_is_rejected(db):
    with pytest.raises(DBAPIError, match="ck_booking_deposit_employee"):
        insert(db, deposit(None))


def test_deposit_has_no_recipient(db, employee_id):
    with pytest.raises(DBAPIError, match="ck_booking_recipient"):
        insert(db, deposit(employee_id, recipient_name="Laura Meier"))


@pytest.mark.parametrize("statement", [
    "UPDATE booking SET message = 'changed'",
    "DELETE FROM booking",
])
def test_bookings_are_immutable_for_the_app(db, statement):
    insert(db, transfer())
    with pytest.raises(DBAPIError, match="command denied"):
        with db.begin() as conn:
            conn.execute(text(statement))
