"""Heikin-Ashi Trend Pulse signal generator.

Heikin-Ashi (HA) candles smooth price noise using averaged values:
    HA_Close = (Open + High + Low + Close) / 4
    HA_Open  = (prev_HA_Open + prev_HA_Close) / 2
    HA_High  = max(High, HA_Open, HA_Close)
    HA_Low   = min(Low, HA_Open, HA_Close)

A HA candle with NO lower wick (HA_Low == HA_Open) means the entire session
was monotonically positive with no intrabar reversal -- a "pure bull bar."

The signal: after N bars of HA candles WITH lower wicks (normal pullback /
consolidation), the first bar where the HA lower wick disappears (transitions
to a pure bull bar) signals re-entry into the strong bull phase.

Crypto-specific advantage: Crypto's 24/7 equal-time candles have no overnight
gap contamination, making HA smoothing cleaner than in equities. HA signals
also filter crypto's high-frequency microstructure noise while preserving the
trend direction signal. (Sakowski et al. 2019 -- HA outperforms standard
candles in crypto trending regimes.)

Entry conditions (LONG only -- bull regime strategy):
    1. Price above EMA(regime_ema_period) -- macro bull context
    2. Price above EMA(ema_period) -- intermediate trend intact
    3. Current HA candle is bullish (HA_Close > HA_Open)
    4. Current HA candle has no lower wick or tiny lower wick
       (HA_Low >= HA_Open - wick_tolerance * HA_body)
    5. At least ha_wick_lookback of the prior bars had lower wicks
       (confirming prior pullback before this pulse)
    6. RSI in [rsi_min, rsi_max] -- momentum supporting
    7. Volume >= vol_ma * volume_threshold -- participation confirmed

Template ID: heikin_ashi_trend_pulse
Strategy Type: trend_continuation
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


class HeikinAshiTrendPulseGenerator(SignalGenerator):
    """Signal generator for Heikin-Ashi Trend Pulse strategy.

    Detects the first "pure bull bar" (no lower wick on HA candle) after a
    period of HA candles with lower wicks, confirming re-entry into the strong
    bull phase following a pullback or consolidation.

    Required parameters:
        ha_wick_lookback, ha_prior_wick_min, wick_tolerance,
        ema_period, regime_ema_period,
        rsi_period, rsi_min, rsi_max,
        volume_period, volume_threshold,
        atr_period, atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        return "heikin_ashi_trend_pulse"

    @property
    def min_bars_required(self) -> int:
        """EMA(200) warmup + HA computation warmup + lookback + buffer."""
        return 230

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate Heikin-Ashi Trend Pulse entry conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if a HA no-lower-wick pulse occurs after a confirmed
            pullback in a macro bull trend, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            ha_wick_lookback: int       = int(params["ha_wick_lookback"])
            ha_prior_wick_min: int      = int(params["ha_prior_wick_min"])
            wick_tolerance: float       = float(params["wick_tolerance"])
            ema_period: int             = int(params["ema_period"])
            regime_ema_period: int      = int(params.get("regime_ema_period", 0))
            rsi_period: int             = int(params["rsi_period"])
            rsi_min: float              = float(params["rsi_min"])
            rsi_max: float              = float(params["rsi_max"])
            volume_period: int          = int(params["volume_period"])
            volume_threshold: float     = float(params["volume_threshold"])
            atr_period: int             = int(params["atr_period"])
            atr_stop_mult: float        = float(params["atr_stop_multiplier"])
            rr_ratio: float             = float(params["risk_reward_ratio"])

            # --- Indicator calculations ---
            ema_result = EMA(period=ema_period).calculate(series)
            rsi_result = RSI(period=rsi_period).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            ema_vals = ema_result.values[~np.isnan(ema_result.values)]
            rsi_vals = rsi_result.values[~np.isnan(rsi_result.values)]
            atr_vals = atr_result.values[~np.isnan(atr_result.values)]

            if len(ema_vals) < 1 or len(rsi_vals) < 1 or len(atr_vals) < 1:
                return None

            price    = float(series.closes[-1])
            ema_curr = float(ema_vals[-1])

            # Intermediate trend gate: price above EMA(ema_period)
            if price <= ema_curr:
                return None

            # Macro bull gate: price above EMA(regime_ema_period)
            if regime_ema_period > 0 and len(series) >= regime_ema_period:
                regime_ema = EMA(period=regime_ema_period).calculate(series)
                regime_vals = regime_ema.values[~np.isnan(regime_ema.values)]
                if len(regime_vals) >= 1 and price <= float(regime_vals[-1]):
                    return None

            rsi_curr = float(rsi_vals[-1])
            atr_curr = float(atr_vals[-1])

            # RSI gate: confirms momentum is within acceptable range
            if not (rsi_min <= rsi_curr <= rsi_max):
                return None

            # Volume gate: above-average participation, excludes current bar
            vols = series.volumes[~np.isnan(series.volumes)]
            if len(vols) < volume_period + 1:
                return None
            vol_ma   = float(np.mean(vols[-(volume_period + 1):-1]))
            vol_curr = float(vols[-1])
            if vol_ma <= 0 or vol_curr <= vol_ma * volume_threshold:
                return None

            # --- Heikin-Ashi computation over all available bars ---
            opens_arr  = series.opens
            highs_arr  = series.highs
            lows_arr   = series.lows
            closes_arr = series.closes
            n = len(closes_arr)

            ha_open  = np.zeros(n)
            ha_close = np.zeros(n)
            ha_high  = np.zeros(n)
            ha_low   = np.zeros(n)

            # Seed first HA bar with actual OHLC
            ha_open[0]  = float(opens_arr[0])
            ha_close[0] = (
                float(opens_arr[0]) + float(highs_arr[0])
                + float(lows_arr[0]) + float(closes_arr[0])
            ) / 4.0
            ha_high[0] = float(highs_arr[0])
            ha_low[0]  = float(lows_arr[0])

            for i in range(1, n):
                o = float(opens_arr[i])
                h = float(highs_arr[i])
                lo = float(lows_arr[i])
                c = float(closes_arr[i])
                if np.isnan(o) or np.isnan(h) or np.isnan(lo) or np.isnan(c):
                    ha_open[i]  = ha_open[i - 1]
                    ha_close[i] = ha_close[i - 1]
                    ha_high[i]  = ha_high[i - 1]
                    ha_low[i]   = ha_low[i - 1]
                    continue
                ha_close[i] = (o + h + lo + c) / 4.0
                ha_open[i]  = (ha_open[i - 1] + ha_close[i - 1]) / 2.0
                ha_high[i]  = max(h, ha_open[i], ha_close[i])
                ha_low[i]   = min(lo, ha_open[i], ha_close[i])

            last_idx = n - 1

            ha_c = ha_close[last_idx]
            ha_o = ha_open[last_idx]
            ha_l = ha_low[last_idx]

            # Current HA bar must be bullish
            ha_body = ha_c - ha_o
            if ha_body <= 0:
                return None

            # No lower wick on current bar: lower wick < wick_tolerance * body
            # Lower wick is measured as the distance from HA_Open down to HA_Low
            ha_lower_wick = ha_o - ha_l
            if ha_lower_wick > wick_tolerance * ha_body:
                return None

            # Prior bars must have had lower wicks (confirms prior pullback)
            if last_idx < ha_wick_lookback + 1:
                return None
            prior_wick_count = 0
            for j in range(1, ha_wick_lookback + 1):
                idx_j  = last_idx - j
                body_j = ha_close[idx_j] - ha_open[idx_j]
                if body_j <= 0:
                    # Bearish HA bar counts as having had a wick (reversal bar)
                    prior_wick_count += 1
                    continue
                wick_j = ha_open[idx_j] - ha_low[idx_j]
                if wick_j > wick_tolerance * body_j:
                    prior_wick_count += 1

            if prior_wick_count < ha_prior_wick_min:
                return None

            # --- Signal strength ---
            strength_base = min(
                1.0,
                0.55
                + min(0.15, (prior_wick_count / ha_wick_lookback) * 0.15)
                + min(0.1, (vol_curr / vol_ma - volume_threshold) * 0.1)
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
                    "ha_close": round(ha_c, 4),
                    "ha_open": round(ha_o, 4),
                    "ha_body": round(ha_body, 4),
                    "ha_lower_wick": round(ha_lower_wick, 4),
                    "prior_wick_bars": float(prior_wick_count),
                    "rsi": round(rsi_curr, 1),
                    "volume_ratio": round(vol_curr / vol_ma, 2),
                    "atr": atr_curr,
                },
                metadata={
                    "trigger": "hatp_long_ha_no_wick_pulse",
                    "prior_wick_bars": prior_wick_count,
                    "ha_body": round(ha_body, 4),
                },
            )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e
