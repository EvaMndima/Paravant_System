"""Keltner Fade ADX signal generator.

Mean-reversion strategy that fades overextensions at Keltner Channel
extremes, filtered by EMA trend direction and ADX weakness confirmation.
StochasticRSI provides momentum confirmation at extremes.

Core concept: In a bear regime (EMA50 sloping down), only SHORT fades
at upper Keltner. In a bull regime (EMA50 sloping up), only LONG fades
at lower Keltner. ADX must be below threshold to confirm the trend is
not too strong for mean reversion to work.

Entry SHORT (bear regime): Upper KC touch + close inside + StochRSI OB + low ADX
Entry LONG  (bull regime): Lower KC touch + close inside + StochRSI OS + low ADX
Exit: Keltner midline (EMA) or ATR-based stop

Template ID: keltner_fade_adx
Strategy Type: mean_reversion
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import ADX, ATR, EMA, KeltnerChannel, StochasticRSI
from src.core.indicators.utils import calculate_normalized_slope
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class KeltnerFadeAdxGenerator(SignalGenerator):
    """Signal generator for Keltner Fade ADX strategy.

    Fades price overextensions at Keltner Channel boundaries when:
    - Trend regime (EMA slope) allows fading in that direction
    - ADX confirms trend is not too strong (favorable for mean reversion)
    - StochasticRSI confirms overbought/oversold at extremes
    - Price has touched the band and closed back inside (rejection candle)

    The key insight: fade WITH the larger trend, not against it.
    In bear trends, sell rallies to upper KC. In bull trends, buy dips
    to lower KC. This aligns mean reversion with trend direction.

    Required parameters:
        kc_ema_period, kc_atr_period, kc_multiplier,
        ema_trend_period, ema_slope_lookback,
        adx_period, adx_max_threshold,
        stoch_rsi_period, stoch_k_smooth, stoch_d_smooth,
        stoch_overbought, stoch_oversold,
        atr_period
    """

    @property
    def template_id(self) -> str:
        """Return template ID for Keltner Fade ADX strategy."""
        return "keltner_fade_adx"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars needed.

        EMA(50) + StochRSI warmup(14+14+3+3=34) + slope lookback(10)
        + buffer = ~80 bars.
        """
        return 80

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate Keltner Fade ADX conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if fade conditions met, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            # Extract parameters
            kc_ema_period = int(params["kc_ema_period"])
            kc_atr_period = int(params["kc_atr_period"])
            kc_multiplier = float(params["kc_multiplier"])
            ema_trend_period = int(params["ema_trend_period"])
            ema_slope_lookback = int(params.get("ema_slope_lookback", 10))
            adx_period = int(params["adx_period"])
            adx_max = float(params["adx_max_threshold"])
            stoch_rsi_period = int(params["stoch_rsi_period"])
            stoch_k = int(params["stoch_k_smooth"])
            stoch_d = int(params["stoch_d_smooth"])
            stoch_ob = float(params["stoch_overbought"])
            stoch_os = float(params["stoch_oversold"])
            atr_period = int(params["atr_period"])

            # Calculate indicators
            kc = KeltnerChannel(
                ema_period=kc_ema_period,
                atr_period=kc_atr_period,
                multiplier=kc_multiplier,
            ).calculate(series)
            ema_trend = EMA(period=ema_trend_period).calculate(series)
            adx_result = ADX(period=adx_period).calculate(series)
            stoch = StochasticRSI(
                rsi_period=stoch_rsi_period,
                stoch_period=stoch_rsi_period,
                k_smooth=stoch_k,
                d_smooth=stoch_d,
            ).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            last_idx = len(series) - 1
            prev_idx = last_idx - 1
            if prev_idx < 0:
                return None

            price = float(series.closes[last_idx])
            prev_high = float(series.highs[prev_idx])
            prev_low = float(series.lows[prev_idx])

            # Validate critical values
            kc_upper = kc.upper[last_idx]
            kc_lower = kc.lower[last_idx]
            kc_middle = kc.middle[last_idx]
            if any(np.isnan(v) for v in [kc_upper, kc_lower, kc_middle]):
                return None

            # EMA slope for regime detection
            valid_ema = ema_trend.values[~np.isnan(ema_trend.values)]
            if len(valid_ema) < ema_slope_lookback:
                return None
            ema_slope = calculate_normalized_slope(valid_ema, ema_slope_lookback)

            # ADX value
            valid_adx = adx_result.adx[~np.isnan(adx_result.adx)]
            if len(valid_adx) == 0:
                return None
            adx_current = float(valid_adx[-1])

            # StochasticRSI K line
            valid_k = stoch.k_line[~np.isnan(stoch.k_line)]
            if len(valid_k) == 0:
                return None
            stoch_k_val = float(valid_k[-1])

            # ATR for stops
            atr_current = atr_result.current
            if np.isnan(atr_current) or atr_current <= 0:
                return None

            # --- ADX Filter: trend must NOT be too strong ---
            if adx_current > adx_max:
                return None

            # Build indicator snapshot
            indicators = {
                "kc_upper": float(kc_upper),
                "kc_middle": float(kc_middle),
                "kc_lower": float(kc_lower),
                "ema_trend": float(valid_ema[-1]),
                "ema_slope": ema_slope,
                "adx": adx_current,
                "stoch_rsi_k": stoch_k_val,
                "atr": atr_current,
            }

            # --- SHORT Fade (Bear Regime) ---
            # EMA sloping down + price touched upper KC + closed back inside + StochRSI OB
            if ema_slope < 0:
                # Any of last 3 bars touched/exceeded upper KC (wick above)
                # Wider window captures rejections that develop over 2-3 bars
                touched_upper = False
                for j in range(1, min(4, last_idx + 1)):
                    idx_j = last_idx - j
                    if not np.isnan(kc.upper[idx_j]):
                        if float(series.highs[idx_j]) >= kc.upper[idx_j]:
                            touched_upper = True
                            break
                # Current bar closes back inside KC (rejection)
                closed_inside = price < float(kc_upper)

                if touched_upper and closed_inside and stoch_k_val > stoch_ob:
                    strength = self._calc_strength(
                        adx_current, adx_max, stoch_k_val, stoch_ob, is_short=True,
                    )
                    # Target: Keltner midline. Stop: above upper KC + ATR buffer
                    stop_loss = float(kc_upper) + 1.0 * atr_current

                    return TradingSignal(
                        direction=SignalDirection.SHORT,
                        symbol=symbol,
                        price=price,
                        strength=strength,
                        stop_loss=stop_loss,
                        take_profit=float(kc_middle),
                        indicators=indicators,
                        metadata={
                            "trigger": "keltner_fade_short",
                            "regime": "bear",
                            "fade_target": "kc_midline",
                        },
                    )

            # --- LONG Fade (Bull Regime) ---
            # EMA sloping up + price touched lower KC + closed back inside + StochRSI OS
            if ema_slope > 0:
                # Any of last 3 bars touched/fell below lower KC
                touched_lower = False
                for j in range(1, min(4, last_idx + 1)):
                    idx_j = last_idx - j
                    if not np.isnan(kc.lower[idx_j]):
                        if float(series.lows[idx_j]) <= kc.lower[idx_j]:
                            touched_lower = True
                            break
                # Current bar closes back inside KC
                closed_inside = price > float(kc_lower)

                if touched_lower and closed_inside and stoch_k_val < stoch_os:
                    strength = self._calc_strength(
                        adx_current, adx_max, stoch_k_val, stoch_os, is_short=False,
                    )
                    # Target: Keltner midline. Stop: below lower KC - ATR buffer
                    stop_loss = float(kc_lower) - 1.0 * atr_current

                    return TradingSignal(
                        direction=SignalDirection.LONG,
                        symbol=symbol,
                        price=price,
                        strength=strength,
                        stop_loss=max(stop_loss, price * 0.001),
                        take_profit=float(kc_middle),
                        indicators=indicators,
                        metadata={
                            "trigger": "keltner_fade_long",
                            "regime": "bull",
                            "fade_target": "kc_midline",
                        },
                    )

        except (ValueError, KeyError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None

    @staticmethod
    def _calc_strength(
        adx: float,
        adx_max: float,
        stoch_k: float,
        stoch_threshold: float,
        *,
        is_short: bool,
    ) -> float:
        """Calculate signal strength from ADX weakness and StochRSI extremity.

        Lower ADX = weaker trend = better for mean reversion.
        More extreme StochRSI = stronger fade signal.

        Args:
            adx: Current ADX value.
            adx_max: Maximum ADX threshold for fading.
            stoch_k: Current StochasticRSI K value.
            stoch_threshold: Overbought/oversold threshold.
            is_short: True for short fade (uses overbought), False for long.

        Returns:
            Signal strength between 0.3 and 0.9.
        """
        # ADX bonus: lower ADX = better for fading
        adx_score = max(0, (adx_max - adx) / adx_max) * 0.2

        # StochRSI extremity bonus
        if is_short:
            extremity = max(0, (stoch_k - stoch_threshold) / (100 - stoch_threshold))
        else:
            extremity = max(0, (stoch_threshold - stoch_k) / stoch_threshold)
        stoch_score = extremity * 0.2

        # Mean reversion strategies have moderate base confidence
        strength = 0.45 + adx_score + stoch_score
        return max(0.3, min(0.9, strength))
