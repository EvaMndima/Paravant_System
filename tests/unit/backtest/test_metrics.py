"""Comprehensive unit tests for BacktestMetricsCalculator and BacktestMetrics."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.core.strategy.backtest.metrics import BacktestMetrics, BacktestMetricsCalculator
from src.core.strategy.backtest.types import BacktestConfig, EquityPoint, TradeRecord
from src.data.models.signal import SignalDirection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_trade(
    pnl: float,
    entry_price: float = 42000.0,
    exit_price: float = 42500.0,
    quantity: float = 0.1,
    hour_offset: int = 0,
    duration_hours: int = 4,
) -> TradeRecord:
    """Create a TradeRecord with the given PnL."""
    entry = datetime(2025, 1, 1, hour_offset % 24, 0, tzinfo=timezone.utc) + timedelta(
        days=hour_offset // 24
    )
    return TradeRecord(
        entry_time=entry,
        exit_time=entry + timedelta(hours=duration_hours),
        symbol="BTCUSDT",
        direction=SignalDirection.LONG,
        entry_price=entry_price,
        exit_price=exit_price,
        quantity=quantity,
        entry_commission=4.2,
        exit_commission=4.25,
        slippage_cost=2.0,
        realized_pnl=pnl,
        return_pct=(pnl / (entry_price * quantity)) * 100,
    )


def _make_equity_curve(values: list[float], start_hour: int = 0) -> list[EquityPoint]:
    """Create equity curve from a list of equity values."""
    points = []
    for i, v in enumerate(values):
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(hours=start_hour + i)
        points.append(
            EquityPoint(
                timestamp=ts,
                equity=v,
                cash=v * 0.5,
                position_value=v * 0.5,
            )
        )
    return points


class TestBacktestMetricsCalculator:
    """Tests for the BacktestMetricsCalculator.calculate method."""

    def test_no_trades_returns_empty_metrics(self) -> None:
        """Zero trades should produce empty metrics."""
        metrics = BacktestMetricsCalculator.calculate(
            trades=[],
            equity_points=_make_equity_curve([10000.0, 10000.0]),
            initial_capital=10000.0,
            config=BacktestConfig(),
        )
        assert metrics.total_trades == 0
        assert metrics.win_rate_pct == 0.0
        assert metrics.sharpe_ratio == 0.0

    def test_all_winners(self) -> None:
        """All winning trades should give 100% win rate."""
        trades = [
            _make_trade(pnl=50.0, hour_offset=i * 5)
            for i in range(10)
        ]
        equity = _make_equity_curve(
            [10000.0 + (i * 50) for i in range(50)]
        )
        metrics = BacktestMetricsCalculator.calculate(
            trades=trades,
            equity_points=equity,
            initial_capital=10000.0,
            config=BacktestConfig(),
        )
        assert metrics.total_trades == 10
        assert metrics.winning_trades == 10
        assert metrics.losing_trades == 0
        assert metrics.win_rate_pct == 100.0

    def test_all_losers(self) -> None:
        """All losing trades should give 0% win rate."""
        trades = [
            _make_trade(pnl=-30.0, hour_offset=i * 5)
            for i in range(5)
        ]
        equity = _make_equity_curve(
            [10000.0 - (i * 30) for i in range(25)]
        )
        metrics = BacktestMetricsCalculator.calculate(
            trades=trades,
            equity_points=equity,
            initial_capital=10000.0,
            config=BacktestConfig(),
        )
        assert metrics.winning_trades == 0
        assert metrics.win_rate_pct == 0.0
        assert metrics.profit_factor == 0.0

    def test_mixed_trades_win_rate(self) -> None:
        """Mixed trades should have correct win rate."""
        trades = [
            _make_trade(pnl=100.0, hour_offset=0),
            _make_trade(pnl=50.0, hour_offset=5),
            _make_trade(pnl=-30.0, hour_offset=10),
        ]
        equity = _make_equity_curve(
            [10000.0, 10100.0, 10150.0, 10120.0]
        )
        metrics = BacktestMetricsCalculator.calculate(
            trades=trades,
            equity_points=equity,
            initial_capital=10000.0,
            config=BacktestConfig(),
        )
        assert metrics.total_trades == 3
        assert metrics.winning_trades == 2
        assert metrics.losing_trades == 1
        assert metrics.win_rate_pct == pytest.approx(66.67, abs=0.1)

    def test_total_return_positive(self) -> None:
        """Positive equity growth should yield positive total return."""
        trades = [_make_trade(pnl=500.0)]
        equity = _make_equity_curve([10000.0, 10500.0])
        metrics = BacktestMetricsCalculator.calculate(
            trades=trades,
            equity_points=equity,
            initial_capital=10000.0,
            config=BacktestConfig(),
        )
        assert metrics.total_return_pct > 0

    def test_total_return_negative(self) -> None:
        """Negative equity change should yield negative total return."""
        trades = [_make_trade(pnl=-500.0)]
        equity = _make_equity_curve([10000.0, 9500.0])
        metrics = BacktestMetricsCalculator.calculate(
            trades=trades,
            equity_points=equity,
            initial_capital=10000.0,
            config=BacktestConfig(),
        )
        assert metrics.total_return_pct < 0

    def test_profit_factor_computation(self) -> None:
        """Profit factor = gross_profits / gross_losses."""
        trades = [
            _make_trade(pnl=200.0, hour_offset=0),
            _make_trade(pnl=-100.0, hour_offset=5),
        ]
        equity = _make_equity_curve([10000.0, 10200.0, 10100.0])
        metrics = BacktestMetricsCalculator.calculate(
            trades=trades,
            equity_points=equity,
            initial_capital=10000.0,
            config=BacktestConfig(),
        )
        assert metrics.profit_factor == pytest.approx(2.0, abs=0.01)

    def test_expectancy(self) -> None:
        """Expectancy = average PnL per trade."""
        trades = [
            _make_trade(pnl=100.0, hour_offset=0),
            _make_trade(pnl=-50.0, hour_offset=5),
        ]
        equity = _make_equity_curve([10000.0, 10100.0, 10050.0])
        metrics = BacktestMetricsCalculator.calculate(
            trades=trades,
            equity_points=equity,
            initial_capital=10000.0,
            config=BacktestConfig(),
        )
        assert metrics.expectancy == pytest.approx(25.0, abs=0.01)

    def test_max_drawdown(self) -> None:
        """Max drawdown should detect equity drops."""
        equity = _make_equity_curve(
            [10000.0, 10500.0, 9500.0, 9800.0, 10200.0]
        )
        trades = [_make_trade(pnl=-500.0)]
        metrics = BacktestMetricsCalculator.calculate(
            trades=trades,
            equity_points=equity,
            initial_capital=10000.0,
            config=BacktestConfig(),
        )
        # peak was 10500, trough was 9500 → dd = 1000/10500 ≈ 9.52%
        assert metrics.max_drawdown_pct > 0

    def test_trade_duration(self) -> None:
        """Average trade duration should be computed correctly."""
        trades = [
            _make_trade(pnl=50.0, duration_hours=2, hour_offset=0),
            _make_trade(pnl=-30.0, duration_hours=6, hour_offset=10),
        ]
        equity = _make_equity_curve([10000.0, 10050.0, 10020.0])
        metrics = BacktestMetricsCalculator.calculate(
            trades=trades,
            equity_points=equity,
            initial_capital=10000.0,
            config=BacktestConfig(),
        )
        assert metrics.avg_trade_duration_hours == pytest.approx(4.0, abs=0.01)


class TestBacktestMetrics:
    """Tests for BacktestMetrics dataclass."""

    def test_to_dict(self) -> None:
        """to_dict should serialize all fields."""
        metrics = BacktestMetrics(
            total_return_pct=10.0,
            annualized_return_pct=42.5,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            max_drawdown_pct=5.0,
            max_drawdown_duration_days=3.0,
            total_trades=50,
            winning_trades=30,
            losing_trades=20,
            win_rate_pct=60.0,
            profit_factor=1.8,
            expectancy=50.0,
            avg_win_pct=1.0,
            avg_loss_pct=0.8,
            largest_win=500.0,
            largest_loss=200.0,
            avg_trade_duration_hours=4.0,
            max_trade_duration_hours=12.0,
        )
        d = metrics.to_dict()
        assert d["total_return_pct"] == 10.0
        assert d["sharpe_ratio"] == 1.5
        assert d["total_trades"] == 50
        assert isinstance(d, dict)

    def test_frozen(self) -> None:
        """Metrics should be immutable."""
        metrics = BacktestMetrics(
            total_return_pct=10.0,
            annualized_return_pct=42.5,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            max_drawdown_pct=5.0,
            max_drawdown_duration_days=3.0,
            total_trades=50,
            winning_trades=30,
            losing_trades=20,
            win_rate_pct=60.0,
            profit_factor=1.8,
            expectancy=50.0,
            avg_win_pct=1.0,
            avg_loss_pct=0.8,
            largest_win=500.0,
            largest_loss=200.0,
            avg_trade_duration_hours=4.0,
            max_trade_duration_hours=12.0,
        )
        with pytest.raises(AttributeError):
            metrics.sharpe_ratio = 99.0  # type: ignore[misc]
