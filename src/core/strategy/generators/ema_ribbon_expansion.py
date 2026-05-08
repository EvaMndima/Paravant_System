"""EMA Ribbon Expansion signal generator.

Measures the spread (ribbon width) between three EMAs — fast (8), medium (21),
and slow (50) — as a percentage of price. During healthy pullbacks in bull trends
the ribbon contracts as EMAs converge. When the ribbon re-expands from a
compressed state with all three EMAs still in bull alignment, the uptrend is
resuming and provides a high-probability long entry.

Quant basis: EMA ribbon compression during pullbacks is a structural resting
signal distinct from price-volatility compression (BB width) or RSI dips. The
spread between EMAs measures trend *momentum geometry* — EMAs converging means
short-term and long-term trend momentum are temporarily in sync at a lower
level. Re-expansion confirms the trend is accelerating again.

This is the "staircase up" pattern quantified: rest (compress) → resume (expand).

Entry conditions (LONG only — bull regime strategy):
    1. All three EMAs in bull order: EMA(fast) > EMA(medium) > EMA(slow)
    2. Price above EMA(fast) — riding the trend, not fighting it
    3. Ribbon recently compressed: min(ribbon_width[-lookback:]) below threshold
    4. Ribbon now expanding: current ribbon_width > mean(ribbon_width[-lookback:])
    5. Volume confirmation: current vol > vol_ma * volume_threshold

Template ID: ema_ribbon_expansion
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

_MIN_RIBBON_SAMPLES = 10


class EmaRibbonExpansionGenerator(SignalGenerator):
    """Signal generator for EMA Ribbon Expansion strategy.

    Detects the EMA ribbon compression-expansion cycle. Ribbon width is
    (EMA_fast - EMA_slow) / price * 100. Compression during pullbacks in
    uptrends is healthy; re-expansion signals trend resumption.

    Required parameters:
        fast_ema_period, medium_ema_period, slow_ema_period,
        ribbon_lookback, ribbon_percentile,
        volume_period, volume_threshold,
        atr_period, atr_stop_multiplier, risk_reward_ratio

    Optional parameters:
        regime_ema_period: When > 0, restricts LONG to price > EMA. Default 0 disables.
        rsi_period, rsi_min, rsi_max: RSI confirmation filter. rsi_period=0 disables.
    """

    @property
    def template_id(self) -> str:
        return "ema_ribbon_expansion"

    @property
    def min_bars_required(self) -> int:
        """EMA(50) warmup + ribbon_lookback(20) + volume(20) + buffer."""
        return 120

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate EMA Ribbon Expansion entry conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if ribbon re-expands from compression in bull
            alignment with volume, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            fast_period: int    = int(params["fast_ema_period"])
            medium_period: int  = int(params["medium_ema_period"])
            slow_period: int    = int(params["slow_ema_period"])
            ribbon_lookback: int = int(params["ribbon_lookback"])
            ribbon_percentile: float = float(params["ribbon_percentile"])
            volume_period: int  = int(params["volume_period"])
            volume_threshold: float = float(params["volume_threshold"])
            atr_period: int     = int(params["atr_period"])
            atr_stop_mult: float = float(params["atr_stop_multiplier"])
            rr_ratio: float     = float(params["risk_reward_ratio"])
            regime_ema_period: int = int(params.get("regime_ema_period", 0))
            rsi_period: int     = int(params.get("rsi_period", 0))
            rsi_min: float      = float(params.get("rsi_min", 40.0))
            rsi_max: float      = float(params.get("rsi_max", 70.0))

            ema_fast = EMA(period=fast_period).calculate(series)
            ema_med  = EMA(period=medium_period).calculate(series)
            ema_slow = EMA(period=slow_period).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            fast_vals = ema_fast.values[~np.isnan(ema_fast.values)]
            med_vals  = ema_med.values[~np.isnan(ema_med.values)]
            slow_vals = ema_slow.values[~np.isnan(ema_slow.values)]
            atr_vals  = atr_result.values[~np.isnan(atr_result.values)]

            if len(fast_vals) < ribbon_lookback + 1:
                return None
            if len(med_vals) < 1 or len(slow_vals) < ribbon_lookback + 1:
                return None
            if len(atr_vals) < 1:
                return None

            fast_curr = float(fast_vals[-1])
            med_curr  = float(med_vals[-1])
            slow_curr = float(slow_vals[-1])
            atr_curr  = float(atr_vals[-1])
            price     = float(series.closes[-1])

            # Bull alignment: all three EMAs ordered and price above slow EMA
            if not (fast_curr > med_curr > slow_curr):
                return None
            if price < slow_curr:
                return None

            # Macro regime gate: restrict LONG to price > EMA(regime_ema_period)
            # Prevents entries during bear-market relief bounces where the short-term
            # EMA ribbon can briefly align bullishly even in a downtrend.
            if regime_ema_period > 0 and len(series) >= regime_ema_period:
                regime_ema = EMA(period=regime_ema_period).calculate(series)
                regime_vals = regime_ema.values[~np.isnan(regime_ema.values)]
                if len(regime_vals) >= 1 and price <= float(regime_vals[-1]):
                    return None

            # RSI confirmation: optional band filter (rsi_period=0 disables)
            if rsi_period > 0:
                rsi_result = RSI(period=rsi_period).calculate(series)
                rsi_vals   = rsi_result.values[~np.isnan(rsi_result.values)]
                if len(rsi_vals) >= 1:
                    rsi_curr = float(rsi_vals[-1])
                    if not (rsi_min <= rsi_curr <= rsi_max):
                        return None

            # Ribbon width: percentage spread between fast and slow EMA
            # Measures trend momentum geometry — compresses during pullbacks,
            # expands when trend resumes
            n = min(len(fast_vals), len(slow_vals))
            closes_aligned = series.closes[-n:]
            ribbon_widths = (fast_vals[-n:] - slow_vals[-n:]) / (closes_aligned + 1e-9) * 100.0
            ribbon_valid = ribbon_widths[~np.isnan(ribbon_widths)]

            if len(ribbon_valid) < ribbon_lookback + 1:
                return None

            recent = ribbon_valid[-ribbon_lookback - 1:-1]
            if len(recent) < _MIN_RIBBON_SAMPLES:
                return None

            # Compression threshold: Nth percentile of the lookback window
            compress_threshold = float(np.percentile(recent, ribbon_percentile))
            recent_mean = float(np.mean(recent))
            recent_min  = float(np.min(recent))
            ribbon_curr = float(ribbon_valid[-1])

            # Compressed: at least one recent bar reached the compressed state
            was_compressed = recent_min < compress_threshold

            # Expanding: current ribbon wider than the lookback mean (resuming)
            is_expanding = ribbon_curr > recent_mean

            if not (was_compressed and is_expanding):
                return None

            # Volume: current bar has above-average participation
            vols = series.volumes[~np.isnan(series.volumes)]
            if len(vols) < volume_period + 1:
                return None
            vol_ma   = float(np.mean(vols[-(volume_period + 1):-1]))
            vol_curr = float(vols[-1])
            if vol_ma <= 0 or vol_curr <= vol_ma * volume_threshold:
                return None

            # Signal strength: depth of compression + degree of expansion
            compression_depth = (
                1.0 - recent_min / compress_threshold if compress_threshold > 0 else 0.0
            )
            expansion_ratio = ribbon_curr / recent_mean if recent_mean > 0 else 1.0
            strength_base = min(
                1.0,
                0.55
                + min(0.2, compression_depth * 0.4)
                + min(0.15, (expansion_ratio - 1.0) * 0.3)
                + min(0.1, (vol_curr / vol_ma - volume_threshold) * 0.05),
            )

            risk = atr_stop_mult * atr_curr
            stop_loss  = price - risk
            take_profit = price + risk * rr_ratio

            return TradingSignal(
                direction=SignalDirection.LONG,
                symbol=symbol,
                price=price,
                strength=max(0.4, strength_base),
                stop_loss=max(stop_loss, price * 0.001),
                take_profit=take_profit,
                indicators={
                    "ema_fast": round(fast_curr, 4),
                    "ema_medium": round(med_curr, 4),
                    "ema_slow": round(slow_curr, 4),
                    "ribbon_width_curr": round(ribbon_curr, 4),
                    "ribbon_compress_threshold": round(compress_threshold, 4),
                    "ribbon_width_min": round(recent_min, 4),
                    "ribbon_expansion_ratio": round(expansion_ratio, 3),
                    "compression_depth_pct": round(compression_depth * 100, 1),
                    "volume_ratio": round(vol_curr / vol_ma, 2),
                    "atr": atr_curr,
                },
                metadata={
                    "trigger": "eree_long_ribbon_expansion",
                    "compression_depth_pct": round(compression_depth * 100, 1),
                    "expansion_ratio": round(expansion_ratio, 3),
                    "vol_ratio": round(vol_curr / vol_ma, 2),
                },
            )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e
