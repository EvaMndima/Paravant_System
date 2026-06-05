"""Tests for the conservative cost model (spec Sections 5, 5.3, 5.5-pre)."""
from __future__ import annotations

import math

from research.backtest.cost_model import (
    CostModel,
    apply_cost_model,
    booked_cost_pct,
    compute_cost_breakdown,
    mean_round_trip_cost_pct_by_symbol,
)
from research.biographies.schema import CostComponentSource


def _trade(**overrides: object) -> dict[str, object]:
    """Build a synthetic trade dict with sensible defaults."""
    base: dict[str, object] = {
        "symbol": "DOGEUSDT",
        "entry_price": 0.10,
        "exit_price": 0.10,
        "quantity": 1000.0,
        "entry_commission": 0.05,
        "exit_commission": 0.05,
        "slippage_cost": 0.02,
        "return_pct": 1.0,
    }
    base.update(overrides)
    return base


def test_v0_components_are_all_estimated_and_padded() -> None:
    """In v0 there is no measured data, so spread and slippage are padded 2x."""
    cm = CostModel.v0_unverified()
    breakdown = compute_cost_breakdown(_trade(), cm)
    assert breakdown.spread_source is CostComponentSource.ESTIMATED
    assert breakdown.slippage_source is CostComponentSource.ESTIMATED
    # DOGE default spread 0.15 padded 2x -> 0.30; slippage 0.05 padded -> 0.10.
    assert math.isclose(breakdown.spread_pct_used, 0.30, rel_tol=1e-9)
    assert math.isclose(breakdown.slippage_pct_used, 0.10, rel_tol=1e-9)
    # Fee is never padded.
    assert math.isclose(breakdown.fee_pct, 0.10, rel_tol=1e-9)


def test_measured_components_are_not_padded() -> None:
    """Measured spread/slippage are used as-is (single-pad rule, spec 5.2)."""
    cm = CostModel(
        version="test",
        default_spread_pct_by_symbol={"DOGEUSDT": 0.15},
        fallback_spread_pct=0.20,
        taker_fee_pct=0.10,
        slippage_pct_default=0.05,
        estimate_pad=2.0,
        measured_spreads_pct={"DOGEUSDT": 0.15},
        measured_slippage_pct={"DOGEUSDT": 0.04},
    )
    breakdown = compute_cost_breakdown(_trade(), cm)
    assert breakdown.spread_source is CostComponentSource.MEASURED
    assert breakdown.slippage_source is CostComponentSource.MEASURED
    assert math.isclose(breakdown.spread_pct_used, 0.15, rel_tol=1e-9)
    assert math.isclose(breakdown.slippage_pct_used, 0.04, rel_tol=1e-9)


def test_hand_checked_doge_round_trip() -> None:
    """Reproduce the spec Section 5.3 hand-checked DOGE round-trip = 0.43%.

    spread p95 = 0.15 (measured), fee = 0.10, slippage = 0.04 (measured).
    cost_per_side = 0.15/2 + 0.10 + 0.04 = 0.215; round trip (flat) = 0.43.
    """
    cm = CostModel(
        version="test",
        default_spread_pct_by_symbol={"DOGEUSDT": 0.15},
        fallback_spread_pct=0.20,
        taker_fee_pct=0.10,
        slippage_pct_default=0.05,
        estimate_pad=2.0,
        measured_spreads_pct={"DOGEUSDT": 0.15},
        measured_slippage_pct={"DOGEUSDT": 0.04},
    )
    # exit == entry so exit_leg_scale == 1 and the round trip is symmetric.
    breakdown = compute_cost_breakdown(_trade(exit_price=0.10), cm)
    assert math.isclose(breakdown.cost_per_side_pct, 0.215, rel_tol=1e-9)
    assert math.isclose(breakdown.conservative_round_trip_cost_pct, 0.43, rel_tol=1e-9)


