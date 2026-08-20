"""Database engine and session management.

Decision: DEC-2026-08-21-002 - Connection liveness for managed Postgres
"""
import os
from contextlib import contextmanager
from typing import Any, Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from .models.base import Base

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///data/trading.db"

#: Maximum age of a pooled connection, in seconds, before it is discarded and
#: reopened. Five minutes sits under the idle window after which a managed
#: Postgres provider will drop or suspend a connection. This is the cheap
#: prophylactic; ``pool_pre_ping`` below is the actual guarantee.
POOL_RECYCLE_SECONDS: int = 300


def engine_options(url: str) -> dict[str, Any]:
    """Return ``create_engine`` keyword arguments appropriate to the backend.

    Extracted from the ``create_engine`` call so the choice can be asserted
    without importing this module under a particular environment. The engine
    itself is built at import time from ``DATABASE_URL``, which makes it
    awkward to test directly.

    **Why pooled connections need this.** Production runs PostgreSQL on Neon.
    A managed Postgres closes idle connections on its own schedule, and the
    client finds out only when it tries to use one -- SQLAlchemy hands out a
    pooled connection the server has already dropped, and the query fails with
    ``psycopg2.OperationalError: SSL connection has been closed unexpectedly``.
    That is not hypothetical: it happened on 2026-08-15 and took down regime
    persistence. ``pool_pre_ping`` makes SQLAlchemy issue a trivial liveness
    check before handing a connection to a caller, and transparently reconnect
    when it fails, which converts that crash into a reconnect nobody notices.

    The two settings do different jobs and both are wanted. ``pool_recycle``
    proactively retires connections by age and prevents most of the problem;
    ``pool_pre_ping`` catches whatever it misses, including a server-side close
    that arrives well inside the recycle window. Pre-ping alone would be
    sufficient for correctness and costs a round trip per checkout; recycle
    alone would be cheaper and would still leave a window.

    SQLite gets neither. It has no server to drop the connection, and its
    pooling is a different mechanism -- a pre-ping there is overhead with no
    failure mode to protect against.

    Args:
        url: A SQLAlchemy database URL.

    Returns:
        Keyword arguments for ``create_engine``, excluding the URL itself.

    Raises:
        sqlalchemy.exc.ArgumentError: If the URL cannot be parsed. This
            replaces a substring test (``"sqlite" in url``) that could not
            fail, but could silently misclassify -- a Postgres host or password
            containing "sqlite" selected the SQLite branch and applied
            ``check_same_thread`` to a driver that does not accept it. Failing
            loudly on a malformed URL is the better of the two behaviours, and
            ``create_engine`` would raise on the same input a line later
            regardless.
    """
    backend = make_url(url).get_backend_name()

    if backend == "sqlite":
        # Required because the API serves sync endpoints from a threadpool and
        # the trading loops hold sessions across await points.
        return {"connect_args": {"check_same_thread": False}}

    return {
        "pool_pre_ping": True,
        "pool_recycle": POOL_RECYCLE_SECONDS,
    }


# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    **engine_options(DATABASE_URL),
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database schema."""
    Base.metadata.create_all(bind=engine)



def drop_db() -> None:
    """Drop all database tables. WARNING: This will delete all data!"""
    Base.metadata.drop_all(bind=engine)


def reset_db() -> None:
    """Reset the database (drop and recreate tables)."""
    drop_db()
    init_db()



@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Get database session with automatic cleanup."""
    from src.utils.logging import get_logger
    
    db = SessionLocal()
    logger = get_logger(__name__)
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error("database_session_error", error=str(e), exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """Get a new database session. Caller is responsible for closing."""
    return SessionLocal()
