"""Keltner Channel Continuation signal generator.

In a confirmed bull trend, closing ABOVE the upper Keltner Channel is a
trend continuation signal — not an overbought warning. The Keltner Channel
is defined as EMA(kc_ema) +/- ATR(kc_atr) * multiplier. Closing above the
upper band means price has moved more than N ATRs above the trend EMA.

Counter-intuitive quant insight: Most textbook uses of Keltner Channels
treat a close above the upper band as "overbought" and fade it. This is
correct in range-bound markets. In trending markets, it is the opposite:
closing above the upper band indicates the trend has enough force to push
through its normal volatility envelope. The first close above the upper KC
during a confirmed bull trend is typically the beginning of a sustained
momentum phase — not its end.

The key distinction from KFA (Keltner Fade ADX): KFA fades when price
TOUCHES the band and closes back INSIDE (rejection). KCC BUYS when price
CLOSES OUTSIDE the band (breakout). Same indicator family, opposite regime,
opposite signal type.

Entry conditions (LONG only — bull regime strategy):
    1. Price above EMA(regime_ema_period) — macro bull context
    2. Price closes ABOVE upper KC (kc_ema + kc_mult * ATR) — band escape
    3. Previous bar was inside or at the upper KC — this is the first breakout
       bar, not a continuation of an existing above-band run
    4. RSI in [rsi_min, rsi_max] — not overbought, has fuel to run
    5. Volume >= vol_ma * volume_threshold — breakout has participation

Template ID: keltner_channel_continuation
Strategy Type: volatility_breakout
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import ATR, EMA, KeltnerChannel, RSI
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class KeltnerChannelContinuationGenerator(SignalGenerator):
    """Signal generator for Keltner Channel Continuation strategy.

    Buys the first close above the upper Keltner Channel in a confirmed
    bull regime. This identifies the transition from normal trend behavior
    to accelerated momentum — the band escape moment.

    Required parameters:
        kc_ema_period, kc_atr_period, kc_multiplier,
        regime_ema_period,
        rsi_period, rsi_min, rsi_max,
        volume_period, volume_threshold,
        atr_period, atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        return "keltner_channel_continuation"

    @property
    def min_bars_required(self) -> int:
        """EMA(200) warmup + KC(EMA-20 + ATR-14) warmup + buffer."""
        return 230

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate Keltner Channel Continuation entry conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if price just closed above upper KC in a bull
            regime with volume confirmation, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            kc_ema_period: int      = int(params["kc_ema_period"])
            kc_atr_period: int      = int(params["kc_atr_period"])
            kc_multiplier: float    = float(params["kc_multiplier"])
            regime_ema_period: int  = int(params.get("regime_ema_period", 0))
            rsi_period: int         = int(params["rsi_period"])
            rsi_min: float          = float(params["rsi_min"])
            rsi_max: float          = float(params["rsi_max"])
            kc_reset_bars: int      = int(params.get("kc_reset_bars", 1))
            volume_period: int      = int(params["volume_period"])
            volume_threshold: float = float(params["volume_threshold"])
            atr_period: int         = int(params["atr_period"])
            atr_stop_mult: float    = float(params["atr_stop_multiplier"])
            rr_ratio: float         = float(params["risk_reward_ratio"])

            kc_result  = KeltnerChannel(
                ema_period=kc_ema_period,
                atr_period=kc_atr_period,
                multiplier=kc_multiplier,
            ).calculate(series)
            rsi_result = RSI(period=rsi_period).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            last_idx = len(series) - 1

            kc_upper_curr = kc_result.upper[last_idx]
            if np.isnan(kc_upper_curr):
                return None

            rsi_vals = rsi_result.values[~np.isnan(rsi_result.values)]
            atr_vals = atr_result.values[~np.isnan(atr_result.values)]

            if len(rsi_vals) < 1 or len(atr_vals) < 1:
                return None

            price    = float(series.closes[last_idx])
            rsi_curr = float(rsi_vals[-1])
            atr_curr = float(atr_vals[-1])

            # Macro bull gate: only trade in confirmed macro uptrend
            if regime_ema_period > 0 and len(series) >= regime_ema_period:
                regime_ema = EMA(period=regime_ema_period).calculate(series)
                regime_vals = regime_ema.values[~np.isnan(regime_ema.values)]
                if len(regime_vals) >= 1 and price <= float(regime_vals[-1]):
                    return None

            # Band escape: current bar closes ABOVE upper KC
            if price <= float(kc_upper_curr):
                return None

            # Reset confirmation: the last kc_reset_bars must ALL be inside the KC.
            # A single-bar reset (kc_reset_bars=1) allows re-entries after every
            # brief 1-bar dip inside the band — too frequent in trending markets.
            # Requiring N consecutive inside-bars ensures the KC has had time to
            # "absorb" the previous breakout before a new one is valid.
            if kc_reset_bars < 1:
                kc_reset_bars = 1
            needed_idx = last_idx - kc_reset_bars
            if needed_idx < 0:
                return None
            for j in range(1, kc_reset_bars + 1):
                idx_j = last_idx - j
                kc_upper_j = kc_result.upper[idx_j]
                if np.isnan(kc_upper_j):
                    return None
                if float(series.closes[idx_j]) > float(kc_upper_j):
                    return None

            # RSI zone: has momentum but not in exhaustion territory.
            # rsi_max=78 allows the full RSI acceleration zone in bull markets.
            if not (rsi_min <= rsi_curr <= rsi_max):
                return None

            # Volume: breakout must have above-average participation
            vols = series.volumes[~np.isnan(series.volumes)]
            if len(vols) < volume_period + 1:
                return None
            vol_ma   = float(np.mean(vols[-(volume_period + 1):-1]))
            vol_curr = float(vols[-1])
            if vol_ma <= 0 or vol_curr <= vol_ma * volume_threshold:
                return None

            # How far above the band is the close?
            band_escape = (price - float(kc_upper_curr)) / float(kc_upper_curr) * 100.0
            strength_base = min(
                1.0,
                0.55
                + min(0.15, band_escape * 0.5)
                + min(0.15, (vol_curr / vol_ma - volume_threshold) * 0.1)
                + min(0.1, (rsi_curr - rsi_min) / (rsi_max - rsi_min) * 0.1),
            )

            # Stop at the KC midline (EMA) — if price drops back below the
            # midline, the breakout has failed and the channel structure is lost
            kc_middle = float(kc_result.middle[last_idx])
            if not np.isnan(kc_middle) and kc_middle < price:
                stop_loss = max(kc_middle, price - atr_stop_mult * atr_curr)
            else:
                stop_loss = price - atr_stop_mult * atr_curr

            take_profit = price + abs(price - stop_loss) * rr_ratio

            return TradingSignal(
                direction=SignalDirection.LONG,
                symbol=symbol,
                price=price,
                strength=max(0.4, strength_base),
                stop_loss=max(stop_loss, price * 0.001),
                take_profit=take_profit,
                indicators={
                    "kc_upper": round(float(kc_upper_curr), 4),
                    "kc_middle": round(kc_middle, 4) if not np.isnan(kc_middle) else 0.0,
                    "band_escape_pct": round(band_escape, 3),
                    "rsi": round(rsi_curr, 1),
                    "volume_ratio": round(vol_curr / vol_ma, 2),
                    "atr": atr_curr,
                },
                metadata={
                    "trigger": "kcc_long_kc_band_escape",
                    "band_escape_pct": round(band_escape, 3),
                    "vol_ratio": round(vol_curr / vol_ma, 2),
                },
            )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e
