"""Tests for the forward liquidation data channel + collector.

Coverage focus, in order of leakage/data-integrity importance:
  1. parse_force_order -- the wire-format parser incl. the SELL->LONG footgun.
  2. The causal accessor liquidations_in_window -- never returns a future event.
  3. LiquidationStore -- JSONL round-trip, window filter, cross-fragment dedup.
  4. LiquidationCollector -- dedup, buffered flush, reconnect/backoff (mocked WS),
     flush-on-silence, graceful stop.

All tests are unit-pure: no real network, no real Binance websocket. The async
collector is exercised via injected ws_factory + sleep, so reconnect/backoff and
flushing are deterministic.
"""
from __future__ import annotations

import asyncio
import json
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from research.data.liquidation_collector import LiquidationCollector
from research.data.liquidations import (
    LiquidationEvent,
    LiquidationStore,
    liquidations_in_window,
    parse_force_order,
)

_BASE = datetime(2026, 6, 11, 12, 0, 0, tzinfo=timezone.utc)


def _ms(dt: datetime) -> int:
    """Epoch milliseconds for a tz-aware datetime."""
    return int(dt.timestamp() * 1000)


def _force_order_msg(
    *,
    symbol: str = "BTCUSDT",
    side: str = "SELL",
    t_ms: int | None = None,
    e_ms: int | None = None,
    q: str = "1.0",
    p: str = "100.0",
    ap: str | None = None,
) -> str:
    """Build a raw Binance forceOrder websocket frame (JSON string)."""
    t_ms = t_ms if t_ms is not None else _ms(_BASE)
    e_ms = e_ms if e_ms is not None else t_ms
    order = {
        "s": symbol,
        "S": side,
        "o": "LIMIT",
        "f": "IOC",
        "q": q,
        "p": p,
        "ap": ap if ap is not None else p,
        "X": "FILLED",
        "l": q,
        "z": q,
        "T": t_ms,
    }
    return json.dumps({"e": "forceOrder", "E": e_ms, "o": order})


def _event(
    *,
    symbol: str = "BTCUSDT",
    side: str = "SELL",
    t_ms: int | None = None,
    price: float = 100.0,
    qty: float = 1.0,
) -> LiquidationEvent:
    """Build a LiquidationEvent directly (store/accessor tests)."""
    t_ms = t_ms if t_ms is not None else _ms(_BASE)
    return LiquidationEvent(
        symbol=symbol,
        trade_time_ms=t_ms,
        event_time_ms=t_ms,
        order_side=side,
        liquidated_side="LONG" if side == "SELL" else "SHORT",
        price=price,
        quantity=qty,
        notional=price * qty,
    )


# ---------------------------------------------------------------------------
# parse_force_order
# ---------------------------------------------------------------------------


def test_parse_sell_order_is_a_long_flush() -> None:
    """A SELL liquidation order means a LONG position was force-sold."""
    event = parse_force_order(json.loads(_force_order_msg(side="SELL")))
    assert event is not None
    assert event.order_side == "SELL"
    assert event.liquidated_side == "LONG"


def test_parse_buy_order_is_a_short_liquidation() -> None:
    """A BUY liquidation order means a SHORT position was force-bought."""
    event = parse_force_order(json.loads(_force_order_msg(side="BUY")))
    assert event is not None
    assert event.order_side == "BUY"
    assert event.liquidated_side == "SHORT"


def test_parse_unwraps_combined_stream_envelope() -> None:
    """The {"stream": ..., "data": {...}} combined-stream shape is unwrapped."""
    inner = json.loads(_force_order_msg(symbol="ETHUSDT"))
    wrapped = {"stream": "!forceOrder@arr", "data": inner}
    event = parse_force_order(wrapped)
    assert event is not None
    assert event.symbol == "ETHUSDT"


def test_parse_notional_is_price_times_quantity() -> None:
    """notional = price * quantity."""
    event = parse_force_order(json.loads(_force_order_msg(p="9910.0", q="0.5")))
    assert event is not None
    assert event.price == 9910.0
    assert event.quantity == 0.5
    assert event.notional == pytest.approx(9910.0 * 0.5)


def test_parse_prefers_average_price_falls_back_to_order_price() -> None:
    """ap is used when positive; p is the fallback when ap is '0'."""
    with_ap = parse_force_order(json.loads(_force_order_msg(p="100.0", ap="101.5")))
    assert with_ap is not None and with_ap.price == 101.5

    zero_ap = parse_force_order(json.loads(_force_order_msg(p="100.0", ap="0")))
    assert zero_ap is not None and zero_ap.price == 100.0


