"""StrategyAssignment model linking strategies to accounts."""
from __future__ import annotations

import enum
from typing import TYPE_CHECKING, cast

from sqlalchemy import JSON, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, generate_id

if TYPE_CHECKING:
    from .account import Account
    from .strategy import Strategy


class AssignmentStatus(str, enum.Enum):
    """Assignment status enum."""

    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


class StrategyAssignment(Base, TimestampMixin):
    """Strategy assignment to account."""

    __tablename__ = "strategy_assignments"  # Explicit table name with snake_case

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: generate_id("asgn"))

    # References
    account_id: Mapped[str] = mapped_column(String, ForeignKey("accounts.id"), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String, ForeignKey("strategies.id"), nullable=False)

    # Configuration
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[AssignmentStatus] = mapped_column(Enum(AssignmentStatus), nullable=False, default=AssignmentStatus.ACTIVE)
    
    # CRITICAL FIX: Changed default=list to lambda to prevent mutable default bug
    # Explicit JSON type required for SQLAlchemy 2.0 with Mapped[] syntax
    regime_filter: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=lambda: cast(list[str], []))

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="strategies")
    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="assignments")

    def __repr__(self) -> str:
        return f"<StrategyAssignment(id={self.id}, account_id={self.account_id}, strategy_id={self.strategy_id}, status={self.status})>"
