"""Tests for the funding-extreme contrarian v2 generator (H-2026-06-006).

Covers the happy path (positive funding in the top decile of its trailing window
+ a downside Donchian break -> SHORT) and the fail-closed branches that matter:
missing funding cache, funding below the percentile threshold, non-positive
funding, a too-thin percentile window, and the absence of a downside break. A
deterministic synthetic series breaks below its prior-N-bar lows on the final bar.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import research.generators.funding_extreme_contrarian_v2 as gen_mod
from research.data import funding_rates as fr_mod
from research.data.funding_rates import FundingSeries
from research.generators import register_research_generators
from research.generators.funding_extreme_contrarian_v2 import (
    FundingExtremeContrarianV2Generator,
)
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import OHLCV, OHLCVSeries
from src.data.models.signal import SignalDirection

_SYMBOL = "BTCUSDT"
_START = datetime(2026, 1, 1, tzinfo=timezone.utc)
_N_BARS = 140
_DECISION_TS = _START + timedelta(hours=_N_BARS - 1)

_PARAMS = {
    "funding_percentile_lookback_days": 90,
    "funding_percentile_threshold": 90.0,
    "breakout_lookback": 20,
    "atr_period": 14,
    "atr_stop_multiplier": 2.0,
    "risk_reward_ratio": 2.0,
}


def _uptrend_with_final_breakdown() -> OHLCVSeries:
    """Slow uptrend then a sharp final-bar drop below the prior-20-bar lows."""
    closes = [100.0 + i * 0.1 for i in range(_N_BARS)]
    closes[-1] = 90.0  # break well below the prior ~20 lows (~111)
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
    return OHLCVSeries(candles=candles, symbol=_SYMBOL, timeframe="1h")


def _no_breakdown_uptrend() -> OHLCVSeries:
    """Steady uptrend with no final breakdown (Donchian break never fires)."""
    closes = [100.0 + i * 0.1 for i in range(_N_BARS)]
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
    return OHLCVSeries(candles=candles, symbol=_SYMBOL, timeframe="1h")


def _seed_funding_window(
    current_rate: float, baseline_rate: float, n_prints: int = 200
) -> None:
    """Seed the memo with an 8h funding window ending at the decision bar.

    The last print (at the decision timestamp) carries ``current_rate``; all
    earlier prints carry ``baseline_rate``. With n_prints*8h < 90 days the whole
    series is the percentile window.
    """
    end_ms = int(_DECISION_TS.timestamp() * 1000)
    step_ms = 8 * 3600 * 1000
    times = tuple(end_ms - (n_prints - 1 - k) * step_ms for k in range(n_prints))
    rates = tuple(
        current_rate if k == n_prints - 1 else baseline_rate for k in range(n_prints)
    )
    gen_mod._FUNDING_BY_SYMBOL[_SYMBOL] = FundingSeries(
        symbol=_SYMBOL,
        times_ms=times,
        rates=rates,
        covered_start_ms=times[0],
        covered_end_ms=times[-1],
    )


@pytest.fixture(autouse=True)
def _isolate_funding(monkeypatch, tmp_path):
    """Isolate the funding memo AND the on-disk cache between tests."""
    monkeypatch.setattr(fr_mod, "_CACHE_DIR", tmp_path)
    gen_mod._FUNDING_BY_SYMBOL.clear()
    yield
    gen_mod._FUNDING_BY_SYMBOL.clear()


def test_emits_short_when_funding_top_decile_and_breakdown() -> None:
    """Positive top-decile funding + downside break -> a SHORT signal."""
    _seed_funding_window(current_rate=0.001, baseline_rate=0.0001)
    gen = FundingExtremeContrarianV2Generator()
    sig = gen.generate(_uptrend_with_final_breakdown(), _PARAMS, _SYMBOL)
    assert sig is not None
    assert sig.direction is SignalDirection.SHORT
    assert sig.indicators["funding_rate_8h"] == 0.001
    assert sig.stop_loss is not None and sig.stop_loss > sig.price
    assert sig.take_profit is not None and sig.take_profit < sig.price


def test_no_signal_when_funding_cache_missing() -> None:
    """No funding known (cache absent) -> fail closed."""
    gen = FundingExtremeContrarianV2Generator()
    assert gen.generate(_uptrend_with_final_breakdown(), _PARAMS, _SYMBOL) is None


def test_no_signal_when_funding_below_percentile() -> None:
    """Current funding below the trailing top-decile -> not extreme -> no signal."""
    # Window mostly high, current low -> current < 90th percentile.
    _seed_funding_window(current_rate=0.0001, baseline_rate=0.001)
    gen = FundingExtremeContrarianV2Generator()
    assert gen.generate(_uptrend_with_final_breakdown(), _PARAMS, _SYMBOL) is None


def test_no_signal_when_funding_non_positive() -> None:
    """Non-positive current funding -> no euphoric longs to fade -> no signal."""
    _seed_funding_window(current_rate=-0.0001, baseline_rate=-0.001)
    gen = FundingExtremeContrarianV2Generator()
    assert gen.generate(_uptrend_with_final_breakdown(), _PARAMS, _SYMBOL) is None


def test_no_signal_when_window_too_thin() -> None:
    """Fewer than the minimum prints to rank -> fail closed."""
    _seed_funding_window(current_rate=0.001, baseline_rate=0.0001, n_prints=5)
    gen = FundingExtremeContrarianV2Generator()
    assert gen.generate(_uptrend_with_final_breakdown(), _PARAMS, _SYMBOL) is None


def test_no_signal_without_downside_break() -> None:
    """Extreme funding but no Donchian breakdown -> no signal."""
    _seed_funding_window(current_rate=0.001, baseline_rate=0.0001)
    gen = FundingExtremeContrarianV2Generator()
    assert gen.generate(_no_breakdown_uptrend(), _PARAMS, _SYMBOL) is None


def test_registry_registers_generator_idempotently() -> None:
    """register_research_generators wires the template into a fresh factory."""
    factory = SignalGeneratorFactory()
    assert not factory.has_generator("funding_extreme_contrarian_v2")
    register_research_generators(factory)
    register_research_generators(factory)  # idempotent: no raise
    assert factory.has_generator("funding_extreme_contrarian_v2")
    assert isinstance(
        factory.get_generator("funding_extreme_contrarian_v2"),
        FundingExtremeContrarianV2Generator,
    )
