"""Database engine and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
import os
from dotenv import load_dotenv

from .models.base import Base

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/trading.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database schema."""
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """Drop all database tables. WARNING: This will delete all data!"""
    Base.metadata.drop_all(bind=engine)


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
