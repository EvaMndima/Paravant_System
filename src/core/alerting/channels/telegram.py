"""Telegram alert channel for instant notifications.

Sends alerts via Telegram Bot API to a configured chat. Primary alert
delivery mechanism for the PARAVANT Trading System.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-02-09-006 - Sensitive data masking
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import aiohttp

from src.core.exceptions import AlertDeliveryError
from src.utils.logging import get_logger

if TYPE_CHECKING:
    from src.core.alerting.manager import Alert, AlertChannel

logger = get_logger(__name__)


class TelegramChannel:
    """Telegram Bot API alert delivery channel.

    Formats and sends alerts via Telegram Bot API. Uses HTML formatting
    for rich message display with severity levels, timestamps, and metadata.

    Message format:
        [CRITICAL] Kill Switch Activated

        All trading halted. Manual intervention required.

        2026-02-15 19:00:00 UTC

        strategy_id: str_001
        account_id: acc_main

    Attributes:
        bot_token: Telegram Bot API token (from BotFather).
        chat_id: Target chat ID (user or group).
    """

    # Severity prefixes (no emoji per user rules)
    SEVERITY_PREFIX = {
        "info": "[INFO]",
        "warning": "[WARNING]",
        "error": "[ERROR]",
        "critical": "[CRITICAL]",
    }

    # Retry configuration for transient failures
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 2.0

    def __init__(self, bot_token: str, chat_id: str) -> None:
        """Initialize Telegram channel.

        Args:
            bot_token: Telegram Bot API token.
            chat_id: Target chat ID for alerts.

        Raises:
            ValueError: If bot_token or chat_id is empty.
        """
        if not bot_token or not bot_token.strip():
            raise ValueError("bot_token cannot be empty")
        if not chat_id or not chat_id.strip():
            raise ValueError("chat_id cannot be empty")

        self.bot_token = bot_token
        self.chat_id = chat_id
        self._session: aiohttp.ClientSession | None = None

        # Log initialization (bot_token is masked by logging utility)
        logger.info(
            "telegram_channel_initialized",
            chat_id=chat_id,
            bot_token=bot_token,  # Will be masked by DEC-2026-02-09-006
        )

    async def send(self, alert: "Alert") -> None:
        """Format and send alert via Telegram Bot API.

        Uses HTML parse mode for formatting. Retries transient failures
        with exponential backoff.

        Args:
            alert: Alert to send.

        Raises:
            AlertDeliveryError: If delivery fails after retries.
        """
        message = self._format_message(alert)
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
        }

        # Retry logic for transient failures
        last_error: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                session = await self._get_session()
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        logger.info(
                            "telegram_alert_sent",
                            alert_id=alert.alert_id,
                            level=alert.level.value,
                            title=alert.title,
                        )
                        return

                    # Non-200 response
                    response_text = await resp.text()
                    error_msg = f"Telegram API returned {resp.status}: {response_text[:200]}"

                    # Rate limit (429) or server error (5xx): retry
                    if resp.status == 429 or resp.status >= 500:
                        last_error = AlertDeliveryError(
                            channel="telegram",
                            reason=error_msg,
                        )
                        if attempt < self.MAX_RETRIES - 1:
                            delay = self.RETRY_DELAY_SECONDS * (2**attempt)
                            logger.warning(
                                "telegram_retry",
                                attempt=attempt + 1,
                                status=resp.status,
                                delay=delay,
                            )
                            await asyncio.sleep(delay)
                            continue

                    # Client error (4xx except 429): don't retry
                    raise AlertDeliveryError(
                        channel="telegram",
                        reason=error_msg,
                    )

            except aiohttp.ClientError as e:
                # Network error: retry
                last_error = AlertDeliveryError(
                    channel="telegram",
                    reason=f"Network error: {str(e)}",
                )
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAY_SECONDS * (2**attempt)
                    logger.warning(
                        "telegram_network_error_retry",
                        attempt=attempt + 1,
                        error=str(e),
                        delay=delay,
                    )
                    await asyncio.sleep(delay)
                    continue

        # All retries exhausted
        logger.error(
            "telegram_delivery_failed",
            alert_id=alert.alert_id,
            retries=self.MAX_RETRIES,
            last_error=str(last_error),
        )
        raise last_error if last_error else AlertDeliveryError(
            channel="telegram",
            reason="Unknown error after retries",
        )

    def _format_message(self, alert: "Alert") -> str:
        """Format alert as HTML message for Telegram.

        Args:
            alert: Alert to format.

        Returns:
            HTML-formatted message string.
        """
        prefix = self.SEVERITY_PREFIX.get(
            alert.level.value, "[ALERT]"
        )

        lines = [
            f"<b>{prefix} {alert.title}</b>",
            "",
            alert.message,
            "",
            f"<i>{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC</i>",
        ]

        # Add metadata if present
        if alert.metadata:
            lines.append("")
            for key, value in alert.metadata.items():
                lines.append(f"<code>{key}</code>: {value}")

        return "\n".join(lines)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session.

        Returns:
            Active ClientSession.
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close HTTP session gracefully."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("telegram_session_closed")
