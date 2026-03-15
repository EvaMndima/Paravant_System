"""Regime-Aware Mean Reversion signal generator.

Multi-timeframe mean reversion strategy that adapts direction bias based
on 4H EMA(200) regime detection. Uses the widest indicator confluence
set: RSI + BB + VWAP + Keltner + MACD + ATR on 1H.

BEAR regime (below 4H EMA200):
    PRIMARY SHORT: RSI>75 + upper BB/KC + MACD confirms (high conviction)
    SECONDARY LONG: RSI<20 + lower BB + VWAP deviation (low conviction)
BULL regime (above 4H EMA200):
    PRIMARY LONG: RSI<25 + lower BB/KC + MACD confirms (high conviction)
    SECONDARY SHORT: RSI>80 + upper BB + VWAP deviation (low conviction)

Exit: VWAP or EMA(20), 1.5*ATR stop, 12-bar time stop

Template ID: regime_aware_mean_reversion
Strategy Type: mean_reversion
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.core.exceptions import SignalGenerationError
from src.core.indicators import (
    ATR,
    MACD,
    RSI,
    VWAP,
    BollingerBands,
    EMA,
    KeltnerChannel,
)
from src.core.indicators.resample import resample_ohlcv
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RegimeAwareMeanReversionGenerator(SignalGenerator):
    """Signal generator for Regime-Aware Mean Reversion strategy.

    The highest priority bear-regime strategy. Combines regime awareness
    (4H EMA200) with multi-indicator confluence on 1H to find high-
    probability mean reversion setups.

    Core thesis: In bear markets, short overbought bounces. In bull
    markets, buy oversold dips. Always fade WITH the regime, not against.
    Secondary signals allow counter-regime trades but with low conviction
    and only at extreme conditions.

    Indicator confluence (7 indicators):
        1. EMA(200) 4H: Regime filter (bear vs bull)
        2. RSI(9) 1H: Momentum extreme detection
        3. BB(20,2.0) 1H: Statistical volatility bands
        4. Keltner(20,14,2.0) 1H: ATR-based volatility bands
        5. VWAP 1H: Institutional reference price / deviation
        6. MACD 1H: Momentum direction confirmation
        7. ATR 1H: Dynamic stop-loss calculation

    Required parameters:
        htf_ema_period, rsi_period, rsi_overbought_bear, rsi_oversold_bear,
        rsi_overbought_bull, rsi_oversold_bull, bb_period, bb_std_dev,
        kc_ema_period, kc_atr_period, kc_multiplier, vwap_deviation_pct,
        macd_fast, macd_slow, macd_signal, atr_period, time_stop_bars
    """

    @property
    def template_id(self) -> str:
        """Return template ID for Regime-Aware Mean Reversion strategy."""
        return "regime_aware_mean_reversion"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars needed.

        EMA(200) on 4H needs 200*4=800 1H bars.
        Plus 1H indicator warmup and buffer = 810.
        """
        return 810

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate Regime-Aware Mean Reversion conditions.

        Args:
            series: OHLCV series (1H timeframe) for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if conditions met, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            # Extract parameters
            htf_ema_period = int(params["htf_ema_period"])
            rsi_period = int(params["rsi_period"])
            rsi_ob_bear = float(params["rsi_overbought_bear"])
            rsi_os_bear = float(params["rsi_oversold_bear"])
            rsi_ob_bull = float(params["rsi_overbought_bull"])
            rsi_os_bull = float(params["rsi_oversold_bull"])
            bb_period = int(params["bb_period"])
            bb_std = float(params["bb_std_dev"])
            kc_ema_period = int(params["kc_ema_period"])
            kc_atr_period = int(params["kc_atr_period"])
            kc_multiplier = float(params["kc_multiplier"])
            vwap_dev_pct = float(params["vwap_deviation_pct"])
            macd_fast = int(params["macd_fast"])
            macd_slow = int(params["macd_slow"])
            macd_signal_period = int(params["macd_signal"])
            atr_period = int(params["atr_period"])
            time_stop_bars = int(params.get("time_stop_bars", 12))

            # --- Higher Timeframe: 4H regime detection ---
            series_4h = resample_ohlcv(series, "4h")
            if len(series_4h) < htf_ema_period:
                return None

            htf_ema = EMA(period=htf_ema_period).calculate(series_4h)
            htf_ema_value = htf_ema.current
            if np.isnan(htf_ema_value):
                return None

            # --- 1H indicators ---
            rsi_result = RSI(period=rsi_period).calculate(series)
            bb = BollingerBands(
                period=bb_period, multiplier=bb_std,
            ).calculate(series)
            kc = KeltnerChannel(
                ema_period=kc_ema_period,
                atr_period=kc_atr_period,
                multiplier=kc_multiplier,
            ).calculate(series)
            vwap_result = VWAP().calculate(series)
            macd_result = MACD(
                fast_period=macd_fast,
                slow_period=macd_slow,
                signal_period=macd_signal_period,
            ).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            last_idx = len(series) - 1
            price = float(series.closes[last_idx])
            high = float(series.highs[last_idx])
            low = float(series.lows[last_idx])

            # Validate all indicator values
            vals = self._extract_values(
                rsi_result, bb, kc, vwap_result, macd_result, atr_result, last_idx,
            )
            if vals is None:
                return None

            rsi_val, bb_upper, bb_lower, bb_middle, kc_upper, kc_lower, \
                kc_mid, vwap_val, hist_curr, hist_prev, atr_val = vals

            # --- Regime Detection ---
            is_bear = price < htf_ema_value
            is_bull = price > htf_ema_value

            # VWAP deviation
            vwap_dev = ((price - vwap_val) / vwap_val * 100) if vwap_val > 0 else 0.0

            # Band extremes: wick-based detection captures rejection candles
            # A wick touching the band is a stronger mean reversion signal
            # than requiring the close to be beyond the band
            at_upper_bb = high >= bb_upper
            at_lower_bb = low <= bb_lower
            at_upper_kc = high >= kc_upper
            at_lower_kc = low <= kc_lower

            # MACD direction
            macd_turning_negative = hist_curr < hist_prev
            macd_turning_positive = hist_curr > hist_prev

            # Indicator snapshot
            indicators = {
                "htf_ema_200": htf_ema_value,
                "regime": "bear" if is_bear else "bull",
                "rsi": rsi_val,
                "bb_upper": bb_upper,
                "bb_lower": bb_lower,
                "kc_upper": kc_upper,
                "kc_lower": kc_lower,
                "vwap": vwap_val,
                "vwap_deviation_pct": vwap_dev,
                "macd_histogram": hist_curr,
                "atr": atr_val,
            }

            # ========================================
            # BEAR REGIME
            # ========================================
            if is_bear:
                # PRIMARY SHORT: RSI overbought + wick at upper band + MACD confirms
                # Wick-based band detection captures rejection candles;
                # MACD gate is required to filter false positives where
                # momentum is still building (not yet reversing)
                if rsi_val > rsi_ob_bear and (at_upper_bb or at_upper_kc):
                    if macd_turning_negative or hist_curr < 0:
                        strength = self._primary_strength(
                            rsi_val, rsi_ob_bear, 100.0,
                            price, htf_ema_value, atr_val,
                        )
                        stop_loss = price + 1.5 * atr_val

                        return TradingSignal(
                            direction=SignalDirection.SHORT,
                            symbol=symbol,
                            price=price,
                            strength=strength,
                            stop_loss=stop_loss,
                            take_profit=vwap_val if vwap_val < price else bb_middle,
                            indicators=indicators,
                            metadata={
                                "trigger": "ramr_bear_primary_short",
                                "regime": "bear",
                                "time_stop_bars": time_stop_bars,
                            },
                        )

                # SECONDARY LONG: deeply oversold + lower band + VWAP deviation
                if rsi_val < rsi_os_bear and at_lower_bb:
                    if abs(vwap_dev) > vwap_dev_pct and vwap_dev < 0:
                        strength = self._secondary_strength(rsi_val, rsi_os_bear)
                        stop_loss = price - 1.5 * atr_val

                        return TradingSignal(
                            direction=SignalDirection.LONG,
                            symbol=symbol,
                            price=price,
                            strength=strength,
                            stop_loss=max(stop_loss, price * 0.001),
                            take_profit=vwap_val if vwap_val > price else bb_middle,
                            indicators=indicators,
                            metadata={
                                "trigger": "ramr_bear_secondary_long",
                                "regime": "bear",
                                "time_stop_bars": time_stop_bars,
                            },
                        )

            # ========================================
            # BULL REGIME
            # ========================================
            if is_bull:
                # PRIMARY LONG: RSI oversold + wick at lower band + MACD confirms
                if rsi_val < rsi_os_bull and (at_lower_bb or at_lower_kc):
                    if macd_turning_positive or hist_curr > 0:
                        strength = self._primary_strength(
                            rsi_val, 0.0, rsi_os_bull,
                            price, htf_ema_value, atr_val,
                        )
                        stop_loss = price - 1.5 * atr_val

                        return TradingSignal(
                            direction=SignalDirection.LONG,
                            symbol=symbol,
                            price=price,
                            strength=strength,
                            stop_loss=max(stop_loss, price * 0.001),
                            take_profit=vwap_val if vwap_val > price else bb_middle,
                            indicators=indicators,
                            metadata={
                                "trigger": "ramr_bull_primary_long",
                                "regime": "bull",
                                "time_stop_bars": time_stop_bars,
                            },
                        )

                # SECONDARY SHORT: extremely overbought + upper band + VWAP dev
                if rsi_val > rsi_ob_bull and at_upper_bb:
                    if abs(vwap_dev) > vwap_dev_pct and vwap_dev > 0:
                        strength = self._secondary_strength(
                            rsi_val, rsi_ob_bull, invert=True,
                        )
                        stop_loss = price + 1.5 * atr_val

                        return TradingSignal(
                            direction=SignalDirection.SHORT,
                            symbol=symbol,
                            price=price,
                            strength=strength,
                            stop_loss=stop_loss,
                            take_profit=vwap_val if vwap_val < price else bb_middle,
                            indicators=indicators,
                            metadata={
                                "trigger": "ramr_bull_secondary_short",
                                "regime": "bull",
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
    def _extract_values(
        rsi_result: Any,
        bb: Any,
        kc: Any,
        vwap_result: Any,
        macd_result: Any,
        atr_result: Any,
        last_idx: int,
    ) -> tuple[float, ...] | None:
        """Extract and validate all indicator values at last_idx.

        Returns:
            Tuple of (rsi, bb_upper, bb_lower, bb_middle, kc_upper, kc_lower,
            kc_middle, vwap, hist_curr, hist_prev, atr) or None if invalid.
        """
        # RSI
        valid_rsi = rsi_result.values[~np.isnan(rsi_result.values)]
        if len(valid_rsi) == 0:
            return None
        rsi_val = float(valid_rsi[-1])

        # Bollinger Bands
        bb_upper = bb.upper[last_idx]
        bb_lower = bb.lower[last_idx]
        bb_middle = bb.middle[last_idx]
        if any(np.isnan(v) for v in [bb_upper, bb_lower, bb_middle]):
            return None

        # Keltner Channels
        kc_upper = kc.upper[last_idx]
        kc_lower = kc.lower[last_idx]
        kc_mid = kc.middle[last_idx]
        if any(np.isnan(v) for v in [kc_upper, kc_lower, kc_mid]):
            return None

        # VWAP
        valid_vwap = vwap_result.values[~np.isnan(vwap_result.values)]
        if len(valid_vwap) == 0:
            return None
        vwap_val = float(valid_vwap[-1])

        # MACD histogram
        valid_hist = macd_result.histogram[~np.isnan(macd_result.histogram)]
        if len(valid_hist) < 2:
            return None
        hist_curr = float(valid_hist[-1])
        hist_prev = float(valid_hist[-2])

        # ATR
        atr_val = atr_result.current
        if np.isnan(atr_val) or atr_val <= 0:
            return None

        return (
            rsi_val, float(bb_upper), float(bb_lower), float(bb_middle),
            float(kc_upper), float(kc_lower), float(kc_mid),
            vwap_val, hist_curr, hist_prev, atr_val,
        )

    @staticmethod
    def _primary_strength(
        rsi: float,
        rsi_low: float,
        rsi_high: float,
        price: float,
        htf_ema: float,
        atr: float,
    ) -> float:
        """Calculate strength for primary (with-regime) signals.

        Higher RSI extremity and greater distance from HTF EMA both
        increase conviction. Primary signals are high-confidence (0.5-1.0).

        Args:
            rsi: Current RSI value.
            rsi_low: Lower RSI bound for extremity calc.
            rsi_high: Upper RSI bound for extremity calc.
            price: Current close price.
            htf_ema: 4H EMA(200) value.
            atr: Current ATR.

        Returns:
            Strength between 0.5 and 1.0.
        """
        # RSI extremity score
        rsi_range = max(rsi_high - rsi_low, 1.0)
        rsi_extremity = abs(rsi - (rsi_low + rsi_high) / 2) / (rsi_range / 2)
        rsi_score = min(0.25, rsi_extremity * 0.15)

        # Regime conviction: distance from 4H EMA in ATR units
        ema_dist = abs(price - htf_ema) / atr if atr > 0 else 0
        regime_score = min(0.2, ema_dist * 0.02)

        return max(0.5, min(1.0, 0.55 + rsi_score + regime_score))

    @staticmethod
    def _secondary_strength(
        rsi: float,
        threshold: float,
        *,
        invert: bool = False,
    ) -> float:
        """Calculate strength for secondary (counter-regime) signals.

        Secondary signals have capped strength (0.25-0.5) because they
        trade against the regime. Only extreme conditions justify entry.

        Args:
            rsi: Current RSI value.
            threshold: RSI threshold that triggered the signal.
            invert: True for overbought (SHORT), False for oversold (LONG).

        Returns:
            Strength between 0.25 and 0.5.
        """
        if invert:
            extremity = max(0, (rsi - threshold) / (100 - threshold))
        else:
            extremity = max(0, (threshold - rsi) / threshold) if threshold > 0 else 0

        return max(0.25, min(0.5, 0.3 + extremity * 0.15))
