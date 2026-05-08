"""StochasticRSI Bull Cross signal generator.

Uses the StochasticRSI K/D crossover from oversold as a micro-pullback
entry signal within a confirmed bull trend. StochasticRSI is a second-order
oscillator: it applies the Stochastic formula to RSI values rather than
raw prices. This makes it significantly more sensitive than RSI alone —
it detects short-term oscillations within the RSI's own range.

Quant basis: In a bull trend, price oscillates between pullbacks and
advances. RSI(14) is too slow to catch the exact inflection point of
micro-pullbacks — by the time RSI turns up from 40, the price is often
already 1-2% off the low. StochasticRSI captures the inflection earlier
because it measures where RSI is relative to its own recent range, not
just relative to the fixed 0-100 scale.

The K/D cross from oversold is the specific signal: StochRSI K-line
represents the fast stochastic of RSI, D-line is the smoothed signal.
A K>D cross while both lines were recently below stoch_oversold means:
(1) RSI had pulled back significantly within its own range (real pullback),
(2) RSI momentum has turned from downward to upward (cross confirms),
(3) The cross happened from a low base (not just oscillating at mid-level).

KFA uses StochasticRSI as a secondary confirmation for mean-reversion fades.
SRC uses it as the primary entry trigger for trend pullbacks — different
use case, different regime, different direction.

Entry conditions (LONG only — bull regime strategy):
    1. Price above EMA(regime_ema_period) — macro bull context
    2. Price above EMA(ema_period) — intermediate trend intact
    3. K-line was below stoch_oversold within last stoch_lookback bars —
       confirms a real pullback occurred, not just mid-range oscillation
    4. K-line crosses above D-line: k_curr > d_curr AND k_prev <= d_prev
    5. K-line still below stoch_max (e.g., 70) — not chasing a run
    6. RSI(rsi_period) in [rsi_min, rsi_max] — underlying momentum acceptable
    7. Volume >= vol_ma * volume_threshold — participation confirmation

Template ID: stoch_rsi_bull_cross
Strategy Type: trend_continuation
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import ATR, EMA, RSI, StochasticRSI
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class StochRsiBullCrossGenerator(SignalGenerator):
    """Signal generator for StochasticRSI Bull Cross strategy.

    Detects micro-pullback entries in bull trends via StochRSI K/D crossover
    from oversold. The "recently oversold" condition distinguishes genuine
    pullbacks (where RSI itself dropped) from random mid-range crosses.

    Required parameters:
        rsi_period, stoch_period, smooth_k, smooth_d,
        stoch_oversold, stoch_max, stoch_lookback,
        ema_period, regime_ema_period,
        rsi_min, rsi_max,
        volume_period, volume_threshold,
        atr_period, atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        return "stoch_rsi_bull_cross"

    @property
    def min_bars_required(self) -> int:
        """EMA(200) warmup + StochRSI(14+14+3+3) warmup + lookback + buffer."""
        return 230

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate StochasticRSI Bull Cross entry conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if StochRSI K/D cross occurs from an oversold
            pullback in a confirmed bull trend, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            rsi_period: int         = int(params["rsi_period"])
            stoch_period: int       = int(params["stoch_period"])
            smooth_k: int           = int(params["smooth_k"])
            smooth_d: int           = int(params["smooth_d"])
            stoch_oversold: float   = float(params["stoch_oversold"])
            stoch_max: float        = float(params["stoch_max"])
            stoch_lookback: int     = int(params["stoch_lookback"])
            ema_period: int         = int(params["ema_period"])
            regime_ema_period: int  = int(params.get("regime_ema_period", 0))
            rsi_min: float          = float(params["rsi_min"])
            rsi_max: float          = float(params["rsi_max"])
            volume_period: int      = int(params["volume_period"])
            volume_threshold: float = float(params["volume_threshold"])
            atr_period: int         = int(params["atr_period"])
            atr_stop_mult: float    = float(params["atr_stop_multiplier"])
            rr_ratio: float         = float(params["risk_reward_ratio"])

            ema_result   = EMA(period=ema_period).calculate(series)
            rsi_result   = RSI(period=rsi_period).calculate(series)
            stoch_result = StochasticRSI(
                rsi_period=rsi_period,
                stoch_period=stoch_period,
                k_smooth=smooth_k,
                d_smooth=smooth_d,
            ).calculate(series)
            atr_result   = ATR(period=atr_period).calculate(series)

            ema_vals = ema_result.values[~np.isnan(ema_result.values)]
            rsi_vals = rsi_result.values[~np.isnan(rsi_result.values)]
            k_vals   = stoch_result.k_line[~np.isnan(stoch_result.k_line)]
            d_vals   = stoch_result.d_line[~np.isnan(stoch_result.d_line)]
            atr_vals = atr_result.values[~np.isnan(atr_result.values)]

            min_stoch_needed = stoch_lookback + 2
            if (
                len(ema_vals) < 1
                or len(rsi_vals) < 1
                or len(k_vals) < min_stoch_needed
                or len(d_vals) < min_stoch_needed
                or len(atr_vals) < 1
            ):
                return None

            price    = float(series.closes[-1])
            ema_curr = float(ema_vals[-1])

            # Intermediate trend gate: price above EMA(ema_period)
            if price <= ema_curr:
                return None

            # Macro bull gate: confirm we are in a macro uptrend
            if regime_ema_period > 0 and len(series) >= regime_ema_period:
                regime_ema = EMA(period=regime_ema_period).calculate(series)
                regime_vals = regime_ema.values[~np.isnan(regime_ema.values)]
                if len(regime_vals) >= 1 and price <= float(regime_vals[-1]):
                    return None

            k_curr = float(k_vals[-1])
            k_prev = float(k_vals[-2])
            d_curr = float(d_vals[-1])
            d_prev = float(d_vals[-2])

            # K/D bullish cross: K crosses above D on this bar
            if not (k_curr > d_curr and k_prev <= d_prev):
                return None

            # Not chasing: K-line must still be below stoch_max.
            # If K is already at 70+, the cross happened earlier and
            # this is momentum exhaustion territory, not pullback entry.
            if k_curr >= stoch_max:
                return None

            # Pullback validation: K-line was below stoch_oversold within
            # the lookback window (confirms a real RSI pullback occurred,
            # not just mid-range oscillation where K/D crosses are noisy).
            recent_k = k_vals[-(stoch_lookback + 2):-1]
            was_oversold = float(np.min(recent_k)) < stoch_oversold
            if not was_oversold:
                return None

            rsi_curr = float(rsi_vals[-1])
            atr_curr = float(atr_vals[-1])

            # Underlying RSI: confirms momentum is acceptable
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

            # Signal strength: depth of pullback + cross magnitude + volume
            pullback_depth = max(0.0, stoch_oversold - float(np.min(recent_k)))
            cross_magnitude = k_curr - d_curr
            strength_base = min(
                1.0,
                0.55
                + min(0.15, pullback_depth / stoch_oversold * 0.2)
                + min(0.1, cross_magnitude * 0.005)
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
                    "stoch_k": round(k_curr, 2),
                    "stoch_d": round(d_curr, 2),
                    "stoch_k_prev": round(k_prev, 2),
                    "stoch_d_prev": round(d_prev, 2),
                    "k_minus_d": round(k_curr - d_curr, 2),
                    "pullback_depth": round(pullback_depth, 2),
                    "rsi": round(rsi_curr, 1),
                    "ema_trend": round(ema_curr, 4),
                    "volume_ratio": round(vol_curr / vol_ma, 2),
                    "atr": atr_curr,
                },
                metadata={
                    "trigger": "src_long_stoch_kd_cross_from_oversold",
                    "stoch_k": round(k_curr, 2),
                    "pullback_depth": round(pullback_depth, 2),
                    "cross_mag": round(k_curr - d_curr, 2),
                },
            )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e
