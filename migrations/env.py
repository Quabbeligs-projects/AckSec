import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def database_url():
    url = os.environ.get("MIGRATION_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("MIGRATION_DATABASE_URL is not set: docker compose run --rm migrate")
    return url


def run_migrations_online():
    engine = create_engine(database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("why would we use offline mode gng, pack it up, don't have shit to do with this project")

run_migrations_online()
