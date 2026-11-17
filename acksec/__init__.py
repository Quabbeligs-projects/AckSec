import os

from dotenv import load_dotenv
from flask import Flask

from acksec.config import load_config


def create_app(env_name=None):
    # app factory instead of a global app object, so tests can build
    # their own instance with a different config later (C031)
    app = Flask(__name__)

    # .env is only for local development, real environment variables win
    load_dotenv()
    # no ACKSEC_ENV means production, a forgotten setting should never turn on debug mode
    env_name = env_name or os.environ.get("ACKSEC_ENV", "production")
    app.config.from_object(load_config(env_name))

    from acksec.health import bp as health_bp
    app.register_blueprint(health_bp)

    return app
