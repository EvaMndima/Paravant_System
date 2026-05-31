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
    _is_corrupt_force_close,
    compute_session_stats,
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
