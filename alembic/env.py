import logging
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the project root to sys.path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from app.infrastructure.database.orm import Base
from app.infrastructure.database import models  # noqa: F401  # Registers all models
# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret alembic.ini logging only when the app has not configured logging yet.
# Programmatic ``alembic upgrade`` during bootstrap runs after ``setup_logging()``;
# ``fileConfig`` would reset root to WARNING and drop the app's file handler.
if config.config_file_name is not None and not logging.getLogger().handlers:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

def get_url():
    from app.config import get_settings
    settings = get_settings()
    if not settings.use_mysql:
        raise RuntimeError("Alembic migrations are configured for MySQL backend only.")
    return settings.database_uri

# ... (rest of the functions using get_url or target_metadata)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
