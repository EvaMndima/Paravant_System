"""Donchian Channel + ATR Breakout signal generator.

Entry: Price breaks above/below Donchian channel with ATR volatility filter.
Exit: Price touches opposite channel or trailing stop hit.

v1.1: EMA(200) regime gate filters breakout direction.
    BEAR (price < EMA200): only SHORT breakouts (breakdowns)
    BULL (price > EMA200): only LONG breakouts
This prevents longing false breakouts in bear markets (dead-cat bounces
that create temporary N-bar highs) and shorting false breakdowns in
bull markets.

Template ID: donchian_atr
Strategy Type: trend_breakout
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import ATR, EMA, DonchianChannel, VolumeAverage
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class DonchianAtrGenerator(SignalGenerator):
    """Signal generator for Donchian Channel + ATR Breakout strategy.

    Detects channel breakouts confirmed by sufficient volatility (ATR)
    and optional volume confirmation. Uses ATR-based trailing stops.

    v1.1: EMA(200) regime gate prevents counter-regime breakout entries.

    Required parameters:
        donchian_period, atr_period, atr_threshold,
        atr_stop_multiplier, volume_ma_period, volume_multiplier
    Optional:
        ema_regime_period (default: 200)
    """

    @property
    def template_id(self) -> str:
        return "donchian_atr"

    @property
    def min_bars_required(self) -> int:
        # EMA(200) needs 200 bars + donchian/ATR buffer
        return 210

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate Donchian breakout + ATR conditions.

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
            dc_period: int = int(params["donchian_period"])
            atr_period: int = int(params["atr_period"])
            atr_threshold: float = float(params["atr_threshold"])
            atr_stop_mult: float = float(params["atr_stop_multiplier"])
            vol_ma_period: int = int(params["volume_ma_period"])
            vol_mult: float = float(params["volume_multiplier"])
            ema_regime_period: int = int(params.get("ema_regime_period", 200))

            # Calculate indicators
            dc_result = DonchianChannel(period=dc_period).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)
            vol_avg = VolumeAverage(period=vol_ma_period).calculate(series)
            ema_regime = EMA(period=ema_regime_period).calculate(series)

            price = float(series.closes[-1])
            atr_curr = atr_result.current
            current_volume = float(series.volumes[-1])
            vol_ma = vol_avg.current
            # Intrabar high/low for standard Turtle-style channel breakout
            # Decision: DEC-2026-03-13-001 — intrabar highs/lows match Donchian channel construction
            current_high = float(series.highs[-1])
            current_low = float(series.lows[-1])

            # Regime detection via EMA(200)
            ema_val = ema_regime.current
            if np.isnan(ema_val):
                return None
            is_bear = price < ema_val
            is_bull = price > ema_val

            # Get Donchian channel values
            valid_upper = dc_result.upper[~np.isnan(dc_result.upper)]
            valid_lower = dc_result.lower[~np.isnan(dc_result.lower)]
            if len(valid_upper) < 2 or len(valid_lower) < 2:
                return None

            upper_channel = float(valid_upper[-1])
            lower_channel = float(valid_lower[-1])
            prev_upper = float(valid_upper[-2])
            prev_lower = float(valid_lower[-2])
            prev_close = float(series.closes[-2])

            # ATR volatility filter (relative to price)
            atr_relative = atr_curr / price if price > 0 else 0
            volatility_ok = atr_relative > atr_threshold

            # Volume confirmation
            volume_ok = current_volume > vol_ma * vol_mult

            indicators = {
                "donchian_upper": upper_channel,
                "donchian_lower": lower_channel,
                "atr": atr_curr,
                "atr_relative": atr_relative,
                "volume_ratio": current_volume / vol_ma if vol_ma > 0 else 0,
                "ema_regime": ema_val,
                "regime": "bear" if is_bear else "bull",
            }

            # LONG: only in BULL regime (price > EMA200)
            # Prevents longing false breakouts (dead-cat bounces) in bear markets
            if (
                is_bull
                and current_high > prev_upper
                and volatility_ok
                and volume_ok
            ):
                risk = atr_stop_mult * atr_curr
                stop_loss = price - risk
                # TP at 2:1 R:R above entry.
                take_profit = price + 2.0 * risk
                return TradingSignal(
                    direction=SignalDirection.LONG,
                    symbol=symbol,
                    price=price,
                    strength=min(1.0, atr_relative / (atr_threshold * 2)),
                    stop_loss=max(stop_loss, price * 0.001),
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={
                        "trigger": "donchian_breakout_long",
                        "regime": "bull",
                    },
                )

            # SHORT: only in BEAR regime (price < EMA200)
            # Breakdowns in bear markets have strong follow-through
            if (
                is_bear
                and current_low < prev_lower
                and volatility_ok
                and volume_ok
            ):
                risk = atr_stop_mult * atr_curr
                stop_loss = price + risk
                # TP at 2:1 R:R below entry.
                take_profit = price - 2.0 * risk
                return TradingSignal(
                    direction=SignalDirection.SHORT,
                    symbol=symbol,
                    price=price,
                    strength=min(1.0, atr_relative / (atr_threshold * 2)),
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    indicators=indicators,
                    metadata={
                        "trigger": "donchian_breakout_short",
                        "regime": "bear",
                    },
                )

            # CLOSE LONG: close falls below prior N-bar low (regime-independent)
            if price <= prev_lower and prev_close > prev_lower:
                return TradingSignal(
                    direction=SignalDirection.CLOSE,
                    symbol=symbol,
                    price=price,
                    strength=0.6,
                    indicators=indicators,
                    metadata={"trigger": "donchian_close_long"},
                )

            # CLOSE SHORT: close recovers above prior N-bar high (regime-independent)
            if price >= prev_upper and prev_close < prev_upper:
                return TradingSignal(
                    direction=SignalDirection.CLOSE,
                    symbol=symbol,
                    price=price,
                    strength=0.6,
                    indicators=indicators,
                    metadata={"trigger": "donchian_close_short"},
                )

        except (ValueError, KeyError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e

        return None
