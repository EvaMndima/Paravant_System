"""In-process async event bus for real-time SSE streaming.

Provides publish/subscribe functionality using asyncio.Queue per subscriber.
No external dependencies (Redis, etc.) - fits monolithic MVP architecture.

Event types:
- kill_switch_changed: Kill switch activated/deactivated
- system_status_changed: System status transitions
- position_updated: Position opened/closed/updated
- alert_created: New alert triggered
- risk_status_changed: Risk threshold changes
- regime_changed: Market regime manually changed

Decision: DEC-2026-01-15-005 - Monolithic architecture (in-process, no Redis)
Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Supported event types (validated on publish)
EVENT_TYPES: frozenset[str] = frozenset({
    "kill_switch_changed",
    "system_status_changed",
    "position_updated",
    "alert_created",
    "risk_status_changed",
    "regime_changed",
})

# Maximum queue depth per subscriber before oldest events are dropped
_MAX_QUEUE_SIZE: int = 500


class EventBus:
    """Async in-process pub/sub event bus.

    Subscribers receive events via per-client asyncio.Queue instances.
    Thread-safe via asyncio.Lock (async context only).

    Usage:
        bus = EventBus()
        sub_id = await bus.subscribe(["position_updated", "alert_created"])
        event = await bus.get_event(sub_id, timeout=30.0)
        await bus.unsubscribe(sub_id)
    """

    def __init__(self) -> None:
        """Initialize the EventBus with empty subscriber registry."""
        # {subscriber_id: {"queue": asyncio.Queue, "event_types": set[str]}}
        self._subscribers: dict[str, dict[str, Any]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def subscribe(
        self,
        event_types: list[str] | None = None,
    ) -> str:
        """Subscribe to events and receive a unique subscriber ID.

        Args:
            event_types: List of event types to subscribe to.
                If None, subscribes to ALL event types.

        Returns:
            Unique subscriber ID for retrieving events.

        Raises:
            ValueError: If an invalid event type is provided.
        """
        if event_types is not None:
            invalid = set(event_types) - EVENT_TYPES
            if invalid:
                raise ValueError(
                    f"Invalid event types: {invalid}. "
                    f"Valid types: {sorted(EVENT_TYPES)}"
                )
            subscribed_types = set(event_types)
        else:
            subscribed_types = set(EVENT_TYPES)

        sub_id = f"sub_{uuid.uuid4().hex[:16]}"

        async with self._lock:
            self._subscribers[sub_id] = {
                "queue": asyncio.Queue(maxsize=_MAX_QUEUE_SIZE),
                "event_types": subscribed_types,
            }

        logger.info(
            "event_bus_subscribed",
            subscriber_id=sub_id,
            event_types=sorted(subscribed_types),
        )
        return sub_id

    async def unsubscribe(self, subscriber_id: str) -> bool:
        """Remove a subscriber from the event bus.

        Args:
            subscriber_id: The subscriber ID to remove.

        Returns:
            True if the subscriber was found and removed, False otherwise.
        """
        async with self._lock:
            removed = self._subscribers.pop(subscriber_id, None) is not None

        if removed:
            logger.info("event_bus_unsubscribed", subscriber_id=subscriber_id)
        else:
            logger.warning(
                "event_bus_unsubscribe_not_found",
                subscriber_id=subscriber_id,
            )
        return removed

    async def publish(self, event_type: str, data: dict[str, Any]) -> int:
        """Publish an event to all matching subscribers.

        Events are delivered asynchronously to subscriber queues.
        If a subscriber's queue is full, the event is dropped for that
        subscriber (logged as warning) to prevent backpressure.

        Args:
            event_type: The type of event (must be in EVENT_TYPES).
            data: Event payload (will be augmented with timestamp and type).

        Returns:
            Number of subscribers the event was delivered to.

        Raises:
            ValueError: If event_type is not in EVENT_TYPES.
        """
        if event_type not in EVENT_TYPES:
            raise ValueError(
                f"Invalid event type: {event_type}. "
                f"Valid types: {sorted(EVENT_TYPES)}"
            )

        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

        delivered = 0
        async with self._lock:
            subscribers_snapshot = list(self._subscribers.items())

        for sub_id, sub_info in subscribers_snapshot:
            if event_type not in sub_info["event_types"]:
                continue
            queue: asyncio.Queue[dict[str, Any]] = sub_info["queue"]
            try:
                queue.put_nowait(event)
                delivered += 1
            except asyncio.QueueFull:
                logger.warning(
                    "event_bus_queue_full",
                    subscriber_id=sub_id,
                    event_type=event_type,
                    queue_size=_MAX_QUEUE_SIZE,
                )

        return delivered

    async def get_event(
        self,
        subscriber_id: str,
        timeout: float = 30.0,
    ) -> dict[str, Any] | None:
        """Get the next event for a subscriber.

        Blocks until an event is available or timeout expires.

        Args:
            subscriber_id: The subscriber ID to get events for.
            timeout: Maximum seconds to wait (default 30s for SSE heartbeat).

        Returns:
            Event dict or None if timeout expired.

        Raises:
            KeyError: If subscriber_id is not found.
        """
        async with self._lock:
            sub_info = self._subscribers.get(subscriber_id)

        if sub_info is None:
            raise KeyError(f"Subscriber not found: {subscriber_id}")

        queue: asyncio.Queue[dict[str, Any]] = sub_info["queue"]
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def get_subscriber_count(self) -> int:
        """Get the current number of active subscribers.

        Returns:
            Number of subscribers.
        """
        async with self._lock:
            return len(self._subscribers)

    async def get_subscriber_info(self) -> list[dict[str, Any]]:
        """Get diagnostic information about all subscribers.

        Returns:
            List of subscriber info dicts with id, event_types, queue_size.
        """
        async with self._lock:
            return [
                {
                    "subscriber_id": sub_id,
                    "event_types": sorted(sub_info["event_types"]),
                    "queue_size": sub_info["queue"].qsize(),
                }
                for sub_id, sub_info in self._subscribers.items()
            ]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the EventBus singleton.

    Returns:
        The EventBus instance.

    Raises:
        RuntimeError: If EventBus has not been initialized.
    """
    if _event_bus is None:
        raise RuntimeError(
            "EventBus not initialized. Call init_event_bus() during startup."
        )
    return _event_bus


def init_event_bus() -> EventBus:
    """Initialize the global EventBus singleton.

    Safe to call multiple times - returns existing instance if already created.

    Returns:
        The EventBus instance.
    """
    global _event_bus  # noqa: PLW0603
    if _event_bus is None:
        _event_bus = EventBus()
        logger.info("event_bus_initialized")
    return _event_bus
