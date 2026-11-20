import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

INSERT = text("""
    INSERT INTO employee (email, password_hash, first_name, last_name)
    VALUES (:email, :password_hash, :first_name, :last_name)
""")


def valid_employee(**changes):
    row = {
        "email": "m.huber@acksec.ch",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$placeholder",
        "first_name": "Martin",
        "last_name": "Huber",
    }
    row.update(changes)
    return row


def add_employee(migrate_engine, **changes):
    with migrate_engine.begin() as conn:
        conn.execute(INSERT, valid_employee(**changes))


def test_new_employee_is_active_without_2fa(db, migrate_engine):
    add_employee(migrate_engine)
    with db.connect() as conn:
        row = conn.execute(text(
            "SELECT is_active, totp_secret, failed_logins FROM employee WHERE email = :email"
        ), {"email": "m.huber@acksec.ch"}).one()
    assert row.is_active == 1
    assert row.totp_secret is None
    assert row.failed_logins == 0


def test_email_is_unique_ignoring_case(db, migrate_engine):
    add_employee(migrate_engine)
    with pytest.raises(DBAPIError, match="uq_employee_email"):
        add_employee(migrate_engine, email="M.Huber@AckSec.ch")


@pytest.mark.parametrize("changes, constraint", [
    ({"email": "kein-at.ch"}, "ck_employee_email"),
    ({"first_name": "  "}, "ck_employee_first_name"),
    ({"last_name": ""}, "ck_employee_last_name"),
])
def test_check_constraints_reject_bad_rows(db, migrate_engine, changes, constraint):
    with pytest.raises(DBAPIError, match=constraint):
        add_employee(migrate_engine, **changes)


def test_app_user_cannot_create_employees(db):
    with pytest.raises(DBAPIError, match="INSERT command denied"):
        with db.begin() as conn:
            conn.execute(INSERT, valid_employee())


def test_app_user_cannot_delete_employees(db, migrate_engine):
    add_employee(migrate_engine)
    with pytest.raises(DBAPIError, match="DELETE command denied"):
        with db.begin() as conn:
            conn.execute(text("DELETE FROM employee"))


def test_app_user_can_update_login_columns(db, migrate_engine):
    add_employee(migrate_engine)
    with db.begin() as conn:
        conn.execute(text("""
            UPDATE employee
            SET failed_logins = 3, login_blocked_until = '2026-11-20 10:15:00',
                totp_secret = :secret, totp_last_step = 59000000
            WHERE email = :email
        """), {"secret": b"encrypted", "email": "m.huber@acksec.ch"})


@pytest.mark.parametrize("column, value", [
    ("email", "attacker@example.ch"),
    ("password_hash", "$argon2id$attacker"),
    ("is_active", 1),
    ("first_name", "Mallory"),
])
def test_app_user_cannot_update_other_columns(db, migrate_engine, column, value):
    add_employee(migrate_engine)
    with pytest.raises(DBAPIError, match="UPDATE command denied"):
        with db.begin() as conn:
            conn.execute(text(f"UPDATE employee SET {column} = :value"), {"value": value})
