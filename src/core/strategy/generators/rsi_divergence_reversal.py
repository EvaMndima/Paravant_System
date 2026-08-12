"""RSI Divergence Reversal signal generator.

Detects classic RSI divergence: price makes a new extreme but RSI
fails to confirm, signalling exhaustion of the prevailing trend.

Bullish divergence (LONG entry):
    - Price makes a lower low compared to a prior confirmed swing low
    - RSI makes a higher low at the same swing point (momentum improving)
    - Current RSI is turning up (reversal confirmation)

Bearish divergence (SHORT entry):
    - Price makes a higher high compared to a prior confirmed swing high
    - RSI makes a lower high at the same swing point (momentum weakening)
    - Current RSI is turning down (reversal confirmation)

Swing detection is restricted to historical bars with confirmed right-side
context (bars[:-swing_bars]), eliminating lookahead bias.

Template ID: rsi_divergence_reversal
Strategy Type: reversal
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


class RsiDivergenceReversalGenerator(SignalGenerator):
    """Signal generator for RSI Divergence Reversal strategy.

    Identifies turning points by detecting disagreement between price
    action and RSI momentum. Two confirmed swing pivots are required
    for the divergence, plus a current-bar confirmation that RSI
    is already reversing direction. This three-part filter (swing 1,
    swing 2, confirmation bar) keeps false divergence signals low.

    Required parameters:
        rsi_period, swing_bars, divergence_lookback,
        atr_period, atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        """Return template ID."""
        return "rsi_divergence_reversal"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars needed.

        rsi_period(14) + divergence_lookback(50) + swing_bars(5)*2 + buffer = 100.
        """
        return 100

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate RSI Divergence Reversal entry conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if divergence confirmed with reversal signal, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            rsi_period: int = int(params["rsi_period"])
            swing_bars: int = int(params["swing_bars"])
            divergence_lookback: int = int(params["divergence_lookback"])
            atr_period: int = int(params["atr_period"])
            atr_stop_mult: float = float(params["atr_stop_multiplier"])
            rr_ratio: float = float(params["risk_reward_ratio"])
            regime_ema_period: int = int(params.get("regime_ema_period", 0))

            rsi_result = RSI(period=rsi_period).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            # Regime gate: in bull regime, only bullish divergence (LONG); in bear, only bearish (SHORT)
            # Guard: skip gate if series too short for the regime EMA period
            in_bull_regime: bool | None = None
            if regime_ema_period > 0 and len(series) >= regime_ema_period:
                regime_ema = EMA(period=regime_ema_period).calculate(series)
                regime_ema_vals = regime_ema.values[~np.isnan(regime_ema.values)]
                if len(regime_ema_vals) >= 1:
                    price_check = float(series.closes[-1])
                    in_bull_regime = price_check > float(regime_ema_vals[-1])

            long_allowed = in_bull_regime is None or in_bull_regime
            short_allowed = in_bull_regime is None or not in_bull_regime

            # Full RSI array including NaN prefix for index-aligned access
            rsi_full = rsi_result.values
            rsi_vals = rsi_full[~np.isnan(rsi_full)]

            if len(rsi_vals) < 2:
                return None

            rsi_curr = float(rsi_vals[-1])
            rsi_prev = float(rsi_vals[-2])

            atr_curr = float(atr_result.current)
            price = float(series.closes[-1])

            lows = series.lows
            highs = series.highs
            n = len(lows)

            # Search region: must have swing_bars confirmed future bars to avoid lookahead
            search_end = n - swing_bars
            search_start = max(swing_bars, search_end - divergence_lookback)

            if search_end <= search_start:
                return None

            # Find confirmed swing lows for bullish divergence
            swing_lows: list[tuple[int, float, float]] = []
            for i in range(search_start, search_end):
                if np.isnan(rsi_full[i]):
                    continue
                left_ok = all(lows[i] < lows[i - j] for j in range(1, swing_bars + 1))
                right_ok = all(lows[i] < lows[i + j] for j in range(1, swing_bars + 1))
                if left_ok and right_ok:
                    swing_lows.append((i, float(lows[i]), float(rsi_full[i])))

            # Find confirmed swing highs for bearish divergence
            swing_highs: list[tuple[int, float, float]] = []
            for i in range(search_start, search_end):
                if np.isnan(rsi_full[i]):
                    continue
                left_ok = all(highs[i] > highs[i - j] for j in range(1, swing_bars + 1))
                right_ok = all(highs[i] > highs[i + j] for j in range(1, swing_bars + 1))
                if left_ok and right_ok:
                    swing_highs.append((i, float(highs[i]), float(rsi_full[i])))

            indicators: dict[str, float | str] = {
                "rsi": rsi_curr,
                "atr": atr_curr,
                "swing_lows_found": len(swing_lows),
                "swing_highs_found": len(swing_highs),
            }

            # --- LONG: bullish divergence + RSI turning up (only allowed in bull regime) ---
            if long_allowed and len(swing_lows) >= 2 and rsi_curr > rsi_prev:
                prior = swing_lows[-2]
                last = swing_lows[-1]

                price_lower_low = last[1] < prior[1]
                rsi_higher_low = last[2] > prior[2]

                if price_lower_low and rsi_higher_low:
                    rsi_divergence_strength = (last[2] - prior[2]) / (abs(prior[2]) + 1e-9)
                    risk = atr_stop_mult * atr_curr
                    stop_loss = price - risk
                    take_profit = price + risk * rr_ratio

                    strength = min(
                        1.0,
                        0.55
                        + min(0.3, rsi_divergence_strength * 0.3)
                        + min(0.15, (rsi_curr - rsi_prev) * 0.05),
                    )

                    indicators["divergence_type"] = "bullish"
                    indicators["price_swing_diff"] = round(last[1] - prior[1], 4)
                    indicators["rsi_swing_diff"] = round(last[2] - prior[2], 2)

                    return TradingSignal(
                        direction=SignalDirection.LONG,
                        symbol=symbol,
                        price=price,
                        strength=max(0.4, strength),
                        stop_loss=max(stop_loss, price * 0.001),
                        take_profit=take_profit,
                        indicators=indicators,
                        metadata={
                            "trigger": "rdr_bullish_divergence",
                            "rsi_div_strength": round(rsi_divergence_strength, 3),
                            "swing_count": len(swing_lows),
                        },
                    )

            # --- SHORT: bearish divergence + RSI turning down (only allowed in bear regime) ---
            if short_allowed and len(swing_highs) >= 2 and rsi_curr < rsi_prev:
                prior = swing_highs[-2]
                last = swing_highs[-1]

                price_higher_high = last[1] > prior[1]
                rsi_lower_high = last[2] < prior[2]

                if price_higher_high and rsi_lower_high:
                    rsi_divergence_strength = (prior[2] - last[2]) / (abs(prior[2]) + 1e-9)
                    risk = atr_stop_mult * atr_curr
                    stop_loss = price + risk
                    take_profit = price - risk * rr_ratio

                    strength = min(
                        1.0,
                        0.55
                        + min(0.3, rsi_divergence_strength * 0.3)
                        + min(0.15, (rsi_prev - rsi_curr) * 0.05),
                    )

                    indicators["divergence_type"] = "bearish"
                    indicators["price_swing_diff"] = round(last[1] - prior[1], 4)
                    indicators["rsi_swing_diff"] = round(last[2] - prior[2], 2)

                    return TradingSignal(
                        direction=SignalDirection.SHORT,
                        symbol=symbol,
                        price=price,
                        strength=max(0.4, strength),
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        indicators=indicators,
                        metadata={
                            "trigger": "rdr_bearish_divergence",
                            "rsi_div_strength": round(rsi_divergence_strength, 3),
                            "swing_count": len(swing_highs),
                        },
                    )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None
