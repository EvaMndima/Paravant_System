"""Central risk management orchestrator.

Coordinates all risk checks for order validation:
1. Kill switch check (immediate rejection if active)
2. Circuit breaker check (if manager provided)
3. Time filter check (if filter provided)
4. Event filter check (if filter provided)
5. Volatility filter check (if analyzer provided)
6. Daily loss limit check
7. Weekly loss limit check
8. Max drawdown check
9. Max positions check
10. Concentration check
11. Position size check

All orders must pass through validate_order() before execution.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-08-007 - Input validation at boundaries
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-02-12-010 - Circuit breakers complement pure checks
Decision: DEC-2026-02-12-013 - New pipeline checks are optional
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from src.core.config.risk_profiles import RiskProfileConfig, RiskProfileManager
from src.core.risk.checks import (check_concentration, check_daily_loss_limit,
                                  check_kill_switch, check_max_drawdown,
                                  check_max_positions, check_portfolio_correlation,
                                  check_position_size, check_weekly_loss_limit)
from src.core.risk.circuit_breakers import (CircuitBreakerManager,
                                            CircuitBreakerResult)
from src.core.risk.event_filter import EventFilter, EventFilterResult
from src.core.risk.kill_switch import KillSwitch
from src.core.risk.sizing import (apply_regime_adjustment, calculate_atr_size,
                                  calculate_available_capital,
                                  calculate_fixed_risk_size,
                                  calculate_kelly_size)
from src.core.risk.time_filter import TimeFilterResult, WeekendHolidayFilter
from src.core.risk.types import (OrderRequest, PortfolioState,
                                 PositionSizeResult, RiskCheckResult)
from src.core.risk.volatility import VolatilityAnalyzer, VolatilityResult
from src.data.store import DataStore
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RiskController:
    """Central risk management orchestrator.

    All orders flow through this controller before execution.
    Uses dependency injection for DataStore, RiskProfileManager,
    and optionally circuit breaker manager, volatility analyzer,
    time filter, and event filter.

    New components are optional (DEC-2026-02-12-013) to maintain
    backward compatibility with existing consumers and tests.

    Attributes:
        store: DataStore for database access.
        profile_manager: Manager for loading risk profiles.
        kill_switch: Kill switch instance.
        circuit_breaker_manager: Optional circuit breaker coordinator.
        volatility_analyzer: Optional volatility regime analyzer.
        time_filter: Optional weekend/holiday filter.
        event_filter: Optional event-based filter.
    """

    def __init__(
        self,
        store: DataStore,
        profile_manager: RiskProfileManager,
        symbol_manager: Any = None,
        circuit_breaker_manager: CircuitBreakerManager | None = None,
        volatility_analyzer: VolatilityAnalyzer | None = None,
        time_filter: WeekendHolidayFilter | None = None,
        event_filter: EventFilter | None = None,
    ) -> None:
        """Initialize the risk controller.

        Args:
            store: DataStore for database operations.
            profile_manager: RiskProfileManager for risk profiles.
            symbol_manager: Optional SymbolManager for symbol validation.
            circuit_breaker_manager: Optional CircuitBreakerManager.
            volatility_analyzer: Optional VolatilityAnalyzer.
            time_filter: Optional WeekendHolidayFilter.
            event_filter: Optional EventFilter.
        """
        self._store = store
        self._profile_manager = profile_manager
        self._symbol_manager = symbol_manager
        self.kill_switch = KillSwitch(store)
        self.circuit_breaker_manager = circuit_breaker_manager
        self.volatility_analyzer = volatility_analyzer
        self.time_filter = time_filter
        self.event_filter = event_filter

    def validate_order(
        self,
        request: OrderRequest,
        volatility_pct: float | None = None,
    ) -> list[RiskCheckResult]:
        """Run all risk checks on an order request.

        Pipeline order (STRICT - do NOT reorder existing checks):
        1. Kill switch (immediate rejection if active)
        2. Circuit breakers (if manager provided)
        3. Time filter (if filter provided)
        4. Event filter (if filter provided)
        5. Volatility filter (if analyzer provided)
        6. Daily loss limit
        7. Weekly loss limit
        8. Max drawdown
        9. Max positions
        10. Concentration
        11. Position size

        Returns on FIRST failure (fail-fast). On success, all
        checks pass and results for each are returned.

        Steps 2-5 are optional (DEC-2026-02-12-013). They only
        run when the corresponding component is injected.

        Args:
            request: Order request to validate.
            volatility_pct: Pre-computed ATR/price*100 for volatility
                check. Required if volatility_analyzer is set.

        Returns:
            List of RiskCheckResult objects. If any check fails,
            the list ends with the failing check.

        Raises:
            ValueError: If the order request contains invalid data.
        """
        # Validate input first
        self._validate_order_request(request)

        results: list[RiskCheckResult] = []

        # 1. Kill switch check (fastest - immediate rejection)
        system_state = self._store.get_system_state()
        ks_result = check_kill_switch(system_state)
        results.append(ks_result)
        if not ks_result.approved:
            logger.warning(
                "order_rejected_kill_switch",
                account_id=request.account_id,
                symbol=request.symbol,
            )
            return results

        # Build portfolio state and get risk profile
        portfolio = self.get_portfolio_state(request.account_id)
        profile = self._get_risk_profile(request.account_id)

        # 2. Circuit breaker check (if manager provided)
        if self.circuit_breaker_manager is not None:
            cb_results = self.circuit_breaker_manager.check_all(
                portfolio, profile
            )
            # Convert to RiskCheckResult for pipeline consistency
            for cb_result in cb_results:
                risk_result = _circuit_breaker_to_risk_result(cb_result)
                results.append(risk_result)
                if not risk_result.approved:
                    logger.warning(
                        "order_rejected_circuit_breaker",
                        account_id=request.account_id,
                        symbol=request.symbol,
                        breaker=cb_result.breaker_name,
                        reason=risk_result.rejection_reason,
                    )
                    return results

        # 3. Time filter check (if filter provided)
        if self.time_filter is not None:
            tf_result = self.time_filter.check()
            risk_result = _time_filter_to_risk_result(tf_result)
            results.append(risk_result)
            if not risk_result.approved:
                logger.warning(
                    "order_rejected_time_filter",
                    account_id=request.account_id,
                    symbol=request.symbol,
                    reason=risk_result.rejection_reason,
                )
                return results

        # 4. Event filter check (if filter provided)
        if self.event_filter is not None:
            ef_result = self.event_filter.check()
            risk_result = _event_filter_to_risk_result(ef_result)
            results.append(risk_result)
            if not risk_result.approved:
                logger.warning(
                    "order_rejected_event_filter",
                    account_id=request.account_id,
                    symbol=request.symbol,
                    reason=risk_result.rejection_reason,
                )
                return results

        # 5. Volatility filter check (if analyzer provided)
        if self.volatility_analyzer is not None and volatility_pct is not None:
            vol_result = self.volatility_analyzer.analyze(volatility_pct)
            risk_result = _volatility_to_risk_result(vol_result)
            results.append(risk_result)
            if not risk_result.approved:
                logger.warning(
                    "order_rejected_volatility",
                    account_id=request.account_id,
                    symbol=request.symbol,
                    regime=vol_result.regime.value,
                    reason=risk_result.rejection_reason,
                )
                return results

        # 6. Daily loss limit
        dl_result = check_daily_loss_limit(portfolio, profile)
        results.append(dl_result)
        if not dl_result.approved:
            logger.warning(
                "order_rejected_daily_loss",
                account_id=request.account_id,
                symbol=request.symbol,
                reason=dl_result.rejection_reason,
            )
            return results

        # 7. Weekly loss limit
        wl_result = check_weekly_loss_limit(portfolio, profile)
        results.append(wl_result)
        if not wl_result.approved:
            logger.warning(
                "order_rejected_weekly_loss",
                account_id=request.account_id,
                symbol=request.symbol,
                reason=wl_result.rejection_reason,
            )
            return results

        # 8. Max drawdown
        dd_result = check_max_drawdown(portfolio, profile)
        results.append(dd_result)
        if not dd_result.approved:
            logger.warning(
                "order_rejected_drawdown",
                account_id=request.account_id,
                symbol=request.symbol,
                reason=dd_result.rejection_reason,
            )
            return results

        # 9. Max positions
        mp_result = check_max_positions(request, portfolio, profile)
        results.append(mp_result)
        if not mp_result.approved:
            logger.warning(
                "order_rejected_max_positions",
                account_id=request.account_id,
                symbol=request.symbol,
                reason=mp_result.rejection_reason,
            )
            return results

        # 10. Concentration
        cc_result = check_concentration(request, portfolio, profile)
        results.append(cc_result)
        if not cc_result.approved:
            logger.warning(
                "order_rejected_concentration",
                account_id=request.account_id,
                symbol=request.symbol,
                reason=cc_result.rejection_reason,
            )
            return results

        # 11. Position size
        ps_result = check_position_size(request, portfolio, profile)
        results.append(ps_result)
        if not ps_result.approved:
            logger.warning(
                "order_rejected_position_size",
                account_id=request.account_id,
                symbol=request.symbol,
                reason=ps_result.rejection_reason,
            )
            return results

        # 12. Portfolio correlation limits (PRD §2.2.1 Feature A)
        # Cross-strategy check: total BTC<=40%, ETH<=30%, long<=60% of equity
        pc_result = check_portfolio_correlation(request, portfolio)
        results.append(pc_result)
        if not pc_result.approved:
            logger.warning(
                "order_rejected_portfolio_correlation",
                account_id=request.account_id,
                symbol=request.symbol,
                reason=pc_result.rejection_reason,
            )
            return results

        # All checks passed
        logger.info(
            "order_approved",
            account_id=request.account_id,
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            checks_passed=len(results),
        )

        return results

    def update_circuit_breakers(
        self,
        portfolio: PortfolioState,
        profile: RiskProfileConfig,
    ) -> list[CircuitBreakerResult]:
        """Evaluate all circuit breakers and persist state.

        Called periodically (e.g., after each trade or on a timer)
        to update circuit breaker states. Results are persisted
        to the database for recovery after restart.

        Args:
            portfolio: Current portfolio state snapshot.
            profile: Risk profile configuration.

        Returns:
            List of CircuitBreakerResult objects.
            Empty list if no circuit breaker manager is configured.
        """
        if self.circuit_breaker_manager is None:
            return []

        results = self.circuit_breaker_manager.check_all(portfolio, profile)
        self.circuit_breaker_manager.persist_state()

        triggered = self.circuit_breaker_manager.get_triggered()
        if triggered:
            logger.warning(
                "circuit_breakers_triggered",
                triggered=triggered,
                account_id=portfolio.account_id,
            )

        return results

    def calculate_position_size(
        self,
        account_id: str,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss_price: float,
        method: str = "fixed_risk",
        atr_value: float | None = None,
        win_rate: float | None = None,
        avg_win: float | None = None,
        avg_loss: float | None = None,
    ) -> PositionSizeResult:
        """Calculate risk-adjusted position size.

        Supports three methods:
        - "fixed_risk": Fixed percentage of equity at risk
        - "atr_based": Size based on ATR volatility
        - "kelly": Kelly Criterion probability-adjusted sizing

        After sizing, applies regime adjustment and caps to max
        position size limit.

        Args:
            account_id: Account identifier.
            symbol: Trading symbol (e.g., "BTCUSDT").
            side: Order side ("buy" or "sell").
            entry_price: Expected entry price.
            stop_loss_price: Stop loss price.
            method: Sizing method (default "fixed_risk").
            atr_value: ATR value (required for "atr_based").
            win_rate: Historical win rate (required for "kelly").
            avg_win: Average win amount (required for "kelly").
            avg_loss: Average loss amount (required for "kelly").

        Returns:
            PositionSizeResult with calculated quantity.

        Raises:
            ValueError: If inputs are invalid or required params missing.
        """
        # Validate stop loss placement
        if side == "buy" and stop_loss_price >= entry_price:
            raise ValueError(
                f"For BUY: stop_loss ({stop_loss_price}) "
                f"must be below entry ({entry_price})"
            )
        if side == "sell" and stop_loss_price <= entry_price:
            raise ValueError(
                f"For SELL: stop_loss ({stop_loss_price}) "
                f"must be above entry ({entry_price})"
            )

        # Get portfolio and profile
        portfolio = self.get_portfolio_state(account_id)
        profile = self._get_risk_profile(account_id)

        # Calculate available capital
        available = calculate_available_capital(portfolio)
        if available <= 0:
            return PositionSizeResult(
                quantity=0.0,
                notional_value=0.0,
                risk_amount=0.0,
                risk_pct=0.0,
                sizing_method=method,
                stop_loss_price=stop_loss_price,
                entry_price=entry_price,
                adjustments_applied=("no_available_capital",),
            )

        # Risk percentage from profile (convert from % to decimal)
        # Use max_position_size_pct as a conservative default risk per trade
        risk_pct = min(
            profile.max_position_size_pct / 100,
            0.02,  # Default 2% risk per trade
        )

        # Calculate size based on method
        result: PositionSizeResult
        if method == "atr_based":
            if atr_value is None or atr_value <= 0:
                raise ValueError(
                    "atr_value is required and must be positive "
                    "for atr_based sizing"
                )
            result = calculate_atr_size(
                capital=available,
                risk_pct=risk_pct,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                atr_value=atr_value,
                atr_multiplier=profile.volatility_multiplier or 2.0,
            )
        elif method == "kelly":
            if (
                win_rate is None
                or avg_win is None
                or avg_loss is None
            ):
                raise ValueError(
                    "win_rate, avg_win, and avg_loss are required "
                    "for kelly sizing"
                )
            result = calculate_kelly_size(
                capital=available,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
            )
        else:
            # Default: fixed_risk
            result = calculate_fixed_risk_size(
                capital=available,
                risk_pct=risk_pct,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
            )

        # Apply regime adjustment
        adjusted_qty, multiplier = apply_regime_adjustment(
            result.quantity, portfolio.regime, profile
        )

        # Cap to max position size
        max_position_value = (
            portfolio.total_equity * profile.max_position_size_pct / 100
        )
        adjusted_notional = adjusted_qty * entry_price
        adjustments = list(result.adjustments_applied)

        if adjusted_notional > max_position_value and entry_price > 0:
            adjusted_qty = max_position_value / entry_price
            adjusted_notional = adjusted_qty * entry_price
            adjustments.append("max_position_size_cap")

        if multiplier < 1.0:
            adjustments.append(f"regime_{portfolio.regime}")

        return PositionSizeResult(
            quantity=adjusted_qty,
            notional_value=adjusted_notional,
            risk_amount=result.risk_amount,
            risk_pct=result.risk_pct,
            sizing_method=result.sizing_method,
            stop_loss_price=stop_loss_price,
            entry_price=entry_price,
            adjustments_applied=tuple(adjustments),
            regime_multiplier=multiplier,
        )

    def get_portfolio_state(self, account_id: str) -> PortfolioState:
        """Build a PortfolioState snapshot from DataStore.

        Queries the account, open positions, and PnL records
        to construct an immutable portfolio state.

        Args:
            account_id: Account identifier.

        Returns:
            Frozen PortfolioState snapshot.

        Raises:
            ValueError: If account not found.
        """
        account = self._store.get_account(account_id)
        if account is None:
            raise ValueError(f"Account not found: {account_id}")

        # Get open positions
        open_positions = self._store.get_open_positions(account_id)

        # Calculate positions value
        positions_value = sum(
            pos.size * pos.current_price for pos in open_positions
        )

        # Get daily PnL
        today = datetime.now(timezone.utc).date()
        daily_pnl_record = self._store.get_pnl_for_date(
            account_id, today
        )
        daily_pnl = (
            daily_pnl_record.total_pnl if daily_pnl_record else 0.0
        )

        # Get weekly PnL (sum of this week's records)
        # Find Monday of current week
        monday = today - timedelta(days=today.weekday())
        weekly_records = self._store.get_pnl_history(
            account_id,
            start_date=monday,
            end_date=today,
        )
        weekly_pnl = sum(r.total_pnl for r in weekly_records)

        # Drawdown
        drawdown_pct = 0.0
        if daily_pnl_record and daily_pnl_record.drawdown_pct is not None:
            drawdown_pct = daily_pnl_record.drawdown_pct

        # Peak equity (use equity if no drawdown data)
        peak_equity = account.equity_usdt
        if drawdown_pct > 0:
            # peak = equity / (1 - drawdown/100)
            peak_equity = account.equity_usdt / (1 - drawdown_pct / 100)

        return PortfolioState(
            account_id=account_id,
            total_equity=account.equity_usdt,
            cash_balance=account.balance_usdt,
            positions_value=positions_value,
            open_positions=tuple(open_positions),
            daily_pnl=daily_pnl,
            weekly_pnl=weekly_pnl,
            drawdown_pct=drawdown_pct,
            peak_equity=peak_equity,
            regime=account.regime or "unknown",
        )

    def _get_risk_profile(self, account_id: str) -> RiskProfileConfig:
        """Resolve the risk profile for an account.

        Looks up the account's profile enum value and retrieves
        the corresponding RiskProfileConfig from the manager.

        Args:
            account_id: Account identifier.

        Returns:
            RiskProfileConfig for the account's risk profile.

        Raises:
            ValueError: If account not found or profile invalid.
        """
        account = self._store.get_account(account_id)
        if account is None:
            raise ValueError(f"Account not found: {account_id}")

        profile_name = account.profile.value
        return self._profile_manager.get_profile(profile_name)

    def _validate_order_request(self, request: OrderRequest) -> None:
        """Validate order request for NaN, Infinity, and invalid values.

        The OrderRequest dataclass already validates at creation,
        but this adds runtime checks for the controller pipeline.

        Args:
            request: Order request to validate.

        Raises:
            ValueError: If request contains invalid data.
        """
        if math.isnan(request.price) or math.isinf(request.price):
            raise ValueError(
                f"Order price must be finite, got {request.price}"
            )
        if request.price <= 0:
            raise ValueError(
                f"Order price must be positive, got {request.price}"
            )

        if math.isnan(request.quantity) or math.isinf(request.quantity):
            raise ValueError(
                f"Order quantity must be finite, got {request.quantity}"
            )
        if request.quantity <= 0:
            raise ValueError(
                f"Order quantity must be positive, got {request.quantity}"
            )


# ---------------------------------------------------------------------------
# Pipeline result conversion helpers
# ---------------------------------------------------------------------------


def _circuit_breaker_to_risk_result(
    cb_result: CircuitBreakerResult,
) -> RiskCheckResult:
    """Convert CircuitBreakerResult to standard RiskCheckResult.

    Args:
        cb_result: Circuit breaker evaluation result.

    Returns:
        RiskCheckResult for pipeline consistency.
    """
    check_name = f"circuit_breaker_{cb_result.breaker_name}"
    if cb_result.is_triggered:
        return RiskCheckResult(
            approved=False,
            check_name=check_name,
            rejection_reason=cb_result.message,
            checks_failed=(check_name,),
        )
    return RiskCheckResult(
        approved=True,
        check_name=check_name,
        checks_passed=(check_name,),
    )


def _time_filter_to_risk_result(
    tf_result: TimeFilterResult,
) -> RiskCheckResult:
    """Convert TimeFilterResult to standard RiskCheckResult.

    Args:
        tf_result: Time filter check result.

    Returns:
        RiskCheckResult for pipeline consistency.
    """
    check_name = f"time_filter_{tf_result.filter_name}"
    if not tf_result.is_tradeable:
        return RiskCheckResult(
            approved=False,
            check_name=check_name,
            rejection_reason=tf_result.reason,
            checks_failed=(check_name,),
        )
    return RiskCheckResult(
        approved=True,
        check_name=check_name,
        checks_passed=(check_name,),
    )


def _event_filter_to_risk_result(
    ef_result: EventFilterResult,
) -> RiskCheckResult:
    """Convert EventFilterResult to standard RiskCheckResult.

    Args:
        ef_result: Event filter check result.

    Returns:
        RiskCheckResult for pipeline consistency.
    """
    check_name = f"event_filter_{ef_result.filter_name}"
    if not ef_result.is_tradeable:
        return RiskCheckResult(
            approved=False,
            check_name=check_name,
            rejection_reason=ef_result.reason,
            checks_failed=(check_name,),
        )
    return RiskCheckResult(
        approved=True,
        check_name=check_name,
        checks_passed=(check_name,),
    )


def _volatility_to_risk_result(
    vol_result: VolatilityResult,
) -> RiskCheckResult:
    """Convert VolatilityResult to standard RiskCheckResult.

    Args:
        vol_result: Volatility analysis result.

    Returns:
        RiskCheckResult for pipeline consistency.
    """
    check_name = "volatility_filter"
    if not vol_result.is_tradeable:
        return RiskCheckResult(
            approved=False,
            check_name=check_name,
            rejection_reason=vol_result.message,
            checks_failed=(check_name,),
        )
    return RiskCheckResult(
        approved=True,
        check_name=check_name,
        checks_passed=(check_name,),
    )