def test_parse_non_liquidation_event_returns_none() -> None:
    """A non-forceOrder event type is ignored (returns None)."""
    assert parse_force_order({"e": "aggTrade", "E": 1, "o": {}}) is None


def test_parse_malformed_returns_none_not_raises() -> None:
    """Missing fields / bad numbers return None rather than raising."""
    assert parse_force_order({"e": "forceOrder"}) is None  # no "o"
    bad_number = json.loads(_force_order_msg())
    bad_number["o"]["q"] = "not-a-number"
    assert parse_force_order(bad_number) is None


def test_parse_non_positive_size_returns_none() -> None:
    """Zero/negative price or quantity is dropped."""
    assert parse_force_order(json.loads(_force_order_msg(q="0"))) is None
    assert parse_force_order(json.loads(_force_order_msg(p="0", ap="0"))) is None


def test_parse_unexpected_side_returns_none() -> None:
    """An out-of-domain order side (not BUY/SELL) is dropped, not crashed."""
    assert parse_force_order(json.loads(_force_order_msg(side="HOLD"))) is None


def test_event_trade_time_is_utc() -> None:
    """trade_time() returns the tz-aware UTC forced-trade instant."""
    event = _event(t_ms=_ms(_BASE))
    assert event.trade_time() == _BASE


# ---------------------------------------------------------------------------
# LiquidationStore
# ---------------------------------------------------------------------------


def test_store_write_read_roundtrip(tmp_path: Any) -> None:
    """Events written to a fragment read back identically."""
    store = LiquidationStore(tmp_path)
    events = [
        _event(symbol="BTCUSDT", t_ms=_ms(_BASE)),
        _event(symbol="ETHUSDT", t_ms=_ms(_BASE + timedelta(seconds=1))),
    ]
    store.write_batch(events, flush_dt=_BASE)
    got = store.read_window(_BASE - timedelta(hours=1), _BASE + timedelta(hours=1))
    assert got == sorted(events, key=lambda e: (e.trade_time_ms, e.symbol))


def test_store_empty_batch_is_noop(tmp_path: Any) -> None:
    """Writing an empty batch returns no fragments and creates none."""
    store = LiquidationStore(tmp_path)
    assert store.write_batch([], flush_dt=_BASE) == []


def test_store_read_window_filters_by_trade_time(tmp_path: Any) -> None:
    """Events outside [t0, t1] (by trade time) are excluded."""
    store = LiquidationStore(tmp_path)
    inside = _event(t_ms=_ms(_BASE))
    before = _event(t_ms=_ms(_BASE - timedelta(hours=3)), symbol="ETHUSDT")
    after = _event(t_ms=_ms(_BASE + timedelta(hours=3)), symbol="SOLUSDT")
    store.write_batch([inside, before, after], flush_dt=_BASE)

    got = store.read_window(_BASE - timedelta(minutes=30), _BASE + timedelta(minutes=30))
    assert got == [inside]


def test_store_read_window_dedups_across_fragments(tmp_path: Any) -> None:
    """The same event written to two fragments is returned once."""
    store = LiquidationStore(tmp_path)
    event = _event(t_ms=_ms(_BASE))
    store.write_batch([event], flush_dt=_BASE)
    store.write_batch([event], flush_dt=_BASE + timedelta(seconds=5))  # re-delivered
    got = store.read_window(_BASE - timedelta(hours=1), _BASE + timedelta(hours=1))
    assert got == [event]


def test_store_read_window_spans_midnight_partition_padding(tmp_path: Any) -> None:
    """An event flushed after midnight is filed under its own trade date."""
    store = LiquidationStore(tmp_path)
    # Trade time at 23:59:59 on day D; flushed at 00:00:02 on day D+1.
    trade_dt = datetime(2026, 6, 11, 23, 59, 59, tzinfo=timezone.utc)
    flush_dt = datetime(2026, 6, 12, 0, 0, 2, tzinfo=timezone.utc)
    event = _event(t_ms=_ms(trade_dt))
    written = store.write_batch([event], flush_dt=flush_dt)

    # Partitioned by trade date, not flush date. This used to land under
    # 2026-06-12 and be readable only because _READ_DATE_PAD widened the scan.
    assert [p.parent.name for p in written] == ["2026-06-11"]

    got = store.read_window(
        trade_dt - timedelta(minutes=5), trade_dt + timedelta(minutes=5)
    )
    assert got == [event]


