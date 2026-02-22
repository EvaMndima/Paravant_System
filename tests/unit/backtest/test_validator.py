"""Comprehensive unit tests for BacktestValidator and BacktestResult."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.strategy.backtest.metrics import BacktestMetrics
from src.core.strategy.backtest.result import BacktestResult
from src.core.strategy.backtest.validator import BacktestValidator, ValidationThresholds


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_result(
    sharpe: float = 1.0,
    max_dd: float = 10.0,
    win_rate: float = 55.0,
    profit_factor: float = 1.5,
    total_trades: int = 100,
) -> BacktestResult:
    """Create a BacktestResult with the specified metrics."""
    metrics = BacktestMetrics(
        total_return_pct=15.0,
        annualized_return_pct=42.5,
        sharpe_ratio=sharpe,
        sortino_ratio=sharpe * 1.2,
        calmar_ratio=42.5 / max(max_dd, 0.001),
        max_drawdown_pct=max_dd,
        max_drawdown_duration_days=5.0,
        total_trades=total_trades,
        winning_trades=int(total_trades * win_rate / 100),
        losing_trades=total_trades - int(total_trades * win_rate / 100),
        win_rate_pct=win_rate,
        profit_factor=profit_factor,
        expectancy=25.0,
        avg_win_pct=1.0,
        avg_loss_pct=0.75,
        largest_win=500.0,
        largest_loss=200.0,
        avg_trade_duration_hours=4.0,
        max_trade_duration_hours=12.0,
    )
    return BacktestResult(
        strategy_id="test-001",
        strategy_name="TestStrategy",
        template_id="Simple_MA",
        symbol="BTCUSDT",
        timeframe="1h",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 4, 1, tzinfo=timezone.utc),
        initial_capital=10000.0,
        final_capital=11500.0,
        metrics=metrics,
    )


# ---------------------------------------------------------------------------
# ValidationThresholds Tests
# ---------------------------------------------------------------------------


class TestValidationThresholds:
    """Tests for ValidationThresholds."""

    def test_default_values(self) -> None:
        """Default thresholds should match PRD §3.6 validation gates."""
        t = ValidationThresholds()
        assert t.min_sharpe_ratio == 1.0      # PRD §3.6: sharpe >= 1.0
        assert t.max_drawdown_pct == 15.0
        assert t.min_win_rate_pct == 50.0     # PRD §3.6: win_rate >= 50%
        assert t.min_profit_factor == 1.3     # PRD §3.6: profit_factor >= 1.3
        assert t.min_num_trades == 100        # PRD §3.6: trades >= 100

    def test_custom_values(self) -> None:
        """Custom thresholds should be accepted."""
        t = ValidationThresholds(
            min_sharpe_ratio=1.0,
            max_drawdown_pct=10.0,
            min_win_rate_pct=50.0,
            min_profit_factor=1.5,
            min_num_trades=100,
        )
        assert t.min_sharpe_ratio == 1.0
        assert t.min_num_trades == 100

    def test_frozen(self) -> None:
        """Thresholds should be immutable."""
        t = ValidationThresholds()
        with pytest.raises(AttributeError):
            t.min_sharpe_ratio = 99.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BacktestValidator Tests
# ---------------------------------------------------------------------------


class TestBacktestValidator:
    """Tests for BacktestValidator.validate method."""

    def test_passing_result(self) -> None:
        """Result meeting all thresholds should pass."""
        result = _make_result(
            sharpe=1.0,
            max_dd=10.0,
            win_rate=55.0,
            profit_factor=1.5,
            total_trades=100,
        )
        passed, errors = BacktestValidator.validate(result)
        assert passed is True
        assert errors == []

    def test_failing_sharpe(self) -> None:
        """Low Sharpe ratio should fail validation."""
        result = _make_result(sharpe=0.1)
        passed, errors = BacktestValidator.validate(result)
        assert passed is False
        assert any("Sharpe" in e for e in errors)

    def test_failing_max_drawdown(self) -> None:
        """High drawdown should fail validation."""
        result = _make_result(max_dd=25.0)
        passed, errors = BacktestValidator.validate(result)
        assert passed is False
        assert any("drawdown" in e.lower() for e in errors)

    def test_failing_win_rate(self) -> None:
        """Low win rate should fail validation."""
        result = _make_result(win_rate=20.0)
        passed, errors = BacktestValidator.validate(result)
        assert passed is False
        assert any("Win rate" in e for e in errors)

    def test_failing_profit_factor(self) -> None:
        """Low profit factor should fail validation."""
        result = _make_result(profit_factor=0.5)
        passed, errors = BacktestValidator.validate(result)
        assert passed is False
        assert any("Profit factor" in e for e in errors)

    def test_failing_trade_count(self) -> None:
        """Too few trades should fail validation."""
        result = _make_result(total_trades=5)
        passed, errors = BacktestValidator.validate(result)
        assert passed is False
        assert any("trades" in e.lower() for e in errors)

    def test_multiple_failures(self) -> None:
        """Multiple failures should report all errors."""
        result = _make_result(
            sharpe=0.1,
            max_dd=25.0,
            win_rate=20.0,
            profit_factor=0.5,
            total_trades=5,
        )
        passed, errors = BacktestValidator.validate(result)
        assert passed is False
        assert len(errors) == 5

    def test_custom_thresholds(self) -> None:
        """Custom thresholds should override defaults."""
        result = _make_result(sharpe=0.3)  # would fail default threshold (1.0)
        thresholds = ValidationThresholds(min_sharpe_ratio=0.2)
        passed, _ = BacktestValidator.validate(result, thresholds)
        assert passed is True


# ---------------------------------------------------------------------------
# BacktestResult Tests
# ---------------------------------------------------------------------------


class TestBacktestResult:
    """Tests for BacktestResult dataclass."""

    def test_to_dict(self) -> None:
        """to_dict should serialize all fields."""
        result = _make_result()
        d = result.to_dict()
        assert d["strategy_id"] == "test-001"
        assert d["strategy_name"] == "TestStrategy"
        assert d["symbol"] == "BTCUSDT"
        assert "metrics" in d
        assert "equity_curve" in d
        assert "trade_log" in d
        assert "config" in d

    def test_summary(self) -> None:
        """summary() should produce readable output."""
        result = _make_result()
        text = result.summary()
        assert "TestStrategy" in text
        assert "BTCUSDT" in text
        assert "Sharpe" in text
        assert "Win Rate" in text

    def test_frozen(self) -> None:
        """Result should be immutable."""
        result = _make_result()
        with pytest.raises(AttributeError):
            result.strategy_id = "changed"  # type: ignore[misc]
