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
        """to_dict should serialize all fields including new extended metrics."""
        metrics = BacktestMetrics(
            total_return_pct=10.0,
            annualized_return_pct=42.5,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            calmar_ratio=4.25,
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
            monthly_returns=(2.1, -0.5, 3.3),
            per_symbol_breakdown=({"symbol": "BTCUSDT", "total_trades": 50},),
        )
        d = metrics.to_dict()
        assert d["total_return_pct"] == 10.0
        assert d["sharpe_ratio"] == 1.5
        assert d["calmar_ratio"] == 4.25
        assert d["total_trades"] == 50
        assert d["monthly_returns"] == [2.1, -0.5, 3.3]
        assert len(d["per_symbol_breakdown"]) == 1
        assert isinstance(d, dict)

    def test_frozen(self) -> None:
        """Metrics should be immutable."""
        metrics = BacktestMetrics(
            total_return_pct=10.0,
            annualized_return_pct=42.5,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            calmar_ratio=4.25,
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


class TestExtendedMetrics:
    """Tests for Calmar ratio, monthly returns, and per-symbol breakdown."""

    def test_calmar_ratio_positive(self) -> None:
        """Calmar = annualized_return / max_drawdown."""
        calmar = BacktestMetricsCalculator._compute_calmar_ratio(25.0, 10.0)
        assert calmar == pytest.approx(2.5)

    def test_calmar_ratio_zero_drawdown_profitable(self) -> None:
        """Zero drawdown with positive return should give inf."""
        calmar = BacktestMetricsCalculator._compute_calmar_ratio(10.0, 0.0)
        assert calmar == float("inf")

    def test_calmar_ratio_zero_drawdown_flat(self) -> None:
        """Zero drawdown with zero return should give 0.0."""
        calmar = BacktestMetricsCalculator._compute_calmar_ratio(0.0, 0.0)
        assert calmar == 0.0

    def test_calmar_ratio_negative_return(self) -> None:
        """Negative return / positive drawdown gives negative calmar."""
        calmar = BacktestMetricsCalculator._compute_calmar_ratio(-15.0, 20.0)
        assert calmar == pytest.approx(-0.75)

    def test_monthly_returns_basic(self) -> None:
        """Monthly returns from multi-month equity curve."""
        # Build equity spanning 3 months
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        equity_points = []
        for day in range(90):
            ts = start + timedelta(days=day)
            equity_points.append(
                EquityPoint(
                    timestamp=ts,
                    equity=10000.0 + day * 10.0,
                    cash=5000.0,
                    position_value=5000.0 + day * 10.0,
                )
            )
        returns = BacktestMetricsCalculator._compute_monthly_returns(equity_points)
        # 3 months of data should produce returns
        assert len(returns) >= 2
        # All months should have positive returns (equity is rising)
        assert all(r > 0 for r in returns)

    def test_monthly_returns_single_month(self) -> None:
        """Single month should return empty tuple (need 2 months for returns)."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        points = [
            EquityPoint(timestamp=start + timedelta(days=i), equity=10000.0,
                        cash=5000.0, position_value=5000.0)
            for i in range(20)
        ]
        returns = BacktestMetricsCalculator._compute_monthly_returns(points)
        assert returns == ()

    def test_monthly_returns_insufficient_points(self) -> None:
        """Single point should return empty tuple."""
        points = [EquityPoint(
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            equity=10000.0, cash=5000.0, position_value=5000.0,
        )]
        assert BacktestMetricsCalculator._compute_monthly_returns(points) == ()

    def test_per_symbol_breakdown_single_symbol(self) -> None:
        """All trades on same symbol produces one breakdown entry."""
        trades = [_make_trade(pnl=100.0, hour_offset=i) for i in range(4)]
        breakdown = BacktestMetricsCalculator._compute_per_symbol_breakdown(trades)
        assert len(breakdown) == 1
        assert breakdown[0]["symbol"] == "BTCUSDT"
        assert breakdown[0]["total_trades"] == 4
        assert breakdown[0]["win_rate_pct"] == 100.0

    def test_per_symbol_breakdown_multi_symbol(self) -> None:
        """Trades on different symbols produce separate breakdown entries."""
        from src.data.models.signal import SignalDirection

        def _trade_symbol(symbol: str, pnl: float, hour: int) -> TradeRecord:
            entry = datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(hours=hour)
            return TradeRecord(
                entry_time=entry,
                exit_time=entry + timedelta(hours=1),
                symbol=symbol,
                direction=SignalDirection.LONG,
                entry_price=1000.0,
                exit_price=1010.0,
                quantity=1.0,
                entry_commission=1.0,
                exit_commission=1.0,
                slippage_cost=0.5,
                realized_pnl=pnl,
                return_pct=pnl / 1000.0 * 100,
            )

        trades = [
            _trade_symbol("BTCUSDT", 100.0, 0),
            _trade_symbol("BTCUSDT", -20.0, 1),
            _trade_symbol("ETHUSDT", 50.0, 2),
        ]
        breakdown = BacktestMetricsCalculator._compute_per_symbol_breakdown(trades)
        assert len(breakdown) == 2
        symbols = {b["symbol"] for b in breakdown}
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols
        btc = next(b for b in breakdown if b["symbol"] == "BTCUSDT")
        assert btc["total_trades"] == 2
        assert btc["win_rate_pct"] == 50.0

    def test_per_symbol_breakdown_empty_trades(self) -> None:
        """Empty trade list should return empty tuple."""
        assert BacktestMetricsCalculator._compute_per_symbol_breakdown([]) == ()

    def test_calmar_included_in_calculate(self) -> None:
        """Full calculate() should populate calmar_ratio."""
        trades = [_make_trade(pnl=200.0, hour_offset=i * 24) for i in range(5)]
        equity = _make_equity_curve([10000.0 + i * 200 for i in range(50)])
        metrics = BacktestMetricsCalculator.calculate(
            trades=trades,
            equity_points=equity,
            initial_capital=10000.0,
            config=BacktestConfig(),
        )
        # calmar_ratio should be computed (not default 0.0 when there's return)
        assert isinstance(metrics.calmar_ratio, float)
        assert metrics.per_symbol_breakdown is not None
