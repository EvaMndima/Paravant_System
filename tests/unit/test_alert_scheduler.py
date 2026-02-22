"""Unit tests for AlertScheduler timing helpers (PRD §8.5-8.6).

Tests the module-level timing helper functions in
src/core/alerting/scheduler.py without requiring a running event loop
or live Telegram/DataStore connections.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.alerting.scheduler import (
    _seconds_until_sunday_midnight,
    _seconds_until_utc_midnight,
)


# ---------------------------------------------------------------------------
# _seconds_until_utc_midnight
# ---------------------------------------------------------------------------


class TestSecondsUntilUtcMidnight:
    def test_returns_positive_float(self) -> None:
        """Result is always a positive float."""
        result = _seconds_until_utc_midnight()
        assert isinstance(result, float)
        assert result > 0

    def test_maximum_is_one_day(self) -> None:
        """Can never be more than 86400 seconds (one full day)."""
        result = _seconds_until_utc_midnight()
        assert result <= 86_400.0

    def test_minimum_is_one_second(self) -> None:
        """Floor is 1.0 second to prevent tight loops at exact midnight."""
        result = _seconds_until_utc_midnight()
        assert result >= 1.0

    def test_result_is_sensible(self) -> None:
        """Cross-check against manual calculation."""
        now = datetime.now(timezone.utc)
        from datetime import timedelta
        tomorrow_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        expected = (tomorrow_midnight - now).total_seconds()
        result = _seconds_until_utc_midnight()
        # Allow 2 seconds of slack for test execution time
        assert abs(result - expected) < 2.0

    def test_called_twice_decreases(self) -> None:
        """Two successive calls should yield a slightly decreasing value."""
        import time
        first = _seconds_until_utc_midnight()
        time.sleep(0.01)
        second = _seconds_until_utc_midnight()
        # second call should be very slightly less (or at worst equal due to 1s floor)
        assert second <= first + 0.1  # allow tiny float imprecision


# ---------------------------------------------------------------------------
# _seconds_until_sunday_midnight
# ---------------------------------------------------------------------------


class TestSecondsUntilSundayMidnight:
    def test_returns_positive_float(self) -> None:
        """Result is always a positive float."""
        result = _seconds_until_sunday_midnight()
        assert isinstance(result, float)
        assert result > 0

    def test_minimum_is_one_second(self) -> None:
        """Floor is 1.0 second."""
        result = _seconds_until_sunday_midnight()
        assert result >= 1.0

    def test_maximum_is_seven_days(self) -> None:
        """Can never be more than 7 days = 604800 seconds."""
        result = _seconds_until_sunday_midnight()
        assert result <= 7 * 86_400.0

    def test_non_sunday_is_less_than_seven_days(self) -> None:
        """On any non-Sunday, result should be < 7 days."""
        now = datetime.now(timezone.utc)
        result = _seconds_until_sunday_midnight()
        if now.weekday() != 6:  # not Sunday
            assert result < 7 * 86_400.0

    def test_result_is_at_least_one_second_on_sunday(self) -> None:
        """Even on Sunday after midnight, result stays >= 1 second."""
        result = _seconds_until_sunday_midnight()
        assert result >= 1.0

    def test_result_is_sensible_against_manual_calc(self) -> None:
        """Cross-check against a manual weekday calculation."""
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0:
            # Today is Sunday; check if midnight has already passed
            midnight_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if now >= midnight_today:
                days_until_sunday = 7
            else:
                days_until_sunday = 0

        target = (now + timedelta(days=days_until_sunday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        expected = max((target - now).total_seconds(), 1.0)
        result = _seconds_until_sunday_midnight()
        # Allow 2 seconds of slack for test execution time
        assert abs(result - expected) < 2.0


# ---------------------------------------------------------------------------
# AlertScheduler lifecycle (smoke tests — no real event loop needed)
# ---------------------------------------------------------------------------


class TestAlertSchedulerInit:
    def test_instantiation_does_not_raise(self) -> None:
        """AlertScheduler can be constructed with mock dependencies."""
        from unittest.mock import MagicMock

        from src.core.alerting.scheduler import AlertScheduler

        manager = MagicMock()
        store = MagicMock()
        scheduler = AlertScheduler(alert_manager=manager, data_store=store)
        assert scheduler._tasks == []

    def test_stop_on_fresh_scheduler_is_safe(self) -> None:
        """Calling stop() before start() should not raise."""
        import asyncio
        from unittest.mock import MagicMock

        from src.core.alerting.scheduler import AlertScheduler

        manager = MagicMock()
        store = MagicMock()
        scheduler = AlertScheduler(alert_manager=manager, data_store=store)

        async def _run() -> None:
            await scheduler.stop()

        asyncio.run(_run())
        assert scheduler._tasks == []
