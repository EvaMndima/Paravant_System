"""Bollinger Band Squeeze Breakout signal generator.

Entry: Price breaks out of BB after a squeeze with MACD confirmation.
Exit: Price touches opposite band or momentum reversal.

Template ID: bb_squeeze_breakout
Strategy Type: volatility_breakout
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import MACD, BollingerBands, VolumeAverage
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BbSqueezeBreakoutGenerator(SignalGenerator):
    """Signal generator for BB Squeeze Breakout strategy.

    Detects Bollinger Band squeezes (low volatility periods) and generates
    signals when price breaks out with volume and MACD confirmation.

    Required parameters:
        bb_period, bb_std_dev, squeeze_threshold, squeeze_lookback,
        macd_fast, macd_slow, macd_signal, volume_threshold
    """

    @property
    def template_id(self) -> str:
        return "bb_squeeze_breakout"

    @property
    def min_bars_required(self) -> int:
        # macd_slow + macd_signal + squeeze_lookback + buffer
        return 60

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate BB squeeze breakout conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if breakout conditions met, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            bb_period: int = int(params["bb_period"])
            bb_std: float = float(params["bb_std_dev"])
            squeeze_threshold: float = float(params["squeeze_threshold"])
            squeeze_lookback: int = int(params["squeeze_lookback"])
            macd_fast: int = int(params["macd_fast"])
            macd_slow: int = int(params["macd_slow"])
            macd_signal_period: int = int(params["macd_signal"])
            vol_threshold: float = float(params["volume_threshold"])

            # Calculate indicators
            bb = BollingerBands(period=bb_period, multiplier=bb_std).calculate(series)
            macd = MACD(
                fast_period=macd_fast,
                slow_period=macd_slow,
                signal_period=macd_signal_period,
            ).calculate(series)
            vol_avg = VolumeAverage(period=bb_period).calculate(series)

            price = float(series.closes[-1])
            current_volume = float(series.volumes[-1])
            vol_ma = vol_avg.current

            # Get valid BB width values for squeeze detection
            valid_widths = bb.width[~np.isnan(bb.width)]
            if len(valid_widths) < squeeze_lookback:
                return None

            # Check for recent squeeze: was BB width below threshold recently?
            recent_widths = valid_widths[-squeeze_lookback:]
            was_squeezed = any(w < squeeze_threshold * 100 for w in recent_widths)

            if not was_squeezed:
                return None

            # Current width should be expanding (breaking out of squeeze)
            current_width = float(valid_widths[-1])
            prev_width = float(valid_widths[-2]) if len(valid_widths) >= 2 else current_width
            is_expanding = current_width > prev_width

            if not is_expanding:
                return None

            # Volume confirmation
            volume_ok = current_volume > vol_ma * vol_threshold

            # Get MACD histogram
            valid_hist = macd.histogram[~np.isnan(macd.histogram)]
            if len(valid_hist) < 2:
                return None
            hist_current = float(valid_hist[-1])

            # Get BB band values
            valid_upper = bb.upper[~np.isnan(bb.upper)]
            valid_lower = bb.lower[~np.isnan(bb.lower)]
            valid_middle = bb.middle[~np.isnan(bb.middle)]
            if len(valid_upper) == 0 or len(valid_lower) == 0:
                return None

            upper_band = float(valid_upper[-1])
            lower_band = float(valid_lower[-1])
            middle_band = float(valid_middle[-1])

            indicators = {
                "bb_upper": upper_band,
                "bb_middle": middle_band,
                "bb_lower": lower_band,
                "bb_width": current_width,
                "macd_histogram": hist_current,
                "volume_ratio": current_volume / vol_ma if vol_ma > 0 else 0,
            }

            # LONG: price above upper BB + MACD histogram positive + volume
            if price > upper_band and hist_current > 0 and volume_ok:
                return TradingSignal(
                    direction=SignalDirection.LONG,
                    symbol=symbol,
                    price=price,
                    strength=min(1.0, hist_current / (upper_band * 0.001 + 1)),
                    stop_loss=max(middle_band, price * 0.001),
                    indicators=indicators,
                    metadata={"trigger": "bb_squeeze_breakout_long"},
                )

            # SHORT: price below lower BB + MACD histogram negative + volume
            if price < lower_band and hist_current < 0 and volume_ok:
                return TradingSignal(
                    direction=SignalDirection.SHORT,
                    symbol=symbol,
                    price=price,
                    strength=min(1.0, abs(hist_current) / (lower_band * 0.001 + 1)),
                    stop_loss=middle_band,
                    indicators=indicators,
                    metadata={"trigger": "bb_squeeze_breakout_short"},
                )

        except (ValueError, KeyError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None
