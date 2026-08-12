"""RSI + Bollinger Bands Mean Reversion signal generator.

Entry: RSI at extremes AND price at BB bands in low-trend environments.
Exit: RSI normalises or price reaches middle BB.

v1.2: Regime-aware strength (replaces v1.1 directional gate).
    The v1.1 EMA(200) directional gate blocked counter-regime entries
    entirely, which killed trade frequency (0-1 trades in 90d bear market).
    Mean reversion NEEDS to trade against the prevailing direction.

    New approach: EMA(200) modulates signal strength instead of gating.
    Counter-regime trades get 0.6x strength (reduced position size),
    with-regime trades get full strength. ADX < threshold remains the
    primary filter ensuring low-trend (ranging) conditions.

Wick-based BB detection: uses high/low (not close) to capture
rejection candles where the wick touches the band.

Template ID: rsi_bb_mean_reversion
Strategy Type: mean_reversion
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import ADX, RSI, EMA, BollingerBands
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RsiBbMeanReversionGenerator(SignalGenerator):
    """Signal generator for RSI + BB Mean Reversion strategy.

    Identifies mean-reversion opportunities when RSI is at oversold/overbought
    levels AND price is near BB bands, with ADX confirming low trend strength.

    v1.2: Regime-aware strength modulation (replaces v1.1 directional gate).
        - EMA(200) regime: counter-regime trades get 0.6x strength (not blocked)
        - Wick-based BB detection for rejection candle identification
        - ADX < threshold is the primary mean-reversion filter

    Required parameters:
        rsi_period, rsi_oversold, rsi_overbought,
        rsi_exit_long, rsi_exit_short,
        bb_period, bb_std_dev,
        adx_threshold, stop_loss_pct
    Optional:
        ema_regime_period (default: 200)
    """

    @property
    def template_id(self) -> str:
        return "rsi_bb_mean_reversion"

    @property
    def min_bars_required(self) -> int:
        # EMA(200) needs 200 bars warmup + ADX/BB/RSI buffer
        return 210

    # Counter-regime strength multiplier: reduces position size for
    # trades against the EMA(200) regime, without blocking them entirely.
    _COUNTER_REGIME_STRENGTH = 0.6

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate mean-reversion conditions with regime-aware strength.

        v1.2: Counter-regime trades are allowed at reduced strength (0.6x)
        instead of being blocked. ADX < threshold is the primary filter.

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
            rsi_exit_short: float = float(params.get("rsi_exit_short", 50.0))
            bb_period: int = int(params["bb_period"])
            bb_std: float = float(params["bb_std_dev"])
            adx_threshold: float = float(params["adx_threshold"])
            stop_loss_pct: float = float(params["stop_loss_pct"])
            ema_regime_period: int = int(params.get("ema_regime_period", 200))

            # Calculate indicators
            rsi_result = RSI(period=rsi_period).calculate(series)
            bb = BollingerBands(period=bb_period, multiplier=bb_std).calculate(series)
            adx_result = ADX(period=14).calculate(series)
            ema_regime = EMA(period=ema_regime_period).calculate(series)

            last_idx = len(series) - 1
            price = float(series.closes[last_idx])
            high = float(series.highs[last_idx])
            low = float(series.lows[last_idx])
            rsi_curr = rsi_result.current
            adx_curr = adx_result.current

            # Regime detection via EMA(200) — used for strength, not gating
            ema_val = ema_regime.current
            if np.isnan(ema_val):
                return None
            is_bear = price < ema_val
            is_bull = price > ema_val

            # Get BB values
            valid_upper = bb.upper[~np.isnan(bb.upper)]
            valid_lower = bb.lower[~np.isnan(bb.lower)]
            valid_middle = bb.middle[~np.isnan(bb.middle)]

            if len(valid_upper) == 0 or len(valid_lower) == 0 or len(valid_middle) == 0:
                return None

            upper_band = float(valid_upper[-1])
            lower_band = float(valid_lower[-1])
            middle_band = float(valid_middle[-1])

            # Wick-based BB detection: captures rejection candles
            at_upper_bb = high >= upper_band
            at_lower_bb = low <= lower_band

            regime = "bear" if is_bear else "bull"
            indicators: dict[str, float | str] = {
                "rsi": rsi_curr,
                "bb_upper": upper_band,
                "bb_middle": middle_band,
                "bb_lower": lower_band,
                "adx": adx_curr,
                "ema_regime": ema_val,
                "regime": regime,
            }

            # ADX filter: only trade mean-reversion when trend is weak
            if adx_curr > adx_threshold:
                return None

            # LONG: RSI oversold + wick touched lower BB = rejection candle
            # Allowed in any regime; counter-regime (bear) gets reduced strength
            if rsi_curr < rsi_oversold and at_lower_bb:
                stop_loss = price * (1 - stop_loss_pct / 100.0)
                strength = min(1.0, (rsi_oversold - rsi_curr) / rsi_oversold)
                # Counter-regime: LONG in bear gets reduced strength
                if is_bear:
                    strength *= self._COUNTER_REGIME_STRENGTH

                return TradingSignal(
                    direction=SignalDirection.LONG,
                    symbol=symbol,
                    price=price,
                    strength=strength,
                    stop_loss=max(stop_loss, price * 0.001),
                    take_profit=middle_band,
                    indicators=indicators,
                    metadata={
                        "trigger": "rsi_bb_mean_reversion_long",
                        "regime": regime,
                    },
                )

            # SHORT: RSI overbought + wick touched upper BB = rejection candle
            # Allowed in any regime; counter-regime (bull) gets reduced strength
            if rsi_curr > rsi_overbought and at_upper_bb:
                stop_loss = price * (1 + stop_loss_pct / 100.0)
                strength = min(1.0, (rsi_curr - rsi_overbought) / (100 - rsi_overbought))
                # Counter-regime: SHORT in bull gets reduced strength
                if is_bull:
                    strength *= self._COUNTER_REGIME_STRENGTH

                return TradingSignal(
                    direction=SignalDirection.SHORT,
                    symbol=symbol,
                    price=price,
                    strength=strength,
                    stop_loss=stop_loss,
                    take_profit=middle_band,
                    indicators=indicators,
                    metadata={
                        "trigger": "rsi_bb_mean_reversion_short",
                        "regime": regime,
                    },
                )

            # CLOSE LONG: RSI normalised above exit threshold
            if rsi_curr > rsi_exit_long:
                return TradingSignal(
                    direction=SignalDirection.CLOSE,
                    symbol=symbol,
                    price=price,
                    strength=0.5,
                    indicators=indicators,
                    metadata={"trigger": "rsi_exit_long_normalised"},
                )

            # CLOSE SHORT: RSI normalised below exit threshold
            if rsi_curr < rsi_exit_short:
                return TradingSignal(
                    direction=SignalDirection.CLOSE,
                    symbol=symbol,
                    price=price,
                    strength=0.5,
                    indicators=indicators,
                    metadata={"trigger": "rsi_exit_short_normalised"},
                )

        except (ValueError, KeyError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None
