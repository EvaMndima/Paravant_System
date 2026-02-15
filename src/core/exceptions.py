"""Custom exception hierarchy for the PARAVANT Trading System.

Provides a structured exception tree where each exception carries a
machine-readable error code, a human-readable message, and an optional
details dictionary for API response serialization.

Exception Hierarchy::

    TradingSystemError (base)
    +-- RiskError
    |   +-- PositionSizeLimitError
    |   +-- DailyLossLimitError
    |   +-- DrawdownLimitError
    |   +-- KillSwitchActiveError
    +-- ExecutionError
    |   +-- OrderRejectedError
    |   +-- InsufficientBalanceError
    |   +-- BrokerConnectionError
    +-- StrategyError
    |   +-- TemplateNotFoundError
    |   +-- InvalidParametersError
    |   +-- BacktestError
    |   +-- PaperTradingError
    |   +-- InvalidStatusTransitionError
    |   +-- RegimeError
    |   +-- SignalGenerationError
    +-- DataError
    |   +-- MarketDataError
    |   +-- SymbolNotFoundError
    +-- ConfigurationError
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Base Exception
# ---------------------------------------------------------------------------


class TradingSystemError(Exception):
    """Base exception for all PARAVANT Trading System errors.

    Every exception in the system carries a machine-readable ``code``,
    a human-readable ``message``, and an optional ``details`` dictionary
    that is included in API error responses.

    Attributes:
        message: Human-readable error description.
        code: Machine-readable error code (uppercase, underscore-separated).
        details: Additional context about the error.
    """

    def __init__(
        self,
        message: str,
        code: str = "TRADING_SYSTEM_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the trading system error.

        Args:
            message: Human-readable error description.
            code: Machine-readable error code.
            details: Optional dictionary with error context.

        Raises:
            ValueError: If message is empty or whitespace-only.
        """
        # MEDIUM-008: Validate message is non-empty for useful error logs
        if not message or not message.strip():
            raise ValueError("Exception message cannot be empty")

        self.message = message
        self.code = code
        self.details: dict[str, Any] = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Serialize exception to a dictionary for API responses.

        Returns:
            Dictionary with ``error`` key containing code, message,
            and details.
        """
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


# ---------------------------------------------------------------------------
# Risk Errors
# ---------------------------------------------------------------------------


class RiskError(TradingSystemError):
    """Base class for risk management errors.

    Raised when a trading action would violate risk management rules.
    """

    def __init__(
        self,
        message: str,
        code: str = "RISK_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class PositionSizeLimitError(RiskError):
    """Raised when requested position size exceeds the maximum allowed.

    Attributes:
        requested_size_pct: The requested position size percentage.
        max_allowed_pct: The maximum allowed position size percentage.
    """

    def __init__(
        self, requested_size_pct: float, max_allowed_pct: float
    ) -> None:
        super().__init__(
            message=(
                f"Position size {requested_size_pct:.1f}% exceeds "
                f"maximum allowed {max_allowed_pct:.1f}%"
            ),
            code="POSITION_SIZE_LIMIT",
            details={
                "requested_size_pct": requested_size_pct,
                "max_allowed_pct": max_allowed_pct,
            },
        )


class DailyLossLimitError(RiskError):
    """Raised when the daily loss limit has been reached.

    Attributes:
        current_loss_pct: The current daily loss percentage.
        limit_pct: The daily loss limit percentage.
    """

    def __init__(self, current_loss_pct: float, limit_pct: float) -> None:
        super().__init__(
            message=(
                f"Daily loss limit reached: {current_loss_pct:.1f}% "
                f"(limit: {limit_pct:.1f}%)"
            ),
            code="DAILY_LOSS_LIMIT",
            details={
                "current_loss_pct": current_loss_pct,
                "limit_pct": limit_pct,
            },
        )


class DrawdownLimitError(RiskError):
    """Raised when maximum drawdown limit has been breached.

    Attributes:
        current_drawdown_pct: The current portfolio drawdown percentage.
        limit_pct: The maximum drawdown limit percentage.
    """

    def __init__(
        self, current_drawdown_pct: float, limit_pct: float
    ) -> None:
        super().__init__(
            message=(
                f"Maximum drawdown breached: {current_drawdown_pct:.1f}% "
                f"(limit: {limit_pct:.1f}%)"
            ),
            code="DRAWDOWN_LIMIT",
            details={
                "current_drawdown_pct": current_drawdown_pct,
                "limit_pct": limit_pct,
            },
        )


class KillSwitchActiveError(RiskError):
    """Raised when the kill switch is active and trading is halted.

    Attributes:
        reason: The reason the kill switch was activated.
    """

    def __init__(self, reason: str = "Kill switch is active") -> None:
        super().__init__(
            message=f"Trading halted: {reason}",
            code="KILL_SWITCH_ACTIVE",
            details={"reason": reason},
        )


# ---------------------------------------------------------------------------
# Execution Errors
# ---------------------------------------------------------------------------


class ExecutionError(TradingSystemError):
    """Base class for order execution errors.

    Raised when an order cannot be placed, filled, or processed.
    """

    def __init__(
        self,
        message: str,
        code: str = "EXECUTION_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class OrderRejectedError(ExecutionError):
    """Raised when an order is rejected by the exchange.

    Attributes:
        order_id: The rejected order identifier.
        reason: Rejection reason from the exchange.
    """

    def __init__(
        self, order_id: str = "", reason: str = "Order rejected"
    ) -> None:
        super().__init__(
            message=f"Order rejected: {reason}",
            code="ORDER_REJECTED",
            details={"order_id": order_id, "reason": reason},
        )


class InsufficientBalanceError(ExecutionError):
    """Raised when account balance is insufficient for the order.

    Attributes:
        required: The required balance amount.
        available: The available balance amount.
        currency: The currency denomination.
    """

    def __init__(
        self,
        required: float,
        available: float,
        currency: str = "USDT",
    ) -> None:
        super().__init__(
            message=(
                f"Insufficient balance: need {required:.2f} {currency}, "
                f"have {available:.2f} {currency}"
            ),
            code="INSUFFICIENT_BALANCE",
            details={
                "required": required,
                "available": available,
                "currency": currency,
            },
        )


class BrokerConnectionError(ExecutionError):
    """Raised when connection to the broker/exchange fails.

    Attributes:
        broker: The broker name that failed.
        reason: Connection failure reason.
    """


    def __init__(
        self,
        broker: str = "binance",
        reason: str = "Connection failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = {"broker": broker, "reason": reason}
        if details:
            error_details.update(details)

        super().__init__(
            message=f"Broker connection error ({broker}): {reason}",
            code="BROKER_CONNECTION_ERROR",
            details=error_details,
        )


class OrderSubmissionError(ExecutionError):
    """Raised when order submission to the exchange fails.

    Attributes:
        order_id: The internal order identifier.
        symbol: The trading pair symbol.
        reason: Submission failure reason from the exchange.
    """

    def __init__(
        self,
        order_id: str = "",
        symbol: str = "",
        reason: str = "Order submission failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = {
            "order_id": order_id,
            "symbol": symbol,
            "reason": reason,
        }
        if details:
            error_details.update(details)

        super().__init__(
            message=f"Order submission failed for {symbol}: {reason}",
            code="ORDER_SUBMISSION_ERROR",
            details=error_details,
        )


class OrderNotFoundError(ExecutionError):
    """Raised when an order cannot be found by ID.

    Attributes:
        order_id: The order identifier that was not found.
    """

    def __init__(
        self,
        order_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = {"order_id": order_id}
        if details:
            error_details.update(details)

        super().__init__(
            message=f"Order not found: {order_id}",
            code="ORDER_NOT_FOUND",
            details=error_details,
        )


class OrderTimeoutError(ExecutionError):
    """Raised when order monitoring exceeds the maximum timeout.

    Attributes:
        order_id: The order that timed out.
        timeout_seconds: The timeout threshold that was exceeded.
    """

    def __init__(
        self,
        order_id: str,
        timeout_seconds: int = 1800,
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = {
            "order_id": order_id,
            "timeout_seconds": timeout_seconds,
        }
        if details:
            error_details.update(details)

        super().__init__(
            message=(
                f"Order {order_id} timed out after "
                f"{timeout_seconds}s"
            ),
            code="ORDER_TIMEOUT",
            details=error_details,
        )


class PositionNotFoundError(ExecutionError):
    """Raised when a position cannot be found by symbol or ID.

    Attributes:
        symbol: The symbol or ID that was not found.
    """

    def __init__(
        self,
        symbol: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = {"symbol": symbol}
        if details:
            error_details.update(details)

        super().__init__(
            message=f"Position not found: {symbol}",
            code="POSITION_NOT_FOUND",
            details=error_details,
        )


class PositionStorageError(ExecutionError):
    """Raised when a position cannot be saved or updated in the database.

    Attributes:
        position_id: The position that failed to persist.
        reason: Storage failure reason.
    """

    def __init__(
        self,
        position_id: str = "",
        reason: str = "Position storage failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = {
            "position_id": position_id,
            "reason": reason,
        }
        if details:
            error_details.update(details)

        super().__init__(
            message=f"Position storage error for {position_id}: {reason}",
            code="POSITION_STORAGE_ERROR",
            details=error_details,
        )


class InvalidStateTransitionError(ExecutionError):
    """Raised when an order state transition violates the state machine.

    The order state machine is strictly one-way:
    PENDING -> SUBMITTED -> PARTIALLY_FILLED -> FILLED
    PENDING -> SUBMITTED -> CANCELLED
    PENDING -> REJECTED

    Attributes:
        order_id: The order with the invalid transition.
        current_status: The current order status.
        requested_status: The requested (invalid) status.
    """

    def __init__(
        self,
        order_id: str,
        current_status: str,
        requested_status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = {
            "order_id": order_id,
            "current_status": current_status,
            "requested_status": requested_status,
        }
        if details:
            error_details.update(details)

        super().__init__(
            message=(
                f"Invalid state transition for order {order_id}: "
                f"{current_status} -> {requested_status}"
            ),
            code="INVALID_STATE_TRANSITION",
            details=error_details,
        )


# ---------------------------------------------------------------------------
# Strategy Errors
# ---------------------------------------------------------------------------


class StrategyError(TradingSystemError):
    """Base class for strategy-related errors.

    Raised when strategy configuration, parameters, or execution fails.
    """

    def __init__(
        self,
        message: str,
        code: str = "STRATEGY_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class TemplateNotFoundError(StrategyError):
    """Raised when a referenced strategy template does not exist.

    Attributes:
        template_id: The missing template identifier.
    """

    def __init__(self, template_id: str) -> None:
        super().__init__(
            message=f"Strategy template not found: {template_id}",
            code="TEMPLATE_NOT_FOUND",
            details={"template_id": template_id},
        )


class InvalidParametersError(StrategyError):
    """Raised when strategy parameters fail validation.

    Attributes:
        errors: List of validation error messages.
        template_id: The template the parameters were validated against.
    """

    def __init__(
        self, errors: list[str], template_id: str = ""
    ) -> None:
        super().__init__(
            message=f"Invalid strategy parameters: {'; '.join(errors)}",
            code="INVALID_PARAMETERS",
            details={
                "template_id": template_id,
                "errors": errors,
            },
        )


class BacktestError(StrategyError):
    """Raised when a backtest operation fails.

    Attributes:
        strategy_id: The strategy that failed backtesting.
        reason: Backtest failure reason.
    """

    def __init__(
        self, strategy_id: str = "", reason: str = "Backtest failed"
    ) -> None:
        super().__init__(
            message=f"Backtest error: {reason}",
            code="BACKTEST_ERROR",
            details={
                "strategy_id": strategy_id,
                "reason": reason,
            },
        )


class PaperTradingError(StrategyError):
    """Raised when a paper trading operation fails.

    Attributes:
        strategy_id: The strategy that failed paper trading.
        reason: Paper trading failure reason.
    """

    def __init__(
        self, strategy_id: str = "", reason: str = "Paper trading failed"
    ) -> None:
        super().__init__(
            message=f"Paper trading error: {reason}",
            code="PAPER_TRADING_ERROR",
            details={
                "strategy_id": strategy_id,
                "reason": reason,
            },
        )


class InvalidStatusTransitionError(StrategyError):
    """Raised when a strategy status transition violates the state machine.

    The strategy lifecycle state machine enforces valid transitions:
    DRAFT -> BACKTEST -> SIMULATED_PAPER -> LIVE_PAPER -> PENDING_APPROVAL -> LIVE
    With lateral transitions: LIVE -> PAUSED, UNDERPERFORMING, RETIRED

    Attributes:
        strategy_id: The strategy with the invalid transition.
        current_status: The current strategy status.
        requested_status: The requested (invalid) status.
    """

    def __init__(
        self,
        strategy_id: str,
        current_status: str,
        requested_status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = {
            "strategy_id": strategy_id,
            "current_status": current_status,
            "requested_status": requested_status,
        }
        if details:
            error_details.update(details)

        super().__init__(
            message=(
                f"Invalid status transition for strategy {strategy_id}: "
                f"{current_status} -> {requested_status}"
            ),
            code="INVALID_STATUS_TRANSITION",
            details=error_details,
        )


class RegimeError(StrategyError):
    """Raised when market regime operations fail.

    Attributes:
        symbol: The symbol associated with the regime error.
        reason: Failure reason.
    """

    def __init__(
        self,
        symbol: str = "",
        reason: str = "Regime operation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = {"symbol": symbol, "reason": reason}
        if details:
            error_details.update(details)

        super().__init__(
            message=f"Regime error for {symbol}: {reason}",
            code="REGIME_ERROR",
            details=error_details,
        )


class SignalGenerationError(StrategyError):
    """Raised when signal generation fails.

    Attributes:
        strategy_id: The strategy that failed signal generation.
        template_id: The template used for signal generation.
        reason: Failure reason.
    """

    def __init__(
        self,
        strategy_id: str = "",
        template_id: str = "",
        reason: str = "Signal generation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = {
            "strategy_id": strategy_id,
            "template_id": template_id,
            "reason": reason,
        }
        if details:
            error_details.update(details)

        super().__init__(
            message=f"Signal generation error: {reason}",
            code="SIGNAL_GENERATION_ERROR",
            details=error_details,
        )


# ---------------------------------------------------------------------------
# Data Errors
# ---------------------------------------------------------------------------


class DataError(TradingSystemError):
    """Base class for data access and integrity errors.

    Raised when market data is unavailable, corrupt, or invalid.
    """

    def __init__(
        self,
        message: str,
        code: str = "DATA_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class MarketDataError(DataError):
    """Raised when market data cannot be fetched or is invalid.

    Attributes:
        symbol: The affected trading symbol.
        reason: Failure reason.
    """

    def __init__(
        self,
        symbol: str = "",
        reason: str = "Market data unavailable",
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = {"symbol": symbol, "reason": reason}
        if details:
            error_details.update(details)

        super().__init__(
            message=f"Market data error for {symbol}: {reason}",
            code="MARKET_DATA_ERROR",
            details=error_details,
        )


class SymbolNotFoundError(DataError):
    """Raised when a requested trading symbol does not exist.

    Attributes:
        symbol: The missing symbol string.
    """

    def __init__(self, symbol: str) -> None:
        super().__init__(
            message=f"Symbol not found: {symbol}",
            code="SYMBOL_NOT_FOUND",
            details={"symbol": symbol},
        )


# ---------------------------------------------------------------------------
# Configuration Errors
# ---------------------------------------------------------------------------


class ConfigurationError(TradingSystemError):
    """Raised when system configuration is invalid or missing.

    Attributes:
        config_key: The configuration key that caused the error.
        reason: Why the configuration is invalid.
    """

    def __init__(
        self,
        message: str = "Configuration error",
        code: str = "CONFIGURATION_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


# ---------------------------------------------------------------------------
# Exception code registry (for uniqueness verification)
# ---------------------------------------------------------------------------

# All exception classes in the hierarchy
ALL_EXCEPTION_CLASSES: list[type[TradingSystemError]] = [
    TradingSystemError,
    RiskError,
    PositionSizeLimitError,
    DailyLossLimitError,
    DrawdownLimitError,
    KillSwitchActiveError,
    ExecutionError,
    OrderRejectedError,
    InsufficientBalanceError,
    BrokerConnectionError,
    OrderSubmissionError,
    OrderNotFoundError,
    OrderTimeoutError,
    PositionNotFoundError,
    PositionStorageError,
    InvalidStateTransitionError,
    StrategyError,
    TemplateNotFoundError,
    InvalidParametersError,
    BacktestError,
    PaperTradingError,
    InvalidStatusTransitionError,
    RegimeError,
    SignalGenerationError,
    DataError,
    MarketDataError,
    SymbolNotFoundError,
    ConfigurationError,
]
