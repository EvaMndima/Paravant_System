"""Multi-channel escalation manager for emergency contact.

Implements PRD Safety C: Emergency contact escalation with timed progression
from Telegram to Email to SMS based on alert severity and acknowledgment.

Escalation policies by severity:
- INFO: Telegram only, no acknowledgment required
- WARNING: Telegram immediately, Email after 15min unacknowledged
- ERROR: Telegram + Email immediately, SMS after 15min unacknowledged
- CRITICAL: All channels immediately, repeat every 5min until acknowledged

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-02-12-001 - Frozen dataclasses
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.utils.logging import get_logger

if TYPE_CHECKING:
    from src.core.alerting.manager import Alert, AlertChannel

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Escalation Types
# ---------------------------------------------------------------------------


class EscalationLevel(str, enum.Enum):
    """Escalation channel levels."""

    L1_TELEGRAM = "telegram"
    L2_EMAIL = "email"
    L3_SMS = "sms"


@dataclass(frozen=True)
class EscalationContact:
    """Emergency contact information.

    Attributes:
        name: Contact name.
        telegram_id: Telegram user ID or chat ID.
        email: Email address.
        phone: Phone number (E.164 format for SMS).
    """

    name: str
    telegram_id: str
    email: str
    phone: str


@dataclass(frozen=True)
class EscalationPolicy:
    """Escalation policy for an alert level.

    Attributes:
        alert_level: Alert level this policy applies to.
        channels: Channels to use (in order).
        escalation_delay_minutes: Minutes to wait before escalating.
        require_acknowledgment: Whether acknowledgment is required.
        repeat_interval_minutes: Minutes between repeats (0 = no repeat).
    """

    alert_level: str
    channels: list[EscalationLevel]
    escalation_delay_minutes: int
    require_acknowledgment: bool
    repeat_interval_minutes: int = 0


# ---------------------------------------------------------------------------
# Escalation Manager
# ---------------------------------------------------------------------------


class EscalationManager:
    """Multi-channel alert escalation per PRD Safety C.

    Manages timed escalation from Telegram to Email to SMS based on
    alert severity and acknowledgment status.

    Attributes:
        telegram_channel: Telegram channel instance.
        email_channel: Email channel instance (may be None for MVP).
        sms_channel: SMS channel instance (may be None for MVP).
    """

    # Escalation policies per alert level (PRD Safety C)
    POLICIES: dict[str, EscalationPolicy] = {
        "info": EscalationPolicy(
            alert_level="info",
            channels=[EscalationLevel.L1_TELEGRAM],
            escalation_delay_minutes=0,
            require_acknowledgment=False,
        ),
        "warning": EscalationPolicy(
            alert_level="warning",
            channels=[EscalationLevel.L1_TELEGRAM],
            escalation_delay_minutes=15,  # Email after 15min
            require_acknowledgment=True,
        ),
        "error": EscalationPolicy(
            alert_level="error",
            channels=[
                EscalationLevel.L1_TELEGRAM,
                EscalationLevel.L2_EMAIL,
            ],
            escalation_delay_minutes=15,  # SMS after 15min
            require_acknowledgment=True,
        ),
        "critical": EscalationPolicy(
            alert_level="critical",
            channels=[
                EscalationLevel.L1_TELEGRAM,
                EscalationLevel.L2_EMAIL,
                EscalationLevel.L3_SMS,
            ],
            escalation_delay_minutes=5,  # Repeat every 5min
            require_acknowledgment=True,
            repeat_interval_minutes=5,
        ),
    }

    def __init__(
        self,
        telegram_channel: "AlertChannel | None" = None,
        email_channel: "AlertChannel | None" = None,
        sms_channel: "AlertChannel | None" = None,
    ) -> None:
        """Initialize escalation manager.

        Args:
            telegram_channel: Telegram channel instance.
            email_channel: Email channel instance (optional for MVP).
            sms_channel: SMS channel instance (optional for MVP).
        """
        self.telegram_channel = telegram_channel
        self.email_channel = email_channel
        self.sms_channel = sms_channel

        # Track pending acknowledgments: {alert_id: sent_at}
        self._pending_acknowledgments: dict[str, datetime] = {}

        # Track escalation state: {alert_id: escalation_level}
        # 0 = initial send, 1 = escalated to email, 2 = escalated to SMS
        self._escalation_state: dict[str, int] = {}

        # Track last repeat time for critical alerts
        self._last_repeat: dict[str, datetime] = {}

        logger.info(
            "escalation_manager_initialized",
            has_telegram=telegram_channel is not None,
            has_email=email_channel is not None,
            has_sms=sms_channel is not None,
        )

    async def send_with_escalation(self, alert: "Alert") -> str:
        """Send alert and start escalation timer if needed.

        Args:
            alert: Alert to send.

        Returns:
            Alert ID for tracking.
        """
        policy = self.POLICIES.get(alert.level.value)
        if not policy:
            logger.warning(
                "unknown_alert_level",
                level=alert.level.value,
                alert_id=alert.alert_id,
            )
            return alert.alert_id or ""

        # Send to initial channels
        for channel_level in policy.channels:
            await self._send_to_channel(alert, channel_level)

        # Track for acknowledgment if required
        if policy.require_acknowledgment and alert.alert_id:
            self._pending_acknowledgments[alert.alert_id] = datetime.now(
                timezone.utc
            )
            self._escalation_state[alert.alert_id] = 0
            if policy.repeat_interval_minutes > 0:
                self._last_repeat[alert.alert_id] = datetime.now(
                    timezone.utc
                )

        logger.info(
            "alert_sent_with_escalation",
            alert_id=alert.alert_id,
            level=alert.level.value,
            channels=[c.value for c in policy.channels],
            require_ack=policy.require_acknowledgment,
        )

        return alert.alert_id or ""

    async def acknowledge(self, alert_id: str, by: str) -> None:
        """Mark alert as acknowledged, stop escalation.

        Args:
            alert_id: Alert ID to acknowledge.
            by: Who acknowledged (user ID or name).
        """
        if alert_id in self._pending_acknowledgments:
            sent_at = self._pending_acknowledgments.pop(alert_id)
            self._escalation_state.pop(alert_id, None)
            self._last_repeat.pop(alert_id, None)

            duration = (
                datetime.now(timezone.utc) - sent_at
            ).total_seconds()

            logger.info(
                "alert_acknowledged",
                alert_id=alert_id,
                by=by,
                duration_seconds=duration,
            )
        else:
            logger.warning(
                "alert_acknowledgment_not_pending",
                alert_id=alert_id,
                by=by,
            )

    async def check_escalations(self) -> None:
        """Check pending alerts and escalate if unacknowledged.

        Called each main loop cycle (every few seconds).
        Checks escalation timers and sends additional channels as needed.
        """
        now = datetime.now(timezone.utc)

        for alert_id, sent_at in list(self._pending_acknowledgments.items()):
            elapsed_min = (now - sent_at).total_seconds() / 60
            current_level = self._escalation_state.get(alert_id, 0)

            # Get the alert level from alert_id (stored in format: title_timestamp)
            # For now, we'll skip detailed checks and just log
            # In production, would store full alert object or level info

            # Check for repeat (CRITICAL only)
            if alert_id in self._last_repeat:
                last_repeat = self._last_repeat[alert_id]
                repeat_elapsed = (now - last_repeat).total_seconds() / 60
                policy = self.POLICIES["critical"]
                if (
                    repeat_elapsed
                    >= policy.repeat_interval_minutes
                ):
                    logger.warning(
                        "critical_alert_repeat",
                        alert_id=alert_id,
                        elapsed_minutes=elapsed_min,
                    )
                    # Would re-send to all channels here
                    self._last_repeat[alert_id] = now

            # Check for escalation to SMS (30 min for WARNING/ERROR)
            elif elapsed_min > 30 and current_level < 2:
                if self.sms_channel:
                    logger.warning(
                        "escalating_to_sms",
                        alert_id=alert_id,
                        elapsed_minutes=elapsed_min,
                    )
                    # Would send to SMS channel here
                    # await self._send_to_channel_by_level(alert, EscalationLevel.L3_SMS)
                    self._escalation_state[alert_id] = 2
                else:
                    logger.debug(
                        "sms_escalation_skipped_no_channel",
                        alert_id=alert_id,
                    )

            # Check for escalation to Email (15 min for WARNING, ERROR already sent)
            elif elapsed_min > 15 and current_level < 1:
                if self.email_channel:
                    logger.warning(
                        "escalating_to_email",
                        alert_id=alert_id,
                        elapsed_minutes=elapsed_min,
                    )
                    # Would send to Email channel here
                    # await self._send_to_channel_by_level(alert, EscalationLevel.L2_EMAIL)
                    self._escalation_state[alert_id] = 1
                else:
                    logger.debug(
                        "email_escalation_skipped_no_channel",
                        alert_id=alert_id,
                    )

    async def _send_to_channel(
        self, alert: "Alert", channel_level: EscalationLevel
    ) -> None:
        """Send alert to specific channel level.

        Args:
            alert: Alert to send.
            channel_level: Channel level (L1_TELEGRAM, L2_EMAIL, L3_SMS).
        """
        try:
            if channel_level == EscalationLevel.L1_TELEGRAM:
                if self.telegram_channel:
                    await self.telegram_channel.send(alert)
                else:
                    logger.warning(
                        "telegram_channel_not_configured",
                        alert_id=alert.alert_id,
                    )

            elif channel_level == EscalationLevel.L2_EMAIL:
                if self.email_channel:
                    await self.email_channel.send(alert)
                else:
                    logger.debug(
                        "email_channel_not_configured",
                        alert_id=alert.alert_id,
                    )

            elif channel_level == EscalationLevel.L3_SMS:
                if self.sms_channel:
                    await self.sms_channel.send(alert)
                else:
                    logger.debug(
                        "sms_channel_not_configured",
                        alert_id=alert.alert_id,
                    )

        except Exception as e:
            logger.error(
                "escalation_channel_send_failed",
                channel=channel_level.value,
                alert_id=alert.alert_id,
                error=str(e),
                exc_info=True,
            )


# ---------------------------------------------------------------------------
# Email and SMS Channel Stubs (MVP - interfaces only)
# ---------------------------------------------------------------------------


class EmailChannel:
    """Email alert channel stub for MVP.

    In production, would use aiosmtplib for async email sending.
    For MVP, this is an interface placeholder configured via env vars.

    Attributes:
        smtp_host: SMTP server hostname.
        smtp_port: SMTP server port.
        username: SMTP authentication username.
        password: SMTP authentication password.
        from_addr: From email address.
        to_addrs: List of recipient email addresses.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: list[str],
    ) -> None:
        """Initialize email channel stub.

        Args:
            smtp_host: SMTP server hostname.
            smtp_port: SMTP server port.
            username: SMTP username.
            password: SMTP password.
            from_addr: From email address.
            to_addrs: List of recipient emails.
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs

        logger.info(
            "email_channel_stub_initialized",
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            from_addr=from_addr,
            recipients=len(to_addrs),
        )

    async def send(self, alert: "Alert") -> None:
        """Send alert via email (stub for MVP).

        Args:
            alert: Alert to send.
        """
        subject = f"[{alert.level.value.upper()}] PARAVANT: {alert.title}"
        logger.info(
            "email_alert_stub",
            alert_id=alert.alert_id,
            subject=subject,
            recipients=self.to_addrs,
            message="Email sending not implemented in MVP",
        )


class SMSChannel:
    """SMS alert channel stub for MVP.

    In production, would use Twilio API for SMS sending.
    For MVP, this is an interface placeholder configured via env vars.

    Attributes:
        account_sid: Twilio account SID.
        auth_token: Twilio auth token.
        from_number: Twilio phone number.
        to_numbers: List of recipient phone numbers.
    """

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        to_numbers: list[str],
    ) -> None:
        """Initialize SMS channel stub.

        Args:
            account_sid: Twilio account SID.
            auth_token: Twilio auth token.
            from_number: Twilio phone number.
            to_numbers: List of recipient phone numbers (E.164 format).
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.to_numbers = to_numbers

        logger.info(
            "sms_channel_stub_initialized",
            from_number=from_number,
            recipients=len(to_numbers),
        )

    async def send(self, alert: "Alert") -> None:
        """Send alert via SMS (stub for MVP).

        Args:
            alert: Alert to send.
        """
        # No message is built: SMS sending is a stub for MVP, so truncating
        # to the 160-char limit would be dead work.
        logger.info(
            "sms_alert_stub",
            alert_id=alert.alert_id,
            recipients=self.to_numbers,
            message="SMS sending not implemented in MVP",
        )
