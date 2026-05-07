"""Multi-Timeframe Confluence signal generator.

Requires trend alignment across three timeframes before entering:
Daily EMA direction + 4H MACD momentum + 1H RSI pullback entry.
Reduces false signals by ensuring macro and medium-term context
agree before acting on short-term pullback entries.

Entry conditions (LONG):
    1. Daily: price > EMA(daily_ema_period) AND EMA is rising
    2. 4H: MACD histogram > 0 AND expanding (histogram growing)
    3. 1H: RSI in [rsi_pullback_min, rsi_pullback_max] AND RSI turning up

SHORT conditions are the symmetric inverse:
    1. Daily: price < EMA(daily_ema_period) AND EMA is falling
    2. 4H: MACD histogram < 0 AND shrinking (histogram more negative)
    3. 1H: RSI in [100-rsi_pullback_max, 100-rsi_pullback_min] AND RSI turning down

Template ID: multi_tf_confluence
Strategy Type: trend_following
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import ATR, EMA, MACD, RSI
from src.core.indicators.resample import resample_ohlcv
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MultiTfConfluenceGenerator(SignalGenerator):
    """Signal generator for Multi-Timeframe Confluence strategy.

    Aligns daily trend (EMA direction), 4H momentum (MACD histogram
    sign and slope), and 1H entry timing (RSI pullback zone with
    reversal confirmation). Three-timeframe agreement sharply reduces
    false entries during choppy or counter-trend periods.

    Required parameters:
        daily_ema_period, macd_fast, macd_slow, macd_signal,
        rsi_period, rsi_pullback_min, rsi_pullback_max,
        atr_period, atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        """Return template ID."""
        return "multi_tf_confluence"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars needed.

        21 daily candles * 24 = 504 1H bars + MACD warmup buffer = 550.
        """
        return 550

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate Multi-Timeframe Confluence entry conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if all three timeframes align, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation or resample fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            daily_ema_period: int = int(params["daily_ema_period"])
            macd_fast: int = int(params["macd_fast"])
            macd_slow: int = int(params["macd_slow"])
            macd_signal_period: int = int(params["macd_signal"])
            rsi_period: int = int(params["rsi_period"])
            rsi_pb_min: float = float(params["rsi_pullback_min"])
            rsi_pb_max: float = float(params["rsi_pullback_max"])
            atr_period: int = int(params["atr_period"])
            atr_stop_mult: float = float(params["atr_stop_multiplier"])
            rr_ratio: float = float(params["risk_reward_ratio"])

            series_daily = resample_ohlcv(series, "1d")
            series_4h = resample_ohlcv(series, "4h")

            # Daily EMA — trend direction gate
            daily_ema = EMA(period=daily_ema_period).calculate(series_daily)
            daily_ema_vals = daily_ema.values[~np.isnan(daily_ema.values)]
            if len(daily_ema_vals) < 2:
                return None

            daily_price = float(series_daily.closes[-1])
            daily_ema_curr = float(daily_ema_vals[-1])
            daily_ema_prev = float(daily_ema_vals[-2])
            daily_ema_rising = daily_ema_curr > daily_ema_prev

            # 4H MACD histogram — momentum sign and direction
            macd_4h = MACD(
                fast_period=macd_fast,
                slow_period=macd_slow,
                signal_period=macd_signal_period,
            ).calculate(series_4h)
            hist_4h_vals = macd_4h.histogram[~np.isnan(macd_4h.histogram)]
            if len(hist_4h_vals) < 1:
                return None

            hist_4h_curr = float(hist_4h_vals[-1])

            # 1H RSI — entry timing within pullback zone
            rsi_1h = RSI(period=rsi_period).calculate(series)
            rsi_1h_vals = rsi_1h.values[~np.isnan(rsi_1h.values)]
            if len(rsi_1h_vals) < 2:
                return None

            rsi_curr = float(rsi_1h_vals[-1])
            rsi_prev = float(rsi_1h_vals[-2])

            atr_1h = ATR(period=atr_period).calculate(series)
            atr_curr = float(atr_1h.current)
            price = float(series.closes[-1])

            indicators = {
                "daily_ema": round(daily_ema_curr, 4),
                "daily_price": daily_price,
                "daily_ema_rising": daily_ema_rising,
                "hist_4h": round(hist_4h_curr, 6),
                "rsi_1h": round(rsi_curr, 2),
                "atr": atr_curr,
            }

            # --- LONG: daily bull + 4H histogram positive (sign only) + 1H RSI pullback ---
            daily_bull = daily_price > daily_ema_curr and daily_ema_rising
            macd_4h_bullish = hist_4h_curr > 0
            rsi_pullback_long = rsi_pb_min <= rsi_curr <= rsi_pb_max and rsi_curr > rsi_prev

            if daily_bull and macd_4h_bullish and rsi_pullback_long:
                risk = atr_stop_mult * atr_curr
                stop_loss = price - risk
                take_profit = price + risk * rr_ratio

                rsi_zone_pct = (rsi_curr - rsi_pb_min) / (rsi_pb_max - rsi_pb_min + 1e-9)
                strength = min(1.0, 0.6 + min(0.25, rsi_zone_pct * 0.25) + min(0.15, abs(hist_4h_curr) * 0.01))

                return TradingSignal(
                    direction=SignalDirection.LONG,
                    symbol=symbol,
                    price=price,
                    strength=max(0.4, strength),
                    stop_loss=max(stop_loss, price * 0.001),
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={
                        "trigger": "mtc_long_confluence",
                        "daily_trend": "bull",
                        "hist_4h": round(hist_4h_curr, 6),
                        "rsi_1h": round(rsi_curr, 2),
                    },
                )

            # --- SHORT: daily bear + 4H histogram negative (sign only) + 1H RSI pullback ---
            daily_bear = daily_price < daily_ema_curr and not daily_ema_rising
            macd_4h_bearish = hist_4h_curr < 0
            rsi_short_min = 100.0 - rsi_pb_max
            rsi_short_max = 100.0 - rsi_pb_min
            rsi_pullback_short = rsi_short_min <= rsi_curr <= rsi_short_max and rsi_curr < rsi_prev

            if daily_bear and macd_4h_bearish and rsi_pullback_short:
                risk = atr_stop_mult * atr_curr
                stop_loss = price + risk
                take_profit = price - risk * rr_ratio

                rsi_zone_pct = (rsi_short_max - rsi_curr) / (rsi_short_max - rsi_short_min + 1e-9)
                strength = min(1.0, 0.6 + min(0.25, rsi_zone_pct * 0.25) + min(0.15, abs(hist_4h_curr) * 0.01))

                return TradingSignal(
                    direction=SignalDirection.SHORT,
                    symbol=symbol,
                    price=price,
                    strength=max(0.4, strength),
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={
                        "trigger": "mtc_short_confluence",
                        "daily_trend": "bear",
                        "hist_4h": round(hist_4h_curr, 6),
                        "rsi_1h": round(rsi_curr, 2),
                    },
                )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None
