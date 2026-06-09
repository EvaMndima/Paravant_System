"""Funding-confirmed trend-continuation signal generator (H-2026-06-003).

Research-stage generator for the uncovered TRENDING_BULL regime. Long-only,
spot. Enters a trend-continuation long ONLY when perpetual funding confirms that
leveraged longs are paying to be long (positive funding) but are not euphoric
(funding below an extreme cap, which would flag a blow-off top prone to
liquidation reversals).

Mechanism (H-2026-06-003): in a sustained bull, perp funding is persistently
positive because leveraged longs crowd the long side and pay funding. A SPOT
long entered while funding is positive-but-moderate free-rides that leveraged
demand without paying funding itself; the counterparty is trend-faders/shorts
squeezed by the move. The extreme cap avoids tops where over-leveraged longs
cascade-liquidate. Funding is a crypto-native derivatives-flow signal with no
equity analogue -- the diversifying mechanism the price/volume KEEP strategies
lack.

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
# ``None`` is memoized too, so a missing cache is not retried per bar.
_FUNDING_BY_SYMBOL: dict[str, FundingSeries | None] = {}


def _funding_for(symbol: str) -> FundingSeries | None:
    """Return the cached funding series for ``symbol`` (memoized, no network)."""
    if symbol not in _FUNDING_BY_SYMBOL:
        _FUNDING_BY_SYMBOL[symbol] = funding_rates.load_cached(symbol)
        if _FUNDING_BY_SYMBOL[symbol] is None:
            logger.warning("funding_cache_missing", symbol=symbol)
    return _FUNDING_BY_SYMBOL[symbol]


class FundingConfirmedTrendGenerator(SignalGenerator):
    """Long-only trend-continuation gated by a perp funding-rate confirmation.

    Entry (LONG) requires ALL of:
        1. Uptrend: close > EMA(trend_ema_period) AND that EMA is rising over
           ``slope_lookback`` bars.
        2. Trigger: a fast-EMA recross -- close crosses up through
           EMA(fast_ema_period) on the last two bars (a trend-resumption tick,
           not a new-high breakout, to stay distinct from donchian_atr).
        3. Funding gate: the causal funding rate is in
           (funding_positive_threshold, extreme_cap], where
           extreme_cap = funding_extreme_cap_pct_per_8h / 100.

    Required parameters:
        trend_ema_period, fast_ema_period, slope_lookback,
        funding_positive_threshold, funding_extreme_cap_pct_per_8h,
        atr_period, atr_stop_multiplier, risk_reward_ratio
    """

    @property
    def template_id(self) -> str:
        """Return the template ID this generator handles."""
        return "funding_confirmed_trend"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars: EMA(trend) warmup + slope window + buffer."""
        return 130

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate funding-confirmed trend-continuation entry conditions.

        Args:
            series: Causal OHLCV window ending at the decision bar.
            params: Validated strategy parameters.
            symbol: Trading pair symbol.

        Returns:
            A LONG ``TradingSignal`` if all conditions hold, else None.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            trend_ema_period: int = int(params["trend_ema_period"])
            fast_ema_period: int = int(params["fast_ema_period"])
            slope_lookback: int = int(params["slope_lookback"])
            pos_threshold: float = float(params["funding_positive_threshold"])
            extreme_cap: float = float(params["funding_extreme_cap_pct_per_8h"]) / 100.0
            atr_period: int = int(params["atr_period"])
            atr_stop_mult: float = float(params["atr_stop_multiplier"])
            rr_ratio: float = float(params["risk_reward_ratio"])

            # --- Funding gate (causal): fail closed if unknown ---
            funding = _funding_for(symbol)
            if funding is None:
                return None
            # series[-1] is the decision bar; its .timestamp is tz-aware UTC
            # (validated by OHLCV). series.timestamps would be np.datetime64
            # (no tzinfo) -- not what the causal rate_at lookup expects.
            current_ts = series[-1].timestamp
            rate = funding.rate_at(current_ts)
            if rate is None:
                return None
            if not (pos_threshold < rate <= extreme_cap):
                return None

            # --- Trend filter: price above a RISING long EMA ---
            trend_ema = EMA(period=trend_ema_period).calculate(series)
            trend_vals = trend_ema.values[~np.isnan(trend_ema.values)]
            if len(trend_vals) < slope_lookback + 1:
                return None
            price = float(series.closes[-1])
            trend_now = float(trend_vals[-1])
            trend_prior = float(trend_vals[-1 - slope_lookback])
            if not (price > trend_now and trend_now > trend_prior):
                return None

            # --- Trigger: fast-EMA recross on the last two bars ---
            fast_ema = EMA(period=fast_ema_period).calculate(series)
            fast_vals = fast_ema.values
            if len(fast_vals) < 2 or np.isnan(fast_vals[-1]) or np.isnan(fast_vals[-2]):
                return None
            close_now = float(series.closes[-1])
            close_prev = float(series.closes[-2])
            fast_now = float(fast_vals[-1])
            fast_prev = float(fast_vals[-2])
            crossed_up = close_prev <= fast_prev and close_now > fast_now
            if not crossed_up:
                return None

            # --- Risk framing via ATR ---
            atr_result = ATR(period=atr_period).calculate(series)
            atr_vals = atr_result.values[~np.isnan(atr_result.values)]
            if len(atr_vals) < 1:
                return None
            atr_curr = float(atr_vals[-1])
            if atr_curr <= 0:
                return None

            risk = atr_stop_mult * atr_curr
            stop_loss = price - risk
            take_profit = price + risk * rr_ratio

            indicators = {
                "funding_rate_8h": rate,
                "trend_ema": trend_now,
                "fast_ema": fast_now,
                "atr": atr_curr,
            }
            # Strength scales with how solidly funding sits inside the gate band
            # (mid-band = strongest; near 0 or near the cap = weaker).
            band = extreme_cap - pos_threshold
            mid = pos_threshold + band / 2.0
            strength = max(0.4, min(1.0, 1.0 - abs(rate - mid) / (band / 2.0) * 0.5))

            return TradingSignal(
                direction=SignalDirection.LONG,
                symbol=symbol,
                price=price,
                strength=strength,
                stop_loss=max(stop_loss, price * 0.001),
                take_profit=take_profit,
                indicators=indicators,
                metadata={
                    "trigger": "funding_confirmed_trend_long",
                    "funding_rate_8h": rate,
                },
            )

        except (ValueError, KeyError, IndexError) as exc:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(exc),
            ) from exc
