"""Tests for the risk controller, check functions, and position sizing.

Covers:
- Risk check data types (OrderRequest, PortfolioState, etc.)
- Individual risk check functions (pure functions)
- Position sizing methods (fixed risk, ATR, Kelly)
- Capital allocation rules
- RiskController pipeline (fail-fast behavior)
- Edge cases (NaN, zero equity, missing data)

Target: >90% coverage for src/core/risk/
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    # Only referenced in annotations. The fixture imports it lazily at runtime,
    # and `from __future__ import annotations` means these are never evaluated.
    from src.core.risk.controller import RiskController

from src.core.config.risk_profiles import (
    RegimeAdjustments,
    RiskProfileConfig,
    RiskProfileManager,
)
from src.core.risk.checks import (
    check_concentration,
    check_daily_loss_limit,
    check_kill_switch,
    check_max_drawdown,
    check_max_positions,
    check_position_size,
    check_weekly_loss_limit,
)
from src.core.risk.sizing import (
    NEW_STRATEGY_MAX_PCT,
    PROVEN_STRATEGY_MAX_PCT,
    apply_regime_adjustment,
    calculate_atr_size,
    calculate_available_capital,
    calculate_fixed_risk_size,
    calculate_kelly_size,
    get_strategy_max_allocation_pct,
    validate_allocation,
)
from src.core.risk.types import (
    OrderRequest,
    PortfolioState,
    PositionSizeResult,
)
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
def conservative_profile() -> RiskProfileConfig:
    """Create a conservative risk profile for testing."""
    return RiskProfileConfig(
        description="Test conservative profile",
        max_position_size_pct=2.0,
        max_concentration_pct=20.0,
        max_open_positions=5,
        daily_loss_limit_pct=1.5,
        weekly_loss_limit_pct=3.0,
        max_drawdown_pct=10.0,
        max_leverage=1.0,
        volatility_multiplier=1.5,
        max_correlation=0.5,
        max_strategies_per_account=3,
        regime_adjustments=RegimeAdjustments(
            volatile=0.3,
            ranging=0.7,
            trending_up=1.0,
            trending_down=0.2,
            unknown=0.5,
        ),
    )


@pytest.fixture
def sample_order() -> OrderRequest:
    """Create a sample order request."""
    return OrderRequest(
        account_id="acc_001",
        strategy_id="str_001",
        symbol="BTCUSDT",
        side="buy",
        quantity=0.1,
        price=50000.0,
        stop_loss_price=49000.0,
    )


@pytest.fixture
def sample_portfolio() -> PortfolioState:
    """Create a sample portfolio state."""
    return PortfolioState(
        account_id="acc_001",
        total_equity=10000.0,
        cash_balance=8000.0,
        positions_value=2000.0,
        open_positions=(),
        daily_pnl=0.0,
        weekly_pnl=0.0,
        drawdown_pct=0.0,
        peak_equity=10000.0,
        regime="unknown",
    )


@pytest.fixture
def mock_position() -> MagicMock:
    """Create a mock Position object."""
    pos = MagicMock()
    pos.symbol = "BTCUSDT"
    pos.side = MagicMock()
    pos.side.value = "long"
    pos.size = 0.05
    pos.current_price = 50000.0
    pos.status = MagicMock()
    pos.status.value = "open"
    return pos


# ===========================================================================
# Data type tests
# ===========================================================================


class TestOrderRequest:
    """Test OrderRequest dataclass validation."""

    def test_valid_order_request(self) -> None:
        """Valid order request should create successfully."""
        order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.1,
            price=50000.0,
        )
        assert order.symbol == "BTCUSDT"
        assert order.side == "buy"

    def test_missing_account_id(self) -> None:
        """Empty account_id should raise ValueError."""
        with pytest.raises(ValueError, match="account_id"):
            OrderRequest(
                account_id="",
                strategy_id="str_001",
                symbol="BTCUSDT",
                side="buy",
                quantity=0.1,
                price=50000.0,
            )

    def test_missing_strategy_id(self) -> None:
        """Empty strategy_id should raise ValueError."""
        with pytest.raises(ValueError, match="strategy_id"):
            OrderRequest(
                account_id="acc_001",
                strategy_id="",
                symbol="BTCUSDT",
                side="buy",
                quantity=0.1,
                price=50000.0,
            )

    def test_invalid_side(self) -> None:
        """Invalid side should raise ValueError."""
        with pytest.raises(ValueError, match="side"):
            OrderRequest(
                account_id="acc_001",
                strategy_id="str_001",
                symbol="BTCUSDT",
                side="invalid",
                quantity=0.1,
                price=50000.0,
            )

    def test_nan_price(self) -> None:
        """NaN price should raise ValueError."""
        with pytest.raises(ValueError, match="price"):
            OrderRequest(
                account_id="acc_001",
                strategy_id="str_001",
                symbol="BTCUSDT",
                side="buy",
                quantity=0.1,
                price=float("nan"),
            )

    def test_negative_quantity(self) -> None:
        """Negative quantity should raise ValueError."""
        with pytest.raises(ValueError, match="quantity"):
            OrderRequest(
                account_id="acc_001",
                strategy_id="str_001",
                symbol="BTCUSDT",
                side="buy",
                quantity=-1.0,
                price=50000.0,
            )

    def test_infinity_price(self) -> None:
        """Infinity price should raise ValueError."""
        with pytest.raises(ValueError, match="price"):
            OrderRequest(
                account_id="acc_001",
                strategy_id="str_001",
                symbol="BTCUSDT",
                side="buy",
                quantity=0.1,
                price=float("inf"),
            )

    def test_frozen_immutability(self) -> None:
        """Frozen dataclass should not allow attribute modification."""
        order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.1,
            price=50000.0,
        )
        with pytest.raises(AttributeError):
            order.price = 60000.0  # type: ignore[misc]


class TestPortfolioState:
    """Test PortfolioState dataclass validation."""

    def test_valid_portfolio(self, sample_portfolio: PortfolioState) -> None:
        """Valid portfolio should create successfully."""
        assert sample_portfolio.total_equity == 10000.0
        assert sample_portfolio.cash_balance == 8000.0

    def test_equity_mismatch(self) -> None:
        """Equity != cash + positions should raise ValueError."""
        with pytest.raises(ValueError, match="Equity mismatch"):
            PortfolioState(
                account_id="acc_001",
                total_equity=10000.0,
                cash_balance=5000.0,
                positions_value=2000.0,  # 5000 + 2000 != 10000
            )

    def test_nan_equity(self) -> None:
        """NaN total_equity should raise ValueError."""
        with pytest.raises(ValueError, match="NaN"):
            PortfolioState(
                account_id="acc_001",
                total_equity=float("nan"),
                cash_balance=0.0,
                positions_value=0.0,
            )

    def test_drawdown_out_of_range(self) -> None:
        """Drawdown > 100% should raise ValueError."""
        with pytest.raises(ValueError, match="drawdown_pct"):
            PortfolioState(
                account_id="acc_001",
                total_equity=10000.0,
                cash_balance=10000.0,
                positions_value=0.0,
                drawdown_pct=150.0,
            )

    def test_negative_consecutive_losses(self) -> None:
        """Negative consecutive_losses should raise ValueError."""
        with pytest.raises(ValueError, match="consecutive_losses"):
            PortfolioState(
                account_id="acc_001",
                total_equity=10000.0,
                cash_balance=10000.0,
                positions_value=0.0,
                consecutive_losses=-1,
            )


class TestPositionSizeResult:
    """Test PositionSizeResult dataclass validation."""

    def test_valid_result(self) -> None:
        """Valid position size result should create successfully."""
        result = PositionSizeResult(
            quantity=0.1,
            notional_value=5000.0,
            risk_amount=200.0,
            risk_pct=2.0,
            sizing_method="fixed_risk",
            stop_loss_price=49000.0,
            entry_price=50000.0,
        )
        assert result.quantity == 0.1
        assert result.sizing_method == "fixed_risk"

    def test_nan_quantity(self) -> None:
        """NaN quantity should raise ValueError."""
        with pytest.raises(ValueError, match="quantity"):
            PositionSizeResult(
                quantity=float("nan"),
                notional_value=0.0,
                risk_amount=0.0,
                risk_pct=0.0,
                sizing_method="fixed_risk",
                stop_loss_price=49000.0,
                entry_price=50000.0,
            )


# ===========================================================================
# Risk check tests
# ===========================================================================


class TestCheckKillSwitch:
    """Test kill switch check function."""

    def test_kill_switch_inactive(self) -> None:
        """Inactive kill switch should pass."""
        state = MagicMock()
        state.kill_switch_active = False
        result = check_kill_switch(state)
        assert result.approved is True

    def test_kill_switch_active(self) -> None:
        """Active kill switch should reject."""
        state = MagicMock()
        state.kill_switch_active = True
        state.kill_switch_reason = "Daily loss limit exceeded"
        result = check_kill_switch(state)
        assert result.approved is False
        assert "kill_switch" in result.checks_failed

    def test_kill_switch_active_no_reason(self) -> None:
        """Active kill switch with no reason should still reject."""
        state = MagicMock()
        state.kill_switch_active = True
        state.kill_switch_reason = None
        result = check_kill_switch(state)
        assert result.approved is False


class TestCheckDailyLossLimit:
    """Test daily loss limit check function."""

    def test_no_daily_loss(
        self,
        sample_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """No daily loss (PnL >= 0) should pass."""
        result = check_daily_loss_limit(sample_portfolio, balanced_profile)
        assert result.approved is True

    def test_daily_loss_within_limit(
        self,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Daily loss within limit should pass."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=9800.0,
            positions_value=200.0,
            daily_pnl=-200.0,  # 2% loss, limit is 3%
        )
        result = check_daily_loss_limit(portfolio, balanced_profile)
        assert result.approved is True

    def test_daily_loss_exceeds_limit(
        self,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Daily loss exceeding limit should reject."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=9500.0,
            positions_value=500.0,
            daily_pnl=-400.0,  # 4% loss, limit is 3%
        )
        result = check_daily_loss_limit(portfolio, balanced_profile)
        assert result.approved is False
        assert "Daily loss" in (result.rejection_reason or "")

    def test_daily_loss_zero_equity(
        self,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Zero equity should reject."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=0.0,
            cash_balance=0.0,
            positions_value=0.0,
        )
        result = check_daily_loss_limit(portfolio, balanced_profile)
        assert result.approved is False


class TestCheckWeeklyLossLimit:
    """Test weekly loss limit check function."""

    def test_weekly_loss_within_limit(
        self,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Weekly loss within limit should pass."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=9400.0,
            positions_value=600.0,
            weekly_pnl=-500.0,  # 5% loss, limit is 7%
        )
        result = check_weekly_loss_limit(portfolio, balanced_profile)
        assert result.approved is True

    def test_weekly_loss_exceeds_limit(
        self,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Weekly loss exceeding limit should reject."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=9200.0,
            positions_value=800.0,
            weekly_pnl=-800.0,  # 8% loss, limit is 7%
        )
        result = check_weekly_loss_limit(portfolio, balanced_profile)
        assert result.approved is False


class TestCheckMaxDrawdown:
    """Test max drawdown check function."""

    def test_drawdown_within_limit(
        self,
        sample_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Drawdown within limit should pass."""
        result = check_max_drawdown(sample_portfolio, balanced_profile)
        assert result.approved is True

    def test_drawdown_exceeds_limit(
        self,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Drawdown exceeding limit should reject."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=8500.0,
            cash_balance=8500.0,
            positions_value=0.0,
            drawdown_pct=16.0,  # 16% drawdown, limit is 15%
        )
        result = check_max_drawdown(portfolio, balanced_profile)
        assert result.approved is False
        assert "Drawdown" in (result.rejection_reason or "")


