"""Tests for the US-spot-ETF net-flow research channel (H-2026-06-007).

Covers the Farside HTML parse (number formats + data-table selection), the
causal ``net_flow_at`` publication lag (a day-D flow is not visible until D+1),
the trailing ``window_flows`` accessor, and the disk-cache roundtrip. No network:
the parse is tested against a small inline HTML fixture and series are built by hand.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from research.data import etf_flows as ef
from research.data.etf_flows import EtfFlowSeries

_UTC = timezone.utc


def _ms(y: int, m: int, d: int) -> int:
    return int(datetime(y, m, d, tzinfo=_UTC).timestamp() * 1000)


_FIXTURE_HTML = """
<html><body>
<table><tr><td>Fund</td><td>About</td></tr></table>
<table>
  <tr><th>Date</th><th>IBIT</th><th>Total</th></tr>
  <tr><td>11 Jan 2024</td><td>1,000.0</td><td>655.3</td></tr>
  <tr><td>12 Jan 2024</td><td>(5.0)</td><td>(12.4)</td></tr>
  <tr><td>13 Jan 2024</td><td>-</td><td>-</td></tr>
  <tr><td>Total</td><td>x</td><td>9999.0</td></tr>
</table>
</body></html>
"""


def test_parse_number_formats() -> None:
    assert ef._parse_number("1,234.5") == 1234.5
    assert ef._parse_number("(123.4)") == -123.4
    assert ef._parse_number("-7.0") == -7.0
    assert ef._parse_number("-") is None
    assert ef._parse_number("") is None


def test_parse_farside_table_selects_data_and_uses_total() -> None:
    """Picks the data table (not nav), reads the LAST cell, skips dash/non-date."""
    pairs = ef._parse_farside_table(_FIXTURE_HTML)
    assert len(pairs) == 2                       # 13 Jan (dash) + Total row skipped
    assert pairs[0] == (_ms(2024, 1, 11), 655.3)
    assert pairs[1] == (_ms(2024, 1, 12), -12.4)  # parenthesised negative


def _series(dates: list[int], flows: list[float]) -> EtfFlowSeries:
    return EtfFlowSeries(
        symbol="BTCUSDT",
        dates_ms=tuple(dates),
        flows=tuple(flows),
        covered_start_ms=dates[0],
        covered_end_ms=dates[-1],
    )


def test_net_flow_at_is_causal_t_plus_1() -> None:
    """A day-D flow is invisible until D+1 (conservative publication lag)."""
    s = _series([_ms(2025, 1, 1), _ms(2025, 1, 2)], [100.0, 200.0])
    # On Jan 1 noon nothing is published yet.
    assert s.net_flow_at(datetime(2025, 1, 1, 12, tzinfo=_UTC)) is None
    # On Jan 2 noon, only Jan 1's flow is known (NOT Jan 2's).
    assert s.net_flow_at(datetime(2025, 1, 2, 12, tzinfo=_UTC)) == 100.0
    # On Jan 3 noon, Jan 2's flow is now published.
    assert s.net_flow_at(datetime(2025, 1, 3, 12, tzinfo=_UTC)) == 200.0


def test_window_flows_respects_lookback_and_publication() -> None:
    s = _series(
        [_ms(2025, 1, 1), _ms(2025, 1, 2), _ms(2025, 1, 3)],
        [10.0, 20.0, 30.0],
    )
    # At Jan 4 noon all three are published; a shorter lookback drops the oldest.
    at = datetime(2025, 1, 4, 12, tzinfo=_UTC)
    assert s.window_flows(at, 90) == [10.0, 20.0, 30.0]
    # lookback=3 -> cutoff Jan 1 12:00, so Jan 2-3 remain (Jan 1 falls just outside).
    assert s.window_flows(at, 3) == [20.0, 30.0]


def test_net_flow_at_requires_tz_aware() -> None:
    s = _series([_ms(2025, 1, 1)], [100.0])
    with pytest.raises(ValueError):
        s.net_flow_at(datetime(2025, 1, 2, 12))  # naive


def test_cache_roundtrip(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ef, "_CACHE_DIR", tmp_path)
    s = _series([_ms(2025, 1, 1), _ms(2025, 1, 2)], [100.0, 200.0])
    ef._write_cache(s)
    loaded = ef.load_cached("BTCUSDT")
    assert loaded is not None
    assert loaded.dates_ms == s.dates_ms
    assert loaded.flows == s.flows
    assert ef.load_cached("ETHUSDT") is None  # absent
