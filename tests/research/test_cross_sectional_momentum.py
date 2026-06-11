"""Tests for the cross-sectional momentum generator (H-2026-06-008).

Covers the happy path (rebalance-grid bar + top-k membership -> LONG with a
trailing stop) and the fail-closed branches: off the rebalance grid, not in the
top-k, and a missing rank-panel cache.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import research.generators.cross_sectional_momentum as gen_mod
from research.data import xs_rank as xs_mod
from research.data.xs_rank import RankSeries
from research.generators import register_research_generators
from research.generators.cross_sectional_momentum import (
    CrossSectionalMomentumGenerator,
)
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import OHLCV, OHLCVSeries
from src.data.models.signal import SignalDirection

_SYMBOL = "BTCUSDT"
_UTC = timezone.utc
# Final bar at 2025-06-10 00:00 UTC -> (epoch_hour % 24)==0 (a rebalance bar).
_LAST_TS = datetime(2025, 6, 10, 0, tzinfo=_UTC)
_N = 60
_START = _LAST_TS - timedelta(hours=_N - 1)

_PARAMS = {
    "rs_lookback_bars": 168,
    "top_k_fraction": 0.25,
    "rebalance_bars": 24,
    "atr_period": 14,
    "atr_stop_multiplier": 2.5,
}


def _series(n: int = _N) -> OHLCVSeries:
    """A gently rising 1H series ending at the rebalance bar (or one bar before)."""
    candles: list[OHLCV] = []
    for i in range(n):
        close = 100.0 + i * 0.2
        prev = 100.0 + (i - 1) * 0.2 if i > 0 else close
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
    return OHLCVSeries(candles=candles, symbol=_SYMBOL, timeframe="1h")


def _seed_rank(in_top_k: bool) -> None:
    """Seed the memo so membership at the final bar is ``in_top_k``."""
    last_ms = int(_LAST_TS.timestamp() * 1000)
    times = tuple(last_ms - (5 - k) * 3_600_000 for k in range(6))
    flags = tuple(in_top_k if k == len(times) - 1 else False for k in range(len(times)))
    gen_mod._RANK_BY_SYMBOL[_SYMBOL] = RankSeries(
        symbol=_SYMBOL, times_ms=times, in_top_k=flags
    )


@pytest.fixture(autouse=True)
def _isolate_rank(monkeypatch, tmp_path):
    """Isolate the rank memo AND the on-disk cache between tests."""
    monkeypatch.setattr(xs_mod, "_CACHE_DIR", tmp_path)
    gen_mod._RANK_BY_SYMBOL.clear()
    yield
    gen_mod._RANK_BY_SYMBOL.clear()


def test_emits_long_on_rebalance_when_top_k() -> None:
    """Rebalance bar + top-k membership -> LONG with a trailing stop."""
    _seed_rank(in_top_k=True)
    gen = CrossSectionalMomentumGenerator()
    sig = gen.generate(_series(), _PARAMS, _SYMBOL)
    assert sig is not None
    assert sig.direction is SignalDirection.LONG
    assert sig.stop_loss is not None and sig.stop_loss < sig.price
    assert sig.take_profit is None   # trailing stop


def test_no_signal_off_rebalance_grid() -> None:
    """A bar one hour before the rebalance boundary -> no signal."""
    _seed_rank(in_top_k=True)
    gen = CrossSectionalMomentumGenerator()
    # Drop the final bar -> last bar is 23:00 UTC, not a multiple of 24h.
    assert gen.generate(_series(_N - 1), _PARAMS, _SYMBOL) is None


def test_no_signal_when_not_top_k() -> None:
    _seed_rank(in_top_k=False)
    gen = CrossSectionalMomentumGenerator()
    assert gen.generate(_series(), _PARAMS, _SYMBOL) is None


def test_no_signal_when_panel_missing() -> None:
    gen = CrossSectionalMomentumGenerator()
    assert gen.generate(_series(), _PARAMS, _SYMBOL) is None


def test_registry_registers_generator_idempotently() -> None:
    factory = SignalGeneratorFactory()
    assert not factory.has_generator("cross_sectional_momentum")
    register_research_generators(factory)
    register_research_generators(factory)  # idempotent
    assert factory.has_generator("cross_sectional_momentum")
    assert isinstance(
        factory.get_generator("cross_sectional_momentum"),
        CrossSectionalMomentumGenerator,
    )
