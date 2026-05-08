"""Realized Volatility Compression Breakout signal generator.

Realized volatility (HV) is computed as the rolling standard deviation of
log returns: HV[t] = std(log(Close[t]/Close[t-1]), window=N) * sqrt(8760)

The crypto-specific insight: crypto exhibits sharper volatility regime
transitions than equities. When short-term realized vol compresses to
< 50% of medium-term realized vol, the market is in a "coiled spring" state.
The subsequent vol expansion is directionally biased to the upside in a
confirmed bull trend. (Baur and Dimpfl 2018 -- crypto vol clustering and
abrupt regime transitions.)

Unlike Bollinger Band width (which measures price range), realized vol
measures the statistical dispersion of log returns -- a fundamentally
different volatility signal. BB width can stay wide due to a single spike;
realized vol requires sustained return magnitude to remain elevated.

Entry conditions (LONG only -- bull regime strategy):
    1. Price above EMA(regime_ema_period) -- macro bull context
    2. Short-term HV (hv_short_period) < hv_compression_ratio * medium-term HV
       (hv_medium_period) -- volatility has compressed
    3. Vol compression has persisted for hv_min_compression_bars consecutive bars
    4. Price makes new N-bar high (breakout from compression zone)
    5. Volume >= vol_ma * volume_threshold -- institutional participation
    6. RSI > rsi_min -- momentum supporting breakout

Template ID: realized_vol_compression_breakout
Strategy Type: volatility_breakout
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


class RealizedVolCompressionBreakoutGenerator(SignalGenerator):
    """Signal generator for Realized Volatility Compression Breakout strategy.

    Identifies breakouts that follow a sustained period of compressed short-term
    realized volatility relative to medium-term realized volatility, combined with
    a confirmed price new-high and volume surge -- the "coiled spring" release.

    Required parameters:
        hv_short_period, hv_medium_period, hv_compression_ratio,
        hv_min_compression_bars, breakout_lookback,
        regime_ema_period,
        rsi_period, rsi_min, rsi_max,
        volume_period, volume_threshold,
        atr_period, atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        return "realized_vol_compression_breakout"

    @property
    def min_bars_required(self) -> int:
        """EMA(200) warmup + medium HV window + compression bars + buffer."""
        return 230

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate Realized Volatility Compression Breakout entry conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if price breaks out of a sustained vol compression zone
            in a confirmed macro bull trend with volume confirmation, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            hv_short_period: int           = int(params["hv_short_period"])
            hv_medium_period: int          = int(params["hv_medium_period"])
            hv_compression_ratio: float    = float(params["hv_compression_ratio"])
            hv_min_compression_bars: int   = int(params["hv_min_compression_bars"])
            breakout_lookback: int         = int(params["breakout_lookback"])
            regime_ema_period: int         = int(params.get("regime_ema_period", 0))
            rsi_period: int                = int(params["rsi_period"])
            rsi_min: float                 = float(params["rsi_min"])
            rsi_max: float                 = float(params["rsi_max"])
            volume_period: int             = int(params["volume_period"])
            volume_threshold: float        = float(params["volume_threshold"])
            atr_period: int                = int(params["atr_period"])
            atr_stop_mult: float           = float(params["atr_stop_multiplier"])
            rr_ratio: float                = float(params["risk_reward_ratio"])

            # --- Indicator calculations ---
            rsi_result = RSI(period=rsi_period).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            rsi_vals = rsi_result.values[~np.isnan(rsi_result.values)]
            atr_vals = atr_result.values[~np.isnan(atr_result.values)]

            if len(rsi_vals) < 1 or len(atr_vals) < 1:
                return None

            price    = float(series.closes[-1])
            rsi_curr = float(rsi_vals[-1])
            atr_curr = float(atr_vals[-1])

            # Macro bull gate: price above EMA(regime_ema_period)
            if regime_ema_period > 0 and len(series) >= regime_ema_period:
                regime_ema = EMA(period=regime_ema_period).calculate(series)
                regime_vals = regime_ema.values[~np.isnan(regime_ema.values)]
                if len(regime_vals) >= 1 and price <= float(regime_vals[-1]):
                    return None

            # RSI gate: momentum supporting the breakout
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

            # --- Realized volatility computation ---
            closes_arr = series.closes
            n          = len(closes_arr)
            last_idx   = n - 1

            # Compute log returns over all bars, skipping invalid values
            log_returns = np.full(n, np.nan)
            for i in range(1, n):
                c_curr = float(closes_arr[i])
                c_prev = float(closes_arr[i - 1])
                if (
                    c_curr > 0
                    and c_prev > 0
                    and not np.isnan(c_curr)
                    and not np.isnan(c_prev)
                ):
                    log_returns[i] = np.log(c_curr / c_prev)

            # Need enough data for the medium-term window plus compression check
            min_data = hv_medium_period + hv_min_compression_bars + 10
            if last_idx < min_data:
                return None

            # Current short and medium realized vol
            short_rets  = log_returns[last_idx - hv_short_period + 1 : last_idx + 1]
            medium_rets = log_returns[last_idx - hv_medium_period + 1 : last_idx + 1]

            short_rets_clean  = short_rets[~np.isnan(short_rets)]
            medium_rets_clean = medium_rets[~np.isnan(medium_rets)]

            if (
                len(short_rets_clean) < hv_short_period // 2
                or len(medium_rets_clean) < hv_medium_period // 2
            ):
                return None

            hv_short  = float(np.std(short_rets_clean))
            hv_medium = float(np.std(medium_rets_clean))

            if hv_medium <= 0:
                return None

            # Current bar must be in compression (short HV below threshold * medium HV)
            if hv_short >= hv_compression_ratio * hv_medium:
                return None

            # Persistent compression: check hv_min_compression_bars consecutive prior bars
            compressed_count = 0
            for j in range(1, hv_min_compression_bars + 1):
                idx_j = last_idx - j
                if idx_j < hv_medium_period:
                    break
                sr_j = log_returns[idx_j - hv_short_period + 1 : idx_j + 1]
                mr_j = log_returns[idx_j - hv_medium_period + 1 : idx_j + 1]
                sr_j_clean = sr_j[~np.isnan(sr_j)]
                mr_j_clean = mr_j[~np.isnan(mr_j)]
                if (
                    len(sr_j_clean) < hv_short_period // 2
                    or len(mr_j_clean) < hv_medium_period // 2
                ):
                    break
                hv_s_j = float(np.std(sr_j_clean))
                hv_m_j = float(np.std(mr_j_clean))
                if hv_m_j > 0 and hv_s_j < hv_compression_ratio * hv_m_j:
                    compressed_count += 1
                else:
                    break

            if compressed_count < hv_min_compression_bars:
                return None

            # Price breakout: current price must exceed the N-bar prior high
            if last_idx < breakout_lookback + 1:
                return None
            price_window   = series.closes[last_idx - breakout_lookback : last_idx]
            price_prior_max = float(np.nanmax(price_window))
            if price <= price_prior_max:
                return None

            # --- Signal strength ---
            # Deeper compression = more energy in the coiled spring
            vol_compression_depth = 1.0 - (hv_short / (hv_medium + 1e-8))
            strength_base = min(
                1.0,
                0.55
                + min(0.15, vol_compression_depth * 0.2)
                + min(0.1, (vol_curr / vol_ma - volume_threshold) * 0.05)
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
                    "hv_short": round(hv_short * 100, 3),
                    "hv_medium": round(hv_medium * 100, 3),
                    "hv_ratio": round(hv_short / (hv_medium + 1e-8), 3),
                    "compression_bars": float(compressed_count),
                    "price_breakout_pct": round(
                        (price / price_prior_max - 1) * 100, 3
                    ),
                    "rsi": round(rsi_curr, 1),
                    "volume_ratio": round(vol_curr / vol_ma, 2),
                    "atr": atr_curr,
                },
                metadata={
                    "trigger": "rvcb_long_vol_compression_breakout",
                    "hv_ratio": round(hv_short / (hv_medium + 1e-8), 3),
                    "compression_bars": compressed_count,
                },
            )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e
