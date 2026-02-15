"""Backtest result validation against performance thresholds.

Validates that a backtest meets minimum quality criteria before
a strategy can progress to paper trading (SIMULATED_PAPER status).

Decision: DEC-2026-02-14-001 - Strategy status transitions follow strict state machine
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

from dataclasses import dataclass

from src.core.strategy.backtest.result import BacktestResult
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ValidationThresholds:
    """Thresholds for backtest result validation.

    A strategy must meet ALL thresholds to pass validation.
    Default values from PHASE_5_IMPLEMENTATION_GUIDE.md.

    Attributes:
        min_sharpe_ratio: Minimum Sharpe ratio (annualized).
        max_drawdown_pct: Maximum allowed drawdown percentage.
        min_win_rate_pct: Minimum win rate percentage.
        min_profit_factor: Minimum profit factor (gross_profit / gross_loss).
        min_num_trades: Minimum number of completed trades.
    """

    min_sharpe_ratio: float = 0.5
    max_drawdown_pct: float = 15.0
    min_win_rate_pct: float = 35.0
    min_profit_factor: float = 1.0
    min_num_trades: int = 30


class BacktestValidator:
    """Validates backtest results against performance thresholds.

    Uses configurable thresholds to determine if a strategy's
    backtest performance qualifies it for paper trading.
    """

    @staticmethod
    def validate(
        result: BacktestResult,
        thresholds: ValidationThresholds | None = None,
    ) -> tuple[bool, list[str]]:
        """Validate backtest result against thresholds.

        Args:
            result: The backtest result to validate.
            thresholds: Validation thresholds. Uses defaults if None.

        Returns:
            Tuple of (passed: bool, errors: list[str]).
            If passed is True, errors will be empty.
        """
        if thresholds is None:
            thresholds = ValidationThresholds()

        errors: list[str] = []
        m = result.metrics

        if m.total_trades < thresholds.min_num_trades:
            errors.append(
                f"Insufficient trades: {m.total_trades} < "
                f"{thresholds.min_num_trades} required"
            )

        if m.sharpe_ratio < thresholds.min_sharpe_ratio:
            errors.append(
                f"Sharpe ratio too low: {m.sharpe_ratio:.4f} < "
                f"{thresholds.min_sharpe_ratio}"
            )

        if m.max_drawdown_pct > thresholds.max_drawdown_pct:
            errors.append(
                f"Max drawdown too high: {m.max_drawdown_pct:.2f}% > "
                f"{thresholds.max_drawdown_pct}%"
            )

        if m.win_rate_pct < thresholds.min_win_rate_pct:
            errors.append(
                f"Win rate too low: {m.win_rate_pct:.2f}% < "
                f"{thresholds.min_win_rate_pct}%"
            )

        if m.profit_factor < thresholds.min_profit_factor:
            errors.append(
                f"Profit factor too low: {m.profit_factor:.4f} < "
                f"{thresholds.min_profit_factor}"
            )

        passed = len(errors) == 0

        logger.info(
            "backtest_validation_complete",
            strategy_id=result.strategy_id,
            passed=passed,
            num_errors=len(errors),
            sharpe=m.sharpe_ratio,
            max_dd=m.max_drawdown_pct,
            win_rate=m.win_rate_pct,
            profit_factor=m.profit_factor,
            total_trades=m.total_trades,
        )

        return passed, errors
