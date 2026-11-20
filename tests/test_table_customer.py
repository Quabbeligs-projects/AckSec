import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

INSERT = text("""
    INSERT INTO customer
        (email, password_hash, first_name, last_name, birth_date, street, zip, city, phone,
         must_change_password, password_expires_at)
    VALUES
        (:email, :password_hash, :first_name, :last_name, :birth_date, :street, :zip, :city, :phone,
         :must_change_password, :password_expires_at)
""")


def valid_customer(**changes):
    row = {
        "email": "laura.meier@example.ch",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$placeholder",
        "first_name": "Laura",
        "last_name": "Meier",
        "birth_date": "1990-04-12",
        "street": "Rämistrasse 56",
        "zip": "8001",
        "city": "Zürich",
        "phone": "+41791234567",
        "must_change_password": False,
        "password_expires_at": None,
    }
    row.update(changes)
    return row


def insert(engine, row):
    with engine.begin() as conn:
        conn.execute(INSERT, row)


def test_valid_customer_is_stored_with_defaults(db):
    insert(db, valid_customer())
    with db.connect() as conn:
        stored = conn.execute(text(
            "SELECT is_locked, failed_logins, totp_secret, created_at FROM customer WHERE email = :email"
        ), {"email": "laura.meier@example.ch"}).one()
    assert stored.is_locked == 0
    assert stored.failed_logins == 0
    assert stored.totp_secret is None
    assert stored.created_at is not None


def test_email_is_unique_ignoring_case(db):
    insert(db, valid_customer())
    with pytest.raises(DBAPIError, match="uq_customer_email"):
        insert(db, valid_customer(email="Laura.Meier@Example.CH"))


@pytest.mark.parametrize("changes, constraint", [
    ({"email": "no-at-sign.ch"}, "ck_customer_email"),
    ({"first_name": "   "}, "ck_customer_first_name"),
    ({"last_name": ""}, "ck_customer_last_name"),
    ({"street": " "}, "ck_customer_street"),
    ({"city": ""}, "ck_customer_city"),
    ({"birth_date": "1899-12-31"}, "ck_customer_birth_date"),
    ({"zip": "0800"}, "ck_customer_zip"),
    ({"zip": "80a1"}, "ck_customer_zip"),
    ({"phone": "0791234567"}, "ck_customer_phone"),
    ({"phone": "+4179123456"}, "ck_customer_phone"),
    ({"phone": "+41 79 123 45 67"}, "ck_customer_phone"),
    ({"password_expires_at": "2026-12-01 12:00:00"}, "ck_customer_password_expiry"),
])
def test_check_constraints_reject_bad_rows(db, changes, constraint):
    with pytest.raises(DBAPIError, match=constraint):
        insert(db, valid_customer(**changes))


def test_one_time_password_expiry_is_allowed_with_forced_change(db):
    insert(db, valid_customer(must_change_password=True, password_expires_at="2026-12-01 12:00:00"))


def test_app_user_cannot_delete_customers(db):
    insert(db, valid_customer())
    with pytest.raises(DBAPIError, match="DELETE command denied"):
        with db.begin() as conn:
            conn.execute(text("DELETE FROM customer"))
