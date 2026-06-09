"""Tests for research.data.funding_rates (causal lookup + cache).

The causal ``rate_at`` lookup is the leakage guard for any funding-conditioned
backtest, so it carries the most coverage here. Network fetch is NOT exercised
(unit-pure); only the in-memory series + the on-disk cache round-trip.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from research.data import funding_rates as fr
from research.data.funding_rates import FundingSeries

_BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _ms(dt: datetime) -> int:
    """Epoch milliseconds for a tz-aware datetime."""
    return int(dt.timestamp() * 1000)


def _series() -> FundingSeries:
    """Three 8h prints at +0h/+8h/+16h with increasing rates."""
    t0, t8, t16 = _BASE, _BASE + timedelta(hours=8), _BASE + timedelta(hours=16)
    return FundingSeries(
        symbol="BTCUSDT",
        times_ms=(_ms(t0), _ms(t8), _ms(t16)),
        rates=(0.0001, 0.0002, 0.0003),
        covered_start_ms=_ms(t0),
        covered_end_ms=_ms(t16),
    )


def test_rate_at_returns_most_recent_prior_print() -> None:
    """Between two prints, rate_at returns the EARLIER (already-known) one."""
    s = _series()
    probe = _BASE + timedelta(hours=4)  # between print 0 and print 1
    assert s.rate_at(probe) == 0.0001


def test_rate_at_exact_settlement_time_is_known() -> None:
    """At a print's exact settlement instant, that print is known (inclusive)."""
    s = _series()
    assert s.rate_at(_BASE + timedelta(hours=8)) == 0.0002


def test_rate_at_before_first_print_is_none_fail_closed() -> None:
    """Before any funding is known, rate_at returns None (caller fails closed)."""
    s = _series()
    assert s.rate_at(_BASE - timedelta(hours=1)) is None


def test_rate_at_after_last_print_holds_last() -> None:
    """After the last print, the most recent known value carries forward."""
    s = _series()
    assert s.rate_at(_BASE + timedelta(days=5)) == 0.0003


def test_rate_at_requires_timezone_aware() -> None:
    """A naive datetime is rejected (UTC discipline)."""
    s = _series()
    with pytest.raises(ValueError):
        s.rate_at(datetime(2026, 1, 1))  # noqa: DTZ001 - intentional naive


def test_cache_roundtrip(tmp_path, monkeypatch) -> None:
    """_write_cache + load_cached reproduce the series exactly."""
    monkeypatch.setattr(fr, "_CACHE_DIR", tmp_path)
    s = _series()
    fr._write_cache(s)
    loaded = fr.load_cached("BTCUSDT")
    assert loaded is not None
    assert loaded.symbol == s.symbol
    assert loaded.times_ms == s.times_ms
    assert loaded.rates == s.rates
    assert loaded.covered_start_ms == s.covered_start_ms
    assert loaded.covered_end_ms == s.covered_end_ms


def test_load_cached_absent_returns_none(tmp_path, monkeypatch) -> None:
    """A missing cache returns None (workers fail closed, never fetch)."""
    monkeypatch.setattr(fr, "_CACHE_DIR", tmp_path)
    assert fr.load_cached("NOPEUSDT") is None


def test_len_reports_print_count() -> None:
    """len(FundingSeries) is the number of prints."""
    assert len(_series()) == 3
