"""MACD Pullback signal generator.

Entry: MACD confirms trend, price pulls back to EMA.
Exit: MACD crossover reversal or ATR-based stop loss.

Template ID: macd_pullback
Strategy Type: trend_continuation
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import ATR, EMA, MACD
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MacdPullbackGenerator(SignalGenerator):
    """Signal generator for the MACD Pullback strategy.

    Identifies pullbacks within established MACD trends. Enters when
    price pulls back to the pullback EMA while MACD confirms trend
    direction.

    Required parameters:
        macd_fast, macd_slow, macd_signal, pullback_ema_period,
        atr_period, atr_stop_multiplier, risk_reward_ratio,
        pullback_tolerance_pct

    Optional parameters:
        regime_ema_period (int, default 0): When > 0, acts as a macro regime
            gate. LONG signals are blocked when price <= regime EMA (bear
            macro context). SHORT signals are blocked when price >= regime EMA
            (bull macro context). Set to 200 in bull-regime paper trading to
            prevent spurious SHORT signals during MACD dips.
    """

    @property
    def template_id(self) -> str:
        return "macd_pullback"

    @property
    def min_bars_required(self) -> int:
        # macd_slow + macd_signal + pullback_ema + buffer
        return 60

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate MACD pullback conditions.

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
            macd_fast: int = int(params["macd_fast"])
            macd_slow: int = int(params["macd_slow"])
            macd_signal_period: int = int(params["macd_signal"])
            pullback_ema_period: int = int(params["pullback_ema_period"])
            atr_period: int = int(params["atr_period"])
            atr_stop_mult: float = float(params["atr_stop_multiplier"])
            rr_ratio: float = float(params["risk_reward_ratio"])
            pullback_tol: float = float(params["pullback_tolerance_pct"])
            regime_ema_period: int = int(params.get("regime_ema_period", 0))

            # Calculate indicators
            macd_result = MACD(
                fast_period=macd_fast,
                slow_period=macd_slow,
                signal_period=macd_signal_period,
            ).calculate(series)
            pullback_ema = EMA(period=pullback_ema_period).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            price = float(series.closes[-1])
            ema_val = pullback_ema.current
            atr_val = atr_result.current

            # --- Optional macro regime gate ---
            # When regime_ema_period > 0, compute a slow EMA to classify the
            # macro trend. LONG signals are blocked below the regime EMA (bear
            # macro); SHORT signals are blocked above it (bull macro). Setting
            # regime_ema_period=200 in the bull-regime paper-trading config
            # eliminates spurious SHORT signals during transient MACD dips.
            in_bull_regime: bool | None = None
            if regime_ema_period > 0 and len(series) >= regime_ema_period:
                regime_ema_result = EMA(period=regime_ema_period).calculate(series)
                regime_vals = regime_ema_result.values[~np.isnan(regime_ema_result.values)]
                if len(regime_vals) >= 1:
                    in_bull_regime = price > float(regime_vals[-1])

            long_allowed  = in_bull_regime is None or in_bull_regime
            short_allowed = in_bull_regime is None or not in_bull_regime

            # MACD state
            macd_curr = macd_result.current
            macd_signal_val = float(
                macd_result.signal_line[
                    ~(np.isnan(macd_result.signal_line))
                ][-1]
            )
            hist_curr = float(
                macd_result.histogram[
                    ~(np.isnan(macd_result.histogram))
                ][-1]
            )
            hist_prev = float(
                macd_result.histogram[
                    ~(np.isnan(macd_result.histogram))
                ][-2]
            )

            # Pullback tolerance band around EMA
            tol_band = ema_val * (pullback_tol / 100.0)
            is_near_ema = abs(price - ema_val) <= tol_band

            indicators = {
                "macd": macd_curr,
                "macd_signal": macd_signal_val,
                "macd_histogram": hist_curr,
                "pullback_ema": ema_val,
                "atr": atr_val,
                "price_ema_distance_pct": abs(price - ema_val) / ema_val * 100 if ema_val > 0 else 0,
            }

            # LONG: MACD > signal (bullish) + price pulled back to EMA +
            # histogram positive and increasing
            if (
                long_allowed
                and macd_curr > macd_signal_val
                and hist_curr > 0
                and hist_curr > hist_prev
                and is_near_ema
            ):
                stop_loss = ema_val - (atr_stop_mult * atr_val)
                risk = price - stop_loss
                # Fallback: if risk ≤ 0 (flat market / zero ATR edge case),
                # use a full ATR unit so take_profit is never None.
                if risk <= 0:
                    risk = atr_stop_mult * atr_val
                take_profit = price + (risk * rr_ratio)

                return TradingSignal(
                    direction=SignalDirection.LONG,
                    symbol=symbol,
                    price=price,
                    strength=min(1.0, hist_curr / (atr_val * 0.5 + 1)),
                    stop_loss=max(stop_loss, price * 0.001),
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={"trigger": "macd_pullback_long"},
                )

            # SHORT: MACD < signal (bearish) + price rallied to EMA +
            # histogram negative and decreasing.
            # Blocked when in bull macro regime (regime_ema_period > 0 and
            # price > regime EMA) to prevent spurious shorts during bull dips.
            if (
                short_allowed
                and macd_curr < macd_signal_val
                and hist_curr < 0
                and hist_curr < hist_prev
                and is_near_ema
            ):
                stop_loss = ema_val + (atr_stop_mult * atr_val)
                risk = stop_loss - price
                if risk <= 0:
                    risk = atr_stop_mult * atr_val
                take_profit = price - (risk * rr_ratio)

                return TradingSignal(
                    direction=SignalDirection.SHORT,
                    symbol=symbol,
                    price=price,
                    strength=min(1.0, abs(hist_curr) / (atr_val * 0.5 + 1)),
                    stop_loss=stop_loss,
                    take_profit=max(take_profit, price * 0.001),
                    indicators=indicators,
                    metadata={"trigger": "macd_pullback_short"},
                )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None
