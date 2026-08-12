"""Unit tests for custom exceptions and health check system (Section 1.4).

Tests cover:
- Exception hierarchy and inheritance
- Exception serialization (to_dict)
- Error code uniqueness
- Context preservation in exception details
- Health checker registration and execution
- Overall status computation
- Latency tracking

Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from src.core.exceptions import (
    ALL_EXCEPTION_CLASSES,
    BacktestError,
    BrokerConnectionError,
    ConfigurationError,
    DailyLossLimitError,
    DataError,
    DrawdownLimitError,
    ExecutionError,
    InsufficientBalanceError,
    InvalidParametersError,
    KillSwitchActiveError,
    MarketDataError,
    OrderRejectedError,
    PositionSizeLimitError,
    RiskError,
    StrategyError,
    SymbolNotFoundError,
    TemplateNotFoundError,
    TradingSystemError,
)
from src.core.health import (
    ComponentHealth,
    HealthChecker,
    HealthStatus,
    SystemHealth,
)


# =========================================================================
# TestExceptionHierarchy
# =========================================================================


class TestExceptionHierarchy:
    """Test suite for exception class hierarchy and inheritance."""

    def test_all_exceptions_inherit_from_base(self) -> None:
        """Every exception class should inherit from TradingSystemError."""
        for exc_class in ALL_EXCEPTION_CLASSES:
            assert issubclass(exc_class, TradingSystemError), (
                f"{exc_class.__name__} does not inherit from TradingSystemError"
            )

    def test_risk_errors_inherit_from_risk_error(self) -> None:
        """Risk-related exceptions should inherit from RiskError."""
        risk_classes = [
            PositionSizeLimitError,
            DailyLossLimitError,
            DrawdownLimitError,
            KillSwitchActiveError,
        ]
        for cls in risk_classes:
            assert issubclass(cls, RiskError)
            assert issubclass(cls, TradingSystemError)

    def test_execution_errors_inherit_from_execution_error(self) -> None:
        """Execution exceptions should inherit from ExecutionError."""
        exec_classes = [
            OrderRejectedError,
            InsufficientBalanceError,
            BrokerConnectionError,
        ]
        for cls in exec_classes:
            assert issubclass(cls, ExecutionError)

    def test_strategy_errors_inherit_from_strategy_error(self) -> None:
        """Strategy exceptions should inherit from StrategyError."""
        strat_classes = [
            TemplateNotFoundError,
            InvalidParametersError,
            BacktestError,
        ]
        for cls in strat_classes:
            assert issubclass(cls, StrategyError)

    def test_data_errors_inherit_from_data_error(self) -> None:
        """Data exceptions should inherit from DataError."""
        data_classes = [MarketDataError, SymbolNotFoundError]
        for cls in data_classes:
            assert issubclass(cls, DataError)

    def test_all_exceptions_are_catchable_as_exception(self) -> None:
        """All custom exceptions should be catchable as standard Exception."""
        for exc_class in ALL_EXCEPTION_CLASSES:
            assert issubclass(exc_class, Exception)


# =========================================================================
# TestExceptionSerialization
# =========================================================================


class TestExceptionSerialization:
    """Test suite for exception to_dict() serialization."""

    def test_base_exception_to_dict(self) -> None:
        """TradingSystemError.to_dict() should produce valid structure."""
        exc = TradingSystemError(
            message="Test error",
            code="TEST_ERROR",
            details={"key": "value"},
        )
        result = exc.to_dict()
        assert "error" in result
        assert result["error"]["code"] == "TEST_ERROR"
        assert result["error"]["message"] == "Test error"
        assert result["error"]["details"]["key"] == "value"

    def test_position_size_limit_serialization(self) -> None:
        """PositionSizeLimitError should serialize with correct details."""
        exc = PositionSizeLimitError(
            requested_size_pct=8.5,
            max_allowed_pct=5.0,
        )
        result = exc.to_dict()
        assert result["error"]["code"] == "POSITION_SIZE_LIMIT"
        assert result["error"]["details"]["requested_size_pct"] == 8.5
        assert result["error"]["details"]["max_allowed_pct"] == 5.0

    def test_daily_loss_limit_serialization(self) -> None:
        """DailyLossLimitError should include loss details."""
        exc = DailyLossLimitError(current_loss_pct=3.5, limit_pct=3.0)
        result = exc.to_dict()
        assert result["error"]["code"] == "DAILY_LOSS_LIMIT"
        assert result["error"]["details"]["current_loss_pct"] == 3.5

    def test_insufficient_balance_serialization(self) -> None:
        """InsufficientBalanceError should include balance details."""
        exc = InsufficientBalanceError(
            required=1000.0,
            available=500.0,
            currency="USDT",
        )
        result = exc.to_dict()
        assert result["error"]["code"] == "INSUFFICIENT_BALANCE"
        assert result["error"]["details"]["required"] == 1000.0
        assert result["error"]["details"]["available"] == 500.0
        assert result["error"]["details"]["currency"] == "USDT"

    def test_invalid_parameters_serialization(self) -> None:
        """InvalidParametersError should include the list of errors."""
        exc = InvalidParametersError(
            errors=["param1 out of range", "param2 missing"],
            template_id="ema_trend_rsi",
        )
        result = exc.to_dict()
        assert result["error"]["code"] == "INVALID_PARAMETERS"
        assert len(result["error"]["details"]["errors"]) == 2


# =========================================================================
# TestExceptionCodes
# =========================================================================


class TestExceptionCodes:
    """Test suite for error code uniqueness."""

    def test_exception_codes_are_unique(self) -> None:
        """Each leaf exception should have a unique error code."""
        # Instantiate each exception to get its code
        instances = [
            TradingSystemError("test", "TRADING_SYSTEM_ERROR"),
            RiskError("test", "RISK_ERROR"),
            PositionSizeLimitError(5.0, 3.0),
            DailyLossLimitError(3.0, 2.0),
            DrawdownLimitError(15.0, 12.0),
            KillSwitchActiveError(),
            ExecutionError("test", "EXECUTION_ERROR"),
            OrderRejectedError(),
            InsufficientBalanceError(100, 50),
            BrokerConnectionError(),
            StrategyError("test", "STRATEGY_ERROR"),
            TemplateNotFoundError("test"),
            InvalidParametersError(["err"]),
            BacktestError(),
            DataError("test", "DATA_ERROR"),
            MarketDataError("BTCUSDT"),
            SymbolNotFoundError("INVALID"),
            ConfigurationError(),
        ]

        _codes = [exc.code for exc in instances]
        # Check for uniqueness (excluding base class codes that are intentionally reused)
        leaf_codes = [
            exc.code for exc in instances
            if type(exc) not in (
                TradingSystemError, RiskError, ExecutionError,
                StrategyError, DataError,
            )
        ]
        assert len(leaf_codes) == len(set(leaf_codes)), (
            f"Duplicate error codes found: {leaf_codes}"
        )


# =========================================================================
# TestExceptionContext
# =========================================================================


class TestExceptionContext:
    """Test suite for exception context preservation."""

    def test_exception_preserves_message(self) -> None:
        """Exception message should be accessible via .message and str()."""
        exc = TradingSystemError("Custom message", "CUSTOM")
        assert exc.message == "Custom message"
        assert str(exc) == "Custom message"

    def test_exception_preserves_details(self) -> None:
        """Details dict should preserve all provided context."""
        details = {"symbol": "BTCUSDT", "quantity": 0.5, "price": 45000.0}
        exc = TradingSystemError("test", "TEST", details=details)
        assert exc.details == details
        assert exc.details["symbol"] == "BTCUSDT"

    def test_exception_default_details_is_empty_dict(self) -> None:
        """Details should default to empty dict, not None."""
        exc = TradingSystemError("test", "TEST")
        assert exc.details == {}
        assert isinstance(exc.details, dict)

    def test_kill_switch_captures_reason(self) -> None:
        """KillSwitchActiveError should capture the activation reason."""
        exc = KillSwitchActiveError(reason="Daily loss limit exceeded")
        assert "Daily loss limit exceeded" in exc.message
        assert exc.details["reason"] == "Daily loss limit exceeded"

    def test_template_not_found_captures_id(self) -> None:
        """TemplateNotFoundError should capture the template ID."""
        exc = TemplateNotFoundError("ema_trend_rsi")
        assert exc.details["template_id"] == "ema_trend_rsi"
        assert "ema_trend_rsi" in exc.message


# =========================================================================
# TestHealthChecker
# =========================================================================


class TestHealthChecker:
    """Test suite for the health check system."""

    def test_health_checker_registration(self) -> None:
        """Should register and list health check functions."""
        checker = HealthChecker()

        async def mock_check() -> ComponentHealth:
            return ComponentHealth(
                name="test",
                status=HealthStatus.HEALTHY,
                message="OK",
            )

        checker.register("test_component", mock_check)
        assert "test_component" in checker.registered_checks

    def test_health_checker_unregister(self) -> None:
        """Should remove a registered health check."""
        checker = HealthChecker()

        async def mock_check() -> ComponentHealth:
            return ComponentHealth(name="test", status=HealthStatus.HEALTHY)

        checker.register("test", mock_check)
        checker.unregister("test")
        assert "test" not in checker.registered_checks

    @pytest.mark.asyncio
    async def test_health_checker_parallel_execution(self) -> None:
        """Health checks should run concurrently."""
        checker = HealthChecker()

        async def healthy_check() -> ComponentHealth:
            return ComponentHealth(
                name="svc",
                status=HealthStatus.HEALTHY,
                message="OK",
            )

        async def degraded_check() -> ComponentHealth:
            return ComponentHealth(
                name="svc2",
                status=HealthStatus.DEGRADED,
                message="Slow",
            )

        checker.register("service_a", healthy_check)
        checker.register("service_b", degraded_check)

        health = await checker.run_checks()
        assert len(health.components) == 2
        assert health.timestamp.tzinfo is not None

    @pytest.mark.asyncio
    async def test_overall_status_all_healthy(self) -> None:
        """Overall status should be HEALTHY when all components are healthy."""
        checker = HealthChecker()

        async def healthy() -> ComponentHealth:
            return ComponentHealth(name="x", status=HealthStatus.HEALTHY)

        checker.register("db", healthy)
        checker.register("api", healthy)

        health = await checker.run_checks()
        assert health.overall_status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_overall_status_degraded(self) -> None:
        """Overall status should be DEGRADED when non-critical is down."""
        checker = HealthChecker()

        async def healthy() -> ComponentHealth:
            return ComponentHealth(name="x", status=HealthStatus.HEALTHY)

        async def unhealthy() -> ComponentHealth:
            return ComponentHealth(name="x", status=HealthStatus.UNHEALTHY)

        checker.register("database", healthy)
        checker.register("logging", unhealthy)  # Non-critical

        health = await checker.run_checks()
        assert health.overall_status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_overall_status_unhealthy_critical(self) -> None:
        """Overall status should be UNHEALTHY when critical component is down."""
        checker = HealthChecker()

        async def healthy() -> ComponentHealth:
            return ComponentHealth(name="x", status=HealthStatus.HEALTHY)

        async def unhealthy() -> ComponentHealth:
            return ComponentHealth(name="x", status=HealthStatus.UNHEALTHY)

        checker.register("database", unhealthy)  # Critical component
        checker.register("logging", healthy)

        health = await checker.run_checks()
        assert health.overall_status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_health_check_exception_handling(self) -> None:
        """Failed health checks should be recorded as UNKNOWN, not crash."""
        checker = HealthChecker()

        async def failing_check() -> ComponentHealth:
            raise RuntimeError("Connection refused")

        checker.register("broken_service", failing_check)

        health = await checker.run_checks()
        assert len(health.components) == 1
        assert health.components[0].status == HealthStatus.UNKNOWN
        assert "Connection refused" in health.components[0].message

    @pytest.mark.asyncio
    async def test_health_latency_tracking(self) -> None:
        """Health check latency should be tracked in milliseconds."""
        checker = HealthChecker()

        async def slow_check() -> ComponentHealth:
            await asyncio.sleep(0.05)  # 50ms
            return ComponentHealth(
                name="slow",
                status=HealthStatus.HEALTHY,
                message="OK",
            )

        checker.register("slow_service", slow_check)

        health = await checker.run_checks()
        assert health.components[0].latency_ms >= 40  # Allow some tolerance
        assert health.check_duration_ms >= 40

    @pytest.mark.asyncio
    async def test_health_empty_checker(self) -> None:
        """Empty checker should return HEALTHY with no components."""
        checker = HealthChecker()
        health = await checker.run_checks()
        assert health.overall_status == HealthStatus.HEALTHY
        assert len(health.components) == 0

    def test_component_health_to_dict(self) -> None:
        """ComponentHealth.to_dict() should produce valid structure."""
        component = ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            latency_ms=5.123,
            message="Connection OK",
            details={"pool_size": 5},
        )
        result = component.to_dict()
        assert result["name"] == "database"
        assert result["status"] == "healthy"
        assert result["latency_ms"] == 5.12
        assert result["details"]["pool_size"] == 5

    def test_system_health_to_dict(self) -> None:
        """SystemHealth.to_dict() should include all components."""
        now = datetime.now(timezone.utc)
        system = SystemHealth(
            overall_status=HealthStatus.HEALTHY,
            components=[
                ComponentHealth(
                    name="db",
                    status=HealthStatus.HEALTHY,
                    message="OK",
                )
            ],
            timestamp=now,
            check_duration_ms=10.5,
        )
        result = system.to_dict()
        assert result["overall_status"] == "healthy"
        assert len(result["components"]) == 1
        assert result["check_duration_ms"] == 10.5


# =========================================================================
# TestLoggingSensitiveData
# =========================================================================


class TestLoggingSensitiveData:
    """Test suite for sensitive data masking in logging."""

    def test_sensitive_data_masked(self) -> None:
        """Sensitive keys should be masked to show only last 4 chars."""
        from src.utils.logging import mask_sensitive_data

        event_dict: dict[str, str | None] = {
            "event": "test",
            "api_key": "sk-abcdefghij1234567890",
            "password": "mysecretpassword",
            "normal_field": "visible",
        }
        result = mask_sensitive_data(None, "info", event_dict)  # type: ignore[arg-type]
        assert result["api_key"].endswith("7890")  # type: ignore[union-attr]
        assert result["api_key"].startswith("*")  # type: ignore[union-attr]
        assert result["password"].endswith("word")  # type: ignore[union-attr]
        assert result["normal_field"] == "visible"

    def test_sensitive_data_short_value_fully_masked(self) -> None:
        """Short sensitive values should be fully masked."""
        from src.utils.logging import mask_sensitive_data

        event_dict: dict[str, str] = {
            "event": "test",
            "api_key": "ab",
        }
        result = mask_sensitive_data(None, "info", event_dict)  # type: ignore[arg-type]
        assert result["api_key"] == "****"

    def test_sensitive_data_none_value_unchanged(self) -> None:
        """None values for sensitive keys should be left unchanged."""
        from src.utils.logging import mask_sensitive_data

        event_dict: dict[str, str | None] = {
            "event": "test",
            "api_key": None,
        }
        result = mask_sensitive_data(None, "info", event_dict)  # type: ignore[arg-type]
        assert result["api_key"] is None
