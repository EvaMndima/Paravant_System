"""US spot Bitcoin/Ether ETF daily net-flow history for the research layer.

Fetches and caches daily net-flow totals (US$m) for the US spot BTC and ETH ETFs
from Farside Investors' public all-data tables. Used by research generators to
condition entries on the institutional spot-flow regime (H-2026-06-007 ETF-flow
structural demand). ETF creations force the issuer/AP to buy real spot
price-insensitively -- a structural-flow signal distinct from leverage positioning
(perp funding, the closed family) and from price action.

CAUSALITY (leak-free by construction). Each flow is labelled by its UTC trading
date D. Farside posts day-D flow in the evening US time (~01:00-03:00 UTC on
D+1). ``EtfFlowSeries.net_flow_at(ts)`` returns the most recent flow whose
PUBLICATION time is at-or-before ``ts``, modelled conservatively as
``date(D) + 1 day <= ts`` (so day-D flow is treated as known only from D+1
00:00 UTC -- never earlier than it is actually published). A generator that calls
``net_flow_at(visible_series[-1].timestamp)`` therefore conditions only on flow
prints already public at the bar it trades on.

Network model. The PARENT process pre-fetches each asset's flow history to a
per-symbol disk cache (``research/.cache/etf_flows/<symbol>.json``) BEFORE any
backtest worker spawns; workers (and generators) only ``load_cached`` -- pure disk
reads, no network. This mirrors the funding-rate channel. The Farside host sits
behind TLS inspection in some environments; the parent injects the OS trust store
(``scripts/regime_dsr._use_os_trust_store``) before pre-fetching, and a browser
User-Agent is sent (the host 403s default clients).

One-way dependency: research/ may import src/, never the reverse (PRD 5.2). This
module imports only the standard library + requests.
"""
from __future__ import annotations

import bisect
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Farside public all-data tables (one per asset). Static HTML; parsed with stdlib.
_ASSET_URLS: dict[str, str] = {
    "BTCUSDT": "https://farside.co.uk/bitcoin-etf-flow-all-data/",
    "ETHUSDT": "https://farside.co.uk/ethereum-etf-flow-all-data/",
}

# Farside 403s default clients; a browser UA returns 200.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# One UTC day in milliseconds (the conservative publication lag).
_DAY_MS = 86_400_000

# Per-symbol on-disk cache (NOT committed; transient like the funding cache).
_CACHE_DIR = Path("research/.cache/etf_flows")

# A Farside data row starts with a "DD Mon YYYY" date in its first cell.
_DATE_RE = re.compile(r"^\d{2}\s+\w{3}\s+\d{4}$")


