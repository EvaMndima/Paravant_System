"""Funding-at-extremes contrarian reversal signal generator (H-2026-06-005).

Research-stage generator for the uncovered HIGH_VOL / reversal regime. SHORT-only
(backtested in FUTURES research mode; live shorts remain gated by the spot-only
lock DEC-2026-05-28-001). Fades an over-extended bull move when perpetual funding
is EXTREMELY positive and price momentum cracks.

Mechanism (H-2026-06-005): in an over-extended bull move funding goes extremely
positive -- leveraged longs crowd the long side and pay escalating funding. That
marks an over-leveraged, fragile long side. When momentum cracks (a fast-EMA
cross DOWN while price is still extended above a longer trend EMA), those longs
are force-liquidated -- the engine market-sells price-insensitively -- and price
reverses sharply down. A SHORT entered at that crack captures the reversal. The
counterparty is euphoric over-leveraged longs who pay carry the whole time and
are liquidated at the worst price.

This is the OPPOSITE usage of funding vs the H-2026-06-003 confirmer: that went
LONG on positive-but-moderate funding (below an extreme cap) and died FUNDAMENTAL;
this goes SHORT on funding ABOVE that cap. If both die, funding carries no
exploitable timing edge in either direction.

CAUSALITY. Funding is looked up via ``FundingSeries.rate_at(ts)`` at the close
timestamp of the LAST VISIBLE bar, returning only the most recent print known
at-or-before that instant. If no funding is known (or the per-symbol cache is
absent), the generator fails closed (no signal) -- never assumes a value.

One-way dependency: this lives in research/, subclasses the production
``SignalGenerator`` (research->src import allowed, never the reverse), and is
loaded into the eval at runtime via ``SignalGeneratorFactory.register_generator``
(DEC-2026-06-04-019). It is NEVER added to ``src/`` before DSR validation.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from research.data import funding_rates
from research.data.funding_rates import FundingSeries
from src.core.exceptions import SignalGenerationError
from src.core.indicators import ATR, EMA
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Per-process memo of loaded funding series (the generator is called once per
# bar; reloading the JSON cache every call would dominate runtime). Each process
# -- including spawned backtest workers -- loads a symbol's cache at most once.
# ``None`` is memoized too, so a missing cache is not retried per bar. Distinct
# from funding_confirmed_trend's memo (separate module = separate dict).
_FUNDING_BY_SYMBOL: dict[str, FundingSeries | None] = {}


def _funding_for(symbol: str) -> FundingSeries | None:
    """Return the cached funding series for ``symbol`` (memoized, no network)."""
    if symbol not in _FUNDING_BY_SYMBOL:
        _FUNDING_BY_SYMBOL[symbol] = funding_rates.load_cached(symbol)
        if _FUNDING_BY_SYMBOL[symbol] is None:
            logger.warning("funding_cache_missing", symbol=symbol)
    return _FUNDING_BY_SYMBOL[symbol]


class FundingExtremeContrarianGenerator(SignalGenerator):
    """Short-only contrarian reversal gated by an EXTREME positive funding rate.

    Entry (SHORT) requires ALL of:
        1. Funding extreme: the causal funding rate strictly exceeds
           ``extreme_cap`` = funding_extreme_threshold_pct_per_8h / 100
           (over-leveraged, euphoric long side).
        2. Still-extended context: close > EMA(trend_ema_period) -- the move is
           an over-extended bull (we fade a top, not pile into a downtrend).
        3. Momentum crack trigger: close crosses DOWN through
           EMA(fast_ema_period) on the last two bars (the first sign the crowded
           longs are losing control), the bearish mirror of the H-003 recross.

    Required parameters:
        trend_ema_period, fast_ema_period, funding_extreme_threshold_pct_per_8h,
        atr_period, atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        """Return the template ID this generator handles."""
        return "funding_extreme_contrarian"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars: EMA(trend) warmup + buffer."""
        return 130

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate funding-extreme contrarian SHORT entry conditions.

        Args:
            series: Causal OHLCV window ending at the decision bar.
            params: Validated strategy parameters.
            symbol: Trading pair symbol.

        Returns:
            A SHORT ``TradingSignal`` if all conditions hold, else None.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            trend_ema_period: int = int(params["trend_ema_period"])
            fast_ema_period: int = int(params["fast_ema_period"])
            extreme_cap: float = (
                float(params["funding_extreme_threshold_pct_per_8h"]) / 100.0
            )
            atr_period: int = int(params["atr_period"])
            atr_stop_mult: float = float(params["atr_stop_multiplier"])
            rr_ratio: float = float(params["risk_reward_ratio"])

            # --- Funding gate (causal): fail closed if unknown ---
            funding = _funding_for(symbol)
            if funding is None:
                return None
            # series[-1] is the decision bar; its .timestamp is tz-aware UTC.
            current_ts = series[-1].timestamp
            rate = funding.rate_at(current_ts)
            if rate is None:
                return None
            # Strictly ABOVE the extreme cap = euphoric/over-leveraged long side.
            if not rate > extreme_cap:
                return None

            # --- Still-extended context: price above a longer trend EMA ---
            # (Fade an over-extended top; do NOT short into an established
            # downtrend where the crowded-long thesis no longer holds.)
            trend_ema = EMA(period=trend_ema_period).calculate(series)
            trend_vals = trend_ema.values[~np.isnan(trend_ema.values)]
            if len(trend_vals) < 1:
                return None
            price = float(series.closes[-1])
            trend_now = float(trend_vals[-1])
            if not price > trend_now:
                return None

            # --- Trigger: fast-EMA cross DOWN on the last two bars ---
            fast_ema = EMA(period=fast_ema_period).calculate(series)
            fast_vals = fast_ema.values
            if len(fast_vals) < 2 or np.isnan(fast_vals[-1]) or np.isnan(fast_vals[-2]):
                return None
            close_now = float(series.closes[-1])
            close_prev = float(series.closes[-2])
            fast_now = float(fast_vals[-1])
            fast_prev = float(fast_vals[-2])
            crossed_down = close_prev >= fast_prev and close_now < fast_now
            if not crossed_down:
                return None

            # --- Risk framing via ATR (SHORT: stop above, target below) ---
            atr_result = ATR(period=atr_period).calculate(series)
            atr_vals = atr_result.values[~np.isnan(atr_result.values)]
            if len(atr_vals) < 1:
                return None
            atr_curr = float(atr_vals[-1])
            if atr_curr <= 0:
                return None

            risk = atr_stop_mult * atr_curr
            stop_loss = price + risk
            take_profit = price - risk * rr_ratio
            # Guard against a non-positive target on a low-priced symbol.
            if take_profit <= 0:
                return None

            indicators = {
                "funding_rate_8h": rate,
                "trend_ema": trend_now,
                "fast_ema": fast_now,
                "atr": atr_curr,
            }
            # Strength scales with how far funding sits ABOVE the extreme cap
            # (more euphoric = stronger fade), saturating at 2x the cap.
            excess = (rate - extreme_cap) / extreme_cap if extreme_cap > 0 else 0.0
            strength = max(0.4, min(1.0, 0.4 + 0.6 * min(excess, 1.0)))

            return TradingSignal(
                direction=SignalDirection.SHORT,
                symbol=symbol,
                price=price,
                strength=strength,
                stop_loss=stop_loss,
                take_profit=take_profit,
                indicators=indicators,
                metadata={
                    "trigger": "funding_extreme_contrarian_short",
                    "funding_rate_8h": rate,
                },
            )

        except (ValueError, KeyError, IndexError) as exc:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(exc),
            ) from exc
