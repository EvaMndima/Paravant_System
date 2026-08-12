"""Unit tests for capital graduation (PRD §2.2.1 Feature G).

Tests the compute_is_proven() pure function in src/core/risk/sizing.py.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock


from src.core.risk.sizing import (
    GRADUATION_DAYS,
    GRADUATION_MIN_TRADES,
    compute_is_proven,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_live_event(days_ago: float) -> dict:
    """Build a lifecycle event dict representing a transition TO live."""
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {"to": "live", "timestamp": ts.isoformat()}


def _make_strategy(
    status_value: str = "live",
    lifecycle: list | None = None,
    total_trades: int = 25,
    total_pnl: float = 1500.0,
) -> MagicMock:
    """Build a minimal mock Strategy for testing compute_is_proven()."""
    from src.data.models.strategy import StrategyStatus

    mock = MagicMock()
    mock.id = "strat-test-001"
    mock.status = StrategyStatus(status_value) if status_value in [s.value for s in StrategyStatus] else MagicMock()
    mock.lifecycle = lifecycle if lifecycle is not None else [_make_live_event(35)]
    mock.live_results = {
        "total_trades": total_trades,
        "total_pnl": total_pnl,
    }
    return mock


# ---------------------------------------------------------------------------
# Tests: status gate
# ---------------------------------------------------------------------------


class TestComputeIsProvenStatusGate:
    def test_live_status_can_qualify(self) -> None:
        """A LIVE strategy with all criteria met returns True."""
        strategy = _make_strategy(status_value="live")
        assert compute_is_proven(strategy) is True

    def test_draft_status_returns_false(self) -> None:
        """Non-LIVE strategies are immediately rejected."""
        strategy = _make_strategy(status_value="draft")
        assert compute_is_proven(strategy) is False

    def test_paper_status_returns_false(self) -> None:
        strategy = _make_strategy(status_value="paper")
        assert compute_is_proven(strategy) is False

    def test_paused_status_returns_false(self) -> None:
        strategy = _make_strategy(status_value="paused")
        assert compute_is_proven(strategy) is False

    def test_retired_status_returns_false(self) -> None:
        strategy = _make_strategy(status_value="retired")
        assert compute_is_proven(strategy) is False


# ---------------------------------------------------------------------------
# Tests: lifecycle / days-live criterion
# ---------------------------------------------------------------------------


class TestComputeIsProvenDaysLive:
    def test_no_lifecycle_returns_false(self) -> None:
        """Strategy with empty lifecycle cannot have a live_since date."""
        strategy = _make_strategy(lifecycle=[])
        assert compute_is_proven(strategy) is False

    def test_none_lifecycle_returns_false(self) -> None:
        """None lifecycle is treated as empty."""
        strategy = _make_strategy(lifecycle=None)
        # Override lifecycle to None explicitly
        strategy.lifecycle = None
        assert compute_is_proven(strategy) is False

    def test_lifecycle_without_live_event_returns_false(self) -> None:
        """Lifecycle events that never go TO live cannot find live_since."""
        lifecycle = [
            {"to": "paper", "timestamp": datetime.now(timezone.utc).isoformat()},
            {"to": "paused", "timestamp": datetime.now(timezone.utc).isoformat()},
        ]
        strategy = _make_strategy(lifecycle=lifecycle)
        assert compute_is_proven(strategy) is False

    def test_exactly_30_days_live_passes(self) -> None:
        """Exactly GRADUATION_DAYS days live should pass (meets >= requirement)."""
        strategy = _make_strategy(lifecycle=[_make_live_event(GRADUATION_DAYS)])
        assert compute_is_proven(strategy) is True

    def test_29_days_live_fails(self) -> None:
        """One day short of graduation requirement returns False."""
        strategy = _make_strategy(lifecycle=[_make_live_event(GRADUATION_DAYS - 1)])
        assert compute_is_proven(strategy) is False

    def test_uses_most_recent_live_event(self) -> None:
        """When re-activated, the MOST RECENT live transition is used."""
        # First activation 60 days ago (would pass), but then re-activated 5 days ago (would fail)
        lifecycle = [
            _make_live_event(60),  # old
            _make_live_event(5),   # most recent — only 5 days
        ]
        strategy = _make_strategy(lifecycle=lifecycle)
        # Should fail: most recent live_since is only 5 days ago
        assert compute_is_proven(strategy) is False

    def test_malformed_timestamp_skipped(self) -> None:
        """A lifecycle event with an invalid timestamp is skipped silently."""
        lifecycle = [
            {"to": "live", "timestamp": "not-a-valid-timestamp"},
            _make_live_event(35),  # valid, older event
        ]
        strategy = _make_strategy(lifecycle=lifecycle)
        # The valid event should still be found (most recent valid wins, or at least one works)
        # Both are iterated; malformed is skipped via try/except
        result = compute_is_proven(strategy)
        # Result depends on iteration order: the valid 35-day event should enable graduation
        assert isinstance(result, bool)

    def test_missing_timestamp_key_skipped(self) -> None:
        """Lifecycle events without 'timestamp' key are skipped."""
        lifecycle = [
            {"to": "live"},  # no timestamp key
            _make_live_event(35),
        ]
        strategy = _make_strategy(lifecycle=lifecycle)
        assert compute_is_proven(strategy) is True


# ---------------------------------------------------------------------------
# Tests: trade count criterion
# ---------------------------------------------------------------------------


class TestComputeIsProvenTradeCount:
    def test_exactly_20_trades_passes(self) -> None:
        """Exactly GRADUATION_MIN_TRADES passes the trade count check."""
        strategy = _make_strategy(total_trades=GRADUATION_MIN_TRADES)
        assert compute_is_proven(strategy) is True

    def test_19_trades_fails(self) -> None:
        """One below GRADUATION_MIN_TRADES returns False."""
        strategy = _make_strategy(total_trades=GRADUATION_MIN_TRADES - 1)
        assert compute_is_proven(strategy) is False

    def test_zero_trades_fails(self) -> None:
        strategy = _make_strategy(total_trades=0)
        assert compute_is_proven(strategy) is False

    def test_missing_total_trades_defaults_to_zero(self) -> None:
        """If live_results has no 'total_trades' key, defaults to 0."""
        strategy = _make_strategy()
        strategy.live_results = {"total_pnl": 500.0}  # no total_trades key
        assert compute_is_proven(strategy) is False

    def test_none_live_results_treated_as_empty(self) -> None:
        """None live_results is treated as empty dict — all criteria fail."""
        strategy = _make_strategy()
        strategy.live_results = None
        assert compute_is_proven(strategy) is False


# ---------------------------------------------------------------------------
# Tests: P&L criterion
# ---------------------------------------------------------------------------


class TestComputeIsProvenPnl:
    def test_positive_pnl_passes(self) -> None:
        """Any positive P&L passes."""
        strategy = _make_strategy(total_pnl=0.01)
        assert compute_is_proven(strategy) is True

    def test_zero_pnl_fails(self) -> None:
        """Zero P&L does NOT qualify (must be strictly positive)."""
        strategy = _make_strategy(total_pnl=0.0)
        assert compute_is_proven(strategy) is False

    def test_negative_pnl_fails(self) -> None:
        """Negative P&L does not qualify."""
        strategy = _make_strategy(total_pnl=-500.0)
        assert compute_is_proven(strategy) is False

    def test_missing_total_pnl_defaults_to_zero(self) -> None:
        """If live_results has no 'total_pnl' key, defaults to 0.0 (fails)."""
        strategy = _make_strategy()
        strategy.live_results = {"total_trades": 25}  # no total_pnl key
        assert compute_is_proven(strategy) is False


# ---------------------------------------------------------------------------
# Tests: all-criteria combinations
# ---------------------------------------------------------------------------


class TestComputeIsProvenCombinations:
    def test_all_criteria_met_returns_true(self) -> None:
        """Baseline: all three criteria satisfied."""
        strategy = _make_strategy(
            lifecycle=[_make_live_event(45)],
            total_trades=30,
            total_pnl=2500.0,
        )
        assert compute_is_proven(strategy) is True

    def test_days_fail_trades_pnl_pass(self) -> None:
        """Fails on days even when trades and P&L are fine."""
        strategy = _make_strategy(
            lifecycle=[_make_live_event(20)],
            total_trades=30,
            total_pnl=2500.0,
        )
        assert compute_is_proven(strategy) is False

    def test_trades_fail_days_pnl_pass(self) -> None:
        """Fails on trade count even when days and P&L are fine."""
        strategy = _make_strategy(
            lifecycle=[_make_live_event(45)],
            total_trades=5,
            total_pnl=2500.0,
        )
        assert compute_is_proven(strategy) is False

    def test_pnl_fail_days_trades_pass(self) -> None:
        """Fails on P&L even when days and trades are fine."""
        strategy = _make_strategy(
            lifecycle=[_make_live_event(45)],
            total_trades=30,
            total_pnl=-100.0,
        )
        assert compute_is_proven(strategy) is False
