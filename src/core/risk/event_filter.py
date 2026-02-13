"""Event-based trading restriction filter.

Blocks trading around known market-moving events such as FOMC
announcements, CPI releases, and other scheduled economic events.
Each event has configurable before/after blocking windows.

Decision: DEC-2026-02-12-012 - Injectable datetime for testability
Decision: DEC-2026-02-12-013 - Optional in RiskController
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class TradingEvent:
    """Immutable definition of a market-moving event.

    Attributes:
        name: Human-readable event name (e.g., "FOMC Rate Decision").
        event_time: Scheduled event time (must be timezone-aware).
        block_before_minutes: Minutes to block trading before event.
        block_after_minutes: Minutes to block trading after event.
        severity: Event severity level ("low", "medium", "high").
    """

    name: str
    event_time: datetime
    block_before_minutes: int = 30
    block_after_minutes: int = 30
    severity: str = "high"

    def __post_init__(self) -> None:
        """Validate event fields.

        Raises:
            ValueError: If event_time is naive (no timezone) or
                name is empty.
        """
        if not self.name:
            raise ValueError("Event name is required")
        if self.event_time.tzinfo is None:
            raise ValueError(
                "event_time must be timezone-aware "
                "(use datetime with timezone.utc)"
            )
        if self.block_before_minutes < 0:
            raise ValueError(
                f"block_before_minutes must be >= 0, "
                f"got {self.block_before_minutes}"
            )
        if self.block_after_minutes < 0:
            raise ValueError(
                f"block_after_minutes must be >= 0, "
                f"got {self.block_after_minutes}"
            )
        if self.severity not in ("low", "medium", "high"):
            raise ValueError(
                f"severity must be 'low', 'medium', or 'high', "
                f"got '{self.severity}'"
            )


@dataclass(frozen=True)
class EventFilterResult:
    """Immutable result of an event filter check.

    Attributes:
        is_tradeable: Whether trading is allowed at this time.
        blocking_event: The event blocking trading (if any).
        reason: Human-readable reason if trading is blocked.
        filter_name: Identifier for the filter.
    """

    is_tradeable: bool
    blocking_event: TradingEvent | None
    reason: str
    filter_name: str


class EventFilter:
    """Filters trading based on scheduled market events.

    Maintains a list of upcoming events and checks whether
    the current time falls within any event's blocking window
    (before or after the event).

    Events are automatically removed once their blocking window
    has fully expired.
    """

    FILTER_NAME: str = "event"

    def __init__(
        self,
        events: tuple[TradingEvent, ...] = (),
    ) -> None:
        """Initialize the event filter.

        Args:
            events: Initial tuple of trading events.
        """
        self._events: list[TradingEvent] = list(events)

    @property
    def events(self) -> list[TradingEvent]:
        """Get all registered events."""
        return list(self._events)

    def check(self, now: datetime | None = None) -> EventFilterResult:
        """Check if trading is blocked by any event.

        Iterates through all events and checks if current time
        falls within any event's blocking window.

        Args:
            now: Current time (injectable for testing).

        Returns:
            EventFilterResult indicating whether trading is allowed.
        """
        now = now or datetime.now(timezone.utc)

        for event in self._events:
            block_start = event.event_time - timedelta(
                minutes=event.block_before_minutes
            )
            block_end = event.event_time + timedelta(
                minutes=event.block_after_minutes
            )

            if block_start <= now <= block_end:
                # Determine if we're before or after the event
                if now < event.event_time:
                    phase = "before"
                    minutes_to_event = int(
                        (event.event_time - now).total_seconds() / 60
                    )
                    reason = (
                        f"Trading blocked {minutes_to_event}min "
                        f"before '{event.name}'"
                    )
                else:
                    phase = "after"
                    minutes_since = int(
                        (now - event.event_time).total_seconds() / 60
                    )
                    reason = (
                        f"Trading blocked {minutes_since}min "
                        f"after '{event.name}'"
                    )

                logger.info(
                    "event_filter_blocked",
                    event_name=event.name,
                    phase=phase,
                    severity=event.severity,
                )

                return EventFilterResult(
                    is_tradeable=False,
                    blocking_event=event,
                    reason=reason,
                    filter_name=self.FILTER_NAME,
                )

        return EventFilterResult(
            is_tradeable=True,
            blocking_event=None,
            reason="",
            filter_name=self.FILTER_NAME,
        )

    def add_event(self, event: TradingEvent) -> None:
        """Add a new event to the filter.

        Args:
            event: Trading event to add.
        """
        self._events.append(event)
        logger.info(
            "event_filter_event_added",
            event_name=event.name,
            event_time=event.event_time.isoformat(),
            severity=event.severity,
        )

    def remove_expired_events(
        self, now: datetime | None = None
    ) -> int:
        """Remove events whose blocking window has fully passed.

        Args:
            now: Current time (injectable for testing).

        Returns:
            Number of events removed.
        """
        now = now or datetime.now(timezone.utc)
        before_count = len(self._events)

        self._events = [
            event
            for event in self._events
            if (
                event.event_time
                + timedelta(minutes=event.block_after_minutes)
            )
            > now
        ]

        removed = before_count - len(self._events)
        if removed > 0:
            logger.info(
                "event_filter_expired_removed",
                removed_count=removed,
                remaining_count=len(self._events),
            )
        return removed

    def get_upcoming_events(
        self,
        hours: int = 24,
        now: datetime | None = None,
    ) -> list[TradingEvent]:
        """Get events occurring within the specified time window.

        Args:
            hours: Look-ahead window in hours.
            now: Current time (injectable for testing).

        Returns:
            List of events within the window, sorted by event_time.
        """
        now = now or datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=hours)

        upcoming = [
            event
            for event in self._events
            if now <= event.event_time <= cutoff
        ]

        return sorted(upcoming, key=lambda e: e.event_time)
