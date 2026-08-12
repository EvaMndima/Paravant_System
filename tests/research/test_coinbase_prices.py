"""Tests for the Coinbase price channel (H-2026-06-010).

Covers the RFC3339 formatting, the causal ``close_at`` lookup, and the disk-cache
roundtrip. Live fetch/pagination is exercised by a smoke run, not unit tests
(no network here).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from research.data import coinbase_prices as cp
from research.data.coinbase_prices import CoinbasePriceSeries

_UTC = timezone.utc


def _ms(*args: int) -> int:
    return int(datetime(*args, tzinfo=_UTC).timestamp() * 1000)


def test_iso_format() -> None:
    s = cp._iso(int(datetime(2025, 1, 2, 3, 4, 5, tzinfo=_UTC).timestamp()))
    assert s == "2025-01-02T03:04:05Z"


def test_close_at_is_causal() -> None:
    s = CoinbasePriceSeries(
        symbol="BTCUSDT",
        times_ms=(_ms(2025, 1, 1, 0), _ms(2025, 1, 1, 1), _ms(2025, 1, 1, 2)),
        closes=(100.0, 101.0, 102.0),
    )
    assert s.close_at(datetime(2024, 12, 31, tzinfo=_UTC)) is None        # before
    assert s.close_at(datetime(2025, 1, 1, 1, 30, tzinfo=_UTC)) == 101.0  # latest <= ts
    assert s.close_at(datetime(2025, 1, 1, 2, tzinfo=_UTC)) == 102.0


def test_close_at_requires_tz_aware() -> None:
    s = CoinbasePriceSeries("BTCUSDT", (_ms(2025, 1, 1, 0),), (100.0,))
    with pytest.raises(ValueError):
        s.close_at(datetime(2025, 1, 1, 1))  # naive


def test_cache_roundtrip(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cp, "_CACHE_DIR", tmp_path)
    s = CoinbasePriceSeries(
        "BTCUSDT", (_ms(2025, 1, 1, 0), _ms(2025, 1, 1, 1)), (100.0, 101.0)
    )
    cp._write_cache(s)
    loaded = cp.load_cached("BTCUSDT")
    assert loaded is not None
    assert loaded.times_ms == s.times_ms and loaded.closes == s.closes
    assert cp.load_cached("ETHUSDT") is None


def test_fetch_candles_rejects_unknown_symbol() -> None:
    with pytest.raises(ValueError):
        cp.fetch_candles("DOGEUSDT", datetime(2025, 1, 1, tzinfo=_UTC), datetime(2025, 1, 2, tzinfo=_UTC))
