"""Coinbase spot price history for the research layer (H-2026-06-010).

Fetches and caches Coinbase Exchange 1H candles (e.g. BTC-USD) so a research
generator can compute the "Coinbase premium" = Coinbase price / offshore
(Binance) price - 1, a documented signal of US-regulated institutional spot
demand. The premium persists because the cross-venue arb is friction-limited
(KYC, banking, USD<->USDT), so it is NOT a leverage/funding signal.

CAUSALITY. ``CoinbasePriceSeries.close_at(ts)`` returns the close of the Coinbase
bar at-or-before ``ts`` (same 1H grid as Binance). A generator computes the
premium from the just-closed decision bar of BOTH venues -- both known at the bar
close -- and the backtest fills on the NEXT bar open, so no future price is used.

Network model. The PARENT process pre-fetches the Coinbase history to a per-symbol
disk cache before any worker spawns; workers/generators only ``load_cached``. The
Coinbase host needs the OS trust store (parent injects it) and a browser UA. The
public candles endpoint caps each request at 300 candles, so the fetch paginates.

One-way dependency: research/ imports src/, never the reverse. Standard library
+ requests only.
"""
from __future__ import annotations

import bisect
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from src.utils.logging import get_logger

logger = get_logger(__name__)

_CANDLES_URL = "https://api.exchange.coinbase.com/products/{product}/candles"
_GRANULARITY_S = 3600          # 1H
_MAX_CANDLES = 300             # Coinbase per-request cap
_PAGE_PAUSE_S = 0.3
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
_CACHE_DIR = Path("research/.cache/coinbase")

# Binance symbol (USDT-quoted) -> Coinbase product (USD-quoted).
_PRODUCT_FOR: dict[str, str] = {"BTCUSDT": "BTC-USD", "ETHUSDT": "ETH-USD"}


@dataclass(frozen=True)
class CoinbasePriceSeries:
    """Immutable Coinbase 1H close history with a causal lookup.

    Attributes:
        symbol: The Binance symbol these Coinbase prices pair with (e.g. BTCUSDT).
        times_ms: Bar open times in epoch ms, sorted ascending.
        closes: Coinbase close aligned 1:1 with ``times_ms``.
    """

    symbol: str
    times_ms: tuple[int, ...]
    closes: tuple[float, ...]

    def __len__(self) -> int:
        """Return the number of bars."""
        return len(self.times_ms)

    def close_at(self, ts: datetime) -> float | None:
        """Return the Coinbase close at-or-before ``ts`` (causal lookup).

        Args:
            ts: Timezone-aware UTC instant (a decision-bar timestamp).

        Returns:
            The Coinbase close, or None if ``ts`` precedes the first bar.

        Raises:
            ValueError: If ``ts`` is not timezone-aware.
        """
        if ts.tzinfo is None:
            raise ValueError("close_at requires a timezone-aware datetime")
        pos = bisect.bisect_right(self.times_ms, int(ts.timestamp() * 1000))
        if pos == 0:
            return None
        return self.closes[pos - 1]


def _cache_path(symbol: str) -> Path:
    """Return the on-disk cache path for ``symbol``'s Coinbase history."""
    return _CACHE_DIR / f"{symbol}.json"


