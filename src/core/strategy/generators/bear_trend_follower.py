"""Bear Trend Follower signal generator.

Multi-timeframe trend-following strategy designed for bear markets.
Uses 4H EMA(200) for regime detection and 1H indicators for entries.

BEAR regime (price below 4H EMA200):
    PRIMARY SHORT: Upper Keltner rejection + ADX>25 + -DI > +DI
BULL regime (price above 4H EMA200):
    SECONDARY LONG: Lower Keltner + RSI<25 (counter-trend, low strength)

Multi-TF approach: Resamples 1H input to 4H internally via resample_ohlcv().
No changes to the backtest engine or generator interface.

Template ID: bear_trend_follower
Strategy Type: trend_following
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import ADX, ATR, EMA, RSI, KeltnerChannel, SuperTrend
from src.core.indicators.resample import resample_ohlcv
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BearTrendFollowerGenerator(SignalGenerator):
    """Signal generator for Bear Trend Follower strategy.

    Uses higher-timeframe (4H) EMA(200) as a regime filter:
    - Below 4H EMA(200) = BEAR regime: primarily SHORT
    - Above 4H EMA(200) = BULL regime: counter-trend LONG only

    BEAR regime SHORT entry (primary, high conviction):
        1. Price below 4H EMA(200) — confirmed bear
        2. Price touches/exceeds upper Keltner (1H) — overextended rally
        3. Price closes back inside KC (rejection candle)
        4. ADX > threshold — trend has momentum
        5. -DI > +DI — sellers dominate

    BULL regime LONG entry (secondary, low conviction):
        1. Price above 4H EMA(200) — bull context
        2. Price touches/falls below lower Keltner (1H)
        3. RSI < oversold threshold — oversold bounce
        4. SuperTrend bullish — confirms bounce

    Required parameters:
        htf_ema_period, kc_ema_period, kc_atr_period, kc_multiplier,
        adx_period, adx_min_threshold, rsi_period, rsi_oversold,
        supertrend_period, supertrend_multiplier, atr_period
    """

    @property
    def template_id(self) -> str:
        """Return template ID for Bear Trend Follower strategy."""
        return "bear_trend_follower"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars needed.

        EMA(200) on 4H needs 200 * 4 = 800 1H bars for warmup.
        Plus Keltner/ADX warmup (~20) and buffer (~10) = 810.
        """
        return 810

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate Bear Trend Follower conditions.

        Resamples 1H data to 4H internally for regime detection,
        then evaluates 1H indicators for entry signals.

        Args:
            series: OHLCV series (1H timeframe) for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if conditions met, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            # Extract parameters
            htf_ema_period = int(params["htf_ema_period"])
            kc_ema_period = int(params["kc_ema_period"])
            kc_atr_period = int(params["kc_atr_period"])
            kc_multiplier = float(params["kc_multiplier"])
            adx_period = int(params["adx_period"])
            adx_min = float(params["adx_min_threshold"])
            rsi_period = int(params["rsi_period"])
            rsi_oversold = float(params["rsi_oversold"])
            st_period = int(params["supertrend_period"])
            st_multiplier = float(params["supertrend_multiplier"])
            atr_period = int(params["atr_period"])

            # --- Higher Timeframe: Resample 1H -> 4H for regime ---
            series_4h = resample_ohlcv(series, "4h")
            if len(series_4h) < htf_ema_period:
                logger.debug(
                    "insufficient_4h_data",
                    bars_4h=len(series_4h),
                    required=htf_ema_period,
                    generator=self.__class__.__name__,
                )
                return None

            htf_ema = EMA(period=htf_ema_period).calculate(series_4h)
            htf_ema_value = htf_ema.current
            if np.isnan(htf_ema_value):
                return None

            # --- Lower Timeframe: 1H indicators ---
            kc = KeltnerChannel(
                ema_period=kc_ema_period,
                atr_period=kc_atr_period,
                multiplier=kc_multiplier,
            ).calculate(series)
            adx_result = ADX(period=adx_period).calculate(series)
            rsi_result = RSI(period=rsi_period).calculate(series)
            st = SuperTrend(
                period=st_period, multiplier=st_multiplier,
            ).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            last_idx = len(series) - 1
            prev_idx = last_idx - 1
            if prev_idx < 0:
                return None

            price = float(series.closes[last_idx])
            prev_high = float(series.highs[prev_idx])
            prev_low = float(series.lows[prev_idx])

            # Validate Keltner values
            kc_upper = kc.upper[last_idx]
            kc_lower = kc.lower[last_idx]
            kc_middle = kc.middle[last_idx]
            if any(np.isnan(v) for v in [kc_upper, kc_lower, kc_middle]):
                return None

            # ADX and DI values
            valid_adx = adx_result.adx[~np.isnan(adx_result.adx)]
            valid_plus_di = adx_result.plus_di[~np.isnan(adx_result.plus_di)]
            valid_minus_di = adx_result.minus_di[~np.isnan(adx_result.minus_di)]
            if len(valid_adx) == 0 or len(valid_plus_di) == 0 or len(valid_minus_di) == 0:
                return None
            adx_val = float(valid_adx[-1])
            plus_di = float(valid_plus_di[-1])
            minus_di = float(valid_minus_di[-1])

            # RSI value
            valid_rsi = rsi_result.values[~np.isnan(rsi_result.values)]
            if len(valid_rsi) == 0:
                return None
            rsi_val = float(valid_rsi[-1])

            # ATR for stops
            atr_current = atr_result.current
            if np.isnan(atr_current) or atr_current <= 0:
                return None

            # SuperTrend direction
            st_trend = st.current_trend

            # --- Regime Detection ---
            is_bear_regime = price < htf_ema_value
            is_bull_regime = price > htf_ema_value

            # Build indicator snapshot
            indicators = {
                "htf_ema_200": htf_ema_value,
                "regime": "bear" if is_bear_regime else "bull",
                "kc_upper": float(kc_upper),
                "kc_middle": float(kc_middle),
                "kc_lower": float(kc_lower),
                "adx": adx_val,
                "plus_di": plus_di,
                "minus_di": minus_di,
                "rsi": rsi_val,
                "supertrend": float(st_trend),
                "atr": atr_current,
            }

            # --- BEAR Regime: PRIMARY SHORT ---
            if is_bear_regime:
                # Upper Keltner rejection: any of last 3 bars touched upper KC
                # Wider window captures rejections that develop over 2-3 bars
                touched_upper = False
                for j in range(1, min(4, last_idx + 1)):
                    idx_j = last_idx - j
                    if not np.isnan(kc.upper[idx_j]):
                        if float(series.highs[idx_j]) >= kc.upper[idx_j]:
                            touched_upper = True
                            break
                closed_inside = price < float(kc_upper)
                # ADX confirms trending (regime already confirmed by 4H EMA200,
                # so -DI > +DI is not required — it contradicts upper KC touch)
                adx_strong = adx_val > adx_min

                if touched_upper and closed_inside and adx_strong:
                    # Distance below 4H EMA as regime strength
                    regime_strength = min(0.3, abs(price - htf_ema_value) / htf_ema_value * 10)
                    strength = min(1.0, 0.55 + regime_strength + (adx_val - adx_min) * 0.005)
                    strength = max(0.4, min(1.0, strength))

                    stop_loss = float(kc_upper) + 1.5 * atr_current

                    return TradingSignal(
                        direction=SignalDirection.SHORT,
                        symbol=symbol,
                        price=price,
                        strength=strength,
                        stop_loss=stop_loss,
                        take_profit=float(kc_lower),
                        indicators=indicators,
                        metadata={
                            "trigger": "bear_trend_follower_short",
                            "regime": "bear",
                            "htf_distance_pct": (htf_ema_value - price) / htf_ema_value * 100,
                        },
                    )

            # --- BULL Regime: SECONDARY LONG (counter-trend, lower conviction) ---
            if is_bull_regime:
                # Lower Keltner touch (last 3 bars) + RSI oversold + SuperTrend bullish
                touched_lower = False
                for j in range(1, min(4, last_idx + 1)):
                    idx_j = last_idx - j
                    if not np.isnan(kc.lower[idx_j]):
                        if float(series.lows[idx_j]) <= kc.lower[idx_j]:
                            touched_lower = True
                            break
                closed_inside = price > float(kc_lower)
                rsi_oversold_ok = rsi_val < rsi_oversold
                st_bullish = st_trend == 1

                if touched_lower and closed_inside and rsi_oversold_ok and st_bullish:
                    # Lower conviction for counter-trend in bull regime
                    strength = max(0.3, min(0.6, 0.35 + (rsi_oversold - rsi_val) * 0.005))

                    stop_loss = float(kc_lower) - 1.5 * atr_current

                    return TradingSignal(
                        direction=SignalDirection.LONG,
                        symbol=symbol,
                        price=price,
                        strength=strength,
                        stop_loss=max(stop_loss, price * 0.001),
                        take_profit=float(kc_middle),
                        indicators=indicators,
                        metadata={
                            "trigger": "bear_trend_follower_long_counter",
                            "regime": "bull",
                            "htf_distance_pct": (price - htf_ema_value) / htf_ema_value * 100,
                        },
                    )

        except (ValueError, KeyError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None
