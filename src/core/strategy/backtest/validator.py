"""Backtest result validation against performance thresholds.

Implements two-tier validation aligned with E. Chan's algorithmic trading
criteria:

  Tier 1 — SUPERVISED_THRESHOLDS (default)
      For manually-watched deployment where an operator monitors the system
      daily and can pause or kill strategies.  Looser thresholds allow viable
      trend-following strategies (35-45 % win rate) to progress to paper
      trading.  Win rate and Calmar checks are disabled; positive expectancy
      is the primary quality gate.

  Tier 2 — AUTOMATED_THRESHOLDS
      For fully-automated deployment with no human intervention.  All checks
      are active.  Win rate floor is 35 % (not 50 %) so Donchian / Supertrend
      templates can pass on merit, but profit factor is raised to 1.5 and
      Calmar >= 1.0 is required as a compensating gate.

The default ValidationThresholds() constructor returns Tier-1 (Supervised)
values because PARAVANT is currently in a manually-supervised phase.  Pass
AUTOMATED_THRESHOLDS explicitly when validating for live automated trading.

Decision: DEC-2026-02-22-003 - Two-tier validation thresholds (E. Chan)
Decision: DEC-2026-02-14-001 - Strategy status lifecycle state machine
Decision: DEC-2026-02-08-008 - Structured logging

References:
    E. Chan, "Algorithmic Trading" (2013) — Sharpe, Calmar, expectancy gates
    E. Chan, "Quantitative Trading" (2008) — minimum trade count (45), win rate
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from src.core.strategy.backtest.result import BacktestResult
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ValidationThresholds:
    """Thresholds for backtest result validation.

    A strategy must meet ALL active thresholds to pass validation and progress
    to SIMULATED_PAPER status.

    Threshold activity rules
    ------------------------
    ``min_win_rate_pct``:
        Skipped when set to 0.0 (disabled).  Disable for trend-following
        templates (donchian_atr, bb_squeeze_breakout) which are designed for
        35-45 % win rates.  Use ``min_expectancy`` as the quality gate.

    ``min_calmar_ratio``:
        Skipped when set to 0.0 (disabled).  Disabled in Tier-1 because human
        oversight provides the protection that Calmar enforces automatically.

    ``min_expectancy``:
        Always checked.  Replaces win rate as the primary quality gate — any
        positive expectancy (strategy earns more than it loses on average) is
        the minimum bar.

    See module-level constants ``SUPERVISED_THRESHOLDS`` and
    ``AUTOMATED_THRESHOLDS`` for the two standard presets.

    Attributes:
        min_sharpe_ratio: Minimum annualized Sharpe ratio.  0.5 is Chan's
            floor for "viable but needs watching".  1.0 is the automation
            floor.
        max_drawdown_pct: Maximum allowed peak-to-trough drawdown percentage.
        min_win_rate_pct: Minimum win rate percentage.  Set to 0.0 to disable.
            Disabling is correct for trend-following strategies (donchian_atr,
            bb_squeeze_breakout) that achieve profitability through a high
            win/loss ratio rather than a high win count.
        min_profit_factor: Minimum ratio of gross profit to gross loss.
        min_num_trades: Minimum number of completed trades.  Per E. Chan, 30
            is the statistical floor; 60 is comfortable for automated.
        min_expectancy: Minimum expected profit per trade in USDT.  0.01 means
            "any positive expectancy passes" (supervised).  10.0 means at
            least $10 average profit per trade on a $10 K capital base.
        min_calmar_ratio: Minimum Calmar ratio (annualized return / max DD).
            Set to 0.0 to disable.  1.0 means annual return >= max drawdown.
            float('inf') calmar (zero drawdown, positive return) always passes.
    """

    min_sharpe_ratio: float = 0.5
    max_drawdown_pct: float = 25.0
    min_win_rate_pct: float = 0.0        # disabled — expectancy is the gate
    min_profit_factor: float = 1.35
    min_num_trades: int = 30
    min_expectancy: float = 0.01         # any positive expectancy passes
    min_calmar_ratio: float = 0.0        # disabled in supervised mode


# ---------------------------------------------------------------------------
# Standard presets — Decision: DEC-2026-02-22-003
# ---------------------------------------------------------------------------

SUPERVISED_THRESHOLDS = ValidationThresholds()
"""Tier-1 thresholds for manually-supervised deployment.

Use when an operator watches the system daily and can intervene.
Allows viable trend-following strategies (35-45 % win rate) to progress.
Win rate and Calmar checks are disabled; expectancy is the quality gate.
"""

AUTOMATED_THRESHOLDS = ValidationThresholds(
    min_sharpe_ratio=1.0,
    max_drawdown_pct=15.0,
    min_win_rate_pct=35.0,     # permits trend strategies; blocks broken ones
    min_profit_factor=1.5,     # raised from 1.35 — compensates for relaxed WR
    min_num_trades=60,         # Chan's comfortable minimum for automated
    min_expectancy=10.0,       # at least $10 avg profit/trade on $10 K capital
    min_calmar_ratio=1.0,      # annual return must cover the max drawdown
)
"""Tier-2 thresholds for fully-automated deployment.

