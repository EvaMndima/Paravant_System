"""Unit tests for the live auto-promotion gate classifier.

Decision: DEC-2026-06-01-001. `_paper_strategy_classification` reuses the
canonical validation-report promotion-gate logic (DEC-2026-05-27-004) to decide
whether a strategy template's pooled live-paper performance is READY_FOR_LIVE.
These tests cover all four classification states, the fail-open-on-DB-error
contract, and that PARA-02-corrupted trades are quarantined before classifying.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from scripts.run_live_trading import (
    _paper_strategy_classification,
    _tier1_activation_blocked,
)


def _trade(
    pnl: float,
    ret: float,
    entry: float = 50000.0,
    exit_: float = 51000.0,
) -> dict[str, float]:
    """Build a serialized trade dict (only the fields the classifier reads)."""
    return {
        "entry_price": entry,
        "exit_price": exit_,
        "realized_pnl": pnl,
        "return_pct": ret,
    }


def _session(trades: list[dict[str, float]], initial_capital: float = 20.0) -> SimpleNamespace:
    """A duck-typed stand-in for a PaperTradingSession row."""
    return SimpleNamespace(initial_capital=initial_capital, trade_log=trades)


def _patch_db(rows: list[SimpleNamespace]):
    """Patch src.data.database.get_db to yield a db whose query returns rows."""
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = rows
    cm = MagicMock()
    cm.__enter__.return_value = db
    cm.__exit__.return_value = False
    return patch("src.data.database.get_db", return_value=cm)


class TestPaperStrategyClassification:
    """All four promotion-gate classification states."""

    def test_research_when_no_trades(self) -> None:
        # The exact gap the gate closes: a brand-new strategy with N=0.
        with _patch_db([_session([])]):
            classification, db_ok = _paper_strategy_classification("brand_new")
        assert (classification, db_ok) == ("RESEARCH", True)

    def test_observing_when_modest_sample_and_profitable(self) -> None:
        # N=10 (>=10, <30) AND PF>=1.0 -> OBSERVING (not yet READY).
        trades = [_trade(10.0, 1.0) for _ in range(6)] + [_trade(-5.0, -0.5) for _ in range(4)]
        with _patch_db([_session(trades)]):
            classification, db_ok = _paper_strategy_classification("observing_strat")
        assert (classification, db_ok) == ("OBSERVING", True)

    def test_degraded_when_losing(self) -> None:
        # N=10 AND PF<0.8 -> DEGRADED.
        trades = [_trade(10.0, 1.0) for _ in range(3)] + [_trade(-10.0, -1.0) for _ in range(7)]
        with _patch_db([_session(trades)]):
            classification, db_ok = _paper_strategy_classification("degraded_strat")
        assert (classification, db_ok) == ("DEGRADED", True)

    def test_ready_for_live_when_gate_cleared(self) -> None:
        # N=30, all wins (PF=inf, MaxDD=0), varied returns so per-trade
        # Sharpe is well above 1.0 -> READY_FOR_LIVE.
        trades = [_trade(10.0, 1.5 if i % 2 == 0 else 2.5) for i in range(30)]
        with _patch_db([_session(trades)]):
            classification, db_ok = _paper_strategy_classification("ready_strat")
        assert (classification, db_ok) == ("READY_FOR_LIVE", True)

    def test_pools_trades_across_multiple_sessions(self) -> None:
        # Two sessions of the same template pool to N=30 -> READY.
        s1 = _session([_trade(10.0, 1.5 if i % 2 == 0 else 2.5) for i in range(15)])
        s2 = _session([_trade(10.0, 1.5 if i % 2 == 0 else 2.5) for i in range(15)])
        with _patch_db([s1, s2]):
            classification, db_ok = _paper_strategy_classification("pooled_strat")
        assert (classification, db_ok) == ("READY_FOR_LIVE", True)


class TestFailOpenOnDbError:
    """A DB read failure must fail OPEN (db_ok False), not block restarts."""

    def test_db_error_returns_db_ok_false(self) -> None:
        with patch("src.data.database.get_db", side_effect=Exception("db down")):
            classification, db_ok = _paper_strategy_classification("any")
        assert db_ok is False
        # Classification value is a safe placeholder the caller ignores.
        assert classification == "RESEARCH"


class TestQuarantineApplied:
    """PARA-02-corrupted force-closes must be excluded before classifying."""

    def test_corrupt_trades_do_not_drag_classification(self) -> None:
        # 30 genuine wins would be READY. Add 10 corrupted force-closes
        # (exit_price ~1.x, huge loss) that — if NOT quarantined — would pull
        # PF below 0.8 and make it DEGRADED. Quarantine must keep it READY.
        good = [_trade(10.0, 1.5 if i % 2 == 0 else 2.5) for i in range(30)]
        corrupt = [_trade(-50.0, -95.0, entry=50000.0, exit_=1.05) for _ in range(10)]
        with _patch_db([_session(good + corrupt)]):
            classification, db_ok = _paper_strategy_classification("with_corruption")
        assert (classification, db_ok) == ("READY_FOR_LIVE", True)


class TestTier1ActivationGate:
    """The tier-1 auto-promotion gate (DEC-2026-06-01-002).

    Tier 1 was exempt from the gate under DEC-2026-06-01-001; this closes that
    gap so the READY_FOR_LIVE requirement is uniform across every live tier.
    ``_tier1_activation_blocked`` delegates to the already-tested classifier,
    so these tests verify only the block/allow/fail-open decision wrapping it.
    """

    def test_blocked_when_not_ready(self) -> None:
        # The blocked path: a maturing OBSERVING strategy (N=10, PF>=1.0 but
        # not yet READY) must NOT auto-start tier 1.
        trades = [_trade(10.0, 1.0) for _ in range(6)] + [_trade(-5.0, -0.5) for _ in range(4)]
        with _patch_db([_session(trades)]):
            blocked, reason = _tier1_activation_blocked("observing_strat")
        assert blocked is True
        assert "OBSERVING" in reason
        assert "not READY_FOR_LIVE" in reason

    def test_blocked_when_research_zero_trades(self) -> None:
        # The exact gap the gate closes for the primary tier: a brand-new
        # strategy with N=0 classifies RESEARCH and must be blocked.
        with _patch_db([_session([])]):
            blocked, reason = _tier1_activation_blocked("brand_new")
        assert blocked is True
        assert "RESEARCH" in reason

    def test_allowed_when_ready(self) -> None:
        # The tier-1-activates path still works: a READY_FOR_LIVE template is
        # not blocked, so main() flips tier1.active = True as before.
        trades = [_trade(10.0, 1.5 if i % 2 == 0 else 2.5) for i in range(30)]
        with _patch_db([_session(trades)]):
            blocked, reason = _tier1_activation_blocked("ready_strat")
        assert blocked is False
        assert reason == ""

    def test_fail_open_on_db_error(self) -> None:
        # A transient DB outage must NOT block tier 1 (fail-open), mirroring
        # the demotion guardrail — an inactive tier 1 leaves any open position
        # unmanaged, so a restart must not be blocked on a DB read failure.
        with patch("src.data.database.get_db", side_effect=Exception("db down")):
            blocked, reason = _tier1_activation_blocked("any")
        assert blocked is False
        assert reason == ""
