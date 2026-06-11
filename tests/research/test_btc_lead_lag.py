"""Tests for the BTC-led lead-lag generator (H-2026-06-011).

Covers the happy path (BTC thrust above threshold + alt lagging -> LONG with a
trailing stop) and the fail-closed branches: BTC thrust below threshold, alt
already caught up, and a missing BTC-thrust cache.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import research.generators.btc_lead_lag as gen_mod
from research.data import btc_reference as btc_mod
from research.data.btc_reference import BtcThrustSeries
from research.generators import register_research_generators
from research.generators.btc_lead_lag import BtcLeadLagGenerator
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import OHLCV, OHLCVSeries
from src.data.models.signal import SignalDirection

_SYMBOL = "ADAUSDT"
_UTC = timezone.utc
_START = datetime(2025, 6, 1, tzinfo=_UTC)
_N = 60
_DECISION_TS = _START + timedelta(hours=_N - 1)

_PARAMS = {
    "btc_thrust_lookback_bars": 24,
    "btc_thrust_threshold_pct": 2.0,   # 0.02
    "alt_lag_window_bars": 6,
    "atr_period": 14,
    "atr_stop_multiplier": 2.5,
}


def _alt_series(slope: float = 0.1) -> OHLCVSeries:
    """A rising alt 1H series; ``slope`` per bar sets the alt's trailing return."""
    candles: list[OHLCV] = []
    for i in range(_N):
        close = 100.0 + i * slope
        prev = 100.0 + (i - 1) * slope if i > 0 else close
        candles.append(
            OHLCV(
                timestamp=_START + timedelta(hours=i),
                open=round(prev, 4),
                high=round(max(prev, close) + 0.2, 4),
                low=round(min(prev, close) - 0.2, 4),
                close=round(close, 4),
                volume=100.0,
            )
        )
    return OHLCVSeries(candles=candles, symbol=_SYMBOL, timeframe="1h")


def _seed_btc_thrust(value: float) -> None:
    """Seed the memo with a BTC thrust series whose value at the decision ts is ``value``."""
    last_ms = int(_DECISION_TS.timestamp() * 1000)
    times = tuple(last_ms - (5 - k) * 3_600_000 for k in range(6))
    thrust = tuple(value for _ in range(6))
    gen_mod._BTC_THRUST[:] = [BtcThrustSeries(times_ms=times, thrust=thrust)]


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(btc_mod, "_CACHE_DIR", tmp_path)
    gen_mod._BTC_THRUST.clear()
    yield
    gen_mod._BTC_THRUST.clear()


def test_emits_long_when_btc_thrust_and_alt_lagging() -> None:
    """BTC thrust 5% (>2% threshold) + alt lagging (~2.2%) -> LONG, trailing stop."""
    _seed_btc_thrust(0.05)
    gen = BtcLeadLagGenerator()
    sig = gen.generate(_alt_series(slope=0.1), _PARAMS, _SYMBOL)
    assert sig is not None
    assert sig.direction is SignalDirection.LONG
    assert sig.indicators["btc_thrust"] == 0.05
    assert sig.stop_loss is not None and sig.stop_loss < sig.price
    assert sig.take_profit is None   # trailing stop


def test_no_signal_when_btc_below_threshold() -> None:
    """BTC thrust 1% (< 2% threshold) -> no BTC up-move -> no signal."""
    _seed_btc_thrust(0.01)
    gen = BtcLeadLagGenerator()
    assert gen.generate(_alt_series(slope=0.1), _PARAMS, _SYMBOL) is None


def test_no_signal_when_alt_already_caught_up() -> None:
    """BTC thrust 4% (>= threshold) but alt up ~6.7% (already ahead) -> no signal."""
    _seed_btc_thrust(0.04)
    gen = BtcLeadLagGenerator()
    assert gen.generate(_alt_series(slope=0.3), _PARAMS, _SYMBOL) is None


def test_no_signal_when_btc_cache_missing() -> None:
    gen = BtcLeadLagGenerator()
    assert gen.generate(_alt_series(slope=0.1), _PARAMS, _SYMBOL) is None


def test_registry_registers_generator_idempotently() -> None:
    factory = SignalGeneratorFactory()
    assert not factory.has_generator("btc_lead_lag")
    register_research_generators(factory)
    register_research_generators(factory)  # idempotent
    assert factory.has_generator("btc_lead_lag")
    assert isinstance(factory.get_generator("btc_lead_lag"), BtcLeadLagGenerator)
