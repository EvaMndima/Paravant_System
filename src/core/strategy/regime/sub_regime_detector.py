"""Live SubRegime detection — counterpart to HistoricalRegimeClassifier.

While HistoricalRegimeClassifier walks an OHLCV series and labels every
bar, SubRegimeDetector fetches the latest BTC daily series at runtime
and reports the most-recent bar's SubRegime label, with confirmation
across the last N bars to avoid whipsaws on threshold-straddling ADX
or vol-percentile transitions.

Architecturally parallel to RegimeDetector (which outputs the coarse
4-state RegimeState). The two can run side-by-side: legacy code reads
RegimeState; new code reads SubRegime.

Decision: DEC-2026-05-28-003 — SubRegime-aware live routing.

Fail-closed contract:
    Any data fetch failure, classification failure, or confirmation
    failure returns SubRegime.UNKNOWN. Callers (router) treat UNKNOWN
    as "do not activate any regime_tags-based strategy" — better to be
    quiet than to route a strategy to the wrong regime.
"""
from __future__ import annotations

from src.core.strategy.regime.historical_classifier import (
    ClassifierThresholds,
    HistoricalRegimeClassifier,
    SubRegime,
)
from src.data.market_data import MarketDataFetcher, OHLCVSeries
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SubRegimeDetector:
    """Detect the current SubRegime from BTC daily OHLCV with confirmation.

    Wraps a MarketDataFetcher (for BTC daily bars) and a
    HistoricalRegimeClassifier (for per-bar SubRegime labels). Reports
    the most-recent bar's SubRegime only when the last `confirmation_bars`
    bars all agree on the same label — otherwise returns UNKNOWN.

    Args:
        fetcher: MarketDataFetcher used to pull BTC 1d OHLCV.
        confirmation_bars: How many consecutive recent bars must share
            the same SubRegime label before reporting it as the current
            state. Default 2, matching the existing RegimeDetector's
            macro-side confirmation policy. Must be >= 1.
        thresholds: Optional ClassifierThresholds override. Default is
            the production threshold set on HistoricalRegimeClassifier.
        daily_bars: How many daily bars to fetch. Default 300 (allows
            EMA(200) + ADX(14) to warm up with buffer).
    """

    def __init__(
        self,
        fetcher: MarketDataFetcher,
        confirmation_bars: int = 2,
        thresholds: ClassifierThresholds | None = None,
        daily_bars: int = 300,
    ) -> None:
        if confirmation_bars < 1:
            raise ValueError(
                f"confirmation_bars must be >= 1, got {confirmation_bars}"
            )
        if daily_bars < 250:
            # EMA(200) needs ~210 bars of warmup; HighVol pct uses 60-bar
            # rolling window; below 250 the percentile calc is unstable.
            raise ValueError(
                f"daily_bars must be >= 250 for stable classification, "
                f"got {daily_bars}"
            )

        self._fetcher = fetcher
        self._confirmation_bars = confirmation_bars
        self._classifier = HistoricalRegimeClassifier(thresholds=thresholds)
        self._daily_bars = daily_bars

    async def detect(self) -> SubRegime:
        """Return the most-recent bar's SubRegime (no confirmation).

        Useful for debugging or read-only status displays. Production
        routing should use `get_confirmed_state()` instead.

        Returns:
            SubRegime label of the latest BTC daily bar, or UNKNOWN on
            fetch/classification failure.
        """
        series = await self._fetch_btc_daily()
        if series is None:
            return SubRegime.UNKNOWN
        labels = self._classifier.classify_series(series)
        if not labels:
            return SubRegime.UNKNOWN
        return labels[-1]

    async def get_confirmed_state(self) -> SubRegime:
        """Return the SubRegime only if last N bars all agree.

        The confirmation rule is intentionally strict: ALL of the last
        `confirmation_bars` bars must have the same label, AND that label
        must not be UNKNOWN or TRANSITIONAL. This prevents:
          - Single-bar fakeouts when ADX briefly crosses 25
          - Routing on the bar of a macro flip (TRANSITIONAL)
          - Acting on warmup-incomplete signals (UNKNOWN)

        Returns:
            Confirmed SubRegime, or UNKNOWN if confirmation fails.
        """
        series = await self._fetch_btc_daily()
        if series is None:
            return SubRegime.UNKNOWN

        labels = self._classifier.classify_series(series)
        if len(labels) < self._confirmation_bars:
            logger.info(
                "sub_regime_confirmation_insufficient_data",
                labels_available=len(labels),
                confirmation_bars=self._confirmation_bars,
            )
            return SubRegime.UNKNOWN

        tail = labels[-self._confirmation_bars:]
        anchor = tail[0]

        # Reject UNKNOWN / TRANSITIONAL anchors — they're never a stable
        # state to activate strategies on.
        if anchor in (SubRegime.UNKNOWN, SubRegime.TRANSITIONAL):
            logger.info(
                "sub_regime_confirmation_unstable_anchor",
                anchor=anchor.value,
                tail=[r.value for r in tail],
            )
            return SubRegime.UNKNOWN

        for bar_label in tail[1:]:
            if bar_label != anchor:
                logger.info(
                    "sub_regime_confirmation_disagreement",
                    anchor=anchor.value,
                    tail=[r.value for r in tail],
                )
                return SubRegime.UNKNOWN

        logger.info(
            "sub_regime_confirmed",
            state=anchor.value,
            bars_checked=self._confirmation_bars,
        )
        return anchor

    async def _fetch_btc_daily(self) -> OHLCVSeries | None:
        """Fetch BTC 1d OHLCV. Returns None on any failure (fail-closed)."""
        try:
            series = await self._fetcher.fetch_ohlcv(
                symbol="BTCUSDT",
                timeframe="1d",
                limit=self._daily_bars,
            )
            logger.debug(
                "sub_regime_data_fetched",
                bars=len(series),
                last_ts=(
                    series.candles[-1].timestamp.isoformat()
                    if len(series) > 0 else None
                ),
            )
            return series
        except Exception as exc:
            logger.error(
                "sub_regime_data_fetch_failed",
                error=str(exc),
                exc_info=True,
            )
            return None
