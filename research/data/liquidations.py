"""Binance USDT-M futures forced-liquidation event channel for the research layer.

Forward-collected, causal-BY-CONSTRUCTION liquidation history. The source is the
FREE, public, no-auth Binance USD-M futures liquidation websocket
(``!forceOrder@arr``) -- the largest liquidation venue in crypto, and the one
reachable free signal behind the H-2026-06-004 / H-2026-06-009 data walls (both
Stage-1 PASS, both blocked only on liquidation-history accessibility; see
``docs/research/NEGATIVE_SPACE_MAP.md`` and ``research/hypotheses/ledger.yaml``).

STREAM THROTTLE (an honest limit, not a bug). Binance pushes at most ONE
liquidation order per symbol per ~1000ms on this stream -- a representative
SNAPSHOT, not the full tick-by-tick volume. This channel persists every event the
stream DELIVERS; it does NOT reconstruct full liquidation volume. Per-second
notional during an intense same-symbol cascade is therefore UNDERCOUNTED. The
H-004 / H-009 cascade trigger is windowed + percentile-based (the H-006 lesson),
which tolerates a proportional undercount; full-volume history still requires a
paid source (Coinglass, DEC-2026-06-04-005). Do not treat ``notional`` as exact
market-wide liquidation volume.

CAUSALITY (leak-free by construction). A forward collector only ever records
events as they arrive, so a future event is structurally impossible to observe.
``liquidations_in_window(t0, t1)`` still enforces ``trade_time <= now`` defensively,
mirroring the as-of discipline of ``research/data/funding_rates.py:FundingSeries.rate_at``.
The causal timestamp is the forced-trade time (Binance ``o.T``), not the push time.

SIDE SEMANTICS (a documented footgun). Binance ``o.S`` is the *order* side, which
is the OPPOSITE of the position being liquidated. ``S == "SELL"`` means a LONG was
force-liquidated (the engine market-SELLS to close it -- the "long flush" H-004
buys into); ``S == "BUY"`` means a SHORT was force-liquidated. This channel stores
the raw ``order_side`` AND a derived ``liquidated_side`` so a downstream generator
cannot invert the direction.

STORE. Append-only JSONL (newline-delimited JSON) fragments under
``research/data/liquidations/<YYYY-MM-DD>/``, one immutable file per flush. The
durable-streaming idiom is to flush each buffer to a NEW file rather than rewrite
one growing file; a crash loses at most one flush interval of buffered events.
JSONL needs no extra dependency (stdlib ``json``), mirrors the funding cache, and
stays human-inspectable. This store is fully namespaced and touches NO production /
Neon table (read-only Neon discipline is unchanged).

One-way dependency: research/ may import src/, never the reverse (PRD Section 5.2).
This module imports only the standard library and src.utils.logging.

Decision: DEC-2026-06-04-021 -- forward liquidation data channel + collector.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Binance USD-M futures market-data websocket host (raw single-stream form). The
# aggregated all-market liquidation stream pushes one forced order per message as
# it happens. No auth, no API key -- public market data.
FORCE_ORDER_STREAM_URL = "wss://fstream.binance.com/ws/!forceOrder@arr"

# Append-only JSONL store root (NOT committed; transient like the regime_dsr /
# funding caches). Each flush writes one immutable fragment under a UTC-date dir.
_STORE_DIR = Path("research/data/liquidations")

# Flush dates can lag the trade time of buffered events by a few seconds across a
# UTC-midnight boundary, so a read over-scans neighbouring date dirs by this much
# and then filters precisely by trade_time_ms.
_READ_DATE_PAD = timedelta(days=1)


@dataclass(frozen=True)
class LiquidationEvent:
    """A single Binance forced-liquidation event.

    Attributes:
        symbol: Trading pair (e.g. ``BTCUSDT``).
        trade_time_ms: Forced-trade time in epoch milliseconds (Binance ``o.T``).
            This is the CAUSAL timestamp -- the instant the liquidation executed.
        event_time_ms: Stream push time in epoch milliseconds (Binance ``E``).
        order_side: Raw liquidation-ORDER side, ``"BUY"`` or ``"SELL"``.
        liquidated_side: Side of the POSITION liquidated -- ``"LONG"`` when the
            order side is ``"SELL"`` (forced selling), ``"SHORT"`` when ``"BUY"``.
        price: Liquidation fill price (average price ``o.ap`` if positive, else the
            order price ``o.p``).
        quantity: Liquidated base-asset quantity (Binance ``o.q``).
        notional: ``price * quantity`` (quote-currency size of the liquidation).
    """

    symbol: str
    trade_time_ms: int
    event_time_ms: int
    order_side: str
    liquidated_side: str
    price: float
    quantity: float
    notional: float

    def dedup_key(self) -> tuple[str, int, str, float, float]:
        """Return the natural de-duplication key.

        The forceOrder stream carries no order id, so identity is the conjunction
        of symbol, forced-trade time, order side, price and quantity. A reconnect
        can re-deliver the same event; this key drops the duplicate.

        Returns:
            ``(symbol, trade_time_ms, order_side, price, quantity)``.
        """
        return (self.symbol, self.trade_time_ms, self.order_side, self.price, self.quantity)

    def trade_time(self) -> datetime:
        """Return the forced-trade time as a timezone-aware UTC datetime."""
        return datetime.fromtimestamp(self.trade_time_ms / 1000.0, tz=timezone.utc)


def _liquidated_side(order_side: str) -> str:
    """Map a raw liquidation-order side to the liquidated POSITION side.

    Args:
        order_side: ``"BUY"`` or ``"SELL"`` (Binance ``o.S``).

    Returns:
        ``"LONG"`` for a ``"SELL"`` order (a long was force-sold), ``"SHORT"`` for
        a ``"BUY"`` order (a short was force-bought).

    Raises:
        ValueError: If ``order_side`` is neither ``"BUY"`` nor ``"SELL"``.
    """
    side = order_side.upper()
    if side == "SELL":
        return "LONG"
    if side == "BUY":
        return "SHORT"
    raise ValueError(f"unexpected liquidation order side: {order_side!r}")


def parse_force_order(payload: dict[str, Any]) -> LiquidationEvent | None:
    """Parse one Binance forceOrder websocket message into a LiquidationEvent.

    Accepts both the raw single-stream shape ``{"e": "forceOrder", "E": ...,
    "o": {...}}`` and the combined-stream wrapper ``{"stream": ..., "data": {...}}``.
    Returns ``None`` (rather than raising) for any malformed or non-liquidation
    message, so the collector can skip-and-continue on unexpected frames.

    Args:
        payload: The decoded JSON object from one websocket frame.

    Returns:
        A ``LiquidationEvent``, or ``None`` if the frame is not a well-formed
        liquidation (wrong event type, missing fields, or non-positive size).
    """
    try:
        # Unwrap the combined-stream envelope if present.
        if "data" in payload and "stream" in payload:
            payload = payload["data"]
        if payload.get("e") != "forceOrder":
            return None
        order = payload["o"]

        symbol = str(order["s"])
        order_side = str(order["S"]).upper()
        trade_time_ms = int(order["T"])
        event_time_ms = int(payload["E"])
        quantity = float(order["q"])

        # Prefer the average fill price; fall back to the order price when ``ap``
        # has not been populated yet (it can be "0" pre-fill).
        avg_price = float(order.get("ap", 0) or 0)
        price = avg_price if avg_price > 0 else float(order["p"])

        if price <= 0 or quantity <= 0:
            return None

        liquidated_side = _liquidated_side(order_side)
    except (KeyError, TypeError, ValueError):
        # Malformed / unexpected frame: skip it rather than crash the collector.
        return None

    return LiquidationEvent(
        symbol=symbol,
        trade_time_ms=trade_time_ms,
        event_time_ms=event_time_ms,
        order_side=order_side,
        liquidated_side=liquidated_side,
        price=price,
        quantity=quantity,
        notional=price * quantity,
    )


def _to_row(event: LiquidationEvent) -> dict[str, Any]:
    """Convert a LiquidationEvent to a JSON-serialisable row dict."""
    return {
        "trade_time_ms": event.trade_time_ms,
        "event_time_ms": event.event_time_ms,
        "symbol": event.symbol,
        "order_side": event.order_side,
        "liquidated_side": event.liquidated_side,
        "price": event.price,
        "quantity": event.quantity,
        "notional": event.notional,
    }


def _row_to_event(row: dict[str, Any]) -> LiquidationEvent:
    """Reconstruct a LiquidationEvent from a stored row dict."""
    return LiquidationEvent(
        symbol=str(row["symbol"]),
        trade_time_ms=int(row["trade_time_ms"]),
        event_time_ms=int(row["event_time_ms"]),
        order_side=str(row["order_side"]),
        liquidated_side=str(row["liquidated_side"]),
        price=float(row["price"]),
        quantity=float(row["quantity"]),
        notional=float(row["notional"]),
    )


def _to_ms(ts: datetime) -> int:
    """Convert a timezone-aware datetime to epoch milliseconds."""
    if ts.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return int(ts.timestamp() * 1000)


class LiquidationStore:
    """Append-only JSONL store for liquidation events.

    Writes one immutable fragment per flush under ``<root>/<YYYY-MM-DD>/`` and
    reads a time window by unioning the fragments whose flush date overlaps the
    request (padded by one day for midnight skew), then filtering precisely on
    ``trade_time_ms``. The store owns ONLY this directory tree; it never reads or
    writes any production / Neon table.
    """

    def __init__(self, root: Path | str = _STORE_DIR) -> None:
        """Initialise the store rooted at ``root`` (created lazily on write)."""
        self._root = Path(root)

    @property
    def root(self) -> Path:
        """Return the store root directory."""
        return self._root

    def write_batch(
        self,
        events: Sequence[LiquidationEvent],
        *,
        flush_dt: datetime | None = None,
    ) -> list[Path]:
        """Write a batch of events to immutable JSONL fragments, one per date.

        Events are grouped by the UTC date of their own ``trade_time_ms`` and
        one immutable fragment is written per date.

        Partitioning on the event's causal timestamp -- not on wall-clock flush
        time -- is what makes ``read_window`` correct. The reader derives
        candidate date directories from the query window, and that window is
        expressed in trade time. Keying writes on flush time made the two
        clocks disagree whenever a flush crossed a UTC midnight or replayed
        historical events, and the affected events became silently unreadable:
        written to disk, absent from every query. ``_READ_DATE_PAD`` masked the
        midnight case and nothing covered the general one.

        Args:
            events: Events to persist; an empty sequence is a no-op.
            flush_dt: Timezone-aware UTC flush time. Used only in the fragment
                *filename*, to order and distinguish fragments written for the
                same date. It no longer selects the partition. Defaults to
                ``datetime.now(timezone.utc)``.

        Returns:
            Paths of the written fragments, one per distinct trade date, sorted
            by date. Empty list if ``events`` was empty.

        Raises:
            ValueError: If ``flush_dt`` is provided but not timezone-aware.
        """
        if not events:
            return []
        if flush_dt is None:
            flush_dt = datetime.now(timezone.utc)
        elif flush_dt.tzinfo is None:
            raise ValueError("flush_dt must be timezone-aware")

        by_trade_date: dict[str, list[LiquidationEvent]] = {}
        for event in events:
            key = event.trade_time().strftime("%Y-%m-%d")
            by_trade_date.setdefault(key, []).append(event)

        written: list[Path] = []
        for date_key in sorted(by_trade_date):
            date_dir = self._root / date_key
            date_dir.mkdir(parents=True, exist_ok=True)
            fragment = date_dir / f"part-{_to_ms(flush_dt)}-{uuid4().hex[:8]}.jsonl"
            payload = "".join(
                json.dumps(_to_row(e)) + "\n" for e in by_trade_date[date_key]
            )
            fragment.write_text(payload, encoding="utf-8")
            written.append(fragment)

        logger.info(
            "liquidations_flushed",
            fragments=len(written),
            events=len(events),
            trade_dates=sorted(by_trade_date),
        )
        return written

    def _candidate_date_dirs(self, t0: datetime, t1: datetime) -> Iterable[Path]:
        """Yield existing date dirs overlapping ``[t0, t1]`` padded by one day."""
        day = (t0 - _READ_DATE_PAD).date()
        last = (t1 + _READ_DATE_PAD).date()
        while day <= last:
            candidate = self._root / day.strftime("%Y-%m-%d")
            if candidate.is_dir():
                yield candidate
            day += timedelta(days=1)

    def read_window(self, t0: datetime, t1: datetime) -> list[LiquidationEvent]:
        """Read all stored events with ``t0 <= trade_time <= t1``.

        Reads every JSONL fragment in the overlapping date dirs, filters by
        ``trade_time_ms``, de-duplicates (a reconnect or overlapping fragment can
        re-store an event), and returns them sorted ascending by trade time.

        Args:
            t0: Timezone-aware inclusive UTC window start.
            t1: Timezone-aware inclusive UTC window end.

        Returns:
            De-duplicated events sorted ascending by ``(trade_time_ms, symbol)``.

        Raises:
            ValueError: If ``t0``/``t1`` are naive or ``t0 > t1``.
        """
        if t0.tzinfo is None or t1.tzinfo is None:
            raise ValueError("t0 and t1 must be timezone-aware")
        if t0 > t1:
            raise ValueError(f"t0 {t0} must be <= t1 {t1}")

        t0_ms, t1_ms = _to_ms(t0), _to_ms(t1)
        seen: dict[tuple[str, int, str, float, float], LiquidationEvent] = {}
        for date_dir in self._candidate_date_dirs(t0, t1):
            for fragment in sorted(date_dir.glob("part-*.jsonl")):
                for line in fragment.read_text(encoding="utf-8").splitlines():
                    if not line:
                        continue
                    row = json.loads(line)
                    if t0_ms <= int(row["trade_time_ms"]) <= t1_ms:
                        event = _row_to_event(row)
                        seen[event.dedup_key()] = event

        return sorted(seen.values(), key=lambda e: (e.trade_time_ms, e.symbol))


def liquidations_in_window(
    t0: datetime,
    t1: datetime,
    *,
    now: datetime | None = None,
    store: LiquidationStore | None = None,
) -> list[LiquidationEvent]:
    """Return liquidations with ``t0 <= trade_time <= min(t1, now)`` (causal).

    The as-of accessor mirroring ``funding_rates.FundingSeries.rate_at``: it never
    returns an event whose forced-trade time is after ``now``. Because the
    collector only records events as they arrive, this clamp is defensive symmetry
    -- a future event cannot exist in the store -- but it guarantees the read is
    causal even if a test or caller back-dates the store.

    Args:
        t0: Timezone-aware inclusive UTC window start.
        t1: Timezone-aware inclusive UTC window end.
        now: Timezone-aware UTC "as-of" instant; events after it are excluded.
            Defaults to ``datetime.now(timezone.utc)``.
        store: Store to read from; defaults to one rooted at the package store dir.

    Returns:
        De-duplicated events sorted ascending by trade time, none after ``now``.

    Raises:
        ValueError: If ``t0``/``t1``/``now`` are naive.
    """
    if t0.tzinfo is None or t1.tzinfo is None:
        raise ValueError("t0 and t1 must be timezone-aware")
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    upper = min(t1, now)
    if t0 > upper:
        return []
    store = store or LiquidationStore()
    return store.read_window(t0, upper)
