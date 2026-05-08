"""ROC Momentum Surge signal generator.

Uses Rate of Change (ROC) acceleration combined with RSI in the 60-75 "power
zone" to detect the mid-bull momentum surge — the phase between initial trend
establishment and parabolic exhaustion where the largest sustained gains occur.

Counter-intuitive quant insight: In crypto bull markets, RSI in the 60-75 zone
is a continuation signal, not an overbought warning. Traditional RSI mean
reversion logic (RSI > 70 = sell) is a losing strategy in crypto bull runs —
high RSI reflects trend strength, not exhaustion. Exhaustion is indicated by
RSI > 78-80 combined with slowing ROC. The "power zone" is 60-75.

ROC measures momentum as a pure price velocity metric — distinct from RSI
(relative strength against own history) and MACD (trend divergence). When ROC
is both above a minimum threshold AND accelerating (current ROC > ROC N bars
ago), the price momentum is building, not plateauing.

Entry conditions (LONG only — bull regime strategy):
    1. Price above EMA(ema_period) — macro bull context
    2. ROC(roc_period) > roc_threshold — minimum price velocity reached
    3. ROC accelerating: current ROC > ROC roc_accel_period bars ago
    4. RSI in [rsi_bull_min, rsi_bull_max]: the 60-75 power zone
    5. RSI rising: current RSI > RSI roc_accel_period bars ago
    6. Volume >= vol_ma * volume_threshold — mild participation confirmation

Template ID: roc_momentum_surge
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


class RocMomentumSurgeGenerator(SignalGenerator):
    """Signal generator for ROC Momentum Surge strategy.

    Detects mid-bull acceleration via ROC > threshold + ROC accelerating +
    RSI in the 60-75 power zone. Buys momentum strength, not dips.

    Required parameters:
        roc_period, roc_threshold, roc_accel_period,
        rsi_period, rsi_bull_min, rsi_bull_max,
        ema_period,
        volume_period, volume_threshold,
        atr_period, atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        return "roc_momentum_surge"

    @property
    def min_bars_required(self) -> int:
        """EMA(50) warmup + RSI(14) warmup + ROC(5+3 lookback) + buffer."""
        return 100

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate ROC Momentum Surge entry conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if ROC accelerating in RSI power zone with bull
            context, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            roc_period: int         = int(params["roc_period"])
            roc_threshold: float    = float(params["roc_threshold"])
            roc_accel_period: int   = int(params["roc_accel_period"])
            rsi_period: int         = int(params["rsi_period"])
            rsi_bull_min: float     = float(params["rsi_bull_min"])
            rsi_bull_max: float     = float(params["rsi_bull_max"])
            ema_period: int         = int(params["ema_period"])
            volume_period: int      = int(params["volume_period"])
            volume_threshold: float = float(params["volume_threshold"])
            atr_period: int         = int(params["atr_period"])
            atr_stop_mult: float    = float(params["atr_stop_multiplier"])
            rr_ratio: float         = float(params["risk_reward_ratio"])
            regime_ema_period: int  = int(params.get("regime_ema_period", 0))

            ema_result = EMA(period=ema_period).calculate(series)
            rsi_result = RSI(period=rsi_period).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            ema_vals = ema_result.values[~np.isnan(ema_result.values)]
            rsi_vals = rsi_result.values[~np.isnan(rsi_result.values)]
            atr_vals = atr_result.values[~np.isnan(atr_result.values)]

            min_rsi_needed = roc_accel_period + 1
            if len(ema_vals) < 1 or len(rsi_vals) < min_rsi_needed or len(atr_vals) < 1:
                return None

            price    = float(series.closes[-1])
            ema_curr = float(ema_vals[-1])
            rsi_curr = float(rsi_vals[-1])
            rsi_past = float(rsi_vals[-roc_accel_period - 1])
            atr_curr = float(atr_vals[-1])

            # Macro trend gate: price above short-term EMA
            if price <= ema_curr:
                return None

            # Regime gate: restrict to confirmed macro bull trend.
            # RSI 60-75 on a bear-market relief bounce looks identical to a bull
            # surge — the EMA-200 gate separates them cleanly.
            if regime_ema_period > 0 and len(series) >= regime_ema_period:
                regime_ema_calc = EMA(period=regime_ema_period).calculate(series)
                regime_vals = regime_ema_calc.values[~np.isnan(regime_ema_calc.values)]
                if len(regime_vals) >= 1 and price <= float(regime_vals[-1]):
                    return None

            # RSI power zone: 60-75 = trend strength in crypto bull markets
            if not (rsi_bull_min <= rsi_curr <= rsi_bull_max):
                return None

            # RSI rising: momentum building, not stalling within the zone
            if rsi_curr <= rsi_past:
                return None

            # ROC: (close[-1] - close[-(roc_period+1)]) / close[-(roc_period+1)] * 100
            closes = series.closes
            n_needed = roc_period + roc_accel_period + 1
            if len(closes) < n_needed:
                return None

            # Current ROC
            price_n_ago      = float(closes[-(roc_period + 1)])
            if price_n_ago <= 0:
                return None
            roc_curr = (price - price_n_ago) / price_n_ago * 100.0

            # ROC N bars ago (for acceleration check)
            price_curr_past  = float(closes[-(roc_accel_period + 1)])
            price_n_plus_a   = float(closes[-(roc_period + roc_accel_period + 1)])
            if price_n_plus_a <= 0 or price_curr_past <= 0:
                return None
            roc_past = (price_curr_past - price_n_plus_a) / price_n_plus_a * 100.0

            # Minimum velocity
            if roc_curr < roc_threshold:
                return None

            # Acceleration: current ROC > past ROC
            if roc_curr <= roc_past:
                return None

            # Volume confirmation
            vols = series.volumes[~np.isnan(series.volumes)]
            if len(vols) < volume_period + 1:
                return None
            vol_ma   = float(np.mean(vols[-(volume_period + 1):-1]))
            vol_curr = float(vols[-1])
            if vol_ma <= 0 or vol_curr <= vol_ma * volume_threshold:
                return None

            # Signal strength: velocity + RSI position in zone + volume
            zone_width = rsi_bull_max - rsi_bull_min
            rsi_pos    = (rsi_curr - rsi_bull_min) / zone_width if zone_width > 0 else 0.5
            roc_excess = roc_curr - roc_threshold
            strength_base = min(
                1.0,
                0.55
                + min(0.15, rsi_pos * 0.2)
                + min(0.15, roc_excess * 0.05)
                + min(0.1, (vol_curr / vol_ma - volume_threshold) * 0.05)
                + min(0.05, (roc_curr - roc_past) * 0.02),
            )

            # Tighter stop for momentum entry (1.5x default) — momentum has a
            # defined invalidation: if ATR gives up, the move is over
            risk = atr_stop_mult * atr_curr
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
                    "roc_curr": round(roc_curr, 3),
                    "roc_past": round(roc_past, 3),
                    "roc_acceleration": round(roc_curr - roc_past, 3),
                    "rsi": round(rsi_curr, 1),
                    "rsi_past": round(rsi_past, 1),
                    "ema_trend": round(ema_curr, 4),
                    "volume_ratio": round(vol_curr / vol_ma, 2),
                    "atr": atr_curr,
                },
                metadata={
                    "trigger": "rms_long_roc_power_zone",
                    "roc_curr": round(roc_curr, 3),
                    "roc_accel": round(roc_curr - roc_past, 3),
                    "rsi_zone": round(rsi_curr, 1),
                },
            )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e
