import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

DENIED = (OperationalError, ProgrammingError)


def test_app_user_can_log_in(app_engine):
    with app_engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1


def test_app_user_cannot_create_tables(app_engine):
    with pytest.raises(DENIED) as error:
        with app_engine.connect() as conn:
            conn.execute(text("CREATE TABLE should_fail (id INT)"))
    assert "denied" in str(error.value).lower()


def test_app_user_cannot_read_migration_state(app_engine):
    with pytest.raises(DENIED) as error:
        with app_engine.connect() as conn:
            conn.execute(text("SELECT version_num FROM alembic_version"))
    assert "denied" in str(error.value).lower()
