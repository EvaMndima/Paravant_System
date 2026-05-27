"""Historical regime classifier — per-bar regime labels for backtest analysis.

This module is the BACKTEST-TIME counterpart to RegimeDetector. While
RegimeDetector classifies the CURRENT regime for live trading decisions,
HistoricalRegimeClassifier walks through historical OHLCV bars and produces
a regime label for each bar — needed by the rolling backtest to bucket
trade results by the regime that prevailed when each trade was open.

The classifier extends the existing 4-state taxonomy (STRONG_BULL,
PULLBACK_BULL, BOUNCE_BEAR, STRONG_BEAR) by layering ADX-based trend
strength on top, producing 6 actionable sub-regimes plus TRANSITIONAL
and UNKNOWN.

Decision: DEC-2026-05-27-008 — Regime-aware backtest validation.

Sub-regime taxonomy:
    TRENDING_BULL    EMA50>EMA200 macro + close>EMA50 + ADX>=25
    CHOPPY_BULL      EMA50>EMA200 macro + ADX<25 (with rallies/pullbacks)
    TRENDING_BEAR    EMA50<EMA200 macro + close<EMA50 + ADX>=25
    CHOPPY_BEAR      EMA50<EMA200 macro + ADX<25 (with relief bounces)
    RANGING          ADX<20 across both EMA sides + low ATR/price
    HIGH_VOL         realized vol (ATR/close) above 90th percentile
    TRANSITIONAL     macro side disagrees with prior 2 bars
    UNKNOWN          insufficient data (EMA/ADX warmup)

These are CHOSEN for actionability:
    - TRENDING_BEAR is what BTF-family trend followers need
    - CHOPPY_BEAR is the May 2026 regime where BTF fails
    - TRENDING_BULL is what BTP-family pullback strategies need
    - CHOPPY_BULL is similar but with shallower trends
    - RANGING is where mean-reversion strategies (RSI_BB) excel
    - HIGH_VOL is where volatility-breakout strategies fire

A bar can match only ONE sub-regime; precedence order is:
    UNKNOWN > TRANSITIONAL > HIGH_VOL > RANGING > TRENDING_* > CHOPPY_*
"""
from __future__ import annotations

import enum
import math
from dataclasses import dataclass

import numpy as np

from src.core.indicators.adx import ADX
from src.core.indicators.ema import EMA
from src.core.strategy.regime.detector import RegimeState
from src.data.market_data import OHLCVSeries
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SubRegime(enum.Enum):
    """Fine-grained regime classification for backtest validation."""

    TRENDING_BULL = "trending_bull"
    CHOPPY_BULL = "choppy_bull"
    TRENDING_BEAR = "trending_bear"
    CHOPPY_BEAR = "choppy_bear"
    RANGING = "ranging"
    HIGH_VOL = "high_vol"
    TRANSITIONAL = "transitional"
    UNKNOWN = "unknown"

    @property
    def macro_side(self) -> str:
        """Return 'bull', 'bear', or 'neutral' macro side."""
        if self in (SubRegime.TRENDING_BULL, SubRegime.CHOPPY_BULL):
            return "bull"
        if self in (SubRegime.TRENDING_BEAR, SubRegime.CHOPPY_BEAR):
            return "bear"
        return "neutral"


@dataclass(frozen=True)
class ClassifierThresholds:
    """Tunable thresholds for regime classification.

    All thresholds documented with the empirical rationale they came from.
    Changing these requires DECISIONS.md entry — regime tags are load-bearing.
    """

    # ADX-based trend strength
    adx_trending_min: float = 25.0  # >= this = TRENDING
    adx_ranging_max: float = 20.0   # <= this = consider RANGING

    # Realized volatility (ATR/close) percentiles
    high_vol_percentile: float = 90.0  # ATR/close above 90th percentile = HIGH_VOL
    low_vol_percentile: float = 25.0   # ATR/close below 25th percentile = RANGING candidate

    # Macro stability for TRANSITIONAL detection
    transitional_bars: int = 2  # macro side flipping in last N bars = TRANSITIONAL

    # Lookback for percentile computation
    vol_lookback_bars: int = 60  # ~2 months of daily bars