class TestCheckMaxPositions:
    """Test max positions check function."""

    def test_below_max_positions(
        self,
        sample_order: OrderRequest,
        sample_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Below max positions should pass."""
        result = check_max_positions(
            sample_order, sample_portfolio, balanced_profile
        )
        assert result.approved is True

    def test_at_max_positions(
        self,
        sample_order: OrderRequest,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """At max positions should reject new positions."""
        # Create 10 mock positions (max for balanced)
        positions = []
        for i in range(10):
            pos = MagicMock()
            pos.symbol = f"SYMBOL{i}"
            pos.side = MagicMock()
            pos.side.value = "long"
            positions.append(pos)

        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=5000.0,
            positions_value=5000.0,
            open_positions=tuple(positions),
        )
        result = check_max_positions(
            sample_order, portfolio, balanced_profile
        )
        assert result.approved is False

    def test_allow_closing_at_max(
        self,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Should allow closing position even at max."""
        # Create position matching the order symbol
        existing = MagicMock()
        existing.symbol = "BTCUSDT"
        existing.side = MagicMock()
        existing.side.value = "long"

        positions = [existing] + [MagicMock() for _ in range(9)]
        for p in positions[1:]:
            p.symbol = "OTHER"
            p.side = MagicMock()
            p.side.value = "long"

        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=5000.0,
            positions_value=5000.0,
            open_positions=tuple(positions),
        )

        # Sell order for existing long position = closing
        close_order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="sell",
            quantity=0.1,
            price=50000.0,
        )
        result = check_max_positions(
            close_order, portfolio, balanced_profile
        )
        assert result.approved is True


