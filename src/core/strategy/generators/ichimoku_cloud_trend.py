"""Ichimoku Cloud Trend signal generator.

Generates trend-following signals using the Ichimoku Cloud system with
crypto-adjusted periods (20/60/120/30 instead of traditional 9/26/52/26).

Entry LONG: Price above cloud + TK bullish cross + Chikou confirms
            + green cloud + volume spike
Entry SHORT: Price below cloud + TK bearish cross + Chikou confirms
             + red cloud + volume spike
Close: Cloud flip or TK cross against position direction

Template ID: ichimoku_cloud_trend
Strategy Type: trend_following
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import ATR, VolumeAverage
from src.core.indicators.ichimoku import IchimokuCloud
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class IchimokuCloudTrendGenerator(SignalGenerator):
    """Signal generator for Ichimoku Cloud Trend strategy.

    Uses the full Ichimoku Kinko Hyo system adapted for 24/7 crypto markets.
    Traditional equity periods (9/26/52/26) are scaled to crypto equivalents
    (20/60/120/30) to account for continuous trading.

    Five confluence conditions required for entry:
        1. Price vs Cloud: Close above (LONG) or below (SHORT) both Senkou spans
        2. TK Cross: Tenkan-sen crosses Kijun-sen in trade direction
        3. Chikou Span: Current close vs displaced historical close confirms trend
        4. Cloud Color: Senkou A vs Senkou B confirms trend bias
        5. Volume: Current volume exceeds threshold * average

    Required parameters:
        tenkan_period, kijun_period, senkou_b_period, displacement,
        atr_period, volume_period, volume_threshold
    """

    @property
    def template_id(self) -> str:
        """Return template ID for Ichimoku Cloud Trend strategy."""
        return "ichimoku_cloud_trend"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars needed.

        Ichimoku with crypto defaults: senkou_b(120) + displacement(30)
        + ATR warmup(15) + buffer(5) = 170 bars.
        """
        return 170

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate Ichimoku Cloud Trend conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if trend conditions met, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            # Extract parameters
            tenkan_period = int(params["tenkan_period"])
            kijun_period = int(params["kijun_period"])
            senkou_b_period = int(params["senkou_b_period"])
            displacement = int(params["displacement"])
            atr_period = int(params["atr_period"])
            volume_period = int(params["volume_period"])
            vol_threshold = float(params["volume_threshold"])
            # Trailing stop distance in ATR units. Default 2.5 preserves
            # original behaviour; sweep range 2.5-5.0 for optimisation.
            atr_stop_mult = float(params.get("atr_stop_multiplier", 2.5))

            # Calculate indicators
            ichimoku = IchimokuCloud(
                tenkan_period=tenkan_period,
                kijun_period=kijun_period,
                senkou_b_period=senkou_b_period,
                displacement=displacement,
            ).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)
            vol_avg = VolumeAverage(period=volume_period).calculate(series)

            last_idx = len(series) - 1
            price = float(series.closes[last_idx])
            current_volume = float(series.volumes[last_idx])

            # Validate Ichimoku components at current index
            sa = ichimoku.senkou_span_a[last_idx]
            sb = ichimoku.senkou_span_b[last_idx]
            tk = ichimoku.tenkan_sen[last_idx]
            kj = ichimoku.kijun_sen[last_idx]
            chikou = ichimoku.chikou_span[last_idx]

            if any(np.isnan(v) for v in [sa, sb, tk, kj, chikou]):
                return None

            atr_current = atr_result.current
            vol_ma = vol_avg.current
            if np.isnan(atr_current) or atr_current <= 0:
                return None
            if np.isnan(vol_ma) or vol_ma <= 0:
                return None

            # --- Condition 1: Price vs Cloud ---
            cloud_top = max(sa, sb)
            cloud_bottom = min(sa, sb)
            price_above_cloud = price > cloud_top
            price_below_cloud = price < cloud_bottom

            # --- Condition 2: TK Cross ---
            tk_bullish = ichimoku.tk_cross_bullish()
            tk_bearish = ichimoku.tk_cross_bearish()

            # --- Condition 3: Chikou Span Confirmation ---
            # chikou_span[i] = close[i - displacement]
            # Bullish: current close > historical close (trending up)
            chikou_bullish = price > float(chikou)
            chikou_bearish = price < float(chikou)

            # --- Condition 4: Cloud Color ---
            cloud_green = float(sa) > float(sb)  # Bullish cloud
            cloud_red = float(sb) > float(sa)    # Bearish cloud

            # --- Condition 5: Volume ---
            volume_ok = current_volume > vol_ma * vol_threshold

            # Build indicator snapshot
            indicators = {
                "tenkan_sen": float(tk),
                "kijun_sen": float(kj),
                "senkou_span_a": float(sa),
                "senkou_span_b": float(sb),
                "chikou_span": float(chikou),
                "cloud_top": float(cloud_top),
                "cloud_bottom": float(cloud_bottom),
                "atr": atr_current,
                "volume_ratio": current_volume / vol_ma,
            }

            # --- LONG Signal ---
            # All 5 conditions: above cloud + TK bullish + chikou up + green + volume
            if (price_above_cloud and tk_bullish and chikou_bullish
                    and cloud_green and volume_ok):
                strength = self._calc_strength(
                    price, cloud_top, atr_current,
                    current_volume / vol_ma, vol_threshold,
                )
                # Stop below cloud bottom or atr_stop_mult*ATR, whichever is tighter
                stop_loss = max(cloud_bottom, price - atr_stop_mult * atr_current)
                # TP at same ATR distance above entry → R:R ≈ 1:1.
                take_profit = price + atr_stop_mult * atr_current

                return TradingSignal(
                    direction=SignalDirection.LONG,
                    symbol=symbol,
                    price=price,
                    strength=strength,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={
                        "trigger": "ichimoku_cloud_trend_long",
                        "cloud_thickness": float(cloud_top - cloud_bottom),
                        "price_cloud_distance": price - cloud_top,
                    },
                )

            # --- SHORT Signal ---
            # All 5 conditions: below cloud + TK bearish + chikou down + red + volume
            if (price_below_cloud and tk_bearish and chikou_bearish
                    and cloud_red and volume_ok):
                strength = self._calc_strength(
                    price, cloud_bottom, atr_current,
                    current_volume / vol_ma, vol_threshold,
                )
                # Stop above cloud top or atr_stop_mult*ATR, whichever is tighter
                stop_loss = min(cloud_top, price + atr_stop_mult * atr_current)
                # TP mirrors stop distance below entry → R:R ≈ 1:1.
                take_profit = price - atr_stop_mult * atr_current

                return TradingSignal(
                    direction=SignalDirection.SHORT,
                    symbol=symbol,
                    price=price,
                    strength=strength,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={
                        "trigger": "ichimoku_cloud_trend_short",
                        "cloud_thickness": float(cloud_top - cloud_bottom),
                        "price_cloud_distance": cloud_bottom - price,
                    },
                )

            # --- CLOSE Signal ---
            # If price crosses into cloud from above or below, close position
            in_cloud = cloud_bottom <= price <= cloud_top
            if in_cloud:
                # Check if there's a TK cross against a potential position
                if tk_bearish:
                    return TradingSignal(
                        direction=SignalDirection.CLOSE,
                        symbol=symbol,
                        price=price,
                        strength=0.6,
                        indicators=indicators,
                        metadata={
                            "trigger": "ichimoku_cloud_close_bearish_tk",
                        },
                    )
                if tk_bullish:
                    return TradingSignal(
                        direction=SignalDirection.CLOSE,
                        symbol=symbol,
                        price=price,
                        strength=0.6,
                        indicators=indicators,
                        metadata={
                            "trigger": "ichimoku_cloud_close_bullish_tk",
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
        price: float,
        cloud_edge: float,
        atr: float,
        vol_ratio: float,
        vol_threshold: float,
    ) -> float:
        """Calculate signal strength from cloud distance and volume.

        Strength increases with distance from cloud (normalized by ATR)
        and volume excess above threshold.

        Args:
            price: Current close price.
            cloud_edge: Nearest cloud boundary.
            atr: Current ATR value.
            vol_ratio: Current volume / average volume.
            vol_threshold: Minimum volume ratio.

        Returns:
            Signal strength between 0.4 and 1.0.
        """
        # Distance from cloud edge in ATR units
        cloud_dist = abs(price - cloud_edge) / atr if atr > 0 else 0
        dist_score = min(0.3, cloud_dist * 0.1)

        # Volume excess
        vol_score = min(0.2, (vol_ratio - vol_threshold) * 0.1)

        # Ichimoku is high-confluence (5 conditions) so base strength is 0.5
        strength = 0.5 + dist_score + vol_score
        return max(0.4, min(1.0, strength))
