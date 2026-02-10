"""P&L tracking models for daily and intraday snapshots.

This module provides models for tracking profit and loss at different time granularities:
- PnLRecord: Daily P&L snapshots with comprehensive metrics
- EquitySnapshot: Intraday equity curve tracking
"""
from datetime import datetime, date, timezone
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import String, Float, ForeignKey, Date, DateTime, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, generate_id

if TYPE_CHECKING:
    from .account import Account
    from .strategy import Strategy


class PnLRecord(Base):
    """Daily P&L snapshot with comprehensive metrics.

    This model captures the daily profit and loss for an account or strategy,
    along with portfolio state and performance metrics.

    Attributes:
        id: Unique identifier (format: pnl_YYYYMMDDHHMMSS_uuid)
        account_id: Reference to the account
        strategy_id: Optional reference to specific strategy
        record_date: The date this P&L record represents
        realized_pnl: Profit/loss from closed positions (USDT)
        unrealized_pnl: Current profit/loss from open positions (USDT)
        total_pnl: Total P&L (realized + unrealized)
        portfolio_value: Total portfolio value (cash + positions)
        cash_balance: Available cash balance
        position_value: Total value of open positions
        daily_return_pct: Daily return percentage
        cumulative_return_pct: Cumulative return from inception
        drawdown_pct: Current drawdown from peak
        trades_count: Number of trades executed this day
        winning_trades: Number of profitable trades
        losing_trades: Number of losing trades
        extra_data: Additional data (JSON) for extensibility
        recorded_at: When this record was created
    """

    __tablename__ = 'pnl_records'

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: generate_id("pnl")
    )

    # Foreign key references
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey('accounts.id'),
        nullable=False,
        index=True
    )
    strategy_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey('strategies.id'),
        index=True  # Optional: for strategy-level P&L
    )

    # Time period
    record_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True  # Index for date-range queries
    )

    # P&L values (in USDT)
    realized_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    unrealized_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    total_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )

    # Portfolio snapshot (in USDT)
    portfolio_value: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    cash_balance: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    position_value: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    # Performance metrics
    daily_return_pct: Mapped[float | None] = mapped_column(Float)
    cumulative_return_pct: Mapped[float | None] = mapped_column(Float)
    drawdown_pct: Mapped[float | None] = mapped_column(Float)

    # Trade statistics for the day
    trades_count: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)

    # Additional data (avoid mutable default bug)
    # Note: Cannot use 'metadata' as field name - it's reserved by SQLAlchemy
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        default=lambda: cast(dict[str, Any] | None, None)
    )

    # When this record was created
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage.

        Returns:
            Win rate as a percentage (0-100), or 0 if no trades
        """
        total_trades = self.winning_trades + self.losing_trades
        if total_trades == 0:
            return 0.0
        return (self.winning_trades / total_trades) * 100

    @property
    def profit_factor(self) -> float | None:
        """Calculate profit factor (gross profit / gross loss).

        Returns:
            Profit factor, or None if cannot be calculated
        """
        # This would need gross profit and gross loss data
        # For MVP, return None - will be calculated in V1
        return None

    def __repr__(self) -> str:
        """String representation of the P&L record."""
        return (
            f"<PnLRecord(date={self.record_date}, "
            f"pnl={self.total_pnl:.2f}, "
            f"value={self.portfolio_value:.2f})>"
        )


class EquitySnapshot(Base):
    """Intraday equity snapshots for equity curve tracking.

    This model captures periodic snapshots of account equity throughout the day,
    enabling visualization of the equity curve and intraday performance analysis.

    Attributes:
        id: Unique identifier (format: eq_YYYYMMDDHHMMSS_uuid)
        account_id: Reference to the account
        timestamp: When this snapshot was taken
        equity: Total account equity (cash + positions value)
        cash: Cash balance
        positions_value: Total value of all open positions
    """

    __tablename__ = 'equity_snapshots'

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: generate_id("eq")
    )
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey('accounts.id'),
        nullable=False,
        index=True
    )

    # When this snapshot was taken
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,  # Index for time-series queries
        default=lambda: datetime.now(timezone.utc)
    )

    # Equity components (in USDT)
    equity: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    cash: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    positions_value: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    def __repr__(self) -> str:
        """String representation of the equity snapshot."""
        return (
            f"<EquitySnapshot(time={self.timestamp.isoformat()}, "
            f"equity={self.equity:.2f})>"
        )