class TestCheckConcentration:
    """Test concentration check function."""

    def test_within_concentration_limit(
        self,
        sample_order: OrderRequest,
        sample_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Order within concentration limit should pass."""
        # Order value: 0.1 * 50000 = 5000 = 50% of 10000
        # But max is 30%, so let's use a smaller order
        small_order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.05,
            price=50000.0,
        )
        # 0.05 * 50000 = 2500 = 25% of 10000 < 30%
        result = check_concentration(
            small_order, sample_portfolio, balanced_profile
        )
        assert result.approved is True

    def test_exceeds_concentration_limit(
        self,
        sample_portfolio: PortfolioState,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Order exceeding concentration should reject."""
        large_order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.1,
            price=50000.0,
        )
        # 0.1 * 50000 = 5000 = 50% of 10000 > 30%
        result = check_concentration(
            large_order, sample_portfolio, balanced_profile
        )
        assert result.approved is False

    def test_concentration_with_existing_position(
        self,
        balanced_profile: RiskProfileConfig,
        mock_position: MagicMock,
    ) -> None:
        """Should sum existing + new position value."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=7500.0,
            positions_value=2500.0,
            open_positions=(mock_position,),  # 0.05 * 50000 = 2500
        )
        # Add 0.02 BTC = 1000 more -> total 3500 = 35% > 30%
        order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.02,
            price=50000.0,
        )
        result = check_concentration(order, portfolio, balanced_profile)
        assert result.approved is False

    def test_zero_equity_concentration(
        self,
        sample_order: OrderRequest,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Zero equity should reject."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=0.0,
            cash_balance=0.0,
            positions_value=0.0,
        )
        result = check_concentration(
            sample_order, portfolio, balanced_profile
        )
        assert result.approved is False


class TestCheckPositionSize:
    """Test position size check function."""

    def test_within_limit(
        self,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Position within size limit should pass."""
        order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.01,
            price=50000.0,
        )
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=100000.0,
            cash_balance=100000.0,
            positions_value=0.0,
        )
        # 0.01 * 50000 = 500 = 0.5% of 100000 < 5%
        result = check_position_size(order, portfolio, balanced_profile)
        assert result.approved is True

    def test_exceeds_limit(
        self,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Position exceeding size limit should reject."""
        order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.2,
            price=50000.0,
        )
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=10000.0,
            positions_value=0.0,
        )
        # 0.2 * 50000 = 10000 = 100% of 10000 > 5%
        result = check_position_size(order, portfolio, balanced_profile)
        assert result.approved is False

    def test_conservative_profile_lower_limit(
        self,
        conservative_profile: RiskProfileConfig,
    ) -> None:
        """Conservative profile should enforce 2% max."""
        order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.01,
            price=50000.0,
        )
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=10000.0,
            positions_value=0.0,
        )
        # 0.01 * 50000 = 500 = 5% > 2% conservative limit
        result = check_position_size(
            order, portfolio, conservative_profile
        )
        assert result.approved is False


# ===========================================================================
# Position sizing tests
# ===========================================================================


class TestFixedRiskSizing:
    """Test fixed risk position sizing."""

    def test_basic_calculation(self) -> None:
        """Basic fixed risk sizing should calculate correctly."""
        result = calculate_fixed_risk_size(
            capital=10000.0,
            risk_pct=0.02,  # 2% risk
            entry_price=50000.0,
            stop_loss_price=49000.0,
        )
        # risk = 10000 * 0.02 = 200
        # risk_per_unit = 50000 - 49000 = 1000
        # quantity = 200 / 1000 = 0.2
        assert result.quantity == pytest.approx(0.2)
        assert result.risk_amount == pytest.approx(200.0)
        assert result.sizing_method == "fixed_risk"

    def test_zero_capital(self) -> None:
        """Zero capital should raise ValueError."""
        with pytest.raises(ValueError, match="capital"):
            calculate_fixed_risk_size(
                capital=0.0,
                risk_pct=0.02,
                entry_price=50000.0,
                stop_loss_price=49000.0,
            )

    def test_equal_entry_stop_loss(self) -> None:
        """Equal entry and stop loss should raise ValueError."""
        with pytest.raises(ValueError, match="equal"):
            calculate_fixed_risk_size(
                capital=10000.0,
                risk_pct=0.02,
                entry_price=50000.0,
                stop_loss_price=50000.0,
            )


class TestATRSizing:
    """Test ATR-based position sizing."""

    def test_basic_atr_calculation(self) -> None:
        """ATR sizing should calculate correctly."""
        result = calculate_atr_size(
            capital=10000.0,
            risk_pct=0.02,
            entry_price=50000.0,
            stop_loss_price=49000.0,
            atr_value=500.0,
            atr_multiplier=2.0,
        )
        # risk = 10000 * 0.02 = 200
        # quantity = 200 / (500 * 2) = 0.2
        assert result.quantity == pytest.approx(0.2)
        assert result.sizing_method == "atr_based"

    def test_zero_atr(self) -> None:
        """Zero ATR should raise ValueError."""
        with pytest.raises(ValueError, match="atr_value"):
            calculate_atr_size(
                capital=10000.0,
                risk_pct=0.02,
                entry_price=50000.0,
                stop_loss_price=49000.0,
                atr_value=0.0,
            )

    def test_nan_atr(self) -> None:
        """NaN ATR should raise ValueError."""
        with pytest.raises(ValueError, match="atr_value"):
            calculate_atr_size(
                capital=10000.0,
                risk_pct=0.02,
                entry_price=50000.0,
                stop_loss_price=49000.0,
                atr_value=float("nan"),
            )


class TestKellySizing:
    """Test Kelly Criterion position sizing."""

    def test_positive_expectancy(self) -> None:
        """Positive expectancy should return non-zero quantity."""
        result = calculate_kelly_size(
            capital=10000.0,
            entry_price=50000.0,
            stop_loss_price=49000.0,
            win_rate=0.6,
            avg_win=200.0,
            avg_loss=100.0,
        )
        assert result.quantity > 0
        assert result.sizing_method == "kelly"

    def test_negative_expectancy(self) -> None:
        """Negative expectancy should return zero quantity."""
        result = calculate_kelly_size(
            capital=10000.0,
            entry_price=50000.0,
            stop_loss_price=49000.0,
            win_rate=0.3,
            avg_win=100.0,
            avg_loss=200.0,
        )
        assert result.quantity == 0.0

    def test_invalid_win_rate(self) -> None:
        """Win rate outside 0-1 should raise ValueError."""
        with pytest.raises(ValueError, match="win_rate"):
            calculate_kelly_size(
                capital=10000.0,
                entry_price=50000.0,
                stop_loss_price=49000.0,
                win_rate=1.5,
                avg_win=200.0,
                avg_loss=100.0,
            )

    def test_zero_avg_win(self) -> None:
        """Zero avg_win should raise ValueError."""
        with pytest.raises(ValueError, match="avg_win"):
            calculate_kelly_size(
                capital=10000.0,
                entry_price=50000.0,
                stop_loss_price=49000.0,
                win_rate=0.6,
                avg_win=0.0,
                avg_loss=100.0,
            )


# ===========================================================================
# Capital allocation tests
# ===========================================================================


class TestCapitalAllocation:
    """Test capital allocation functions."""

    def test_available_capital(self) -> None:
        """Available capital should subtract reserves."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=10000.0,
            positions_value=0.0,
        )
        available = calculate_available_capital(portfolio)
        # Reserved: 10000 * (20 + 10) / 100 = 3000
        # Available: 10000 - 3000 = 7000
        assert available == pytest.approx(7000.0)

    def test_available_capital_with_positions(self) -> None:
        """Available capital should account for existing positions."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=5000.0,
            positions_value=5000.0,
        )
        available = calculate_available_capital(portfolio)
        # Reserved: 10000 * 30% = 3000
        # Available: 5000 - 3000 = 2000
        assert available == pytest.approx(2000.0)

    def test_available_capital_insufficient(self) -> None:
        """Should return 0 when cash < reserves."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=2000.0,
            positions_value=8000.0,
        )
        available = calculate_available_capital(portfolio)
        # Reserved: 10000 * 30% = 3000, cash = 2000
        assert available == 0.0

    def test_new_strategy_allocation(self) -> None:
        """New strategy should get 5% max."""
        pct = get_strategy_max_allocation_pct(is_proven=False)
        assert pct == NEW_STRATEGY_MAX_PCT

    def test_proven_strategy_allocation(self) -> None:
        """Proven strategy should get 15% max."""
        pct = get_strategy_max_allocation_pct(is_proven=True)
        assert pct == PROVEN_STRATEGY_MAX_PCT

    def test_validate_allocation_approved(self) -> None:
        """Valid allocation should be approved."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=10000.0,
            positions_value=0.0,
        )
        approved, reason = validate_allocation(
            requested_pct=4.0,
            is_proven=False,
            portfolio=portfolio,
        )
        assert approved is True

    def test_validate_allocation_exceeds_max(self) -> None:
        """Allocation exceeding max should be rejected."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=10000.0,
            positions_value=0.0,
        )
        approved, reason = validate_allocation(
            requested_pct=10.0,
            is_proven=False,
            portfolio=portfolio,
        )
        assert approved is False
        assert "Max allocation" in reason


