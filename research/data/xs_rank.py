"""Cross-symbol relative-strength rank panel for the research layer.

Computes, for each symbol, a per-bar boolean "is this symbol in the top-k by
trailing relative return among the universe" -- the cross-sectional signal
H-2026-06-008 needs. The per-symbol backtest workers in ``scripts/regime_dsr.py``
are isolated (a worker sees only its own symbol's series), so the rank, which is
inherently cross-symbol, is precomputed in the PARENT from all symbols' series
and cached per symbol; workers/generators only ``load_cached`` (the funding-channel
network model).

CAUSALITY (leak-free by construction). The rank at bar time ``t`` uses each
symbol's trailing return ``close[t]/close[t - lookback] - 1`` -- all closes at-or-
before ``t``. ``RankSeries.in_top_k_at(ts)`` returns the membership at the latest
panel bar at-or-before ``ts``. No future bar enters the rank.

Alignment. Ranks are computed only on the timestamp INTERSECTION of the universe
(bars all symbols share), so a missing bar in one symbol never produces a stale
cross-section. For liquid majors on the same 1H grid this is the full grid.

One-way dependency: research/ imports src/, never the reverse. Standard library
+ numpy only.
"""
from __future__ import annotations

import bisect
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from src.data.market_data import OHLCVSeries
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Per-symbol on-disk cache (NOT committed; transient like the funding cache).
_CACHE_DIR = Path("research/.cache/xs_rank")


@dataclass(frozen=True)
class RankSeries:
    """Immutable per-symbol top-k membership over the shared panel grid.

    Attributes:
        symbol: Trading pair.
        times_ms: Panel bar timestamps (epoch ms), sorted ascending. These are
            the timestamps the universe shares (intersection grid).
        in_top_k: Booleans aligned 1:1 with ``times_ms`` -- True when the symbol
            is in the top-k by trailing relative return at that bar.
    """

    symbol: str
    times_ms: tuple[int, ...]
    in_top_k: tuple[bool, ...]

    def __len__(self) -> int:
        """Return the number of panel bars."""
        return len(self.times_ms)

    def in_top_k_at(self, ts: datetime) -> bool | None:
        """Return top-k membership at the latest panel bar at-or-before ``ts``.

        Causal: never looks past ``ts``. Returns None if ``ts`` precedes the
        first panel bar (membership unknown -> generator fails closed).

        Args:
            ts: Timezone-aware UTC instant (a decision bar timestamp).

        Returns:
            True/False membership, or None if before the panel starts.

        Raises:
            ValueError: If ``ts`` is not timezone-aware.
        """
        if ts.tzinfo is None:
            raise ValueError("in_top_k_at requires a timezone-aware datetime")
        pos = bisect.bisect_right(self.times_ms, int(ts.timestamp() * 1000))
        if pos == 0:
            return None
        return self.in_top_k[pos - 1]


def _cache_path(symbol: str) -> Path:
    """Return the on-disk cache path for ``symbol``'s rank series."""
    return _CACHE_DIR / f"{symbol}.json"


def _series_closes_by_ms(series: OHLCVSeries) -> dict[int, float]:
    """Map each bar's epoch-ms timestamp to its close for one symbol."""
    closes = series.closes
    out: dict[int, float] = {}
    for i, candle in enumerate(series.candles):
        out[int(candle.timestamp.timestamp() * 1000)] = float(closes[i])
    return out


def compute_panel(
    series_by_symbol: dict[str, OHLCVSeries],
    *,
    rs_lookback_bars: int,
    top_k_fraction: float,
) -> dict[str, RankSeries]:
    """Compute per-symbol top-k membership over the shared timestamp grid.

    Args:
        series_by_symbol: Each universe symbol's causal OHLCV series.
        rs_lookback_bars: Trailing window (bars) for the relative-return rank.
        top_k_fraction: Fraction of the universe counted as "top" (e.g. 0.25);
            at least one symbol is always selected.

    Returns:
        A ``RankSeries`` per symbol over the intersection grid.
    """
    symbols = sorted(series_by_symbol)
    closes_by_symbol = {s: _series_closes_by_ms(series_by_symbol[s]) for s in symbols}

    # Intersection grid: bars every symbol shares (no stale cross-sections).
    common: list[int] = sorted(
        set.intersection(*[set(closes_by_symbol[s]) for s in symbols])
    )
    n = len(common)
    top_count = max(1, math.ceil(top_k_fraction * len(symbols)))

    # Aligned close matrix [symbol][grid_index].
    aligned = {s: np.array([closes_by_symbol[s][t] for t in common]) for s in symbols}

    membership = {s: [False] * n for s in symbols}
    for i in range(rs_lookback_bars, n):
        rets: list[tuple[float, str]] = []
        for s in symbols:
            prior = aligned[s][i - rs_lookback_bars]
            if prior > 0:
                rets.append((aligned[s][i] / prior - 1.0, s))
        # Strongest relative return first; mark the top_count symbols.
        rets.sort(key=lambda r: r[0], reverse=True)
        for _, s in rets[:top_count]:
            membership[s][i] = True

    panel = {
        s: RankSeries(
            symbol=s,
            times_ms=tuple(common),
            in_top_k=tuple(membership[s]),
        )
        for s in symbols
    }
    logger.info(
        "xs_rank_panel_computed",
        symbols=symbols,
        grid_bars=n,
        top_count=top_count,
        rs_lookback_bars=rs_lookback_bars,
    )
    return panel


def _write_cache(series: RankSeries) -> None:
    """Persist a ``RankSeries`` to its per-symbol JSON cache."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "symbol": series.symbol,
        "times_ms": list(series.times_ms),
        "in_top_k": [1 if b else 0 for b in series.in_top_k],
    }
    _cache_path(series.symbol).write_text(json.dumps(payload), encoding="utf-8")


def load_cached(symbol: str) -> RankSeries | None:
    """Load ``symbol``'s rank series from disk cache (no network/compute).

    Used by backtest workers and the generator. Returns None if absent.

    Args:
        symbol: Trading pair.

    Returns:
        The cached ``RankSeries``, or None if absent.
    """
    path = _cache_path(symbol)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return RankSeries(
        symbol=data["symbol"],
        times_ms=tuple(int(t) for t in data["times_ms"]),
        in_top_k=tuple(bool(b) for b in data["in_top_k"]),
    )


def compute_and_cache(
    series_list: list[OHLCVSeries],
    *,
    rs_lookback_bars: int,
    top_k_fraction: float,
) -> None:
    """Compute the rank panel from ``series_list`` and cache each symbol.

    Intended to run in the PARENT process before backtest workers spawn (the
    rank is cross-symbol; workers are per-symbol and isolated).

    Args:
        series_list: All universe symbols' causal OHLCV series.
        rs_lookback_bars: Trailing window (bars) for the relative-return rank.
        top_k_fraction: Fraction of the universe counted as "top".
    """
    panel = compute_panel(
        {s.symbol: s for s in series_list},
        rs_lookback_bars=rs_lookback_bars,
        top_k_fraction=top_k_fraction,
    )
    for rank_series in panel.values():
        _write_cache(rank_series)
    logger.info("xs_rank_panel_cached", symbols=sorted(panel))