Use when the system runs unsupervised.  All checks are active.  Win rate is
lowered to 35 % (permits Donchian / Supertrend templates) but profit factor
is raised to 1.5 and Calmar >= 1.0 is required as a compensating gate.
"""


class BacktestValidator:
    """Validates backtest results against performance thresholds.

    Uses configurable thresholds to determine if a strategy's backtest
    performance qualifies it for paper trading (SIMULATED_PAPER status).

    The default thresholds are Tier-1 Supervised.  Pass
    ``AUTOMATED_THRESHOLDS`` explicitly when validating for live deployment.
    """

    @staticmethod
    def validate(
        result: BacktestResult,
        thresholds: ValidationThresholds | None = None,
    ) -> tuple[bool, list[str]]:
        """Validate backtest result against thresholds.

        Checks up to seven criteria.  ``min_win_rate_pct`` and
        ``min_calmar_ratio`` are skipped when their threshold is 0.0,
        allowing them to be disabled per strategy type.

        Checks applied (in order):
            1. Minimum trade count
            2. Sharpe ratio
            3. Max drawdown
            4. Win rate  (skipped when threshold == 0.0)
            5. Profit factor
            6. Expectancy  (always checked)
            7. Calmar ratio  (skipped when threshold == 0.0)

        Args:
            result: The backtest result to validate.
            thresholds: Validation thresholds.  Defaults to
                ``SUPERVISED_THRESHOLDS`` (Tier-1) if None.

        Returns:
            Tuple of (passed: bool, errors: list[str]).
            If passed is True, errors will be empty.
        """
        if thresholds is None:
            thresholds = SUPERVISED_THRESHOLDS

        errors: list[str] = []
        m = result.metrics

        # --- Check 1: Minimum trade count ---
        # Per E. Chan "Quantitative Trading": 30 is the statistical floor for
        # any validity claim (central limit theorem requires n >= 30).
        if m.total_trades < thresholds.min_num_trades:
            errors.append(
                f"Insufficient trades: {m.total_trades} < "
                f"{thresholds.min_num_trades} required"
            )

        # --- Check 2: Sharpe ratio ---
        # 0.5 is Chan's floor for "viable but needs human oversight".
        # 1.0 is the automation floor.
        if m.sharpe_ratio < thresholds.min_sharpe_ratio:
            errors.append(
                f"Sharpe ratio too low: {m.sharpe_ratio:.4f} < "
                f"{thresholds.min_sharpe_ratio}"
            )

        # --- Check 3: Max drawdown ---
        if m.max_drawdown_pct > thresholds.max_drawdown_pct:
            errors.append(
                f"Max drawdown too high: {m.max_drawdown_pct:.2f}% > "
                f"{thresholds.max_drawdown_pct}%"
            )

        # --- Check 4: Win rate (skipped when threshold is 0.0) ---
        # Disabled for trend-following templates (donchian_atr,
        # bb_squeeze_breakout) which operate at 35-45 % win rates by design
        # and achieve profitability through a favourable win/loss ratio.
        # Use min_expectancy as the quality gate instead.
        if thresholds.min_win_rate_pct > 0.0 and m.win_rate_pct < thresholds.min_win_rate_pct:
            errors.append(
                f"Win rate too low: {m.win_rate_pct:.2f}% < "
                f"{thresholds.min_win_rate_pct}%"
            )

        # --- Check 5: Profit factor ---
        if m.profit_factor < thresholds.min_profit_factor:
            errors.append(
                f"Profit factor too low: {m.profit_factor:.4f} < "
                f"{thresholds.min_profit_factor}"
            )

        # --- Check 6: Expectancy (always checked) ---
        # Expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        # Any positive expectancy means the strategy earns more than it loses
        # on average per trade, regardless of win rate.  This is the primary
        # quality gate when win rate checking is disabled.
        if m.expectancy < thresholds.min_expectancy:
            errors.append(
                f"Expectancy too low: {m.expectancy:.4f} USDT < "
                f"{thresholds.min_expectancy} USDT required"
            )

        # --- Check 7: Calmar ratio (skipped when threshold is 0.0) ---
        # Calmar = annualized_return / max_drawdown.  Calmar >= 1.0 means the
        # annual return is at least as large as the worst drawdown experienced.
        # float('inf') calmar (zero drawdown, positive return) always passes.
        if thresholds.min_calmar_ratio > 0.0:
            # inf calmar (no drawdown, positive return) is excellent — passes
            effective_calmar = (
                m.calmar_ratio
                if math.isfinite(m.calmar_ratio)
                else thresholds.min_calmar_ratio
            )
            if effective_calmar < thresholds.min_calmar_ratio:
                errors.append(
                    f"Calmar ratio too low: {m.calmar_ratio:.4f} < "
                    f"{thresholds.min_calmar_ratio} required "
                    f"(annualized return does not cover max drawdown)"
                )

        passed = len(errors) == 0

        # Determine tier label for structured log
        tier = "automated" if thresholds.min_calmar_ratio > 0.0 else "supervised"

        logger.info(
            "backtest_validation_complete",
            strategy_id=result.strategy_id,
            passed=passed,
            tier=tier,
            num_errors=len(errors),
            sharpe=m.sharpe_ratio,
            max_dd=m.max_drawdown_pct,
            win_rate=m.win_rate_pct,
            profit_factor=m.profit_factor,
            expectancy=m.expectancy,
            calmar=m.calmar_ratio,
            total_trades=m.total_trades,
        )

        return passed, errors
