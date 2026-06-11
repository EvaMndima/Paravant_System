"""Forward Binance liquidation collector -- a long-running DATA process.

Connects to the public Binance USD-M futures liquidation websocket
(``!forceOrder@arr``), de-duplicates events, buffers them, and flushes to the
append-only JSONL store in ``research.data.liquidations``. It starts the data
clock for the H-2026-06-004 / H-2026-06-009 liquidation hypotheses, whose builds
passed Stage-1 and were blocked ONLY on liquidation-history accessibility
(``docs/research/NEGATIVE_SPACE_MAP.md``).

THIS IS A DATA PROCESS ONLY. It places NO orders, imports NO execution code, and
does not read or touch ``LIVE_TRADING_ENABLED`` (which stays OFF). Its sole side
effect is appending JSONL fragments under ``research/data/liquidations/``.

RELIABILITY. Auto-reconnect with exponential backoff on any websocket error; an
in-memory bounded dedup set drops events re-delivered across a reconnect; the
buffer is flushed on (a) reaching ``flush_max_events``, (b) every
``flush_interval_s`` of stream silence, (c) any disconnect, and (d) shutdown --
so a crash loses at most one flush interval of buffered events.

HOST / GEO NOTE. The Binance market-data websocket is rejected from geo-blocked
regions (the DEC-2026-06-04-003 root cause). This collector must run on an
always-on, non-geo-blocked host. Per operator decision (DEC-2026-06-04-021) the
deploy target is Railway, gated on the Railway region geo-block being fixed; the
code is host-agnostic and runs anywhere with an outbound websocket to Binance.

One-way dependency: research/ may import src/, never the reverse (PRD Section 5.2).
The ``websockets`` dependency is imported lazily in the default factory so the
causal accessor module stays import-light for generators.

Decision: DEC-2026-06-04-021 -- forward liquidation data channel + collector.
"""
from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Any

from research.data.liquidations import (
    FORCE_ORDER_STREAM_URL,
    LiquidationEvent,
    LiquidationStore,
    parse_force_order,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)

# A websocket connection exposes an async ``recv() -> str``. The factory returns
# an async context manager yielding such a connection. Both (and ``sleep``) are
# injectable so the reconnect/backoff/flush logic is unit-testable without a real
# socket.
WsFactory = Callable[[str], AbstractAsyncContextManager[Any]]
SleepFn = Callable[[float], Awaitable[None]]


def _default_ws_factory(url: str) -> AbstractAsyncContextManager[Any]:
    """Return the real Binance websocket connection context manager.

    Imports ``websockets`` lazily so importing this module (or the accessor it
    re-exports) does not require the websocket library to be installed.

    Args:
        url: The websocket URL to connect to.

    Returns:
        An async context manager yielding a connection with ``async recv()``.
    """
    import websockets  # local import: only the collector needs the WS library

    # ping_interval keeps the connection warm; on any drop the run loop reconnects.
    return websockets.connect(url, ping_interval=20, ping_timeout=20)


