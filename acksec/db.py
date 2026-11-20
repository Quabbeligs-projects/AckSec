from flask import current_app
from sqlalchemy import create_engine

def init_db(app):
    url = app.config["DATABASE_URL"]
    if url is None:
        app.extensions["db_engine"] = None
        return

    app.extensions["db_engine"] = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={
            "charset": "utf8mb4",
            "init_command": "SET time_zone = '+00:00'",
        },
    )


def get_engine():
    engine = current_app.extensions.get("db_engine")
    if engine is None:
        raise RuntimeError("no database configured")
    return engine


def transaction():
    """Use as `with transaction() as conn:`. Commits at the end, rolls everything
    back if anything inside raises. Keep the block as short as the work allows."""
    return get_engine().begin()