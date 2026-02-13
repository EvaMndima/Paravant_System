"""Immutable data types for the risk management engine.

Provides frozen dataclasses that flow through the risk checking pipeline:
- OrderRequest: Incoming order to validate
- RiskCheckResult: Result of a single risk check
- PortfolioState: Snapshot of portfolio for risk calculations
- PositionSizeResult: Output of position sizing calculation

All types are frozen (immutable) for thread safety and audit integrity.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-08-007 - Input validation at boundaries
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class OrderRequest:
    """Order request submitted for risk validation.

    Immutable snapshot of an order before execution. All fields
    are validated at creation time via __post_init__.

    Attributes:
        account_id: Account placing the order.
        strategy_id: Strategy that generated the signal.
        symbol: Trading pair (e.g., "BTCUSDT").
        side: Order side ("buy" or "sell").
        quantity: Size in base currency units.
        price: Expected execution price in USDT.
        order_type: Order type (MVP: "market" only).
        reason: Why this order was generated.
        stop_loss_price: Stop loss price for position sizing.
    """

    account_id: str
    strategy_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    order_type: str = "market"
    reason: str = ""
    stop_loss_price: float | None = None

    def __post_init__(self) -> None:
        """Validate all fields at creation time.

        Raises:
            ValueError: If any field contains invalid data.
        """
        if not self.account_id:
            raise ValueError("account_id is required")
        if not self.strategy_id:
            raise ValueError("strategy_id is required")
        if not self.symbol:
            raise ValueError("symbol is required")
        if self.side not in ("buy", "sell"):
            raise ValueError(
                f"side must be 'buy' or 'sell', got '{self.side}'"
            )
        # Validate numeric fields
        _validate_positive_float("price", self.price)
        _validate_positive_float("quantity", self.quantity)
        if self.stop_loss_price is not None:
            _validate_finite_float("stop_loss_price", self.stop_loss_price)
            if self.stop_loss_price <= 0:
                raise ValueError("stop_loss_price must be positive")


@dataclass(frozen=True)
class RiskCheckResult:
    """Result of a single risk check operation.

    Returned by each check function in the pipeline.
    Frozen so results cannot be tampered with after creation.

    Attributes:
        approved: Whether the check passed.
        check_name: Name of the check (e.g., "position_size").
        adjusted_quantity: Adjusted size if position was capped.
        rejection_reason: Human-readable rejection reason.
        warnings: Non-blocking warnings.
        checks_passed: List of checks that passed.
        checks_failed: List of checks that failed.
        timestamp: When this result was created (UTC).
    """

    approved: bool
    check_name: str
    adjusted_quantity: float | None = None
    rejection_reason: str | None = None
    warnings: tuple[str, ...] = ()
    checks_passed: tuple[str, ...] = ()
    checks_failed: tuple[str, ...] = ()
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass(frozen=True)
class PortfolioState:
    """Immutable snapshot of portfolio state for risk calculations.

    Reconstructed from DataStore for each risk check cycle.
    All financial values are in USDT.

    Attributes:
        account_id: Account identifier.
        total_equity: Total account value (cash + positions).
        cash_balance: Available cash balance.
        positions_value: Total value of open positions.
        open_positions: Tuple of open Position objects (immutable).
        daily_pnl: Realized PnL since UTC 00:00 today.
        weekly_pnl: Realized PnL since Monday UTC 00:00.
        drawdown_pct: Current drawdown from peak equity (0-100).
        peak_equity: Highest equity recorded.
        consecutive_losses: Count of consecutive losing trades.
        regime: Current market regime string.
    """

    account_id: str
    total_equity: float
    cash_balance: float
    positions_value: float
    open_positions: tuple[Any, ...] = ()
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    drawdown_pct: float = 0.0
    peak_equity: float = 0.0
    consecutive_losses: int = 0
    regime: str = "unknown"

    def __post_init__(self) -> None:
        """Validate portfolio state is internally consistent.

        Raises:
            ValueError: If financial values are invalid or inconsistent.
        """
        # Reject NaN/Infinity on critical financial fields
        for field_name in (
            "total_equity",
            "cash_balance",
            "positions_value",
            "daily_pnl",
            "weekly_pnl",
            "drawdown_pct",
        ):
            value = getattr(self, field_name)
            _validate_finite_float(field_name, value)

        # Equity invariant: total = cash + positions (allow 1 cent rounding)
        expected_total = self.cash_balance + self.positions_value
        if abs(self.total_equity - expected_total) > 0.01:
            raise ValueError(
                f"Equity mismatch: total_equity={self.total_equity}, "
                f"but cash({self.cash_balance}) + "
                f"positions({self.positions_value}) = {expected_total}"
            )

        # Drawdown must be 0-100%
        if not 0 <= self.drawdown_pct <= 100:
            raise ValueError(
                f"drawdown_pct must be 0-100, got {self.drawdown_pct}"
            )

        # Consecutive losses must be non-negative
        if self.consecutive_losses < 0:
            raise ValueError(
                f"consecutive_losses must be >= 0, "
                f"got {self.consecutive_losses}"
            )


@dataclass(frozen=True)
class PositionSizeResult:
    """Result of a position sizing calculation.

    Returned by calculate_position_size and its variants.

    Attributes:
        quantity: Position size in base currency.
        notional_value: Position value in USDT (quantity * price).
        risk_amount: Dollar amount at risk.
        risk_pct: Risk as percentage of equity.
        sizing_method: Method used ("fixed_risk", "atr_based", "kelly").
        stop_loss_price: Stop loss price used in calculation.
        entry_price: Entry price used in calculation.
        adjustments_applied: Tuple of adjustments that were applied.
        regime_multiplier: Regime adjustment multiplier applied.
    """

    quantity: float
    notional_value: float
    risk_amount: float
    risk_pct: float
    sizing_method: str
    stop_loss_price: float
    entry_price: float
    adjustments_applied: tuple[str, ...] = ()
    regime_multiplier: float = 1.0

    def __post_init__(self) -> None:
        """Validate sizing result.

        Raises:
            ValueError: If any value is invalid.
        """
        _validate_finite_float("quantity", self.quantity)
        if self.quantity < 0:
            raise ValueError(
                f"quantity must be >= 0, got {self.quantity}"
            )
        _validate_finite_float("notional_value", self.notional_value)
        _validate_finite_float("risk_amount", self.risk_amount)
        _validate_positive_float("entry_price", self.entry_price)
        _validate_positive_float("stop_loss_price", self.stop_loss_price)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_finite_float(name: str, value: float) -> None:
    """Validate that a float is finite (not NaN or Infinity).

    Args:
        name: Field name for error message.
        value: Value to validate.

    Raises:
        ValueError: If value is NaN or Infinity.
    """
    if math.isnan(value):
        raise ValueError(f"{name} cannot be NaN")
    if math.isinf(value):
        raise ValueError(f"{name} cannot be Infinity")


def _validate_positive_float(name: str, value: float) -> None:
    """Validate that a float is positive and finite.

    Args:
        name: Field name for error message.
        value: Value to validate.

    Raises:
        ValueError: If value is NaN, Infinity, zero, or negative.
    """
    _validate_finite_float(name, value)
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
