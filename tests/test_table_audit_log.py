import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

INSERT = text("""
    INSERT INTO audit_log
        (actor_type, actor_customer_id, actor_employee_id, action,
         subject_customer_id, subject_account_id, reason, ip_address, details)
    VALUES
        (:actor_type, :actor_customer_id, :actor_employee_id, :action,
         :subject_customer_id, :subject_account_id, :reason, :ip_address, :details)
""")


def entry(**changes):
    row = {
        "actor_type": "anonymous",
        "actor_customer_id": None,
        "actor_employee_id": None,
        "action": "login_failed",
        "subject_customer_id": None,
        "subject_account_id": None,
        "reason": None,
        "ip_address": "203.0.113.7",
        "details": None,
    }
    row.update(changes)
    return row


def insert(engine, row):
    with engine.begin() as conn:
        return conn.execute(INSERT, row).lastrowid


def test_entries_for_every_kind_of_actor(db, customer_id, employee_id):
    insert(db, entry())
    insert(db, entry(actor_type="system", action="standing_orders_run", ip_address=None))
    insert(db, entry(actor_type="customer", actor_customer_id=customer_id, action="login_ok",
                     subject_customer_id=customer_id))
    insert(db, entry(actor_type="employee", actor_employee_id=employee_id, action="account_locked",
                     subject_customer_id=customer_id, reason="Verdacht auf Betrug, Kunde hat angerufen"))


def test_details_are_stored_as_json(db, employee_id, customer_id):
    entry_id = insert(db, entry(
        actor_type="employee", actor_employee_id=employee_id, action="personal_data_changed",
        subject_customer_id=customer_id, reason="Heirat",
        details='{"last_name": {"old": "Meier", "new": "Keller"}}',
    ))
    with db.connect() as conn:
        new_name = conn.execute(text(
            "SELECT details->>'$.last_name.new' FROM audit_log WHERE id = :id"
        ), {"id": entry_id}).scalar()
    assert new_name == "Keller"


def test_created_at_keeps_microseconds(db):
    with db.connect() as conn:
        precision = conn.execute(text("""
            SELECT DATETIME_PRECISION FROM information_schema.columns
            WHERE table_schema = DATABASE() AND table_name = 'audit_log' AND column_name = 'created_at'
        """)).scalar()
    assert precision == 6


@pytest.mark.parametrize("actor_type, with_customer, with_employee", [
    ("customer", False, False),
    ("employee", False, False),
    ("anonymous", True, False),
    ("system", False, True),
    ("customer", True, True),
    ("employee", True, False),
])
def test_actor_columns_must_match_the_actor_type(db, customer_id, employee_id,
                                                 actor_type, with_customer, with_employee):
    row = entry(
        actor_type=actor_type,
        actor_customer_id=customer_id if with_customer else None,
        actor_employee_id=employee_id if with_employee else None,
    )
    with pytest.raises(DBAPIError, match="ck_audit_log_actor"):
        insert(db, row)


@pytest.mark.parametrize("changes, constraint", [
    ({"action": "Login Failed"}, "ck_audit_log_action"),
    ({"action": "login-failed"}, "ck_audit_log_action"),
    ({"action": "_login"}, "ck_audit_log_action"),
    ({"reason": "   "}, "ck_audit_log_reason"),
    ({"details": "[1, 2, 3]"}, "ck_audit_log_details"),
    ({"details": '"just a string"'}, "ck_audit_log_details"),
])
def test_check_constraints_reject_bad_rows(db, changes, constraint):
    with pytest.raises(DBAPIError, match=constraint):
        insert(db, entry(**changes))


def test_unknown_customer_is_rejected(db):
    with pytest.raises(DBAPIError, match="fk_audit_log_subject_customer"):
        insert(db, entry(subject_customer_id=999999))


def test_audited_customer_cannot_be_deleted(db, migrate_engine, customer_id):
    insert(db, entry(subject_customer_id=customer_id))
    with pytest.raises(DBAPIError, match="fk_audit_log_subject_customer"):
        with migrate_engine.begin() as conn:
            conn.execute(text("DELETE FROM customer WHERE id = :id"), {"id": customer_id})


@pytest.mark.parametrize("statement", [
    "UPDATE audit_log SET reason = 'nothing happened'",
    "UPDATE audit_log SET action = 'login_ok'",
    "DELETE FROM audit_log",
])
def test_app_cannot_cover_its_tracks(db, statement):
    insert(db, entry())
    with pytest.raises(DBAPIError, match="command denied"):
        with db.begin() as conn:
            conn.execute(text(statement))
