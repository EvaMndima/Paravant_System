"""Position model for tracking open and closed positions."""
from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime, timezone
import enum

from sqlalchemy import String, Float, ForeignKey, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
import math

from .base import Base, TimestampMixin, generate_id

if TYPE_CHECKING:
    from .account import Account
    from .strategy import Strategy


class PositionSide(str, enum.Enum):
    """Position side enum."""

    LONG = "long"
    SHORT = "short"


class PositionStatus(str, enum.Enum):
    """Position status enum."""

    OPEN = "open"
    CLOSED = "closed"


class Position(Base, TimestampMixin):
    """Position model with PnL tracking."""

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: generate_id("pos"))

    # References
    account_id: Mapped[str] = mapped_column(String, ForeignKey("accounts.id"), nullable=False)
    strategy_id: Mapped[str | None] = mapped_column(String, ForeignKey("strategies.id"))

    # Position details
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[PositionSide] = mapped_column(Enum(PositionSide), nullable=False)
    size: Mapped[float] = mapped_column(Float, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[float] = mapped_column(Float, nullable=False)

    # PnL
    pnl_usdt: Mapped[float] = mapped_column(Float, default=0.0)
    pnl_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Status
    status: Mapped[PositionStatus] = mapped_column(Enum(PositionStatus), nullable=False, default=PositionStatus.OPEN)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)  # Auto-populate with timezone-aware UTC timestamp
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)
    exit_price: Mapped[float | None] = mapped_column(Float)

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="positions")
    strategy: Mapped["Strategy | None"] = relationship("Strategy", back_populates="positions")

    @validates("size", "entry_price", "current_price", "exit_price")
    def validate_numeric_values(self, key: str, value: float | None) -> float | None:
        """Validate numeric values are positive and not NaN/Infinity.

        Args:
            key: Field name being validated
            value: Value to validate

        Returns:
            Validated value

        Raises:
            ValueError: If value is invalid
        """
        if value is None:
            # Allow None for optional field (exit_price)
            if key == "exit_price":
                return value
            raise ValueError(f"{key} cannot be None")

        if math.isnan(value):
            raise ValueError(f"{key} cannot be NaN")
        if math.isinf(value):
            raise ValueError(f"{key} cannot be Infinity")
        if value <= 0:
            raise ValueError(f"{key} must be positive, got {value}")
        return value

    def __repr__(self) -> str:
        return f"<Position(id={self.id}, symbol={self.symbol}, side={self.side}, status={self.status})>"
