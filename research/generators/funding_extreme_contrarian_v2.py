"""Funding-extreme contrarian v2: percentile gate + windowed break (H-2026-06-006).

The CORRECTED operationalization of the H-2026-06-005 funding-contrarian, which
died at INSUFFICIENT_DATA (N=4) because three rare conditions had to coincide on
the SAME bar. The mechanism is unchanged -- fade euphoric over-leveraged longs at
a funding extreme, capturing the liquidation-driven reversal -- but two changes
fix the feasibility flaw:

  1. EXTREME is a per-symbol funding PERCENTILE (top decile over a trailing
     window), not an absolute 0.05%/8h cap. It self-calibrates per symbol and, by
     construction, ~10% of bars clear the funding dimension -- so funding is no
     longer the rarity bottleneck.
  2. The reversal trigger is DECOUPLED from the funding print: a downside Donchian
     break (close < the lowest low of the last ``breakout_lookback`` bars) that
     only needs to occur WHILE funding is in the extreme band, not on the exact
     funding-print bar.

The separate trend EMA filter of v1 is dropped (parsimony; extreme positive
funding already implies an up-phase). SHORT-only; backtested in FUTURES research
mode (allow_shorts, DEC-2026-05-28-001). LIVE shorts remain gated by the spot-only
lock -- a pass is a research finding, not deployable.

CAUSALITY. The funding percentile is computed only from prints whose settlement
time is at-or-before the decision bar's close timestamp (a trailing window ending
at that instant); the current funding is ``FundingSeries.rate_at(ts)``. No future
print is used. If funding is unknown or the window is too thin to rank, the
generator fails closed (no signal).

One-way dependency: research/ may import src/, never the reverse. Reuses the
funding channel (research/data/funding_rates.py) with NO new data channel and NO
change to the shared ``FundingSeries`` (the percentile is derived here from its
public ``times_ms`` / ``rates``). Loaded via the factory's runtime
``register_generator`` hook (DEC-2026-06-04-019). NEVER added to src/ pre-validation.
"""
from __future__ import annotations

import bisect
from typing import Any

import numpy as np

from research.data import funding_rates
from research.data.funding_rates import FundingSeries
from src.core.exceptions import SignalGenerationError
from src.core.indicators import ATR
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Minimum funding prints in the trailing window for a meaningful percentile rank.
_MIN_WINDOW_PRINTS = 10

# Per-process memo of loaded funding series (one disk read per symbol per process,
# including spawned workers). Distinct dict from the other funding generators.
_FUNDING_BY_SYMBOL: dict[str, FundingSeries | None] = {}


def _funding_for(symbol: str) -> FundingSeries | None:
    """Return the cached funding series for ``symbol`` (memoized, no network)."""
    if symbol not in _FUNDING_BY_SYMBOL:
        _FUNDING_BY_SYMBOL[symbol] = funding_rates.load_cached(symbol)
        if _FUNDING_BY_SYMBOL[symbol] is None:
            logger.warning("funding_cache_missing", symbol=symbol)
    return _FUNDING_BY_SYMBOL[symbol]


def _funding_window_rates(
    funding: FundingSeries, ts_ms: int, lookback_ms: int
) -> list[float]:
    """Return funding rates with settlement time in ``(ts_ms - lookback, ts_ms]``.

    Causal by construction: only prints at-or-before ``ts_ms`` are included
    (``bisect_right`` gives the count of times <= ts_ms). The window start is
    inclusive of prints strictly after ``ts_ms - lookback_ms``.

    Args:
        funding: The per-symbol funding series (times sorted ascending).
        ts_ms: Decision-bar close time in epoch milliseconds.
        lookback_ms: Trailing window length in milliseconds.

    Returns:
        The list of funding rates in the trailing window (chronological order).
    """
    hi = bisect.bisect_right(funding.times_ms, ts_ms)            # count of times <= ts_ms
    lo = bisect.bisect_right(funding.times_ms, ts_ms - lookback_ms)
    return list(funding.rates[lo:hi])


class FundingExtremeContrarianV2Generator(SignalGenerator):
    """Short-only contrarian: per-symbol funding percentile + downside break.

    Entry (SHORT) requires ALL of:
        1. Funding extreme: the causal current funding rate is POSITIVE and
           >= the ``funding_percentile_threshold`` percentile of the trailing
           ``funding_percentile_lookback_days`` window (self-calibrating per
           symbol; needs at least ``_MIN_WINDOW_PRINTS`` prints to rank).
        2. Momentum crack: a downside Donchian break -- the current close is
           below the lowest low of the prior ``breakout_lookback`` bars.

    Required parameters:
        funding_percentile_lookback_days, funding_percentile_threshold,
        breakout_lookback, atr_period, atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        """Return the template ID this generator handles."""
        return "funding_extreme_contrarian_v2"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars: breakout window + ATR warmup + buffer."""
        return 130

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate percentile-gated, windowed-break contrarian SHORT conditions.

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
            lookback_days: int = int(params["funding_percentile_lookback_days"])
            pct_threshold: float = float(params["funding_percentile_threshold"])
            breakout_lookback: int = int(params["breakout_lookback"])
            atr_period: int = int(params["atr_period"])
            atr_stop_mult: float = float(params["atr_stop_multiplier"])
            rr_ratio: float = float(params["risk_reward_ratio"])

            # --- Funding extreme via per-symbol percentile (causal) ---
            funding = _funding_for(symbol)
            if funding is None:
                return None
            current_ts = series[-1].timestamp   # tz-aware UTC decision bar close
            current_rate = funding.rate_at(current_ts)
            if current_rate is None or current_rate <= 0.0:
                # Need a POSITIVE funding extreme (euphoric longs); fail closed.
                return None
            ts_ms = int(current_ts.timestamp() * 1000)
            lookback_ms = lookback_days * 86_400_000
            window = _funding_window_rates(funding, ts_ms, lookback_ms)
            if len(window) < _MIN_WINDOW_PRINTS:
                return None
            threshold_rate = float(np.percentile(window, pct_threshold))
            if current_rate < threshold_rate:
                return None

            # --- Momentum crack: downside Donchian break ---
            # Lowest low of the prior breakout_lookback bars (excluding current).
            lows = series.lows
            if len(lows) < breakout_lookback + 1:
                return None
            prior_low = float(np.min(lows[-(breakout_lookback + 1):-1]))
            price = float(series.closes[-1])
            if not price < prior_low:
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
            if take_profit <= 0:
                return None

            indicators = {
                "funding_rate_8h": current_rate,
                "funding_pct_threshold": threshold_rate,
                "donchian_prior_low": prior_low,
                "atr": atr_curr,
            }
            # Strength scales with how far current funding exceeds the percentile
            # threshold (more euphoric = stronger fade), saturating modestly.
            span = max(threshold_rate, 1e-9)
            strength = max(0.4, min(1.0, 0.4 + 0.6 * min((current_rate - threshold_rate) / span, 1.0)))

            return TradingSignal(
                direction=SignalDirection.SHORT,
                symbol=symbol,
                price=price,
                strength=strength,
                stop_loss=stop_loss,
                take_profit=take_profit,
                indicators=indicators,
                metadata={
                    "trigger": "funding_extreme_contrarian_v2_short",
                    "funding_rate_8h": current_rate,
                },
            )

        except (ValueError, KeyError, IndexError) as exc:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(exc),
            ) from exc