class TestRegimeAdjustment:
    """Test regime adjustment function."""

    def test_volatile_regime(self, balanced_profile: RiskProfileConfig) -> None:
        """Volatile regime should reduce position size."""
        adjusted, multiplier = apply_regime_adjustment(
            1.0, "volatile", balanced_profile
        )
        assert adjusted == pytest.approx(0.5)
        assert multiplier == 0.5

    def test_trending_up_regime(
        self, balanced_profile: RiskProfileConfig
    ) -> None:
        """Trending up should keep full size."""
        adjusted, multiplier = apply_regime_adjustment(
            1.0, "trending_up", balanced_profile
        )
        assert adjusted == pytest.approx(1.0)
        assert multiplier == 1.0

    def test_unknown_regime(
        self, balanced_profile: RiskProfileConfig
    ) -> None:
        """Unknown regime should use unknown multiplier."""
        adjusted, multiplier = apply_regime_adjustment(
            1.0, "unknown", balanced_profile
        )
        assert adjusted == pytest.approx(0.7)


# ===========================================================================
# RiskController integration tests (with mocks)
# ===========================================================================


class TestRiskControllerPipeline:
    """Test the RiskController order validation pipeline."""

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        """Create a mock DataStore."""
        store = MagicMock(spec=DataStore)

        # Mock account
        account = MagicMock()
        account.equity_usdt = 10000.0
        account.balance_usdt = 10000.0
        account.profile = MagicMock()
        account.profile.value = "balanced"
        account.regime = "unknown"
        store.get_account.return_value = account

        # Mock system state
        state = MagicMock()
        state.kill_switch_active = False
        state.kill_switch_reason = None
        store.get_system_state.return_value = state

        # Mock positions (empty)
        store.get_open_positions.return_value = []

        # Mock PnL
        store.get_pnl_for_date.return_value = None
        store.get_pnl_history.return_value = []

        return store

    @pytest.fixture
    def mock_profile_manager(
        self, balanced_profile: RiskProfileConfig
    ) -> MagicMock:
        """Create a mock RiskProfileManager."""
        manager = MagicMock(spec=RiskProfileManager)
        manager.get_profile.return_value = balanced_profile
        return manager

    @pytest.fixture
    def controller(
        self,
        mock_store: MagicMock,
        mock_profile_manager: MagicMock,
    ) -> "RiskController":
        """Create a RiskController with mocks."""
        from src.core.risk.controller import RiskController

        return RiskController(
            store=mock_store,
            profile_manager=mock_profile_manager,
        )

    def test_all_checks_pass(
        self,
        controller: Any,
    ) -> None:
        """Order passing all checks should return all approved results."""
        order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.001,
            price=50000.0,
        )
        results = controller.validate_order(order)
        assert all(r.approved for r in results)
        assert len(results) == 8  # All 8 checks ran (includes portfolio_correlation)

    def test_kill_switch_short_circuits(
        self,
        controller: Any,
        mock_store: MagicMock,
    ) -> None:
        """Kill switch should short-circuit the pipeline."""
        state = MagicMock()
        state.kill_switch_active = True
        state.kill_switch_reason = "Test"
        mock_store.get_system_state.return_value = state

        order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.001,
            price=50000.0,
        )
        results = controller.validate_order(order)
        assert len(results) == 1  # Only kill switch ran
        assert results[0].approved is False
        assert results[0].check_name == "kill_switch"

    def test_position_size_reject(
        self,
        controller: Any,
    ) -> None:
        """Order exceeding position size should fail after checks 1-2-3-4-5-6."""
        order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=1.0,  # 1 BTC = $50k = 500% of equity
            price=50000.0,
        )
        results = controller.validate_order(order)
        # Should fail on position_size check (7th check)
        # But concentration (6th) will fail first since 500% > 30%
        failed = [r for r in results if not r.approved]
        assert len(failed) == 1
        assert failed[0].check_name in ("concentration", "position_size")

    def test_validate_nan_price_raises(
        self,
        controller: Any,
    ) -> None:
        """NaN price should raise ValueError at OrderRequest creation."""
        with pytest.raises(ValueError):
            OrderRequest(
                account_id="acc_001",
                strategy_id="str_001",
                symbol="BTCUSDT",
                side="buy",
                quantity=0.1,
                price=float("nan"),
            )


