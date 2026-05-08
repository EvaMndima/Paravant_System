"""OBV Trend Divergence signal generator -- institutional accumulation lead.

On-Balance Volume accumulates +volume on up bars and -volume on down bars,
creating a cumulative indicator that reveals whether institutions are
accumulating (OBV rising) or distributing (OBV falling) independent of
price direction.

The crypto-specific insight: when price is consolidating (range-bound) but
OBV is rising, institutions are absorbing available supply without revealing
their intent through price movement. When price eventually breaks to a new
N-bar high AND OBV is already at a new N-bar high, the breakout is confirmed
by prior institutional accumulation. OBV leads price.

OBV is also more wash-trade resistant in crypto than raw volume: to manipulate
OBV upward, a wash trader would need to consistently close bars in the positive
direction, which would itself move price -- making it self-defeating.

Entry conditions (LONG only -- bull regime strategy):
    1. Price above EMA(regime_ema_period) -- macro bull context
    2. OBV at new N-bar high (OBV leading price -- accumulation ahead of price)
    3. Price makes new N-bar high on current bar (price breakout confirmation)
    4. OBV EMA slope positive (OBV trend direction confirmed)
    5. RSI in [rsi_min, rsi_max] -- momentum positive, not extended
    6. Volume >= vol_ma * volume_threshold -- breakout volume

Template ID: obv_trend_divergence
Strategy Type: volume_confirmation_breakout
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


class ObvTrendDivergenceGenerator(SignalGenerator):
    """Signal generator for the OBV Trend Divergence strategy.

    Identifies breakouts that are confirmed by prior institutional accumulation
    measured via On-Balance Volume. An OBV new-high that precedes a price
    new-high indicates that buying pressure was building before price reacted,
    improving the probability that the breakout is genuine rather than a
    liquidity grab.

    Required parameters:
        obv_period, obv_ema_period,
        regime_ema_period,
        rsi_period, rsi_min, rsi_max,
        volume_period, volume_threshold,
        atr_period, atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        return "obv_trend_divergence"

    @property
    def min_bars_required(self) -> int:
        """EMA(200) warmup + OBV lookback + RSI(14) warmup + ATR(14) + buffer."""
        return 230

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate OBV Trend Divergence entry conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if OBV leads a price breakout to a new N-bar high
            in a confirmed bull trend with volume confirmation, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            obv_period: int           = int(params["obv_period"])
            obv_ema_period: int       = int(params["obv_ema_period"])
            regime_ema_period: int    = int(params.get("regime_ema_period", 200))
            rsi_period: int           = int(params["rsi_period"])
            rsi_min: float            = float(params["rsi_min"])
            rsi_max: float            = float(params["rsi_max"])
            volume_period: int        = int(params["volume_period"])
            volume_threshold: float   = float(params["volume_threshold"])
            atr_period: int           = int(params["atr_period"])
            atr_stop_mult: float      = float(params["atr_stop_multiplier"])
            rr_ratio: float           = float(params["risk_reward_ratio"])

            rsi_result = RSI(period=rsi_period).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            rsi_vals = rsi_result.values[~np.isnan(rsi_result.values)]
            atr_vals = atr_result.values[~np.isnan(atr_result.values)]

            if len(rsi_vals) < 1 or len(atr_vals) < 1:
                return None

            last_idx = len(series) - 1

            # Guard against NaN on the current bar's close
            if np.isnan(series.closes[last_idx]):
                return None

            price = float(series.closes[last_idx])

            # Macro bull gate: price must be above the long-period regime EMA
            if regime_ema_period > 0 and len(series) >= regime_ema_period:
                regime_ema  = EMA(period=regime_ema_period).calculate(series)
                regime_vals = regime_ema.values[~np.isnan(regime_ema.values)]
                if len(regime_vals) >= 1 and price <= float(regime_vals[-1]):
                    return None

            # Ensure there are enough bars for the OBV lookback windows
            if last_idx < obv_period + obv_ema_period + 10:
                return None

            closes_arr = series.closes
            vols_arr   = series.volumes

            # Compute OBV cumulatively over the full series.
            # NaN bars carry forward the previous OBV value to avoid gaps.
            obv: np.ndarray = np.zeros(len(closes_arr))
            for i in range(1, len(closes_arr)):
                if (
                    np.isnan(closes_arr[i])
                    or np.isnan(closes_arr[i - 1])
                    or np.isnan(vols_arr[i])
                ):
                    obv[i] = obv[i - 1]
                elif closes_arr[i] > closes_arr[i - 1]:
                    obv[i] = obv[i - 1] + float(vols_arr[i])
                elif closes_arr[i] < closes_arr[i - 1]:
                    obv[i] = obv[i - 1] - float(vols_arr[i])
                else:
                    obv[i] = obv[i - 1]

            obv_curr      = obv[last_idx]
            obv_lead_min: int = int(params.get("obv_lead_min", 2))
            obv_lead_max: int = int(params.get("obv_lead_max", 8))

            # True OBV-leads-price divergence: OBV peaked in the past M bars
            # (not on the current bar), and price is only NOW breaking to a new
            # N-bar high. This captures the institutional accumulation scenario:
            # OBV signals intent early, price confirms the move later.
            obv_full_window = obv[last_idx - obv_period : last_idx + 1]
            obv_max_idx     = int(np.argmax(obv_full_window))  # 0=oldest, obv_period=current
            bars_since_peak = obv_period - obv_max_idx         # 0 = current bar

            # OBV peak must be within the lead window (not too recent, not too stale)
            if bars_since_peak < obv_lead_min or bars_since_peak > obv_lead_max:
                return None

            obv_prior_max = float(np.max(obv_full_window))

            # OBV is still elevated: current OBV above its recent mean confirms
            # the accumulation is ongoing, not already reversed.
            obv_recent_mean = float(np.mean(obv[last_idx - obv_ema_period : last_idx]))
            if obv_curr <= obv_recent_mean:
                return None

            # Price breakout: price is NOW making a new N-bar high (catching up).
            # The OBV lead makes this a confirmation entry, not a chase entry.
            price_window    = closes_arr[last_idx - obv_period : last_idx]
            price_prior_max = float(np.nanmax(price_window))
            if price <= price_prior_max:
                return None

            rsi_curr = float(rsi_vals[-1])
            atr_curr = float(atr_vals[-1])

            # RSI filter: momentum should be positive but not overextended;
            # an RSI above rsi_max suggests the move has already run far
            if not (rsi_min <= rsi_curr <= rsi_max):
                return None

            # Volume filter: genuine breakouts attract above-average volume;
            # low-volume breakouts have higher failure rates in crypto
            vols = series.volumes[~np.isnan(series.volumes)]
            if len(vols) < volume_period + 1:
                return None
            vol_ma   = float(np.mean(vols[-(volume_period + 1):-1]))
            vol_curr = float(vols[-1])
            if vol_ma <= 0 or vol_curr <= vol_ma * volume_threshold:
                return None

            # Signal strength: OBV lead magnitude, volume excess, and RSI
            # positioning within the allowed range all increase confidence
            obv_lead_pct    = (obv_curr / (obv_prior_max + 1e-8) - 1.0) * 100.0
            strength_base   = min(
                1.0,
                0.55
                + min(0.15, obv_lead_pct * 0.02)
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
                    "obv": round(obv_curr, 0),
                    "obv_prior_max": round(obv_prior_max, 0),
                    "obv_lead_pct": round(obv_lead_pct, 2),
                    "price_breakout": round(price - price_prior_max, 4),
                    "rsi": round(rsi_curr, 1),
                    "volume_ratio": round(vol_curr / vol_ma, 2),
                    "atr": atr_curr,
                },
                metadata={
                    "trigger": "obv_td_long_breakout_with_obv_lead",
                    "obv_lead_pct": round(obv_lead_pct, 2),
                    "vol_ratio": round(vol_curr / vol_ma, 2),
                },
            )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e
