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
from dataclasses import dataclass, field
from typing import Any

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
        annualized_return_pct: Annualized return percentage (CAGR).
        sharpe_ratio: Risk-adjusted return (annualized). Gate: >= 1.0 per PRD §3.6.
        sortino_ratio: Downside risk-adjusted return (annualized).
        calmar_ratio: Annualized return / max drawdown. Measures return per
            unit of drawdown risk. Gate: typically >= 0.5 per PRD §3.6.
        max_drawdown_pct: Maximum peak-to-trough drawdown percentage.
        max_drawdown_duration_days: Duration of longest drawdown in days.
        total_trades: Total number of completed trades. Gate: >= 100 per PRD §3.6.
        winning_trades: Number of profitable trades.
        losing_trades: Number of unprofitable trades.
        win_rate_pct: Percentage of winning trades. Gate: >= 50% per PRD §3.6.
        profit_factor: Ratio of gross profit to gross loss. Gate: >= 1.3 per PRD §3.6.
        avg_win_pct: Average winning trade return percentage.
        avg_loss_pct: Average losing trade return percentage.
        expectancy: Expected value per trade in USDT. Gate: > 0 per PRD §3.6.
        largest_win: Largest single winning trade P&L in USDT.
        largest_loss: Largest single losing trade P&L in USDT (negative).
        avg_trade_duration_hours: Average trade duration in hours.
        max_trade_duration_hours: Maximum trade duration in hours.
        monthly_returns: Ordered tuple of monthly return percentages.
            Each element is a percentage return for one calendar month,
            chronological order. Empty if fewer than 30 days of data.
        per_symbol_breakdown: Per-symbol performance breakdown as a tuple of
            dicts, each with keys: symbol, total_trades, win_rate_pct,
            total_return_pct, max_drawdown_pct. Required by PRD §3.2.
    """

    total_return_pct: float
    annualized_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
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
    monthly_returns: tuple[float, ...] = field(default=())
    per_symbol_breakdown: tuple[dict[str, Any], ...] = field(default=())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON storage.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return {
            "total_return_pct": round(self.total_return_pct, 4),
            "annualized_return_pct": round(self.annualized_return_pct, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "sortino_ratio": round(self.sortino_ratio, 4),
            "calmar_ratio": round(self.calmar_ratio, 4),
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
            "monthly_returns": [round(r, 4) for r in self.monthly_returns],
            "per_symbol_breakdown": list(self.per_symbol_breakdown),
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

        # Trade extremes — computed over the matching trade set (PARA-09).
        # Taking min()/max() over ALL trades mislabels the extremes: a loss-free
        # run would report its smallest win as "largest loss", and a win-free
        # run its least-bad loss as "largest win". Reuse the winning/losing
        # classification above; default 0.0 when the set is empty.
        largest_win = max((t.realized_pnl for t in winning_trades), default=0.0)
        largest_loss = min((t.realized_pnl for t in losing_trades), default=0.0)

        # Duration metrics
        durations = [t.duration_hours for t in trades]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        max_duration = max(durations) if durations else 0.0

        # Extended metrics (PRD §3.2)
        calmar = BacktestMetricsCalculator._compute_calmar_ratio(
            annualized_return_pct, max_dd_pct
        )
        monthly_returns = BacktestMetricsCalculator._compute_monthly_returns(equity_points)
        per_symbol = BacktestMetricsCalculator._compute_per_symbol_breakdown(trades)

        return BacktestMetrics(
            total_return_pct=total_return_pct,
            annualized_return_pct=annualized_return_pct,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
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
            monthly_returns=monthly_returns,
            per_symbol_breakdown=per_symbol,
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
            calmar_ratio=0.0,
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

    @staticmethod
    def _compute_calmar_ratio(
        annualized_return_pct: float,
        max_drawdown_pct: float,
    ) -> float:
        """Compute Calmar ratio: annualized return divided by max drawdown.

        A higher Calmar ratio means better risk-adjusted performance —
        more return per unit of drawdown risk. Typical good values > 0.5.

        Args:
            annualized_return_pct: CAGR in percentage points (e.g., 25.0 = 25%).
            max_drawdown_pct: Max drawdown as positive percentage (e.g., 10.0 = 10%).

        Returns:
            Calmar ratio, 0.0 if drawdown is zero and return is non-positive,
            or float('inf') if drawdown is zero but return is positive.
        """
        if max_drawdown_pct <= 0:
            # No drawdown: inf if profitable, 0.0 otherwise
            return float("inf") if annualized_return_pct > 0 else 0.0
        return annualized_return_pct / max_drawdown_pct

    @staticmethod
    def _compute_monthly_returns(
        equity_points: list[EquityPoint],
    ) -> tuple[float, ...]:
        """Compute month-over-month return percentages from equity curve.

        Groups equity snapshots by calendar month and computes the percentage
        change from the prior month-end to the current month-end.

        Args:
            equity_points: Ordered equity snapshots (must be chronological).

        Returns:
            Tuple of monthly return percentages in chronological order.
            Empty tuple if fewer than 2 calendar months of data.
        """
        if len(equity_points) < 2:
            return ()

        # Group by YYYY-MM, retaining first and last equity per month
        month_first: dict[str, float] = {}
        month_last: dict[str, float] = {}
        for point in equity_points:
            key = point.timestamp.strftime("%Y-%m")
            if key not in month_first:
                month_first[key] = point.equity
            month_last[key] = point.equity

        sorted_months = sorted(month_first.keys())
        if len(sorted_months) < 2:
            return ()

        returns: list[float] = []
        for i, month in enumerate(sorted_months):
            if i == 0:
                # First month: return within the month itself
                start_val = month_first[month]
            else:
                # Subsequent months: from prior month-end
                start_val = month_last[sorted_months[i - 1]]

            end_val = month_last[month]
            if start_val > 0:
                monthly_ret = ((end_val - start_val) / start_val) * 100.0
                returns.append(monthly_ret)

        return tuple(returns)

    @staticmethod
    def _compute_per_symbol_breakdown(
        trades: list[TradeRecord],
    ) -> tuple[dict[str, Any], ...]:
        """Compute per-symbol performance breakdown.

        Groups trades by symbol and computes key metrics for each.
        Required by PRD §3.2.

        Args:
            trades: All completed trade records.

        Returns:
            Tuple of dicts sorted by symbol name. Each dict contains:
            symbol, total_trades, win_rate_pct, total_return_pct,
            profit_factor.
        """
        if not trades:
            return ()

        # Group trades by symbol
        symbol_trades: dict[str, list[TradeRecord]] = {}
        for trade in trades:
            if trade.symbol not in symbol_trades:
                symbol_trades[trade.symbol] = []
            symbol_trades[trade.symbol].append(trade)

        breakdown: list[dict[str, Any]] = []
        for symbol in sorted(symbol_trades):
            sym_trades = symbol_trades[symbol]
            n = len(sym_trades)
            wins = [t for t in sym_trades if t.realized_pnl > 0]
            losses = [t for t in sym_trades if t.realized_pnl <= 0]

            gross_profit = sum(t.realized_pnl for t in wins)
            gross_loss = abs(sum(t.realized_pnl for t in losses))

            if gross_loss > 0:
                pf = gross_profit / gross_loss
            else:
                pf = float("inf") if gross_profit > 0 else 0.0

            win_rate = (len(wins) / n) * 100.0
            # Compound per-trade returns rather than summing percentages
            # (PARA-08). return_pct is a percent (e.g. 2.5 == +2.5%); a plain
            # sum is not a real return and isn't comparable to the portfolio-
            # level compounded total_return_pct. Compounding assumes each trade
            # reinvests the prior result into the next trade's notional.
            compounded = 1.0
            for t in sym_trades:
                compounded *= 1.0 + t.return_pct / 100.0
            total_return = (compounded - 1.0) * 100.0

            breakdown.append({
                "symbol": symbol,
                "total_trades": n,
                "win_rate_pct": round(win_rate, 2),
                "total_return_pct": round(total_return, 4),
                "profit_factor": round(pf, 4) if math.isfinite(pf) else pf,
            })

        return tuple(breakdown)