class TestRiskControllerPositionSizing:
    """Test RiskController position sizing method."""

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        """Create mock DataStore."""
        store = MagicMock(spec=DataStore)

        account = MagicMock()
        account.equity_usdt = 10000.0
        account.balance_usdt = 10000.0
        account.profile = MagicMock()
        account.profile.value = "balanced"
        account.regime = "unknown"
        store.get_account.return_value = account
        store.get_open_positions.return_value = []
        store.get_pnl_for_date.return_value = None
        store.get_pnl_history.return_value = []

        return store

    @pytest.fixture
    def controller(
        self,
        mock_store: MagicMock,
        balanced_profile: RiskProfileConfig,
    ) -> Any:
        """Create controller with mocks."""
        from src.core.risk.controller import RiskController

        manager = MagicMock(spec=RiskProfileManager)
        manager.get_profile.return_value = balanced_profile
        return RiskController(
            store=mock_store, profile_manager=manager
        )

    def test_fixed_risk_sizing(self, controller: Any) -> None:
        """Fixed risk sizing through controller should work."""
        result = controller.calculate_position_size(
            account_id="acc_001",
            symbol="BTCUSDT",
            side="buy",
            entry_price=50000.0,
            stop_loss_price=49000.0,
            method="fixed_risk",
        )
        assert result.quantity > 0
        assert result.sizing_method == "fixed_risk"

    def test_invalid_stop_loss_buy(self, controller: Any) -> None:
        """Stop loss above entry for buy should raise."""
        with pytest.raises(ValueError, match="below"):
            controller.calculate_position_size(
                account_id="acc_001",
                symbol="BTCUSDT",
                side="buy",
                entry_price=50000.0,
                stop_loss_price=51000.0,
            )

    def test_invalid_stop_loss_sell(self, controller: Any) -> None:
        """Stop loss below entry for sell should raise."""
        with pytest.raises(ValueError, match="above"):
            controller.calculate_position_size(
                account_id="acc_001",
                symbol="BTCUSDT",
                side="sell",
                entry_price=50000.0,
                stop_loss_price=49000.0,
            )

    def test_atr_sizing_missing_atr(self, controller: Any) -> None:
        """ATR sizing without atr_value should raise."""
        with pytest.raises(ValueError, match="atr_value"):
            controller.calculate_position_size(
                account_id="acc_001",
                symbol="BTCUSDT",
                side="buy",
                entry_price=50000.0,
                stop_loss_price=49000.0,
                method="atr_based",
            )

    def test_kelly_sizing_missing_params(self, controller: Any) -> None:
        """Kelly sizing without required params should raise."""
        with pytest.raises(ValueError, match="win_rate"):
            controller.calculate_position_size(
                account_id="acc_001",
                symbol="BTCUSDT",
                side="buy",
                entry_price=50000.0,
                stop_loss_price=49000.0,
                method="kelly",
            )

    def test_atr_sizing_via_controller(self, controller: Any) -> None:
        """ATR sizing through controller should return valid result."""
        result = controller.calculate_position_size(
            account_id="acc_001",
            symbol="BTCUSDT",
            side="buy",
            entry_price=50000.0,
            stop_loss_price=49000.0,
            method="atr_based",
            atr_value=500.0,
        )
        assert result.quantity > 0
        assert result.sizing_method == "atr_based"

    def test_kelly_sizing_via_controller(self, controller: Any) -> None:
        """Kelly sizing through controller should return valid result."""
        result = controller.calculate_position_size(
            account_id="acc_001",
            symbol="BTCUSDT",
            side="buy",
            entry_price=50000.0,
            stop_loss_price=49000.0,
            method="kelly",
            win_rate=0.6,
            avg_win=200.0,
            avg_loss=100.0,
        )
        assert result.quantity > 0
        assert result.sizing_method == "kelly"

    def test_zero_available_capital(
        self,
        mock_store: MagicMock,
        balanced_profile: RiskProfileConfig,
    ) -> None:
        """Zero available capital should return zero quantity."""
        from src.core.risk.controller import RiskController

        # Set cash very low so available = 0 after reserves
        # equity = cash + positions must hold, so adjust both
        account = mock_store.get_account.return_value
        account.balance_usdt = 1000.0
        account.equity_usdt = 10000.0  # equity stays 10000

        # Need positions to make up the difference
        pos = MagicMock()
        pos.size = 1.0
        pos.current_price = 9000.0  # 1 * 9000 = 9000 positions value
        mock_store.get_open_positions.return_value = [pos]

        manager = MagicMock(spec=RiskProfileManager)
        manager.get_profile.return_value = balanced_profile
        ctrl = RiskController(store=mock_store, profile_manager=manager)

        result = ctrl.calculate_position_size(
            account_id="acc_001",
            symbol="BTCUSDT",
            side="buy",
            entry_price=50000.0,
            stop_loss_price=49000.0,
        )
        assert result.quantity == 0.0
        assert "no_available_capital" in result.adjustments_applied


