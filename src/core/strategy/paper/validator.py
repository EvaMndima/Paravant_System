"""Paper trading validation.

Validates paper trading results to determine if a strategy
qualifies for live deployment. Used for auto-transitioning
strategies from SIMULATED_PAPER to LIVE_PAPER, or from
LIVE_PAPER to PENDING_APPROVAL.

Decision: DEC-2026-02-14-001 - Strategy status transitions
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

from dataclasses import dataclass

from src.core.strategy.backtest.metrics import BacktestMetricsCalculator
from src.core.strategy.paper.engine import PaperTradingEngine
from src.core.strategy.paper.types import PaperTradingMode
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class PaperTradingThresholds:
    """Validation thresholds for paper trading results.

    More lenient than backtest thresholds since paper trading
    operates on less data and in real-time conditions.

    Attributes:
        min_sharpe_ratio: Minimum annualized Sharpe ratio.
        max_drawdown_pct: Maximum allowed drawdown percentage.
        min_win_rate_pct: Minimum win rate percentage.
        min_num_trades: Minimum completed trades for validation.
        min_days_simulated: Minimum simulated days (for SIMULATED mode).
        min_days_live: Minimum live days (for LIVE mode).
    """

    min_sharpe_ratio: float = 0.3
    max_drawdown_pct: float = 20.0
    min_win_rate_pct: float = 30.0
    min_num_trades: int = 10
    min_days_simulated: float = 14.0
    min_days_live: float = 7.0


class PaperTradingValidator:
    """Validates paper trading results against thresholds.

    Determines if a strategy should advance in the lifecycle:
    - SIMULATED_PAPER -> LIVE_PAPER (simulated validation)
    - LIVE_PAPER -> PENDING_APPROVAL (live validation)
    """

    @staticmethod
    def validate(
        engine: PaperTradingEngine,
        thresholds: PaperTradingThresholds | None = None,
    ) -> tuple[bool, list[str]]:
        """Validate paper trading results against thresholds.

        Args:
            engine: Paper trading engine with completed or ongoing session.
            thresholds: Validation thresholds. Uses defaults if None.

        Returns:
            Tuple of (passed: bool, errors: list[str]).
        """
        if thresholds is None:
            thresholds = PaperTradingThresholds()

        errors: list[str] = []
        status = engine.get_status()

        # Check minimum duration
        if engine.mode == PaperTradingMode.SIMULATED:
            if status.days_elapsed < thresholds.min_days_simulated:
                errors.append(
                    f"Insufficient simulated duration: {status.days_elapsed:.1f} days < "
                    f"{thresholds.min_days_simulated} days required"
                )
        else:
            if status.days_elapsed < thresholds.min_days_live:
                errors.append(
                    f"Insufficient live duration: {status.days_elapsed:.1f} days < "
                    f"{thresholds.min_days_live} days required"
                )

        # Check minimum trades
        if status.num_trades < thresholds.min_num_trades:
            errors.append(
                f"Insufficient trades: {status.num_trades} < "
                f"{thresholds.min_num_trades} required"
            )

        # Calculate metrics from engine data
        trades = engine.portfolio.trade_log
        equity_points = engine.portfolio.equity_curve

        if trades and equity_points:
            metrics = BacktestMetricsCalculator.calculate(
                trades=trades,
                equity_points=equity_points,
                initial_capital=engine.config.initial_capital,
                config=engine.config,
            )

            if metrics.sharpe_ratio < thresholds.min_sharpe_ratio:
                errors.append(
                    f"Sharpe ratio too low: {metrics.sharpe_ratio:.4f} < "
                    f"{thresholds.min_sharpe_ratio}"
                )

            if metrics.max_drawdown_pct > thresholds.max_drawdown_pct:
                errors.append(
                    f"Max drawdown too high: {metrics.max_drawdown_pct:.2f}% > "
                    f"{thresholds.max_drawdown_pct}%"
                )

            if metrics.win_rate_pct < thresholds.min_win_rate_pct:
                errors.append(
                    f"Win rate too low: {metrics.win_rate_pct:.2f}% < "
                    f"{thresholds.min_win_rate_pct}%"
                )

        passed = len(errors) == 0

        logger.info(
            "paper_trading_validation",
            strategy_id=status.strategy_id,
            mode=status.mode.value,
            passed=passed,
            num_errors=len(errors),
            num_trades=status.num_trades,
            days_elapsed=status.days_elapsed,
        )

        return passed, errors
