import os
import secrets

EXAMPLE_SECRET = "change-me"
MIN_SECRET_LENGTH = 32


def _secret_key_from_env():
    key = os.environ.get("SECRET_KEY", "").strip()
    if not key:
        raise RuntimeError("SECRET_KEY is not set, see .env.example")
    if key.startswith(EXAMPLE_SECRET):
        raise RuntimeError("SECRET_KEY is still the example value, generate a real one")
    if len(key) < MIN_SECRET_LENGTH:
        raise RuntimeError(f"SECRET_KEY must be at least {MIN_SECRET_LENGTH} characters")
    return key


def _database_url_from_env():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not set, docker-compose.yml builds it from MYSQL_APP_PASSWORD")
    return url


class Config:
    DEBUG = False
    TESTING = False
    LOG_LEVEL = "INFO"

    def __init__(self):
        self.SECRET_KEY = _secret_key_from_env()
        self.DATABASE_URL = _database_url_from_env()


class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = "DEBUG"


class TestingConfig(Config):
    TESTING = True

    def __init__(self):
        self.SECRET_KEY = secrets.token_hex(32)
        self.DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "").strip() or None


class ProductionConfig(Config):
    pass


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def load_config(env_name):
    try:
        config_class = CONFIGS[env_name]
    except KeyError:
        raise RuntimeError(
            f"unknown ACKSEC_ENV '{env_name}', use one of: {', '.join(CONFIGS)}"
        ) from None
    return config_class()