def test_store_partitions_by_trade_date_not_flush_date(tmp_path: Any) -> None:
    """An event flushed long after it occurred is still readable.

    Regression test. write_batch used to choose the date-partition directory
    from the wall-clock flush time while read_window derives candidate
    directories from the query window, which is in trade time. Any flush more
    than _READ_DATE_PAD from the event's own date wrote the event to disk and
    then made it invisible to every query -- silent data loss in a store whose
    entire purpose is accruing a causal history over months.
    """
    store = LiquidationStore(tmp_path)
    trade_dt = datetime(2026, 6, 11, 12, 0, 0, tzinfo=timezone.utc)
    flush_dt = trade_dt + timedelta(days=62)  # replay / late flush
    event = _event(t_ms=_ms(trade_dt))

    written = store.write_batch([event], flush_dt=flush_dt)
    assert [p.parent.name for p in written] == ["2026-06-11"]

    got = store.read_window(
        trade_dt - timedelta(hours=1), trade_dt + timedelta(hours=1)
    )
    assert got == [event]


def test_store_batch_spanning_dates_splits_fragments(tmp_path: Any) -> None:
    """A buffer straddling UTC midnight writes one fragment per trade date."""
    store = LiquidationStore(tmp_path)
    before = _event(
        t_ms=_ms(datetime(2026, 6, 11, 23, 59, 50, tzinfo=timezone.utc)),
    )
    after = _event(
        t_ms=_ms(datetime(2026, 6, 12, 0, 0, 10, tzinfo=timezone.utc)),
        symbol="ETHUSDT",
    )

    written = store.write_batch([before, after], flush_dt=_BASE)
    assert sorted(p.parent.name for p in written) == ["2026-06-11", "2026-06-12"]

    got = store.read_window(
        datetime(2026, 6, 11, 23, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 6, 12, 1, 0, 0, tzinfo=timezone.utc),
    )
    assert got == sorted([before, after], key=lambda e: (e.trade_time_ms, e.symbol))


def test_store_read_window_rejects_naive_datetime(tmp_path: Any) -> None:
    """Naive datetimes are rejected (UTC discipline)."""
    store = LiquidationStore(tmp_path)
    with pytest.raises(ValueError):
        store.read_window(datetime(2026, 6, 11), _BASE)  # noqa: DTZ001


def test_store_read_window_rejects_inverted_range(tmp_path: Any) -> None:
    """t0 > t1 is a programming error."""
    store = LiquidationStore(tmp_path)
    with pytest.raises(ValueError):
        store.read_window(_BASE, _BASE - timedelta(hours=1))


# ---------------------------------------------------------------------------
# liquidations_in_window -- the causal accessor
# ---------------------------------------------------------------------------


def test_accessor_excludes_events_after_now(tmp_path: Any) -> None:
    """An event after the as-of 'now' is never returned (causal clamp)."""
    store = LiquidationStore(tmp_path)
    past = _event(t_ms=_ms(_BASE - timedelta(hours=1)))
    future = _event(t_ms=_ms(_BASE + timedelta(hours=1)), symbol="ETHUSDT")
    store.write_batch([past, future], flush_dt=_BASE + timedelta(hours=2))

    got = liquidations_in_window(
        _BASE - timedelta(days=1),
        _BASE + timedelta(days=1),
        now=_BASE,  # as-of NOW: the future event must be excluded
        store=store,
    )
    assert got == [past]


def test_accessor_t1_clamped_to_now(tmp_path: Any) -> None:
    """When t1 is past now, the upper bound is now (no peeking ahead)."""
    store = LiquidationStore(tmp_path)
    at_now = _event(t_ms=_ms(_BASE))
    later = _event(t_ms=_ms(_BASE + timedelta(minutes=30)), symbol="ETHUSDT")
    store.write_batch([at_now, later], flush_dt=_BASE + timedelta(hours=1))

    got = liquidations_in_window(
        _BASE - timedelta(hours=1),
        _BASE + timedelta(hours=1),
        now=_BASE,
        store=store,
    )
    assert got == [at_now]


def test_accessor_rejects_naive_datetimes(tmp_path: Any) -> None:
    """Naive t0/t1/now are rejected."""
    store = LiquidationStore(tmp_path)
    with pytest.raises(ValueError):
        liquidations_in_window(datetime(2026, 6, 11), _BASE, store=store)  # noqa: DTZ001
    with pytest.raises(ValueError):
        liquidations_in_window(_BASE, _BASE, now=datetime(2026, 6, 11), store=store)  # noqa: DTZ001


