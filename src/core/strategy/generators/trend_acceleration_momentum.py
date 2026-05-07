"""Trend Acceleration Momentum signal generator.

Enters when an established trend is not just present but ACCELERATING:
EMA spread widening between fast and slow + volume expanding + ATR
growing. Captures the parabolic-run pattern unique to crypto.

Entry conditions (LONG):
    1. Price > EMA(fast) > EMA(slow)  -- trend structure confirmed
    2. EMA spread today > EMA spread N bars ago  -- acceleration
    3. RSI in [rsi_bull_min, rsi_bull_max]  -- momentum without extreme
    4. Volume > volume_ma * threshold  -- participation expanding
    5. ATR > ATR[atr_acceleration_lookback bars ago]  -- volatility growing
    6. (Optional) Price > EMA(regime_ema_period)  -- macro regime gate

SHORT conditions are the symmetric inverse with reversed regime gate.

Optional parameters:
    regime_ema_period: When > 0, restricts LONG signals to bull regime
        (price > EMA) and SHORT signals to bear regime (price < EMA).
        Default 0 disables the gate (both directions always allowed).

Template ID: trend_acceleration_momentum
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


class TrendAccelerationMomentumGenerator(SignalGenerator):
    """Signal generator for Trend Acceleration Momentum strategy.

    Identifies trends that are strengthening rather than merely present.
    Three independent acceleration signals must align: EMA spread widening,
    volume expanding, and ATR growing. This reduces false entries during
    flat or decelerating trend phases.

    Required parameters:
        fast_ema_period, slow_ema_period,
        rsi_period, rsi_bull_min, rsi_bull_max,
        volume_period, volume_threshold,
        atr_period, acceleration_lookback, atr_acceleration_lookback,
        atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        """Return template ID."""
        return "trend_acceleration_momentum"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars needed.

        slow_ema (21) + volume_ma (20) + atr_acceleration_lookback (5) + buffer = 60.
        """
        return 60

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate Trend Acceleration Momentum entry conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if trend is accelerating, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            fast_period: int = int(params["fast_ema_period"])
            slow_period: int = int(params["slow_ema_period"])
            rsi_period: int = int(params["rsi_period"])
            rsi_bull_min: float = float(params["rsi_bull_min"])
            rsi_bull_max: float = float(params["rsi_bull_max"])
            volume_period: int = int(params["volume_period"])
            volume_threshold: float = float(params["volume_threshold"])
            atr_period: int = int(params["atr_period"])
            accel_lookback: int = int(params["acceleration_lookback"])
            atr_accel_lookback: int = int(params["atr_acceleration_lookback"])
            atr_stop_mult: float = float(params["atr_stop_multiplier"])
            rr_ratio: float = float(params["risk_reward_ratio"])
            regime_ema_period: int = int(params.get("regime_ema_period", 0))

            fast_ema = EMA(period=fast_period).calculate(series)
            slow_ema = EMA(period=slow_period).calculate(series)
            rsi_result = RSI(period=rsi_period).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            # Strip NaNs for safe indexing
            fast_vals = fast_ema.values[~np.isnan(fast_ema.values)]
            slow_vals = slow_ema.values[~np.isnan(slow_ema.values)]
            rsi_vals = rsi_result.values[~np.isnan(rsi_result.values)]
            atr_vals = atr_result.values[~np.isnan(atr_result.values)]

            min_len = accel_lookback + 1
            if len(fast_vals) < min_len or len(slow_vals) < min_len:
                return None
            if len(rsi_vals) < 1 or len(atr_vals) < atr_accel_lookback + 1:
                return None

            price = float(series.closes[-1])
            fast_curr = float(fast_vals[-1])
            slow_curr = float(slow_vals[-1])
            rsi_curr = float(rsi_vals[-1])
            atr_curr = float(atr_vals[-1])
            atr_past = float(atr_vals[-(atr_accel_lookback + 1)])

            # EMA spread: positive = fast above slow, negative = fast below slow
            spread_curr = fast_curr - slow_curr
            spread_past = float(fast_vals[-accel_lookback - 1]) - float(slow_vals[-accel_lookback - 1])

            # Volume: rolling mean and current bar
            volumes = series.volumes
            valid_vols = volumes[~np.isnan(volumes)]
            if len(valid_vols) < volume_period + 1:
                return None
            vol_ma = float(np.mean(valid_vols[-(volume_period + 1):-1]))
            vol_curr = float(valid_vols[-1])

            # Regime gate: restricts direction to the macro trend when active
            # Guard: skip gate if series too short for the regime EMA period
            in_bull_regime: bool | None = None
            if regime_ema_period > 0 and len(series) >= regime_ema_period:
                regime_ema = EMA(period=regime_ema_period).calculate(series)
                regime_ema_vals = regime_ema.values[~np.isnan(regime_ema.values)]
                if len(regime_ema_vals) >= 1:
                    in_bull_regime = price > float(regime_ema_vals[-1])

            long_allowed = in_bull_regime is None or in_bull_regime
            short_allowed = in_bull_regime is None or not in_bull_regime

            indicators = {
                "fast_ema": fast_curr,
                "slow_ema": slow_curr,
                "ema_spread": spread_curr,
                "ema_spread_change": spread_curr - spread_past,
                "rsi": rsi_curr,
                "volume_ratio": vol_curr / vol_ma if vol_ma > 0 else 0.0,
                "atr": atr_curr,
                "atr_change": atr_curr - atr_past,
            }

            # --- LONG: trend structure + acceleration signals ---
            bull_structure = price > fast_curr > slow_curr
            bull_spread_accel = spread_curr > spread_past  # spread widening
            bull_rsi = rsi_bull_min <= rsi_curr <= rsi_bull_max
            bull_volume = vol_curr > vol_ma * volume_threshold
            bull_atr_accel = atr_curr > atr_past

            if long_allowed and bull_structure and bull_spread_accel and bull_rsi and bull_volume and bull_atr_accel:
                risk = atr_stop_mult * atr_curr
                stop_loss = price - risk
                take_profit = price + risk * rr_ratio

                strength = min(
                    1.0,
                    0.6
                    + min(0.2, (rsi_curr - rsi_bull_min) / (rsi_bull_max - rsi_bull_min) * 0.2)
                    + min(0.1, (vol_curr / vol_ma - volume_threshold) * 0.05)
                    + min(0.1, abs(spread_curr - spread_past) / (atr_curr + 1e-9) * 0.05),
                )

                return TradingSignal(
                    direction=SignalDirection.LONG,
                    symbol=symbol,
                    price=price,
                    strength=max(0.4, strength),
                    stop_loss=max(stop_loss, price * 0.001),
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={
                        "trigger": "tam_long_acceleration",
                        "spread_change": round(spread_curr - spread_past, 6),
                        "vol_ratio": round(vol_curr / vol_ma, 2) if vol_ma > 0 else 0.0,
                    },
                )

            # --- SHORT: trend structure + deceleration signals ---
            bear_structure = price < fast_curr < slow_curr
            bear_spread_accel = spread_curr < spread_past  # spread widening negatively
            # Mirror RSI range: short when RSI is [100-rsi_bull_max, 100-rsi_bull_min]
            rsi_bear_min = 100.0 - rsi_bull_max
            rsi_bear_max = 100.0 - rsi_bull_min
            bear_rsi = rsi_bear_min <= rsi_curr <= rsi_bear_max
            bear_volume = vol_curr > vol_ma * volume_threshold
            bear_atr_accel = atr_curr > atr_past

            if short_allowed and bear_structure and bear_spread_accel and bear_rsi and bear_volume and bear_atr_accel:
                risk = atr_stop_mult * atr_curr
                stop_loss = price + risk
                take_profit = price - risk * rr_ratio

                strength = min(
                    1.0,
                    0.6
                    + min(0.2, (rsi_bear_max - rsi_curr) / (rsi_bear_max - rsi_bear_min + 1e-9) * 0.2)
                    + min(0.1, (vol_curr / vol_ma - volume_threshold) * 0.05)
                    + min(0.1, abs(spread_curr - spread_past) / (atr_curr + 1e-9) * 0.05),
                )

                return TradingSignal(
                    direction=SignalDirection.SHORT,
                    symbol=symbol,
                    price=price,
                    strength=max(0.4, strength),
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={
                        "trigger": "tam_short_acceleration",
                        "spread_change": round(spread_curr - spread_past, 6),
                        "vol_ratio": round(vol_curr / vol_ma, 2) if vol_ma > 0 else 0.0,
                    },
                )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None
