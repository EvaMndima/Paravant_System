"""BB Squeeze Momentum Breakout signal generator.

Uses the TTM Squeeze method (BB inside Keltner Channels) to detect
volatility compression. Enters on squeeze release with MACD momentum,
SuperTrend trend confirmation, and volume spike validation.

Key difference from bb_squeeze_breakout: true squeeze detection via
BB-inside-Keltner (John Carter's method) rather than BB width percentile.

Entry: Squeeze releases + directional close + volume + MACD histogram + SuperTrend
Exit: 2*ATR trailing stop (stored in metadata for engine)

Template ID: bb_squeeze_momentum
Strategy Type: volatility_breakout
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import (
    ATR,
    MACD,
    BollingerBands,
    KeltnerChannel,
    SuperTrend,
    VolumeAverage,
)
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BbSqueezeMomentumGenerator(SignalGenerator):
    """Signal generator for BB Squeeze Momentum Breakout strategy.

    Uses the TTM Squeeze method: Bollinger Bands inside Keltner Channels
    indicates volatility compression. When the squeeze releases (BB expands
    outside KC), enter in the direction of momentum with volume confirmation.

    Squeeze detection (per bar):
        BB_upper < KC_upper AND BB_lower > KC_lower => squeeze ON

    Entry conditions (all must be true):
        1. Previous bar was in squeeze, current bar is NOT (squeeze fired)
        2. Close is directional (up for LONG, down for SHORT)
        3. MACD histogram confirms direction and is accelerating
        4. SuperTrend agrees with direction
        5. Volume exceeds threshold * average volume

    Required parameters:
        bb_period, bb_std_dev, kc_ema_period, kc_atr_period,
        kc_multiplier, macd_fast, macd_slow, macd_signal,
        volume_threshold, supertrend_period, supertrend_multiplier,
        atr_period, time_stop_bars
    """

    @property
    def template_id(self) -> str:
        """Return template ID for BB Squeeze Momentum strategy."""
        return "bb_squeeze_momentum"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars needed.

        Worst case: macd_slow(26) + macd_signal(9) + squeeze detection(2)
        + KC warmup(max(20, 15)) + buffer = ~60 bars.
        """
        return 60

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate BB Squeeze Momentum Breakout conditions.

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
            # Extract parameters
            bb_period = int(params["bb_period"])
            bb_std = float(params["bb_std_dev"])
            kc_ema_period = int(params["kc_ema_period"])
            kc_atr_period = int(params["kc_atr_period"])
            kc_multiplier = float(params["kc_multiplier"])
            macd_fast = int(params["macd_fast"])
            macd_slow = int(params["macd_slow"])
            macd_signal_period = int(params["macd_signal"])
            vol_threshold = float(params["volume_threshold"])
            st_period = int(params["supertrend_period"])
            st_multiplier = float(params["supertrend_multiplier"])
            atr_period = int(params["atr_period"])
            time_stop_bars = int(params.get("time_stop_bars", 20))

            # Calculate indicators
            bb = BollingerBands(
                period=bb_period, multiplier=bb_std,
            ).calculate(series)
            kc = KeltnerChannel(
                ema_period=kc_ema_period,
                atr_period=kc_atr_period,
                multiplier=kc_multiplier,
            ).calculate(series)
            macd_result = MACD(
                fast_period=macd_fast,
                slow_period=macd_slow,
                signal_period=macd_signal_period,
            ).calculate(series)
            vol_avg = VolumeAverage(period=bb_period).calculate(series)
            st = SuperTrend(
                period=st_period, multiplier=st_multiplier,
            ).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            # Current bar index
            last_idx = len(series) - 1
            prev_idx = last_idx - 1
            if prev_idx < 0:
                return None

            # Validate critical indicator values are not NaN
            critical = [
                bb.upper[last_idx], bb.lower[last_idx], bb.middle[last_idx],
                kc.upper[last_idx], kc.lower[last_idx],
                bb.upper[prev_idx], bb.lower[prev_idx],
                kc.upper[prev_idx], kc.lower[prev_idx],
            ]
            if any(np.isnan(v) for v in critical):
                return None

            # MACD histogram: need at least 2 valid values
            valid_hist = macd_result.histogram[~np.isnan(macd_result.histogram)]
            if len(valid_hist) < 2:
                return None
            hist_current = float(valid_hist[-1])
            hist_prev = float(valid_hist[-2])

            # Volume average
            vol_ma = vol_avg.current
            if np.isnan(vol_ma) or vol_ma <= 0:
                return None

            # ATR for stop calculation
            atr_current = atr_result.current
            if np.isnan(atr_current) or atr_current <= 0:
                return None

            # --- TTM Squeeze Detection ---
            # Squeeze = BB bands fit inside Keltner bands
            prev_squeeze = (
                bb.upper[prev_idx] < kc.upper[prev_idx]
                and bb.lower[prev_idx] > kc.lower[prev_idx]
            )
            curr_squeeze = (
                bb.upper[last_idx] < kc.upper[last_idx]
                and bb.lower[last_idx] > kc.lower[last_idx]
            )

            # Squeeze must fire: was squeezed, now released
            squeeze_fired = prev_squeeze and not curr_squeeze
            if not squeeze_fired:
                return None

            # --- Volume Confirmation ---
            price = float(series.closes[last_idx])
            current_volume = float(series.volumes[last_idx])
            volume_ok = current_volume > vol_ma * vol_threshold
            if not volume_ok:
                return None

            # --- Direction Filters ---
            macd_bullish = hist_current > 0 and hist_current > hist_prev
            macd_bearish = hist_current < 0 and hist_current < hist_prev
            st_trend = st.current_trend  # +1 bullish, -1 bearish
            prev_close = float(series.closes[prev_idx])
            close_bullish = price > prev_close
            close_bearish = price < prev_close

            # Indicator snapshot for signal metadata
            indicators = {
                "bb_upper": float(bb.upper[last_idx]),
                "bb_middle": float(bb.middle[last_idx]),
                "bb_lower": float(bb.lower[last_idx]),
                "bb_width": float(bb.width[last_idx])
                if not np.isnan(bb.width[last_idx]) else 0.0,
                "kc_upper": float(kc.upper[last_idx]),
                "kc_lower": float(kc.lower[last_idx]),
                "macd_histogram": hist_current,
                "supertrend_trend": float(st_trend),
                "atr": atr_current,
                "volume_ratio": current_volume / vol_ma,
            }

            # --- LONG: squeeze release + bullish momentum ---
            if close_bullish and macd_bullish and st_trend == 1:
                vol_ratio = current_volume / vol_ma
                strength = self._calc_strength(
                    vol_ratio, vol_threshold, hist_current, price,
                )
                stop_loss = price - 2.5 * atr_current
                # TP at 2.5×ATR: symmetric with stop (R:R = 1:1).
                # BB upper at squeeze fire is near price (bands just expanded),
                # so using ATR avoids trivially small TP distances.
                take_profit = price + 2.5 * atr_current

                return TradingSignal(
                    direction=SignalDirection.LONG,
                    symbol=symbol,
                    price=price,
                    strength=strength,
                    stop_loss=max(stop_loss, price * 0.001),
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={
                        "trigger": "bb_squeeze_momentum_long",
                        "squeeze_type": "ttm",
                        "atr_stop_distance": 2.5 * atr_current,
                        "time_stop_bars": time_stop_bars,
                    },
                )

            # --- SHORT: squeeze release + bearish momentum ---
            if close_bearish and macd_bearish and st_trend == -1:
                vol_ratio = current_volume / vol_ma
                strength = self._calc_strength(
                    vol_ratio, vol_threshold, hist_current, price,
                )
                stop_loss = price + 2.5 * atr_current
                # TP at 2.5×ATR: symmetric with stop (R:R = 1:1).
                take_profit = price - 2.5 * atr_current

                return TradingSignal(
                    direction=SignalDirection.SHORT,
                    symbol=symbol,
                    price=price,
                    strength=strength,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={
                        "trigger": "bb_squeeze_momentum_short",
                        "squeeze_type": "ttm",
                        "atr_stop_distance": 2.5 * atr_current,
                        "time_stop_bars": time_stop_bars,
                    },
                )

        except (ValueError, KeyError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None

    @staticmethod
    def _calc_strength(
        vol_ratio: float,
        vol_threshold: float,
        histogram: float,
        price: float,
    ) -> float:
        """Calculate signal strength from volume and momentum.

        Combines volume ratio excess above threshold with MACD histogram
        magnitude relative to price. Clamped to [0.3, 1.0].

        Args:
            vol_ratio: Current volume / average volume.
            vol_threshold: Minimum volume ratio for signal.
            histogram: Current MACD histogram value.
            price: Current close price.

        Returns:
            Signal strength between 0.3 and 1.0.
        """
        # Base strength 0.5, add volume bonus and momentum bonus
        vol_bonus = (vol_ratio - vol_threshold) * 0.15
        momentum_bonus = abs(histogram) / (price * 0.001 + 1) * 0.1
        strength = 0.5 + vol_bonus + momentum_bonus
        return max(0.3, min(1.0, strength))
