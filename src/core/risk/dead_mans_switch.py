"""Dead man's switch - auto-halt if system becomes unresponsive.

Heartbeat-based mechanism per PRD Feature C:
- System records heartbeat every cycle (externally called)
- External watchdog checks heartbeat periodically
- If too many heartbeats are missed, triggers kill switch
- Sequence: check -> auto-activate kill switch

This is separate from the Kill Switch:
- Kill Switch: Manual or loss-trigger based
- Dead Man's Switch: Triggers if SYSTEM itself stops responding

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.core.risk.kill_switch import KillSwitch
from src.data.store import DataStore
from src.utils.logging import get_logger

logger = get_logger(__name__)


class DeadMansSwitch:
    """Auto-halt mechanism for unresponsive system.

    The orchestrator calls heartbeat() every cycle. An external
    watchdog calls check() periodically. If check() detects too
    many missed heartbeats, it activates the kill switch.

    No internal threading for MVP - the caller is responsible
    for periodic invocation of both heartbeat() and check().

    Attributes:
        store: DataStore for persistence.
        kill_switch: KillSwitch to activate on trigger.
        interval_minutes: Expected heartbeat interval.
        max_missed: Maximum missed heartbeats before trigger.
    """

    def __init__(
        self,
        store: DataStore,
        kill_switch: KillSwitch,
        interval_minutes: int = 5,
        max_missed: int = 6,
    ) -> None:
        """Initialize the dead man's switch.

        Args:
            store: DataStore for persistence.
            kill_switch: KillSwitch instance to activate on trigger.
            interval_minutes: Expected interval between heartbeats.
            max_missed: Max missed heartbeats before triggering (default 6 = 30min).
        """
        self._store = store
        self._kill_switch = kill_switch
        self._interval_minutes = interval_minutes
        self._max_missed = max_missed
        self._last_heartbeat = datetime.now(timezone.utc)
        self._missed_count = 0
        self._triggered = False

    def heartbeat(self) -> None:
        """Record that the system is alive and responsive.

        Called by the orchestrator main loop every cycle.
        Resets the missed heartbeat counter.
        """
        self._last_heartbeat = datetime.now(timezone.utc)
        self._missed_count = 0

        logger.debug(
            "dead_mans_switch_heartbeat",
            timestamp=self._last_heartbeat.isoformat(),
        )

    def check(self) -> bool:
        """Check if heartbeat is still active.

        Called by the external watchdog process periodically.
        Increments missed counter if heartbeat is overdue.
        If max_missed is reached, auto-activates the kill switch.

        Returns:
            True if system is healthy, False if triggered.
        """
        if self._triggered:
            return False

        now = datetime.now(timezone.utc)
        elapsed = now - self._last_heartbeat
        max_elapsed = timedelta(minutes=self._interval_minutes)

        if elapsed > max_elapsed:
            self._missed_count += 1
            logger.warning(
                "dead_mans_switch_missed_heartbeat",
                missed_count=self._missed_count,
                max_missed=self._max_missed,
                elapsed_minutes=elapsed.total_seconds() / 60,
            )

            if self._missed_count >= self._max_missed:
                self._trigger()
                return False
        else:
            # Heartbeat is on time, but don't reset counter
            # (only heartbeat() resets it)
            pass

        return True

    def _trigger(self) -> None:
        """Trigger the dead man's switch by activating kill switch.

        Activates the kill switch with a descriptive reason and
        logs the event.
        """
        if self._triggered:
            return

        self._triggered = True
        total_minutes = self._missed_count * self._interval_minutes

        reason = (
            f"Dead man's switch: system unresponsive for "
            f"{total_minutes} minutes "
            f"({self._missed_count} missed heartbeats)"
        )

        logger.critical(
            "dead_mans_switch_triggered",
            missed_count=self._missed_count,
            total_minutes=total_minutes,
        )

        # Activate kill switch
        try:
            self._kill_switch.activate(
                reason=reason,
                actor="dead_mans_switch",
            )
        except Exception as e:
            logger.error(
                "dead_mans_switch_kill_switch_failed",
                error=str(e),
                exc_info=True,
            )

    def get_status(self) -> dict[str, Any]:
        """Get dead man's switch status for monitoring.

        Returns:
            Status dictionary with heartbeat info and trigger state.
        """
        now = datetime.now(timezone.utc)
        elapsed = now - self._last_heartbeat
        time_until_trigger = max(
            0,
            (self._max_missed - self._missed_count)
            * self._interval_minutes
            - elapsed.total_seconds() / 60,
        )

        return {
            "last_heartbeat": self._last_heartbeat.isoformat(),
            "missed_count": self._missed_count,
            "max_missed": self._max_missed,
            "interval_minutes": self._interval_minutes,
            "triggered": self._triggered,
            "elapsed_since_heartbeat_seconds": elapsed.total_seconds(),
            "minutes_until_trigger": round(time_until_trigger, 1),
        }

    @property
    def is_triggered(self) -> bool:
        """Check if the dead man's switch has been triggered.

        Returns:
            True if triggered.
        """
        return self._triggered

    def reset(self) -> None:
        """Reset the dead man's switch after manual intervention.

        Should only be called after the operator has verified
        system health and resolved the root cause.
        """
        self._triggered = False
        self._missed_count = 0
        self._last_heartbeat = datetime.now(timezone.utc)

        logger.info("dead_mans_switch_reset")
