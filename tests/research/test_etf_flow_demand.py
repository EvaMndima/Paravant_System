"""Tests for the ETF-flow structural-demand generator (H-2026-06-007).

Covers the happy path (noon decision bar + positive top-percentile net inflow ->
LONG with a trailing stop) and the fail-closed branches: off the decision hour,
missing flow cache, non-positive flow, and flow below the trailing percentile.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import research.generators.etf_flow_demand as gen_mod
from research.data import etf_flows as ef_mod
from research.data.etf_flows import EtfFlowSeries
from research.generators import register_research_generators
from research.generators.etf_flow_demand import EtfFlowDemandGenerator
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import OHLCV, OHLCVSeries
from src.data.models.signal import SignalDirection

_SYMBOL = "BTCUSDT"
_UTC = timezone.utc
# Start so the final bar (index n-1) lands on 12:00 UTC: start 00:00 + 60h -> 12:00.
_START = datetime(2025, 6, 1, 0, tzinfo=_UTC)
_N = 61
_DECISION_TS = _START + timedelta(hours=_N - 1)  # 2025-06-03 12:00 UTC

_PARAMS = {
    "flow_lookback_days": 90,
    "flow_percentile_threshold": 80.0,
    "holding_days": 3,
    "atr_period": 14,
    "atr_stop_multiplier": 2.5,
}


def _series(n: int = _N) -> OHLCVSeries:
    """A gently rising 1H series whose final bar is at 12:00 UTC."""
    candles: list[OHLCV] = []
    for i in range(n):
        close = 100.0 + i * 0.2
        open_p = 100.0 + (i - 1) * 0.2 if i > 0 else close
        candles.append(
            OHLCV(
                timestamp=_START + timedelta(hours=i),
                open=round(open_p, 2),
                high=round(max(open_p, close) + 0.5, 2),
                low=round(min(open_p, close) - 0.5, 2),
                close=round(close, 2),
                volume=100.0,
            )
        )
    return OHLCVSeries(candles=candles, symbol=_SYMBOL, timeframe="1h")


def _seed_flows(current_flow: float, baseline: float, n_days: int = 40) -> None:
    """Seed the memo so the latest PUBLISHED flow at the decision bar is current_flow.

    Daily flows end the day BEFORE the decision date (so they are published by the
    noon decision bar). The last flow is ``current_flow``; the rest ``baseline``.
    """
    last_date = datetime(
        _DECISION_TS.year, _DECISION_TS.month, _DECISION_TS.day, tzinfo=_UTC
    ) - timedelta(days=1)
    dates = [
        int((last_date - timedelta(days=n_days - 1 - k)).timestamp() * 1000)
        for k in range(n_days)
    ]
    flows = [current_flow if k == n_days - 1 else baseline for k in range(n_days)]
    gen_mod._FLOWS_BY_SYMBOL[_SYMBOL] = EtfFlowSeries(
        symbol=_SYMBOL,
        dates_ms=tuple(dates),
        flows=tuple(flows),
        covered_start_ms=dates[0],
        covered_end_ms=dates[-1],
    )


@pytest.fixture(autouse=True)
def _isolate_flows(monkeypatch, tmp_path):
    """Isolate the flow memo AND the on-disk cache between tests."""
    monkeypatch.setattr(ef_mod, "_CACHE_DIR", tmp_path)
    gen_mod._FLOWS_BY_SYMBOL.clear()
    yield
    gen_mod._FLOWS_BY_SYMBOL.clear()


def test_emits_long_on_noon_large_inflow() -> None:
    """Noon bar + positive top-percentile inflow -> LONG with a trailing stop."""
    _seed_flows(current_flow=900.0, baseline=50.0)
    gen = EtfFlowDemandGenerator()
    sig = gen.generate(_series(), _PARAMS, _SYMBOL)
    assert sig is not None
    assert sig.direction is SignalDirection.LONG
    assert sig.indicators["etf_net_flow_usd_m"] == 900.0
    assert sig.stop_loss is not None and sig.stop_loss < sig.price
    assert sig.take_profit is None   # trailing stop -> ride the drift


def test_no_signal_off_decision_hour() -> None:
    """A bar that is not the noon decision bar -> no signal."""
    _seed_flows(current_flow=900.0, baseline=50.0)
    gen = EtfFlowDemandGenerator()
    # Drop the final bar so the last bar is 11:00, not 12:00.
    assert gen.generate(_series(_N - 1), _PARAMS, _SYMBOL) is None


def test_no_signal_when_cache_missing() -> None:
    gen = EtfFlowDemandGenerator()
    assert gen.generate(_series(), _PARAMS, _SYMBOL) is None


def test_no_signal_when_flow_non_positive() -> None:
    """A net OUTFLOW day -> no creation pressure -> no signal."""
    _seed_flows(current_flow=-300.0, baseline=-50.0)
    gen = EtfFlowDemandGenerator()
    assert gen.generate(_series(), _PARAMS, _SYMBOL) is None


def test_no_signal_when_flow_below_percentile() -> None:
    """A positive but ordinary inflow (below the trailing top-quintile) -> none."""
    _seed_flows(current_flow=60.0, baseline=500.0)  # window mostly large -> 60 < p80
    gen = EtfFlowDemandGenerator()
    assert gen.generate(_series(), _PARAMS, _SYMBOL) is None


def test_registry_registers_generator_idempotently() -> None:
    factory = SignalGeneratorFactory()
    assert not factory.has_generator("etf_flow_demand")
    register_research_generators(factory)
    register_research_generators(factory)  # idempotent
    assert factory.has_generator("etf_flow_demand")
    assert isinstance(
        factory.get_generator("etf_flow_demand"), EtfFlowDemandGenerator
    )
