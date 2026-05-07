"""Backtest core data types.

Frozen dataclasses for backtest configuration, trade records, and equity
curve points. All values are validated at construction time.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-007 - Input validation at model layer (NaN, Inf, negatives)
Decision: DEC-2026-02-12-001 - Compute-on-demand; frozen immutable outputs
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.data.models.signal import SignalDirection


def _validate_finite_positive(value: float, name: str) -> None:
    """Validate that a float is finite and non-negative.

    Args:
        value: The value to validate.
        name: Field name for error messages.

    Raises:
        ValueError: If value is NaN, Infinity, or negative.
    """
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"{name} must be finite, got {value}")
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")


def _validate_finite(value: float, name: str) -> None:
    """Validate that a float is finite (allows negative for P&L).

    Args:
        value: The value to validate.
        name: Field name for error messages.

    Raises:
        ValueError: If value is NaN or Infinity.
    """
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"{name} must be finite, got {value}")


def _validate_tz_aware(ts: datetime, name: str) -> None:
    """Validate that a datetime is timezone-aware.

    Decision: DEC-2026-02-08-003 - All timestamps must be timezone-aware UTC.

    Args:
        ts: The datetime to validate.
        name: Field name for error messages.

    Raises:
        ValueError: If timestamp is timezone-naive.
    """
    if ts.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware (UTC)")


@dataclass(frozen=True)
class BacktestConfig:
    """Configuration for a backtest run.

    Controls initial capital, commission/slippage rates, and fill behavior.
    All rates are expressed as decimals (e.g., 0.001 = 0.1%).

    Attributes:
        initial_capital: Starting portfolio value in USDT.
        commission_rate: Commission per trade as decimal fraction (0.001 = 0.1%).
        slippage_rate: Slippage per trade as decimal fraction (0.0005 = 0.05%).
        use_next_bar_open: If True, fill at next bar open (prevents lookahead).
        risk_free_rate: Annual risk-free rate for Sharpe/Sortino (0.02 = 2%).
        position_size_pct: Fraction of equity to risk per trade (0.95 = 95%).
    """

    initial_capital: float = 10_000.0
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    use_next_bar_open: bool = True
    risk_free_rate: float = 0.02
    position_size_pct: float = 0.35

    def __post_init__(self) -> None:
        """Validate config fields after initialization.

        Raises:
            ValueError: If any field has an invalid value.
        """
        _validate_finite_positive(self.initial_capital, "initial_capital")
        if self.initial_capital <= 0:
            raise ValueError(
                f"initial_capital must be positive, got {self.initial_capital}"
            )

        _validate_finite_positive(self.commission_rate, "commission_rate")
        _validate_finite_positive(self.slippage_rate, "slippage_rate")
        _validate_finite_positive(self.risk_free_rate, "risk_free_rate")
        _validate_finite_positive(self.position_size_pct, "position_size_pct")

        if self.commission_rate >= 1.0:
            raise ValueError(
                f"commission_rate must be < 1.0, got {self.commission_rate}"
            )
        if self.slippage_rate >= 1.0:
            raise ValueError(
                f"slippage_rate must be < 1.0, got {self.slippage_rate}"
            )
        if self.position_size_pct <= 0 or self.position_size_pct > 1.0:
            raise ValueError(
                f"position_size_pct must be in (0, 1.0], got {self.position_size_pct}"
            )


@dataclass(frozen=True)
class TradeRecord:
    """Immutable record of a completed simulated trade.

    Captures all details of a round-trip trade: entry, exit, costs, and
    realized P&L. Created by the SimulatedTrader when a position is closed.

    Attributes:
        entry_time: Timezone-aware UTC timestamp of trade entry.
        exit_time: Timezone-aware UTC timestamp of trade exit.
        symbol: Trading pair (e.g., ``BTCUSDT``).
        direction: Signal direction that triggered entry (LONG/SHORT).
        entry_price: Fill price at entry (after slippage).
        exit_price: Fill price at exit (after slippage).
        quantity: Trade size in base asset.
        entry_commission: Commission paid at entry in USDT.
        exit_commission: Commission paid at exit in USDT.
        slippage_cost: Total slippage cost in USDT (entry + exit).
        realized_pnl: Net profit/loss after all costs in USDT.
        return_pct: Return as percentage of entry value.
    """

    entry_time: datetime
    exit_time: datetime
    symbol: str
    direction: SignalDirection
    entry_price: float
    exit_price: float
    quantity: float
    entry_commission: float
    exit_commission: float
    slippage_cost: float
    realized_pnl: float
    return_pct: float

    def __post_init__(self) -> None:
        """Validate trade record fields.

        Raises:
            ValueError: If any field has an invalid value.
        """
        _validate_tz_aware(self.entry_time, "entry_time")
        _validate_tz_aware(self.exit_time, "exit_time")

        if self.exit_time < self.entry_time:
            raise ValueError(
                "exit_time cannot be before entry_time"
            )

        if not self.symbol or not self.symbol.strip():
            raise ValueError("symbol cannot be empty")

        _validate_finite_positive(self.entry_price, "entry_price")
        _validate_finite_positive(self.exit_price, "exit_price")
        _validate_finite_positive(self.quantity, "quantity")
        if self.entry_price <= 0:
            raise ValueError(
                f"entry_price must be positive, got {self.entry_price}"
            )
        if self.exit_price <= 0:
            raise ValueError(
                f"exit_price must be positive, got {self.exit_price}"
            )
        if self.quantity <= 0:
            raise ValueError(
                f"quantity must be positive, got {self.quantity}"
            )

        _validate_finite_positive(self.entry_commission, "entry_commission")
        _validate_finite_positive(self.exit_commission, "exit_commission")
        _validate_finite_positive(self.slippage_cost, "slippage_cost")
        _validate_finite(self.realized_pnl, "realized_pnl")
        _validate_finite(self.return_pct, "return_pct")

    @property
    def total_commission(self) -> float:
        """Total commission paid (entry + exit).

        Returns:
            Sum of entry and exit commissions.
        """
        return self.entry_commission + self.exit_commission

    @property
    def is_winner(self) -> bool:
        """Whether this trade was profitable.

        Returns:
            True if realized P&L is positive.
        """
        return self.realized_pnl > 0

    @property
    def duration_hours(self) -> float:
        """Trade duration in hours.

        Returns:
            Duration from entry to exit in hours.
        """
        delta = self.exit_time - self.entry_time
        return delta.total_seconds() / 3600.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON storage.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return {
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat(),
            "symbol": self.symbol,
            "direction": self.direction.value,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "entry_commission": self.entry_commission,
            "exit_commission": self.exit_commission,
            "slippage_cost": self.slippage_cost,
            "realized_pnl": self.realized_pnl,
            "return_pct": self.return_pct,
            # Pre-computed derived fields so readers don't need to re-derive them
            "duration_hours": round(self.duration_hours, 2),
            "total_commission": round(self.total_commission, 6),
        }


@dataclass(frozen=True)
class EquityPoint:
    """Single point on the equity curve.

    Tracks total portfolio value at a given bar timestamp, split into
    cash and position (mark-to-market) components.

    Attributes:
        timestamp: Timezone-aware UTC timestamp of this equity snapshot.
        equity: Total portfolio value (cash + position_value).
        cash: Cash held outside of open positions.
        position_value: Mark-to-market value of any open position.
    """

    timestamp: datetime
    equity: float
    cash: float
    position_value: float

    def __post_init__(self) -> None:
        """Validate equity point fields.

        Raises:
            ValueError: If any field has an invalid value.
        """
        _validate_tz_aware(self.timestamp, "timestamp")
        _validate_finite(self.equity, "equity")
        _validate_finite(self.cash, "cash")
        _validate_finite(self.position_value, "position_value")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON storage.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "equity": self.equity,
            "cash": self.cash,
            "position_value": self.position_value,
        }