def test_accessor_empty_when_t0_after_now(tmp_path: Any) -> None:
    """A window starting after now yields nothing without touching the store."""
    store = LiquidationStore(tmp_path)
    got = liquidations_in_window(
        _BASE + timedelta(days=1),
        _BASE + timedelta(days=2),
        now=_BASE,
        store=store,
    )
    assert got == []


# ---------------------------------------------------------------------------
# LiquidationCollector -- buffering + dedup
# ---------------------------------------------------------------------------


def test_collector_on_message_buffers_event(tmp_path: Any) -> None:
    """A valid frame is parsed and buffered; counters update."""
    collector = LiquidationCollector(store=LiquidationStore(tmp_path))
    event = collector.on_message(_force_order_msg())
    assert event is not None
    assert collector.buffer_size == 1
    assert collector.stats["received"] == 1


def test_collector_dedups_repeated_event(tmp_path: Any) -> None:
    """The same liquidation delivered twice is buffered once."""
    collector = LiquidationCollector(store=LiquidationStore(tmp_path))
    raw = _force_order_msg(t_ms=_ms(_BASE))
    assert collector.on_message(raw) is not None
    assert collector.on_message(raw) is None  # duplicate
    assert collector.buffer_size == 1
    assert collector.stats["duplicates"] == 1


def test_collector_counts_malformed_frames(tmp_path: Any) -> None:
    """Non-JSON and non-liquidation frames are counted, not buffered."""
    collector = LiquidationCollector(store=LiquidationStore(tmp_path))
    assert collector.on_message("{not json") is None
    assert collector.on_message(json.dumps({"e": "aggTrade"})) is None
    assert collector.buffer_size == 0
    assert collector.stats["malformed"] == 2


def test_collector_dedup_window_evicts_oldest(tmp_path: Any) -> None:
    """With a tiny dedup memory, an old key is evicted so it can re-buffer."""
    collector = LiquidationCollector(store=LiquidationStore(tmp_path), dedup_memory=1)
    collector.on_message(_force_order_msg(t_ms=1))
    collector.on_message(_force_order_msg(t_ms=2))  # evicts key for t=1
    # t=1 is no longer remembered -> re-buffers instead of dropping as duplicate.
    assert collector.on_message(_force_order_msg(t_ms=1)) is not None
    assert collector.stats["duplicates"] == 0


def test_collector_flush_writes_and_clears(tmp_path: Any) -> None:
    """flush() persists the buffer, clears it, and is readable back."""
    store = LiquidationStore(tmp_path)
    collector = LiquidationCollector(store=store)
    collector.on_message(_force_order_msg(t_ms=_ms(_BASE)))
    written = collector.flush()
    assert len(written) == 1
    assert collector.buffer_size == 0
    got = store.read_window(_BASE - timedelta(hours=1), _BASE + timedelta(hours=1))
    assert len(got) == 1


def test_collector_flush_empty_is_noop(tmp_path: Any) -> None:
    """Flushing an empty buffer writes nothing."""
    collector = LiquidationCollector(store=LiquidationStore(tmp_path))
    assert collector.flush() == []


# ---------------------------------------------------------------------------
# LiquidationCollector -- async run loop (mocked websocket)
# ---------------------------------------------------------------------------


class _ScriptedWs:
    """Async context manager whose recv() yields frames then forces a disconnect.

    After the scripted frames are exhausted, recv() raises ConnectionError to
    simulate a dropped websocket, exercising the reconnect path.
    """

    def __init__(self, frames: list[str]) -> None:
        self._frames = deque(frames)

    async def __aenter__(self) -> "_ScriptedWs":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def recv(self) -> str:
        if self._frames:
            return self._frames.popleft()
        raise ConnectionError("stream closed")


