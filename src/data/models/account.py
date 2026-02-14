from __future__ import annotations

import enum
import math
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import JSON, Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .base import Base, TimestampMixin, generate_id

if TYPE_CHECKING:
    from .order import Order
    from .position import Position
    from .strategy_assignment import StrategyAssignment


class AccountStatus(str, enum.Enum):
    """Account status enum."""

    ACTIVE = "active"
    PAUSED = "paused"
    SUSPENDED = "suspended"


class RiskProfile(str, enum.Enum):
    """Risk profile enum."""

    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class Account(Base, TimestampMixin):
    """Trading account model."""

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: generate_id("acc"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    broker: Mapped[str] = mapped_column(String(50), nullable=False, default="binance")
    profile: Mapped[RiskProfile] = mapped_column(Enum(RiskProfile), nullable=False, default=RiskProfile.BALANCED)
    status: Mapped[AccountStatus] = mapped_column(Enum(AccountStatus), nullable=False, default=AccountStatus.ACTIVE)
    balance_usdt: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    equity_usdt: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    regime: Mapped[str] = mapped_column(String(20), default="unknown")  # Manual regime tagging
    
    # CRITICAL FIX: Changed default=dict to default=lambda: {} to prevent mutable default bug
    # Explicit JSON type required for SQLAlchemy 2.0 with Mapped[] syntax
    risk_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=lambda: cast(dict[str, Any], {}))

    # Relationships
    strategies: Mapped[list["StrategyAssignment"]] = relationship("StrategyAssignment", back_populates="account")
    positions: Mapped[list["Position"]] = relationship("Position", back_populates="account")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="account")

    @validates("balance_usdt", "equity_usdt")
    def validate_financial_values(self, key: str, value: float) -> float:
        """Validate financial values are non-negative and not NaN/Infinity.

        Args:
            key: Field name being validated
            value: Value to validate

        Returns:
            Validated value

        Raises:
            ValueError: If value is invalid
        """
        if value is None:
            raise ValueError(f"{key} cannot be None")
        if math.isnan(value):
            raise ValueError(f"{key} cannot be NaN")
        if math.isinf(value):
            raise ValueError(f"{key} cannot be Infinity")
        if value < 0:
            raise ValueError(f"{key} must be non-negative, got {value}")
        return value

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, name={self.name}, status={self.status})>"
