"""Unit tests for the portfolio capital model in run_live_trading.

Decision: DEC-2026-05-31-003 (PARA-12). Each live strategy is allocated a slice
of total capital rather than the full account; activation is bounded by a
concurrency cap and a capital reserve. These tests cover the two portfolio
rails in `_can_activate_tier`.
"""
from __future__ import annotations

from scripts.run_live_trading import LiveTier, _can_activate_tier


def _tier(capital: float, active: bool, label: str = "T") -> LiveTier:
    """Build a minimal LiveTier with a given capital and active flag."""
    t = LiveTier(
        label=label,
        template="dummy_template",
        symbol="BTCUSDT",
        capital=capital,
        activation_threshold=0.0,
        regime_tag="all",
        params={},
        lookback_bars=10,
    )
    t.active = active
    return t


class TestConcurrencyCap:
    """Rail 1: at most max_concurrent tiers active at once."""

    def test_blocks_when_at_max(self) -> None:
        active = [_tier(4.0, active=True, label=f"A{i}") for i in range(4)]
        candidate = _tier(4.0, active=False, label="cand")
        allowed, reason = _can_activate_tier(
            candidate,
            active + [candidate],
            max_concurrent=4,
            reserve_cap_usdt=1000.0,  # generous — isolate the count rail
        )
        assert allowed is False
        assert "concurrency cap" in reason

    def test_allows_below_max(self) -> None:
        active = [_tier(4.0, active=True, label=f"A{i}") for i in range(3)]
        candidate = _tier(4.0, active=False, label="cand")
        allowed, reason = _can_activate_tier(
            candidate,
            active + [candidate],
            max_concurrent=4,
            reserve_cap_usdt=1000.0,
        )
        assert allowed is True
        assert reason == ""


class TestCapitalReserve:
    """Rail 2: projected committed capital must not exceed the reserve cap."""

    def test_blocks_when_projected_exceeds_cap(self) -> None:
        # 3 active x $30 = $90 committed; +$30 candidate -> $120 > $100 cap.
        active = [_tier(30.0, active=True, label=f"A{i}") for i in range(3)]
        candidate = _tier(30.0, active=False, label="cand")
        allowed, reason = _can_activate_tier(
            candidate,
            active + [candidate],
            max_concurrent=10,  # generous — isolate the reserve rail
            reserve_cap_usdt=100.0,
        )
        assert allowed is False
        assert "capital reserve" in reason

    def test_allows_within_cap(self) -> None:
        # 2 active x $20 = $40 committed; +$20 candidate -> $60 <= $100 cap.
        active = [_tier(20.0, active=True, label=f"A{i}") for i in range(2)]
        candidate = _tier(20.0, active=False, label="cand")
        allowed, reason = _can_activate_tier(
            candidate,
            active + [candidate],
            max_concurrent=10,
            reserve_cap_usdt=100.0,
        )
        assert allowed is True
        assert reason == ""

    def test_projected_check_blocks_single_overshoot(self) -> None:
        # Current committed ($80) is UNDER the cap ($85), but activating the
        # candidate would push it to $100 — the projected check must block it,
        # proving we don't permit a single overshoot past the reserve.
        active = [_tier(80.0, active=True, label="A0")]
        candidate = _tier(20.0, active=False, label="cand")
        allowed, reason = _can_activate_tier(
            candidate,
            active + [candidate],
            max_concurrent=10,
            reserve_cap_usdt=85.0,
        )
        assert allowed is False
        assert "capital reserve" in reason


class TestDefaultPortfolioConfigCoherence:
    """The shipped defaults must let the intended portfolio fit the reserve."""

    def test_four_default_strategies_fit_under_reserve(self) -> None:
        # 4 strategies x 20% = 80% committed, under the 85% reserve.
        from scripts.run_live_trading import (
            CAPITAL_RESERVE_FRACTION,
            MAX_STRATEGIES_LIVE_CONCURRENT,
            PER_STRATEGY_ALLOCATION_PCT,
        )

        committed_fraction = (
            MAX_STRATEGIES_LIVE_CONCURRENT * PER_STRATEGY_ALLOCATION_PCT
        )
        assert committed_fraction <= CAPITAL_RESERVE_FRACTION
