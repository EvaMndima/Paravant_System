"""ADX Directional Thrust signal generator.

Uses the Average Directional Index (ADX) system — specifically the
+DI/-DI directional movement spread — as the primary signal. When ADX
is above a threshold AND rising (trend is strengthening) AND +DI exceeds
-DI by a minimum margin, buyers are decisively overpowering sellers in
a trend that is gaining momentum.

Quant basis: ADX has two orthogonal components: (1) ADX value = trend
intensity regardless of direction; (2) +DI/-DI = directional conviction.
Most strategies use ADX only as a filter (e.g., KFA: fade when ADX is low,
BTF: enter when ADX > 20). ADT uses the full DI system as the entry signal:
ADX level + ADX slope (rising = accelerating trend) + +DI/-DI spread
(buyers winning by a margin).

The "rising ADX" condition is critical and often overlooked: an ADX of 25
that was 20 three bars ago means the trend is in its acceleration phase —
the best phase to enter. An ADX of 25 that was 35 three bars ago means the
trend is fading — the worst phase to enter.

Entry conditions (LONG only — bull regime strategy):
    1. Price above EMA(regime_ema_period) — macro bull context
    2. Price above EMA(ema_period) — intermediate trend intact
    3. ADX(adx_period) > adx_threshold — trend has sufficient strength
    4. ADX rising: ADX_curr > ADX adx_rise_bars ago — trend accelerating
    5. +DI > -DI + di_min_spread — bullish directional dominance
    6. RSI in [rsi_min, rsi_max] — not bearish, not overbought
    7. Volume >= vol_ma * volume_threshold — participation confirmation

Template ID: adx_directional_thrust
Strategy Type: trend_continuation
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import ADX, ATR, EMA, RSI
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AdxDirectionalThrustGenerator(SignalGenerator):
    """Signal generator for ADX Directional Thrust strategy.

    Enters longs when the ADX system confirms a strengthening bull trend:
    ADX above threshold, ADX rising (not plateauing), and +DI dominant
    over -DI by a meaningful margin. This captures the trend acceleration
    phase rather than mature or fading trends.

    Required parameters:
        adx_period, adx_threshold, adx_rise_bars, di_min_spread,
        ema_period, regime_ema_period,
        rsi_period, rsi_min, rsi_max,
        volume_period, volume_threshold,
        atr_period, atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        return "adx_directional_thrust"

    @property
    def min_bars_required(self) -> int:
        """EMA(200) warmup + ADX warmup (~3x period) + rise lookback + buffer."""
        return 230

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate ADX Directional Thrust entry conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if ADX system confirms accelerating bull trend
            with +DI dominance, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            adx_period: int         = int(params["adx_period"])
            adx_threshold: float    = float(params["adx_threshold"])
            adx_rise_bars: int      = int(params["adx_rise_bars"])
            di_min_spread: float    = float(params["di_min_spread"])
            ema_period: int         = int(params["ema_period"])
            regime_ema_period: int  = int(params.get("regime_ema_period", 0))
            rsi_period: int         = int(params["rsi_period"])
            rsi_min: float          = float(params["rsi_min"])
            rsi_max: float          = float(params["rsi_max"])
            volume_period: int      = int(params["volume_period"])
            volume_threshold: float = float(params["volume_threshold"])
            atr_period: int         = int(params["atr_period"])
            atr_stop_mult: float    = float(params["atr_stop_multiplier"])
            rr_ratio: float         = float(params["risk_reward_ratio"])

            ema_result = EMA(period=ema_period).calculate(series)
            rsi_result = RSI(period=rsi_period).calculate(series)
            adx_result = ADX(period=adx_period).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            ema_vals = ema_result.values[~np.isnan(ema_result.values)]
            rsi_vals = rsi_result.values[~np.isnan(rsi_result.values)]
            adx_vals = adx_result.adx[~np.isnan(adx_result.adx)]
            dip_vals = adx_result.plus_di[~np.isnan(adx_result.plus_di)]
            dim_vals = adx_result.minus_di[~np.isnan(adx_result.minus_di)]
            atr_vals = atr_result.values[~np.isnan(atr_result.values)]

            min_adx_needed = adx_rise_bars + 1
            if (
                len(ema_vals) < 1
                or len(rsi_vals) < 1
                or len(adx_vals) < min_adx_needed
                or len(dip_vals) < 1
                or len(dim_vals) < 1
                or len(atr_vals) < 1
            ):
                return None

            price    = float(series.closes[-1])
            ema_curr = float(ema_vals[-1])

            # Intermediate trend gate: price above EMA(ema_period)
            if price <= ema_curr:
                return None

            # Macro bull gate: restrict to confirmed macro uptrend
            if regime_ema_period > 0 and len(series) >= regime_ema_period:
                regime_ema = EMA(period=regime_ema_period).calculate(series)
                regime_vals = regime_ema.values[~np.isnan(regime_ema.values)]
                if len(regime_vals) >= 1 and price <= float(regime_vals[-1]):
                    return None

            adx_curr = float(adx_vals[-1])
            adx_past = float(adx_vals[-adx_rise_bars - 1])
            dip_curr = float(dip_vals[-1])
            dim_curr = float(dim_vals[-1])
            rsi_curr = float(rsi_vals[-1])
            atr_curr = float(atr_vals[-1])

            # ADX level: trend must have sufficient strength
            if adx_curr < adx_threshold:
                return None

            # ADX rising: trend is in acceleration phase, not plateauing/fading.
            # A rising ADX confirms new buyers are entering, not just existing
            # positions being held.
            if adx_curr <= adx_past:
                return None

            # Directional dominance: +DI must exceed -DI by minimum spread.
            # A spread of 8+ points means buyers are winning by a decisive
            # margin — not just slightly ahead.
            if (dip_curr - dim_curr) < di_min_spread:
                return None

            # RSI zone: momentum positive (not bearish) and not extended
            if not (rsi_min <= rsi_curr <= rsi_max):
                return None

            # Volume: above-average participation
            vols = series.volumes[~np.isnan(series.volumes)]
            if len(vols) < volume_period + 1:
                return None
            vol_ma   = float(np.mean(vols[-(volume_period + 1):-1]))
            vol_curr = float(vols[-1])
            if vol_ma <= 0 or vol_curr <= vol_ma * volume_threshold:
                return None

            # Signal strength: ADX level + ADX rise rate + DI spread + volume
            adx_excess      = adx_curr - adx_threshold
            adx_rise_rate   = adx_curr - adx_past
            di_excess       = (dip_curr - dim_curr) - di_min_spread
            strength_base   = min(
                1.0,
                0.55
                + min(0.15, adx_excess * 0.01)
                + min(0.1, adx_rise_rate * 0.02)
                + min(0.1, di_excess * 0.01)
                + min(0.1, (vol_curr / vol_ma - volume_threshold) * 0.05),
            )

            risk        = atr_stop_mult * atr_curr
            stop_loss   = price - risk
            take_profit = price + risk * rr_ratio

            return TradingSignal(
                direction=SignalDirection.LONG,
                symbol=symbol,
                price=price,
                strength=max(0.4, strength_base),
                stop_loss=max(stop_loss, price * 0.001),
                take_profit=take_profit,
                indicators={
                    "adx": round(adx_curr, 2),
                    "adx_past": round(adx_past, 2),
                    "adx_rise": round(adx_curr - adx_past, 2),
                    "di_plus": round(dip_curr, 2),
                    "di_minus": round(dim_curr, 2),
                    "di_spread": round(dip_curr - dim_curr, 2),
                    "rsi": round(rsi_curr, 1),
                    "ema_trend": round(ema_curr, 4),
                    "volume_ratio": round(vol_curr / vol_ma, 2),
                    "atr": atr_curr,
                },
                metadata={
                    "trigger": "adt_long_adx_directional_thrust",
                    "adx": round(adx_curr, 2),
                    "di_spread": round(dip_curr - dim_curr, 2),
                    "adx_rising": round(adx_curr - adx_past, 2),
                },
            )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e
