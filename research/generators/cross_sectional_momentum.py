"""Cross-sectional relative-strength momentum generator (H-2026-06-008).

Research-stage generator for the uncovered TRENDING_BULL / dispersion regime.
Long-only, spot (deployable if it passes). On a periodic rebalance grid, goes
LONG the symbol while it sits in the top-k of the universe by trailing relative
return -- a CROSS-SECTIONAL signal (rank across symbols), distinct from the DEAD
single-symbol (absolute) momentum corpses.

Mechanism (H-2026-06-008): relative winners keep outperforming short-term because
flows chase recent relative strength with a lag (under-reaction + attention). The
counterparty is late rotators / non-rotating holders. Crypto evidence:
Liu & Tsyvinski (2021).

Cross-symbol via a precomputed panel. The per-symbol backtest workers are isolated,
so the cross-sectional rank is precomputed in the PARENT (research/data/xs_rank.py)
and cached per symbol; this generator only reads ``RankSeries.in_top_k_at(ts)``
(causal: the rank at a bar uses only closes at-or-before it). If the panel is
absent (cache miss) the generator fails closed.

ENTRY: on a rebalance-grid bar (every ``rebalance_bars`` hours, anchored to the
epoch so it is computable from the timestamp alone), if the symbol is in the
top-k, emit LONG with a TRAILING ATR stop (take_profit None). The trader skips a
same-direction signal while already long (trader.py), so re-emitting each
rebalance while still top-k is a no-op; the trailing stop exits on reversal and
the next rebalance re-enters if the symbol is top-k again.

One-way dependency: research/ imports src/, never the reverse. Loaded via the
factory's ``register_generator`` hook (DEC-2026-06-04-019). NEVER added to src/
before DSR validation.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from research.data import xs_rank
from research.data.xs_rank import RankSeries
from src.core.exceptions import SignalGenerationError
from src.core.indicators import ATR
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)

_MS_PER_HOUR = 3_600_000

# Per-process memo of loaded rank panels (one disk read per symbol per process,
# including spawned workers). Distinct dict from the other research generators.
_RANK_BY_SYMBOL: dict[str, RankSeries | None] = {}


def _rank_for(symbol: str) -> RankSeries | None:
    """Return the cached rank series for ``symbol`` (memoized, no recompute)."""
    if symbol not in _RANK_BY_SYMBOL:
        _RANK_BY_SYMBOL[symbol] = xs_rank.load_cached(symbol)
        if _RANK_BY_SYMBOL[symbol] is None:
            logger.warning("xs_rank_cache_missing", symbol=symbol)
    return _RANK_BY_SYMBOL[symbol]


class CrossSectionalMomentumGenerator(SignalGenerator):
    """Long-only: hold the top-k relative-strength symbols on a rebalance grid.

    Entry (LONG) requires ALL of:
        1. Rebalance bar: the bar's epoch-hour is a multiple of ``rebalance_bars``
           (a fixed grid, e.g. 24 -> daily at 00:00 UTC).
        2. Top-k membership: the precomputed cross-symbol rank panel marks this
           symbol as in the top-k by trailing relative return at this bar.

    Exit is a TRAILING ATR stop (take_profit None).

    Required parameters:
        rs_lookback_bars, top_k_fraction (panel-build, read by the parent),
        rebalance_bars, atr_period, atr_stop_multiplier
    """

    @property
    def template_id(self) -> str:
        """Return the template ID this generator handles."""
        return "cross_sectional_momentum"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars: ATR warmup + buffer (rank is precomputed)."""
        return 50

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate the cross-sectional top-k LONG entry conditions.

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
            rebalance_bars: int = int(params["rebalance_bars"])
            atr_period: int = int(params["atr_period"])
            atr_stop_mult: float = float(params["atr_stop_multiplier"])

            # --- Rebalance grid: fixed cadence, computable from the timestamp ---
            current_ts = series[-1].timestamp   # tz-aware UTC bar timestamp
            ts_ms = int(current_ts.timestamp() * 1000)
            if (ts_ms // _MS_PER_HOUR) % rebalance_bars != 0:
                return None

            # --- Cross-sectional rank gate (causal): fail closed if unknown ---
            rank = _rank_for(symbol)
            if rank is None:
                return None
            in_top_k = rank.in_top_k_at(current_ts)
            if not in_top_k:
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

            return TradingSignal(
                direction=SignalDirection.LONG,
                symbol=symbol,
                price=price,
                strength=0.6,   # binary top-k membership; fixed moderate strength
                stop_loss=stop_loss,
                take_profit=None,   # trailing stop -> ride the relative-strength run
                indicators={"atr": atr_curr},
                metadata={"trigger": "cross_sectional_momentum_long"},
            )

        except (ValueError, KeyError, IndexError) as exc:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(exc),
            ) from exc
