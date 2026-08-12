"""BTC reference-momentum series for the research layer (H-2026-06-011).

The BTC-led lead-lag generator trades a mid-cap ALT but must see BTC's recent
move at the decision bar. The per-symbol backtest workers are isolated (a worker
sees only its own alt's series), so BTC's trailing-return ("thrust") series is
precomputed in the PARENT from BTC 1H closes and cached; workers/generators only
``load_cached`` (the funding-channel network model).

CAUSALITY (leak-free by construction). The thrust at bar ``t`` is
``btc_close[t] / btc_close[t - lookback] - 1`` -- only closes at-or-before ``t``.
``BtcThrustSeries.thrust_at(ts)`` returns the thrust at the latest BTC bar
at-or-before ``ts``. No future bar enters.

One-way dependency: research/ imports src/, never the reverse. Standard library
+ numpy only.
"""
from __future__ import annotations

import bisect
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

from src.data.market_data import OHLCVSeries
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Bar duration. These series are 1H and are stamped with bar OPEN times,
# so a bar is only knowable _BAR_MS after its timestamp.
_BAR_MS = 3_600_000

_CACHE_DIR = Path("research/.cache/btc_reference")
# Single fixed cache key (the reference is the same for every alt).
_CACHE_NAME = "BTC_THRUST"


@dataclass(frozen=True)
class BtcThrustSeries:
    """Immutable BTC trailing-return ("thrust") series with a causal lookup.

    Attributes:
        times_ms: BTC bar timestamps (epoch ms), sorted ascending.
        thrust: Trailing return aligned 1:1 with ``times_ms`` (NaN during warmup).
    """

    times_ms: tuple[int, ...]
    thrust: tuple[float, ...]

    def __len__(self) -> int:
        """Return the number of bars."""
        return len(self.times_ms)

    def thrust_at(self, ts: datetime) -> float | None:
        """Return BTC's thrust at the last bar to have CLOSED at-or-before ``ts``.

        Args:
            ts: Timezone-aware UTC instant (an alt decision-bar timestamp).

        Returns:
            BTC's trailing return at-or-before ``ts``, or None if before the
            series / still in warmup (NaN).

        Raises:
            ValueError: If ``ts`` is not timezone-aware.
        """
        if ts.tzinfo is None:
            raise ValueError("thrust_at requires a timezone-aware datetime")
        # Select on the bar's CLOSE. times_ms holds bar OPEN times while thrust
        # is computed from closes[i], so a bar is knowable only after _BAR_MS.
        # See DEC-2026-08-13-001.
        pos = bisect.bisect_right(self.times_ms, int(ts.timestamp() * 1000) - _BAR_MS)
        if pos == 0:
            return None
        value = self.thrust[pos - 1]
        if value != value:   # NaN (warmup)
            return None
        return value


def _cache_path() -> Path:
    """Return the on-disk cache path for the BTC thrust series."""
    return _CACHE_DIR / f"{_CACHE_NAME}.json"


def compute_thrust(btc_series: OHLCVSeries, *, lookback_bars: int) -> BtcThrustSeries:
    """Compute BTC's trailing-return series from 1H closes.

    Args:
        btc_series: BTC 1H OHLCV series.
        lookback_bars: Trailing window (bars) for the return.

    Returns:
        A ``BtcThrustSeries`` aligned to the BTC bars (NaN for the warmup head).
    """
    closes = btc_series.closes
    times = [int(c.timestamp.timestamp() * 1000) for c in btc_series.candles]
    thrust: list[float] = []
    for i in range(len(closes)):
        if i < lookback_bars or closes[i - lookback_bars] <= 0:
            thrust.append(float("nan"))
        else:
            thrust.append(float(closes[i]) / float(closes[i - lookback_bars]) - 1.0)
    return BtcThrustSeries(times_ms=tuple(times), thrust=tuple(thrust))


def _write_cache(series: BtcThrustSeries) -> None:
    """Persist the BTC thrust series to its JSON cache."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"times_ms": list(series.times_ms), "thrust": list(series.thrust)}
    _cache_path().write_text(json.dumps(payload), encoding="utf-8")


def load_cached() -> BtcThrustSeries | None:
    """Load the BTC thrust series from disk cache (no network/compute).

    Returns:
        The cached ``BtcThrustSeries``, or None if absent.
    """
    path = _cache_path()
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return BtcThrustSeries(
        times_ms=tuple(int(t) for t in data["times_ms"]),
        thrust=tuple(float(x) for x in data["thrust"]),
    )


def compute_and_cache(btc_series: OHLCVSeries, *, lookback_bars: int) -> None:
    """Compute BTC's thrust series and cache it (parent process, pre-spawn).

    Args:
        btc_series: BTC 1H OHLCV series fetched by the parent.
        lookback_bars: Trailing window (bars) for the return.
    """
    series = compute_thrust(btc_series, lookback_bars=lookback_bars)
    _write_cache(series)
    n_valid = int(np.sum(~np.isnan(np.array(series.thrust))))
    logger.info(
        "btc_thrust_cached", bars=len(series), valid=n_valid, lookback_bars=lookback_bars
    )
