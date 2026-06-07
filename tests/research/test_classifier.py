"""Tests for the Tier A/B/C/D classifier + base-vs-conservative resolution."""
from __future__ import annotations

from research.biographies.schema import Tier
from research.promotion.classifier import (
    MIN_N_FOR_CLASSIFICATION,
    action_description,
    build_hard_floor_status,
    classify_tier,
    recommended_action,
    resolve_final_tier,
)


def test_tier_a_requires_all_strict_thresholds() -> None:
    """Tier A: DSR p<0.2, MaxDD<5%, PF>=1.35, Sharpe>=1.0, N>=30."""
    assert classify_tier(0.15, 4.0, 1.5, 1.2, 40) == Tier.TIER_A
    # Miss N -> not Tier A (drops to B if it clears B thresholds).
    assert classify_tier(0.15, 4.0, 1.5, 1.2, 25) == Tier.TIER_B


def test_tier_b_relaxed_thresholds() -> None:
    """Tier B: DSR p<0.3, MaxDD<5%, PF>=1.25, Sharpe>=0.8, N>=20."""
    assert classify_tier(0.28, 4.0, 1.30, 0.9, 22) == Tier.TIER_B


def test_dsr_floor_blocks_tier_a_and_b() -> None:
    """p>=0.3 cannot be Tier A or B regardless of other metrics."""
    assert classify_tier(0.35, 2.0, 2.0, 2.0, 100) == Tier.TIER_C


def test_tier_d_on_high_p_or_high_dd() -> None:
    """Tier D: p>=0.5 OR MaxDD>=10%."""
    assert classify_tier(0.6, 2.0, 2.0, 2.0, 100) == Tier.TIER_D
    assert classify_tier(0.1, 12.0, 2.0, 2.0, 100) == Tier.TIER_D


def test_resolve_gates_on_conservative() -> None:
    """The final tier is the conservative tier when both agree or simply lower."""
    final, fragile = resolve_final_tier(Tier.TIER_A, Tier.TIER_B)
    assert final == Tier.TIER_B
    assert fragile is True

    final2, fragile2 = resolve_final_tier(Tier.TIER_A, Tier.TIER_A)
    assert final2 == Tier.TIER_A
    assert fragile2 is False


def test_real_but_fragile_softens_d_to_c() -> None:
    """Tier A/B base + Tier D conservative -> held at Tier C (not retired)."""
    final, fragile = resolve_final_tier(Tier.TIER_A, Tier.TIER_D)
    assert final == Tier.TIER_C
    assert fragile is True

    final_b, _ = resolve_final_tier(Tier.TIER_B, Tier.TIER_D)
    assert final_b == Tier.TIER_C


def test_genuine_no_edge_stays_d() -> None:
    """Tier D in both cases stays Tier D (safe to retire)."""
    final, fragile = resolve_final_tier(Tier.TIER_D, Tier.TIER_D)
    assert final == Tier.TIER_D
    assert fragile is False


def test_insufficient_data_below_min_n_not_reject() -> None:
    """N below the minimum -> INSUFFICIENT_DATA, never TIER_D (DEC-2026-06-04-014).

    This is the guard for the 2026-06-05 Neon-run misread: degenerate N=0..few
    strategies were shown as TIER_D_REJECT. "No data" is not "proven noise".
    """
    # N=0 with a degenerate DSR p=1.0 must NOT be a reject.
    assert classify_tier(1.0, 0.0, 0.0, 0.0, 0) == Tier.INSUFFICIENT_DATA
    # N just below the floor -> still insufficient, even with great metrics.
    assert classify_tier(0.05, 1.0, 2.0, 2.0, MIN_N_FOR_CLASSIFICATION - 1) == (
        Tier.INSUFFICIENT_DATA
    )


def test_at_min_n_classifies_normally() -> None:
    """At exactly the minimum N the normal A/B/C/D logic applies again."""
    # At the floor, a noise-level p still rejects (it has enough data to judge).
    assert classify_tier(0.6, 2.0, 2.0, 2.0, MIN_N_FOR_CLASSIFICATION) == Tier.TIER_D
    # And a clean low-p low-N case lands Tier C (misses Tier B's N>=20 floor).
    assert classify_tier(0.1, 2.0, 2.0, 2.0, MIN_N_FOR_CLASSIFICATION) == Tier.TIER_C


def test_action_maps_cover_insufficient_data() -> None:
    """Both action maps handle INSUFFICIENT_DATA (no KeyError) and signal 'gather'."""
    assert recommended_action(Tier.INSUFFICIENT_DATA) == "gather_more_data"
    assert "Insufficient data" in action_description(Tier.INSUFFICIENT_DATA)


def test_hard_floor_status_records_unverified_cost() -> None:
    """Hard floor status records cost_model_verified=False for v0."""
    status = build_hard_floor_status(0.18, 4.0, cost_model_verified=False)
    assert status.dsr_passed is True
    assert status.max_dd_passed is True
    assert status.cost_model_verified is False
    assert status.leakage_check == "not_run"
    # p>=0.3 fails the DSR floor.
    failing = build_hard_floor_status(0.4, 4.0, cost_model_verified=False)
    assert failing.dsr_passed is False
