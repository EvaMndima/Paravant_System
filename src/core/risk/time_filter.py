"""Weekend and holiday trading restriction filter.

Provides time-based trading restrictions including weekend blocking,
holiday blocking, and blocked-hour filtering. Designed primarily for
traditional markets; crypto markets trade 24/7 so weekend blocking
defaults to False.

Decision: DEC-2026-02-12-012 - Injectable datetime for testability
Decision: DEC-2026-02-12-013 - Optional in RiskController
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class TimeFilterResult:
    """Immutable result of a time-based filter check.

    Attributes:
        is_tradeable: Whether trading is allowed at this time.
        reason: Human-readable reason if trading is blocked.
        filter_name: Identifier for the filter that produced this result.
        current_time: The time that was evaluated.
    """

    is_tradeable: bool
    reason: str
    filter_name: str
    current_time: datetime


class WeekendHolidayFilter:
    """Filter that blocks trading on weekends, holidays, or specific hours.

    Crypto markets trade 24/7 so weekend blocking defaults to False.
    Users can enable it or configure specific holidays and blocked
    hours (e.g., low-liquidity UTC hours) as needed.

    Attributes:
        block_weekends: Whether to block Saturday/Sunday trading.
        holidays: Tuple of specific dates to block.
        blocked_hours: Tuple of UTC hours (0-23) to block.
    """

    FILTER_NAME: str = "weekend_holiday"

    def __init__(
        self,
        block_weekends: bool = False,
        holidays: tuple[date, ...] = (),
        blocked_hours: tuple[int, ...] = (),
    ) -> None:
        """Initialize the time filter.

        Args:
            block_weekends: Whether to block Saturday/Sunday.
            holidays: Tuple of dates to block trading.
            blocked_hours: Tuple of UTC hours (0-23) to block.

        Raises:
            ValueError: If blocked_hours contains invalid hour values.
        """
        for hour in blocked_hours:
            if not 0 <= hour <= 23:
                raise ValueError(
                    f"Blocked hour must be 0-23, got {hour}"
                )

        self.block_weekends: bool = block_weekends
        self.holidays: tuple[date, ...] = holidays
        self.blocked_hours: tuple[int, ...] = blocked_hours

    def check(self, now: datetime | None = None) -> TimeFilterResult:
        """Check if trading is allowed at the given time.

        Evaluates in order: weekend -> holiday -> blocked hour.
        Returns on first restriction found.

        Args:
            now: Current time (injectable for testing).

        Returns:
            TimeFilterResult indicating whether trading is allowed.
        """
        now = now or datetime.now(timezone.utc)

        # Check weekend
        if self.block_weekends and self.is_weekend(now):
            reason = (
                f"Weekend trading blocked "
                f"({now.strftime('%A')})"
            )
            logger.info(
                "time_filter_weekend_blocked",
                day=now.strftime("%A"),
            )
            return TimeFilterResult(
                is_tradeable=False,
                reason=reason,
                filter_name=self.FILTER_NAME,
                current_time=now,
            )

        # Check holiday
        if self.is_holiday(now):
            reason = (
                f"Holiday trading blocked "
                f"({now.date().isoformat()})"
            )
            logger.info(
                "time_filter_holiday_blocked",
                date=now.date().isoformat(),
            )
            return TimeFilterResult(
                is_tradeable=False,
                reason=reason,
                filter_name=self.FILTER_NAME,
                current_time=now,
            )

        # Check blocked hours
        if self.is_blocked_hour(now):
            reason = (
                f"Blocked hour {now.hour:02d}:00 UTC"
            )
            logger.info(
                "time_filter_hour_blocked",
                hour=now.hour,
            )
            return TimeFilterResult(
                is_tradeable=False,
                reason=reason,
                filter_name=self.FILTER_NAME,
                current_time=now,
            )

        return TimeFilterResult(
            is_tradeable=True,
            reason="",
            filter_name=self.FILTER_NAME,
            current_time=now,
        )

    def is_weekend(self, now: datetime | None = None) -> bool:
        """Check if the given time falls on a weekend.

        Args:
            now: Time to check (defaults to current UTC time).

        Returns:
            True if Saturday (5) or Sunday (6).
        """
        now = now or datetime.now(timezone.utc)
        return now.weekday() >= 5

    def is_holiday(self, now: datetime | None = None) -> bool:
        """Check if the given time falls on a configured holiday.

        Args:
            now: Time to check (defaults to current UTC time).

        Returns:
            True if date matches any holiday.
        """
        now = now or datetime.now(timezone.utc)
        return now.date() in self.holidays

    def is_blocked_hour(self, now: datetime | None = None) -> bool:
        """Check if the given time falls in a blocked hour.

        Args:
            now: Time to check (defaults to current UTC time).

        Returns:
            True if current UTC hour is in blocked_hours.
        """
        now = now or datetime.now(timezone.utc)
        return now.hour in self.blocked_hours
