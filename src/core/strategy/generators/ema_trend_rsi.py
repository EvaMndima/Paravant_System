"""EMA Trend + RSI Filter signal generator.

Entry: EMA crossover with RSI momentum confirmation.
Exit: EMA cross-back or RSI extreme reversal.

Template ID: ema_trend_rsi
Strategy Type: trend_following
"""
from __future__ import annotations

from typing import Any

from src.core.exceptions import SignalGenerationError
from src.core.indicators import ATR, EMA, RSI
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class EmaTrendRsiGenerator(SignalGenerator):
    """Signal generator for the EMA Trend + RSI Filter strategy.

    Produces LONG signals when the fast EMA crosses above the slow EMA
    with RSI confirmation, and SHORT signals on the inverse crossover.
    Also produces CLOSE signals on RSI extremes.

    Required parameters:
        fast_ema_period, slow_ema_period, rsi_period,
        rsi_buy_threshold, rsi_sell_threshold,
        rsi_overbought, rsi_oversold,
        atr_multiplier, atr_period

    Optional parameters:
        risk_reward_ratio: Take-profit distance as multiple of stop risk.
            Default 2.0 (2:1 R:R). Increase to 3.0-4.0 in strong trends
            where the fixed TP exits too early.
    """

    @property
    def template_id(self) -> str:
        return "ema_trend_rsi"

    @property
    def min_bars_required(self) -> int:
        # slow_ema_period (up to 200) + buffer
        return 210

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate EMA crossover + RSI conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if entry/exit conditions met, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            fast_period: int = int(params["fast_ema_period"])
            slow_period: int = int(params["slow_ema_period"])
            rsi_period: int = int(params["rsi_period"])
            rsi_buy: float = float(params["rsi_buy_threshold"])
            rsi_sell: float = float(params["rsi_sell_threshold"])
            rsi_overbought: float = float(params["rsi_overbought"])
            rsi_oversold: float = float(params["rsi_oversold"])
            atr_mult: float = float(params["atr_multiplier"])
            atr_period: int = int(params["atr_period"])
            rr_ratio: float = float(params.get("risk_reward_ratio", 2.0))

            # Calculate indicators
            fast_ema = EMA(period=fast_period).calculate(series)
            slow_ema = EMA(period=slow_period).calculate(series)
            rsi_result = RSI(period=rsi_period).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            fast_curr = fast_ema.current
            fast_prev = fast_ema.previous
            slow_curr = slow_ema.current
            slow_prev = slow_ema.previous
            rsi_curr = rsi_result.current
            atr_curr = atr_result.current
            price = float(series.closes[-1])

            indicators = {
                "fast_ema": fast_curr,
                "slow_ema": slow_curr,
                "rsi": rsi_curr,
                "atr": atr_curr,
            }

            # LONG entry: fast EMA crosses above slow EMA + RSI > buy threshold
            if fast_prev <= slow_prev and fast_curr > slow_curr and rsi_curr > rsi_buy:
                risk = atr_mult * atr_curr
                stop_loss = price - risk
                take_profit = price + rr_ratio * risk
                return TradingSignal(
                    direction=SignalDirection.LONG,
                    symbol=symbol,
                    price=price,
                    strength=min(1.0, (rsi_curr - rsi_buy) / (rsi_overbought - rsi_buy)),
                    stop_loss=max(stop_loss, price * 0.001),
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={"trigger": "ema_crossover_bullish"},
                )

            # SHORT entry: fast EMA crosses below slow EMA + RSI < sell threshold
            if fast_prev >= slow_prev and fast_curr < slow_curr and rsi_curr < rsi_sell:
                risk = atr_mult * atr_curr
                stop_loss = price + risk
                take_profit = price - rr_ratio * risk
                return TradingSignal(
                    direction=SignalDirection.SHORT,
                    symbol=symbol,
                    price=price,
                    strength=min(1.0, (rsi_sell - rsi_curr) / (rsi_sell - rsi_oversold)),
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={"trigger": "ema_crossover_bearish"},
                )

            # CLOSE on RSI extremes
            if rsi_curr > rsi_overbought:
                return TradingSignal(
                    direction=SignalDirection.CLOSE,
                    symbol=symbol,
                    price=price,
                    strength=min(1.0, (rsi_curr - rsi_overbought) / (100 - rsi_overbought)),
                    indicators=indicators,
                    metadata={"trigger": "rsi_overbought_exit"},
                )

            if rsi_curr < rsi_oversold:
                return TradingSignal(
                    direction=SignalDirection.CLOSE,
                    symbol=symbol,
                    price=price,
                    strength=min(1.0, (rsi_oversold - rsi_curr) / rsi_oversold),
                    indicators=indicators,
                    metadata={"trigger": "rsi_oversold_exit"},
                )

        except (ValueError, KeyError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None
