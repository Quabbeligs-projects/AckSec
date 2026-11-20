import hashlib

import pytest
from sqlalchemy import text

from acksec import create_app
from acksec.db import transaction

INSERT_SESSION = text("INSERT INTO session (token_hash, data) VALUES (:hash, '{}')")
COUNT_SESSIONS = text("SELECT COUNT(*) FROM session")


def test_transaction_commits(app, db):
    with app.app_context():
        with transaction() as conn:
            conn.execute(INSERT_SESSION, {"hash": hashlib.sha256(b"one").digest()})
        with transaction() as conn:
            assert conn.execute(COUNT_SESSIONS).scalar() == 1


def test_transaction_rolls_back_everything_on_error(app, db):
    with app.app_context():
        with pytest.raises(ValueError):
            with transaction() as conn:
                conn.execute(INSERT_SESSION, {"hash": hashlib.sha256(b"one").digest()})
                conn.execute(INSERT_SESSION, {"hash": hashlib.sha256(b"two").digest()})
                raise ValueError("something went wrong halfway")
        with transaction() as conn:
            assert conn.execute(COUNT_SESSIONS).scalar() == 0


def test_connection_uses_utc_and_utf8mb4(app, db):
    with app.app_context():
        with transaction() as conn:
            time_zone, charset = conn.execute(
                text("SELECT @@session.time_zone, @@session.character_set_client")
            ).one()
    assert time_zone == "+00:00"
    assert charset == "utf8mb4"


def test_app_connects_as_the_app_user(app, db):
    # never as root or the migration user, see C026
    with app.app_context():
        with transaction() as conn:
            user = conn.execute(text("SELECT CURRENT_USER()")).scalar()
    assert user.startswith("acksec_app@")


def test_without_database_transaction_says_so(monkeypatch):
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    app = create_app("testing")
    with app.app_context():
        with pytest.raises(RuntimeError, match="no database configured"):
            transaction()