@dataclass(frozen=True)
class EtfFlowSeries:
    """Immutable per-asset daily ETF net-flow history with a causal lookup.

    Attributes:
        symbol: Trading pair the flows back (e.g. ``BTCUSDT`` for the BTC ETFs).
        dates_ms: UTC trading dates at 00:00 in epoch milliseconds, sorted
            ascending and de-duplicated. One entry per flow day.
        flows: Daily net-flow total in US$ millions, aligned 1:1 with
            ``dates_ms`` (positive = net inflow, negative = net outflow).
        covered_start_ms: Inclusive start (first flow date) in epoch ms.
        covered_end_ms: Inclusive end (last flow date) in epoch ms.
    """

    symbol: str
    dates_ms: tuple[int, ...]
    flows: tuple[float, ...]
    covered_start_ms: int
    covered_end_ms: int

    def __len__(self) -> int:
        """Return the number of flow days."""
        return len(self.dates_ms)

    def _known_count_at(self, ts_ms: int) -> int:
        """Return how many flow days are PUBLISHED at-or-before ``ts_ms``.

        A day-D flow is treated as known from ``D + 1 day`` (conservative
        publication lag), so the cutoff date is ``ts_ms - _DAY_MS``.
        """
        return bisect.bisect_right(self.dates_ms, ts_ms - _DAY_MS)

    def net_flow_at(self, ts: datetime) -> float | None:
        """Return the most recent net flow PUBLISHED at-or-before ``ts``.

        Causal: only flows whose ``date + 1 day <= ts`` are considered, so a
        generator never sees a flow before it is published. Returns None if no
        flow is published yet at ``ts``.

        Args:
            ts: Timezone-aware UTC instant (typically a bar close timestamp).

        Returns:
            The latest published net flow (US$m), or None if none is known yet.

        Raises:
            ValueError: If ``ts`` is not timezone-aware.
        """
        if ts.tzinfo is None:
            raise ValueError("net_flow_at requires a timezone-aware datetime")
        pos = self._known_count_at(int(ts.timestamp() * 1000))
        if pos == 0:
            return None
        return self.flows[pos - 1]

    def window_flows(self, ts: datetime, lookback_days: int) -> list[float]:
        """Return published net flows in the trailing ``lookback_days`` at ``ts``.

        Causal: only flows published at-or-before ``ts`` (``date + 1 day <= ts``)
        and dated within the trailing window are returned. Used to rank the
        current flow against its recent distribution (a per-asset percentile).

        Args:
            ts: Timezone-aware UTC instant.
            lookback_days: Trailing window length in days.

        Returns:
            Net-flow values (US$m) in the window, chronological order.

        Raises:
            ValueError: If ``ts`` is not timezone-aware.
        """
        if ts.tzinfo is None:
            raise ValueError("window_flows requires a timezone-aware datetime")
        ts_ms = int(ts.timestamp() * 1000)
        hi = self._known_count_at(ts_ms)
        lo = bisect.bisect_left(self.dates_ms, ts_ms - lookback_days * _DAY_MS)
        return list(self.flows[lo:hi])


def _cache_path(symbol: str) -> Path:
    """Return the on-disk cache path for ``symbol``'s ETF-flow history."""
    return _CACHE_DIR / f"{symbol}.json"


def _parse_number(text: str) -> float | None:
    """Parse a Farside flow cell into a float US$m value.

    Handles thousands separators, parenthesised negatives, and the ``-``/empty
    placeholders Farside uses for a no-data day.

    Args:
        text: Raw cell text (e.g. ``"1,234.5"``, ``"(123.4)"``, ``"-"``).

    Returns:
        The numeric value, or None if the cell is a blank/dash placeholder.
    """
    s = text.strip().replace(",", "").replace("$", "")
    if s in ("", "-", "–", "n/a", "N/A"):
        return None
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1]
    try:
        value = float(s)
    except ValueError:
        return None
    return -value if negative else value


def _parse_farside_table(html: str) -> list[tuple[int, float]]:
    """Parse a Farside all-data page into ``(date_ms, total_flow)`` pairs.

    Selects the widest table (the data grid), keeps rows whose first cell is a
    ``DD Mon YYYY`` date, and reads the LAST cell (the daily Total, US$m).

    Args:
        html: Raw HTML of a Farside all-data page.

    Returns:
        Ascending, de-duplicated ``(date_ms, total_flow)`` pairs. Days whose
        Total is a blank/dash placeholder are skipped.
    """
    tables = re.findall(r"<table.*?</table>", html, flags=re.S | re.I)
    if not tables:
        return []
    data_table = max(tables, key=lambda t: len(re.findall(r"<tr", t, flags=re.I)))

    def _cells(row_html: str) -> list[str]:
        raw = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, flags=re.S | re.I)
        return [re.sub(r"<[^>]+>", "", c).strip() for c in raw]

    out: dict[int, float] = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", data_table, flags=re.S | re.I):
        cells = _cells(row)
        if not cells or not _DATE_RE.match(cells[0]):
            continue
        total = _parse_number(cells[-1])
        if total is None:
            continue
        day = datetime.strptime(cells[0], "%d %b %Y").replace(tzinfo=timezone.utc)
        out[int(day.timestamp() * 1000)] = total
    return sorted(out.items())


