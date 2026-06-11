"""Tests for the funding-extreme contrarian generator (H-2026-06-005).

Covers the happy path (SHORT when funding is above the extreme cap + price still
above the trend EMA + a fast-EMA cross-DOWN on the decision bar) and the
fail-closed branches that matter most: missing funding cache, funding at/below
the extreme cap (not euphoric), and a downtrend (no over-extended top to fade).
A deterministic synthetic series is engineered to produce a fast-EMA cross-down
on the final bar while price remains above EMA(100).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import research.generators.funding_extreme_contrarian as gen_mod
from research.data import funding_rates as fr_mod
from research.data.funding_rates import FundingSeries
from research.generators import register_research_generators
from research.generators.funding_extreme_contrarian import (
    FundingExtremeContrarianGenerator,
)
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import OHLCV, OHLCVSeries
from src.data.models.signal import SignalDirection

_SYMBOL = "BTCUSDT"
_START = datetime(2026, 1, 1, tzinfo=timezone.utc)

_PARAMS = {
    "trend_ema_period": 100,
    "fast_ema_period": 20,
    "funding_extreme_threshold_pct_per_8h": 0.05,  # -> cap rate 0.0005
    "atr_period": 14,
    "atr_stop_multiplier": 2.0,
    "risk_reward_ratio": 2.0,
}


def _uptrend_with_final_crossdown(n: int = 140) -> OHLCVSeries:
    """Steady +1/bar uptrend with a 1-bar spike above fast EMA then a drop below.

    The penultimate bar spikes sharply above the (lagging) EMA(20); the final bar
    drops below it -- a deterministic fast-EMA cross-DOWN on the decision bar --
    while the final close stays above EMA(100) (the still-extended top context).
    """
    closes = [100.0 + i for i in range(n)]
    closes[-2] = closes[-3] + 16.0  # sharp spike above EMA20
    closes[-1] = closes[-3] - 16.0  # drop below EMA20 (the cross-down), still > EMA100

    candles: list[OHLCV] = []
    for i, close in enumerate(closes):
        open_p = closes[i - 1] if i > 0 else close
        high = max(open_p, close) + 0.5
        low = min(open_p, close) - 0.5
        candles.append(
            OHLCV(
                timestamp=_START + timedelta(hours=i),
                open=round(open_p, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=100.0,
            )
        )
    return OHLCVSeries(candles=candles, symbol=_SYMBOL, timeframe="1h")


def _seed_funding(rate: float, *, symbol: str = _SYMBOL) -> None:
    """Seed the generator's per-process funding memo with a single print."""
    gen_mod._FUNDING_BY_SYMBOL[symbol] = FundingSeries(
        symbol=symbol,
        times_ms=(int(_START.timestamp() * 1000),),
        rates=(rate,),
        covered_start_ms=int(_START.timestamp() * 1000),
        covered_end_ms=int((_START + timedelta(days=30)).timestamp() * 1000),
    )


@pytest.fixture(autouse=True)
def _isolate_funding(monkeypatch, tmp_path):
    """Isolate the funding memo AND the on-disk cache between tests.

    Pointing the cache dir at an empty tmp path ensures a test that does NOT seed
    the memo sees genuinely-missing funding (load_cached -> None), independent of
    any real cache written by smoke runs or a live screen on this machine.
    """
    monkeypatch.setattr(fr_mod, "_CACHE_DIR", tmp_path)
    gen_mod._FUNDING_BY_SYMBOL.clear()
    yield
    gen_mod._FUNDING_BY_SYMBOL.clear()


def test_emits_short_when_funding_extreme_and_crossdown() -> None:
    """Funding above the extreme cap + still-extended + cross-down -> a SHORT."""
    _seed_funding(0.001)  # 0.1% per 8h, strictly above cap 0.0005
    gen = FundingExtremeContrarianGenerator()
    sig = gen.generate(_uptrend_with_final_crossdown(), _PARAMS, _SYMBOL)
    assert sig is not None
    assert sig.direction is SignalDirection.SHORT
    assert sig.indicators["funding_rate_8h"] == 0.001
    # SHORT framing: stop above entry, target below entry.
    assert sig.stop_loss is not None and sig.stop_loss > sig.price
    assert sig.take_profit is not None and sig.take_profit < sig.price


def test_no_signal_when_funding_cache_missing() -> None:
    """No funding known (cache absent) -> fail closed, no signal."""
    # memo cleared by fixture; load_cached will return None for the symbol
    gen = FundingExtremeContrarianGenerator()
    sig = gen.generate(_uptrend_with_final_crossdown(), _PARAMS, _SYMBOL)
    assert sig is None


def test_no_signal_when_funding_at_or_below_cap() -> None:
    """Funding at/below the extreme cap is not euphoric -> no fade."""
    _seed_funding(0.0005)  # exactly the cap -> NOT strictly above -> no signal
    gen = FundingExtremeContrarianGenerator()
    assert gen.generate(_uptrend_with_final_crossdown(), _PARAMS, _SYMBOL) is None


def test_no_signal_when_funding_moderate() -> None:
    """Moderate positive funding (H-003's band) -> no contrarian fade."""
    _seed_funding(0.0001)  # 0.01% per 8h, well below the extreme cap
    gen = FundingExtremeContrarianGenerator()
    assert gen.generate(_uptrend_with_final_crossdown(), _PARAMS, _SYMBOL) is None


def test_no_signal_in_downtrend_even_with_extreme_funding() -> None:
    """A falling market (close below EMA100) fails the still-extended filter."""
    _seed_funding(0.001)
    n = 140
    closes = [240.0 - i for i in range(n)]  # steady downtrend
    candles: list[OHLCV] = []
    for i, close in enumerate(closes):
        open_p = closes[i - 1] if i > 0 else close
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
    series = OHLCVSeries(candles=candles, symbol=_SYMBOL, timeframe="1h")
    gen = FundingExtremeContrarianGenerator()
    assert gen.generate(series, _PARAMS, _SYMBOL) is None


def test_registry_registers_generator_idempotently() -> None:
    """register_research_generators wires the template into a fresh factory."""
    factory = SignalGeneratorFactory()
    assert not factory.has_generator("funding_extreme_contrarian")
    register_research_generators(factory)
    register_research_generators(factory)  # idempotent: no raise
    assert factory.has_generator("funding_extreme_contrarian")
    assert isinstance(
        factory.get_generator("funding_extreme_contrarian"),
        FundingExtremeContrarianGenerator,
    )
