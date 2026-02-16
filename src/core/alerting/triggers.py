"""Alert triggers for system events.

Connects system events to the alerting system with appropriate severity levels.
Each trigger method maps a specific event to an alert, routing it through
AlertManager with relevant context metadata.

Alert Level Mapping:
- INFO: Normal operations (order filled, system start/stop)
- WARNING: Performance issues, approaching limits (drawdown, daily loss, strategy underperformance)
- ERROR: Integration failures, protective mechanisms (exchange errors, circuit breakers)
- CRITICAL: Emergency situations (kill switch activation)

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.utils.logging import get_logger

if TYPE_CHECKING:
    from src.core.alerting.manager import AlertManager

logger = get_logger(__name__)


class AlertTriggers:
    """Connects system events to alerting system.

    Provides convenience methods for triggering alerts from various system
    events. Each method calls the appropriate AlertManager method (send_info,
    send_warning, send_error, send_critical) with relevant context.

    Attributes:
        alert_manager: AlertManager instance for sending alerts.
    """

    def __init__(self, alert_manager: "AlertManager") -> None:
        """Initialize alert triggers.

        Args:
            alert_manager: AlertManager instance for sending alerts.
        """
        self._alert_manager = alert_manager
        logger.info("alert_triggers_initialized")

    async def on_order_filled(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        **metadata: Any,
    ) -> None:
        """Trigger alert when order is filled.

        Args:
            order_id: Order ID.
            symbol: Trading symbol.
            side: Order side (BUY/SELL).
            quantity: Fill quantity.
            price: Fill price.
            **metadata: Additional context (strategy_id, account_id, etc.).
        """
        await self._alert_manager.send_info(
            title="Order Filled",
            message=f"{side} {quantity} {symbol} @ {price}",
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            **metadata,
        )

    async def on_order_rejected(
        self,
        order_id: str,
        symbol: str,
        reason: str,
        **metadata: Any,
    ) -> None:
        """Trigger alert when order is rejected by risk or exchange.

        Args:
            order_id: Order ID.
            symbol: Trading symbol.
            reason: Rejection reason.
            **metadata: Additional context (risk_check, account_id, etc.).
        """
        await self._alert_manager.send_warning(
            title="Order Rejected",
            message=f"Order {order_id} for {symbol} rejected: {reason}",
            order_id=order_id,
            symbol=symbol,
            reason=reason,
            **metadata,
        )

    async def on_daily_loss_warning(
        self,
        current_loss_pct: float,
        limit_pct: float,
        account_id: str,
        **metadata: Any,
    ) -> None:
        """Trigger alert when approaching daily loss limit.

        Args:
            current_loss_pct: Current daily loss percentage.
            limit_pct: Daily loss limit percentage.
            account_id: Account ID.
            **metadata: Additional context.
        """
        await self._alert_manager.send_warning(
            title="Daily Loss Warning",
            message=(
                f"Daily loss {current_loss_pct:.2f}% approaching "
                f"limit {limit_pct:.1f}%"
            ),
            current_loss_pct=current_loss_pct,
            limit_pct=limit_pct,
            account_id=account_id,
            **metadata,
        )

    async def on_drawdown_warning(
        self,
        current_drawdown_pct: float,
        limit_pct: float,
        account_id: str,
        **metadata: Any,
    ) -> None:
        """Trigger alert when approaching drawdown limit.

        Args:
            current_drawdown_pct: Current drawdown percentage.
            limit_pct: Drawdown limit percentage.
            account_id: Account ID.
            **metadata: Additional context.
        """
        await self._alert_manager.send_warning(
            title="Drawdown Warning",
            message=(
                f"Drawdown {current_drawdown_pct:.2f}% approaching "
                f"limit {limit_pct:.1f}%"
            ),
            current_drawdown_pct=current_drawdown_pct,
            limit_pct=limit_pct,
            account_id=account_id,
            **metadata,
        )

    async def on_kill_switch_activated(
        self,
        reason: str,
        actor: str = "system",
        **metadata: Any,
    ) -> None:
        """Trigger CRITICAL alert when kill switch is activated.

        Args:
            reason: Why kill switch was activated.
            actor: Who/what activated it (system, user, etc.).
            **metadata: Additional context.
        """
        await self._alert_manager.send_critical(
            title="Kill Switch Activated",
            message=f"Trading halted: {reason}",
            reason=reason,
            actor=actor,
            **metadata,
        )

    async def on_circuit_breaker_triggered(
        self,
        breaker_type: str,
        symbol: str | None = None,
        **metadata: Any,
    ) -> None:
        """Trigger ERROR alert when circuit breaker is triggered.

        Args:
            breaker_type: Type of circuit breaker (volatility, volume, spread).
            symbol: Symbol affected (if applicable).
            **metadata: Additional context.
        """
        message = f"Circuit breaker triggered: {breaker_type}"
        if symbol:
            message += f" for {symbol}"

        await self._alert_manager.send_error(
            title="Circuit Breaker Triggered",
            message=message,
            breaker_type=breaker_type,
            symbol=symbol,
            **metadata,
        )

    async def on_strategy_underperforming(
        self,
        strategy_id: str,
        metric: str,
        current_value: float,
        threshold: float,
        **metadata: Any,
    ) -> None:
        """Trigger WARNING alert when strategy is underperforming.

        Args:
            strategy_id: Strategy ID.
            metric: Performance metric (win_rate, sharpe_ratio, etc.).
            current_value: Current metric value.
            threshold: Threshold value.
            **metadata: Additional context.
        """
        await self._alert_manager.send_warning(
            title="Strategy Underperforming",
            message=(
                f"Strategy {strategy_id} {metric} {current_value:.2f} "
                f"below threshold {threshold:.2f}"
            ),
            strategy_id=strategy_id,
            metric=metric,
            current_value=current_value,
            threshold=threshold,
            **metadata,
        )

    async def on_exchange_api_error(
        self,
        exchange: str,
        error_type: str,
        error_message: str,
        **metadata: Any,
    ) -> None:
        """Trigger ERROR alert when exchange API fails.

        Args:
            exchange: Exchange name (Binance).
            error_type: Error type (timeout, auth, rate_limit, etc.).
            error_message: Error message.
            **metadata: Additional context.
        """
        await self._alert_manager.send_error(
            title="Exchange API Error",
            message=f"{exchange} API error ({error_type}): {error_message}",
            exchange=exchange,
            error_type=error_type,
            error_message=error_message,
            **metadata,
        )

    async def on_system_started(
        self,
        version: str = "1.0.0",
        **metadata: Any,
    ) -> None:
        """Trigger INFO alert when system starts.

        Args:
            version: System version.
            **metadata: Additional context (strategies_loaded, accounts_active, etc.).
        """
        await self._alert_manager.send_info(
            title="System Started",
            message=f"PARAVANT Trading System v{version} started successfully",
            version=version,
            **metadata,
        )

    async def on_system_stopped(
        self,
        graceful: bool = True,
        reason: str | None = None,
        **metadata: Any,
    ) -> None:
        """Trigger alert when system stops.

        Sends INFO for graceful shutdown, WARNING for unexpected shutdown.

        Args:
            graceful: Whether shutdown was graceful.
            reason: Shutdown reason (if applicable).
            **metadata: Additional context (uptime_seconds, trades_today, etc.).
        """
        message = "System stopped"
        if reason:
            message += f": {reason}"

        if graceful:
            await self._alert_manager.send_info(
                title="System Stopped",
                message=message,
                graceful=graceful,
                reason=reason,
                **metadata,
            )
        else:
            await self._alert_manager.send_warning(
                title="System Stopped Unexpectedly",
                message=message,
                graceful=graceful,
                reason=reason,
                **metadata,
            )

    async def on_position_sync_mismatch(
        self,
        symbol: str,
        local_qty: float,
        exchange_qty: float,
        **metadata: Any,
    ) -> None:
        """Trigger ERROR alert when position sync detects mismatch.

        Args:
            symbol: Trading symbol.
            local_qty: Local position quantity.
            exchange_qty: Exchange position quantity.
            **metadata: Additional context.
        """
        await self._alert_manager.send_error(
            title="Position Sync Mismatch",
            message=(
                f"Position mismatch for {symbol}: "
                f"local={local_qty}, exchange={exchange_qty}"
            ),
            symbol=symbol,
            local_qty=local_qty,
            exchange_qty=exchange_qty,
            **metadata,
        )

    async def on_risk_limit_breached(
        self,
        limit_type: str,
        current_value: float,
        limit_value: float,
        **metadata: Any,
    ) -> None:
        """Trigger ERROR alert when risk limit is breached.

        Args:
            limit_type: Type of limit (position_size, daily_loss, drawdown, etc.).
            current_value: Current value.
            limit_value: Limit value.
            **metadata: Additional context.
        """
        await self._alert_manager.send_error(
            title="Risk Limit Breached",
            message=(
                f"{limit_type} limit breached: "
                f"current={current_value:.2f}, limit={limit_value:.2f}"
            ),
            limit_type=limit_type,
            current_value=current_value,
            limit_value=limit_value,
            **metadata,
        )

    async def on_health_check_failed(
        self,
        check_name: str,
        reason: str,
        **metadata: Any,
    ) -> None:
        """Trigger WARNING alert when health check fails.

        Args:
            check_name: Name of failed health check.
            reason: Failure reason.
            **metadata: Additional context.
        """
        await self._alert_manager.send_warning(
            title="Health Check Failed",
            message=f"{check_name} health check failed: {reason}",
            check_name=check_name,
            reason=reason,
            **metadata,
        )

    async def on_degradation_mode_entered(
        self,
        mode: str,
        reason: str,
        **metadata: Any,
    ) -> None:
        """Trigger WARNING alert when system enters degradation mode.

        Args:
            mode: Degradation mode (read_only, cache_only, etc.).
            reason: Why degradation mode was entered.
            **metadata: Additional context.
        """
        await self._alert_manager.send_warning(
            title="Degradation Mode Entered",
            message=f"System entered {mode} mode: {reason}",
            mode=mode,
            reason=reason,
            **metadata,
        )

    async def on_degradation_mode_recovered(
        self,
        mode: str,
        duration_seconds: float,
        **metadata: Any,
    ) -> None:
        """Trigger INFO alert when system recovers from degradation.

        Args:
            mode: Degradation mode recovered from.
            duration_seconds: Duration in degradation mode.
            **metadata: Additional context.
        """
        await self._alert_manager.send_info(
            title="Degradation Mode Recovered",
            message=(
                f"System recovered from {mode} mode "
                f"after {duration_seconds:.1f}s"
            ),
            mode=mode,
            duration_seconds=duration_seconds,
            **metadata,
        )
