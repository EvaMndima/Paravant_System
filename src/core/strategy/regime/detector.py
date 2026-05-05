"""Regime detection from BTC daily EMA(50)/EMA(200).

Decision: DEC-2026-05-04-001 - Dual-EMA composite 4-state approach
Decision: DEC-2026-05-04-002 - 2-consecutive-close confirmation rule
Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

import enum
import math

from src.core.indicators.ema import EMA
from src.data.market_data import MarketDataFetcher, OHLCVSeries
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RegimeState(enum.Enum):
    """Market regime classification based on BTC daily EMA(50)/EMA(200).

    Decision: DEC-2026-05-04-001 - Dual-EMA composite 4-state approach

    4 states capture both market structure (EMA relationship) and price
    position within that structure:
        STRONG_BULL    EMA50 > EMA200, price > EMA50   (full participation)
        PULLBACK_BULL  EMA50 > EMA200, price <= EMA50  (retracement in bull)
        BOUNCE_BEAR    EMA50 < EMA200, price >= EMA50  (dead-cat / recovery)
        STRONG_BEAR    EMA50 < EMA200, price < EMA50   (full bear momentum)
        UNKNOWN        Insufficient data or confirmation failure
    """

    STRONG_BULL = "strong_bull"
    PULLBACK_BULL = "pullback_bull"
    BOUNCE_BEAR = "bounce_bear"
    STRONG_BEAR = "strong_bear"
    UNKNOWN = "unknown"

    @property
    def is_bull(self) -> bool:
        """Return True if any bull variant (STRONG_BULL or PULLBACK_BULL)."""
        return self in (RegimeState.STRONG_BULL, RegimeState.PULLBACK_BULL)

    @property
    def is_bear(self) -> bool:
        """Return True if any bear variant (STRONG_BEAR or BOUNCE_BEAR)."""
        return self in (RegimeState.STRONG_BEAR, RegimeState.BOUNCE_BEAR)


class RegimeDetector:
    """Detects crypto market regime from BTC daily EMA(50)/EMA(200).

    Decision: DEC-2026-05-04-001 - Dual-EMA composite 4-state approach
    Decision: DEC-2026-05-04-002 - 2-consecutive-close confirmation rule

    Fetches BTC 1d OHLCV bars, computes EMA(ema_fast) and EMA(ema_slow),
    and classifies into 4 regime states. A regime change requires
    confirmation_bars consecutive daily closes on the same macro side
    (bull or bear) before it is confirmed — preventing whipsaw switches.

    Args:
        fetcher: MarketDataFetcher instance for OHLCV data.
        ema_fast: Fast EMA period (default 50).
        ema_slow: Slow EMA period (default 200).
        confirmation_bars: Consecutive closes required for confirmation (default 2).
        daily_bars: Number of daily bars to fetch (default 300).

    Raises:
        ValueError: If ema_fast >= ema_slow, confirmation_bars < 1, or
                    daily_bars is insufficient for EMA warmup.
    """

    def __init__(
        self,
        fetcher: MarketDataFetcher,
        ema_fast: int = 50,
        ema_slow: int = 200,
        confirmation_bars: int = 2,
        daily_bars: int = 300,
    ) -> None:
        if ema_fast >= ema_slow:
            raise ValueError(
                f"ema_fast ({ema_fast}) must be less than ema_slow ({ema_slow})"
            )
        if confirmation_bars < 1:
            raise ValueError(
                f"confirmation_bars must be >= 1, got {confirmation_bars}"
            )
        if daily_bars < ema_slow + confirmation_bars:
            raise ValueError(
                f"daily_bars ({daily_bars}) must exceed ema_slow + confirmation_bars "
                f"({ema_slow + confirmation_bars}) to allow EMA warmup"
            )

        self._fetcher = fetcher
        self._ema_fast = EMA(period=ema_fast)
        self._ema_slow = EMA(period=ema_slow)
        self._confirmation_bars = confirmation_bars
        self._daily_bars = daily_bars

    async def detect(self) -> RegimeState:
        """Fetch fresh BTC daily data and return current state (no confirmation).

        Raw classification of the most recent bar. Does not apply the
        2-consecutive-close rule — use get_confirmed_state() before acting.
        Returns UNKNOWN if data is insufficient or fetch fails.

        Returns:
            RegimeState for the most recent daily close.
        """
        series = await self._fetch_btc_daily()
        if series is None:
            return RegimeState.UNKNOWN

        return self._classify_bar(series, index=-1)

    async def get_confirmed_state(self) -> RegimeState:
        """Return confirmed state requiring confirmation_bars consecutive closes.

        Decision: DEC-2026-05-04-002 - 2-consecutive-close confirmation rule

        Checks the last confirmation_bars daily closes. If they all agree on
        the same macro side (both bull or both bear), returns the most recent
        specific state. If any bar disagrees or is UNKNOWN, returns UNKNOWN
        to block action on a single-candle fakeout.

        Returns:
            Confirmed RegimeState, or UNKNOWN if confirmation fails.
        """
        series = await self._fetch_btc_daily()
        if series is None:
            return RegimeState.UNKNOWN

        states: list[RegimeState] = []
        for i in range(-self._confirmation_bars, 0):
            state = self._classify_bar(series, index=i)
            states.append(state)

        if not states:
            return RegimeState.UNKNOWN

        anchor = states[0]
        if anchor == RegimeState.UNKNOWN:
            return RegimeState.UNKNOWN

        for state in states[1:]:
            if state == RegimeState.UNKNOWN:
                logger.info(
                    "regime_confirmation_failed",
                    reason="unknown_bar",
                    states=[s.value for s in states],
                )
                return RegimeState.UNKNOWN
            # Macro side must match: both bull or both bear
            if state.is_bull != anchor.is_bull:
                logger.info(
                    "regime_confirmation_failed",
                    reason="macro_side_disagreement",
                    states=[s.value for s in states],
                )
                return RegimeState.UNKNOWN

        confirmed = states[-1]
        logger.info(
            "regime_confirmed",
            state=confirmed.value,
            bars_checked=self._confirmation_bars,
        )
        return confirmed

    def _classify_bar(self, series: OHLCVSeries, index: int) -> RegimeState:
        """Classify a single bar at the given index.

        Args:
            series: BTC daily OHLCV series.
            index: Bar index (supports negative indexing, e.g. -1 for latest).

        Returns:
            RegimeState for the bar, UNKNOWN if EMAs are not yet warm or invalid.
        """
        try:
            fast_result = self._ema_fast.calculate(series)
            slow_result = self._ema_slow.calculate(series)
        except ValueError:
            logger.warning(
                "regime_ema_calculation_failed",
                bars=len(series),
                ema_fast_period=self._ema_fast.period,
                ema_slow_period=self._ema_slow.period,
            )
            return RegimeState.UNKNOWN

        n = len(series)
        # Map negative index to positive
        pos_index = index if index >= 0 else n + index

        if pos_index < 0 or pos_index >= n:
            return RegimeState.UNKNOWN

        ema_fast_val = fast_result.values[pos_index]
        ema_slow_val = slow_result.values[pos_index]
        close = series.closes[pos_index]

        # EMA warmup produces NaN; treat as insufficient data
        if (
            math.isnan(ema_fast_val)
            or math.isinf(ema_fast_val)
            or math.isnan(ema_slow_val)
            or math.isinf(ema_slow_val)
        ):
            logger.debug(
                "regime_ema_warmup_incomplete",
                bar_index=pos_index,
                total_bars=n,
            )
            return RegimeState.UNKNOWN

        bull_structure = ema_fast_val > ema_slow_val

        if bull_structure:
            state = (
                RegimeState.STRONG_BULL
                if close > ema_fast_val
                else RegimeState.PULLBACK_BULL
            )
        else:
            state = (
                RegimeState.BOUNCE_BEAR
                if close >= ema_fast_val
                else RegimeState.STRONG_BEAR
            )

        logger.debug(
            "regime_bar_classified",
            bar_index=pos_index,
            state=state.value,
            close=round(close, 2),
            ema_fast=round(ema_fast_val, 2),
            ema_slow=round(ema_slow_val, 2),
        )
        return state

    async def _fetch_btc_daily(self) -> OHLCVSeries | None:
        """Fetch BTC 1d OHLCV data from Binance.

        Returns:
            OHLCVSeries on success, None if fetch fails (non-fatal).
        """
        try:
            series = await self._fetcher.fetch_ohlcv(
                symbol="BTCUSDT",
                timeframe="1d",
                limit=self._daily_bars,
            )
            logger.info(
                "regime_data_fetched",
                bars=len(series),
                last_close=round(float(series.closes[-1]), 2) if len(series) > 0 else None,
                last_ts=(
                    series.candles[-1].timestamp.isoformat()
                    if len(series) > 0
                    else None
                ),
            )
            return series
        except Exception as exc:
            logger.error(
                "regime_data_fetch_failed",
                error=str(exc),
                exc_info=True,
            )
            return None
