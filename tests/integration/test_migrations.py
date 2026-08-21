"""The migration chain must build exactly the schema the ORM models declare.

Nothing compared these two for six months, and they had diverged in four ways:
`paper_trading_sessions` and `symbols` existed only in the models, along with
`ix_symbols_symbol` and `signals.symbol`. The chain also aborted at revision two
of six on SQLite, so it could not even be measured -- two revisions applied and
four never ran, silently, because no runtime invokes Alembic and nobody had run
it by hand.

`paper_trading_sessions` is the one that mattered. Despite the name it is where
`scripts/run_live_trading.py` persists live position state. A database built
from the chain would have had no table for live trading to write to.

This is a class of failure, not an instance: a migration chain and a set of
models are two descriptions of one schema, and nothing forces them to agree
unless something checks. That is what this file is.

Decision: DEC-2026-08-21-005 - Migration chain asserted against the ORM models
Decision: DEC-2026-08-21-004 - The constraint that could not be applied on SQLite
"""
from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from src.data.models import Base

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_DIR = REPO_ROOT / "alembic"

#: Bookkeeping table Alembic maintains. Not part of the ORM metadata and not a
#: difference.
ALEMBIC_VERSION_TABLE = "alembic_version"


def _config(database_url: str) -> Config:
    """Build an Alembic config pointed at a scratch database.

    Deliberately constructed without ``alembic.ini``. ``env.py`` calls
    ``fileConfig(config.config_file_name)`` when one is present, which
    reconfigures Python logging process-wide and disables existing loggers --
    including structlog, for every test that runs after this one. Leaving
    ``config_file_name`` as None skips that branch.

    Args:
        database_url: SQLAlchemy URL for a scratch database.

    Returns:
        A Config with the script location and URL set.
    """
    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@pytest.fixture
def scratch_db(tmp_path: Path) -> str:
    """A URL for an empty database that no other test can see."""
    return f"sqlite:///{(tmp_path / 'migrations.db').as_posix()}"


@pytest.fixture
def migrated_db(scratch_db: str) -> str:
    """A scratch database with the whole chain applied."""
    command.upgrade(_config(scratch_db), "head")
    return scratch_db


class TestTheChainIsWellFormed:
    """Properties of the revision graph itself, independent of any database."""

    def test_exactly_one_head(self) -> None:
        """Two heads means `upgrade head` is ambiguous and a merge is missing."""
        heads = ScriptDirectory.from_config(_config("sqlite://")).get_heads()
        assert len(heads) == 1, f"expected a single head, found {heads}"

    def test_the_chain_is_not_empty(self) -> None:
        """Guards the guard.

        Every assertion below is about the result of applying revisions. If the
        directory were empty, or the script location wrong, they would all pass
        against a schema built from nothing -- which is exactly the shape of
        failure this file exists to catch, so it must not be able to happen
        here.
        """
        revisions = list(ScriptDirectory.from_config(_config("sqlite://")).walk_revisions())
        assert len(revisions) >= 6, f"expected at least 6 revisions, found {len(revisions)}"


class TestTheChainApplies:
    """It ran two of six revisions on SQLite until 2026-08-21 and said nothing."""

    def test_upgrade_head_succeeds_on_an_empty_database(self, scratch_db: str) -> None:
        command.upgrade(_config(scratch_db), "head")

        tables = inspect(create_engine(scratch_db)).get_table_names()
        assert ALEMBIC_VERSION_TABLE in tables
        assert len(tables) > 1, "the chain stamped a version and created nothing"

    def test_downgrade_to_base_then_upgrade_again(self, migrated_db: str) -> None:
        """A chain that cannot be reversed cannot be rolled back.

        This is the only test of the `downgrade()` functions. They were written
        alongside every `upgrade()` and, like the chain itself, had never run.
        """
        config = _config(migrated_db)
        command.downgrade(config, "base")

        remaining = set(inspect(create_engine(migrated_db)).get_table_names())
        assert remaining <= {ALEMBIC_VERSION_TABLE}, (
            f"downgrade to base left tables behind: {sorted(remaining)}"
        )

        command.upgrade(config, "head")


class TestTheChainMatchesTheModels:
    """The check that did not exist."""

    def test_every_model_table_is_created_by_the_chain(self, migrated_db: str) -> None:
        migrated = set(inspect(create_engine(migrated_db)).get_table_names())
        migrated.discard(ALEMBIC_VERSION_TABLE)
        declared = set(Base.metadata.tables)

        assert declared - migrated == set(), (
            f"tables declared on the models but not created by any migration: "
            f"{sorted(declared - migrated)}"
        )

    def test_the_chain_creates_no_table_the_models_do_not_declare(
        self, migrated_db: str
    ) -> None:
        migrated = set(inspect(create_engine(migrated_db)).get_table_names())
        migrated.discard(ALEMBIC_VERSION_TABLE)
        declared = set(Base.metadata.tables)

        assert migrated - declared == set(), (
            f"tables created by a migration but absent from the models: "
            f"{sorted(migrated - declared)}"
        )

    def test_no_schema_difference_of_any_kind(self, migrated_db: str) -> None:
        """The whole-schema comparison, and the one that catches the rest.

        `compare_metadata` is what `alembic revision --autogenerate` uses to
        decide what a new migration should contain. An empty result means
        autogenerate would produce an empty migration, which is precisely the
        statement "the chain and the models agree" -- columns, types,
        nullability, indexes and constraints, not only table names.
        """
        with create_engine(migrated_db).connect() as connection:
            differences = compare_metadata(
                MigrationContext.configure(connection), Base.metadata
            )

        assert differences == [], (
            "the migration chain and the ORM models describe different schemas. "
            "Each entry is what `alembic revision --autogenerate` would emit:\n  "
            + "\n  ".join(str(d) for d in differences)
        )
