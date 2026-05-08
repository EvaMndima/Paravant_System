"""Stop-hunt wick reversal signal generator -- crypto leverage cascade recovery.

Crypto's 24/7 leveraged markets create coordinated stop hunts: rapid price
spikes below obvious support levels trigger stop losses and liquidations,
followed by immediate recovery as buyers absorb the forced selling.

This appears as a 1H candle with a very long lower wick (wick >= 2.5x body)
that closes back in the upper portion of the candle range. The combination
of wick magnitude (>= 1.0 ATR absolute) + volume spike (>= 1.8x average)
+ close in upper half confirms stop-cascade absorption, not trend breakdown.

Crypto-specific: Equity markets have circuit breakers and T+2 settlement that
prevent this pattern. Crypto's 24/7, leveraged, no-circuit-breaker structure
creates systematic stop hunt dynamics (Jiang et al. 2021).

Entry conditions (LONG only -- bull regime strategy):
    1. Price above EMA(regime_ema_period) -- macro bull context
    2. Lower wick >= wick_body_ratio * body size (stop hunt signature)
    3. Lower wick >= wick_atr_min * ATR(atr_period) (substantial in absolute terms)
    4. Close >= midpoint of high-low range (closed in upper half)
    5. RSI in [rsi_min, rsi_max] -- real pullback, not overextended
    6. Volume >= vol_ma * volume_threshold -- cascade attracted volume

Template ID: crypto_wick_reversal
Strategy Type: reversal_momentum
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import ATR, EMA, RSI
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CryptoWickReversalGenerator(SignalGenerator):
    """Signal generator for the Crypto Wick Reversal strategy.

    Identifies leveraged stop-hunt events on 1H bars where an extremely long
    lower wick forms and price closes back in the upper half of the candle
    range, signalling that forced selling was fully absorbed by buyers.

    Required parameters:
        wick_body_ratio, wick_atr_min,
        regime_ema_period, ema_period,
        rsi_period, rsi_min, rsi_max,
        volume_period, volume_threshold,
        atr_period, atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        return "crypto_wick_reversal"

    @property
    def min_bars_required(self) -> int:
        """EMA(200) warmup + ATR(14) warmup + RSI(14) warmup + buffer."""
        return 230

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate Crypto Wick Reversal entry conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if a valid stop-hunt wick reversal is detected in a
            confirmed bull trend with volume confirmation, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            wick_body_ratio: float    = float(params["wick_body_ratio"])
            wick_atr_min: float       = float(params["wick_atr_min"])
            regime_ema_period: int    = int(params.get("regime_ema_period", 200))
            ema_period: int           = int(params["ema_period"])
            rsi_period: int           = int(params["rsi_period"])
            rsi_min: float            = float(params["rsi_min"])
            rsi_max: float            = float(params["rsi_max"])
            volume_period: int        = int(params["volume_period"])
            volume_threshold: float   = float(params["volume_threshold"])
            atr_period: int           = int(params["atr_period"])
            atr_stop_mult: float      = float(params["atr_stop_multiplier"])
            rr_ratio: float           = float(params["risk_reward_ratio"])

            ema_result = EMA(period=ema_period).calculate(series)
            rsi_result = RSI(period=rsi_period).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            ema_vals = ema_result.values[~np.isnan(ema_result.values)]
            rsi_vals = rsi_result.values[~np.isnan(rsi_result.values)]
            atr_vals = atr_result.values[~np.isnan(atr_result.values)]

            if len(ema_vals) < 1 or len(rsi_vals) < 1 or len(atr_vals) < 1:
                return None

            last_idx = len(series) - 1

            # Guard against NaN in OHLCV values for the current bar
            if (
                np.isnan(series.closes[last_idx])
                or np.isnan(series.opens[last_idx])
                or np.isnan(series.highs[last_idx])
                or np.isnan(series.lows[last_idx])
            ):
                return None

            price    = float(series.closes[last_idx])
            open_    = float(series.opens[last_idx])
            high_    = float(series.highs[last_idx])
            low_     = float(series.lows[last_idx])

            # Macro bull gate: price must be above the long-period regime EMA
            if regime_ema_period > 0 and len(series) >= regime_ema_period:
                regime_ema    = EMA(period=regime_ema_period).calculate(series)
                regime_vals   = regime_ema.values[~np.isnan(regime_ema.values)]
                if len(regime_vals) >= 1 and price <= float(regime_vals[-1]):
                    return None

            # Intermediate trend gate: price above EMA(ema_period)
            ema_curr = float(ema_vals[-1])
            if price <= ema_curr:
                return None

            # Candle anatomy
            body_size    = abs(price - open_)
            # Lower wick: distance from the lower of close/open down to the low
            lower_wick   = min(price, open_) - low_
            candle_range = high_ - low_

            # Require a meaningful body and range; avoid doji candles where
            # wick/body ratios are undefined and produce misleading signals
            if body_size < 1e-8 or candle_range < 1e-8:
                return None

            atr_curr = float(atr_vals[-1])

            # Wick conditions: stop-hunt signature requires both a large
            # relative wick and an absolutely significant wick vs. ATR
            if lower_wick < wick_body_ratio * body_size:
                return None
            if lower_wick < wick_atr_min * atr_curr:
                return None

            # Close must be in the upper half of the bar's range, confirming
            # that buyers absorbed all of the forced selling before close
            candle_midpoint = (high_ + low_) / 2.0
            if price < candle_midpoint:
                return None

            rsi_curr = float(rsi_vals[-1])

            # RSI filter: confirms a real pullback occurred but momentum is
            # not overextended upward at entry
            if not (rsi_min <= rsi_curr <= rsi_max):
                return None

            # Volume filter: stop cascades attract elevated volume; low-volume
            # wicks are more likely to be thin-market noise
            vols = series.volumes[~np.isnan(series.volumes)]
            if len(vols) < volume_period + 1:
                return None
            vol_ma   = float(np.mean(vols[-(volume_period + 1):-1]))
            vol_curr = float(vols[-1])
            if vol_ma <= 0 or vol_curr <= vol_ma * volume_threshold:
                return None

            # Signal strength: larger wick ratio, higher volume excess, and
            # better RSI positioning all increase confidence
            wick_ratio    = lower_wick / (body_size + 1e-8)
            strength_base = min(
                1.0,
                0.55
                + min(0.15, (wick_ratio - wick_body_ratio) * 0.05)
                + min(0.15, (vol_curr / vol_ma - volume_threshold) * 0.1)
                + min(0.1, (rsi_curr - rsi_min) / (rsi_max - rsi_min + 1e-8) * 0.1),
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
                    "lower_wick": round(lower_wick, 4),
                    "body_size": round(body_size, 4),
                    "wick_body_ratio": round(lower_wick / (body_size + 1e-8), 2),
                    "wick_atr_ratio": round(lower_wick / (atr_curr + 1e-8), 2),
                    "close_position_pct": round(
                        (price - low_) / (candle_range + 1e-8) * 100, 1
                    ),
                    "rsi": round(rsi_curr, 1),
                    "volume_ratio": round(vol_curr / vol_ma, 2),
                    "atr": atr_curr,
                },
                metadata={
                    "trigger": "cwr_long_wick_reversal",
                    "wick_body_ratio": round(lower_wick / (body_size + 1e-8), 2),
                    "vol_ratio": round(vol_curr / vol_ma, 2),
                },
            )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e