class TestRiskControllerRejectionPaths:
    """Test each rejection path in validate_order pipeline."""

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        """Create mock DataStore with configurable state."""
        store = MagicMock(spec=DataStore)

        account = MagicMock()
        account.equity_usdt = 10000.0
        account.balance_usdt = 10000.0
        account.profile = MagicMock()
        account.profile.value = "balanced"
        account.regime = "unknown"
        store.get_account.return_value = account

        state = MagicMock()
        state.kill_switch_active = False
        state.kill_switch_reason = None
        store.get_system_state.return_value = state

        store.get_open_positions.return_value = []
        store.get_pnl_for_date.return_value = None
        store.get_pnl_history.return_value = []

        return store

    @pytest.fixture
    def controller(
        self,
        mock_store: MagicMock,
        balanced_profile: RiskProfileConfig,
    ) -> Any:
        """Create RiskController with mocks."""
        from src.core.risk.controller import RiskController

        manager = MagicMock(spec=RiskProfileManager)
        manager.get_profile.return_value = balanced_profile
        return RiskController(store=mock_store, profile_manager=manager)

    def test_daily_loss_rejection(
        self,
        controller: Any,
        mock_store: MagicMock,
    ) -> None:
        """Daily loss exceeding limit should reject at check 2."""
        pnl_record = MagicMock()
        pnl_record.total_pnl = -500.0  # 5% loss > 3% limit
        pnl_record.drawdown_pct = 0.0
        mock_store.get_pnl_for_date.return_value = pnl_record

        order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.001,
            price=50000.0,
        )
        results = controller.validate_order(order)
        failed = [r for r in results if not r.approved]
        assert len(failed) == 1
        assert failed[0].check_name == "daily_loss_limit"

    def test_weekly_loss_rejection(
        self,
        controller: Any,
        mock_store: MagicMock,
    ) -> None:
        """Weekly loss exceeding limit should reject at check 3."""
        # Make daily PnL pass (within 3% limit)
        daily_pnl = MagicMock()
        daily_pnl.total_pnl = -100.0  # 1% loss < 3% limit
        daily_pnl.drawdown_pct = 0.0
        mock_store.get_pnl_for_date.return_value = daily_pnl

        # Make weekly PnL fail (exceed 7% limit)
        weekly_record = MagicMock()
        weekly_record.total_pnl = -800.0  # Will sum to 8% > 7%
        mock_store.get_pnl_history.return_value = [weekly_record]

        order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.001,
            price=50000.0,
        )
        results = controller.validate_order(order)
        failed = [r for r in results if not r.approved]
        assert len(failed) == 1
        assert failed[0].check_name == "weekly_loss_limit"

    def test_drawdown_rejection(
        self,
        controller: Any,
        mock_store: MagicMock,
    ) -> None:
        """Drawdown exceeding limit should reject at check 4."""
        pnl_record = MagicMock()
        pnl_record.total_pnl = -50.0  # Small daily loss
        pnl_record.drawdown_pct = 20.0  # 20% > 15% limit
        mock_store.get_pnl_for_date.return_value = pnl_record

        order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.001,
            price=50000.0,
        )
        results = controller.validate_order(order)
        failed = [r for r in results if not r.approved]
        assert len(failed) == 1
        assert failed[0].check_name == "max_drawdown"

    def test_max_positions_rejection(
        self,
        controller: Any,
        mock_store: MagicMock,
    ) -> None:
        """Exceeding max positions should reject at check 5."""
        # Create 10 positions (balanced max = 10)
        positions = []
        for i in range(10):
            pos = MagicMock()
            pos.symbol = f"SYMBOL{i}"
            pos.side = MagicMock()
            pos.side.value = "long"
            pos.size = 0.01
            pos.current_price = 1000.0
            positions.append(pos)
        mock_store.get_open_positions.return_value = positions

        # Adjust account to match positions value
        account = mock_store.get_account.return_value
        account.balance_usdt = 9900.0
        account.equity_usdt = 10000.0

        order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="NEWCOIN",
            side="buy",
            quantity=0.001,
            price=50000.0,
        )
        results = controller.validate_order(order)
        failed = [r for r in results if not r.approved]
        assert len(failed) == 1
        assert failed[0].check_name == "max_positions"

    def test_position_size_rejection(
        self,
        controller: Any,
    ) -> None:
        """Large position should fail position_size check."""
        # Concentration check passes for equity 100000 at 30%
        # but position_size check at 5% fails for 6000/100000 = 6%
        # Need to craft: passes concentration (< 30%) but fails size (> 5%)
        order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.02,
            price=50000.0,
        )
        # 0.02 * 50000 = 1000 = 10% of 10000 > 5% max_position_size
        # But also > 30% concentration? No: 1000/10000 = 10% < 30%
        results = controller.validate_order(order)
        failed = [r for r in results if not r.approved]
        assert len(failed) == 1
        assert failed[0].check_name == "position_size"


