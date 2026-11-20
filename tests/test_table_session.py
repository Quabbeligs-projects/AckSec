import hashlib
import secrets

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

INSERT = text("""
    INSERT INTO session (token_hash, customer_id, employee_id, data)
    VALUES (:token_hash, :customer_id, :employee_id, :data)
""")


def token_hash():
    return hashlib.sha256(secrets.token_bytes(32)).digest()


def session_row(**changes):
    row = {"token_hash": token_hash(), "customer_id": None, "employee_id": None, "data": "{}"}
    row.update(changes)
    return row


def insert(engine, row):
    with engine.begin() as conn:
        return conn.execute(INSERT, row).lastrowid


def test_sessions_before_login_and_for_both_kinds_of_users(db, customer_id, employee_id):
    insert(db, session_row(data='{"csrf": "abc"}'))
    insert(db, session_row(customer_id=customer_id))
    insert(db, session_row(employee_id=employee_id))


def test_token_hash_is_unique(db):
    same = token_hash()
    insert(db, session_row(token_hash=same))
    with pytest.raises(DBAPIError, match="uq_session_token_hash"):
        insert(db, session_row(token_hash=same))


@pytest.mark.parametrize("bad_hash", [b"\x01" * 31, b"", b"\x01" * 16])
def test_short_hash_is_rejected_not_padded(db, bad_hash):
    with pytest.raises(DBAPIError, match="ck_session_token_hash"):
        insert(db, session_row(token_hash=bad_hash))


def test_hash_longer_than_32_bytes_is_rejected(db):
    with pytest.raises(DBAPIError, match="too long"):
        insert(db, session_row(token_hash=b"\x01" * 33))


def test_session_cannot_belong_to_customer_and_staff(db, customer_id, employee_id):
    with pytest.raises(DBAPIError, match="ck_session_owner"):
        insert(db, session_row(customer_id=customer_id, employee_id=employee_id))


@pytest.mark.parametrize("data", ["[]", '"text"', "42"])
def test_data_must_be_a_json_object(db, data):
    with pytest.raises(DBAPIError, match="ck_session_data"):
        insert(db, session_row(data=data))


def test_last_seen_cannot_be_before_created(db):
    session_id = insert(db, session_row())
    with pytest.raises(DBAPIError, match="ck_session_times"):
        with db.begin() as conn:
            conn.execute(text(
                "UPDATE session SET last_seen_at = created_at - INTERVAL 1 MINUTE WHERE id = :id"
            ), {"id": session_id})


def test_app_can_touch_and_delete_sessions(db, customer_id):
    session_id = insert(db, session_row(customer_id=customer_id))
    with db.begin() as conn:
        conn.execute(text(
            "UPDATE session SET data = '{\"step\": \"totp\"}', last_seen_at = NOW() WHERE id = :id"
        ), {"id": session_id})
        conn.execute(text("DELETE FROM session WHERE customer_id = :id"), {"id": customer_id})
        left = conn.execute(text("SELECT COUNT(*) FROM session")).scalar()
    assert left == 0


@pytest.mark.parametrize("column", ["customer_id", "employee_id", "token_hash", "created_at"])
def test_session_cannot_change_owner_or_token(db, customer_id, employee_id, column):
    session_id = insert(db, session_row())
    values = {"customer_id": customer_id, "employee_id": employee_id,
              "token_hash": token_hash(), "created_at": "2026-01-01 00:00:00"}
    with pytest.raises(DBAPIError, match="UPDATE command denied"):
        with db.begin() as conn:
            conn.execute(text(f"UPDATE session SET {column} = :value WHERE id = :id"),
                         {"value": values[column], "id": session_id})
