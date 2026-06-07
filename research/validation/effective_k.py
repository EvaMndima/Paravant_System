"""Effective-K derivation and the K / variance_sr sensitivity sweeps (spec 6).

The Deflated Sharpe Ratio deflates an observed Sharpe against the expected
MAXIMUM Sharpe that ``K`` zero-edge trials would produce by luck. Two inputs
drive that benchmark and are each decisive:

1. ``K`` (effective number of trials). Section 4.4 of the spec proves the same
   strategy is Tier A at K=115 but fails the floor at K>=500. A single
   hardcoded, memory-derived K is rejected (DEC-2026-06-04-012). We derive K
   where the database records it and SWEEP it otherwise.

2. ``variance_sr`` (cross-sectional variance of per-trade Sharpe estimates
   across trials). It scales the benchmark directly: larger -> harder to pass.
   It is estimated from a biased, small (11-strategy) sample, so it is swept
   unconditionally exactly like K (spec Section 6.4).

DATA REALITY (2026-06-05 reconnaissance): the database holds NO recorded
parameter-combination counts or optimization history for these eleven
strategies. So K cannot be reconstructed exactly here; it is an ESTIMATED lower
bound whose derivation is stored in the biography for auditability (spec Section
6.2), and the mandatory multi-K sweep [115, 500, 2000] is always reported with
the GATING verdict using the most conservative (highest) K.

Research-only module: ``src/`` must never import from here (PRD Section 5.2).
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from research.biographies.schema import EffectiveKDerivation

# Mandatory multi-K sweep grid (spec Section 6.3). Every strategy reports DSR at
# these K values plus the DB-derived/estimated point estimate.
RETROSPECTIVE_K_SWEEP: tuple[int, ...] = (115, 500, 2000)

# variance_sr sweep factors applied to the point estimate (spec Section 6.4).
VARIANCE_SR_SWEEP_FACTORS: tuple[float, ...] = (0.5, 1.0, 2.0)

# Floor for the variance_sr point estimate. A variance_sr of exactly 0 makes the
# expected-max-Sharpe benchmark 0 (no deflation), which is unrealistically
# optimistic; this floor keeps the deflation honest when the sampled dispersion
# is degenerate (e.g. fewer than two strategies).
MIN_VARIANCE_SR: float = 0.01


@dataclass(frozen=True)
class EffectiveKEstimate:
    """Effective-K point estimate plus the swept grid and its derivation.

    Attributes:
        point_estimate: The base-case effective K (used for the BASE operating
            point, spec Section 6.5).
        gating_k: The conservative (highest defensible) K that gates the verdict.
        sweep: Sorted unique K values to report DSR at (grid + point estimate).
        derivation: Auditable record of how the point estimate was reached.
    """

    point_estimate: int
    gating_k: int
    sweep: tuple[int, ...]
    derivation: EffectiveKDerivation = field(
        default_factory=lambda: EffectiveKDerivation(
            method="estimated", effective_k_point_estimate=0
        )
    )


def estimate_portfolio_k(
    *,
    hypotheses_counted: int,
    symbols_per_hypothesis_avg: float,
    param_combos_recorded: int,
    param_combos_estimated: int,
    notes: str = "",
) -> EffectiveKEstimate:
    """Estimate portfolio-level effective K from reconstructed search-space counts.

    Effective K is the actual hypothesis search space executed::

        K ~= sum over hypotheses of (param combinations x symbols x timeframes)

    Where parameter-combination counts are recorded, the real number is used;
    where only the surviving config exists with no recorded sweep, a per-strategy
    estimate is added and the whole estimate is flagged as a lower bound (the
    true K is higher). This must include parameter combinations or it reproduces
    the exact undercount the PRD repudiated (spec Section 6.1).

    Args:
        hypotheses_counted: Number of distinct hypotheses in the search space.
        symbols_per_hypothesis_avg: Average symbols tested per hypothesis.
        param_combos_recorded: Parameter combinations summed from recorded
            optimization history (0 here -- none recorded in the DB).
        param_combos_estimated: Estimated parameter combinations for runs with no
            recorded sweep.
        notes: Free-text derivation notes for the audit trail.

    Returns:
        An ``EffectiveKEstimate`` with the point estimate, gating K, sweep grid,
        and derivation. The point estimate is floored at 1 (a single trial means
        no selection bias).
    """
    combos_total = max(0, param_combos_recorded) + max(0, param_combos_estimated)
    # Lower bound: at least one combo per hypothesis-symbol pair even when no
    # sweep was recorded.
    floor_from_symbols = int(
        round(max(0, hypotheses_counted) * max(0.0, symbols_per_hypothesis_avg))
    )
    point_estimate = max(1, combos_total, floor_from_symbols)

    is_lower_bound = param_combos_recorded == 0  # nothing recorded -> lower bound
    method = "estimated_lower_bound" if is_lower_bound else "db_reconstructed_partial"

    sweep = _build_sweep(point_estimate)
    gating_k = max(sweep)  # conservative: highest defensible K gates the verdict

    derivation = EffectiveKDerivation(
        method=method,
        hypotheses_counted=hypotheses_counted,
        symbols_per_hypothesis_avg=symbols_per_hypothesis_avg,
        param_combos_recorded=param_combos_recorded,
        param_combos_estimated=param_combos_estimated,
        effective_k_point_estimate=point_estimate,
        is_lower_bound=is_lower_bound,
        notes=notes,
    )
    return EffectiveKEstimate(
        point_estimate=point_estimate,
        gating_k=gating_k,
        sweep=sweep,
        derivation=derivation,
    )


def _build_sweep(point_estimate: int) -> tuple[int, ...]:
    """Return the sorted unique K sweep (mandatory grid + point estimate).

    Args:
        point_estimate: The derived/estimated point-estimate K.

    Returns:
        Sorted unique tuple of K values, always including 115, 500, 2000.
    """
    values = set(RETROSPECTIVE_K_SWEEP)
    values.add(max(1, point_estimate))
    return tuple(sorted(values))


def variance_sr_point_estimate(per_strategy_sharpes: list[float]) -> float:
    """Cross-sectional variance of per-trade Sharpe estimates across trials.

    Estimated from the dispersion of the Sharpe ratios actually observed across
    the analyzed strategies. Honest caveat (spec Section 6.4): these strategies
    are a SELECTED, small sample (survivors + retirees we kept records for), so
    this is a biased estimate of the true cross-trial dispersion -- which is
    exactly why it is swept, not trusted as a point value.

    Args:
        per_strategy_sharpes: Per-trade Sharpe ratio of each analyzed strategy.

    Returns:
        The sample variance (ddof=1) of the Sharpe ratios, floored at
        ``MIN_VARIANCE_SR``. Returns the floor if fewer than two values.
    """
    finite = [s for s in per_strategy_sharpes if s == s]  # drop NaN (NaN != NaN)
    if len(finite) < 2:
        return MIN_VARIANCE_SR
    return max(MIN_VARIANCE_SR, statistics.variance(finite))


def regime_conditional_k(
    base: EffectiveKEstimate, n_regime_buckets: int
) -> EffectiveKEstimate:
    """Scale an effective-K estimate by the number of regime buckets tested.

    Guard #2 (DEC-2026-06-04-014): computing DSR separately within each of
    ``n_regime_buckets`` regime buckets and keeping the best is selection bias
    ACROSS regimes. The effective number of trials must multiply by the bucket
    count or the deflation understates the search and the screen is dishonest::

        regime_conditional_K = base_K x n_regime_buckets

    The fixed sensitivity grid (115, 500, 2000) is preserved; the regime-scaled
    point estimate is folded into the sweep so the gating (highest) K reflects
    the larger search space.

    Args:
        base: The non-regime effective-K estimate (param-combos x symbols x
            timeframes), e.g. from ``estimate_portfolio_k``.
        n_regime_buckets: Number of regime buckets DSR is computed across (3 for
            coarse bull/bear/chop, more for fine SubRegimes). Values < 1 are
            treated as 1 (no regime split adds no trials).

    Returns:
        A new ``EffectiveKEstimate`` with point estimate and gating K scaled by
        the bucket count and the derivation annotated for auditability.
    """
    buckets = max(1, n_regime_buckets)
    scaled_point = max(1, base.point_estimate * buckets)
    sweep = _build_sweep(scaled_point)
    gating_k = max(sweep)

    d = base.derivation
    suffix = (
        f" Regime-conditional: x{buckets} regime buckets counted as trials "
        f"(guard #2, DEC-2026-06-04-014); base K {base.point_estimate} -> "
        f"{scaled_point}."
    )
    derivation = EffectiveKDerivation(
        method=d.method,
        hypotheses_counted=d.hypotheses_counted,
        symbols_per_hypothesis_avg=d.symbols_per_hypothesis_avg,
        param_combos_recorded=d.param_combos_recorded,
        param_combos_estimated=d.param_combos_estimated,
        effective_k_point_estimate=scaled_point,
        is_lower_bound=d.is_lower_bound,
        notes=(d.notes + suffix).strip(),
    )
    return EffectiveKEstimate(
        point_estimate=scaled_point,
        gating_k=gating_k,
        sweep=sweep,
        derivation=derivation,
    )


def variance_sr_sweep(point_estimate: float) -> tuple[float, ...]:
    """Return the variance_sr sweep grid (factors x point estimate).

    Args:
        point_estimate: The variance_sr point estimate.

    Returns:
        Sorted unique tuple of variance_sr values (0.5x, 1.0x, 2.0x of the
        point estimate), each floored at ``MIN_VARIANCE_SR``.
    """
    values = {
        max(MIN_VARIANCE_SR, point_estimate * factor)
        for factor in VARIANCE_SR_SWEEP_FACTORS
    }
    return tuple(sorted(values))
