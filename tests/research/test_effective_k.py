"""Tests for effective-K derivation and the K / variance_sr sweeps (spec 6)."""
from __future__ import annotations

import math

from research.validation.deflated_sharpe import deflated_sharpe_ratio
from research.validation.effective_k import (
    MIN_VARIANCE_SR,
    RETROSPECTIVE_K_SWEEP,
    estimate_portfolio_k,
    regime_conditional_k,
    variance_sr_point_estimate,
    variance_sr_sweep,
)


def test_k_estimate_includes_parameter_combinations() -> None:
    """K must include parameter combinations, not just hypothesis x symbol count."""
    est = estimate_portfolio_k(
        hypotheses_counted=23,
        symbols_per_hypothesis_avg=5.0,
        param_combos_recorded=0,
        param_combos_estimated=23 * 50,
        notes="test",
    )
    # 23*50 = 1150 param combos dwarfs the 23*5 = 115 symbol floor.
    assert est.point_estimate == 1150
    assert est.derivation.param_combos_estimated == 1150
    assert est.derivation.is_lower_bound is True
    assert est.derivation.method == "estimated_lower_bound"


def test_k_sweep_contains_mandatory_grid_and_point_estimate() -> None:
    """The sweep always includes 115, 500, 2000 plus the point estimate."""
    est = estimate_portfolio_k(
        hypotheses_counted=10,
        symbols_per_hypothesis_avg=5.0,
        param_combos_recorded=0,
        param_combos_estimated=1150,
    )
    for k in RETROSPECTIVE_K_SWEEP:
        assert k in est.sweep
    assert est.point_estimate in est.sweep
    # Gating K is the most conservative (highest) value.
    assert est.gating_k == max(est.sweep)


def test_recorded_combos_are_not_a_lower_bound() -> None:
    """When parameter combos are recorded, the estimate is not flagged lower-bound."""
    est = estimate_portfolio_k(
        hypotheses_counted=5,
        symbols_per_hypothesis_avg=3.0,
        param_combos_recorded=400,
        param_combos_estimated=0,
    )
    assert est.derivation.is_lower_bound is False
    assert est.derivation.method == "db_reconstructed_partial"
    assert est.point_estimate == 400


def test_multi_k_sweep_is_monotonic_deflation() -> None:
    """Larger K => larger expected-max-Sharpe => lower DSR => higher p-value."""
    returns_sharpe = 0.5
    # Fixed return-series moments; only K varies.
    p_values = []
    for k in (1, 115, 500, 2000):
        result = deflated_sharpe_ratio(
            observed_sharpe=returns_sharpe,
            variance_sr=0.05,
            n_trials=k,
            n_returns=40,
            skewness=-0.1,
            kurtosis=3.0,
        )
        p_values.append(result.dsr_p_value)
    # Monotonic non-decreasing in K.
    assert all(b >= a - 1e-12 for a, b in zip(p_values, p_values[1:]))
    # And strictly higher at the extremes.
    assert p_values[-1] > p_values[0]


def test_variance_sr_point_estimate_from_dispersion() -> None:
    """variance_sr is the sample variance of the strategies' Sharpe ratios."""
    sharpes = [0.2, 0.5, 0.8, 1.1]
    est = variance_sr_point_estimate(sharpes)
    assert est > MIN_VARIANCE_SR
    # Degenerate input (fewer than 2) -> floor.
    assert variance_sr_point_estimate([0.5]) == MIN_VARIANCE_SR


def test_variance_sr_sweep_factors() -> None:
    """The variance_sr sweep is 0.5x, 1.0x, 2.0x of the point estimate."""
    grid = variance_sr_sweep(0.10)
    assert math.isclose(min(grid), 0.05, rel_tol=1e-9)
    assert math.isclose(max(grid), 0.20, rel_tol=1e-9)
    assert len(grid) == 3


def test_variance_sr_sweep_respects_floor() -> None:
    """Sweep values never drop below the variance_sr floor."""
    grid = variance_sr_sweep(MIN_VARIANCE_SR / 10.0)
    assert all(v >= MIN_VARIANCE_SR for v in grid)


def test_regime_conditional_k_multiplies_by_bucket_count() -> None:
    """Guard #2: effective K multiplies by the number of regime buckets tested."""
    base = estimate_portfolio_k(
        hypotheses_counted=10,
        symbols_per_hypothesis_avg=5.0,
        param_combos_recorded=0,
        param_combos_estimated=1150,
    )
    scaled = regime_conditional_k(base, n_regime_buckets=3)
    assert scaled.point_estimate == base.point_estimate * 3
    assert scaled.point_estimate in scaled.sweep
    assert scaled.gating_k == max(scaled.sweep)
    # Auditable: derivation records the regime multiplier.
    assert "regime buckets" in scaled.derivation.notes
    assert scaled.derivation.effective_k_point_estimate == base.point_estimate * 3


def test_regime_conditional_k_floors_bucket_count_at_one() -> None:
    """Zero/negative bucket counts are treated as 1 (no extra trials)."""
    base = estimate_portfolio_k(
        hypotheses_counted=5,
        symbols_per_hypothesis_avg=3.0,
        param_combos_recorded=400,
        param_combos_estimated=0,
    )
    same = regime_conditional_k(base, n_regime_buckets=0)
    assert same.point_estimate == base.point_estimate


def test_regime_conditional_k_increases_deflation() -> None:
    """More regime buckets => higher gating K => higher (worse) DSR p-value."""
    base = estimate_portfolio_k(
        hypotheses_counted=10,
        symbols_per_hypothesis_avg=5.0,
        param_combos_recorded=0,
        param_combos_estimated=200,
    )
    scaled = regime_conditional_k(base, n_regime_buckets=3)
    p_base = deflated_sharpe_ratio(
        observed_sharpe=0.5, variance_sr=0.05, n_trials=base.gating_k,
        n_returns=40, skewness=-0.1, kurtosis=3.0,
    ).dsr_p_value
    p_scaled = deflated_sharpe_ratio(
        observed_sharpe=0.5, variance_sr=0.05, n_trials=scaled.gating_k,
        n_returns=40, skewness=-0.1, kurtosis=3.0,
    ).dsr_p_value
    assert p_scaled >= p_base - 1e-12