class TestRiskControllerEdgeCases:
    """Test edge cases in RiskController."""

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        """Create mock DataStore."""
        store = MagicMock(spec=DataStore)

        account = MagicMock()
        account.equity_usdt = 10000.0
        account.balance_usdt = 10000.0
        account.profile = MagicMock()
        account.profile.value = "balanced"
        account.regime = "trending_up"
        store.get_account.return_value = account

        state = MagicMock()
        state.kill_switch_active = False
        store.get_system_state.return_value = state

        store.get_open_positions.return_value = []
        store.get_pnl_for_date.return_value = None
        store.get_pnl_history.return_value = []

        return store

    @pytest.fixture
    def controller(
        self,
        mock_store: MagicMock,
        balanced_profile: RiskProfileConfig,
    ) -> Any:
        """Create RiskController with mocks."""
        from src.core.risk.controller import RiskController

        manager = MagicMock(spec=RiskProfileManager)
        manager.get_profile.return_value = balanced_profile
        return RiskController(store=mock_store, profile_manager=manager)

    def test_account_not_found_portfolio(
        self,
        controller: Any,
        mock_store: MagicMock,
    ) -> None:
        """Account not found should raise ValueError."""
        mock_store.get_account.return_value = None
        with pytest.raises(ValueError, match="Account not found"):
            controller.get_portfolio_state("nonexistent")

    def test_account_not_found_risk_profile(
        self,
        controller: Any,
        mock_store: MagicMock,
    ) -> None:
        """Account not found in _get_risk_profile should raise ValueError."""
        mock_store.get_account.return_value = None
        with pytest.raises(ValueError, match="Account not found"):
            controller._get_risk_profile("nonexistent")

    def test_portfolio_with_drawdown_from_pnl(
        self,
        controller: Any,
        mock_store: MagicMock,
    ) -> None:
        """Portfolio should pick up drawdown_pct from PnL record."""
        pnl_record = MagicMock()
        pnl_record.total_pnl = -200.0
        pnl_record.drawdown_pct = 5.0
        mock_store.get_pnl_for_date.return_value = pnl_record

        portfolio = controller.get_portfolio_state("acc_001")
        assert portfolio.drawdown_pct == 5.0
        # peak_equity = 10000 / (1 - 5/100) = 10000 / 0.95 ~ 10526
        assert portfolio.peak_equity > portfolio.total_equity

    def test_validate_order_request_nan_price(
        self,
        controller: Any,
    ) -> None:
        """_validate_order_request should reject NaN price."""
        # Use object.__new__ to bypass frozen dataclass __init__ validation
        order = object.__new__(OrderRequest)
        object.__setattr__(order, "account_id", "acc_001")
        object.__setattr__(order, "strategy_id", "str_001")
        object.__setattr__(order, "symbol", "BTCUSDT")
        object.__setattr__(order, "side", "buy")
        object.__setattr__(order, "quantity", 0.1)
        object.__setattr__(order, "price", float("nan"))
        object.__setattr__(order, "stop_loss_price", None)

        with pytest.raises(ValueError, match="price must be finite"):
            controller._validate_order_request(order)

    def test_validate_order_request_negative_price(
        self,
        controller: Any,
    ) -> None:
        """_validate_order_request should reject negative price."""
        order = object.__new__(OrderRequest)
        object.__setattr__(order, "account_id", "acc_001")
        object.__setattr__(order, "strategy_id", "str_001")
        object.__setattr__(order, "symbol", "BTCUSDT")
        object.__setattr__(order, "side", "buy")
        object.__setattr__(order, "quantity", 0.1)
        object.__setattr__(order, "price", -100.0)
        object.__setattr__(order, "stop_loss_price", None)

        with pytest.raises(ValueError, match="price must be positive"):
            controller._validate_order_request(order)

    def test_validate_order_request_nan_quantity(
        self,
        controller: Any,
    ) -> None:
        """_validate_order_request should reject NaN quantity."""
        order = object.__new__(OrderRequest)
        object.__setattr__(order, "account_id", "acc_001")
        object.__setattr__(order, "strategy_id", "str_001")
        object.__setattr__(order, "symbol", "BTCUSDT")
        object.__setattr__(order, "side", "buy")
        object.__setattr__(order, "quantity", float("nan"))
        object.__setattr__(order, "price", 50000.0)
        object.__setattr__(order, "stop_loss_price", None)

        with pytest.raises(ValueError, match="quantity must be finite"):
            controller._validate_order_request(order)

    def test_validate_order_request_negative_quantity(
        self,
        controller: Any,
    ) -> None:
        """_validate_order_request should reject negative quantity."""
        order = object.__new__(OrderRequest)
        object.__setattr__(order, "account_id", "acc_001")
        object.__setattr__(order, "strategy_id", "str_001")
        object.__setattr__(order, "symbol", "BTCUSDT")
        object.__setattr__(order, "side", "buy")
        object.__setattr__(order, "quantity", -1.0)
        object.__setattr__(order, "price", 50000.0)
        object.__setattr__(order, "stop_loss_price", None)

        with pytest.raises(ValueError, match="quantity must be positive"):
            controller._validate_order_request(order)


# ===========================================================================
# Additional sizing validation tests
# ===========================================================================


