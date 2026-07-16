"""Alembic environment configuration — supports SQLite and Postgres."""

import os
from logging.config import fileConfig

from backend.app.db.base import Base
from backend.app.models import *  # noqa: F401,F403 — register all models
from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override database URL from DATABASE_URL env var so Alembic uses the same
# database the app connects to (critical in Docker where alembic.ini's
# hardcoded path can differ from the runtime config).
db_url = os.environ.get("DATABASE_URL")
if db_url is not None:
    config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
