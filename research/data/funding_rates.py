"""Binance perpetual funding-rate history for the research layer.

Fetches and caches historical 8-hour funding rates from the Binance USD-M
futures public endpoint (``/fapi/v1/fundingRate``). Used by research generators
to condition entries on the funding regime (H-2026-06-003 funding-confirmed
trend). Funding has no equity analogue: it is the price leveraged longs pay
shorts on perpetual swaps, a crypto-native derivatives-flow signal.

CAUSALITY (leak-free by construction). Funding prints are stamped at their
settlement time. ``FundingSeries.rate_at(ts)`` returns the most recent funding
KNOWN at-or-before ``ts`` (strictly ``funding_time <= ts``), never a future
print. A backtest generator that calls ``rate_at(visible_series[-1].timestamp)``
therefore conditions only on information available at the bar it trades on --
directly addressing the funding-leakage fail mode pre-registered for
H-2026-06-003.

Network model. The PARENT process pre-fetches each symbol's funding history to a
per-symbol disk cache (``research/.cache/funding/<symbol>.json``) BEFORE any
backtest worker spawns; workers (and generators) only ever ``load_cached`` --
pure disk reads, no network. This mirrors ``scripts/regime_dsr.py`` fetching
OHLCV in the parent (parallel cross-process fetches trigger Binance connection
resets).

One-way dependency: research/ may import src/, never the reverse (PRD 5.2). This
module imports only the standard library + requests.
"""
from __future__ import annotations

