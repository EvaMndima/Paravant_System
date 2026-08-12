"""Performance benchmarks for risk management operations.

Verifies performance requirements are met:
- Kill switch activation < 1 second (spec requirement)
- Order validation pipeline < 100ms (target)
- Position sizing calculation < 50ms (target)

These tests set hard performance thresholds to catch regressions.

Decision: DEC-2026-02-12-008 - Test coverage threshold 90% per file
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from src.core.config.risk_profiles import RiskProfileConfig, RiskProfileManager
from src.core.risk.controller import RiskController
from src.core.risk.kill_switch import KillSwitch
from src.core.risk.sizing import calculate_fixed_risk_size
from src.core.risk.types import OrderRequest, PortfolioState
from src.data.store import DataStore


@pytest.fixture
def mock_store() -> MagicMock:
    """Create mock DataStore for performance testing."""
    store = MagicMock(spec=DataStore)

    # Configure account
    account = MagicMock()
    account.account_id = "PERF_001"
    account.equity_usdt = 10000.0
    account.balance_usdt = 10000.0
    account.profile = MagicMock()
    account.profile.value = "balanced"
    account.regime = "trending_up"
    store.get_account.return_value = account

    # Configure system state
    state = MagicMock()
    state.kill_switch_active = False
    state.kill_switch_reason = None
    store.get_system_state.return_value = state

    # Configure positions
    store.get_open_positions.return_value = []

    # Configure PnL
    store.get_pnl_for_date.return_value = None
    store.get_pnl_history.return_value = []

    return store


@pytest.fixture
def balanced_profile() -> RiskProfileConfig:
    """Create balanced risk profile for testing."""
    return RiskProfileConfig(
        name="balanced",
        max_position_size_pct=5.0,
        max_open_positions=10,
        max_concentration_pct=30.0,
        daily_loss_limit_pct=3.0,
        weekly_loss_limit_pct=7.0,
        max_drawdown_pct=15.0,
        max_leverage=1.0,
        volatility_multiplier=2.0,
        max_correlation=0.7,
        max_strategies_per_account=5,
        regime_adjustments={
            "trending_up": 1.0,
            "trending_down": 0.8,
            "ranging": 0.5,
            "volatile": 0.5,
            "unknown": 0.7,
        },
    )


# ===========================================================================
# Kill Switch Performance Tests
# ===========================================================================


class TestKillSwitchPerformance:
    """Test kill switch performance requirements."""

    def test_activation_under_1_second(self, mock_store: MagicMock) -> None:
        """Kill switch activation MUST complete in < 1 second (spec requirement)."""
        kill_switch = KillSwitch(mock_store)

        start = time.perf_counter()
        kill_switch.activate("Performance test", actor="benchmark")
        duration = time.perf_counter() - start

        # CRITICAL: Must be under 1 second per specification
        assert duration < 1.0, f"Activation took {duration:.3f}s (spec: <1s)"

        # Log performance for tracking
        print(f"\nKill switch activation: {duration*1000:.2f}ms")

    def test_deactivation_under_1_second(self, mock_store: MagicMock) -> None:
        """Kill switch deactivation should be fast."""
        kill_switch = KillSwitch(mock_store)
        kill_switch._deactivation_code = "test_code"

        mock_state = MagicMock()
        mock_state.kill_switch_active = True
        mock_state.kill_switch_activated_at = None
        mock_store.get_system_state.return_value = mock_state

        start = time.perf_counter()
        kill_switch.deactivate("test_code", actor="benchmark")
        duration = time.perf_counter() - start

        # Should complete quickly
        assert duration < 1.0, f"Deactivation took {duration:.3f}s"

        print(f"Kill switch deactivation: {duration*1000:.2f}ms")

    def test_status_check_under_50ms(self, mock_store: MagicMock) -> None:
        """Status check should be very fast (read-only operation)."""
        kill_switch = KillSwitch(mock_store)

        start = time.perf_counter()
        for _ in range(100):
            kill_switch.get_status()
        duration = time.perf_counter() - start

        avg_duration = duration / 100

        # 100 status checks should average < 50ms each
        assert avg_duration < 0.050, f"Avg status check: {avg_duration*1000:.2f}ms"

        print(f"Kill switch status (avg of 100): {avg_duration*1000:.2f}ms")


# ===========================================================================
# Risk Pipeline Performance Tests
# ===========================================================================


class TestRiskPipelinePerformance:
    """Test risk validation pipeline performance."""

    def test_validate_order_under_100ms(
        self,
        mock_store: MagicMock,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Order validation pipeline target: < 100ms."""
        profile_manager = MagicMock(spec=RiskProfileManager)
        profile_manager.get_profile.return_value = balanced_profile

        controller = RiskController(
            store=mock_store,
            profile_manager=profile_manager,
        )

        order = OrderRequest(
            account_id="PERF_001",
            strategy_id="PERF_STRAT_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.001,
            price=50000.0,
        )

        # Run multiple times for better measurement
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            controller.validate_order(order)
        duration = time.perf_counter() - start

        avg_duration = duration / iterations

        # Target: < 100ms per validation
        assert avg_duration < 0.100, f"Avg validation: {avg_duration*1000:.2f}ms"

        print(f"Order validation (avg of {iterations}): {avg_duration*1000:.2f}ms")


