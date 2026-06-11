"""Coinbase-premium structural-demand generator (H-2026-06-010).

Research-stage generator for the TRENDING_BULL / accumulation regime. Long-only,
spot (deployable if it passes). Goes LONG when the Coinbase BTC-USD price trades
at an elevated PREMIUM to the offshore (Binance BTC-USDT) price -- a documented
signal of US-regulated institutional spot demand.

Mechanism (H-2026-06-010): US institutions accumulate spot on Coinbase (USD
on-ramp, KYC); the premium persists because the cross-venue arb is
FRICTION-LIMITED (KYC, banking, USD<->USDT, time), so an elevated premium predicts
short-term continuation as the global price catches up. The counterparty is the
friction-limited cross-venue arbitrageur + slow global price. This is a
MICROSTRUCTURE-FRICTION signal, distinct from the H-007 ETF creation-flow.

CAUSALITY. The premium is computed from the just-closed decision bar of BOTH
venues (Coinbase ``close_at(ts)`` and the Binance close), both known at the bar
close; the backtest fills on the next bar open. The trailing-premium percentile
is built from the generator's own causal window. If the Coinbase cache is absent
the generator fails closed.

EXIT: a TRAILING ATR stop (take_profit None).

One-way dependency: research/ imports src/, never the reverse. Reuses the FREE
Coinbase channel (research/data/coinbase_prices.py); loaded via the factory hook
(DEC-2026-06-04-019). NEVER added to src/ before DSR validation.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from research.data import coinbase_prices
from research.data.coinbase_prices import CoinbasePriceSeries
from src.core.exceptions import SignalGenerationError
from src.core.indicators import ATR
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)

_MIN_WINDOW_PREMIUMS = 50

# Per-process memo of the Coinbase price series (one disk read per symbol/process).
_COINBASE_BY_SYMBOL: dict[str, CoinbasePriceSeries | None] = {}


def _coinbase_for(symbol: str) -> CoinbasePriceSeries | None:
    """Return the cached Coinbase price series for ``symbol`` (memoized)."""
    if symbol not in _COINBASE_BY_SYMBOL:
        _COINBASE_BY_SYMBOL[symbol] = coinbase_prices.load_cached(symbol)
        if _COINBASE_BY_SYMBOL[symbol] is None:
            logger.warning("coinbase_cache_missing", symbol=symbol)
    return _COINBASE_BY_SYMBOL[symbol]


class CoinbasePremiumGenerator(SignalGenerator):
    """Long when the Coinbase premium is positive and in its trailing top-percentile.

    Entry (LONG) requires ALL of:
        1. The current Coinbase premium (Coinbase/Binance - 1) is POSITIVE.
        2. That premium is >= the ``premium_percentile_threshold`` percentile of
           the trailing ``premium_lookback_days`` window (needs at least
           ``_MIN_WINDOW_PREMIUMS`` premium observations).

    Exit is a TRAILING ATR stop (take_profit None).

    Required parameters:
        premium_lookback_days, premium_percentile_threshold,
        atr_period, atr_stop_multiplier
    """

    @property
    def template_id(self) -> str:
        """Return the template ID this generator handles."""
        return "coinbase_premium"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars: ATR warmup (the premium window is checked inline)."""
        return 50

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate the Coinbase-premium LONG entry conditions.

        Args:
            series: Causal Binance OHLCV window ending at the decision bar.
            params: Validated strategy parameters.
            symbol: Trading pair symbol (must have a Coinbase product: BTC/ETH).

        Returns:
            A LONG ``TradingSignal`` if all conditions hold, else None.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            lookback_bars: int = int(params["premium_lookback_days"]) * 24
            pct_threshold: float = float(params["premium_percentile_threshold"])
            atr_period: int = int(params["atr_period"])
            atr_stop_mult: float = float(params["atr_stop_multiplier"])

            cb = _coinbase_for(symbol)
            if cb is None:
                return None

            # --- Current premium (causal: both closes from the decision bar) ---
            current_ts = series[-1].timestamp
            binance_close = float(series.closes[-1])
            cb_close = cb.close_at(current_ts)
            if cb_close is None or binance_close <= 0:
                return None
            current_premium = cb_close / binance_close - 1.0
            if current_premium <= 0.0:
                return None

            # --- Trailing-premium percentile from the generator's own window ---
            closes = series.closes
            candles = series.candles
            n = len(closes)
            if n < lookback_bars + 1:
                return None
            window: list[float] = []
            for j in range(n - lookback_bars, n):
                b_close = float(closes[j])
                if b_close <= 0:
                    continue
                c_close = cb.close_at(candles[j].timestamp)
                if c_close is None:
                    continue
                window.append(c_close / b_close - 1.0)
            if len(window) < _MIN_WINDOW_PREMIUMS:
                return None
            threshold = float(np.percentile(window, pct_threshold))
            if current_premium < threshold:
                return None

            # --- Risk framing via ATR (LONG: trailing stop below, no TP) ---
            atr_result = ATR(period=atr_period).calculate(series)
            atr_vals = atr_result.values[~np.isnan(atr_result.values)]
            if len(atr_vals) < 1:
                return None
            atr_curr = float(atr_vals[-1])
            if atr_curr <= 0:
                return None

            stop_loss = max(binance_close - atr_stop_mult * atr_curr, binance_close * 0.001)
            indicators = {
                "coinbase_premium": current_premium,
                "premium_pct_threshold": threshold,
                "atr": atr_curr,
            }
            span = max(abs(threshold), 1e-6)
            strength = max(0.4, min(1.0, 0.4 + 0.6 * min((current_premium - threshold) / span, 1.0)))

            return TradingSignal(
                direction=SignalDirection.LONG,
                symbol=symbol,
                price=binance_close,
                strength=strength,
                stop_loss=stop_loss,
                take_profit=None,   # trailing stop
                indicators=indicators,
                metadata={"trigger": "coinbase_premium_long"},
            )

        except (ValueError, KeyError, IndexError) as exc:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(exc),
            ) from exc
