"""Volume Price Trend (VPT) Momentum signal generator.

VPT is a cumulative volume indicator that weights each bar by the magnitude
of the price change:

    VPT[i] = VPT[i-1] + Volume[i] * (Close[i] - Close[i-1]) / Close[i-1]

Unlike OBV (which uses binary direction), VPT weighs bars proportionally --
a 3% move on 1M volume adds 3x more to VPT than a 1% move on 1M volume.

Crypto-specific insight: Exchanges can fabricate raw volume (wash trading),
but cannot easily fake volume simultaneously with large price movements --
doing so would itself move the price significantly. VPT is therefore more
wash-trade-resistant than pure OBV or volume averages, which matters in
crypto where exchange volume manipulation is documented. (Cong et al. 2021)

The signal: when VPT is trending above its own EMA (VPT_EMA rising) AND
the current bar's VPT contribution is outsized (this bar's volume x price
return exceeds the average contribution), institutional momentum is
accelerating -- both trade SIZE and price MOVE are above baseline.

Entry conditions (LONG only -- bull regime strategy):
    1. Price above EMA(regime_ema_period) -- macro bull context
    2. Price above EMA(ema_period) -- intermediate trend intact
    3. VPT > EMA(VPT, vpt_ema_period) -- VPT trend is up
    4. VPT is at a new N-bar high (VPT accelerating, not just positive)
    5. Current bar's VPT contribution > vpt_contrib_threshold * avg contribution
       (this bar's momentum is outsized vs. history)
    6. RSI in [rsi_min, rsi_max] -- not overbought
    7. Volume >= vol_ma * volume_threshold -- participation confirmed

Template ID: vpt_momentum
Strategy Type: volume_momentum
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


class VptMomentumGenerator(SignalGenerator):
    """Signal generator for VPT Momentum strategy.

    Identifies bars where both cumulative VPT is accelerating (new N-bar high)
    and the current bar's volume-weighted price return is outsized relative to
    the recent average -- a compound signal of institutional momentum surging.

    Required parameters:
        vpt_ema_period, vpt_lookback, vpt_contrib_period, vpt_contrib_threshold,
        ema_period, regime_ema_period,
        rsi_period, rsi_min, rsi_max,
        volume_period, volume_threshold,
        atr_period, atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        return "vpt_momentum"

    @property
    def min_bars_required(self) -> int:
        """EMA(200) warmup + VPT contribution lookback + buffer."""
        return 230

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate VPT Momentum entry conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if VPT reaches a new high with an outsized current-bar
            contribution in a confirmed bull trend, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            vpt_ema_period: int          = int(params["vpt_ema_period"])
            vpt_lookback: int            = int(params["vpt_lookback"])
            vpt_contrib_period: int      = int(params["vpt_contrib_period"])
            vpt_contrib_threshold: float = float(params["vpt_contrib_threshold"])
            ema_period: int              = int(params["ema_period"])
            regime_ema_period: int       = int(params.get("regime_ema_period", 0))
            rsi_period: int              = int(params["rsi_period"])
            rsi_min: float               = float(params["rsi_min"])
            rsi_max: float               = float(params["rsi_max"])
            volume_period: int           = int(params["volume_period"])
            volume_threshold: float      = float(params["volume_threshold"])
            atr_period: int              = int(params["atr_period"])
            atr_stop_mult: float         = float(params["atr_stop_multiplier"])
            rr_ratio: float              = float(params["risk_reward_ratio"])

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

            # RSI gate: momentum within acceptable range
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

            # --- VPT computation over all available bars ---
            closes_arr = series.closes
            vols_arr   = series.volumes
            n = len(closes_arr)

            vpt        = np.zeros(n)
            vpt_contrib = np.zeros(n)

            for i in range(1, n):
                c_curr = float(closes_arr[i])
                c_prev = float(closes_arr[i - 1])
                v      = float(vols_arr[i])
                if (
                    np.isnan(c_curr)
                    or np.isnan(c_prev)
                    or np.isnan(v)
                    or c_prev <= 0
                ):
                    vpt[i] = vpt[i - 1]
                    vpt_contrib[i] = 0.0
                    continue
                contrib = v * (c_curr - c_prev) / c_prev
                vpt[i] = vpt[i - 1] + contrib
                vpt_contrib[i] = contrib

            last_idx = n - 1
            vpt_curr = vpt[last_idx]

            # --- VPT EMA via exponential smoothing over recent bars ---
            alpha = 2.0 / (vpt_ema_period + 1)
            start_idx    = max(0, last_idx - vpt_ema_period * 3)
            vpt_ema_val  = vpt[start_idx]
            for i in range(start_idx + 1, last_idx + 1):
                vpt_ema_val = alpha * vpt[i] + (1 - alpha) * vpt_ema_val
            vpt_ema = vpt_ema_val

            # VPT must be above its EMA (VPT trend is up)
            if vpt_curr <= vpt_ema:
                return None

            # VPT must be at a new N-bar high (momentum accelerating)
            if last_idx < vpt_lookback + 1:
                return None
            vpt_window = vpt[last_idx - vpt_lookback : last_idx]
            if vpt_curr <= float(np.max(vpt_window)):
                return None

            # Current bar's VPT contribution must be outsized vs. average
            if last_idx < vpt_contrib_period + 1:
                return None
            contrib_window = np.abs(
                vpt_contrib[last_idx - vpt_contrib_period : last_idx]
            )
            avg_contrib  = float(np.mean(contrib_window))
            curr_contrib = vpt_contrib[last_idx]
            if avg_contrib <= 0 or curr_contrib <= vpt_contrib_threshold * avg_contrib:
                return None

            # --- Signal strength ---
            contrib_ratio = curr_contrib / (avg_contrib + 1e-8)
            strength_base = min(
                1.0,
                0.55
                + min(0.15, (contrib_ratio - vpt_contrib_threshold) * 0.05)
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
                    "vpt": round(vpt_curr, 2),
                    "vpt_ema": round(vpt_ema, 2),
                    "vpt_contrib": round(curr_contrib, 2),
                    "vpt_contrib_ratio": round(contrib_ratio, 2),
                    "rsi": round(rsi_curr, 1),
                    "volume_ratio": round(vol_curr / vol_ma, 2),
                    "atr": atr_curr,
                },
                metadata={
                    "trigger": "vpt_long_momentum_surge",
                    "vpt_contrib_ratio": round(contrib_ratio, 2),
                    "vol_ratio": round(vol_curr / vol_ma, 2),
                },
            )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e
