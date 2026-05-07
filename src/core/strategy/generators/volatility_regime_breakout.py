"""Volatility Regime Breakout signal generator.

Detects the squeeze-release pattern using Bollinger Band width as the
compression measure. BB width is price-normalized ((upper-lower)/middle*100),
making it regime-agnostic: it compresses during local consolidations inside
trending markets as well as during sideways ranges.

The prior ATR-based implementation used absolute volatility which never
triggered in sustained trending markets (ATR stays elevated in dollar terms
even during quiet bars at high price levels). BB width solves this by
measuring volatility relative to current price.

Entry conditions (LONG):
    1. BB width recently compressed to a local percentile low (local squeeze)
    2. BB width is now expanding above its recent mean (squeeze releasing)
    3. Price breaks above the HIGH of the squeeze window (range breakout)
    4. Volume above vol_ma * volume_threshold (participation confirms move)

SHORT conditions are the symmetric inverse.

Reference window:
    The squeeze_percentile is evaluated against a FIXED reference_lookback
    window of bars immediately before the squeeze window (default 100 bars).
    This anchors "compressed" to recent volatility context rather than
    all-time history. Using all available history caused 0 trades in 90-day
    backtests: local consolidations never reached the 20th percentile of a
    2100-bar distribution spanning multiple volatility regimes.

Breakout level:
    Uses the squeeze window's own high/low (max/min of series.highs over the
    squeeze_lookback bars) rather than a separate Donchian channel. The Donchian
    upper includes bars BEFORE the squeeze (when price was higher), causing
    zero breakout triggers even when price is only 0.17% below the level.
    The squeeze-window high is the natural resistance to break.

Optional: regime_ema_period > 0 restricts LONG to bull regime and SHORT
to bear regime, preventing counter-trend entries.

Template ID: volatility_regime_breakout
Strategy Type: breakout
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import ATR, EMA, BollingerBands
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Minimum number of prior BB width samples required for percentile calculation
_MIN_REFERENCE_SAMPLES = 30


class VolatilityRegimeBreakoutGenerator(SignalGenerator):
    """Signal generator for Volatility Regime Breakout strategy.

    Detects local squeeze-release cycles using Bollinger Band width. BB width
    is price-normalized, so it compresses during mini-consolidations inside
    trending markets — not just during sideways regimes. When a local squeeze
    releases (BB width expands above its recent mean) and price simultaneously
    breaks the Donchian channel, the breakout is confirmed.

    Required parameters:
        bb_period, bb_std_dev,
        squeeze_lookback, squeeze_percentile, reference_lookback,
        volume_period, volume_threshold,
        atr_period, atr_stop_multiplier, risk_reward_ratio

    Optional parameters:
        regime_ema_period: When > 0, restricts LONG to price > EMA and
            SHORT to price < EMA. Default 0 disables gate.
    """

    @property
    def template_id(self) -> str:
        """Return template ID."""
        return "volatility_regime_breakout"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars needed.

        bb_period(20) warmup + reference_lookback(100) + squeeze_lookback(20)
        + donchian(20) + buffer = 160.
        """
        return 160

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate Volatility Regime Breakout entry conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if BB squeeze releases into Donchian breakout, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            bb_period: int = int(params["bb_period"])
            bb_std_dev: float = float(params["bb_std_dev"])
            squeeze_lookback: int = int(params["squeeze_lookback"])
            squeeze_percentile: float = float(params["squeeze_percentile"])
            reference_lookback: int = int(params.get("reference_lookback", 100))
            volume_period: int = int(params["volume_period"])
            volume_threshold: float = float(params["volume_threshold"])
            atr_period: int = int(params["atr_period"])
            atr_stop_mult: float = float(params["atr_stop_multiplier"])
            rr_ratio: float = float(params["risk_reward_ratio"])
            regime_ema_period: int = int(params.get("regime_ema_period", 0))

            bb = BollingerBands(period=bb_period, multiplier=bb_std_dev).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            # Strip NaNs from BB width — these are price-normalized percentage values
            bb_width_vals = bb.width[~np.isnan(bb.width)]

            # Need: reference window + squeeze window + current bar
            if len(bb_width_vals) < reference_lookback + squeeze_lookback + 1:
                return None

            # Reference distribution: fixed window of reference_lookback bars ending just
            # before the squeeze window. A fixed window (not all-time history) ensures
            # "squeeze" means compressed relative to RECENT context, not the full series.
            # All-time history caused 0 trades in 90d: local consolidations never reached
            # the 20th percentile of a 2100-bar multi-regime distribution.
            ref_end = -(squeeze_lookback + 1)
            ref_start = ref_end - reference_lookback
            prior_widths = bb_width_vals[ref_start:ref_end]
            if len(prior_widths) < _MIN_REFERENCE_SAMPLES:
                return None

            # Squeeze threshold: the Nth percentile of the recent reference window
            # Below this level = "compressed relative to recent volatility context"
            squeeze_threshold = float(np.percentile(prior_widths, squeeze_percentile))

            # Recent window: the squeeze_lookback bars before current bar (not including current)
            recent_window = bb_width_vals[-(squeeze_lookback + 1):-1]
            width_recent_min = float(np.min(recent_window))
            width_recent_mean = float(np.mean(recent_window))

            # Width was compressed: at least one bar in the window reached a local squeeze
            was_squeezed = width_recent_min < squeeze_threshold

            # Width is now expanding: current bar is above the recent window mean
            # (volatility returning after the consolidation)
            width_curr = float(bb_width_vals[-1])
            is_expanding = width_curr > width_recent_mean

            if not (was_squeezed and is_expanding):
                return None

            # Volume confirmation
            volumes = series.volumes
            valid_vols = volumes[~np.isnan(volumes)]
            if len(valid_vols) < volume_period + 1:
                return None
            vol_ma = float(np.mean(valid_vols[-(volume_period + 1):-1]))
            vol_curr = float(valid_vols[-1])

            if vol_ma <= 0 or vol_curr <= vol_ma * volume_threshold:
                return None

            # ATR for stop/target sizing
            atr_vals = atr_result.values[~np.isnan(atr_result.values)]
            if len(atr_vals) < 1:
                return None
            atr_curr = float(atr_vals[-1])

            # Breakout levels: high/low of the squeeze window itself.
            # Using Donchian-20 caused 0 triggers because it records the highest
            # high over 20 bars including bars BEFORE the squeeze (when price was
            # higher). The squeeze window high is the actual consolidation ceiling
            # that price needs to break to confirm the squeeze-release move.
            highs = series.highs
            lows  = series.lows
            if len(highs) < squeeze_lookback + 1:
                return None
            upper_curr = float(np.max(highs[-(squeeze_lookback + 1):-1]))
            lower_curr = float(np.min(lows[-(squeeze_lookback + 1):-1]))

            price = float(series.closes[-1])

            # Regime gate: restricts direction to macro trend when active
            in_bull_regime: bool | None = None
            if regime_ema_period > 0 and len(series) >= regime_ema_period:
                regime_ema = EMA(period=regime_ema_period).calculate(series)
                regime_ema_vals = regime_ema.values[~np.isnan(regime_ema.values)]
                if len(regime_ema_vals) >= 1:
                    in_bull_regime = price > float(regime_ema_vals[-1])

            long_allowed = in_bull_regime is None or in_bull_regime
            short_allowed = in_bull_regime is None or not in_bull_regime

            # Squeeze metrics for signal strength and diagnostics
            squeeze_depth = 1.0 - width_recent_min / squeeze_threshold if squeeze_threshold > 0 else 0.0
            width_expansion = width_curr / width_recent_mean if width_recent_mean > 0 else 1.0

            indicators = {
                "bb_width_curr": round(width_curr, 3),
                "bb_width_squeeze_threshold": round(squeeze_threshold, 3),
                "bb_width_min_recent": round(width_recent_min, 3),
                "squeeze_depth_pct": round(squeeze_depth * 100, 1),
                "width_expansion_ratio": round(width_expansion, 3),
                "squeeze_range_high": upper_curr,
                "squeeze_range_low": lower_curr,
                "volume_ratio": round(vol_curr / vol_ma, 2),
                "atr": atr_curr,
            }

            strength_base = min(
                1.0,
                0.55
                + min(0.25, squeeze_depth * 0.5)
                + min(0.1, (width_expansion - 1.0) * 0.2)
                + min(0.1, (vol_curr / vol_ma - volume_threshold) * 0.05),
            )

            # LONG: price breaks above Donchian upper after BB squeeze releases
            if long_allowed and price > upper_curr:
                risk = atr_stop_mult * atr_curr
                stop_loss = price - risk
                take_profit = price + risk * rr_ratio

                return TradingSignal(
                    direction=SignalDirection.LONG,
                    symbol=symbol,
                    price=price,
                    strength=max(0.4, strength_base),
                    stop_loss=max(stop_loss, price * 0.001),
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={
                        "trigger": "vrb_long_squeeze_range_break",
                        "squeeze_depth_pct": indicators["squeeze_depth_pct"],
                        "width_expansion_ratio": indicators["width_expansion_ratio"],
                        "vol_ratio": indicators["volume_ratio"],
                    },
                )

            # SHORT: price breaks below Donchian lower after BB squeeze releases
            if short_allowed and price < lower_curr:
                risk = atr_stop_mult * atr_curr
                stop_loss = price + risk
                take_profit = price - risk * rr_ratio

                return TradingSignal(
                    direction=SignalDirection.SHORT,
                    symbol=symbol,
                    price=price,
                    strength=max(0.4, strength_base),
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={
                        "trigger": "vrb_short_squeeze_range_break",
                        "squeeze_depth_pct": indicators["squeeze_depth_pct"],
                        "width_expansion_ratio": indicators["width_expansion_ratio"],
                        "vol_ratio": indicators["volume_ratio"],
                    },
                )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None