class LiquidationCollector:
    """Long-running collector that persists Binance liquidation events.

    Owns the in-memory buffer + dedup window and the reconnect loop. All I/O
    boundaries (websocket, sleep, store) are injectable for testing.
    """

    def __init__(
        self,
        *,
        url: str = FORCE_ORDER_STREAM_URL,
        store: LiquidationStore | None = None,
        flush_max_events: int = 200,
        flush_interval_s: float = 30.0,
        backoff_initial_s: float = 1.0,
        backoff_max_s: float = 60.0,
        backoff_factor: float = 2.0,
        backoff_reset_after_s: float = 60.0,
        dedup_memory: int = 10_000,
        ws_factory: WsFactory | None = None,
        sleep: SleepFn | None = None,
    ) -> None:
        """Initialise the collector.

        Args:
            url: Binance liquidation websocket URL.
            store: Parquet store sink; defaults to the package store dir.
            flush_max_events: Flush when the buffer reaches this many events.
            flush_interval_s: Flush after this many seconds of stream silence;
                also the per-recv timeout that drives the periodic flush tick.
            backoff_initial_s: First reconnect delay after a disconnect.
            backoff_max_s: Cap on the exponential reconnect delay.
            backoff_factor: Multiplier applied to the delay after each failure.
            backoff_reset_after_s: A session that stayed connected at least this
                long is treated as healthy and resets the backoff to its initial
                value; shorter sessions (flaps) keep escalating the delay.
            dedup_memory: Number of recent event keys kept to drop duplicates.
            ws_factory: Factory returning the websocket context manager
                (injectable for tests); defaults to the real Binance connection.
            sleep: Awaitable sleep (injectable for tests); defaults to
                ``asyncio.sleep``.
        """
        self._url = url
        self._store = store or LiquidationStore()
        self._flush_max_events = flush_max_events
        self._flush_interval_s = flush_interval_s
        self._backoff_initial_s = backoff_initial_s
        self._backoff_max_s = backoff_max_s
        self._backoff_factor = backoff_factor
        self._backoff_reset_after_s = backoff_reset_after_s
        self._dedup_memory = dedup_memory
        self._ws_factory = ws_factory or _default_ws_factory
        self._sleep = sleep or asyncio.sleep

        self._buffer: list[LiquidationEvent] = []
        self._recent_keys: set[tuple[str, int, str, float, float]] = set()
        self._recent_order: deque[tuple[str, int, str, float, float]] = deque()
        self._stop = False

        # Lifetime counters (structured-log diagnostics; not persisted).
        self._received = 0
        self._duplicates = 0
        self._malformed = 0

    def stop(self) -> None:
        """Request a graceful shutdown after the current recv/flush."""
        self._stop = True

    @property
    def buffer_size(self) -> int:
        """Return the number of events currently buffered (un-flushed)."""
        return len(self._buffer)

    @property
    def stats(self) -> dict[str, int]:
        """Return lifetime counters (received / duplicates / malformed / buffered)."""
        return {
            "received": self._received,
            "duplicates": self._duplicates,
            "malformed": self._malformed,
            "buffered": len(self._buffer),
        }

    def on_message(self, raw: str) -> LiquidationEvent | None:
        """Parse, de-duplicate, and buffer one raw websocket frame.

        Args:
            raw: The raw text frame from the websocket.

        Returns:
            The buffered ``LiquidationEvent``, or ``None`` if the frame was
            malformed, not a liquidation, or a duplicate.
        """
        try:
            payload: dict[str, Any] = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            self._malformed += 1
            return None

        event = parse_force_order(payload)
        if event is None:
            self._malformed += 1
            return None

        key = event.dedup_key()
        if key in self._recent_keys:
            self._duplicates += 1
            return None

        self._recent_keys.add(key)
        self._recent_order.append(key)
        if len(self._recent_order) > self._dedup_memory:
            evicted = self._recent_order.popleft()
            self._recent_keys.discard(evicted)

        self._buffer.append(event)
        self._received += 1
        return event

    def flush(self) -> Path | None:
        """Write the buffered events to one immutable fragment and clear it.

        Returns:
            The fragment path written, or ``None`` if the buffer was empty.
        """
        if not self._buffer:
            return None
        batch = self._buffer
        self._buffer = []
        return self._store.write_batch(batch)

    async def _consume(self, ws: Any) -> None:
        """Read frames until disconnect/stop, flushing on size and on silence.

        Args:
            ws: A connected websocket exposing ``async recv() -> str``.
        """
        while not self._stop:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=self._flush_interval_s)
            except asyncio.TimeoutError:
                # Stream silence: flush any buffered burst so it cannot sit unsaved.
                self.flush()
                continue
            self.on_message(raw)
            if len(self._buffer) >= self._flush_max_events:
                self.flush()

    async def run(self) -> None:
        """Run the reconnect loop until ``stop()`` is requested.

        Reconnects with exponential backoff on any websocket error and always
        flushes the buffer when a connection ends (disconnect or shutdown) so no
        buffered events are lost. The backoff resets to its initial value only
        after a connection that stayed healthy at least ``backoff_reset_after_s``;
        a connect-then-immediately-drop flap keeps escalating the delay (so the
        collector never hammers a misbehaving endpoint).
        """
        backoff = self._backoff_initial_s
        while not self._stop:
            session_start = time.monotonic()
            try:
                async with self._ws_factory(self._url) as ws:
                    logger.info("liquidation_ws_connected", url=self._url)
                    await self._consume(ws)
            except asyncio.CancelledError:
                self.flush()
                raise
            except Exception as exc:  # noqa: BLE001 - reconnect on ANY ws error
                logger.warning(
                    "liquidation_ws_disconnected",
                    error=str(exc),
                    backoff_s=backoff,
                    **self.stats,
                )
            finally:
                # Never carry a buffer across a reconnect.
                self.flush()

            if self._stop:
                break

            # A long-lived session was healthy: reconnect fast. A flap escalates.
            if time.monotonic() - session_start >= self._backoff_reset_after_s:
                backoff = self._backoff_initial_s
            await self._sleep(backoff)
            backoff = min(backoff * self._backoff_factor, self._backoff_max_s)

        self.flush()
        logger.info("liquidation_collector_stopped", **self.stats)
