"""Backtest performance metrics calculator.

Computes comprehensive financial metrics from trade records and equity curve
data. All formulas follow PHASE_5_IMPLEMENTATION_GUIDE.md specifications.

Formulas:
    Sharpe Ratio = (mean(daily_returns) - Rf_daily) / std(daily_returns) * sqrt(252)
    Sortino Ratio = (mean(daily_returns) - Rf_daily) / downside_std * sqrt(252)
    Max Drawdown = max((peak - trough) / peak)
    Profit Factor = sum(winning_pnl) / abs(sum(losing_pnl))
    Win Rate = winning_trades / total_trades * 100
    Expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)

Decision: DEC-2026-02-08-007 - Input validation at boundaries
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from src.core.strategy.backtest.types import BacktestConfig, EquityPoint, TradeRecord
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Annualization factor: trading days per year for crypto (24/7 market)
TRADING_DAYS_PER_YEAR = 365


@dataclass(frozen=True)
class BacktestMetrics:
    """Comprehensive backtest performance metrics.

    All metrics are computed from trade records and equity curve by
    BacktestMetricsCalculator. This is an immutable value object.

    Attributes:
        total_return_pct: Total return as percentage.
        annualized_return_pct: Annualized return percentage.
        sharpe_ratio: Risk-adjusted return (annualized).
        sortino_ratio: Downside risk-adjusted return (annualized).
        max_drawdown_pct: Maximum peak-to-trough drawdown percentage.
        max_drawdown_duration_days: Duration of longest drawdown in days.
        total_trades: Total number of completed trades.
        winning_trades: Number of profitable trades.
        losing_trades: Number of unprofitable trades.
        win_rate_pct: Percentage of winning trades.
        profit_factor: Ratio of gross profit to gross loss.
        avg_win_pct: Average winning trade return percentage.
        avg_loss_pct: Average losing trade return percentage.
        expectancy: Expected value per trade in USDT.
        largest_win: Largest single winning trade P&L in USDT.
        largest_loss: Largest single losing trade P&L in USDT (negative).
        avg_trade_duration_hours: Average trade duration in hours.
        max_trade_duration_hours: Maximum trade duration in hours.
    """

    total_return_pct: float
    annualized_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    max_drawdown_duration_days: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    avg_win_pct: float
    avg_loss_pct: float
    expectancy: float
    largest_win: float
    largest_loss: float
    avg_trade_duration_hours: float
    max_trade_duration_hours: float

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return {
            "total_return_pct": round(self.total_return_pct, 4),
            "annualized_return_pct": round(self.annualized_return_pct, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "sortino_ratio": round(self.sortino_ratio, 4),
            "max_drawdown_pct": round(self.max_drawdown_pct, 4),
            "max_drawdown_duration_days": round(self.max_drawdown_duration_days, 2),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate_pct": round(self.win_rate_pct, 2),
            "profit_factor": round(self.profit_factor, 4),
            "avg_win_pct": round(self.avg_win_pct, 4),
            "avg_loss_pct": round(self.avg_loss_pct, 4),
            "expectancy": round(self.expectancy, 4),
            "largest_win": round(self.largest_win, 4),
            "largest_loss": round(self.largest_loss, 4),
            "avg_trade_duration_hours": round(self.avg_trade_duration_hours, 2),
            "max_trade_duration_hours": round(self.max_trade_duration_hours, 2),
        }


class BacktestMetricsCalculator:
    """Calculates comprehensive backtest metrics from raw data.

    All methods are static — this class serves as a namespace.
    """

    @staticmethod
    def calculate(
        trades: list[TradeRecord],
        equity_points: list[EquityPoint],
        initial_capital: float,
        config: BacktestConfig,
    ) -> BacktestMetrics:
        """Compute all metrics from trade records and equity curve.

        Handles edge cases: zero trades, zero variance, zero losses.

        Args:
            trades: List of completed trade records.
            equity_points: List of equity curve snapshots.
            initial_capital: Starting portfolio value.
            config: Backtest configuration (for risk-free rate).

        Returns:
            BacktestMetrics with all computed performance metrics.
        """
        if not trades:
            return BacktestMetricsCalculator._empty_metrics()

        # Trade classification
        winning_trades = [t for t in trades if t.realized_pnl > 0]
        losing_trades = [t for t in trades if t.realized_pnl <= 0]

        total = len(trades)
        n_wins = len(winning_trades)
        n_losses = len(losing_trades)

        # Basic returns
        if equity_points:
            final_equity = equity_points[-1].equity
        else:
            final_equity = initial_capital + sum(t.realized_pnl for t in trades)

        total_return_pct = ((final_equity - initial_capital) / initial_capital) * 100.0

        # Time span for annualization
        time_span = None
        if equity_points and len(equity_points) >= 2:
            time_span = equity_points[-1].timestamp - equity_points[0].timestamp
            years = time_span.total_seconds() / (365.25 * 24 * 3600)
        else:
            years = 0.0

        if years > 0:
            try:
                # CAGR calculation
                ratio = final_equity / initial_capital
                if ratio <= 0:
                    # Bankruptcy or loss of all capital
                    annualized_return_pct = -100.0
                else:
                    annualized_return_pct = (ratio ** (1.0 / years) - 1.0) * 100.0
            except (OverflowError, ValueError):
                # Fallback to simple annualization if CAGR overflows (e.g. short duration high return)
                annualized_return_pct = total_return_pct * (1.0 / years) if years > 0 else total_return_pct
        else:
            annualized_return_pct = total_return_pct

        # Daily returns from equity curve
        daily_returns = BacktestMetricsCalculator._compute_daily_returns(equity_points)

        # Risk metrics
        sharpe = BacktestMetricsCalculator._compute_sharpe(
            daily_returns, config.risk_free_rate
        )
        sortino = BacktestMetricsCalculator._compute_sortino(
            daily_returns, config.risk_free_rate
        )

        max_dd_pct, max_dd_duration = BacktestMetricsCalculator._compute_max_drawdown(
            equity_points
        )

        # Trade metrics
        win_rate = (n_wins / total) * 100.0

        gross_profit = sum(t.realized_pnl for t in winning_trades)
        gross_loss = abs(sum(t.realized_pnl for t in losing_trades))

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        else:
            # All trades profitable or no losing trades
            profit_factor = float("inf") if gross_profit > 0 else 0.0

        avg_win_pct = (
            sum(t.return_pct for t in winning_trades) / n_wins
            if n_wins > 0 else 0.0
        )
        avg_loss_pct = (
            sum(t.return_pct for t in losing_trades) / n_losses
            if n_losses > 0 else 0.0
        )

        # Expectancy in USDT
        avg_win = gross_profit / n_wins if n_wins > 0 else 0.0
        avg_loss = gross_loss / n_losses if n_losses > 0 else 0.0
        win_rate_frac = n_wins / total
        loss_rate_frac = n_losses / total
        expectancy = (win_rate_frac * avg_win) - (loss_rate_frac * avg_loss)

        # Trade extremes
        all_pnl = [t.realized_pnl for t in trades]
        largest_win = max(all_pnl) if all_pnl else 0.0
        largest_loss = min(all_pnl) if all_pnl else 0.0

        # Duration metrics
        durations = [t.duration_hours for t in trades]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        max_duration = max(durations) if durations else 0.0

        return BacktestMetrics(
            total_return_pct=total_return_pct,
            annualized_return_pct=annualized_return_pct,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown_pct=max_dd_pct,
            max_drawdown_duration_days=max_dd_duration,
            total_trades=total,
            winning_trades=n_wins,
            losing_trades=n_losses,
            win_rate_pct=win_rate,
            profit_factor=profit_factor,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            expectancy=expectancy,
            largest_win=largest_win,
            largest_loss=largest_loss,
            avg_trade_duration_hours=avg_duration,
            max_trade_duration_hours=max_duration,
        )

    @staticmethod
    def _empty_metrics() -> BacktestMetrics:
        """Return zeroed metrics for backtests with no trades.

        Returns:
            BacktestMetrics with all values zeroed.
        """
        return BacktestMetrics(
            total_return_pct=0.0,
            annualized_return_pct=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown_pct=0.0,
            max_drawdown_duration_days=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate_pct=0.0,
            profit_factor=0.0,
            avg_win_pct=0.0,
            avg_loss_pct=0.0,
            expectancy=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            avg_trade_duration_hours=0.0,
            max_trade_duration_hours=0.0,
        )

    @staticmethod
    def _compute_daily_returns(
        equity_points: list[EquityPoint],
    ) -> list[float]:
        """Compute daily returns from equity curve.

        Groups equity points by day and computes day-over-day returns.

        Args:
            equity_points: Ordered equity snapshots.

        Returns:
            List of daily return fractions.
        """
        if len(equity_points) < 2:
            return []

        # Group by date, take last equity value per day
        daily_equity: dict[str, float] = {}
        for point in equity_points:
            date_key = point.timestamp.strftime("%Y-%m-%d")
            daily_equity[date_key] = point.equity

        values = list(daily_equity.values())
        if len(values) < 2:
            return []

        returns = []
        for i in range(1, len(values)):
            if values[i - 1] != 0:
                ret = (values[i] - values[i - 1]) / values[i - 1]
                returns.append(ret)

        return returns

    @staticmethod
    def _compute_sharpe(
        daily_returns: list[float],
        annual_risk_free_rate: float,
    ) -> float:
        """Compute annualized Sharpe ratio.

        Formula: (mean(returns) - Rf_daily) / std(returns) * sqrt(365)

        Args:
            daily_returns: List of daily return fractions.
            annual_risk_free_rate: Annual risk-free rate (e.g., 0.02).

        Returns:
            Annualized Sharpe ratio, or 0.0 if insufficient data.
        """
        if len(daily_returns) < 2:
            return 0.0

        rf_daily = annual_risk_free_rate / TRADING_DAYS_PER_YEAR
        mean_return = sum(daily_returns) / len(daily_returns)
        excess_return = mean_return - rf_daily

        # Standard deviation
        variance = sum(
            (r - mean_return) ** 2 for r in daily_returns
        ) / (len(daily_returns) - 1)
        std_dev = math.sqrt(variance) if variance > 0 else 0.0

        if std_dev == 0:
            return 0.0

        return (excess_return / std_dev) * math.sqrt(TRADING_DAYS_PER_YEAR)

    @staticmethod
    def _compute_sortino(
        daily_returns: list[float],
        annual_risk_free_rate: float,
    ) -> float:
        """Compute annualized Sortino ratio.

        Like Sharpe but uses only downside deviation (negative returns).

        Formula: (mean(returns) - Rf_daily) / downside_std * sqrt(365)

        Args:
            daily_returns: List of daily return fractions.
            annual_risk_free_rate: Annual risk-free rate.

        Returns:
            Annualized Sortino ratio, or 0.0 if insufficient data.
        """
        if len(daily_returns) < 2:
            return 0.0

        rf_daily = annual_risk_free_rate / TRADING_DAYS_PER_YEAR
        mean_return = sum(daily_returns) / len(daily_returns)
        excess_return = mean_return - rf_daily

        # Downside deviation: only count negative returns
        downside_returns = [min(r - rf_daily, 0) for r in daily_returns]
        downside_variance = sum(
            r ** 2 for r in downside_returns
        ) / (len(downside_returns) - 1)
        downside_std = math.sqrt(downside_variance) if downside_variance > 0 else 0.0

        if downside_std == 0:
            return 0.0

        return (excess_return / downside_std) * math.sqrt(TRADING_DAYS_PER_YEAR)

    @staticmethod
    def _compute_max_drawdown(
        equity_points: list[EquityPoint],
    ) -> tuple[float, float]:
        """Compute maximum drawdown percentage and duration.

        Drawdown = (peak - trough) / peak.
        Duration is measured in calendar days.

        Args:
            equity_points: Ordered equity snapshots.

        Returns:
            Tuple of (max_drawdown_pct, max_drawdown_duration_days).
        """
        if not equity_points:
            return 0.0, 0.0

        peak = equity_points[0].equity

        max_dd = 0.0
        max_dd_duration = 0.0
        current_dd_start = equity_points[0].timestamp

        for point in equity_points:
            if point.equity >= peak:
                # New peak — record duration of previous drawdown
                if max_dd > 0:
                    duration = (point.timestamp - current_dd_start).total_seconds() / 86400.0
                    max_dd_duration = max(max_dd_duration, duration)
                peak = point.equity

                current_dd_start = point.timestamp
            else:
                # In drawdown
                dd = ((peak - point.equity) / peak) * 100.0 if peak > 0 else 0.0
                if dd > max_dd:
                    max_dd = dd

        # Check if still in drawdown at end
        if equity_points[-1].equity < peak:
            duration = (equity_points[-1].timestamp - current_dd_start).total_seconds() / 86400.0
            max_dd_duration = max(max_dd_duration, duration)

        return max_dd, max_dd_duration
