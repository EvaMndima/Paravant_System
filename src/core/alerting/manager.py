"""Central alert management with multi-channel support and rate limiting.

Manages alert routing, deduplication, persistence, and escalation for the
PARAVANT Trading System. All system events flow through AlertManager to
reach the operator via multiple channels (Telegram, Email, SMS).

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-007 - Input validation at boundaries
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-02-12-001 - Frozen dataclasses for immutable types
"""
from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.data.store import DataStore
from src.utils.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Alert Level and Data Types
# ---------------------------------------------------------------------------


class AlertLevel(str, enum.Enum):
    """Alert severity levels.

    Determines routing, escalation policy, and operator response urgency.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Alert:
    """Immutable alert message.

    Represents a single alert event with severity, content, and metadata.
    Once created, alerts cannot be modified (audit integrity).

    Attributes:
        level: Alert severity (INFO, WARNING, ERROR, CRITICAL).
        title: Short alert title (shown in notifications).
        message: Detailed alert message.
        timestamp: When alert was generated (timezone-aware UTC).
        metadata: Additional context (strategy_id, symbol, etc.).
        alert_id: Unique identifier for tracking/acknowledgment.
    """

    level: AlertLevel
    title: str
    message: str
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: dict[str, Any] = field(default_factory=dict)
    alert_id: str | None = None


# ---------------------------------------------------------------------------
# Alert Channel Abstract Base Class
# ---------------------------------------------------------------------------


class AlertChannel(ABC):
    """Abstract base class for alert delivery channels.

    All channels (Telegram, Email, SMS) must implement the send() method.
    Channel failures are isolated: one channel failing doesn't block others.
    """

    @abstractmethod
    async def send(self, alert: Alert) -> None:
        """Send alert through this channel.

        Args:
            alert: Alert to deliver.

        Raises:
            AlertDeliveryError: If delivery fails.
        """
        pass


# ---------------------------------------------------------------------------
# Alert Rate Limiter
# ---------------------------------------------------------------------------


class AlertRateLimiter:
    """Rate limiting to prevent alert spam.

    Rules:
    - Same title: max 1 per 5 minutes (prevents duplicate spam)
    - Same level: max 10 per hour (prevents level-specific floods)
    - CRITICAL alerts: ALWAYS sent (no rate limit - safety priority)
    - Suppressed alerts: counted for monitoring

    Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
    """

    TITLE_COOLDOWN_SECONDS = 300  # 5 minutes
    LEVEL_MAX_PER_HOUR = 10

    def __init__(self) -> None:
        """Initialize rate limiter."""
        self._recent_by_title: dict[str, datetime] = {}
        self._level_counts: dict[AlertLevel, deque[datetime]] = defaultdict(
            deque
        )
        self._suppressed_count: int = 0

    def should_send(self, alert: Alert) -> bool:
        """Check if alert should be sent or suppressed.

        CRITICAL alerts always bypass rate limiting for safety.

        Args:
            alert: Alert to check.

        Returns:
            True if alert should be sent, False if suppressed.
        """
        # Critical always sends - safety priority
        if alert.level == AlertLevel.CRITICAL:
            return True

        now = datetime.now(timezone.utc)

        # Check title cooldown (prevent duplicate spam)
        if alert.title in self._recent_by_title:
            last_sent = self._recent_by_title[alert.title]
            if (now - last_sent).total_seconds() < self.TITLE_COOLDOWN_SECONDS:
                self._suppressed_count += 1
                logger.debug(
                    "alert_suppressed_title_cooldown",
                    title=alert.title,
                    last_sent=last_sent.isoformat(),
                )
                return False

        # Check level rate limit (prevent level-specific floods)
        level_times = self._level_counts[alert.level]

        # Clean old entries (>1 hour)
        while level_times and (now - level_times[0]).total_seconds() > 3600:
            level_times.popleft()

        if len(level_times) >= self.LEVEL_MAX_PER_HOUR:
            self._suppressed_count += 1
            logger.debug(
                "alert_suppressed_level_limit",
                level=alert.level.value,
                count=len(level_times),
            )
            return False

        # Record and allow
        self._recent_by_title[alert.title] = now
        self._level_counts[alert.level].append(now)

        return True

    def get_suppressed_count(self) -> int:
        """Get total suppressed alert count for monitoring.

        Returns:
            Number of alerts suppressed since last reset.
        """
        return self._suppressed_count

    def reset_suppressed_count(self) -> None:
        """Reset suppressed count (called periodically for metrics)."""
        self._suppressed_count = 0


# ---------------------------------------------------------------------------
# Alert Manager
# ---------------------------------------------------------------------------


class AlertManager:
    """Central alert management with multi-channel support.

    Responsibilities:
    - Route alerts to appropriate channels based on severity
    - Rate limit to prevent spam (respecting CRITICAL bypass)
    - Track acknowledgments for escalation
    - Persist alert history for dashboard feed
    - Coordinate with EscalationManager for multi-channel escalation

    Attributes:
        data_store: DataStore for alert persistence.
    """

    def __init__(self, data_store: DataStore) -> None:
        """Initialize alert manager.

        Args:
            data_store: DataStore for alert persistence.
        """
        self._data_store = data_store
        self._channels: list[AlertChannel] = []
        self._rate_limiter = AlertRateLimiter()
        self._escalation_manager: Any = None  # EscalationManager (avoid circular import)

        logger.info("alert_manager_initialized")

    def register_channel(self, channel: AlertChannel) -> None:
        """Register an alert delivery channel.

        Args:
            channel: AlertChannel implementation (Telegram, Email, SMS).
        """
        self._channels.append(channel)
        logger.info(
            "alert_channel_registered",
            channel=channel.__class__.__name__,
            total_channels=len(self._channels),
        )

    def set_escalation_manager(self, manager: Any) -> None:
        """Set escalation manager for multi-channel escalation.

        Args:
            manager: EscalationManager instance.
        """
        self._escalation_manager = manager
        logger.info("escalation_manager_set")

    async def send_alert(self, alert: Alert) -> None:
        """Send alert to all registered channels, respecting rate limits.

        CRITICAL alerts bypass rate limiting for safety priority.
        Channel failures are isolated: one failing doesn't block others.

        Args:
            alert: Alert to send.
        """
        # Generate alert ID for tracking
        if alert.alert_id is None:
            alert_id = f"{alert.title}_{alert.timestamp.timestamp()}"
            # Recreate alert with ID (frozen dataclass requires recreation)
            alert = Alert(
                level=alert.level,
                title=alert.title,
                message=alert.message,
                timestamp=alert.timestamp,
                metadata=alert.metadata,
                alert_id=alert_id,
            )

        # Check rate limit (CRITICAL bypasses)
        if not self._rate_limiter.should_send(alert):
            logger.debug(
                "alert_rate_limited",
                title=alert.title,
                level=alert.level.value,
            )
            return

        # Persist to database (for dashboard alert feed)
        # Note: This is a simplified version - in production would save to AlertLog table
        # For MVP, we log it which can be queried later
        logger.info(
            "alert_generated",
            alert_id=alert.alert_id,
            level=alert.level.value,
            title=alert.title,
            message=alert.message[:100],  # Truncate for log
            metadata=alert.metadata,
        )

        # Route through escalation if available
        if self._escalation_manager:
            await self._escalation_manager.send_with_escalation(alert)
        else:
            # No escalation manager: send directly to all channels
            for channel in self._channels:
                try:
                    await channel.send(alert)
                except Exception as e:
                    # Channel failure is non-fatal: log and continue
                    logger.error(
                        "alert_channel_failed",
                        channel=channel.__class__.__name__,
                        alert_id=alert.alert_id,
                        error=str(e),
                        exc_info=True,
                    )

    async def send_info(
        self, title: str, message: str, **metadata: Any
    ) -> None:
        """Send INFO level alert.

        Args:
            title: Alert title.
            message: Alert message.
            **metadata: Additional context.
        """
        alert = Alert(
            level=AlertLevel.INFO,
            title=title,
            message=message,
            metadata=metadata,
        )
        await self.send_alert(alert)

    async def send_warning(
        self, title: str, message: str, **metadata: Any
    ) -> None:
        """Send WARNING level alert.

        Args:
            title: Alert title.
            message: Alert message.
            **metadata: Additional context.
        """
        alert = Alert(
            level=AlertLevel.WARNING,
            title=title,
            message=message,
            metadata=metadata,
        )
        await self.send_alert(alert)

    async def send_error(
        self, title: str, message: str, **metadata: Any
    ) -> None:
        """Send ERROR level alert.

        Args:
            title: Alert title.
            message: Alert message.
            **metadata: Additional context.
        """
        alert = Alert(
            level=AlertLevel.ERROR,
            title=title,
            message=message,
            metadata=metadata,
        )
        await self.send_alert(alert)

    async def send_critical(
        self, title: str, message: str, **metadata: Any
    ) -> None:
        """Send CRITICAL level alert.

        CRITICAL alerts bypass rate limiting for safety priority.

        Args:
            title: Alert title.
            message: Alert message.
            **metadata: Additional context.
        """
        alert = Alert(
            level=AlertLevel.CRITICAL,
            title=title,
            message=message,
            metadata=metadata,
        )
        await self.send_alert(alert)

    async def check_escalations(self) -> None:
        """Check pending alerts and escalate if unacknowledged.

        Called each main loop cycle to check escalation timers.
        Delegates to EscalationManager if configured.
        """
        if self._escalation_manager:
            await self._escalation_manager.check_escalations()
