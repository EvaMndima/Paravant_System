from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add src to path for importing models
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all models so Alembic can detect them
from src.data.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata to our models' Base metadata
# This enables Alembic autogenerate to detect model changes
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    x_args = context.get_x_argument(as_dictionary=True)
    url = (
        x_args.get("sqlalchemy.url")
        or os.getenv("DATABASE_URL")
        or config.get_main_option("sqlalchemy.url")
    )
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    section = config.get_section(config.config_ini_section, {}) or {}

    # DATABASE_URL wins over alembic.ini.
    #
    # alembic.ini hardcodes `sqlalchemy.url = sqlite:///data/trading.db`, and
    # nothing here read the environment. Running `alembic upgrade head` on a
    # host configured for PostgreSQL would therefore have migrated a local
    # SQLite file and reported success, leaving the real database untouched --
    # a silent no-op with a green exit code. Production is PostgreSQL on Neon.
    #
    # An explicit -x override still wins over both, for the case where an
    # operator wants to point a one-off migration somewhere specific without
    # exporting anything:
    #
    #     alembic -x sqlalchemy.url=postgresql://... upgrade head
    #
    # Decision: DEC-2026-08-21-005
    x_args = context.get_x_argument(as_dictionary=True)
    url = x_args.get("sqlalchemy.url") or os.getenv("DATABASE_URL")
    if url:
        section["sqlalchemy.url"] = url

    connectable = engine_from_config(
        section,
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
