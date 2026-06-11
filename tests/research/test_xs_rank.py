"""Tests for the cross-symbol relative-strength rank panel (H-2026-06-008).

Covers the rank computation (strongest trailing return -> top-k), the causal
``in_top_k_at`` lookup (membership at the latest bar at-or-before ts; None before
the panel), and the disk-cache roundtrip.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from research.data import xs_rank
from research.data.xs_rank import RankSeries
from src.data.market_data import OHLCV, OHLCVSeries

_UTC = timezone.utc
_START = datetime(2025, 1, 1, tzinfo=_UTC)


def _make_series(symbol: str, factor: float, n: int = 20) -> OHLCVSeries:
    """A 1H series whose close compounds by ``factor`` each bar (>1 rises)."""
    candles: list[OHLCV] = []
    close = 100.0
    for i in range(n):
        prev = close
        close = 100.0 * (factor ** i)
        candles.append(
            OHLCV(
                timestamp=_START + timedelta(hours=i),
                open=round(prev, 4),
                high=round(max(prev, close) + 0.5, 4),
                low=round(min(prev, close) - 0.5, 4),
                close=round(close, 4),
                volume=100.0,
            )
        )
    return OHLCVSeries(candles=candles, symbol=symbol, timeframe="1h")


def test_compute_panel_ranks_strongest_into_top_k() -> None:
    """Rising symbol is top-k; falling symbol is not (top 2 of 3)."""
    panel = xs_rank.compute_panel(
        {
            "AAA": _make_series("AAA", 1.01),   # rising
            "BBB": _make_series("BBB", 1.0),    # flat
            "CCC": _make_series("CCC", 0.99),   # falling
        },
        rs_lookback_bars=5,
        top_k_fraction=0.34,   # ceil(0.34*3) = 2 -> top two
    )
    last = _START + timedelta(hours=19)
    assert panel["AAA"].in_top_k_at(last) is True   # strongest
    assert panel["BBB"].in_top_k_at(last) is True   # second
    assert panel["CCC"].in_top_k_at(last) is False  # weakest -> excluded


def test_in_top_k_at_is_causal() -> None:
    """No membership before lookback is met; None before the panel starts."""
    panel = xs_rank.compute_panel(
        {"AAA": _make_series("AAA", 1.01), "CCC": _make_series("CCC", 0.99)},
        rs_lookback_bars=5,
        top_k_fraction=0.5,   # ceil(0.5*2)=1 -> only the strongest
    )
    aaa = panel["AAA"]
    # Before the panel's first bar -> unknown.
    assert aaa.in_top_k_at(_START - timedelta(hours=1)) is None
    # Within the first lookback bars membership is False (rank undefined).
    assert aaa.in_top_k_at(_START + timedelta(hours=2)) is False
    # Later, the strongest symbol is the sole top-1.
    assert aaa.in_top_k_at(_START + timedelta(hours=19)) is True


def test_in_top_k_at_requires_tz_aware() -> None:
    rs = RankSeries("AAA", times_ms=(0,), in_top_k=(True,))
    with pytest.raises(ValueError):
        rs.in_top_k_at(datetime(2025, 1, 1))  # naive


def test_cache_roundtrip(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(xs_rank, "_CACHE_DIR", tmp_path)
    panel = xs_rank.compute_panel(
        {"AAA": _make_series("AAA", 1.01), "CCC": _make_series("CCC", 0.99)},
        rs_lookback_bars=5,
        top_k_fraction=0.5,
    )
    for rs in panel.values():
        xs_rank._write_cache(rs)
    loaded = xs_rank.load_cached("AAA")
    assert loaded is not None
    assert loaded.times_ms == panel["AAA"].times_ms
    assert loaded.in_top_k == panel["AAA"].in_top_k
    assert xs_rank.load_cached("ZZZ") is None
