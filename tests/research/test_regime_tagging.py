"""Tests for causal per-trade regime tagging (DEC-2026-06-04-014, guard #3).

The keystone is the LEAKAGE test: ``is_labeling_causal`` must return True for the
real (causal) classifier and False for a deliberately lookahead-leaking one.
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

from research.backtest.regime_tagging import (
    RegimeTimeline,
    bucket_by_coarse,
    bucket_by_sub_regime,
    build_regime_timeline,
    coarse_bucket_of,
    is_labeling_causal,
    regime_at_entry,
    tag_trades,
)
from src.core.strategy.regime.historical_classifier import (
    HistoricalRegimeClassifier,
    SubRegime,
)
from src.data.market_data import OHLCV, OHLCVSeries

UTC = timezone.utc


def _daily_series(n: int = 260, seed: int = 7) -> OHLCVSeries:
    """Build a deterministic daily OHLCV series with bull/bear cycles."""
    rng = random.Random(seed)
    base = datetime(2025, 1, 1, tzinfo=UTC)
    candles: list[OHLCV] = []
    price = 100.0
    for i in range(n):
        drift = 0.8 * math.sin(i / 25.0)  # cyclical bull/bear macro
        price = max(2.0, price * (1.0 + drift / 100.0) + rng.uniform(-0.5, 0.5))
        close = max(1.0, price * (1.0 + rng.uniform(-0.01, 0.01)))
        hi = max(price, close) * 1.002
        lo = min(price, close) * 0.998
        candles.append(
            OHLCV(
                timestamp=base + timedelta(days=i),
                open=price,
                high=hi,
                low=lo,
                close=close,
                volume=1000.0 + rng.random() * 100.0,
            )
        )
    return OHLCVSeries(candles=candles, symbol="BTCUSDT", timeframe="1d")


class _LeakyClassifier(HistoricalRegimeClassifier):
    """A classifier that PEEKS at the next bar -- the negative control.

    ``label[i]`` depends on ``close[i+1]`` (a future bar), so the full-series
    label at ``i`` will differ from the prefix label computed on ``series[:i+1]``
    (where bar ``i`` has no successor). ``is_labeling_causal`` MUST catch this.
    """

    def classify_series(self, series: OHLCVSeries) -> list[SubRegime]:  # type: ignore[override]
        closes = series.closes
        n = len(closes)
        labels: list[SubRegime] = []
        for i in range(n):
            if i + 1 < n:
                labels.append(
                    SubRegime.TRENDING_BULL
                    if closes[i + 1] > closes[i]
                    else SubRegime.TRENDING_BEAR
                )
            else:
                labels.append(SubRegime.UNKNOWN)  # no future bar to peek at
        return labels


# --- coarse bucket mapping ---------------------------------------------------
def test_coarse_bucket_mapping() -> None:
    """Bull/bear SubRegimes map to coarse buckets; UNKNOWN/TRANSITIONAL do not."""
    assert coarse_bucket_of(SubRegime.TRENDING_BULL) == "bull"
    assert coarse_bucket_of(SubRegime.CHOPPY_BULL) == "bull"
    assert coarse_bucket_of(SubRegime.TRENDING_BEAR) == "bear"
    assert coarse_bucket_of(SubRegime.CHOPPY_BEAR) == "bear"
    assert coarse_bucket_of(SubRegime.RANGING) == "chop"
    assert coarse_bucket_of(SubRegime.HIGH_VOL) == "chop"
    assert coarse_bucket_of(SubRegime.UNKNOWN) is None
    assert coarse_bucket_of(SubRegime.TRANSITIONAL) is None


# --- causal lookup -----------------------------------------------------------
def test_regime_at_entry_is_causal_lookup() -> None:
    """regime_at_entry returns the latest bar AT OR BEFORE the entry time."""
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    timeline = RegimeTimeline(
        timestamps=[t0, t0 + timedelta(days=1), t0 + timedelta(days=2)],
        labels=[SubRegime.TRENDING_BULL, SubRegime.CHOPPY_BEAR, SubRegime.TRENDING_BEAR],
    )
    # Exactly on a bar -> that bar's label.
    assert regime_at_entry(t0, timeline) == SubRegime.TRENDING_BULL
    # Between bars -> the earlier bar (no lookahead to the next).
    assert regime_at_entry(t0 + timedelta(hours=12), timeline) == SubRegime.TRENDING_BULL
    assert regime_at_entry(t0 + timedelta(days=1, hours=6), timeline) == SubRegime.CHOPPY_BEAR
    # Before the first bar -> UNKNOWN (no data available yet).
    assert regime_at_entry(t0 - timedelta(days=1), timeline) == SubRegime.UNKNOWN
    # After the last bar -> the last bar's label.
    assert regime_at_entry(t0 + timedelta(days=10), timeline) == SubRegime.TRENDING_BEAR


def test_regime_at_entry_empty_timeline() -> None:
    """An empty timeline yields UNKNOWN, never an index error."""
    assert regime_at_entry(datetime(2025, 1, 1, tzinfo=UTC),
                           RegimeTimeline(timestamps=[], labels=[])) == SubRegime.UNKNOWN


# --- tagging + bucketing -----------------------------------------------------
def test_tag_trades_and_bucketing_excludes_unknown() -> None:
    """Trades tag by entry regime; UNKNOWN/TRANSITIONAL excluded from buckets."""
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    timeline = RegimeTimeline(
        timestamps=[t0, t0 + timedelta(days=1)],
        labels=[SubRegime.TRENDING_BULL, SubRegime.CHOPPY_BEAR],
    )
    trades = [
        {"entry_time": (t0 + timedelta(hours=2)).isoformat(), "symbol": "BTCUSDT"},  # bull
        {"entry_time": t0 + timedelta(days=1, hours=1), "symbol": "BTCUSDT"},  # bear (datetime)
        {"entry_time": (t0 - timedelta(days=5)).isoformat(), "symbol": "BTCUSDT"},  # UNKNOWN
        {"entry_time": "not-a-timestamp", "symbol": "BTCUSDT"},  # unparseable -> UNKNOWN
    ]
    tagged = tag_trades(trades, timeline)
    assert [t.sub_regime for t in tagged] == [
        SubRegime.TRENDING_BULL,
        SubRegime.CHOPPY_BEAR,
        SubRegime.UNKNOWN,
        SubRegime.UNKNOWN,
    ]
    coarse = bucket_by_coarse(tagged)
    assert sorted(coarse) == ["bear", "bull"]  # UNKNOWN trades excluded
    assert len(coarse["bull"]) == 1
    assert len(coarse["bear"]) == 1
    sub = bucket_by_sub_regime(tagged)
    assert set(sub) == {SubRegime.TRENDING_BULL, SubRegime.CHOPPY_BEAR}


# --- the leakage keystone ----------------------------------------------------
def test_real_classifier_labels_are_causal() -> None:
    """The real historical classifier passes the prefix==full causal check."""
    series = _daily_series()
    assert is_labeling_causal(series) is True


def test_leaky_classifier_is_caught() -> None:
    """A lookahead-leaking classifier is detected (negative control)."""
    series = _daily_series()
    leaky = _LeakyClassifier()
    # Sample mid-series indices where a future bar exists to leak from.
    assert is_labeling_causal(series, classifier=leaky,
                              sample_indices=[50, 100, 150]) is False


def test_build_regime_timeline_sorted_and_aligned() -> None:
    """build_regime_timeline returns sorted timestamps aligned to labels."""
    series = _daily_series(n=230)
    timeline = build_regime_timeline(series)
    assert len(timeline.timestamps) == len(timeline.labels) == 230
    assert timeline.timestamps == sorted(timeline.timestamps)
    # Past EMA(200) warmup at least some bars classify to a real regime.
    assert any(label != SubRegime.UNKNOWN for label in timeline.labels)
