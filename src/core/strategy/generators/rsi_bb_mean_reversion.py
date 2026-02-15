"""RSI + Bollinger Bands Mean Reversion signal generator.

Entry: RSI at extremes AND price at BB bands in low-trend environments.
Exit: RSI normalises or price reaches middle BB.

Template ID: rsi_bb_mean_reversion
Strategy Type: mean_reversion
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import ADX, RSI, BollingerBands
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RsiBbMeanReversionGenerator(SignalGenerator):
    """Signal generator for RSI + BB Mean Reversion strategy.

    Identifies mean-reversion opportunities when RSI is at oversold/overbought
    levels AND price is near BB bands, with ADX confirming low trend strength.

    Required parameters:
        rsi_period, rsi_oversold, rsi_overbought,
        rsi_exit_long, rsi_exit_short,
        bb_period, bb_std_dev,
        adx_threshold, stop_loss_pct
    """

    @property
    def template_id(self) -> str:
        return "rsi_bb_mean_reversion"

    @property
    def min_bars_required(self) -> int:
        # ADX needs 2*period+1 warmup, BB needs period, RSI needs period+1
        return 50

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate mean-reversion conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if mean-reversion conditions met, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            rsi_period: int = int(params["rsi_period"])
            rsi_oversold: float = float(params["rsi_oversold"])
            rsi_overbought: float = float(params["rsi_overbought"])
            rsi_exit_long: float = float(params["rsi_exit_long"])
            # Note: rsi_exit_short reserved for SHORT exit implementation (MVP: long-only)
            bb_period: int = int(params["bb_period"])
            bb_std: float = float(params["bb_std_dev"])
            adx_threshold: float = float(params["adx_threshold"])
            stop_loss_pct: float = float(params["stop_loss_pct"])

            # Calculate indicators
            rsi_result = RSI(period=rsi_period).calculate(series)
            bb = BollingerBands(period=bb_period, multiplier=bb_std).calculate(series)
            adx_result = ADX(period=14).calculate(series)

            price = float(series.closes[-1])
            rsi_curr = rsi_result.current
            adx_curr = adx_result.current

            # Get BB values
            valid_upper = bb.upper[~np.isnan(bb.upper)]
            valid_lower = bb.lower[~np.isnan(bb.lower)]
            valid_middle = bb.middle[~np.isnan(bb.middle)]

            if len(valid_upper) == 0 or len(valid_lower) == 0 or len(valid_middle) == 0:
                return None

            upper_band = float(valid_upper[-1])
            lower_band = float(valid_lower[-1])
            middle_band = float(valid_middle[-1])

            indicators = {
                "rsi": rsi_curr,
                "bb_upper": upper_band,
                "bb_middle": middle_band,
                "bb_lower": lower_band,
                "adx": adx_curr,
            }

            # ADX filter: only trade mean-reversion when trend is weak
            if adx_curr > adx_threshold:
                return None

            # LONG: RSI oversold AND price at or below lower BB
            if rsi_curr < rsi_oversold and price <= lower_band:
                stop_loss = price * (1 - stop_loss_pct / 100.0)
                strength = min(1.0, (rsi_oversold - rsi_curr) / rsi_oversold)

                return TradingSignal(
                    direction=SignalDirection.LONG,
                    symbol=symbol,
                    price=price,
                    strength=strength,
                    stop_loss=max(stop_loss, price * 0.001),
                    take_profit=middle_band,
                    indicators=indicators,
                    metadata={"trigger": "rsi_bb_mean_reversion_long"},
                )

            # SHORT: RSI overbought AND price at or above upper BB
            if rsi_curr > rsi_overbought and price >= upper_band:
                stop_loss = price * (1 + stop_loss_pct / 100.0)
                strength = min(1.0, (rsi_curr - rsi_overbought) / (100 - rsi_overbought))

                return TradingSignal(
                    direction=SignalDirection.SHORT,
                    symbol=symbol,
                    price=price,
                    strength=strength,
                    stop_loss=stop_loss,
                    take_profit=middle_band,
                    indicators=indicators,
                    metadata={"trigger": "rsi_bb_mean_reversion_short"},
                )

            # CLOSE signals when RSI normalises
            if rsi_curr > rsi_exit_long:
                return TradingSignal(
                    direction=SignalDirection.CLOSE,
                    symbol=symbol,
                    price=price,
                    strength=0.5,
                    indicators=indicators,
                    metadata={"trigger": "rsi_exit_long_normalised"},
                )

        except (ValueError, KeyError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None
