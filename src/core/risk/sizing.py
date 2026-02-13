"""Position sizing methods and capital allocation rules.

Provides three sizing methods:
- Fixed Risk %: Risk a fixed percentage of equity per trade
- ATR-based: Size inversely proportional to volatility
- Kelly Criterion: Probability-adjusted sizing (fractional Kelly)

Also enforces capital allocation rules per PRD Feature G:
- 20% minimum cash reserve
- 10% emergency buffer
- 5% max for new strategies, 15% for proven strategies

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-08-007 - Input validation at boundaries
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

import math

from src.core.config.risk_profiles import RiskProfileConfig
from src.core.risk.types import PortfolioState, PositionSizeResult
from src.utils.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Capital allocation constants (PRD Feature G)
# ---------------------------------------------------------------------------

MINIMUM_CASH_RESERVE_PCT: float = 20.0
EMERGENCY_BUFFER_PCT: float = 10.0
NEW_STRATEGY_MAX_PCT: float = 5.0
PROVEN_STRATEGY_MAX_PCT: float = 15.0
GRADUATION_DAYS: int = 30
GRADUATION_MIN_TRADES: int = 20
GRADUATION_INCREASE_PCT: float = 5.0


# ---------------------------------------------------------------------------
# Position sizing methods
# ---------------------------------------------------------------------------


def calculate_fixed_risk_size(
    capital: float,
    risk_pct: float,
    entry_price: float,
    stop_loss_price: float,
) -> PositionSizeResult:
    """Calculate position size using fixed risk percentage method.

    Formula: quantity = (capital * risk_pct) / |entry - stop_loss|

    Args:
        capital: Available capital in USDT.
        risk_pct: Risk per trade as decimal (e.g., 0.02 for 2%).
        entry_price: Expected entry price.
        stop_loss_price: Stop loss price.

    Returns:
        PositionSizeResult with calculated quantity.

    Raises:
        ValueError: If inputs are invalid.
    """
    _validate_sizing_inputs(capital, risk_pct, entry_price, stop_loss_price)

    risk_per_unit = abs(entry_price - stop_loss_price)
    risk_amount = capital * risk_pct
    quantity = risk_amount / risk_per_unit
    notional_value = quantity * entry_price

    logger.debug(
        "position_size_fixed_risk",
        capital=capital,
        risk_pct=risk_pct,
        risk_amount=risk_amount,
        quantity=quantity,
    )

    return PositionSizeResult(
        quantity=quantity,
        notional_value=notional_value,
        risk_amount=risk_amount,
        risk_pct=risk_pct * 100,
        sizing_method="fixed_risk",
        stop_loss_price=stop_loss_price,
        entry_price=entry_price,
    )


def calculate_atr_size(
    capital: float,
    risk_pct: float,
    entry_price: float,
    stop_loss_price: float,
    atr_value: float,
    atr_multiplier: float = 2.0,
) -> PositionSizeResult:
    """Calculate position size using ATR-based method.

    Formula: quantity = (capital * risk_pct) / (atr_value * multiplier)

    The ATR-based method sizes positions inversely to volatility.
    In volatile markets, positions are smaller; in calm markets, larger.

    Args:
        capital: Available capital in USDT.
        risk_pct: Risk per trade as decimal (e.g., 0.02 for 2%).
        entry_price: Expected entry price.
        stop_loss_price: Stop loss price (for result tracking).
        atr_value: Current ATR value for the symbol.
        atr_multiplier: ATR multiplier (default 2.0).

    Returns:
        PositionSizeResult with calculated quantity.

    Raises:
        ValueError: If inputs are invalid or ATR is non-positive.
    """
    _validate_sizing_inputs(capital, risk_pct, entry_price, stop_loss_price)

    if atr_value <= 0:
        raise ValueError(f"atr_value must be positive, got {atr_value}")
    if math.isnan(atr_value) or math.isinf(atr_value):
        raise ValueError(f"atr_value must be finite, got {atr_value}")
    if atr_multiplier <= 0:
        raise ValueError(
            f"atr_multiplier must be positive, got {atr_multiplier}"
        )

    risk_amount = capital * risk_pct
    quantity = risk_amount / (atr_value * atr_multiplier)
    notional_value = quantity * entry_price

    logger.debug(
        "position_size_atr",
        capital=capital,
        risk_pct=risk_pct,
        atr_value=atr_value,
        atr_multiplier=atr_multiplier,
        quantity=quantity,
    )

    return PositionSizeResult(
        quantity=quantity,
        notional_value=notional_value,
        risk_amount=risk_amount,
        risk_pct=risk_pct * 100,
        sizing_method="atr_based",
        stop_loss_price=stop_loss_price,
        entry_price=entry_price,
        adjustments_applied=("atr_volatility",),
    )


def calculate_kelly_size(
    capital: float,
    entry_price: float,
    stop_loss_price: float,
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    kelly_fraction: float = 0.25,
) -> PositionSizeResult:
    """Calculate position size using Kelly Criterion.

    Kelly formula: f = (win_rate * avg_win - (1-win_rate) * avg_loss) / avg_win
    Uses fractional Kelly (default 25%) for safety.

    Args:
        capital: Available capital in USDT.
        entry_price: Expected entry price.
        stop_loss_price: Stop loss price.
        win_rate: Historical win rate (0.0 to 1.0).
        avg_win: Average winning trade amount in USDT.
        avg_loss: Average losing trade amount in USDT (positive value).
        kelly_fraction: Fraction of full Kelly to use (default 0.25).

    Returns:
        PositionSizeResult with calculated quantity.

    Raises:
        ValueError: If inputs are invalid or Kelly yields negative.
    """
    if not 0 < win_rate < 1:
        raise ValueError(f"win_rate must be between 0 and 1, got {win_rate}")
    if avg_win <= 0:
        raise ValueError(f"avg_win must be positive, got {avg_win}")
    if avg_loss <= 0:
        raise ValueError(f"avg_loss must be positive, got {avg_loss}")
    if not 0 < kelly_fraction <= 1:
        raise ValueError(
            f"kelly_fraction must be between 0 and 1, got {kelly_fraction}"
        )

    _validate_sizing_inputs(capital, 0.01, entry_price, stop_loss_price)

    # Kelly formula
    kelly_pct = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    fractional_kelly = kelly_pct * kelly_fraction

    # If Kelly is negative, strategy has negative expectancy - size to 0
    if fractional_kelly <= 0:
        logger.warning(
            "kelly_negative_expectancy",
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            kelly_pct=kelly_pct,
        )
        return PositionSizeResult(
            quantity=0.0,
            notional_value=0.0,
            risk_amount=0.0,
            risk_pct=0.0,
            sizing_method="kelly",
            stop_loss_price=stop_loss_price,
            entry_price=entry_price,
            adjustments_applied=("kelly_negative_expectancy",),
        )

    # Calculate position size
    risk_amount = capital * fractional_kelly
    risk_per_unit = abs(entry_price - stop_loss_price)
    quantity = risk_amount / risk_per_unit
    notional_value = quantity * entry_price

    logger.debug(
        "position_size_kelly",
        capital=capital,
        kelly_pct=kelly_pct,
        fractional_kelly=fractional_kelly,
        quantity=quantity,
    )

    return PositionSizeResult(
        quantity=quantity,
        notional_value=notional_value,
        risk_amount=risk_amount,
        risk_pct=fractional_kelly * 100,
        sizing_method="kelly",
        stop_loss_price=stop_loss_price,
        entry_price=entry_price,
        adjustments_applied=("kelly_criterion",),
    )


# ---------------------------------------------------------------------------
# Capital allocation
# ---------------------------------------------------------------------------


def calculate_available_capital(
    portfolio: PortfolioState,
) -> float:
    """Calculate capital available for new positions.

    Subtracts the minimum cash reserve (20%) and emergency buffer (10%)
    from the cash balance.

    Available = cash_balance - (total_equity * (reserve + buffer) / 100)

    Args:
        portfolio: Current portfolio state.

    Returns:
        Available capital in USDT (never negative).
    """
    reserved_pct = MINIMUM_CASH_RESERVE_PCT + EMERGENCY_BUFFER_PCT
    reserved_amount = portfolio.total_equity * reserved_pct / 100

    available = max(0.0, portfolio.cash_balance - reserved_amount)

    logger.debug(
        "capital_available",
        total_equity=portfolio.total_equity,
        cash_balance=portfolio.cash_balance,
        reserved_amount=reserved_amount,
        available=available,
    )

    return available


def apply_regime_adjustment(
    size: float,
    regime: str,
    profile: RiskProfileConfig,
) -> tuple[float, float]:
    """Apply regime-specific multiplier to position size.

    Uses the regime_adjustments from the risk profile to scale
    position size based on current market regime.

    Args:
        size: Raw position size (quantity).
        regime: Current market regime string.
        profile: Risk profile with regime adjustments.

    Returns:
        Tuple of (adjusted_size, multiplier_applied).
    """
    adjustments = profile.regime_adjustments.model_dump()
    multiplier = adjustments.get(regime, adjustments.get("unknown", 1.0))

    adjusted = size * multiplier

    if multiplier < 1.0:
        logger.info(
            "regime_adjustment_applied",
            regime=regime,
            multiplier=multiplier,
            original_size=size,
            adjusted_size=adjusted,
        )

    return adjusted, multiplier


def get_strategy_max_allocation_pct(
    is_proven: bool,
) -> float:
    """Get the maximum allocation percentage for a strategy.

    New strategies are limited to 5% of portfolio.
    Proven strategies (30+ profitable days, 20+ trades) get 15%.

    Args:
        is_proven: Whether the strategy qualifies as proven.

    Returns:
        Maximum allocation as percentage of portfolio.
    """
    if is_proven:
        return PROVEN_STRATEGY_MAX_PCT
    return NEW_STRATEGY_MAX_PCT


def validate_allocation(
    requested_pct: float,
    is_proven: bool,
    portfolio: PortfolioState,
) -> tuple[bool, str]:
    """Validate a requested capital allocation for a strategy.

    Checks both the per-strategy limit and available capital.

    Args:
        requested_pct: Requested allocation as % of portfolio.
        is_proven: Whether the strategy is proven.
        portfolio: Current portfolio state.

    Returns:
        Tuple of (approved, reason_message).
    """
    max_allowed = get_strategy_max_allocation_pct(is_proven)

    if requested_pct > max_allowed:
        status = "proven" if is_proven else "new"
        return False, (
            f"Max allocation for {status} strategy is "
            f"{max_allowed:.1f}%, requested {requested_pct:.1f}%"
        )

    available = calculate_available_capital(portfolio)
    requested_value = portfolio.total_equity * requested_pct / 100

    if requested_value > available:
        return False, (
            f"Insufficient available capital. "
            f"Requested: ${requested_value:,.2f}, "
            f"Available: ${available:,.2f}"
        )

    return True, "OK"


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_sizing_inputs(
    capital: float,
    risk_pct: float,
    entry_price: float,
    stop_loss_price: float,
) -> None:
    """Validate common inputs for sizing calculations.

    Args:
        capital: Capital amount.
        risk_pct: Risk percentage (decimal).
        entry_price: Entry price.
        stop_loss_price: Stop loss price.

    Raises:
        ValueError: If any input is invalid.
    """
    if capital <= 0:
        raise ValueError(f"capital must be positive, got {capital}")
    if math.isnan(capital) or math.isinf(capital):
        raise ValueError(f"capital must be finite, got {capital}")

    if risk_pct <= 0:
        raise ValueError(f"risk_pct must be positive, got {risk_pct}")
    if risk_pct > 1.0:
        raise ValueError(
            f"risk_pct must be <= 1.0 (100%), got {risk_pct}"
        )

    if entry_price <= 0:
        raise ValueError(f"entry_price must be positive, got {entry_price}")
    if math.isnan(entry_price) or math.isinf(entry_price):
        raise ValueError(f"entry_price must be finite, got {entry_price}")

    if stop_loss_price <= 0:
        raise ValueError(
            f"stop_loss_price must be positive, got {stop_loss_price}"
        )
    if math.isnan(stop_loss_price) or math.isinf(stop_loss_price):
        raise ValueError(
            f"stop_loss_price must be finite, got {stop_loss_price}"
        )

    if entry_price == stop_loss_price:
        raise ValueError(
            "entry_price and stop_loss_price cannot be equal "
            "(zero risk per unit)"
        )