def fetch_etf_flow_history(
    symbol: str, *, session: requests.Session | None = None
) -> EtfFlowSeries:
    """Fetch the full daily ETF net-flow history for ``symbol`` from Farside.

    Args:
        symbol: ``BTCUSDT`` or ``ETHUSDT`` (the assets with US spot ETFs).
        session: Optional ``requests.Session`` to reuse a connection pool.

    Returns:
        An ``EtfFlowSeries`` sorted ascending.

    Raises:
        ValueError: If ``symbol`` has no known ETF-flow source.
        requests.HTTPError: If the endpoint returns a non-200 status.
    """
    url = _ASSET_URLS.get(symbol)
    if url is None:
        raise ValueError(f"no ETF-flow source for symbol {symbol}")
    sess = session or requests.Session()
    resp = sess.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    pairs = _parse_farside_table(resp.text)
    if not pairs:
        raise ValueError(f"no ETF-flow rows parsed for {symbol} from {url}")

    series = EtfFlowSeries(
        symbol=symbol,
        dates_ms=tuple(d for d, _ in pairs),
        flows=tuple(f for _, f in pairs),
        covered_start_ms=pairs[0][0],
        covered_end_ms=pairs[-1][0],
    )
    logger.info(
        "etf_flow_fetched",
        symbol=symbol,
        days=len(series),
        start=datetime.fromtimestamp(pairs[0][0] / 1000, tz=timezone.utc).date().isoformat(),
        end=datetime.fromtimestamp(pairs[-1][0] / 1000, tz=timezone.utc).date().isoformat(),
    )
    return series


def _write_cache(series: EtfFlowSeries) -> None:
    """Persist an ``EtfFlowSeries`` to its per-symbol JSON cache."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "symbol": series.symbol,
        "covered_start_ms": series.covered_start_ms,
        "covered_end_ms": series.covered_end_ms,
        "dates_ms": list(series.dates_ms),
        "flows": list(series.flows),
    }
    _cache_path(series.symbol).write_text(json.dumps(payload), encoding="utf-8")


def load_cached(symbol: str) -> EtfFlowSeries | None:
    """Load ``symbol``'s ETF-flow history from disk cache (no network).

    Used by backtest workers and generators, which must never hit the network
    (the parent pre-fetches). Returns None if no cache exists.

    Args:
        symbol: Trading pair.

    Returns:
        The cached ``EtfFlowSeries``, or None if absent.
    """
    path = _cache_path(symbol)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return EtfFlowSeries(
        symbol=data["symbol"],
        dates_ms=tuple(int(d) for d in data["dates_ms"]),
        flows=tuple(float(f) for f in data["flows"]),
        covered_start_ms=int(data["covered_start_ms"]),
        covered_end_ms=int(data["covered_end_ms"]),
    )


def load_or_fetch(
    symbol: str,
    end: datetime,
    *,
    use_cache: bool = True,
    session: requests.Session | None = None,
) -> EtfFlowSeries:
    """Return cached ETF flows if they cover through ``end``, else fetch + cache.

    Intended to run in the PARENT process before backtest workers spawn. Farside
    publishes the full history on each request, so a single fetch backfills
    everything; the cache is reused while it already extends to ``end``.

    Args:
        symbol: ``BTCUSDT`` or ``ETHUSDT``.
        end: Timezone-aware UTC instant the cache must cover up to.
        use_cache: If True, reuse a cache already covering ``end``.
        session: Optional ``requests.Session``.

    Returns:
        An ``EtfFlowSeries`` covering at least through ``end``.
    """
    if use_cache:
        cached = load_cached(symbol)
        if cached is not None and cached.covered_end_ms >= int(end.timestamp() * 1000) - _DAY_MS:
            logger.info("etf_flow_cache_hit", symbol=symbol, days=len(cached))
            return cached

    series = fetch_etf_flow_history(symbol, session=session)
    if use_cache:
        _write_cache(series)
        logger.info("etf_flow_cache_write", symbol=symbol, days=len(series))
    return series
