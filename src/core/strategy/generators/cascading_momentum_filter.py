"""Cascading Momentum Filter signal generator.

Triple-timeframe trend-following strategy requiring ALL 3 timeframes
to agree on direction before entry. Uses a top-down cascade:

Daily:  SuperTrend => macro regime direction
4H:     EMA(21) slope + ADX => trend confirmation with momentum
1H:     SuperTrend flip + MACD crossover => precise entry timing

Only enters when all 3 layers agree. Very high conviction signals
(strength 0.8-1.0) but lower frequency.

Template ID: cascading_momentum_filter
Strategy Type: trend_following
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import ADX, ATR, EMA, MACD, SuperTrend
from src.core.indicators.resample import resample_ohlcv
from src.core.indicators.utils import calculate_normalized_slope
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CascadingMomentumFilterGenerator(SignalGenerator):
    """Signal generator for Cascading Momentum Filter strategy.

    Implements a strict top-down multi-timeframe filter where each
    lower timeframe must confirm the higher timeframe's direction
    before entry is permitted.

    Cascade structure:
        Layer 1 (Daily): SuperTrend defines macro regime
            - Bullish ST => only consider LONG entries
            - Bearish ST => only consider SHORT entries

        Layer 2 (4H): EMA(21) slope + ADX confirms trend
            - EMA slope must agree with Daily direction
            - ADX must exceed minimum threshold (trend has momentum)

        Layer 3 (1H): SuperTrend flip + MACD provides entry timing
            - SuperTrend must just flip in the cascade direction
            - MACD histogram must confirm momentum direction

    All 3 layers must agree. If ANY layer disagrees, no signal.

    Required parameters:
        daily_st_period, daily_st_multiplier,
        htf_ema_period, htf_adx_period, htf_adx_min, htf_slope_lookback,
        st_period_1h, st_multiplier_1h,
        macd_fast, macd_slow, macd_signal,
        atr_period
    """

    @property
    def template_id(self) -> str:
        """Return template ID for Cascading Momentum Filter strategy."""
        return "cascading_momentum_filter"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars needed.

        Daily SuperTrend(10,3) needs ~11 complete days = 264 1H bars.
        Plus 4H warmup and buffer = 350 bars.
        """
        return 350

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate Cascading Momentum Filter conditions.

        Resamples 1H data to both 4H and Daily internally, then
        checks all 3 cascade layers for directional agreement.

        Args:
            series: OHLCV series (1H timeframe) for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if all 3 layers agree, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            # Extract parameters
            daily_st_period = int(params["daily_st_period"])
            daily_st_mult = float(params["daily_st_multiplier"])
            htf_ema_period = int(params["htf_ema_period"])
            htf_adx_period = int(params["htf_adx_period"])
            htf_adx_min = float(params["htf_adx_min"])
            htf_slope_lookback = int(params.get("htf_slope_lookback", 5))
            st_period_1h = int(params["st_period_1h"])
            st_mult_1h = float(params["st_multiplier_1h"])
            macd_fast = int(params["macd_fast"])
            macd_slow = int(params["macd_slow"])
            macd_signal_period = int(params["macd_signal"])
            atr_period = int(params["atr_period"])
            # Default stop=3.0 and rr=1.0 preserves prior ATR-distance
            # behaviour (stop=3x, TP=3x → R:R 1:1 vs old hardcoded 2.5/3.0).
            atr_stop_mult = float(params.get("atr_stop_multiplier", 3.0))
            rr_ratio = float(params.get("risk_reward_ratio", 1.0))

            # ==========================================
            # LAYER 1: Daily SuperTrend (Macro Regime)
            # ==========================================
            series_daily = resample_ohlcv(series, "1d")
            min_daily = daily_st_period + 1
            if len(series_daily) < min_daily:
                logger.debug(
                    "insufficient_daily_data",
                    bars_daily=len(series_daily),
                    required=min_daily,
                    generator=self.__class__.__name__,
                )
                return None

            daily_st = SuperTrend(
                period=daily_st_period, multiplier=daily_st_mult,
            ).calculate(series_daily)

            daily_trend = daily_st.current_trend
            if daily_trend == 0:
                return None  # No trend established yet

            # ==========================================
            # LAYER 2: 4H EMA slope + ADX (Confirmation)
            # ==========================================
            series_4h = resample_ohlcv(series, "4h")
            if len(series_4h) < max(htf_ema_period, htf_adx_period + 1):
                return None

            htf_ema = EMA(period=htf_ema_period).calculate(series_4h)
            htf_adx = ADX(period=htf_adx_period).calculate(series_4h)

            # EMA slope direction
            valid_ema = htf_ema.values[~np.isnan(htf_ema.values)]
            if len(valid_ema) < htf_slope_lookback:
                return None
            ema_slope = calculate_normalized_slope(valid_ema, htf_slope_lookback)

            # ADX strength
            valid_adx = htf_adx.adx[~np.isnan(htf_adx.adx)]
            if len(valid_adx) == 0:
                return None
            adx_4h = float(valid_adx[-1])

            # Layer 2 checks: slope agrees with Daily + ADX strong enough
            if daily_trend == 1:  # Daily bullish
                if ema_slope <= 0 or adx_4h < htf_adx_min:
                    return None  # 4H doesn't confirm bullish
            else:  # Daily bearish
                if ema_slope >= 0 or adx_4h < htf_adx_min:
                    return None  # 4H doesn't confirm bearish

            # ==========================================
            # LAYER 3: 1H SuperTrend + MACD (Entry)
            # ==========================================
            st_1h = SuperTrend(
                period=st_period_1h, multiplier=st_mult_1h,
            ).calculate(series)
            macd_result = MACD(
                fast_period=macd_fast,
                slow_period=macd_slow,
                signal_period=macd_signal_period,
            ).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            atr_val = atr_result.current
            if np.isnan(atr_val) or atr_val <= 0:
                return None

            # MACD histogram
            valid_hist = macd_result.histogram[~np.isnan(macd_result.histogram)]
            if len(valid_hist) < 2:
                return None
            hist_curr = float(valid_hist[-1])
            hist_prev = float(valid_hist[-2])

            last_idx = len(series) - 1
            price = float(series.closes[last_idx])

            # Indicator snapshot
            indicators = {
                "daily_supertrend": float(daily_trend),
                "htf_ema_slope": ema_slope,
                "htf_adx": adx_4h,
                "st_1h_trend": float(st_1h.current_trend),
                "macd_histogram": hist_curr,
                "atr": atr_val,
            }

            # --- LONG: all 3 layers bullish ---
            if daily_trend == 1:
                # Check if 1H SuperTrend flipped bullish in last 3 bars
                # (wider window than single-bar just_flipped)
                st_flipped_bull = self._recently_flipped(
                    st_1h.trend, target_direction=1, lookback=3,
                )
                # MACD must be positive (direction only, no acceleration
                # requirement — acceleration is too strict on the exact
                # bar of a ST flip)
                macd_bullish = hist_curr > 0

                if st_flipped_bull and macd_bullish:
                    strength = self._calc_strength(adx_4h, htf_adx_min, ema_slope)
                    stop_loss = price - atr_stop_mult * atr_val
                    take_profit = price + rr_ratio * atr_stop_mult * atr_val

                    return TradingSignal(
                        direction=SignalDirection.LONG,
                        symbol=symbol,
                        price=price,
                        strength=strength,
                        stop_loss=max(stop_loss, price * 0.001),
                        take_profit=take_profit,
                        indicators=indicators,
                        metadata={
                            "trigger": "cmf_cascade_long",
                            "daily_regime": "bullish",
                            "htf_confirmation": "bullish",
                            "entry_timing": "st_flip_macd",
                        },
                    )

            # --- SHORT: all 3 layers bearish ---
            if daily_trend == -1:
                # Check if 1H SuperTrend flipped bearish in last 3 bars
                st_flipped_bear = self._recently_flipped(
                    st_1h.trend, target_direction=-1, lookback=3,
                )
                # MACD must be negative (direction only)
                macd_bearish = hist_curr < 0

                if st_flipped_bear and macd_bearish:
                    strength = self._calc_strength(adx_4h, htf_adx_min, ema_slope)
                    stop_loss = price + atr_stop_mult * atr_val
                    take_profit = price - rr_ratio * atr_stop_mult * atr_val

                    return TradingSignal(
                        direction=SignalDirection.SHORT,
                        symbol=symbol,
                        price=price,
                        strength=strength,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        indicators=indicators,
                        metadata={
                            "trigger": "cmf_cascade_short",
                            "daily_regime": "bearish",
                            "htf_confirmation": "bearish",
                            "entry_timing": "st_flip_macd",
                        },
                    )

        except (ValueError, KeyError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None

    @staticmethod
    def _recently_flipped(
        trend: np.ndarray,
        target_direction: int,
        lookback: int = 3,
    ) -> bool:
        """Check if SuperTrend flipped to target direction within recent bars.

        Unlike just_flipped() which only detects flips on the exact bar,
        this checks a window of recent bars for any sign change. This
        captures entries where the flip occurred 1-2 bars ago but price
        action is still confirming the new direction.

        Args:
            trend: SuperTrend trend array (+1/-1/0 per bar).
            target_direction: Direction to check for (+1 bullish, -1 bearish).
            lookback: Number of recent transitions to check.

        Returns:
            True if a flip to target_direction occurred within the window.
        """
        # Filter to valid (non-zero) trend values
        valid = trend[trend != 0]
        if len(valid) < 2:
            return False

        # Check last `lookback` transitions for a flip
        end = len(valid)
        start = max(1, end - lookback)
        for i in range(end - 1, start - 1, -1):
            if valid[i] == target_direction and valid[i - 1] == -target_direction:
                return True
        return False

    @staticmethod
    def _calc_strength(
        adx_4h: float,
        adx_min: float,
        ema_slope: float,
    ) -> float:
        """Calculate signal strength from cascade agreement quality.

        Triple-TF agreement signals start at 0.8 base strength.
        Higher ADX and steeper slope push toward 1.0.

        Args:
            adx_4h: 4H ADX value (already confirmed > adx_min).
            adx_min: Minimum ADX threshold.
            ema_slope: 4H EMA normalized slope.

        Returns:
            Strength between 0.8 and 1.0.
        """
        # ADX bonus: stronger trend = more conviction
        adx_excess = max(0, adx_4h - adx_min)
        adx_score = min(0.1, adx_excess * 0.003)

        # Slope bonus: steeper slope = more conviction
        slope_score = min(0.1, abs(ema_slope) * 0.05)

        return max(0.8, min(1.0, 0.8 + adx_score + slope_score))
