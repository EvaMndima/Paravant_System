"""Backtest result aggregation.

Combines all backtest outputs into a single immutable result object
that can be serialized and stored in Strategy.backtest_results.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-12-001 - Frozen immutable outputs
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.core.strategy.backtest.metrics import BacktestMetrics
from src.core.strategy.backtest.types import BacktestConfig, EquityPoint, TradeRecord


@dataclass(frozen=True)
class BacktestResult:
    """Complete result of a backtest run.

    Aggregates metrics, equity curve, trade log, and validation status
    into a single immutable object. Serializable to dict for storage
    in the Strategy.backtest_results JSON column.

    Attributes:
        strategy_id: ID of the strategy that was backtested.
        strategy_name: Name of the strategy.
        template_id: Strategy template identifier.
        symbol: Trading pair symbol.
        timeframe: Candlestick timeframe used.
        start_date: Backtest start date (first bar).
        end_date: Backtest end date (last bar).
        initial_capital: Starting portfolio value.
        final_capital: Ending portfolio value.
        metrics: Computed performance metrics.
        equity_curve: List of equity snapshots.
        trade_log: List of completed trade records.
        config: Backtest configuration used.
        passed_validation: Whether result met validation thresholds.
        validation_errors: List of validation failure reasons.
    """

    strategy_id: str
    strategy_name: str
    template_id: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    metrics: BacktestMetrics
    equity_curve: list[EquityPoint] = field(default_factory=list)
    trade_log: list[TradeRecord] = field(default_factory=list)
    config: BacktestConfig = field(default_factory=BacktestConfig)
    passed_validation: bool = False
    validation_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON storage.

        Used to persist results in Strategy.backtest_results.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "template_id": self.template_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "initial_capital": self.initial_capital,
            "final_capital": round(self.final_capital, 4),
            "metrics": self.metrics.to_dict(),
            "equity_curve": [p.to_dict() for p in self.equity_curve],
            "trade_log": [t.to_dict() for t in self.trade_log],
            "config": {
                "initial_capital": self.config.initial_capital,
                "commission_rate": self.config.commission_rate,
                "slippage_rate": self.config.slippage_rate,
                "risk_free_rate": self.config.risk_free_rate,
                "position_size_pct": self.config.position_size_pct,
            },
            "passed_validation": self.passed_validation,
            "validation_errors": self.validation_errors,
        }

    def summary(self) -> str:
        """Generate human-readable summary of backtest results.

        Returns:
            Multi-line string summarizing key metrics.
        """
        m = self.metrics
        lines = [
            f"=== Backtest Result: {self.strategy_name} ===",
            f"Symbol: {self.symbol} | Timeframe: {self.timeframe}",
            f"Period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}",
            f"Capital: ${self.initial_capital:,.2f} -> ${self.final_capital:,.2f}",
            "",
            "--- Returns ---",
            f"Total Return: {m.total_return_pct:+.2f}%",
            f"Annualized Return: {m.annualized_return_pct:+.2f}%",
            "",
            "--- Risk ---",
            f"Sharpe Ratio: {m.sharpe_ratio:.4f}",
            f"Sortino Ratio: {m.sortino_ratio:.4f}",
            f"Max Drawdown: {m.max_drawdown_pct:.2f}%",
            f"Max DD Duration: {m.max_drawdown_duration_days:.1f} days",
            "",
            "--- Trades ---",
            f"Total: {m.total_trades} | W: {m.winning_trades} | L: {m.losing_trades}",
            f"Win Rate: {m.win_rate_pct:.1f}%",
            f"Profit Factor: {m.profit_factor:.4f}",
            f"Expectancy: ${m.expectancy:+.2f}",
            f"Avg Trade Duration: {m.avg_trade_duration_hours:.1f}h",
            "",
            "--- Validation ---",
            f"Passed: {'YES' if self.passed_validation else 'NO'}",
        ]

        if self.validation_errors:
            lines.append("Errors:")
            for err in self.validation_errors:
                lines.append(f"  - {err}")

        return "\n".join(lines)
