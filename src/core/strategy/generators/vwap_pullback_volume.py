"""VWAP Pullback + Volume signal generator.

Entry: Price pulls back to VWAP with volume confirmation and RSI momentum.
Exit: Price reaches target distance from VWAP or volume fades.

Template ID: vwap_pullback_volume
Strategy Type: intraday_pullback
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import RSI, VWAP, VolumeAverage
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class VwapPullbackVolumeGenerator(SignalGenerator):
    """Signal generator for VWAP Pullback + Volume strategy.

    Identifies pullbacks to VWAP in established trends with volume
    confirmation. Designed for intraday timeframes.

    Required parameters:
        entry_buffer_pct, exit_distance_pct,
        volume_ma_period, volume_multiplier, exit_volume_threshold,
        rsi_period, stop_loss_pct
    """

    @property
    def template_id(self) -> str:
        return "vwap_pullback_volume"

    @property
    def min_bars_required(self) -> int:
        # VWAP period (20) + RSI period (up to 21) + buffer
        return 50

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate VWAP pullback + volume conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if pullback entry conditions met, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            entry_buffer: float = float(params["entry_buffer_pct"])
            exit_dist: float = float(params["exit_distance_pct"])
            vol_ma_period: int = int(params["volume_ma_period"])
            vol_mult: float = float(params["volume_multiplier"])
            exit_vol_thresh: float = float(params["exit_volume_threshold"])
            rsi_period: int = int(params["rsi_period"])
            stop_loss_pct: float = float(params["stop_loss_pct"])

            # Calculate indicators
            vwap_result = VWAP(period=vol_ma_period).calculate(series)
            rsi_result = RSI(period=rsi_period).calculate(series)
            vol_avg = VolumeAverage(period=vol_ma_period).calculate(series)

            price = float(series.closes[-1])
            prev_price = float(series.closes[-2])
            rsi_curr = rsi_result.current
            current_volume = float(series.volumes[-1])
            vol_ma = vol_avg.current

            # Get VWAP value
            valid_vwap = vwap_result.values[~np.isnan(vwap_result.values)]
            if len(valid_vwap) < 2:
                return None
            vwap_curr = float(valid_vwap[-1])
            vwap_prev = float(valid_vwap[-2])

            # Buffer zone around VWAP
            buffer_abs = vwap_curr * (entry_buffer / 100.0)
            is_near_vwap = abs(price - vwap_curr) <= buffer_abs

            # Volume check
            volume_ok = current_volume > vol_ma * vol_mult

            # Volume exit check
            volume_fading = current_volume < vol_ma * exit_vol_thresh

            indicators = {
                "vwap": vwap_curr,
                "rsi": rsi_curr,
                "volume_ratio": current_volume / vol_ma if vol_ma > 0 else 0,
                "price_vwap_distance_pct": (price - vwap_curr) / vwap_curr * 100 if vwap_curr > 0 else 0,
            }

            # LONG: was above VWAP, pulled back to it, RSI > 50, volume confirms
            if (
                prev_price > vwap_prev  # Was above VWAP
                and is_near_vwap  # Pulled back to VWAP
                and rsi_curr > 50  # Bullish momentum
                and volume_ok  # Volume confirmation
            ):
                stop_loss = price * (1 - stop_loss_pct / 100.0)
                take_profit = vwap_curr + (vwap_curr * exit_dist / 100.0)

                return TradingSignal(
                    direction=SignalDirection.LONG,
                    symbol=symbol,
                    price=price,
                    strength=min(1.0, (rsi_curr - 50) / 30),
                    stop_loss=max(stop_loss, price * 0.001),
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={"trigger": "vwap_pullback_long"},
                )

            # SHORT: was below VWAP, rallied to it, RSI < 50, volume confirms
            if (
                prev_price < vwap_prev  # Was below VWAP
                and is_near_vwap  # Rallied to VWAP
                and rsi_curr < 50  # Bearish momentum
                and volume_ok  # Volume confirmation
            ):
                stop_loss = price * (1 + stop_loss_pct / 100.0)
                take_profit = vwap_curr - (vwap_curr * exit_dist / 100.0)

                return TradingSignal(
                    direction=SignalDirection.SHORT,
                    symbol=symbol,
                    price=price,
                    strength=min(1.0, (50 - rsi_curr) / 30),
                    stop_loss=stop_loss,
                    take_profit=max(take_profit, price * 0.001),
                    indicators=indicators,
                    metadata={"trigger": "vwap_pullback_short"},
                )

            # CLOSE on volume fade
            if volume_fading:
                return TradingSignal(
                    direction=SignalDirection.CLOSE,
                    symbol=symbol,
                    price=price,
                    strength=0.4,
                    indicators=indicators,
                    metadata={"trigger": "volume_fade_exit"},
                )

        except (ValueError, KeyError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None