def _iso(ts_s: int) -> str:
    """Format epoch seconds as an RFC3339 UTC string for the Coinbase API."""
    return datetime.fromtimestamp(ts_s, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_candles(
    symbol: str,
    start: datetime,
    end: datetime,
    *,
    session: requests.Session | None = None,
) -> CoinbasePriceSeries:
    """Fetch Coinbase 1H closes for ``symbol`` over ``[start, end]`` (paginated).

    Args:
        symbol: Binance symbol (mapped to a Coinbase product).
        start: Timezone-aware inclusive UTC window start.
        end: Timezone-aware inclusive UTC window end.
        session: Optional ``requests.Session``.

    Returns:
        A ``CoinbasePriceSeries`` sorted ascending and de-duplicated.

    Raises:
        ValueError: If ``symbol`` has no Coinbase product or window is invalid.
        requests.HTTPError: On a non-200 response.
    """
    product = _PRODUCT_FOR.get(symbol)
    if product is None:
        raise ValueError(f"no Coinbase product for symbol {symbol}")
    if start.tzinfo is None or end.tzinfo is None or start > end:
        raise ValueError("start/end must be tz-aware with start <= end")

    sess = session or requests.Session()
    url = _CANDLES_URL.format(product=product)
    window_s = _MAX_CANDLES * _GRANULARITY_S
    cursor = int(start.timestamp())
    end_s = int(end.timestamp())

    merged: dict[int, float] = {}
    pages = 0
    while cursor <= end_s:
        chunk_end = min(cursor + window_s, end_s)
        resp = sess.get(
            url,
            params={"granularity": _GRANULARITY_S, "start": _iso(cursor), "end": _iso(chunk_end)},
            headers=_HEADERS,
            timeout=25,
        )
        resp.raise_for_status()
        pages += 1
        for row in resp.json():   # [time_s, low, high, open, close, volume]
            t_s = int(row[0])
            merged[t_s * 1000] = float(row[4])
        cursor = chunk_end + _GRANULARITY_S
        time.sleep(_PAGE_PAUSE_S)

    ordered = sorted(merged.items())
    series = CoinbasePriceSeries(
        symbol=symbol,
        times_ms=tuple(t for t, _ in ordered),
        closes=tuple(c for _, c in ordered),
    )
    logger.info("coinbase_fetched", symbol=symbol, product=product, bars=len(series), pages=pages)
    return series


def _write_cache(series: CoinbasePriceSeries) -> None:
    """Persist a ``CoinbasePriceSeries`` to its per-symbol JSON cache."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "symbol": series.symbol,
        "times_ms": list(series.times_ms),
        "closes": list(series.closes),
    }
    _cache_path(series.symbol).write_text(json.dumps(payload), encoding="utf-8")


def load_cached(symbol: str) -> CoinbasePriceSeries | None:
    """Load ``symbol``'s Coinbase history from disk cache (no network).

    Args:
        symbol: Binance symbol.

    Returns:
        The cached ``CoinbasePriceSeries``, or None if absent.
    """
    path = _cache_path(symbol)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return CoinbasePriceSeries(
        symbol=data["symbol"],
        times_ms=tuple(int(t) for t in data["times_ms"]),
        closes=tuple(float(c) for c in data["closes"]),
    )


def load_or_fetch(
    symbol: str,
    start: datetime,
    end: datetime,
    *,
    use_cache: bool = True,
    session: requests.Session | None = None,
) -> CoinbasePriceSeries:
    """Return cached Coinbase prices if they cover ``[start, end]``, else fetch.

    Intended to run in the PARENT process before workers spawn.

    Args:
        symbol: Binance symbol.
        start: Timezone-aware inclusive UTC window start.
        end: Timezone-aware inclusive UTC window end.
        use_cache: If True, reuse a cache already covering the window.
        session: Optional ``requests.Session``.

    Returns:
        A ``CoinbasePriceSeries`` covering at least ``[start, end]``.
    """
    if use_cache:
        cached = load_cached(symbol)
        if (
            cached is not None
            and cached.times_ms
            and cached.times_ms[0] <= int(start.timestamp() * 1000)
            and cached.times_ms[-1] >= int(end.timestamp() * 1000) - _GRANULARITY_S * 1000
        ):
            logger.info("coinbase_cache_hit", symbol=symbol, bars=len(cached))
            return cached

    series = fetch_candles(symbol, start, end, session=session)
    if use_cache:
        _write_cache(series)
        logger.info("coinbase_cache_write", symbol=symbol, bars=len(series))
    return series
