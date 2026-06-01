"""Unit tests for the PARA-02 historical quarantine in validation_report.

Decision: DEC-2026-05-31-002 — a read-time filter that drops force-close trades
whose exit_price is the corrupted equity/position_value ratio (PARA-02), without
ever modifying the stored trade_log. Verifies the corruption signature is
detected surgically (no false positives on genuine trades) and that quarantined
trades are excluded from session statistics.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from scripts.validation_report import (
    PromotionDistance,
    SessionStats,
    _distance_cells,
    _is_corrupt_force_close,
    compact_text,
    compute_session_stats,
    promotion_distance,
)


def _trade(
    entry_price: float,
    exit_price: float,
    realized_pnl: float = 0.0,
    return_pct: float = 0.0,
) -> dict[str, float]:
    """Build a minimal serialized trade dict (only the fields the filter reads)."""
    return {
        "entry_price": entry_price,
        "exit_price": exit_price,
        "realized_pnl": realized_pnl,
        "return_pct": return_pct,
    }


class TestIsCorruptForceClose:
    """The PARA-02 corruption-signature predicate."""

    def test_detects_corrupted_btc_force_close(self) -> None:
        # Real BTC entry, exit booked as the ~1.x ratio -> corrupt.
        assert _is_corrupt_force_close(_trade(50000.0, 1.05)) is True

    def test_detects_corrupted_eth_force_close(self) -> None:
        assert _is_corrupt_force_close(_trade(2000.0, 2.1)) is True

    def test_keeps_clean_btc_trade(self) -> None:
        assert _is_corrupt_force_close(_trade(50000.0, 51000.0)) is False

    def test_keeps_clean_xrp_trade_in_price_band(self) -> None:
        # XRP genuinely trades near $2: entry ~ exit, ratio ~1, never flagged
        # even though exit_price falls inside the [0.5, 3.0] ratio band.
        assert _is_corrupt_force_close(_trade(2.0, 2.1)) is False

    def test_keeps_clean_doge_trade_below_band(self) -> None:
        # DOGE near $0.15: exit_price < 0.5, outside the corruption band.
        assert _is_corrupt_force_close(_trade(0.15, 0.16)) is False

    def test_ignores_missing_or_nonpositive_prices(self) -> None:
        assert _is_corrupt_force_close(_trade(0.0, 1.0)) is False
        assert _is_corrupt_force_close(_trade(50000.0, 0.0)) is False
        assert _is_corrupt_force_close({}) is False


def _session(
    trades: list[dict[str, float]], initial_capital: float = 20.0
) -> SimpleNamespace:
    """A duck-typed stand-in for a PaperTradingSession row (read-only fields)."""
    return SimpleNamespace(
        session_id="live_test_BTCUSDT",
        template_id="test_template",
        symbol="BTCUSDT",
        initial_capital=initial_capital,
        cash=initial_capital,
        started_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        trade_log=trades,
    )


class TestQuarantineInSessionStats:
    """Quarantine integration into compute_session_stats."""

    def test_corrupt_trades_excluded_from_stats(self) -> None:
        trades = [
            _trade(50000.0, 51000.0, realized_pnl=10.0, return_pct=2.0),   # clean win
            _trade(50000.0, 49000.0, realized_pnl=-5.0, return_pct=-1.0),  # clean loss
            _trade(50000.0, 1.05, realized_pnl=-19.0, return_pct=-95.0),   # PARA-02 corrupt
        ]
        stats = compute_session_stats(_session(trades))
        assert stats.total_trades == 2          # corrupt trade excluded
        assert stats.quarantined_trades == 1
        assert stats.realized_pnl == 5.0        # 10 - 5; corrupt -19 excluded
        assert stats.quarantine_flag is True    # 1/3 = 33% > 20%

    def test_no_corruption_leaves_stats_unchanged(self) -> None:
        trades = [
            _trade(50000.0, 51000.0, realized_pnl=10.0, return_pct=2.0),
            _trade(50000.0, 49000.0, realized_pnl=-5.0, return_pct=-1.0),
        ]
        stats = compute_session_stats(_session(trades))
        assert stats.total_trades == 2
        assert stats.quarantined_trades == 0
        assert stats.quarantine_flag is False

    def test_flag_false_when_below_twenty_percent(self) -> None:
        # 1 corrupt out of 6 raw = 16.7% < 20% -> dropped but not flagged.
        clean = [
            _trade(50000.0, 50500.0, realized_pnl=1.0, return_pct=0.1)
            for _ in range(5)
        ]
        trades = clean + [_trade(50000.0, 1.2, realized_pnl=-19.0, return_pct=-95.0)]
        stats = compute_session_stats(_session(trades))
        assert stats.total_trades == 5
        assert stats.quarantined_trades == 1
        assert stats.quarantine_flag is False


def _stats(
    *,
    session_id: str = "live_test_BTCUSDT",
    total_trades: int = 0,
    profit_factor: float = 0.0,
    sharpe_per_trade: float = 0.0,
    max_drawdown_pct: float = 0.0,
    classification: str = "RESEARCH",
) -> SessionStats:
    """Build a SessionStats with only the gate-relevant fields varied.

    Non-gate fields are filled with neutral placeholders so the distance
    computation (which reads only the four gate dimensions) is exercised in
    isolation.
    """
    return SessionStats(
        session_id=session_id,
        template_id="test_template",
        symbol="BTCUSDT",
        initial_capital=20.0,
        cash=20.0,
        total_trades=total_trades,
        wins=0,
        losses=0,
        win_rate_pct=0.0,
        realized_pnl=0.0,
        profit_factor=profit_factor,
        sharpe_per_trade=sharpe_per_trade,
        avg_win=0.0,
        avg_loss=0.0,
        max_drawdown_pct=max_drawdown_pct,
        days_active=0.0,
        classification=classification,
    )


class TestPromotionDistance:
    """Distance-to-promotion gap computation (DEC-2026-06-01-002)."""

    def test_research_zero_trades_needs_full_thirty(self) -> None:
        d = promotion_distance(_stats(total_trades=0))
        # N=0 -> needs the full 30 trades; PF/Sharpe 0 -> below floors.
        assert d.trades_needed == 30
        assert d.pf_deficit == 1.35
        assert d.sharpe_deficit == 1.0
        assert d.dd_overage == 0.0  # 0% DD is within the 5% ceiling
        assert d.is_ready is False

    def test_partial_progress_floors_at_zero(self) -> None:
        # N=20 (need +10), PF=1.5 (clears 1.35 -> 0), Sharpe=0.7 (need +0.30),
        # DD=7% (over the 5% ceiling by 2.0).
        d = promotion_distance(
            _stats(total_trades=20, profit_factor=1.5,
                   sharpe_per_trade=0.7, max_drawdown_pct=7.0)
        )
        assert d.trades_needed == 10
        assert d.pf_deficit == 0.0
        assert round(d.sharpe_deficit, 4) == 0.3
        assert d.dd_overage == 2.0

    def test_infinite_pf_clears_pf_dimension(self) -> None:
        # All-wins sessions have PF=+inf; that must read as a 0 deficit, never
        # poison the gap with infinity.
        d = promotion_distance(
            _stats(total_trades=30, profit_factor=float("inf"),
                   sharpe_per_trade=2.0, max_drawdown_pct=1.0)
        )
        assert d.pf_deficit == 0.0
        assert d.is_ready is True

    def test_is_ready_matches_all_zero_gaps(self) -> None:
        # Exactly meeting every threshold -> all gaps zero -> is_ready True.
        d = promotion_distance(
            _stats(total_trades=30, profit_factor=1.35,
                   sharpe_per_trade=1.0, max_drawdown_pct=5.0)
        )
        assert d == PromotionDistance(0, 0.0, 0.0, 0.0)
        assert d.is_ready is True


class TestDistanceCells:
    """ASCII status-cell rendering (project rule: no unicode glyphs)."""

    def test_ok_cells_when_satisfied(self) -> None:
        cells = _distance_cells(PromotionDistance(0, 0.0, 0.0, 0.0))
        assert cells == {"trades": "[OK]", "pf": "[OK]", "sharpe": "[OK]", "dd": "[OK]"}

    def test_waiting_and_miss_markers(self) -> None:
        cells = _distance_cells(PromotionDistance(18, 0.35, 0.30, 2.0))
        assert cells["trades"] == "[...] +18"
        assert cells["pf"] == "[MISS] +0.35"
        assert cells["sharpe"] == "[MISS] +0.30"
        assert cells["dd"] == "[MISS] -2.0%"

    def test_cells_are_ascii_only(self) -> None:
        # Guard against accidental reintroduction of unicode glyphs.
        cells = _distance_cells(PromotionDistance(5, 0.1, 0.1, 0.1))
        for value in cells.values():
            assert value.isascii()


class TestCompactTextTradeGap:
    """Compact/Telegram mode shows only the trade gap for brevity."""

    def test_includes_trade_gap_for_non_ready_sessions(self) -> None:
        sessions = [
            _stats(session_id="live_a_BTCUSDT", total_trades=12,
                   profit_factor=1.1, classification="OBSERVING"),
            _stats(session_id="live_b_ETHUSDT", total_trades=5,
                   profit_factor=1.1, classification="RESEARCH"),
        ]
        text = compact_text(sessions)
        # Closest-to-ready (fewest trades needed) listed first: a needs +18, b +25.
        assert "Trades to READY:" in text
        assert "live_a_BTCUSDT +18" in text
        assert "live_b_ETHUSDT +25" in text
        assert text.index("live_a_BTCUSDT") < text.index("live_b_ETHUSDT")

    def test_ready_sessions_excluded_from_trade_gap(self) -> None:
        sessions = [
            _stats(session_id="live_ready_BTCUSDT", total_trades=40,
                   profit_factor=2.0, sharpe_per_trade=1.5,
                   classification="READY_FOR_LIVE"),
        ]
        text = compact_text(sessions)
        assert "Trades to READY:" not in text
