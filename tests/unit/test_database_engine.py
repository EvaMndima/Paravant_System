"""Engine configuration: pooled connections must survive a server-side close.

Production runs PostgreSQL on Neon. A managed Postgres drops idle connections on
its own schedule and the client discovers this only on use, as
``psycopg2.OperationalError: SSL connection has been closed unexpectedly``. That
happened on 2026-08-15 and took down regime persistence.

These tests assert the configuration that prevents it, and assert that SQLite --
which has no server and therefore no such failure mode -- does not receive it.

Decision: DEC-2026-08-21-002 - Connection liveness for managed Postgres
"""
from __future__ import annotations

import pytest
from sqlalchemy.exc import ArgumentError

from src.data.database import POOL_RECYCLE_SECONDS, engine_options

#: URLs that reach a network server over a pooled connection.
SERVER_URLS = [
    "postgresql://u:p@ep-example.eu-central-1.aws.neon.tech/paravant?sslmode=require",
    "postgresql+psycopg2://u:p@localhost:5432/paravant",
    "mysql+pymysql://u:p@localhost/paravant",
]

SQLITE_URLS = [
    "sqlite:///data/trading.db",
    "sqlite:///:memory:",
    "sqlite+aiosqlite:///data/trading.db",
]


class TestServerBackendsGetLivenessChecking:
    """The regression guard. Without pool_pre_ping these all fail."""

    @pytest.mark.parametrize("url", SERVER_URLS)
    def test_pre_ping_is_enabled(self, url: str) -> None:
        assert engine_options(url)["pool_pre_ping"] is True, (
            "A pooled connection to a server that closed it must be detected "
            "before the connection is handed to a caller. Without this the "
            "failure surfaces as OperationalError inside application code."
        )

    @pytest.mark.parametrize("url", SERVER_URLS)
    def test_connections_are_recycled_by_age(self, url: str) -> None:
        recycle = engine_options(url)["pool_recycle"]
        assert recycle == POOL_RECYCLE_SECONDS
        assert 0 < recycle <= 300, (
            "Recycle must sit under the idle window after which a managed "
            "Postgres drops a connection, or it protects nothing."
        )

    @pytest.mark.parametrize("url", SERVER_URLS)
    def test_sqlite_connect_args_are_not_applied(self, url: str) -> None:
        """``check_same_thread`` is a SQLite driver argument.

        Passing it to psycopg2 raises ``TypeError: 'check_same_thread' is an
        invalid keyword argument``. The previous substring test could do this:
        any Postgres URL whose host, database or password contained "sqlite"
        selected the SQLite branch.
        """
        assert "connect_args" not in engine_options(url)


class TestSQLiteIsUnchanged:
    """SQLite has no server to drop the connection, so it gets neither setting."""

    @pytest.mark.parametrize("url", SQLITE_URLS)
    def test_check_same_thread_disabled(self, url: str) -> None:
        assert engine_options(url)["connect_args"] == {"check_same_thread": False}

    @pytest.mark.parametrize("url", SQLITE_URLS)
    def test_no_pool_settings(self, url: str) -> None:
        options = engine_options(url)
        assert "pool_pre_ping" not in options
        assert "pool_recycle" not in options


class TestBackendDetection:
    """The substring test this replaced could not fail, only misclassify."""

    def test_postgres_url_containing_the_word_sqlite_is_not_sqlite(self) -> None:
        """The concrete case the old ``"sqlite" in url`` check got wrong.

        A database named ``sqlite_migration`` is unusual but legal, and there is
        nothing to stop a generated password from containing the substring. The
        old check would have applied ``check_same_thread`` to psycopg2 and the
        process would have failed to start with an unhelpful driver error.
        """
        url = "postgresql://u:p@db.example.com/sqlite_migration"
        options = engine_options(url)

        assert options["pool_pre_ping"] is True
        assert "connect_args" not in options

    def test_malformed_url_raises_rather_than_guessing(self) -> None:
        """Failing loudly beats silently choosing a branch.

        ``create_engine`` would reject the same input one line later, so this
        moves the error earlier rather than introducing a new one.
        """
        with pytest.raises(ArgumentError):
            engine_options("not-a-url-at-all")


class TestTheLiveEngineActuallyUsesThis:
    """Guards the guard.

    ``engine_options`` could be perfectly correct and not wired into the engine
    the application uses. That is the failure mode this repository keeps finding
    in other subsystems -- a tested component nothing calls -- so it is asserted
    here rather than assumed.
    """

    def test_module_engine_was_built_from_engine_options(self) -> None:
        from src.data.database import DATABASE_URL, engine

        expected = engine_options(DATABASE_URL)

        if "pool_pre_ping" in expected:
            assert engine.pool._pre_ping is True
        else:
            # SQLite: the engine exists and is bound to the configured URL.
            assert engine.url.get_backend_name() == "sqlite"
