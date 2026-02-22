"""Strategy model with full lifecycle tracking."""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import JSON, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.attributes import flag_modified

from .base import Base, TimestampMixin, generate_id

if TYPE_CHECKING:
    from .order import Order
    from .position import Position
    from .signal import Signal
    from .strategy_assignment import StrategyAssignment


class StrategyStatus(str, enum.Enum):
    """Strategy lifecycle status enum."""

    DRAFT = "draft"
    BACKTEST = "backtest"
    SIMULATED_PAPER = "simulated_paper"
    LIVE_PAPER = "live_paper"
    PENDING_APPROVAL = "pending_approval"
    LIVE = "live"
    PAUSED = "paused"
    UNDERPERFORMING = "underperforming"
    OPTIMIZATION = "optimization"
    RETIRED = "retired"


class StrategyType(str, enum.Enum):
    """Strategy classification enum."""

    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    VOLATILITY_BREAKOUT = "volatility_breakout"
    TREND_CONTINUATION = "trend_continuation"
    TREND_BREAKOUT = "trend_breakout"
    INTRADAY_PULLBACK = "intraday_pullback"


class Strategy(Base, TimestampMixin):
    """Strategy model with comprehensive metadata."""

    __tablename__ = "strategies"  # Explicit table name for correct plural form

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: generate_id("str"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))

    # Classification
    type: Mapped[StrategyType] = mapped_column(Enum(StrategyType), nullable=False)
    template_id: Mapped[str] = mapped_column(String(100), nullable=False)
    template_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")

    # Configuration - CRITICAL FIX: Changed default=list/dict to lambda (prevents mutable default bug)
    # Explicit JSON type required for SQLAlchemy 2.0 with Mapped[] syntax
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: cast(dict[str, Any], {})  # Safe default prevents runtime error
    )
    symbols: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=lambda: cast(list[str], []))

    # Status
    status: Mapped[StrategyStatus] = mapped_column(Enum(StrategyStatus), nullable=False, default=StrategyStatus.DRAFT)
    status_reason: Mapped[str | None] = mapped_column(String(500))

    # Results (stored as JSON for flexibility)
    backtest_results: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    paper_results: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    live_results: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # Metadata - CRITICAL FIX: Changed default=list to lambda
    lifecycle: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=lambda: cast(list[dict[str, Any]], []))
    recommendations: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    insights: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # Relationships
    assignments: Mapped[list["StrategyAssignment"]] = relationship("StrategyAssignment", back_populates="strategy")
    positions: Mapped[list["Position"]] = relationship("Position", back_populates="strategy")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="strategy")
    signals: Mapped[list["Signal"]] = relationship("Signal", back_populates="strategy")

    def __repr__(self) -> str:
        return f"<Strategy(id={self.id}, name={self.name}, status={self.status})>"

    def add_lifecycle_event(self, from_status: str, to_status: str, reason: str) -> None:
        """
        Record a lifecycle status change.

        Args:
            from_status: Previous status
            to_status: New status
            reason: Reason for status change
        """
        if self.lifecycle is None:
            self.lifecycle = []

        self.lifecycle.append(
            {
                "from": from_status,
                "to": to_status,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),  # Timezone-aware timestamp
            }
        )
        # Signal SQLAlchemy that the JSON column was mutated in-place
        # Without this, in-place list mutations are not detected by the ORM
        flag_modified(self, "lifecycle")