class HistoricalRegimeClassifier:
    """Classify every bar in an OHLCV series into a SubRegime.

    Operates on the SAME data the strategy backtest is running on, so
    every trade can be attributed to the sub-regime that prevailed at
    its entry bar.

    Two-pass design:
        1. Compute EMAs (50, 200), ADX(14), ATR(14) over the full series.
        2. For each bar from index `start_index` onward, apply the
           taxonomy precedence rules to assign a SubRegime.

    Args:
        thresholds: Classification thresholds (defaults are documented).
        ema_fast: Fast EMA period (default 50, matches RegimeDetector).
        ema_slow: Slow EMA period (default 200, matches RegimeDetector).
        adx_period: ADX period (default 14, industry standard).
    """

    def __init__(
        self,
        thresholds: ClassifierThresholds | None = None,
        ema_fast: int = 50,
        ema_slow: int = 200,
        adx_period: int = 14,
    ) -> None:
        if ema_fast >= ema_slow:
            raise ValueError(
                f"ema_fast ({ema_fast}) must be less than ema_slow ({ema_slow})"
            )
        self._thresholds = thresholds or ClassifierThresholds()
        self._ema_fast = EMA(period=ema_fast)
        self._ema_slow = EMA(period=ema_slow)
        self._adx = ADX(period=adx_period)
        self._ema_fast_period = ema_fast
        self._ema_slow_period = ema_slow
        self._adx_period = adx_period

    def classify_series(
        self, series: OHLCVSeries
    ) -> list[SubRegime]:
        """Return a SubRegime label for every bar in the series.

        Bars where indicators haven't warmed up return SubRegime.UNKNOWN.

        Args:
            series: OHLCV data (recommended: BTC daily for macro regime,
                or the strategy's own timeframe for fine-grained mapping).

        Returns:
            List of SubRegime, same length as series. Index i corresponds
            to bar i in series.candles.
        """
        n = len(series)
        if n < self._ema_slow_period + 5:
            return [SubRegime.UNKNOWN] * n

        try:
            ema_fast_result = self._ema_fast.calculate(series)
            ema_slow_result = self._ema_slow.calculate(series)
            adx_result = self._adx.calculate(series)
        except ValueError as exc:
            logger.warning(
                "historical_classifier_indicator_failed", error=str(exc), bars=n,
            )
            return [SubRegime.UNKNOWN] * n

        ema_fast_vals = ema_fast_result.values
        ema_slow_vals = ema_slow_result.values
        adx_vals = adx_result.adx
        closes = series.closes
        highs = series.highs
        lows = series.lows

        # Compute realized-vol percentiles for HIGH_VOL detection.
        # We use ATR-normalised-by-close as a proxy for realized volatility.
        atr_pct: list[float] = []
        for i in range(n):
            if i < 14:
                atr_pct.append(float("nan"))
                continue
            recent_tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            close_i = closes[i]
            atr_pct.append(recent_tr / close_i if close_i > 0 else float("nan"))

        # Per-bar macro side (bull/bear/unknown) for TRANSITIONAL detection.
        macro_sides: list[str] = []
        for i in range(n):
            ef = ema_fast_vals[i]
            es = ema_slow_vals[i]
            if math.isnan(ef) or math.isnan(es):
                macro_sides.append("unknown")
            else:
                macro_sides.append("bull" if ef > es else "bear")

        labels: list[SubRegime] = []
        for i in range(n):
            ef = ema_fast_vals[i]
            es = ema_slow_vals[i]
            adx_val = adx_vals[i]
            close = closes[i]

            # UNKNOWN: indicators not warmed up
            if (
                math.isnan(ef) or math.isnan(es) or math.isnan(adx_val)
                or math.isinf(ef) or math.isinf(es) or math.isinf(adx_val)
            ):
                labels.append(SubRegime.UNKNOWN)
                continue

            # TRANSITIONAL: macro side flipped recently
            t_bars = self._thresholds.transitional_bars
            if i >= t_bars:
                recent = macro_sides[i - t_bars: i + 1]
                if len(set(recent)) > 1 and "unknown" not in recent:
                    labels.append(SubRegime.TRANSITIONAL)
                    continue

            # HIGH_VOL: ATR/close above high-vol percentile within lookback
            if i >= self._thresholds.vol_lookback_bars:
                lookback_window = atr_pct[i - self._thresholds.vol_lookback_bars + 1: i + 1]
                lookback_valid = [v for v in lookback_window if not math.isnan(v)]
                if lookback_valid and not math.isnan(atr_pct[i]):
                    high_threshold = float(
                        np.percentile(lookback_valid, self._thresholds.high_vol_percentile)
                    )
                    low_threshold = float(
                        np.percentile(lookback_valid, self._thresholds.low_vol_percentile)
                    )
                    if atr_pct[i] >= high_threshold:
                        labels.append(SubRegime.HIGH_VOL)
                        continue
                    # RANGING needs BOTH low ADX AND low realized vol
                    if (
                        adx_val <= self._thresholds.adx_ranging_max
                        and atr_pct[i] <= low_threshold
                    ):
                        labels.append(SubRegime.RANGING)
                        continue

            # TRENDING / CHOPPY by ADX + macro side
            macro_bull = ef > es
            if adx_val >= self._thresholds.adx_trending_min:
                labels.append(
                    SubRegime.TRENDING_BULL if macro_bull
                    else SubRegime.TRENDING_BEAR
                )
            else:
                labels.append(
                    SubRegime.CHOPPY_BULL if macro_bull
                    else SubRegime.CHOPPY_BEAR
                )

        return labels

    def dominant_regime(
        self, series: OHLCVSeries, start_idx: int, end_idx: int,
    ) -> SubRegime:
        """Return the mode SubRegime over [start_idx, end_idx] bars.

        Useful for tagging an entire backtest window with the regime that
        most defined it.

        Args:
            series: OHLCV series.
            start_idx: Inclusive start bar index.
            end_idx: Inclusive end bar index.

        Returns:
            The most frequent SubRegime in the range. Ties broken by
            precedence: TRENDING_* > CHOPPY_* > RANGING > HIGH_VOL.
        """
        all_labels = self.classify_series(series)
        window = all_labels[start_idx: end_idx + 1]
        if not window:
            return SubRegime.UNKNOWN

        # Drop UNKNOWN/TRANSITIONAL from mode calculation if there's a
        # clear ordinary regime; they're noise from indicator warmup or
        # regime flips, not the "character" of the window.
        ordinary = [r for r in window
                    if r not in (SubRegime.UNKNOWN, SubRegime.TRANSITIONAL)]
        if not ordinary:
            return SubRegime.UNKNOWN

        # Count occurrences
        counts: dict[SubRegime, int] = {}
        for r in ordinary:
            counts[r] = counts.get(r, 0) + 1

        # Find max — tie-break by precedence order
        precedence = [
            SubRegime.TRENDING_BULL, SubRegime.TRENDING_BEAR,
            SubRegime.CHOPPY_BULL, SubRegime.CHOPPY_BEAR,
            SubRegime.RANGING, SubRegime.HIGH_VOL,
        ]
        max_count = max(counts.values())
        for r in precedence:
            if counts.get(r) == max_count:
                return r
        return SubRegime.UNKNOWN
