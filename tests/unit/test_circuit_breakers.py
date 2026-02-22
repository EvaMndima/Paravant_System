"""Tests for circuit breaker framework.

Covers:
- CircuitBreakerResult validation and immutability
- All 5 circuit breaker implementations
- Cooldown and auto-reset behavior
- Manual reset
- State serialization/deserialization (to_dict/restore_from_dict)
- CircuitBreakerManager coordination and persistence
- Edge cases (NaN, Infinity, zero equity)

Target: >90% coverage for circuit_breakers.py
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.core.config.risk_profiles import RegimeAdjustments, RiskProfileConfig
from src.core.risk.circuit_breakers import (
    CircuitBreakerManager,
    CircuitBreakerResult,
    ConsecutiveLossCircuitBreaker,
    CorrelationCircuitBreaker,
    DailyLossCircuitBreaker,
    DrawdownCircuitBreaker,
    WeeklyLossCircuitBreaker,
)
from src.core.risk.types import PortfolioState
from src.data.store import DataStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def balanced_profile() -> RiskProfileConfig:
    """Create a balanced risk profile for testing."""
    return RiskProfileConfig(
        description="Test balanced profile",
        max_position_size_pct=5.0,
        max_concentration_pct=30.0,
        max_open_positions=10,
        daily_loss_limit_pct=3.0,
        weekly_loss_limit_pct=7.0,
        max_drawdown_pct=15.0,
        max_leverage=1.0,
        volatility_multiplier=2.0,
        max_correlation=0.7,
        max_strategies_per_account=5,
        regime_adjustments=RegimeAdjustments(
            volatile=0.5,
            ranging=0.8,
            trending_up=1.0,
            trending_down=0.3,
            unknown=0.7,
        ),
    )


@pytest.fixture
def healthy_portfolio() -> PortfolioState:
    """Portfolio with no losses."""
    return PortfolioState(
        account_id="acc_001",
        total_equity=10000.0,
        cash_balance=8000.0,
        positions_value=2000.0,
        daily_pnl=0.0,
        weekly_pnl=0.0,
        drawdown_pct=0.0,
        peak_equity=10000.0,
        consecutive_losses=0,
        regime="unknown",
    )


@pytest.fixture
def losing_portfolio() -> PortfolioState:
    """Portfolio with significant losses that should trigger breakers."""
    return PortfolioState(
        account_id="acc_001",
        total_equity=10000.0,
        cash_balance=8000.0,
        positions_value=2000.0,
        daily_pnl=-500.0,  # 5% daily loss
        weekly_pnl=-900.0,  # 9% weekly loss
        drawdown_pct=18.0,  # Above 15% max drawdown
        peak_equity=12195.12,  # Approx to make 18% drawdown work
        consecutive_losses=6,
        regime="volatile",
    )


@pytest.fixture
def mock_store() -> MagicMock:
    """Create a mock DataStore."""
    store = MagicMock(spec=DataStore)

    state = MagicMock()
    state.circuit_breakers = {}
    store.get_system_state.return_value = state
    store.update_system_state.return_value = state

    return store


@pytest.fixture
def fixed_now() -> datetime:
    """Fixed datetime for deterministic tests."""
    return datetime(2026, 2, 12, 14, 0, 0, tzinfo=timezone.utc)


# ===========================================================================
# CircuitBreakerResult tests
# ===========================================================================


class TestCircuitBreakerResult:
    """Tests for CircuitBreakerResult frozen dataclass."""

    def test_creation_with_valid_data(self) -> None:
        """Result can be created with valid fields."""
        result = CircuitBreakerResult(
            breaker_name="daily_loss",
            is_triggered=True,
            current_value=5.0,
            threshold=3.0,
            message="Daily loss exceeded",
        )
        assert result.breaker_name == "daily_loss"
        assert result.is_triggered is True
        assert result.current_value == 5.0
        assert result.threshold == 3.0

    def test_frozen_immutability(self) -> None:
        """Result fields cannot be modified after creation."""
        result = CircuitBreakerResult(
            breaker_name="test",
            is_triggered=False,
            current_value=1.0,
            threshold=5.0,
        )
        with pytest.raises(AttributeError):
            result.is_triggered = True  # type: ignore[misc]

    def test_validation_rejects_nan_current_value(self) -> None:
        """Result rejects NaN current_value."""
        with pytest.raises(ValueError, match="current_value cannot be NaN"):
            CircuitBreakerResult(
                breaker_name="test",
                is_triggered=False,
                current_value=float("nan"),
                threshold=5.0,
            )

    def test_validation_rejects_inf_current_value(self) -> None:
        """Result rejects Infinity current_value."""
        with pytest.raises(
            ValueError, match="current_value cannot be Infinity"
        ):
            CircuitBreakerResult(
                breaker_name="test",
                is_triggered=False,
                current_value=float("inf"),
                threshold=5.0,
            )

    def test_validation_rejects_nan_threshold(self) -> None:
        """Result rejects NaN threshold."""
        with pytest.raises(ValueError, match="threshold cannot be NaN"):
            CircuitBreakerResult(
                breaker_name="test",
                is_triggered=False,
                current_value=1.0,
                threshold=float("nan"),
            )

    def test_validation_rejects_inf_threshold(self) -> None:
        """Result rejects Infinity threshold."""
        with pytest.raises(
            ValueError, match="threshold cannot be Infinity"
        ):
            CircuitBreakerResult(
                breaker_name="test",
                is_triggered=False,
                current_value=1.0,
                threshold=float("inf"),
            )


# ===========================================================================
# DailyLossCircuitBreaker tests
# ===========================================================================


class TestDailyLossCircuitBreaker:
    """Tests for DailyLossCircuitBreaker."""

    def test_not_triggered_when_within_limits(
        self,
        healthy_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker does not trip when daily PnL is positive."""
        breaker = DailyLossCircuitBreaker(cooldown_minutes=60)
        result = breaker.check(healthy_portfolio, balanced_profile, fixed_now)
        assert result.is_triggered is False
        assert result.breaker_name == "daily_loss"

    def test_triggered_when_daily_loss_exceeds_threshold(
        self,
        losing_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker trips when daily loss exceeds profile limit."""
        breaker = DailyLossCircuitBreaker(cooldown_minutes=60)
        result = breaker.check(losing_portfolio, balanced_profile, fixed_now)
        assert result.is_triggered is True
        assert result.triggered_at == fixed_now
        assert "Daily loss" in result.message

    def test_stays_triggered_after_cooldown_not_elapsed(
        self,
        losing_portfolio: PortfolioState,
        healthy_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker stays tripped during cooldown even if PnL recovers."""
        breaker = DailyLossCircuitBreaker(cooldown_minutes=60)

        # Trip the breaker
        breaker.check(losing_portfolio, balanced_profile, fixed_now)
        assert breaker.is_triggered is True

        # Check with healthy portfolio 30 min later (cooldown not elapsed)
        later = fixed_now + timedelta(minutes=30)
        result = breaker.check(healthy_portfolio, balanced_profile, later)
        assert result.is_triggered is True  # Still tripped

    def test_auto_resets_after_cooldown(
        self,
        losing_portfolio: PortfolioState,
        healthy_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker auto-resets after cooldown period elapses."""
        breaker = DailyLossCircuitBreaker(cooldown_minutes=60)

        # Trip the breaker
        breaker.check(losing_portfolio, balanced_profile, fixed_now)
        assert breaker.is_triggered is True

        # Check after cooldown elapsed with healthy portfolio
        after_cooldown = fixed_now + timedelta(minutes=61)
        result = breaker.check(
            healthy_portfolio, balanced_profile, after_cooldown
        )
        assert result.is_triggered is False

    def test_manual_reset(
        self,
        losing_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker can be manually reset."""
        breaker = DailyLossCircuitBreaker(cooldown_minutes=60)
        breaker.check(losing_portfolio, balanced_profile, fixed_now)
        assert breaker.is_triggered is True

        breaker.reset()
        assert breaker.is_triggered is False

    def test_to_dict_and_from_dict_roundtrip(
        self,
        losing_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """State can be serialized and restored."""
        breaker = DailyLossCircuitBreaker(cooldown_minutes=60)
        breaker.check(losing_portfolio, balanced_profile, fixed_now)

        state = breaker.to_dict()
        assert state["name"] == "daily_loss"
        assert state["is_triggered"] is True
        assert state["triggered_at"] is not None

        # Restore into a new breaker
        new_breaker = DailyLossCircuitBreaker(cooldown_minutes=60)
        new_breaker.restore_from_dict(state)
        assert new_breaker.is_triggered is True

    def test_triggered_with_zero_equity(
        self,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker trips when equity is zero."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=0.0,
            cash_balance=0.0,
            positions_value=0.0,
        )
        breaker = DailyLossCircuitBreaker(cooldown_minutes=60)
        result = breaker.check(portfolio, balanced_profile, fixed_now)
        assert result.is_triggered is True


# ===========================================================================
# WeeklyLossCircuitBreaker tests
# ===========================================================================


class TestWeeklyLossCircuitBreaker:
    """Tests for WeeklyLossCircuitBreaker."""

    def test_not_triggered_within_limits(
        self,
        healthy_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker does not trip when weekly PnL is positive."""
        breaker = WeeklyLossCircuitBreaker(cooldown_minutes=120)
        result = breaker.check(healthy_portfolio, balanced_profile, fixed_now)
        assert result.is_triggered is False

    def test_triggered_on_weekly_loss(
        self,
        losing_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker trips when weekly loss exceeds profile limit."""
        breaker = WeeklyLossCircuitBreaker(cooldown_minutes=120)
        result = breaker.check(losing_portfolio, balanced_profile, fixed_now)
        assert result.is_triggered is True
        assert "Weekly loss" in result.message

    def test_auto_resets_after_cooldown(
        self,
        losing_portfolio: PortfolioState,
        healthy_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker auto-resets after cooldown."""
        breaker = WeeklyLossCircuitBreaker(cooldown_minutes=120)
        breaker.check(losing_portfolio, balanced_profile, fixed_now)
        assert breaker.is_triggered is True

        after_cooldown = fixed_now + timedelta(minutes=121)
        result = breaker.check(
            healthy_portfolio, balanced_profile, after_cooldown
        )
        assert result.is_triggered is False


# ===========================================================================
# DrawdownCircuitBreaker tests
# ===========================================================================


class TestDrawdownCircuitBreaker:
    """Tests for DrawdownCircuitBreaker."""

    def test_not_triggered_within_limits(
        self,
        healthy_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker does not trip when drawdown is acceptable."""
        breaker = DrawdownCircuitBreaker(cooldown_minutes=60)
        result = breaker.check(healthy_portfolio, balanced_profile, fixed_now)
        assert result.is_triggered is False

    def test_triggered_on_excessive_drawdown(
        self,
        losing_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker trips when drawdown exceeds max_drawdown_pct."""
        breaker = DrawdownCircuitBreaker(cooldown_minutes=60)
        result = breaker.check(losing_portfolio, balanced_profile, fixed_now)
        assert result.is_triggered is True
        assert "Drawdown" in result.message

    def test_resets_on_80pct_recovery(
        self,
        losing_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker resets when drawdown drops below 80% of threshold."""
        breaker = DrawdownCircuitBreaker(cooldown_minutes=120)

        # Trip the breaker (18% drawdown, 15% threshold)
        breaker.check(losing_portfolio, balanced_profile, fixed_now)
        assert breaker.is_triggered is True

        # Recovery to 11% (below 15% * 0.8 = 12%)
        recovered = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=8000.0,
            positions_value=2000.0,
            drawdown_pct=11.0,
            peak_equity=11235.96,
        )
        later = fixed_now + timedelta(minutes=10)
        result = breaker.check(recovered, balanced_profile, later)
        assert result.is_triggered is False

    def test_stays_triggered_with_partial_recovery(
        self,
        losing_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker stays tripped if recovery is insufficient."""
        breaker = DrawdownCircuitBreaker(cooldown_minutes=120)

        # Trip the breaker
        breaker.check(losing_portfolio, balanced_profile, fixed_now)

        # Partial recovery to 13% (above 15% * 0.8 = 12%)
        partial = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=8000.0,
            positions_value=2000.0,
            drawdown_pct=13.0,
            peak_equity=11494.25,
        )
        later = fixed_now + timedelta(minutes=10)
        result = breaker.check(partial, balanced_profile, later)
        assert result.is_triggered is True


# ===========================================================================
# ConsecutiveLossCircuitBreaker tests
# ===========================================================================


class TestConsecutiveLossCircuitBreaker:
    """Tests for ConsecutiveLossCircuitBreaker."""

    def test_not_triggered_below_threshold(
        self,
        healthy_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker does not trip when losses are below threshold."""
        breaker = ConsecutiveLossCircuitBreaker(
            threshold=5, cooldown_minutes=60
        )
        result = breaker.check(healthy_portfolio, balanced_profile, fixed_now)
        assert result.is_triggered is False

    def test_triggered_at_threshold(
        self,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker trips when consecutive losses reach threshold."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=8000.0,
            positions_value=2000.0,
            consecutive_losses=5,
        )
        breaker = ConsecutiveLossCircuitBreaker(
            threshold=5, cooldown_minutes=60
        )
        result = breaker.check(portfolio, balanced_profile, fixed_now)
        assert result.is_triggered is True
        assert "5 consecutive losses" in result.message

    def test_auto_resets_after_cooldown(
        self,
        healthy_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker auto-resets after cooldown."""
        losing = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=8000.0,
            positions_value=2000.0,
            consecutive_losses=5,
        )
        breaker = ConsecutiveLossCircuitBreaker(
            threshold=5, cooldown_minutes=60
        )
        breaker.check(losing, balanced_profile, fixed_now)
        assert breaker.is_triggered is True

        after_cooldown = fixed_now + timedelta(minutes=61)
        result = breaker.check(
            healthy_portfolio, balanced_profile, after_cooldown
        )
        assert result.is_triggered is False


# ===========================================================================
# CorrelationCircuitBreaker tests
# ===========================================================================


class TestCorrelationCircuitBreaker:
    """Tests for CorrelationCircuitBreaker (PRD §2.2.1 Feature A).

    Checks portfolio-level asset exposure limits:
      - BTC long exposure: max 40% of total equity
      - ETH long exposure: max 30% of total equity
      - Total correlated long exposure: max 60% of total equity
    """

    def _make_long_pos(self, symbol: str, size: float, price: float) -> MagicMock:
        """Build a mock long position."""
        pos = MagicMock()
        pos.symbol = symbol
        pos.size = size
        pos.current_price = price
        pos.side = MagicMock()
        pos.side.value = "long"
        return pos

    def test_not_triggered_low_exposure(
        self,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker does not trip when per-asset and total exposure are under limits."""
        # BTC: 20% of $10k equity, ETH: 15% — total 35% (all under limits)
        btc_pos = self._make_long_pos("BTCUSDT", size=0.05, price=40_000.0)  # $2000 = 20%
        eth_pos = self._make_long_pos("ETHUSDT", size=0.5, price=3_000.0)   # $1500 = 15%

        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10_000.0,
            cash_balance=6_500.0,
            positions_value=3_500.0,
            open_positions=(btc_pos, eth_pos),
        )
        breaker = CorrelationCircuitBreaker(cooldown_minutes=60)
        result = breaker.check(portfolio, balanced_profile, fixed_now)
        assert result.is_triggered is False

    def test_triggered_on_btc_exposure_over_40pct(
        self,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker trips when BTC long exposure exceeds 40% of total equity."""
        # BTC: $5000 out of $10k equity = 50% > 40% limit
        btc_pos = self._make_long_pos("BTCUSDT", size=0.125, price=40_000.0)  # $5000 = 50%

        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10_000.0,
            cash_balance=5_000.0,
            positions_value=5_000.0,
            open_positions=(btc_pos,),
        )
        breaker = CorrelationCircuitBreaker(cooldown_minutes=60)
        result = breaker.check(portfolio, balanced_profile, fixed_now)
        assert result.is_triggered is True
        assert "BTC" in result.message

    def test_not_triggered_with_no_positions(
        self,
        healthy_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        fixed_now: datetime,
    ) -> None:
        """Breaker does not trip with empty positions."""
        breaker = CorrelationCircuitBreaker(cooldown_minutes=60)
        result = breaker.check(healthy_portfolio, balanced_profile, fixed_now)
        assert result.is_triggered is False


# ===========================================================================
# CircuitBreakerManager tests
# ===========================================================================


class TestCircuitBreakerManager:
    """Tests for CircuitBreakerManager."""

    def test_check_all_returns_results_for_each_breaker(
        self,
        healthy_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        mock_store: MagicMock,
        fixed_now: datetime,
    ) -> None:
        """Manager returns one result per registered breaker."""
        breakers = [
            DailyLossCircuitBreaker(),
            WeeklyLossCircuitBreaker(),
            DrawdownCircuitBreaker(),
        ]
        manager = CircuitBreakerManager(breakers, mock_store)
        results = manager.check_all(
            healthy_portfolio, balanced_profile, fixed_now
        )
        assert len(results) == 3
        assert results[0].breaker_name == "daily_loss"
        assert results[1].breaker_name == "weekly_loss"
        assert results[2].breaker_name == "drawdown"

    def test_any_triggered_when_one_breaker_trips(
        self,
        losing_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        mock_store: MagicMock,
        fixed_now: datetime,
    ) -> None:
        """any_triggered() returns True when at least one breaker trips."""
        breakers = [
            DailyLossCircuitBreaker(),
            WeeklyLossCircuitBreaker(),
        ]
        manager = CircuitBreakerManager(breakers, mock_store)
        manager.check_all(losing_portfolio, balanced_profile, fixed_now)
        assert manager.any_triggered() is True

    def test_any_triggered_false_when_none_tripped(
        self,
        healthy_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        mock_store: MagicMock,
        fixed_now: datetime,
    ) -> None:
        """any_triggered() returns False when no breakers are tripped."""
        breakers = [
            DailyLossCircuitBreaker(),
            WeeklyLossCircuitBreaker(),
        ]
        manager = CircuitBreakerManager(breakers, mock_store)
        manager.check_all(healthy_portfolio, balanced_profile, fixed_now)
        assert manager.any_triggered() is False

    def test_get_triggered_returns_names(
        self,
        losing_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        mock_store: MagicMock,
        fixed_now: datetime,
    ) -> None:
        """get_triggered() returns names of tripped breakers."""
        breakers = [
            DailyLossCircuitBreaker(),
            WeeklyLossCircuitBreaker(),
            DrawdownCircuitBreaker(),
        ]
        manager = CircuitBreakerManager(breakers, mock_store)
        manager.check_all(losing_portfolio, balanced_profile, fixed_now)
        triggered = manager.get_triggered()
        assert "daily_loss" in triggered
        assert "weekly_loss" in triggered
        assert "drawdown" in triggered

    def test_reset_specific_breaker(
        self,
        losing_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        mock_store: MagicMock,
        fixed_now: datetime,
    ) -> None:
        """Can reset a specific breaker by name."""
        breakers = [
            DailyLossCircuitBreaker(),
            WeeklyLossCircuitBreaker(),
        ]
        manager = CircuitBreakerManager(breakers, mock_store)
        manager.check_all(losing_portfolio, balanced_profile, fixed_now)

        manager.reset("daily_loss")
        triggered = manager.get_triggered()
        assert "daily_loss" not in triggered
        assert "weekly_loss" in triggered

    def test_reset_unknown_breaker_raises(
        self,
        mock_store: MagicMock,
    ) -> None:
        """Resetting an unknown breaker raises ValueError."""
        manager = CircuitBreakerManager(
            [DailyLossCircuitBreaker()], mock_store
        )
        with pytest.raises(ValueError, match="not found"):
            manager.reset("nonexistent")

    def test_reset_all(
        self,
        losing_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        mock_store: MagicMock,
        fixed_now: datetime,
    ) -> None:
        """Can reset all breakers at once."""
        breakers = [
            DailyLossCircuitBreaker(),
            WeeklyLossCircuitBreaker(),
        ]
        manager = CircuitBreakerManager(breakers, mock_store)
        manager.check_all(losing_portfolio, balanced_profile, fixed_now)
        assert manager.any_triggered() is True

        manager.reset_all()
        assert manager.any_triggered() is False

    def test_persist_state_calls_store(
        self,
        losing_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
        mock_store: MagicMock,
        fixed_now: datetime,
    ) -> None:
        """persist_state() saves to store.update_system_state."""
        breakers = [DailyLossCircuitBreaker()]
        manager = CircuitBreakerManager(breakers, mock_store)
        manager.check_all(losing_portfolio, balanced_profile, fixed_now)

        manager.persist_state()
        mock_store.update_system_state.assert_called_once()
        call_kwargs = mock_store.update_system_state.call_args[1]
        assert "circuit_breakers" in call_kwargs
        cb_state = call_kwargs["circuit_breakers"]
        # Top-level has breaker name -> bool for any_circuit_breaker_active
        assert cb_state["daily_loss"] is True
        # Detailed state under _state key
        assert "_state" in cb_state
        assert "daily_loss" in cb_state["_state"]

    def test_restore_state_from_store(
        self,
        mock_store: MagicMock,
        fixed_now: datetime,
    ) -> None:
        """restore_state() loads state from store."""
        # Set up stored state
        stored = {
            "daily_loss": True,
            "_state": {
                "daily_loss": {
                    "name": "daily_loss",
                    "is_triggered": True,
                    "triggered_at": fixed_now.isoformat(),
                    "cooldown_minutes": 60,
                },
            },
        }
        state_mock = MagicMock()
        state_mock.circuit_breakers = stored
        mock_store.get_system_state.return_value = state_mock

        breakers = [DailyLossCircuitBreaker()]
        manager = CircuitBreakerManager(breakers, mock_store)
        manager.restore_state()

        assert breakers[0].is_triggered is True

    def test_restore_state_empty_store(
        self,
        mock_store: MagicMock,
    ) -> None:
        """restore_state() handles empty circuit_breakers gracefully."""
        state_mock = MagicMock()
        state_mock.circuit_breakers = {}
        mock_store.get_system_state.return_value = state_mock

        breakers = [DailyLossCircuitBreaker()]
        manager = CircuitBreakerManager(breakers, mock_store)
        manager.restore_state()  # Should not raise
        assert breakers[0].is_triggered is False

    def test_breakers_property_returns_copy(
        self,
        mock_store: MagicMock,
    ) -> None:
        """breakers property returns a copy, not the internal list."""
        breakers = [DailyLossCircuitBreaker()]
        manager = CircuitBreakerManager(breakers, mock_store)
        returned = manager.breakers
        returned.append(WeeklyLossCircuitBreaker())
        # Internal list unchanged
        assert len(manager.breakers) == 1


# ===========================================================================
# State serialization edge cases
# ===========================================================================


class TestCircuitBreakerSerialization:
    """Tests for to_dict/restore_from_dict edge cases."""

    def test_restore_with_naive_datetime(self) -> None:
        """Restoring a naive datetime string adds UTC timezone."""
        breaker = DailyLossCircuitBreaker()
        # Simulate a naive datetime stored without timezone
        data = {
            "name": "daily_loss",
            "is_triggered": True,
            "triggered_at": "2026-02-12T14:00:00",
            "cooldown_minutes": 60,
        }
        breaker.restore_from_dict(data)
        assert breaker.is_triggered is True
        assert breaker._triggered_at is not None
        assert breaker._triggered_at.tzinfo is not None

    def test_restore_with_none_triggered_at(self) -> None:
        """Restoring with None triggered_at works."""
        breaker = DailyLossCircuitBreaker()
        data = {
            "name": "daily_loss",
            "is_triggered": False,
            "triggered_at": None,
            "cooldown_minutes": 60,
        }
        breaker.restore_from_dict(data)
        assert breaker.is_triggered is False
        assert breaker._triggered_at is None

    def test_to_dict_untriggered(self) -> None:
        """to_dict for untriggered breaker has None triggered_at."""
        breaker = DailyLossCircuitBreaker()
        state = breaker.to_dict()
        assert state["is_triggered"] is False
        assert state["triggered_at"] is None
