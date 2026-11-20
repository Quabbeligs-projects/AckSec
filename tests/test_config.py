import pytest

from acksec import create_app


@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch):
    monkeypatch.setattr("acksec.load_dotenv", lambda: None)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("ACKSEC_ENV", raising=False)
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://nobody:nothing@localhost:3306/none")


def test_refuses_missing_secret_key():
    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        create_app("production")


def test_refuses_missing_database_url(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    monkeypatch.delenv("DATABASE_URL")
    with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
        create_app("production")


def test_refuses_example_secret_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "change-me")
    with pytest.raises(RuntimeError, match="example value"):
        create_app("production")


def test_refuses_short_secret_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * 31)
    with pytest.raises(RuntimeError, match="at least 32"):
        create_app("production")


def test_accepts_long_secret_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * 32)
    app = create_app("production")
    assert app.config["SECRET_KEY"] == "a" * 32


def test_production_is_the_default(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    app = create_app()
    assert not app.debug
    assert not app.testing


def test_unknown_environment_is_refused(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    with pytest.raises(RuntimeError, match="unknown ACKSEC_ENV"):
        create_app("prod")


def test_testing_needs_no_secret_key():
    app = create_app("testing")
    assert app.testing
    assert len(app.config["SECRET_KEY"]) >= 32