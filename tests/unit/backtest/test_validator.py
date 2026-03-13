"""Comprehensive unit tests for BacktestValidator and ValidationThresholds.

Covers both validation tiers:
    - SUPERVISED_THRESHOLDS  (Tier-1, default) — manually-watched deployment
    - AUTOMATED_THRESHOLDS   (Tier-2)          — fully-automated deployment

Decision: DEC-2026-02-22-003 - Two-tier validation thresholds (E. Chan)
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from src.core.strategy.backtest.metrics import BacktestMetrics
from src.core.strategy.backtest.result import BacktestResult
from src.core.strategy.backtest.validator import (
    AUTOMATED_THRESHOLDS,
    SUPERVISED_THRESHOLDS,
    BacktestValidator,
    ValidationThresholds,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    sharpe: float = 1.2,
    max_dd: float = 10.0,
    win_rate: float = 55.0,
    profit_factor: float = 1.6,
    total_trades: int = 80,
    expectancy: float = 30.0,
    calmar: float | None = None,
    annualized_return: float = 42.5,
) -> BacktestResult:
    """Create a BacktestResult with the specified metrics.

    Defaults are a strategy that comfortably passes both Tier-1 and Tier-2.
    Override individual fields to exercise specific failure paths.
    """
    computed_calmar = (
        calmar
        if calmar is not None
        else annualized_return / max(max_dd, 0.001)
    )
    metrics = BacktestMetrics(
        total_return_pct=15.0,
        annualized_return_pct=annualized_return,
        sharpe_ratio=sharpe,
        sortino_ratio=sharpe * 1.2,
        calmar_ratio=computed_calmar,
        max_drawdown_pct=max_dd,
        max_drawdown_duration_days=5.0,
        total_trades=total_trades,
        winning_trades=int(total_trades * win_rate / 100),
        losing_trades=total_trades - int(total_trades * win_rate / 100),
        win_rate_pct=win_rate,
        profit_factor=profit_factor,
        expectancy=expectancy,
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
        template_id="ema_trend_rsi",
        symbol="BTCUSDT",
        timeframe="1h",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 4, 1, tzinfo=timezone.utc),
        initial_capital=10000.0,
        final_capital=11500.0,
        metrics=metrics,
    )


# ---------------------------------------------------------------------------
# ValidationThresholds — dataclass tests
# ---------------------------------------------------------------------------


class TestValidationThresholds:
    """Tests for ValidationThresholds dataclass and preset constants."""

    def test_default_values_are_supervised_tier(self) -> None:
        """Default constructor produces Tier-1 Supervised thresholds."""
        t = ValidationThresholds()
        assert t.min_sharpe_ratio == 0.5
        assert t.max_drawdown_pct == 25.0
        assert t.min_win_rate_pct == 0.0      # disabled — expectancy is the gate
        assert t.min_profit_factor == 1.35
        assert t.min_num_trades == 30
        assert t.min_expectancy == 0.01
        assert t.min_calmar_ratio == 0.0      # disabled in supervised

    def test_supervised_preset_matches_defaults(self) -> None:
        """SUPERVISED_THRESHOLDS should equal the default constructor."""
        assert SUPERVISED_THRESHOLDS == ValidationThresholds()

    def test_automated_preset_values(self) -> None:
        """AUTOMATED_THRESHOLDS should reflect Tier-2 values."""
        t = AUTOMATED_THRESHOLDS
        assert t.min_sharpe_ratio == 1.0
        assert t.max_drawdown_pct == 15.0
        assert t.min_win_rate_pct == 35.0
        assert t.min_profit_factor == 1.5
        assert t.min_num_trades == 60
        assert t.min_expectancy == 10.0
        assert t.min_calmar_ratio == 1.0

    def test_automated_is_stricter_than_supervised(self) -> None:
        """Automated thresholds must be strictly tighter in every dimension."""
        s = SUPERVISED_THRESHOLDS
        a = AUTOMATED_THRESHOLDS
        assert a.min_sharpe_ratio > s.min_sharpe_ratio
        assert a.max_drawdown_pct < s.max_drawdown_pct
        assert a.min_profit_factor > s.min_profit_factor
        assert a.min_num_trades > s.min_num_trades
        assert a.min_expectancy > s.min_expectancy
        # Win rate is disabled (0) in supervised and active in automated
        assert a.min_win_rate_pct > s.min_win_rate_pct
        assert a.min_calmar_ratio > s.min_calmar_ratio

    def test_custom_values_accepted(self) -> None:
        """Custom thresholds should be accepted."""
        t = ValidationThresholds(
            min_sharpe_ratio=2.0,
            max_drawdown_pct=5.0,
            min_win_rate_pct=60.0,
            min_profit_factor=2.0,
            min_num_trades=200,
            min_expectancy=50.0,
            min_calmar_ratio=3.0,
        )
        assert t.min_sharpe_ratio == 2.0
        assert t.min_num_trades == 200

    def test_frozen(self) -> None:
        """Thresholds should be immutable."""
        t = ValidationThresholds()
        with pytest.raises(AttributeError):
            t.min_sharpe_ratio = 99.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BacktestValidator — Tier-1 Supervised (default)
# ---------------------------------------------------------------------------


class TestBacktestValidatorSupervised:
    """Tests using default Supervised (Tier-1) thresholds."""

    def test_passing_result(self) -> None:
        """Result meeting all supervised thresholds should pass."""
        result = _make_result()
        passed, errors = BacktestValidator.validate(result)
        assert passed is True
        assert errors == []

    def test_failing_sharpe(self) -> None:
        """Sharpe below 0.5 should fail."""
        result = _make_result(sharpe=0.3)
        passed, errors = BacktestValidator.validate(result)
        assert passed is False
        assert any("Sharpe" in e for e in errors)

    def test_sharpe_at_boundary_passes(self) -> None:
        """Sharpe exactly at 0.5 should pass."""
        result = _make_result(sharpe=0.5)
        passed, _ = BacktestValidator.validate(result)
        assert passed is True

    def test_failing_max_drawdown(self) -> None:
        """Drawdown above 25 % should fail."""
        result = _make_result(max_dd=30.0)
        passed, errors = BacktestValidator.validate(result)
        assert passed is False
        assert any("drawdown" in e.lower() for e in errors)

    def test_max_drawdown_at_boundary_passes(self) -> None:
        """Drawdown exactly at 25 % should pass."""
        result = _make_result(max_dd=25.0)
        passed, _ = BacktestValidator.validate(result)
        assert passed is True

    def test_win_rate_not_checked_when_threshold_zero(self) -> None:
        """Win rate should NOT be checked when min_win_rate_pct == 0.0.

        This is the key change from the old validator.  A donchian_atr
        strategy with 40 % win rate and good profit factor should pass
        supervised validation.
        """
        result = _make_result(win_rate=20.0)  # would have failed old 50% gate
        passed, errors = BacktestValidator.validate(result)
        # Win rate error must NOT appear — other checks may still fail
        assert not any("Win rate" in e for e in errors)

    def test_failing_profit_factor(self) -> None:
        """Profit factor below 1.35 should fail."""
        result = _make_result(profit_factor=1.0)
        passed, errors = BacktestValidator.validate(result)
        assert passed is False
        assert any("Profit factor" in e for e in errors)

    def test_failing_trade_count(self) -> None:
        """Too few trades (< 30) should fail."""
        result = _make_result(total_trades=10)
        passed, errors = BacktestValidator.validate(result)
        assert passed is False
        assert any("trades" in e.lower() for e in errors)

    def test_trade_count_at_boundary_passes(self) -> None:
        """Exactly 30 trades should pass."""
        result = _make_result(total_trades=30)
        passed, _ = BacktestValidator.validate(result)
        assert passed is True

    def test_failing_expectancy(self) -> None:
        """Negative expectancy should fail (always checked)."""
        result = _make_result(expectancy=-5.0)
        passed, errors = BacktestValidator.validate(result)
        assert passed is False
        assert any("Expectancy" in e for e in errors)

    def test_zero_expectancy_fails(self) -> None:
        """Zero expectancy is below the 0.01 floor and should fail."""
        result = _make_result(expectancy=0.0)
        passed, errors = BacktestValidator.validate(result)
        assert passed is False
        assert any("Expectancy" in e for e in errors)

    def test_calmar_not_checked_in_supervised(self) -> None:
        """Calmar ratio should NOT be checked in supervised tier."""
        result = _make_result(calmar=0.1)  # very low calmar
        passed, errors = BacktestValidator.validate(result)
        # Calmar error must NOT appear
        assert not any("Calmar" in e for e in errors)

    def test_trend_following_strategy_passes(self) -> None:
        """40 % win rate, PF=1.56, Sharpe=0.7 should pass supervised.

        This is the canonical E. Chan trend-following scenario:
        - Low win rate (40 %) is normal for breakout strategies
        - High average win / average loss compensates (PF = 1.56)
        - This scenario would have been wrongly rejected by the old validator.
        """
        result = _make_result(
            win_rate=40.0,
            profit_factor=1.56,
            sharpe=0.7,
            max_dd=18.0,
            total_trades=45,
            expectancy=15.0,
            calmar=0.8,
        )
        passed, errors = BacktestValidator.validate(result)
        assert passed is True, f"Expected pass, got errors: {errors}"

    def test_multiple_failures_reported(self) -> None:
        """Multiple failures should all be reported (no early exit)."""
        result = _make_result(
            sharpe=0.1,       # fails: < 0.5
            max_dd=30.0,      # fails: > 25.0
            profit_factor=0.8,  # fails: < 1.35
            total_trades=5,   # fails: < 30
            expectancy=-10.0, # fails: < 0.01
        )
        passed, errors = BacktestValidator.validate(result)
        assert passed is False
        assert len(errors) == 5  # all five active checks fail


# ---------------------------------------------------------------------------
# BacktestValidator — Tier-2 Automated
# ---------------------------------------------------------------------------


class TestBacktestValidatorAutomated:
    """Tests using AUTOMATED_THRESHOLDS (Tier-2)."""

    def test_passing_result(self) -> None:
        """Result meeting all automated thresholds should pass."""
        result = _make_result(
            sharpe=1.2,
            max_dd=10.0,
            win_rate=55.0,
            profit_factor=1.6,
            total_trades=80,
            expectancy=30.0,
            calmar=4.0,
        )
        passed, errors = BacktestValidator.validate(result, AUTOMATED_THRESHOLDS)
        assert passed is True
        assert errors == []

    def test_failing_sharpe(self) -> None:
        """Sharpe below 1.0 should fail automated."""
        result = _make_result(sharpe=0.8)
        passed, errors = BacktestValidator.validate(result, AUTOMATED_THRESHOLDS)
        assert passed is False
        assert any("Sharpe" in e for e in errors)

    def test_sharpe_passes_supervised_but_fails_automated(self) -> None:
        """Sharpe=0.7 passes supervised tier but fails automated tier."""
        result = _make_result(sharpe=0.7)
        sup_passed, _ = BacktestValidator.validate(result, SUPERVISED_THRESHOLDS)
        auto_passed, _ = BacktestValidator.validate(result, AUTOMATED_THRESHOLDS)
        assert sup_passed is True
        assert auto_passed is False

    def test_failing_max_drawdown(self) -> None:
        """Drawdown above 15 % should fail automated."""
        result = _make_result(max_dd=20.0)
        passed, errors = BacktestValidator.validate(result, AUTOMATED_THRESHOLDS)
        assert passed is False
        assert any("drawdown" in e.lower() for e in errors)

    def test_drawdown_passes_supervised_fails_automated(self) -> None:
        """20 % drawdown passes supervised (<=25%) but fails automated (<=15%)."""
        result = _make_result(max_dd=20.0)
        sup_passed, _ = BacktestValidator.validate(result, SUPERVISED_THRESHOLDS)
        auto_passed, _ = BacktestValidator.validate(result, AUTOMATED_THRESHOLDS)
        assert sup_passed is True
        assert auto_passed is False

    def test_failing_win_rate(self) -> None:
        """Win rate below 35 % should fail automated."""
        result = _make_result(win_rate=30.0, expectancy=5.0)
        passed, errors = BacktestValidator.validate(result, AUTOMATED_THRESHOLDS)
        assert passed is False
        assert any("Win rate" in e for e in errors)

    def test_trend_following_40pct_winrate_passes_automated(self) -> None:
        """40 % win rate (trend strategy) should pass automated tier.

        The old 50 % threshold would reject this.  The new 35 % threshold
        allows legitimate breakout strategies while still blocking broken ones.
        """
        result = _make_result(
            win_rate=40.0,
            profit_factor=1.6,
            sharpe=1.1,
            max_dd=12.0,
            total_trades=65,
            expectancy=18.0,
            calmar=1.4,
        )
        passed, errors = BacktestValidator.validate(result, AUTOMATED_THRESHOLDS)
        assert passed is True, f"Expected pass, got errors: {errors}"

    def test_failing_profit_factor(self) -> None:
        """Profit factor below 1.5 should fail automated."""
        result = _make_result(profit_factor=1.4)
        passed, errors = BacktestValidator.validate(result, AUTOMATED_THRESHOLDS)
        assert passed is False
        assert any("Profit factor" in e for e in errors)

    def test_failing_trade_count(self) -> None:
        """Fewer than 60 trades should fail automated."""
        result = _make_result(total_trades=45)
        passed, errors = BacktestValidator.validate(result, AUTOMATED_THRESHOLDS)
        assert passed is False
        assert any("trades" in e.lower() for e in errors)

    def test_failing_expectancy(self) -> None:
        """Expectancy below $10 should fail automated."""
        result = _make_result(expectancy=5.0)
        passed, errors = BacktestValidator.validate(result, AUTOMATED_THRESHOLDS)
        assert passed is False
        assert any("Expectancy" in e for e in errors)

    def test_failing_calmar_ratio(self) -> None:
        """Calmar below 1.0 should fail automated."""
        # annualized=5%, max_dd=20% => calmar=0.25
        result = _make_result(
            annualized_return=5.0,
            max_dd=20.0,
            calmar=0.25,
            sharpe=1.1,
            win_rate=45.0,
            profit_factor=1.6,
            total_trades=65,
            expectancy=12.0,
        )
        passed, errors = BacktestValidator.validate(result, AUTOMATED_THRESHOLDS)
        assert passed is False
        assert any("Calmar" in e for e in errors)

    def test_infinite_calmar_passes(self) -> None:
        """float('inf') Calmar (zero drawdown) should pass automated."""
        result = _make_result(
            calmar=math.inf,
            max_dd=0.0,
            sharpe=1.2,
            win_rate=55.0,
            profit_factor=1.6,
            total_trades=65,
            expectancy=15.0,
        )
        passed, errors = BacktestValidator.validate(result, AUTOMATED_THRESHOLDS)
        assert not any("Calmar" in e for e in errors)

    def test_multiple_failures_automated(self) -> None:
        """All five active checks that can fail should be reported together."""
        result = _make_result(
            sharpe=0.1,        # fails: < 1.0
            max_dd=25.0,       # fails: > 15.0
            win_rate=20.0,     # fails: < 35.0
            profit_factor=0.5, # fails: < 1.5
            total_trades=5,    # fails: < 60
            expectancy=25.0,   # passes: 25 >= 10
            calmar=1.7,        # passes: 1.7 >= 1.0
        )
        passed, errors = BacktestValidator.validate(result, AUTOMATED_THRESHOLDS)
        assert passed is False
        assert len(errors) == 5


# ---------------------------------------------------------------------------
# BacktestValidator — custom thresholds backward compatibility
# ---------------------------------------------------------------------------


class TestBacktestValidatorCustomThresholds:
    """Tests that custom thresholds still work (backward compatibility)."""

    def test_custom_threshold_overrides_default(self) -> None:
        """Custom min_sharpe=0.2 should allow sharpe=0.3 to pass."""
        result = _make_result(sharpe=0.3)
        thresholds = ValidationThresholds(min_sharpe_ratio=0.2)
        passed, _ = BacktestValidator.validate(result, thresholds)
        assert passed is True

    def test_can_enable_win_rate_check_via_custom(self) -> None:
        """Setting min_win_rate_pct > 0 should activate the check."""
        result = _make_result(win_rate=30.0)
        thresholds = ValidationThresholds(min_win_rate_pct=50.0)
        passed, errors = BacktestValidator.validate(result, thresholds)
        assert passed is False
        assert any("Win rate" in e for e in errors)

    def test_can_enable_calmar_check_via_custom(self) -> None:
        """Setting min_calmar_ratio > 0 should activate the check."""
        result = _make_result(calmar=0.3)
        thresholds = ValidationThresholds(min_calmar_ratio=1.0)
        passed, errors = BacktestValidator.validate(result, thresholds)
        assert passed is False
        assert any("Calmar" in e for e in errors)

    def test_none_thresholds_uses_supervised_defaults(self) -> None:
        """Passing None should fall back to SUPERVISED_THRESHOLDS."""
        result = _make_result()
        passed_none, _ = BacktestValidator.validate(result, None)
        passed_explicit, _ = BacktestValidator.validate(result, SUPERVISED_THRESHOLDS)
        assert passed_none == passed_explicit


# ---------------------------------------------------------------------------
# BacktestResult — serialisation and summary (unchanged behaviour)
# ---------------------------------------------------------------------------


class TestBacktestResult:
    """Tests for BacktestResult dataclass — serialisation and display."""

    def test_to_dict(self) -> None:
        """to_dict should serialise all fields."""
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