import bisect
import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Binance USD-M futures public REST host (funding rate is a futures concept; the
# spot api.binance.com host the rest of the system uses does not serve it).
_FAPI_FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"

# Max records the endpoint returns per call.
_PAGE_LIMIT = 1000

# Politeness pause between paginated calls (seconds). The endpoint is generous,
# but a small gap avoids hammering it during a multi-page backfill.
_PAGE_PAUSE_S = 0.25

# Per-symbol on-disk cache (NOT committed; transient like the regime_dsr cache).
_CACHE_DIR = Path("research/.cache/funding")


@dataclass(frozen=True)
class FundingSeries:
    """Immutable per-symbol funding-rate history with a causal lookup.

    Attributes:
        symbol: Trading pair (e.g. ``BTCUSDT``).
        times_ms: Funding settlement times in epoch milliseconds, sorted
            ascending and de-duplicated.
        rates: Funding rate per 8h aligned 1:1 with ``times_ms`` (e.g.
            ``0.0001`` == 0.01% per 8h).
        covered_start_ms: Inclusive start of the fetched window (epoch ms).
        covered_end_ms: Inclusive end of the fetched window (epoch ms).
    """

    symbol: str
    times_ms: tuple[int, ...]
    rates: tuple[float, ...]
    covered_start_ms: int
    covered_end_ms: int

    def __len__(self) -> int:
        """Return the number of funding prints."""
        return len(self.times_ms)

    def rate_at(self, ts: datetime) -> float | None:
        """Return the most recent funding rate known at-or-before ``ts``.

        Causal lookup: finds the last print whose settlement time is ``<= ts``.
        Returns None if no funding print exists at-or-before ``ts`` (e.g. ``ts``
        precedes the first cached print), so a generator can fail closed (skip
        the entry) rather than assume a value.

        Args:
            ts: Timezone-aware UTC instant (typically the close timestamp of the
                last visible bar).

        Returns:
            The funding rate per 8h in effect at ``ts``, or None if unknown.

        Raises:
            ValueError: If ``ts`` is not timezone-aware.
        """
        if ts.tzinfo is None:
            raise ValueError("rate_at requires a timezone-aware datetime")
        ts_ms = int(ts.timestamp() * 1000)
        # bisect_right -> index of first time strictly greater than ts_ms; the
        # element before it (pos-1) is the latest time <= ts_ms (causal).
        pos = bisect.bisect_right(self.times_ms, ts_ms)
        if pos == 0:
            return None
        return self.rates[pos - 1]


def _cache_path(symbol: str) -> Path:
    """Return the on-disk cache path for ``symbol``'s funding history."""
    return _CACHE_DIR / f"{symbol}.json"


def _to_ms(ts: datetime) -> int:
    """Convert a timezone-aware datetime to epoch milliseconds."""
    if ts.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return int(ts.timestamp() * 1000)


def fetch_funding_history(
    symbol: str,
    start: datetime,
    end: datetime,
    *,
    session: requests.Session | None = None,
) -> FundingSeries:
    """Fetch the full 8h funding history for ``symbol`` over ``[start, end]``.

    Paginates the public endpoint (ascending, ``_PAGE_LIMIT`` per call) until the
    window is covered. Network-bound; never writes to the network.

    Args:
        symbol: Trading pair (e.g. ``BTCUSDT``).
        start: Timezone-aware inclusive UTC window start.
        end: Timezone-aware inclusive UTC window end.
        session: Optional ``requests.Session`` to reuse a connection pool.

    Returns:
        A ``FundingSeries`` sorted ascending and de-duplicated.

    Raises:
        ValueError: If ``start``/``end`` are naive or ``start > end``.
        requests.HTTPError: If the endpoint returns a non-200 status.
    """
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start and end must be timezone-aware")
    if start > end:
        raise ValueError(f"start {start} must be <= end {end}")

    sess = session or requests.Session()
    start_ms = _to_ms(start)
    end_ms = _to_ms(end)

    times: list[int] = []
    rates: list[float] = []
    cursor = start_ms
    pages = 0
    while cursor <= end_ms:
        # Annotated rather than inline: a literal mixing str and int values
        # infers as dict[str, object], which requests' params does not accept.
        params: dict[str, str | int] = {
            "symbol": symbol,
            "startTime": cursor,
            "endTime": end_ms,
            "limit": _PAGE_LIMIT,
        }
        resp = sess.get(_FAPI_FUNDING_URL, params=params, timeout=25)
        resp.raise_for_status()
        batch = resp.json()
        pages += 1
        if not batch:
            break
        for row in batch:
            t = int(row["fundingTime"])
            if t < start_ms or t > end_ms:
                continue
            times.append(t)
            rates.append(float(row["fundingRate"]))
        # Advance past the last fundingTime in this page; stop if the page was
        # not full (no more history in the window).
        last_t = int(batch[-1]["fundingTime"])
        if len(batch) < _PAGE_LIMIT or last_t <= cursor:
            break
        cursor = last_t + 1
        time.sleep(_PAGE_PAUSE_S)

    # De-duplicate while preserving ascending order (pages can overlap by 1ms).
    dedup: dict[int, float] = {}
    for t, r in zip(times, rates):
        dedup[t] = r
    ordered = sorted(dedup.items())

    series = FundingSeries(
        symbol=symbol,
        times_ms=tuple(t for t, _ in ordered),
        rates=tuple(r for _, r in ordered),
        covered_start_ms=start_ms,
        covered_end_ms=end_ms,
    )
    logger.info(
        "funding_fetched",
        symbol=symbol,
        prints=len(series),
        pages=pages,
        start=start.isoformat(),
        end=end.isoformat(),
    )
    return series


def _write_cache(series: FundingSeries) -> None:
    """Persist a ``FundingSeries`` to its per-symbol JSON cache."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "symbol": series.symbol,
        "covered_start_ms": series.covered_start_ms,
        "covered_end_ms": series.covered_end_ms,
        "times_ms": list(series.times_ms),
        "rates": list(series.rates),
    }
    _cache_path(series.symbol).write_text(json.dumps(payload), encoding="utf-8")


def load_cached(symbol: str) -> FundingSeries | None:
    """Load ``symbol``'s funding history from disk cache (no network).

    Used by backtest workers and generators, which must never hit the network
    (the parent pre-fetches). Returns None if no cache exists.

    Args:
        symbol: Trading pair.

    Returns:
        The cached ``FundingSeries``, or None if absent.
    """
    path = _cache_path(symbol)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return FundingSeries(
        symbol=data["symbol"],
        times_ms=tuple(int(t) for t in data["times_ms"]),
        rates=tuple(float(r) for r in data["rates"]),
        covered_start_ms=int(data["covered_start_ms"]),
        covered_end_ms=int(data["covered_end_ms"]),
    )


def load_or_fetch(
    symbol: str,
    start: datetime,
    end: datetime,
    *,
    use_cache: bool = True,
    session: requests.Session | None = None,
) -> FundingSeries:
    """Return cached funding if it covers ``[start, end]``, else fetch + cache.

    Intended to run in the PARENT process before backtest workers spawn.

    Args:
        symbol: Trading pair.
        start: Timezone-aware inclusive UTC window start.
        end: Timezone-aware inclusive UTC window end.
        use_cache: If True, reuse a cache that covers the requested window.
        session: Optional ``requests.Session``.

    Returns:
        A ``FundingSeries`` covering at least ``[start, end]``.
    """
    if use_cache:
        cached = load_cached(symbol)
        if (
            cached is not None
            and cached.covered_start_ms <= _to_ms(start)
            and cached.covered_end_ms >= _to_ms(end)
        ):
            logger.info(
                "funding_cache_hit", symbol=symbol, prints=len(cached),
            )
            return cached

    series = fetch_funding_history(symbol, start, end, session=session)
    if use_cache:
        _write_cache(series)
        logger.info("funding_cache_write", symbol=symbol, prints=len(series))
    return series
