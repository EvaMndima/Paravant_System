"""Pure risk check functions for the order validation pipeline.

Each function takes typed inputs and returns a RiskCheckResult.
Functions are pure (no side effects, no database access) and
can be composed into a pipeline by the RiskController.

Pipeline order (STRICT - do NOT reorder):
1. check_kill_switch - immediate rejection if active
2. check_daily_loss_limit - daily loss threshold
3. check_weekly_loss_limit - weekly loss threshold
4. check_max_drawdown - max drawdown threshold
5. check_max_positions - concurrent position limit
6. check_concentration - single-symbol exposure limit
7. check_position_size - individual position size limit
8. check_portfolio_correlation - cross-strategy asset exposure limits

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-08-007 - Input validation at boundaries
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

from src.core.config.risk_profiles import RiskProfileConfig
from src.core.risk.types import OrderRequest, PortfolioState, RiskCheckResult
from src.data.models.system import SystemState
from src.utils.logging import get_logger

logger = get_logger(__name__)


def check_kill_switch(system_state: SystemState) -> RiskCheckResult:
    """Check if the kill switch is active.

    This is the first check in the pipeline. If the kill switch
    is active, all trading is immediately halted.

    Args:
        system_state: Current system state singleton.

    Returns:
        RiskCheckResult indicating pass or fail.
    """
    if system_state.kill_switch_active:
        reason = system_state.kill_switch_reason or "Kill switch is active"
        logger.warning(
            "risk_check_kill_switch_rejected",
            reason=reason,
        )
        return RiskCheckResult(
            approved=False,
            check_name="kill_switch",
            rejection_reason=f"Kill switch is active: {reason}",
            checks_failed=("kill_switch",),
        )

    return RiskCheckResult(
        approved=True,
        check_name="kill_switch",
        checks_passed=("kill_switch",),
    )


def check_daily_loss_limit(
    portfolio: PortfolioState,
    profile: RiskProfileConfig,
) -> RiskCheckResult:
    """Check if daily loss limit has been breached.

    Compares the portfolio's daily PnL against the profile's
    daily_loss_limit_pct. Negative PnL that exceeds the limit
    (as a % of equity) triggers rejection.

    Args:
        portfolio: Current portfolio state snapshot.
        profile: Risk profile configuration with limits.

    Returns:
        RiskCheckResult indicating pass or fail.
    """
    if portfolio.total_equity <= 0:
        return RiskCheckResult(
            approved=False,
            check_name="daily_loss_limit",
            rejection_reason="Cannot trade with zero or negative equity",
            checks_failed=("daily_loss_limit",),
        )

    if portfolio.daily_pnl >= 0:
        # No daily loss - check passes
        return RiskCheckResult(
            approved=True,
            check_name="daily_loss_limit",
            checks_passed=("daily_loss_limit",),
        )

    daily_loss_pct = abs(portfolio.daily_pnl) / portfolio.total_equity * 100

    if daily_loss_pct >= profile.daily_loss_limit_pct:
        reason = (
            f"Daily loss {daily_loss_pct:.2f}% exceeds limit "
            f"{profile.daily_loss_limit_pct:.1f}%"
        )
        logger.warning(
            "risk_check_daily_loss_rejected",
            daily_loss_pct=daily_loss_pct,
            limit_pct=profile.daily_loss_limit_pct,
            daily_pnl=portfolio.daily_pnl,
        )
        return RiskCheckResult(
            approved=False,
            check_name="daily_loss_limit",
            rejection_reason=reason,
            checks_failed=("daily_loss_limit",),
        )

    return RiskCheckResult(
        approved=True,
        check_name="daily_loss_limit",
        checks_passed=("daily_loss_limit",),
    )


def check_weekly_loss_limit(
    portfolio: PortfolioState,
    profile: RiskProfileConfig,
) -> RiskCheckResult:
    """Check if weekly loss limit has been breached.

    Args:
        portfolio: Current portfolio state snapshot.
        profile: Risk profile configuration with limits.

    Returns:
        RiskCheckResult indicating pass or fail.
    """
    if portfolio.total_equity <= 0:
        return RiskCheckResult(
            approved=False,
            check_name="weekly_loss_limit",
            rejection_reason="Cannot trade with zero or negative equity",
            checks_failed=("weekly_loss_limit",),
        )

    if portfolio.weekly_pnl >= 0:
        return RiskCheckResult(
            approved=True,
            check_name="weekly_loss_limit",
            checks_passed=("weekly_loss_limit",),
        )

    weekly_loss_pct = abs(portfolio.weekly_pnl) / portfolio.total_equity * 100

    if weekly_loss_pct >= profile.weekly_loss_limit_pct:
        reason = (
            f"Weekly loss {weekly_loss_pct:.2f}% exceeds limit "
            f"{profile.weekly_loss_limit_pct:.1f}%"
        )
        logger.warning(
            "risk_check_weekly_loss_rejected",
            weekly_loss_pct=weekly_loss_pct,
            limit_pct=profile.weekly_loss_limit_pct,
            weekly_pnl=portfolio.weekly_pnl,
        )
        return RiskCheckResult(
            approved=False,
            check_name="weekly_loss_limit",
            rejection_reason=reason,
            checks_failed=("weekly_loss_limit",),
        )

    return RiskCheckResult(
        approved=True,
        check_name="weekly_loss_limit",
        checks_passed=("weekly_loss_limit",),
    )


def check_max_drawdown(
    portfolio: PortfolioState,
    profile: RiskProfileConfig,
) -> RiskCheckResult:
    """Check if maximum drawdown limit has been breached.

    Args:
        portfolio: Current portfolio state snapshot.
        profile: Risk profile configuration with limits.

    Returns:
        RiskCheckResult indicating pass or fail.
    """
    if portfolio.drawdown_pct >= profile.max_drawdown_pct:
        reason = (
            f"Drawdown {portfolio.drawdown_pct:.2f}% exceeds limit "
            f"{profile.max_drawdown_pct:.1f}%"
        )
        logger.warning(
            "risk_check_drawdown_rejected",
            drawdown_pct=portfolio.drawdown_pct,
            limit_pct=profile.max_drawdown_pct,
        )
        return RiskCheckResult(
            approved=False,
            check_name="max_drawdown",
            rejection_reason=reason,
            checks_failed=("max_drawdown",),
        )

    return RiskCheckResult(
        approved=True,
        check_name="max_drawdown",
        checks_passed=("max_drawdown",),
    )


def check_max_positions(
    order: OrderRequest,
    portfolio: PortfolioState,
    profile: RiskProfileConfig,
) -> RiskCheckResult:
    """Check if opening this order would exceed the max positions limit.

    Exception: closing trades (opposite side to existing position)
    are always allowed, even at max positions.

    Args:
        order: The order to validate.
        portfolio: Current portfolio state snapshot.
        profile: Risk profile configuration with limits.

    Returns:
        RiskCheckResult indicating pass or fail.
    """
    open_count = len(portfolio.open_positions)

    # Check if this is a closing trade (always allowed)
    for position in portfolio.open_positions:
        if position.symbol == order.symbol:
            is_closing = (
                (position.side.value == "long" and order.side == "sell")
                or (position.side.value == "short" and order.side == "buy")
            )
            if is_closing:
                return RiskCheckResult(
                    approved=True,
                    check_name="max_positions",
                    checks_passed=("max_positions",),
                )
            break

    if open_count >= profile.max_open_positions:
        reason = (
            f"At max positions ({profile.max_open_positions}). "
            f"Current: {open_count}. "
            f"Close a position to open a new one."
        )
        logger.warning(
            "risk_check_max_positions_rejected",
            open_count=open_count,
            max_positions=profile.max_open_positions,
        )
        return RiskCheckResult(
            approved=False,
            check_name="max_positions",
            rejection_reason=reason,
            checks_failed=("max_positions",),
        )

    return RiskCheckResult(
        approved=True,
        check_name="max_positions",
        checks_passed=("max_positions",),
    )


def check_concentration(
    order: OrderRequest,
    portfolio: PortfolioState,
    profile: RiskProfileConfig,
) -> RiskCheckResult:
    """Check if the order would exceed concentration limit for a symbol.

    Sums existing position value + new order value and checks
    against max_concentration_pct.

    Args:
        order: The order to validate.
        portfolio: Current portfolio state snapshot.
        profile: Risk profile configuration with limits.

    Returns:
        RiskCheckResult indicating pass or fail.
    """
    if portfolio.total_equity <= 0:
        return RiskCheckResult(
            approved=False,
            check_name="concentration",
            rejection_reason="Cannot check concentration with zero equity",
            checks_failed=("concentration",),
        )

    # Calculate existing exposure for this symbol
    existing_value = 0.0
    for position in portfolio.open_positions:
        if position.symbol == order.symbol:
            existing_value = position.size * position.current_price
            break

    # New order value
    new_value = order.quantity * order.price

    # Combined concentration
    combined_value = existing_value + new_value
    combined_pct = (combined_value / portfolio.total_equity) * 100

    if combined_pct > profile.max_concentration_pct:
        existing_pct = (existing_value / portfolio.total_equity) * 100
        remaining_pct = max(0, profile.max_concentration_pct - existing_pct)
        reason = (
            f"{order.symbol} would be {combined_pct:.2f}% of portfolio. "
            f"Max allowed: {profile.max_concentration_pct:.1f}%. "
            f"Remaining capacity: {remaining_pct:.2f}%"
        )
        logger.warning(
            "risk_check_concentration_rejected",
            symbol=order.symbol,
            combined_pct=combined_pct,
            max_pct=profile.max_concentration_pct,
        )
        return RiskCheckResult(
            approved=False,
            check_name="concentration",
            rejection_reason=reason,
            checks_failed=("concentration",),
        )

    return RiskCheckResult(
        approved=True,
        check_name="concentration",
        checks_passed=("concentration",),
    )


def check_position_size(
    order: OrderRequest,
    portfolio: PortfolioState,
    profile: RiskProfileConfig,
) -> RiskCheckResult:
    """Check if the individual position size exceeds the limit.

    Calculates order value as a percentage of total equity and
    compares against max_position_size_pct.

    Args:
        order: The order to validate.
        portfolio: Current portfolio state snapshot.
        profile: Risk profile configuration with limits.

    Returns:
        RiskCheckResult indicating pass or fail.
    """
    if portfolio.total_equity <= 0:
        return RiskCheckResult(
            approved=False,
            check_name="position_size",
            rejection_reason="Cannot check position size with zero equity",
            checks_failed=("position_size",),
        )

    position_value = order.quantity * order.price
    position_pct = (position_value / portfolio.total_equity) * 100

    if position_pct > profile.max_position_size_pct:
        reason = (
            f"Position size {position_pct:.2f}% exceeds max "
            f"{profile.max_position_size_pct:.1f}% "
            f"(value: ${position_value:,.2f}, "
            f"equity: ${portfolio.total_equity:,.2f})"
        )
        logger.warning(
            "risk_check_position_size_rejected",
            position_pct=position_pct,
            max_pct=profile.max_position_size_pct,
            position_value=position_value,
        )
        return RiskCheckResult(
            approved=False,
            check_name="position_size",
            rejection_reason=reason,
            checks_failed=("position_size",),
        )

    return RiskCheckResult(
        approved=True,
        check_name="position_size",
        checks_passed=("position_size",),
    )


# ---------------------------------------------------------------------------
# Portfolio Correlation Limits (PRD §2.2.1 Feature A)
# ---------------------------------------------------------------------------

# Per-asset long exposure caps (base asset -> max % of total equity).
# Decision: PRD §2.2.1 Feature A - prevent over-concentration in same direction.
_ASSET_EXPOSURE_LIMITS: dict[str, float] = {
    "BTC": 40.0,  # max_btc_exposure_pct
    "ETH": 30.0,  # max_eth_exposure_pct
}

# Maximum total long exposure across all correlated positions.
_MAX_CORRELATED_EXPOSURE_PCT: float = 60.0


def check_portfolio_correlation(
    order: OrderRequest,
    portfolio: PortfolioState,
) -> RiskCheckResult:
    """Check portfolio-level asset exposure limits across all strategies.

    Enforces per-asset and total-correlated caps to prevent over-concentration
    in any single asset or direction. This is a cross-strategy check — it sums
    ALL open positions regardless of which strategy owns them.

    Per PRD §2.2.1 Feature A (Portfolio Correlation Limits):
      - BTC long exposure: max 40% of total equity
      - ETH long exposure: max 30% of total equity
      - Total correlated long exposure: max 60% of total equity

    Only applied to BUY orders (opening long positions). SELL orders
    that close existing positions are always allowed through this check.

    Args:
        order: The order to validate.
        portfolio: Current portfolio state (all open positions, all strategies).

    Returns:
        RiskCheckResult indicating pass or fail.
    """
    if portfolio.total_equity <= 0:
        return RiskCheckResult(
            approved=False,
            check_name="portfolio_correlation",
            rejection_reason="Cannot check correlation with zero equity",
            checks_failed=("portfolio_correlation",),
        )

    # Only apply to orders that open new long positions.
    # Closing trades (SELL against existing LONG) pass through freely.
    if order.side != "buy":
        return RiskCheckResult(
            approved=True,
            check_name="portfolio_correlation",
            checks_passed=("portfolio_correlation",),
        )

    new_order_base = _extract_base_asset(order.symbol)
    new_order_value = order.quantity * order.price

    # Tally existing long exposure per base asset
    asset_long_exposure: dict[str, float] = {}
    total_long_exposure: float = 0.0

    for pos in portfolio.open_positions:
        if pos.side.value != "long":
            continue
        base = _extract_base_asset(pos.symbol)
        pos_value = pos.size * pos.current_price
        asset_long_exposure[base] = asset_long_exposure.get(base, 0.0) + pos_value
        total_long_exposure += pos_value

    # Include the proposed new buy order in the totals
    asset_long_exposure[new_order_base] = (
        asset_long_exposure.get(new_order_base, 0.0) + new_order_value
    )
    total_long_exposure += new_order_value

    # Check per-asset limits (BTC 40%, ETH 30%)
    for asset, limit_pct in _ASSET_EXPOSURE_LIMITS.items():
        exposure = asset_long_exposure.get(asset, 0.0)
        exposure_pct = (exposure / portfolio.total_equity) * 100
        if exposure_pct > limit_pct:
            reason = (
                f"{asset} long exposure {exposure_pct:.2f}% exceeds "
                f"portfolio limit {limit_pct:.1f}%"
            )
            logger.warning(
                "risk_check_correlation_asset_rejected",
                asset=asset,
                exposure_pct=exposure_pct,
                limit_pct=limit_pct,
                symbol=order.symbol,
            )
            return RiskCheckResult(
                approved=False,
                check_name="portfolio_correlation",
                rejection_reason=reason,
                checks_failed=("portfolio_correlation",),
            )

    # Check total correlated (all-long) exposure cap
    total_pct = (total_long_exposure / portfolio.total_equity) * 100
    if total_pct > _MAX_CORRELATED_EXPOSURE_PCT:
        reason = (
            f"Total correlated long exposure {total_pct:.2f}% exceeds "
            f"limit {_MAX_CORRELATED_EXPOSURE_PCT:.1f}%"
        )
        logger.warning(
            "risk_check_correlation_total_rejected",
            total_exposure_pct=total_pct,
            limit_pct=_MAX_CORRELATED_EXPOSURE_PCT,
            symbol=order.symbol,
        )
        return RiskCheckResult(
            approved=False,
            check_name="portfolio_correlation",
            rejection_reason=reason,
            checks_failed=("portfolio_correlation",),
        )

    return RiskCheckResult(
        approved=True,
        check_name="portfolio_correlation",
        checks_passed=("portfolio_correlation",),
    )


def _extract_base_asset(symbol: str) -> str:
    """Extract base asset from a USDT-quoted trading symbol.

    Strips common quote currency suffixes. All MVP symbols are USDT pairs
    (BTCUSDT, ETHUSDT, etc.) per DEC-2026-01-15-001.

    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT").

    Returns:
        Base asset string (e.g., "BTC").
    """
    symbol_upper = symbol.upper()
    for quote in ("USDT", "BUSD"):
        if symbol_upper.endswith(quote) and len(symbol_upper) > len(quote):
            return symbol_upper[: -len(quote)]
    return symbol_upper
