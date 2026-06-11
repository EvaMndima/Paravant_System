"""Tests for the BTC reference-thrust channel (H-2026-06-011).

Covers the thrust computation (trailing return + NaN warmup), the causal
``thrust_at`` lookup (latest bar at-or-before ts; None in warmup / before start),
and the disk-cache roundtrip.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from research.data import btc_reference
from research.data.btc_reference import BtcThrustSeries
from src.data.market_data import OHLCV, OHLCVSeries

_UTC = timezone.utc
_START = datetime(2025, 1, 1, tzinfo=_UTC)


def _btc_series(n: int = 30) -> OHLCVSeries:
    """A BTC 1H series with closes 100, 101, ... (steady +1/bar)."""
    candles: list[OHLCV] = []
    for i in range(n):
        close = 100.0 + i
        prev = 100.0 + (i - 1) if i > 0 else close
        candles.append(
            OHLCV(
                timestamp=_START + timedelta(hours=i),
                open=round(prev, 2),
                high=round(max(prev, close) + 0.5, 2),
                low=round(min(prev, close) - 0.5, 2),
                close=round(close, 2),
                volume=100.0,
            )
        )
    return OHLCVSeries(candles=candles, symbol="BTCUSDT", timeframe="1h")


def test_compute_thrust_and_warmup() -> None:
    s = btc_reference.compute_thrust(_btc_series(), lookback_bars=5)
    # First 5 bars are warmup -> NaN.
    assert all(s.thrust[i] != s.thrust[i] for i in range(5))   # NaN check
    # thrust[5] = close[5]/close[0] - 1 = 105/100 - 1 = 0.05.
    assert abs(s.thrust[5] - 0.05) < 1e-9


def test_thrust_at_is_causal() -> None:
    s = btc_reference.compute_thrust(_btc_series(), lookback_bars=5)
    assert s.thrust_at(_START - timedelta(hours=1)) is None      # before series
    assert s.thrust_at(_START + timedelta(hours=2)) is None      # warmup -> NaN -> None
    val = s.thrust_at(_START + timedelta(hours=5))
    assert val is not None and abs(val - 0.05) < 1e-9


def test_thrust_at_requires_tz_aware() -> None:
    s = btc_reference.compute_thrust(_btc_series(), lookback_bars=5)
    with pytest.raises(ValueError):
        s.thrust_at(datetime(2025, 1, 1, 6))  # naive


def test_cache_roundtrip(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(btc_reference, "_CACHE_DIR", tmp_path)
    btc_reference.compute_and_cache(_btc_series(), lookback_bars=5)
    loaded = btc_reference.load_cached()
    assert loaded is not None
    assert len(loaded) == 30
    val = loaded.thrust_at(_START + timedelta(hours=5))
    assert val is not None and abs(val - 0.05) < 1e-9
