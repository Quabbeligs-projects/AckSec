import logging
import logging.config
import secrets
import time

from flask import g, has_request_context

# no 0/O or 1/I, so the id is easy to read, because with em it lowk pisses me off
REQUEST_ID_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"

def new_request_id():
    return "".join(secrets.choice(REQUEST_ID_ALPHABET) for _ in range(8))

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = g.get("request_id", "-") if has_request_context() else "-"
        return True

class UTCFormatter(logging.Formatter):
    converter = time.gmtime

def configure_logging(level):
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {"()": RequestIdFilter},
        },
        "formatters": {
            "default": {
                "()": UTCFormatter,
                "format": "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%SZ",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "filters": ["request_id"],
            },
        },
        "root": {"level": level, "handlers": ["console"]},
        "loggers": {
            "sqlalchemy": {"level": "WARNING"},
        },
    })

def register_request_id(app):
    @app.before_request
    def assign_request_id():
        g.request_id = new_request_id()
