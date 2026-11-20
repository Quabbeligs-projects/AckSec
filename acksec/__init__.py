import os

from dotenv import load_dotenv
from flask import Flask

from acksec.config import load_config

def create_app(env_name=None):
    # for tests
    app = Flask(__name__)

    # .env is only for local development, real environment variables win
    load_dotenv()
    env_name = env_name or os.environ.get("ACKSEC_ENV", "production")
    app.config.from_object(load_config(env_name))

    from acksec.logging_setup import configure_logging, register_request_id
    configure_logging(app.config["LOG_LEVEL"])
    register_request_id(app)

    from acksec.errors import register_error_handlers
    register_error_handlers(app)

    from acksec.health import bp as health_bp
    app.register_blueprint(health_bp)

    from acksec.public import bp as public_bp
    app.register_blueprint(public_bp)

    return app
