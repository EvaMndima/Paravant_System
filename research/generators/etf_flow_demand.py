"""Spot-ETF net-flow structural-demand signal generator (H-2026-06-007).

Research-stage generator for the uncovered TRENDING_BULL / accumulation regime.
Long-only, spot (DEPLOYABLE if it passes). Goes LONG after a large daily net
INFLOW into the US spot ETF for the asset, on the thesis that ETF creations are
mechanical, price-insensitive spot buying whose published flow diffuses into
slow-money positioning over the next few days.

Mechanism (H-2026-06-007): a large net-inflow day forces issuers/APs to buy real
spot; the published flow then under-reacts into slow-allocator positioning. The
counterparty is the liquidity providers selling into mechanical creation-buying
plus slow allocators reacting after the print. This is a STRUCTURAL spot-flow
signal -- distinct from perp funding (leverage positioning, the closed family)
and from price action. Crypto-native to the 2024+ spot-ETF era.

DAILY signal on 1H bars (the funding-channel pattern). The ETF flow is a daily
cadence; it is applied as a slowly-varying CAUSAL gate on the 1H backtest. The
generator makes at most ONE decision per UTC day, at the noon (12:00 UTC) bar --
by which time the prior day's flow is published (Farside posts ~01:00-03:00 UTC).
``EtfFlowSeries.net_flow_at`` returns only flows whose publication (date + 1 day)
is at-or-before the bar, so no unpublished flow is ever used.

EXIT: a TRAILING stop (stop_loss set, take_profit None) -- the engine trails the
stop favorably each bar (portfolio.py), letting the position ride the multi-day
drift and exit on reversal. This expresses the ``holding_days`` intent without a
hard timer (the engine has no time-exit).

One-way dependency: research/ imports src/, never the reverse. Reuses the FREE
ETF-flow channel (research/data/etf_flows.py); loaded via the factory's runtime
``register_generator`` hook (DEC-2026-06-04-019). NEVER added to src/ pre-validation.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from research.data import etf_flows
from research.data.etf_flows import EtfFlowSeries
from src.core.exceptions import SignalGenerationError
from src.core.indicators import ATR
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Minimum flows in the trailing window for a meaningful percentile rank.
_MIN_WINDOW_FLOWS = 20

# The single decision hour per UTC day (noon -> prior-day flow is published).
_DECISION_HOUR_UTC = 12

# Per-process memo of loaded flow series (one disk read per symbol per process,
# including spawned workers). Distinct dict from the funding generators.
_FLOWS_BY_SYMBOL: dict[str, EtfFlowSeries | None] = {}


def _flows_for(symbol: str) -> EtfFlowSeries | None:
    """Return the cached ETF-flow series for ``symbol`` (memoized, no network)."""
    if symbol not in _FLOWS_BY_SYMBOL:
        _FLOWS_BY_SYMBOL[symbol] = etf_flows.load_cached(symbol)
        if _FLOWS_BY_SYMBOL[symbol] is None:
            logger.warning("etf_flow_cache_missing", symbol=symbol)
    return _FLOWS_BY_SYMBOL[symbol]


class EtfFlowDemandGenerator(SignalGenerator):
    """Long-only: go long after a large, top-percentile daily ETF net inflow.

    Entry (LONG) requires ALL of:
        1. Decision bar: the bar is the noon (12:00 UTC) bar -- one decision per
           day, after the prior day's flow is published (causal).
        2. Inflow: the causal current net flow is POSITIVE (net creation).
        3. Large: that flow is >= the ``flow_percentile_threshold`` percentile of
           the trailing ``flow_lookback_days`` window (needs at least
           ``_MIN_WINDOW_FLOWS`` flows to rank).

    Exit is a TRAILING ATR stop (take_profit None) to ride the multi-day drift.

    Required parameters:
        flow_lookback_days, flow_percentile_threshold, holding_days,
        atr_period, atr_stop_multiplier
    """

    @property
    def template_id(self) -> str:
        """Return the template ID this generator handles."""
        return "etf_flow_demand"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars: ATR warmup + buffer (no long-EMA needed)."""
        return 50

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate the ETF-flow structural-demand LONG entry conditions.

        Args:
            series: Causal OHLCV window ending at the decision bar.
            params: Validated strategy parameters.
            symbol: Trading pair symbol (must have a US spot ETF: BTC/ETH).

        Returns:
            A LONG ``TradingSignal`` if all conditions hold, else None.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            lookback_days: int = int(params["flow_lookback_days"])
            pct_threshold: float = float(params["flow_percentile_threshold"])
            atr_period: int = int(params["atr_period"])
            atr_stop_mult: float = float(params["atr_stop_multiplier"])

            # --- One decision per UTC day, after publication ---
            current_ts = series[-1].timestamp   # tz-aware UTC bar timestamp
            if current_ts.hour != _DECISION_HOUR_UTC:
                return None

            # --- ETF-flow gate (causal): fail closed if unknown ---
            flows = _flows_for(symbol)
            if flows is None:
                return None
            current_flow = flows.net_flow_at(current_ts)
            if current_flow is None or current_flow <= 0.0:
                # Need a POSITIVE net inflow (creation pressure); fail closed.
                return None
            window = flows.window_flows(current_ts, lookback_days)
            if len(window) < _MIN_WINDOW_FLOWS:
                return None
            threshold_flow = float(np.percentile(window, pct_threshold))
            if current_flow < threshold_flow:
                return None

            # --- Risk framing via ATR (LONG: trailing stop below, no TP) ---
            atr_result = ATR(period=atr_period).calculate(series)
            atr_vals = atr_result.values[~np.isnan(atr_result.values)]
            if len(atr_vals) < 1:
                return None
            atr_curr = float(atr_vals[-1])
            if atr_curr <= 0:
                return None

            price = float(series.closes[-1])
            stop_loss = max(price - atr_stop_mult * atr_curr, price * 0.001)

            indicators = {
                "etf_net_flow_usd_m": current_flow,
                "etf_flow_pct_threshold": threshold_flow,
                "atr": atr_curr,
            }
            # Strength scales with how far the inflow exceeds the percentile cut.
            span = max(threshold_flow, 1.0)
            strength = max(0.4, min(1.0, 0.4 + 0.6 * min((current_flow - threshold_flow) / span, 1.0)))

            return TradingSignal(
                direction=SignalDirection.LONG,
                symbol=symbol,
                price=price,
                strength=strength,
                stop_loss=stop_loss,
                take_profit=None,   # trailing stop -> ride the multi-day drift
                indicators=indicators,
                metadata={
                    "trigger": "etf_flow_demand_long",
                    "etf_net_flow_usd_m": current_flow,
                },
            )

        except (ValueError, KeyError, IndexError) as exc:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(exc),
            ) from exc
