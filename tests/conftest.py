import os

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from acksec import create_app

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

@pytest.fixture
def app():
    return create_app("testing")


@pytest.fixture
def client(app):
    return app.test_client()


def _test_db_url(name):
    url = os.environ.get(name, "").strip()
    if not url:
        pytest.skip(f"{name} not set, db tests only run in docker: docker compose run --rm test")
    if not make_url(url).database.endswith("_test"):
        pytest.exit(f"{name} must point to a database ending in _test, refusing to run", returncode=2)
    return url


@pytest.fixture(scope="session")
def migrated_db():
    migrate_url = _test_db_url("TEST_MIGRATION_DATABASE_URL")

    alembic_cfg = AlembicConfig(os.path.join(PROJECT_ROOT, "alembic.ini"))
    old_url = os.environ.get("MIGRATION_DATABASE_URL")
    os.environ["MIGRATION_DATABASE_URL"] = migrate_url
    try:
        command.downgrade(alembic_cfg, "base")
        command.upgrade(alembic_cfg, "head")
    finally:
        if old_url is None:
            os.environ.pop("MIGRATION_DATABASE_URL", None)
        else:
            os.environ["MIGRATION_DATABASE_URL"] = old_url


@pytest.fixture(scope="session")
def app_engine(migrated_db):
    engine = create_engine(_test_db_url("TEST_DATABASE_URL"))
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def migrate_engine(migrated_db):
    engine = create_engine(_test_db_url("TEST_MIGRATION_DATABASE_URL"))
    yield engine
    engine.dispose()

TABLES_TO_CLEAN = ["customer"]


@pytest.fixture
def db(app_engine, migrate_engine):
    yield app_engine
    with migrate_engine.begin() as conn:
        for table in TABLES_TO_CLEAN:
            conn.execute(text(f"DELETE FROM {table}"))
