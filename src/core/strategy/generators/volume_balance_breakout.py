"""Volume Balance Breakout signal generator.

Measures the "up-volume balance ratio" — the fraction of recent volume that
flowed into rising (close > open) candles. When institutional players accumulate
before a move, they buy into weakness while suppressing price, creating a pattern
where volume is dominated by up-bars even when price is consolidating.

When the up-volume ratio exceeds a threshold AND price breaks above the recent
range high on elevated volume, the smart-money accumulation phase has ended
and the mark-up phase begins.

Quant basis: The volume balance concept is distinct from raw volume analysis.
A single spike bar has high volume but tells you direction of one event.
The balance ratio over 15 bars tells you the *consistent directional bias* of
market participants — 65%+ of volume on up-bars means buyers have been absorbing
sellers for 15 bars before the breakout. This is a strong institutional signal.

RSI [45, 65]: the "not yet overbought" zone. Entering with RSI below 65 means
there is room for the standard RSI run to 70-80, adding further to the edge.

Entry conditions (LONG only — bull regime strategy):
    1. Price above EMA(ema_period) — macro bull trend
    2. Up-volume ratio over balance_period bars >= balance_threshold (65%)
    3. RSI in [rsi_min, rsi_max]: 45-65 zone (momentum positive, not exhausted)
    4. Price breaks above max(highs[-breakout_lookback:]) — range breakout
    5. Breakout bar volume > vol_ma * volume_threshold — capital confirms move

Template ID: volume_balance_breakout
Strategy Type: volatility_breakout
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


class VolumeBalanceBreakoutGenerator(SignalGenerator):
    """Signal generator for Volume Balance Breakout strategy.

    Identifies institutional accumulation via up-volume ratio before breakouts.
    High balance ratio + range breakout + elevated volume = high-probability move.

    Required parameters:
        balance_period, balance_threshold,
        breakout_lookback,
        ema_period,
        rsi_period, rsi_min, rsi_max,
        volume_period, volume_threshold,
        atr_period, atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        return "volume_balance_breakout"

    @property
    def min_bars_required(self) -> int:
        """EMA(50) warmup + balance_period(15) + breakout_lookback(15) + buffer."""
        return 110

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate Volume Balance Breakout entry conditions.

        Args:
            series: OHLCV series for the symbol.
            params: Validated parameters from the template.
            symbol: Trading pair symbol.

        Returns:
            TradingSignal if up-volume balance exceeds threshold and price
            breaks the recent high on elevated volume, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            balance_period: int     = int(params["balance_period"])
            balance_threshold: float = float(params["balance_threshold"])
            breakout_lookback: int   = int(params["breakout_lookback"])
            ema_period: int          = int(params["ema_period"])
            rsi_period: int          = int(params["rsi_period"])
            rsi_min: float           = float(params["rsi_min"])
            rsi_max: float           = float(params["rsi_max"])
            volume_period: int       = int(params["volume_period"])
            volume_threshold: float  = float(params["volume_threshold"])
            atr_period: int          = int(params["atr_period"])
            atr_stop_mult: float     = float(params["atr_stop_multiplier"])
            rr_ratio: float          = float(params["risk_reward_ratio"])

            ema_result = EMA(period=ema_period).calculate(series)
            rsi_result = RSI(period=rsi_period).calculate(series)
            atr_result = ATR(period=atr_period).calculate(series)

            ema_vals = ema_result.values[~np.isnan(ema_result.values)]
            rsi_vals = rsi_result.values[~np.isnan(rsi_result.values)]
            atr_vals = atr_result.values[~np.isnan(atr_result.values)]

            if len(ema_vals) < 1 or len(rsi_vals) < 1 or len(atr_vals) < 1:
                return None

            price     = float(series.closes[-1])
            ema_curr  = float(ema_vals[-1])
            rsi_curr  = float(rsi_vals[-1])
            atr_curr  = float(atr_vals[-1])

            # Trend gate: price must be above the macro EMA
            if price <= ema_curr:
                return None

            # RSI in accumulation zone: not bearish and not overbought
            if not (rsi_min <= rsi_curr <= rsi_max):
                return None

            # Up-volume balance: fraction of volume in rising candles
            closes = series.closes
            opens  = series.opens
            vols   = series.volumes

            n_needed = balance_period + 1
            if len(closes) < n_needed or len(vols) < n_needed:
                return None

            balance_closes = closes[-(balance_period + 1):-1]
            balance_opens  = opens[-(balance_period + 1):-1]
            balance_vols   = vols[-(balance_period + 1):-1]

            up_mask    = balance_closes > balance_opens
            up_volume  = float(np.sum(balance_vols[up_mask]))
            total_volume = float(np.sum(balance_vols))

            if total_volume <= 0:
                return None

            up_ratio = up_volume / total_volume

            if up_ratio < balance_threshold:
                return None

            # Breakout: price closes above the high of the lookback window
            if len(series.highs) < breakout_lookback + 1:
                return None
            range_high = float(np.max(series.highs[-(breakout_lookback + 1):-1]))
            if price <= range_high:
                return None

            # Volume on breakout bar confirms the move
            valid_vols = vols[~np.isnan(vols)]
            if len(valid_vols) < volume_period + 1:
                return None
            vol_ma   = float(np.mean(valid_vols[-(volume_period + 1):-1]))
            vol_curr = float(valid_vols[-1])
            if vol_ma <= 0 or vol_curr <= vol_ma * volume_threshold:
                return None

            # Signal strength: balance strength + breakout distance + volume
            balance_excess = up_ratio - balance_threshold
            breakout_pct   = (price - range_high) / range_high * 100
            strength_base  = min(
                1.0,
                0.55
                + min(0.2, balance_excess * 2.0)
                + min(0.1, breakout_pct * 0.5)
                + min(0.15, (vol_curr / vol_ma - volume_threshold) * 0.1),
            )

            risk = atr_stop_mult * atr_curr
            stop_loss   = price - risk
            take_profit = price + risk * rr_ratio

            return TradingSignal(
                direction=SignalDirection.LONG,
                symbol=symbol,
                price=price,
                strength=max(0.4, strength_base),
                stop_loss=max(stop_loss, price * 0.001),
                take_profit=take_profit,
                indicators={
                    "up_volume_ratio": round(up_ratio, 3),
                    "balance_threshold": balance_threshold,
                    "range_high_broken": round(range_high, 4),
                    "breakout_pct": round(breakout_pct, 3),
                    "rsi": round(rsi_curr, 1),
                    "ema_trend": round(ema_curr, 4),
                    "volume_ratio": round(vol_curr / vol_ma, 2),
                    "atr": atr_curr,
                },
                metadata={
                    "trigger": "vbb_long_volume_balance_breakout",
                    "up_ratio": round(up_ratio, 3),
                    "breakout_pct": round(breakout_pct, 3),
                    "vol_ratio": round(vol_curr / vol_ma, 2),
                },
            )

        except (ValueError, KeyError, IndexError) as e:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(e),
            ) from e
