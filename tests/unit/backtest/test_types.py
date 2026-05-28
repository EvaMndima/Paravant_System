"""Comprehensive unit tests for backtest types (BacktestConfig, TradeRecord, EquityPoint)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.strategy.backtest.types import BacktestConfig, EquityPoint, TradeRecord
from src.data.models.signal import SignalDirection


# ---------------------------------------------------------------------------
# BacktestConfig Tests
# ---------------------------------------------------------------------------


class TestBacktestConfig:
    """Tests for BacktestConfig frozen dataclass."""

    def test_default_values(self) -> None:
        """Default config should have sensible values."""
        config = BacktestConfig()
        assert config.initial_capital == 10_000.0
        assert config.commission_rate == 0.001
        assert config.slippage_rate == 0.0005
        assert config.use_next_bar_open is True
        assert config.risk_free_rate == 0.02
        assert config.position_size_pct == 0.35

    def test_custom_values(self) -> None:
        """Config accepts custom values."""
        config = BacktestConfig(
            initial_capital=50_000.0,
            commission_rate=0.002,
            slippage_rate=0.001,
            risk_free_rate=0.05,
            position_size_pct=0.80,
        )
        assert config.initial_capital == 50_000.0
        assert config.commission_rate == 0.002
        assert config.slippage_rate == 0.001
        assert config.risk_free_rate == 0.05
        assert config.position_size_pct == 0.80

    def test_frozen(self) -> None:
        """Config should be immutable."""
        config = BacktestConfig()
        with pytest.raises(AttributeError):
            config.initial_capital = 999.0  # type: ignore[misc]

    def test_execution_model_defaults(self) -> None:
        """Default config preserves long-short futures behavior (allow_shorts)."""
        config = BacktestConfig()
        assert config.allow_shorts is True
        assert config.funding_rate_per_8h == 0.0

    def test_spot_long_only_config(self) -> None:
        """Spot mode disables shorts and has no funding."""
        config = BacktestConfig(allow_shorts=False, funding_rate_per_8h=0.0)
        assert config.allow_shorts is False
        assert config.funding_rate_per_8h == 0.0

    def test_futures_config(self) -> None:
        """Futures mode allows shorts with a funding drag."""
        config = BacktestConfig(allow_shorts=True, funding_rate_per_8h=0.0001)
        assert config.allow_shorts is True
        assert config.funding_rate_per_8h == pytest.approx(0.0001)

    def test_negative_funding_rejected(self) -> None:
        """Negative funding rate should raise ValueError."""
        with pytest.raises(ValueError, match="funding_rate_per_8h"):
            BacktestConfig(funding_rate_per_8h=-0.0001)

    def test_absurd_funding_rejected(self) -> None:
        """Funding rate >= 1% per 8h is implausible and rejected."""
        with pytest.raises(ValueError, match="funding_rate_per_8h"):
            BacktestConfig(funding_rate_per_8h=0.02)

    def test_negative_capital_rejected(self) -> None:
        """Negative initial capital should raise ValueError."""
        with pytest.raises(ValueError, match="initial_capital"):
            BacktestConfig(initial_capital=-1000.0)

    def test_zero_capital_rejected(self) -> None:
        """Zero initial capital should raise ValueError."""
        with pytest.raises(ValueError, match="initial_capital"):
            BacktestConfig(initial_capital=0.0)

    def test_negative_commission_rejected(self) -> None:
        """Negative commission rate should raise ValueError."""
        with pytest.raises(ValueError, match="commission_rate"):
            BacktestConfig(commission_rate=-0.01)

    def test_negative_slippage_rejected(self) -> None:
        """Negative slippage rate should raise ValueError."""
        with pytest.raises(ValueError, match="slippage_rate"):
            BacktestConfig(slippage_rate=-0.01)

    def test_position_size_zero_rejected(self) -> None:
        """Zero position size should raise ValueError."""
        with pytest.raises(ValueError, match="position_size_pct"):
            BacktestConfig(position_size_pct=0.0)

    def test_position_size_over_one_rejected(self) -> None:
        """Position size > 1 should raise ValueError."""
        with pytest.raises(ValueError, match="position_size_pct"):
            BacktestConfig(position_size_pct=1.5)

    def test_nan_capital_rejected(self) -> None:
        """NaN capital should raise ValueError."""
        with pytest.raises(ValueError):
            BacktestConfig(initial_capital=float("nan"))

    def test_inf_capital_rejected(self) -> None:
        """Infinity capital should raise ValueError."""
        with pytest.raises(ValueError):
            BacktestConfig(initial_capital=float("inf"))

    def test_commission_rate_at_one_rejected(self) -> None:
        """Commission rate >= 1.0 should raise ValueError."""
        with pytest.raises(ValueError, match="commission_rate"):
            BacktestConfig(commission_rate=1.0)


# ---------------------------------------------------------------------------
# TradeRecord Tests
# ---------------------------------------------------------------------------


class TestTradeRecord:
    """Tests for TradeRecord frozen dataclass."""

    @pytest.fixture
    def sample_trade(self) -> TradeRecord:
        """Create a sample winning trade."""
        return TradeRecord(
            entry_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            exit_time=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            entry_price=42000.0,
            exit_price=42500.0,
            quantity=0.1,
            entry_commission=4.2,
            exit_commission=4.25,
            slippage_cost=2.1,
            realized_pnl=39.45,
            return_pct=0.94,
        )

    def test_is_winner(self, sample_trade: TradeRecord) -> None:
        """Positive PnL trade should be a winner."""
        assert sample_trade.is_winner is True

    def test_is_loser(self) -> None:
        """Negative PnL trade should not be a winner."""
        trade = TradeRecord(
            entry_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            exit_time=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            entry_price=42000.0,
            exit_price=41500.0,
            quantity=0.1,
            entry_commission=4.2,
            exit_commission=4.15,
            slippage_cost=2.1,
            realized_pnl=-60.45,
            return_pct=-1.44,
        )
        assert trade.is_winner is False

    def test_total_commission(self, sample_trade: TradeRecord) -> None:
        """Total commission should sum entry + exit."""
        assert sample_trade.total_commission == pytest.approx(8.45, abs=0.01)

    def test_duration_hours(self, sample_trade: TradeRecord) -> None:
        """Duration should calculate correctly."""
        assert sample_trade.duration_hours == pytest.approx(4.0, abs=0.01)

    def test_to_dict(self, sample_trade: TradeRecord) -> None:
        """to_dict should return serializable dictionary."""
        d = sample_trade.to_dict()
        assert d["symbol"] == "BTCUSDT"
        assert d["direction"] == "long"
        assert d["entry_price"] == 42000.0
        assert d["realized_pnl"] == 39.45
        assert "entry_time" in d
        assert "exit_time" in d

    def test_frozen(self, sample_trade: TradeRecord) -> None:
        """Trade records should be immutable."""
        with pytest.raises(AttributeError):
            sample_trade.realized_pnl = 100.0  # type: ignore[misc]

    def test_exit_before_entry_rejected(self) -> None:
        """Exit time before entry time should raise ValueError."""
        with pytest.raises(ValueError, match="exit_time"):
            TradeRecord(
                entry_time=datetime(2025, 1, 2, 10, 0, tzinfo=timezone.utc),
                exit_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
                symbol="BTCUSDT",
                direction=SignalDirection.LONG,
                entry_price=42000.0,
                exit_price=42500.0,
                quantity=0.1,
                entry_commission=4.2,
                exit_commission=4.25,
                slippage_cost=2.1,
                realized_pnl=39.45,
                return_pct=0.94,
            )

    def test_empty_symbol_rejected(self) -> None:
        """Empty symbol should raise ValueError."""
        with pytest.raises(ValueError, match="symbol"):
            TradeRecord(
                entry_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
                exit_time=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
                symbol="",
                direction=SignalDirection.LONG,
                entry_price=42000.0,
                exit_price=42500.0,
                quantity=0.1,
                entry_commission=4.2,
                exit_commission=4.25,
                slippage_cost=2.1,
                realized_pnl=39.45,
                return_pct=0.94,
            )

    def test_nan_entry_price_rejected(self) -> None:
        """NaN entry price should raise ValueError."""
        with pytest.raises(ValueError):
            TradeRecord(
                entry_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
                exit_time=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
                symbol="BTCUSDT",
                direction=SignalDirection.LONG,
                entry_price=float("nan"),
                exit_price=42500.0,
                quantity=0.1,
                entry_commission=4.2,
                exit_commission=4.25,
                slippage_cost=2.1,
                realized_pnl=39.45,
                return_pct=0.94,
            )

    def test_zero_quantity_rejected(self) -> None:
        """Zero quantity should raise ValueError."""
        with pytest.raises(ValueError, match="quantity"):
            TradeRecord(
                entry_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
                exit_time=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
                symbol="BTCUSDT",
                direction=SignalDirection.LONG,
                entry_price=42000.0,
                exit_price=42500.0,
                quantity=0.0,
                entry_commission=4.2,
                exit_commission=4.25,
                slippage_cost=2.1,
                realized_pnl=39.45,
                return_pct=0.94,
            )


# ---------------------------------------------------------------------------
# EquityPoint Tests
# ---------------------------------------------------------------------------


class TestEquityPoint:
    """Tests for EquityPoint frozen dataclass."""

    def test_creation(self) -> None:
        """EquityPoint should store values correctly."""
        point = EquityPoint(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            equity=10500.0,
            cash=500.0,
            position_value=10000.0,
        )
        assert point.equity == 10500.0
        assert point.cash == 500.0
        assert point.position_value == 10000.0

    def test_to_dict(self) -> None:
        """to_dict should serialize correctly."""
        point = EquityPoint(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            equity=10500.0,
            cash=500.0,
            position_value=10000.0,
        )
        d = point.to_dict()
        assert d["equity"] == 10500.0
        assert "timestamp" in d

    def test_frozen(self) -> None:
        """Equity points should be immutable."""
        point = EquityPoint(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            equity=10500.0,
            cash=500.0,
            position_value=10000.0,
        )
        with pytest.raises(AttributeError):
            point.equity = 999.0  # type: ignore[misc]

    def test_nan_equity_rejected(self) -> None:
        """NaN equity should raise ValueError."""
        with pytest.raises(ValueError):
            EquityPoint(
                timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                equity=float("nan"),
                cash=500.0,
                position_value=10000.0,
            )

    def test_inf_equity_rejected(self) -> None:
        """Infinity equity should raise ValueError."""
        with pytest.raises(ValueError):
            EquityPoint(
                timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                equity=float("inf"),
                cash=500.0,
                position_value=10000.0,
            )

    def test_naive_timestamp_rejected(self) -> None:
        """Timezone-naive timestamp should raise ValueError."""
        with pytest.raises(ValueError, match="timezone-aware"):
            EquityPoint(
                timestamp=datetime(2025, 1, 1, 12, 0),
                equity=10500.0,
                cash=500.0,
                position_value=10000.0,
            )