class TestSizingValidationEdgeCases:
    """Test edge cases in sizing validation helpers."""

    def test_negative_atr_multiplier(self) -> None:
        """Negative ATR multiplier should raise ValueError."""
        with pytest.raises(ValueError, match="atr_multiplier"):
            calculate_atr_size(
                capital=10000.0,
                risk_pct=0.02,
                entry_price=50000.0,
                stop_loss_price=49000.0,
                atr_value=500.0,
                atr_multiplier=-1.0,
            )

    def test_negative_avg_loss_kelly(self) -> None:
        """Negative avg_loss in Kelly should raise ValueError."""
        with pytest.raises(ValueError, match="avg_loss"):
            calculate_kelly_size(
                capital=10000.0,
                entry_price=50000.0,
                stop_loss_price=49000.0,
                win_rate=0.6,
                avg_win=200.0,
                avg_loss=-100.0,
            )

    def test_invalid_kelly_fraction(self) -> None:
        """Kelly fraction outside 0-1 should raise ValueError."""
        with pytest.raises(ValueError, match="kelly_fraction"):
            calculate_kelly_size(
                capital=10000.0,
                entry_price=50000.0,
                stop_loss_price=49000.0,
                win_rate=0.6,
                avg_win=200.0,
                avg_loss=100.0,
                kelly_fraction=0.0,
            )

    def test_validate_allocation_insufficient_capital(self) -> None:
        """Allocation exceeding available capital should reject."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=3500.0,  # Available = 3500 - 3000 reserve = 500
            positions_value=6500.0,
        )
        approved, reason = validate_allocation(
            requested_pct=4.0,  # 4% of 10000 = 400, but below 5% max for new
            is_proven=False,
            portfolio=portfolio,
        )
        # 4% of 10000 = 400, available = 500 -> should pass
        # Need to request more: 4.5% of 10000 = 450 < 500 still passes
        # Actually available = 3500 - 3000 = 500
        # Request 5% new max = 500, equal to available
        approved2, reason2 = validate_allocation(
            requested_pct=4.9,  # 4.9% of 10000 = 490 < 500 available
            is_proven=False,
            portfolio=portfolio,
        )
        assert approved2 is True

        # Now test insufficient: cash = 3100, reserved = 3000, available = 100
        tight_portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=3100.0,
            positions_value=6900.0,
        )
        approved3, reason3 = validate_allocation(
            requested_pct=4.0,  # 4% of 10000 = 400 > 100 available
            is_proven=False,
            portfolio=tight_portfolio,
        )
        assert approved3 is False
        assert "Insufficient" in reason3

    def test_nan_capital_sizing(self) -> None:
        """NaN capital should raise ValueError."""
        with pytest.raises(ValueError, match="capital"):
            calculate_fixed_risk_size(
                capital=float("nan"),
                risk_pct=0.02,
                entry_price=50000.0,
                stop_loss_price=49000.0,
            )

    def test_inf_capital_sizing(self) -> None:
        """Infinity capital should raise ValueError."""
        with pytest.raises(ValueError, match="capital"):
            calculate_fixed_risk_size(
                capital=float("inf"),
                risk_pct=0.02,
                entry_price=50000.0,
                stop_loss_price=49000.0,
            )

    def test_risk_pct_too_high(self) -> None:
        """Risk percentage > 100% should raise ValueError."""
        with pytest.raises(ValueError, match="risk_pct"):
            calculate_fixed_risk_size(
                capital=10000.0,
                risk_pct=1.5,
                entry_price=50000.0,
                stop_loss_price=49000.0,
            )

    def test_negative_risk_pct(self) -> None:
        """Negative risk percentage should raise ValueError."""
        with pytest.raises(ValueError, match="risk_pct"):
            calculate_fixed_risk_size(
                capital=10000.0,
                risk_pct=-0.02,
                entry_price=50000.0,
                stop_loss_price=49000.0,
            )

    def test_negative_entry_price(self) -> None:
        """Negative entry price should raise ValueError."""
        with pytest.raises(ValueError, match="entry_price"):
            calculate_fixed_risk_size(
                capital=10000.0,
                risk_pct=0.02,
                entry_price=-50000.0,
                stop_loss_price=49000.0,
            )

    def test_nan_entry_price(self) -> None:
        """NaN entry price should raise ValueError."""
        with pytest.raises(ValueError, match="entry_price"):
            calculate_fixed_risk_size(
                capital=10000.0,
                risk_pct=0.02,
                entry_price=float("nan"),
                stop_loss_price=49000.0,
            )

    def test_negative_stop_loss(self) -> None:
        """Negative stop loss should raise ValueError."""
        with pytest.raises(ValueError, match="stop_loss_price"):
            calculate_fixed_risk_size(
                capital=10000.0,
                risk_pct=0.02,
                entry_price=50000.0,
                stop_loss_price=-49000.0,
            )

    def test_nan_stop_loss(self) -> None:
        """NaN stop loss should raise ValueError."""
        with pytest.raises(ValueError, match="stop_loss_price"):
            calculate_fixed_risk_size(
                capital=10000.0,
                risk_pct=0.02,
                entry_price=50000.0,
                stop_loss_price=float("nan"),
            )

    def test_inf_entry_price(self) -> None:
        """Infinity entry price should raise ValueError."""
        with pytest.raises(ValueError, match="entry_price"):
            calculate_fixed_risk_size(
                capital=10000.0,
                risk_pct=0.02,
                entry_price=float("inf"),
                stop_loss_price=49000.0,
            )


# ===========================================================================
# Additional coverage tests for types.py
# ===========================================================================


class TestOrderRequestValidation:
    """Test OrderRequest __post_init__ validation."""

    def test_empty_symbol(self) -> None:
        """Empty symbol should raise ValueError."""
        with pytest.raises(ValueError, match="symbol is required"):
            OrderRequest(
                account_id="acc_001",
                strategy_id="str_001",
                symbol="",  # Empty symbol
                side="buy",
                quantity=0.1,
                price=50000.0,
            )

    def test_negative_stop_loss_price(self) -> None:
        """Negative stop_loss_price should raise ValueError."""
        with pytest.raises(ValueError, match="stop_loss_price must be positive"):
            OrderRequest(
                account_id="acc_001",
                strategy_id="str_001",
                symbol="BTCUSDT",
                side="buy",
                quantity=0.1,
                price=50000.0,
                stop_loss_price=-100.0,  # Negative stop loss
            )

    def test_zero_stop_loss_price(self) -> None:
        """Zero stop_loss_price should raise ValueError."""
        with pytest.raises(ValueError, match="stop_loss_price must be positive"):
            OrderRequest(
                account_id="acc_001",
                strategy_id="str_001",
                symbol="BTCUSDT",
                side="buy",
                quantity=0.1,
                price=50000.0,
                stop_loss_price=0.0,  # Zero stop loss
            )


class TestPositionSizeResultValidation:
    """Test PositionSizeResult __post_init__ validation."""

    def test_negative_quantity_in_result(self) -> None:
        """Negative quantity in PositionSizeResult should raise ValueError."""
        with pytest.raises(ValueError, match="quantity must be >= 0"):
            PositionSizeResult(
                quantity=-1.0,  # Negative quantity
                notional_value=5000.0,
                risk_amount=100.0,
                risk_pct=0.02,
                sizing_method="fixed_risk",
                stop_loss_price=49000.0,
                entry_price=50000.0,
                adjustments_applied=(),
            )


# ===========================================================================
# Additional coverage tests for checks.py
# ===========================================================================


class TestChecksEdgeCases:
    """Test edge cases in risk check functions."""

    def test_weekly_loss_limit_zero_equity(self, balanced_profile: RiskProfileConfig) -> None:
        """Weekly loss check with zero equity should reject."""
        from src.core.risk.checks import check_weekly_loss_limit

        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=0.0,  # Zero equity
            cash_balance=0.0,
            positions_value=0.0,
        )

        result = check_weekly_loss_limit(portfolio, balanced_profile)

        assert not result.approved
        assert "zero or negative equity" in result.rejection_reason

    def test_position_size_check_zero_equity(self, balanced_profile: RiskProfileConfig) -> None:
        """Position size check with zero equity should reject."""
        from src.core.risk.checks import check_position_size

        order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.1,
            price=50000.0,
        )

        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=0.0,  # Zero equity
            cash_balance=0.0,
            positions_value=0.0,
        )

        result = check_position_size(order, portfolio, balanced_profile)

        assert not result.approved
        assert "zero equity" in result.rejection_reason

    def test_max_positions_closing_position(self) -> None:
        """Closing a position when at max should be approved."""
        from src.core.risk.checks import check_max_positions
        from unittest.mock import MagicMock

        # Create sell order for existing position
        order = OrderRequest(
            account_id="acc_001",
            strategy_id="str_001",
            symbol="BTCUSDT",  # Existing position
            side="sell",  # Closing position
            quantity=0.1,
            price=50000.0,
        )

        # Portfolio at max positions with BTCUSDT position
        pos1 = MagicMock()
        pos1.symbol = "BTCUSDT"
        pos1.side = MagicMock()
        pos1.side.value = "long"

        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=5000.0,
            positions_value=5000.0,
            open_positions=(pos1,),
        )

        # Create profile with max_open_positions = 1
        profile = RiskProfileConfig(
            name="test",
            max_position_size_pct=2.0,
            max_open_positions=1,  # At max
            max_concentration_pct=30.0,
            daily_loss_limit_pct=2.0,
            weekly_loss_limit_pct=5.0,
            max_drawdown_pct=10.0,
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

        result = check_max_positions(order, portfolio, profile)

        # Should approve closing position even at max
        assert result.approved
