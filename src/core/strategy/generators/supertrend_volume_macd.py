"""SuperTrend + Volume + MACD confluence signal generator.

Entry: All three conditions must be met simultaneously - SuperTrend direction,
MACD confirmation, and volume surge.
Exit: SuperTrend flip or MACD crossover reversal.

v1.1: Added SuperTrend persistence check (3-bar hold).
In bear markets, SuperTrend whipsaws on relief bounces — flips bullish
for 1-2 bars then flips back bearish. Requiring 3 consecutive bars in
the same direction filters out these false flips.

Template ID: supertrend_volume_macd
Strategy Type: trend_following
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import MACD, SuperTrend, VolumeAverage
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Minimum consecutive bars SuperTrend must hold direction before entry
_ST_PERSISTENCE_BARS = 3


class SupertrendVolumeMacdGenerator(SignalGenerator):
    """Signal generator for SuperTrend + Volume + MACD strategy.

    Requires triple confluence: SuperTrend trend direction, MACD
    confirmation (above/below zero), and volume above average. This
    multi-factor approach reduces false signals.

    v1.1: SuperTrend must hold direction for 3+ consecutive bars
    before entry is permitted, filtering bear-bounce whipsaws.

    Required parameters:
        supertrend_period, supertrend_multiplier,
        macd_fast, macd_slow, macd_signal,
        volume_ma_period, volume_multiplier
    """

    @property
    def template_id(self) -> str:
        return "supertrend_volume_macd"

    @property
    def min_bars_required(self) -> int:
        # macd_slow + macd_signal + supertrend_period + buffer
        return 60

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate triple confluence conditions with persistence filter.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if all three conditions met, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            st_period: int = int(params["supertrend_period"])
            st_mult: float = float(params["supertrend_multiplier"])
            macd_fast: int = int(params["macd_fast"])
            macd_slow: int = int(params["macd_slow"])
            macd_signal_period: int = int(params["macd_signal"])
            vol_ma_period: int = int(params["volume_ma_period"])
            vol_mult: float = float(params["volume_multiplier"])

            # Calculate indicators
            st_result = SuperTrend(period=st_period, multiplier=st_mult).calculate(series)
            macd_result = MACD(
                fast_period=macd_fast,
                slow_period=macd_slow,
                signal_period=macd_signal_period,
            ).calculate(series)
            vol_avg = VolumeAverage(period=vol_ma_period).calculate(series)

            price = float(series.closes[-1])
            current_volume = float(series.volumes[-1])
            vol_ma = vol_avg.current

            # SuperTrend direction
            st_trend = st_result.current_trend  # +1 bullish, -1 bearish
            st_value = st_result.current

            # SuperTrend persistence: direction must hold for 3+ bars
            # Filters bear-bounce whipsaws where ST flips for 1-2 bars
            valid_trend = st_result.trend[st_result.trend != 0]
            if len(valid_trend) < _ST_PERSISTENCE_BARS:
                return None
            st_persistent_bull = all(
                int(valid_trend[-i]) == 1 for i in range(1, _ST_PERSISTENCE_BARS + 1)
            )
            st_persistent_bear = all(
                int(valid_trend[-i]) == -1 for i in range(1, _ST_PERSISTENCE_BARS + 1)
            )

            # MACD state
            macd_curr = macd_result.current
            valid_signal = macd_result.signal_line[~np.isnan(macd_result.signal_line)]
            if len(valid_signal) == 0:
                return None
            macd_signal_val = float(valid_signal[-1])

            # Volume check
            volume_ok = current_volume > vol_ma * vol_mult

            indicators = {
                "supertrend": st_value,
                "supertrend_trend": float(st_trend),
                "st_persistent": st_persistent_bull or st_persistent_bear,
                "macd": macd_curr,
                "macd_signal": macd_signal_val,
                "volume_ratio": current_volume / vol_ma if vol_ma > 0 else 0,
            }

            # LONG: SuperTrend bullish (3-bar persistent) + MACD > signal + MACD > 0 + volume
            if (
                st_persistent_bull
                and macd_curr > macd_signal_val
                and macd_curr > 0
                and volume_ok
            ):
                return TradingSignal(
                    direction=SignalDirection.LONG,
                    symbol=symbol,
                    price=price,
                    strength=min(1.0, macd_curr / (price * 0.001 + 1)),
                    stop_loss=max(st_value, price * 0.001),  # SuperTrend as stop
                    indicators=indicators,
                    metadata={"trigger": "supertrend_macd_volume_long"},
                )

            # SHORT: SuperTrend bearish (3-bar persistent) + MACD < signal + MACD < 0 + volume
            if (
                st_persistent_bear
                and macd_curr < macd_signal_val
                and macd_curr < 0
                and volume_ok
            ):
                return TradingSignal(
                    direction=SignalDirection.SHORT,
                    symbol=symbol,
                    price=price,
                    strength=min(1.0, abs(macd_curr) / (price * 0.001 + 1)),
                    stop_loss=st_value,  # SuperTrend as stop
                    indicators=indicators,
                    metadata={"trigger": "supertrend_macd_volume_short"},
                )

            # CLOSE on SuperTrend flip (no persistence required for exits)
            if st_result.just_flipped_bullish() or st_result.just_flipped_bearish():
                return TradingSignal(
                    direction=SignalDirection.CLOSE,
                    symbol=symbol,
                    price=price,
                    strength=0.7,
                    indicators=indicators,
                    metadata={"trigger": "supertrend_flip_exit"},
                )

        except (ValueError, KeyError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None
