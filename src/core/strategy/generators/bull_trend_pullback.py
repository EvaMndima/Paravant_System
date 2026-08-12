"""Bull Trend Pullback signal generator.

Long-only trend continuation strategy for confirmed bull regimes.
Enters on RSI pullbacks within an established uptrend, confirmed
by MACD histogram and dual EMA regime filter.

Regime gate (BOTH conditions required for any entry):
    price > EMA(htf_ema_period)   -- above long-term trend
    EMA(trend_ema_period) > EMA(htf_ema_period)  -- trend EMA above baseline

Entry (LONG only):
    1. RSI(rsi_period) has pulled back to [rsi_pullback_low, rsi_pullback_high]
    2. RSI is turning up (current > previous bar) -- confirms pullback end
    3. MACD histogram > 0 -- underlying bull momentum intact
    4. Price > EMA(trend_ema_period) -- still riding the trend

Exit:
    Stop loss: ATR(atr_period) * atr_stop_multiplier below entry
    Take profit: entry + risk * risk_reward_ratio

Template ID: bull_trend_pullback
Strategy Type: trend_continuation (long-only)
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import ATR, EMA, MACD, RSI
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BullTrendPullbackGenerator(SignalGenerator):
    """Signal generator for the Bull Trend Pullback strategy.

    Long-only. Designed for confirmed bull regimes where price is above
    EMA(200) and the medium-term EMA(50) is also above EMA(200).

    Entries fire only when RSI has pulled back to a consolidation zone
    and is beginning to recover, while MACD histogram remains positive.
    This selects the confirmation bar of a pullback end rather than
    trying to catch the exact bottom.

    Required parameters:
        htf_ema_period, trend_ema_period,
        rsi_period, rsi_pullback_low, rsi_pullback_high,
        macd_fast, macd_slow, macd_signal,
        atr_period, atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        """Return template ID."""
        return "bull_trend_pullback"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars required.

        EMA(200) warmup (200) + ATR buffer (14) + extra (10) = 224.
        """
        return 224

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate Bull Trend Pullback entry conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal (LONG) if pullback entry conditions met, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            htf_ema_period: int = int(params["htf_ema_period"])
            trend_ema_period: int = int(params["trend_ema_period"])
            rsi_period: int = int(params["rsi_period"])
            rsi_low: float = float(params["rsi_pullback_low"])
            rsi_high: float = float(params["rsi_pullback_high"])
            macd_fast: int = int(params["macd_fast"])
            macd_slow: int = int(params["macd_slow"])
            macd_signal_period: int = int(params["macd_signal"])
            atr_period: int = int(params["atr_period"])
            atr_stop_mult: float = float(params["atr_stop_multiplier"])
            rr_ratio: float = float(params["risk_reward_ratio"])

            # Calculate indicators
            htf_ema = EMA(period=htf_ema_period).calculate(series)
            trend_ema = EMA(period=trend_ema_period).calculate(series)
            rsi_result = RSI(period=rsi_period).calculate(series)
            macd_result = MACD(
                fast_period=macd_fast,
                slow_period=macd_slow,
                signal_period=macd_signal_period,
            ).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            price = float(series.closes[-1])
            htf_ema_val = htf_ema.current
            trend_ema_val = trend_ema.current

            if np.isnan(htf_ema_val) or np.isnan(trend_ema_val):
                return None

            # --- Regime gate: both EMA conditions must hold ---
            if price <= htf_ema_val:
                return None
            if trend_ema_val <= htf_ema_val:
                return None

            # --- RSI: current and previous for turn-up detection ---
            valid_rsi = rsi_result.values[~np.isnan(rsi_result.values)]
            if len(valid_rsi) < 2:
                return None
            rsi_curr = float(valid_rsi[-1])
            rsi_prev = float(valid_rsi[-2])

            # --- MACD histogram (last valid value) ---
            valid_hist = macd_result.histogram[~np.isnan(macd_result.histogram)]
            if len(valid_hist) == 0:
                return None
            hist_curr = float(valid_hist[-1])

            # --- ATR for stop sizing ---
            atr_val = atr_result.current
            if np.isnan(atr_val) or atr_val <= 0:
                return None

            indicators: dict[str, float | str] = {
                "htf_ema": htf_ema_val,
                "trend_ema": trend_ema_val,
                "rsi": rsi_curr,
                "rsi_prev": rsi_prev,
                "macd_histogram": hist_curr,
                "atr": atr_val,
                "regime": "bull",
            }

            # --- LONG entry: RSI pullback zone + RSI turning up + MACD hist > 0 ---
            rsi_in_zone = rsi_low <= rsi_curr <= rsi_high
            rsi_turning_up = rsi_curr > rsi_prev
            macd_positive = hist_curr > 0
            price_above_trend = price > trend_ema_val

            if rsi_in_zone and rsi_turning_up and macd_positive and price_above_trend:
                stop_loss = price - (atr_stop_mult * atr_val)
                risk = price - stop_loss
                take_profit = price + (risk * rr_ratio) if risk > 0 else None

                strength = min(
                    1.0,
                    0.5 + (rsi_high - rsi_curr) / (rsi_high - rsi_low) * 0.3
                    + min(0.2, hist_curr / (atr_val + 1e-9) * 0.1),
                )

                return TradingSignal(
                    direction=SignalDirection.LONG,
                    symbol=symbol,
                    price=price,
                    strength=max(0.3, strength),
                    stop_loss=max(stop_loss, price * 0.001),
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={
                        "trigger": "bull_trend_pullback_long",
                        "rsi_zone": f"{rsi_low:.0f}-{rsi_high:.0f}",
                        "trend_distance_pct": (price - trend_ema_val) / trend_ema_val * 100,
                    },
                )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None
