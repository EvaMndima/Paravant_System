"""Tests for the Coinbase-premium generator (H-2026-06-010).

Covers the happy path (positive top-percentile premium -> LONG with a trailing
stop) and the fail-closed branches: non-positive premium, premium below the
trailing percentile, a missing Coinbase cache, and a too-short window.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import research.generators.coinbase_premium as gen_mod
from research.data import coinbase_prices as cp_mod
from research.data.coinbase_prices import CoinbasePriceSeries
from research.generators import register_research_generators
from research.generators.coinbase_premium import CoinbasePremiumGenerator
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import OHLCV, OHLCVSeries
from src.data.models.signal import SignalDirection

_SYMBOL = "BTCUSDT"
_UTC = timezone.utc
_START = datetime(2025, 6, 1, tzinfo=_UTC)
_N = 80

_PARAMS = {
    "premium_lookback_days": 3,   # 72 bars window (< N)
    "premium_percentile_threshold": 80.0,
    "atr_period": 14,
    "atr_stop_multiplier": 2.5,
}


def _binance_series(n: int = _N, base: float = 100.0) -> OHLCVSeries:
    """A flat-ish Binance series at ``base`` (premium is driven by Coinbase)."""
    candles: list[OHLCV] = []
    for i in range(n):
        candles.append(
            OHLCV(
                timestamp=_START + timedelta(hours=i),
                open=base, high=base + 0.5, low=base - 0.5, close=base, volume=100.0,
            )
        )
    return OHLCVSeries(candles=candles, symbol=_SYMBOL, timeframe="1h")


def _seed_coinbase(closes: list[float], n: int = _N) -> None:
    """Seed the memo with a Coinbase series aligned to the Binance bar times."""
    times = tuple(int((_START + timedelta(hours=i)).timestamp() * 1000) for i in range(n))
    gen_mod._COINBASE_BY_SYMBOL[_SYMBOL] = CoinbasePriceSeries(
        symbol=_SYMBOL, times_ms=times, closes=tuple(closes)
    )


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(cp_mod, "_CACHE_DIR", tmp_path)
    gen_mod._COINBASE_BY_SYMBOL.clear()
    yield
    gen_mod._COINBASE_BY_SYMBOL.clear()


def test_emits_long_on_positive_top_percentile_premium() -> None:
    """Window mostly at parity, current bar elevated -> LONG, trailing stop."""
    closes = [100.0] * (_N - 1) + [101.0]   # last bar: +1% Coinbase premium
    _seed_coinbase(closes)
    gen = CoinbasePremiumGenerator()
    sig = gen.generate(_binance_series(), _PARAMS, _SYMBOL)
    assert sig is not None
    assert sig.direction is SignalDirection.LONG
    assert sig.indicators["coinbase_premium"] > 0
    assert sig.stop_loss is not None and sig.stop_loss < sig.price
    assert sig.take_profit is None


def test_no_signal_when_premium_non_positive() -> None:
    """Coinbase below Binance (discount) -> no signal."""
    _seed_coinbase([100.0] * (_N - 1) + [99.0])
    gen = CoinbasePremiumGenerator()
    assert gen.generate(_binance_series(), _PARAMS, _SYMBOL) is None


def test_no_signal_when_premium_below_percentile() -> None:
    """Window mostly high premium, current small positive -> below p80 -> no signal."""
    _seed_coinbase([105.0] * (_N - 1) + [100.5])   # window ~5%, current 0.5%
    gen = CoinbasePremiumGenerator()
    assert gen.generate(_binance_series(), _PARAMS, _SYMBOL) is None


def test_no_signal_when_cache_missing() -> None:
    gen = CoinbasePremiumGenerator()
    assert gen.generate(_binance_series(), _PARAMS, _SYMBOL) is None


def test_no_signal_when_window_too_short() -> None:
    """Fewer bars than the lookback window -> no signal."""
    _seed_coinbase([100.0] * 60 + [101.0] * 0 + [101.0], n=61)
    gen = CoinbasePremiumGenerator()
    assert gen.generate(_binance_series(n=61), _PARAMS, _SYMBOL) is None


def test_registry_registers_generator_idempotently() -> None:
    factory = SignalGeneratorFactory()
    assert not factory.has_generator("coinbase_premium")
    register_research_generators(factory)
    register_research_generators(factory)  # idempotent
    assert factory.has_generator("coinbase_premium")
    assert isinstance(factory.get_generator("coinbase_premium"), CoinbasePremiumGenerator)