def test_run_reconnects_with_exponential_backoff(tmp_path: Any) -> None:
    """Each disconnect triggers a reconnect with a growing backoff delay."""
    store = LiquidationStore(tmp_path)
    # Anchor on real now so the flush-date partition matches the read window
    # regardless of the calendar date the suite runs on (flush() stamps wall-clock).
    now = datetime.now(timezone.utc)
    n_ms = int(now.timestamp() * 1000)
    # Three connections, each delivering one DISTINCT liquidation then closing.
    conns = [_ScriptedWs([_force_order_msg(t_ms=n_ms + i)]) for i in range(3)]
    factory_calls: list[str] = []
    sleeps: list[float] = []

    collector = LiquidationCollector(
        store=store,
        ws_factory=lambda url: (factory_calls.append(url) or conns.pop(0)),
        sleep=None,  # replaced below so it can also stop the loop
        backoff_initial_s=1.0,
        backoff_factor=2.0,
        backoff_max_s=10.0,
        flush_interval_s=5.0,
    )

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)
        if len(sleeps) >= 3:  # stop after observing three reconnect waits
            collector.stop()

    collector._sleep = fake_sleep  # inject the stopping sleep

    asyncio.run(collector.run())

    assert len(factory_calls) == 3
    assert sleeps == [1.0, 2.0, 4.0]  # exponential growth
    got = store.read_window(now - timedelta(hours=1), now + timedelta(hours=1))
    assert len(got) == 3  # one event flushed per connection


def test_run_resets_backoff_after_healthy_session(tmp_path: Any) -> None:
    """A session counted as healthy resets the backoff (no escalation)."""
    store = LiquidationStore(tmp_path)
    now = datetime.now(timezone.utc)
    n_ms = int(now.timestamp() * 1000)
    conns = [_ScriptedWs([_force_order_msg(t_ms=n_ms + i)]) for i in range(3)]
    sleeps: list[float] = []

    collector = LiquidationCollector(
        store=store,
        ws_factory=lambda url: conns.pop(0),
        backoff_initial_s=1.0,
        backoff_factor=2.0,
        backoff_reset_after_s=0.0,  # every session is "healthy" -> always reset
        flush_interval_s=5.0,
    )

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)
        if len(sleeps) >= 3:
            collector.stop()

    collector._sleep = fake_sleep
    asyncio.run(collector.run())

    assert sleeps == [1.0, 1.0, 1.0]  # reset each time -> no exponential growth


def test_run_flushes_on_stream_silence(tmp_path: Any) -> None:
    """A recv timeout (silence) flushes the buffered burst mid-connection."""
    store = LiquidationStore(tmp_path)
    now = datetime.now(timezone.utc)
    n_ms = int(now.timestamp() * 1000)

    class _SilentAfterFirst:
        def __init__(self) -> None:
            self.calls = 0

        async def __aenter__(self) -> "_SilentAfterFirst":
            return self

        async def __aexit__(self, *exc: object) -> bool:
            return False

        async def recv(self) -> str:
            self.calls += 1
            if self.calls == 1:
                return _force_order_msg(t_ms=n_ms)
            if self.calls == 2:
                await asyncio.sleep(5.0)  # hang -> wait_for times out -> flush
                return ""  # unreachable
            raise ConnectionError("closed")

    collector = LiquidationCollector(
        store=store,
        ws_factory=lambda url: _SilentAfterFirst(),
        flush_interval_s=0.02,  # tiny so the silence timeout fires fast
    )

    async def stop_sleep(delay: float) -> None:
        collector.stop()

    collector._sleep = stop_sleep
    asyncio.run(collector.run())

    # The single event was flushed by the silence-timeout, before the disconnect.
    got = store.read_window(now - timedelta(hours=1), now + timedelta(hours=1))
    assert len(got) == 1


def test_run_graceful_stop_flushes_buffer(tmp_path: Any) -> None:
    """Requesting stop mid-stream flushes the buffer and exits cleanly."""
    store = LiquidationStore(tmp_path)
    now = datetime.now(timezone.utc)
    n_ms = int(now.timestamp() * 1000)

    class _OneThenStop:
        async def __aenter__(self) -> "_OneThenStop":
            return self

        async def __aexit__(self, *exc: object) -> bool:
            return False

        async def recv(self) -> str:
            return _force_order_msg(t_ms=n_ms)

    collector = LiquidationCollector(
        store=store,
        ws_factory=lambda url: _OneThenStop(),
        flush_interval_s=5.0,
        flush_max_events=1,  # flush after the first event
    )

    # Stop right after the first flush by polling buffer state via sleep hook.
    async def stop_after_first(delay: float) -> None:
        collector.stop()

    # Drive a single consume pass then stop: patch _consume to stop after 1 event.
    original_on_message = collector.on_message

    def on_message_then_stop(raw: str) -> Any:
        result = original_on_message(raw)
        collector.stop()
        return result

    collector.on_message = on_message_then_stop  # type: ignore[method-assign]
    collector._sleep = stop_after_first
    asyncio.run(collector.run())

    got = store.read_window(now - timedelta(hours=1), now + timedelta(hours=1))
    assert len(got) == 1
    assert collector.buffer_size == 0