def test_large_winner_exit_leg_uses_exit_notional() -> None:
    """A +40% winner charges the exit leg on the larger exit notional (5.5-pre)."""
    cm = CostModel.v0_unverified()
    flat = compute_cost_breakdown(_trade(exit_price=0.10), cm)
    winner = compute_cost_breakdown(_trade(exit_price=0.14), cm)
    # exit_leg_scale is the notional ratio exit/entry.
    assert math.isclose(winner.exit_leg_scale, 1.4, rel_tol=1e-9)
    # The winner's round trip is strictly larger than the flat trade's because
    # the exit-leg cost is scaled up by 1.4, not 1.0.
    assert winner.conservative_round_trip_cost_pct > flat.conservative_round_trip_cost_pct
    expected = flat.cost_per_side_pct * (1.0 + 1.4)
    assert math.isclose(winner.conservative_round_trip_cost_pct, expected, rel_tol=1e-9)


def test_booked_cost_pct_from_recorded_fields() -> None:
    """Booked cost is (entry+exit commission + slippage_cost)/entry_notional."""
    trade = _trade(entry_commission=0.10, exit_commission=0.14, slippage_cost=0.05)
    # entry_notional = 0.10 * 1000 = 100. booked = (0.10+0.14+0.05)/100*100 = 0.29%.
    assert math.isclose(booked_cost_pct(trade), 0.29, rel_tol=1e-9)


def test_incremental_pad_is_excess_over_booked_floored_at_zero() -> None:
    """Incremental pad = max(0, conservative - booked); never negative."""
    cm = CostModel.v0_unverified()
    # Large booked cost exceeding the conservative model -> pad floored at 0.
    trade = _trade(entry_commission=5.0, exit_commission=5.0, slippage_cost=0.0)
    breakdown = compute_cost_breakdown(trade, cm)
    assert breakdown.incremental_pad_pct == 0.0
    adjusted = apply_cost_model(trade, cm)
    # Conservative return equals base when the pad is zero.
    assert math.isclose(adjusted.conservative_return_pct, adjusted.base_return_pct, rel_tol=1e-9)


def test_apply_cost_model_base_unchanged_conservative_subtracts_pad() -> None:
    """Base return is the recorded value; conservative subtracts the pad."""
    cm = CostModel.v0_unverified()
    trade = _trade(return_pct=2.0, exit_price=0.10)
    adjusted = apply_cost_model(trade, cm)
    assert math.isclose(adjusted.base_return_pct, 2.0, rel_tol=1e-9)
    expected = 2.0 - adjusted.breakdown.incremental_pad_pct
    assert math.isclose(adjusted.conservative_return_pct, expected, rel_tol=1e-9)
    assert adjusted.conservative_return_pct <= adjusted.base_return_pct


def test_unlisted_symbol_uses_padded_fallback_spread() -> None:
    """A symbol absent from the table uses the (padded) fallback spread."""
    cm = CostModel.v0_unverified()
    breakdown = compute_cost_breakdown(_trade(symbol="PEPEUSDT"), cm)
    # fallback 0.20 padded 2x -> 0.40.
    assert math.isclose(breakdown.spread_pct_used, 0.40, rel_tol=1e-9)


def test_mean_round_trip_cost_by_symbol() -> None:
    """Per-symbol mean round-trip cost is reported for operator sanity-check."""
    cm = CostModel.v0_unverified()
    trades = [
        _trade(symbol="BTCUSDT", entry_price=50000, exit_price=50000, quantity=0.01),
        _trade(symbol="DOGEUSDT", entry_price=0.10, exit_price=0.10, quantity=1000),
    ]
    costs = mean_round_trip_cost_pct_by_symbol(trades, cm)
    assert set(costs) == {"BTCUSDT", "DOGEUSDT"}
    # BTC spread is tighter than DOGE, so its round-trip cost is lower.
    assert costs["BTCUSDT"] < costs["DOGEUSDT"]
