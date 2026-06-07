"""Causal per-trade regime tagging for regime-conditional backtest DSR.

Phase B guard #3 (DEC-2026-06-04-014): every backtest trade is tagged with the
SubRegime active AT ITS ENTRY, using only information available at that time. We
reuse the existing ``HistoricalRegimeClassifier`` (the SAME labeller the rolling
backtest and -- via the live detector's shared taxonomy -- production use), so
the research screen and live trading agree on what a regime IS.

CAUSALITY (the load-bearing property):

``HistoricalRegimeClassifier.classify_series`` assigns ``label[i]`` from EMA(50),
EMA(200), ADX(14) at bar ``i``, a TRAILING TRANSITIONAL check, and a TRAILING
ATR-percentile window -- no future bars enter any label. Tagging a trade entered
at time ``E`` with the label of the latest daily close at or before ``E`` therefore
uses only data available at ``E``. ``is_labeling_causal`` makes this checkable on
real data (and is asserted by ``tests/research/test_regime_tagging.py``): the
label for bar ``i`` computed on the truncated prefix ``series[:i+1]`` must equal
the label computed on the full series.

COARSE BUCKETS (guard #4): splitting trades across all 8 SubRegimes leaves too
few per bucket for DSR. The coarse mapping collapses to directional
``bull``/``bear``/``chop``. UNKNOWN and TRANSITIONAL are NOT assignable to a
coarse bucket (the regime is undefined at entry) -- those trades are excluded
from coarse buckets rather than misattributed.

Research-only module: ``src/`` must never import from here (PRD Section 5.2).
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass
from datetime import datetime, timezone

from src.core.strategy.regime.historical_classifier import (
    HistoricalRegimeClassifier,
    SubRegime,
)
from src.data.market_data import OHLCVSeries
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Coarse directional bucket per SubRegime (guard #4). None = not assignable to a
# coarse bucket (regime undefined at entry -> exclude rather than misattribute).
_COARSE_BUCKET_BY_SUBREGIME: dict[SubRegime, str | None] = {
    SubRegime.TRENDING_BULL: "bull",
    SubRegime.CHOPPY_BULL: "bull",
    SubRegime.TRENDING_BEAR: "bear",
    SubRegime.CHOPPY_BEAR: "bear",
    SubRegime.RANGING: "chop",
    SubRegime.HIGH_VOL: "chop",
    SubRegime.TRANSITIONAL: None,
    SubRegime.UNKNOWN: None,
}

# Stable order for reporting coarse buckets.
COARSE_BUCKETS: tuple[str, ...] = ("bull", "bear", "chop")


@dataclass(frozen=True)
class RegimeTimeline:
    """Causal regime labels indexed by bar timestamp.

    Attributes:
        timestamps: Sorted, timezone-aware UTC bar timestamps.
        labels: ``labels[i]`` is the SubRegime of ``timestamps[i]``, computed
            causally (only data up to bar ``i``).
    """

    timestamps: list[datetime]
    labels: list[SubRegime]


@dataclass(frozen=True)
class TaggedTrade:
    """A backtest trade plus the regime that prevailed at its entry.

    Attributes:
        trade: The serialized ``TradeRecord`` dict (unchanged).
        sub_regime: The fine SubRegime active at the trade's entry time.
        coarse_bucket: The coarse directional bucket (``bull``/``bear``/``chop``),
            or ``None`` when the entry regime is UNKNOWN/TRANSITIONAL.
    """

    trade: dict[str, object]
    sub_regime: SubRegime
    coarse_bucket: str | None


def coarse_bucket_of(sub_regime: SubRegime) -> str | None:
    """Return the coarse directional bucket for a SubRegime, or None.

    Args:
        sub_regime: The fine SubRegime.

    Returns:
        ``"bull"``, ``"bear"``, ``"chop"``, or ``None`` (UNKNOWN/TRANSITIONAL).
    """
    return _COARSE_BUCKET_BY_SUBREGIME.get(sub_regime)


def _parse_entry_time(trade: dict[str, object]) -> datetime | None:
    """Parse a trade's ``entry_time`` into a timezone-aware UTC datetime.

    Accepts a ``datetime`` (as produced in-memory) or an ISO-8601 string (as
    produced by ``TradeRecord.to_dict``). Naive datetimes are assumed UTC.

    Args:
        trade: One serialized ``TradeRecord`` dict.

    Returns:
        A timezone-aware UTC ``datetime``, or ``None`` if unparseable/missing.
    """
    raw = trade.get("entry_time")
    if isinstance(raw, datetime):
        dt = raw
    elif isinstance(raw, str):
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def build_regime_timeline(
    btc_daily: OHLCVSeries, classifier: HistoricalRegimeClassifier | None = None
) -> RegimeTimeline:
    """Build a causal regime timeline from BTC daily bars.

    BTC daily is the universal macro-regime anchor (DEC-2026-05-27-008), matching
    the rolling backtest and the live SubRegime detector.

    Args:
        btc_daily: BTC daily OHLCV series (the regime anchor).
        classifier: Classifier to use; a default ``HistoricalRegimeClassifier``
            is constructed if omitted.

    Returns:
        A ``RegimeTimeline`` whose ``timestamps`` are sorted ascending.
    """
    clf = classifier or HistoricalRegimeClassifier()
    labels = clf.classify_series(btc_daily)
    pairs = sorted(
        ((bar.timestamp, label) for bar, label in zip(btc_daily.candles, labels)),
        key=lambda kv: kv[0],
    )
    timestamps = [ts for ts, _ in pairs]
    ordered_labels = [label for _, label in pairs]
    return RegimeTimeline(timestamps=timestamps, labels=ordered_labels)


def regime_at_entry(entry_time: datetime, timeline: RegimeTimeline) -> SubRegime:
    """Return the SubRegime active at ``entry_time`` (causal lookup).

    Finds the most recent timeline bar at or before ``entry_time`` and returns
    its label. Because each label uses only data up to its own bar, this uses
    only information available at ``entry_time`` -- no lookahead.

    Args:
        entry_time: Timezone-aware UTC trade entry time.
        timeline: The causal regime timeline.

    Returns:
        The SubRegime of the latest bar at or before ``entry_time``;
        ``SubRegime.UNKNOWN`` if the entry precedes the first timeline bar.
    """
    if not timeline.timestamps:
        return SubRegime.UNKNOWN
    # bisect_right gives the insertion point AFTER any equal timestamp, so
    # idx-1 is the latest bar with timestamp <= entry_time.
    idx = bisect.bisect_right(timeline.timestamps, entry_time)
    if idx == 0:
        return SubRegime.UNKNOWN
    return timeline.labels[idx - 1]


def tag_trades(
    trades: list[dict[str, object]], timeline: RegimeTimeline
) -> list[TaggedTrade]:
    """Tag each trade with the regime active at its entry (causal).

    Trades with an unparseable/missing entry time are tagged ``UNKNOWN`` (and
    therefore excluded from coarse buckets) rather than dropped silently.

    Args:
        trades: Serialized ``TradeRecord`` dicts.
        timeline: The causal regime timeline.

    Returns:
        A list of ``TaggedTrade`` in the same order as ``trades``.
    """
    tagged: list[TaggedTrade] = []
    for trade in trades:
        entry = _parse_entry_time(trade)
        sub = regime_at_entry(entry, timeline) if entry is not None else SubRegime.UNKNOWN
        tagged.append(
            TaggedTrade(
                trade=trade,
                sub_regime=sub,
                coarse_bucket=coarse_bucket_of(sub),
            )
        )
    return tagged


def bucket_by_coarse(
    tagged: list[TaggedTrade],
) -> dict[str, list[dict[str, object]]]:
    """Group tagged trades into coarse directional buckets (guard #4).

    UNKNOWN/TRANSITIONAL trades (``coarse_bucket is None``) are excluded.

    Args:
        tagged: Trades tagged with their entry regime.

    Returns:
        Mapping of coarse bucket -> list of trade dicts. Empty buckets omitted.
    """
    buckets: dict[str, list[dict[str, object]]] = {}
    for tt in tagged:
        if tt.coarse_bucket is None:
            continue
        buckets.setdefault(tt.coarse_bucket, []).append(tt.trade)
    return buckets


def bucket_by_sub_regime(
    tagged: list[TaggedTrade],
) -> dict[SubRegime, list[dict[str, object]]]:
    """Group tagged trades by fine SubRegime (used only where per-bucket N is rich).

    UNKNOWN/TRANSITIONAL are excluded (undefined regime at entry).

    Args:
        tagged: Trades tagged with their entry regime.

    Returns:
        Mapping of SubRegime -> list of trade dicts. Empty buckets omitted.
    """
    buckets: dict[SubRegime, list[dict[str, object]]] = {}
    for tt in tagged:
        if tt.sub_regime in (SubRegime.UNKNOWN, SubRegime.TRANSITIONAL):
            continue
        buckets.setdefault(tt.sub_regime, []).append(tt.trade)
    return buckets


def is_labeling_causal(
    series: OHLCVSeries,
    classifier: HistoricalRegimeClassifier | None = None,
    sample_indices: list[int] | None = None,
) -> bool:
    """Verify regime labels are causal: prefix label == full-series label.

    The leakage check for guard #3. For each sampled bar ``i``, classify the
    truncated prefix ``series[:i+1]`` and compare ``label[i]`` to the full-series
    ``label[i]``. If any differ, a label used a future bar -- leakage.

    This is a real, runnable guard (not only a test fixture): the runner can call
    it on the actual BTC daily series before trusting any regime verdict.

    Args:
        series: The OHLCV series whose labelling is checked (e.g. BTC daily).
        classifier: Classifier to use; defaults to a fresh one.
        sample_indices: Bar indices to check. Defaults to a spread of indices
            past the indicator warmup.

    Returns:
        True if every sampled prefix label matches the full-series label.
    """
    clf = classifier or HistoricalRegimeClassifier()
    full = clf.classify_series(series)
    n = len(full)
    if n == 0:
        return True

    if sample_indices is None:
        # Spread checks across the post-warmup range; checking every bar is
        # O(n^2) and unnecessary to detect lookahead.
        start = min(n - 1, 210)  # past EMA(200) warmup
        if start >= n - 1:
            sample_indices = [n - 1]
        else:
            step = max(1, (n - 1 - start) // 25)
            sample_indices = list(range(start, n, step))

    candles = series.candles
    for i in sample_indices:
        if i < 0 or i >= n:
            continue
        prefix = OHLCVSeries(symbol=series.symbol, timeframe=series.timeframe,
                             candles=candles[: i + 1])
        prefix_labels = clf.classify_series(prefix)
        if not prefix_labels:
            continue
        if prefix_labels[-1] != full[i]:
            logger.warning(
                "regime_label_leakage_detected",
                bar_index=i,
                prefix_label=prefix_labels[-1].value,
                full_label=full[i].value,
            )
            return False
    return True
