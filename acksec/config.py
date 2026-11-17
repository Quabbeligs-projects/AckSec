import os
import secrets

# placeholder used in .env.example, must never end up in a running app
EXAMPLE_SECRET = "change-me"
MIN_SECRET_LENGTH = 32


def _secret_key_from_env():
    key = os.environ.get("SECRET_KEY", "").strip()
    if not key:
        raise RuntimeError("SECRET_KEY is not set, see .env.example")
    if key.startswith(EXAMPLE_SECRET):
        raise RuntimeError("SECRET_KEY is still the example value, generate a real one")
    # flask signs sessions and csrf tokens with this, a short key could be brute forced
    if len(key) < MIN_SECRET_LENGTH:
        raise RuntimeError(f"SECRET_KEY must be at least {MIN_SECRET_LENGTH} characters")
    return key


class Config:
    DEBUG = False
    TESTING = False

    def __init__(self):
        self.SECRET_KEY = _secret_key_from_env()


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True

    def __init__(self):
        # tests shouldn't depend on someone's local .env
        self.SECRET_KEY = secrets.token_hex(32)


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
