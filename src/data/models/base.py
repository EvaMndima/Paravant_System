"""Base model with common functionality."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column
import uuid


class Base(DeclarativeBase):
    """Base class for all models."""

    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower() + "s"

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


def _utc_now() -> datetime:
    """Get current UTC time with timezone awareness."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )


def generate_id(prefix: str = "") -> str:
    """
    Generate a unique ID with optional prefix.
    
    Args:
        prefix: Optional prefix for the ID (e.g., "acc", "ord")
        
    Returns:
        Unique ID in format: prefix_YYYYMMDDHHMMSS_uuid8 or YYYYMMDDHHMMSS_uuid8
        
    Example:
        >>> generate_id("acc")
        'acc_20260208012900_a1b2c3d4'
    """
    uid = str(uuid.uuid4())[:8]
    timestamp = _utc_now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{timestamp}_{uid}" if prefix else f"{timestamp}_{uid}"