# ===========================================================================
# Position Sizing Performance Tests
# ===========================================================================


class TestPositionSizingPerformance:
    """Test position sizing calculation performance."""

    def test_fixed_risk_sizing_under_10ms(self) -> None:
        """Fixed risk sizing should be very fast (pure calculation)."""
        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            calculate_fixed_risk_size(
                capital=10000.0,
                risk_pct=0.02,
                entry_price=50000.0,
                stop_loss_price=49000.0,
            )

        duration = time.perf_counter() - start
        avg_duration = duration / iterations

        # Pure math should be extremely fast
        assert avg_duration < 0.010, f"Avg sizing: {avg_duration*1000:.2f}ms"

        print(f"Fixed risk sizing (avg of {iterations}): {avg_duration*1000000:.2f}us")

    def test_portfolio_state_build_under_50ms(
        self,
        mock_store: MagicMock,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Building portfolio state should be fast."""
        profile_manager = MagicMock(spec=RiskProfileManager)
        profile_manager.get_profile.return_value = balanced_profile

        controller = RiskController(
            store=mock_store,
            profile_manager=profile_manager,
        )

        iterations = 100
        start = time.perf_counter()

        for _ in range(iterations):
            controller.get_portfolio_state("PERF_001")

        duration = time.perf_counter() - start
        avg_duration = duration / iterations

        # Should build quickly
        assert avg_duration < 0.050, f"Avg build: {avg_duration*1000:.2f}ms"

        print(f"Portfolio state build (avg of {iterations}): {avg_duration*1000:.2f}ms")


# ===========================================================================
# Concurrent Performance Tests
# ===========================================================================


class TestConcurrentPerformance:
    """Test performance under concurrent load."""

    def test_validate_multiple_orders_in_parallel(
        self,
        mock_store: MagicMock,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Multiple order validations should complete quickly."""
        profile_manager = MagicMock(spec=RiskProfileManager)
        profile_manager.get_profile.return_value = balanced_profile

        controller = RiskController(
            store=mock_store,
            profile_manager=profile_manager,
        )

        # Create 10 different orders
        orders = [
            OrderRequest(
                account_id="PERF_001",
                strategy_id=f"STRAT_{i}",
                symbol="BTCUSDT",
                side="buy",
                quantity=0.001,
                price=50000.0 + i * 100,
            )
            for i in range(10)
        ]

        start = time.perf_counter()
        for order in orders:
            controller.validate_order(order)
        duration = time.perf_counter() - start

        # 10 orders should complete in < 1 second
        assert duration < 1.0, f"10 orders took {duration:.3f}s"

        print(f"10 sequential order validations: {duration*1000:.2f}ms")
