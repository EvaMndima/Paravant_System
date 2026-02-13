"""Tests for volatility analyzer, time filter, and event filter.

Covers:
- VolatilityRegime enum values
- VolatilityResult validation and immutability
- VolatilityAnalyzer regime classification and cooldown
- TimeFilterResult immutability
- WeekendHolidayFilter weekend/holiday/hour blocking
- TradingEvent validation
- EventFilterResult immutability
- EventFilter blocking windows and event management

Target: >90% coverage for volatility.py, time_filter.py, event_filter.py
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from src.core.risk.event_filter import (
    EventFilter,
    EventFilterResult,
    TradingEvent,
)
from src.core.risk.time_filter import TimeFilterResult, WeekendHolidayFilter
from src.core.risk.volatility import (
    VolatilityAnalyzer,
    VolatilityRegime,
    VolatilityResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fixed_now() -> datetime:
    """Fixed datetime for deterministic tests (Wednesday)."""
    return datetime(2026, 2, 11, 14, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def saturday() -> datetime:
    """A Saturday datetime."""
    return datetime(2026, 2, 14, 14, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sunday() -> datetime:
    """A Sunday datetime."""
    return datetime(2026, 2, 15, 14, 0, 0, tzinfo=timezone.utc)


# ===========================================================================
# VolatilityRegime tests
# ===========================================================================


class TestVolatilityRegime:
    """Tests for VolatilityRegime enum."""

    def test_enum_values(self) -> None:
        """All four regime values exist."""
        assert VolatilityRegime.LOW == "low"
        assert VolatilityRegime.NORMAL == "normal"
        assert VolatilityRegime.HIGH == "high"
        assert VolatilityRegime.EXTREME == "extreme"

    def test_string_values(self) -> None:
        """Regime values are strings."""
        for regime in VolatilityRegime:
            assert isinstance(regime.value, str)


# ===========================================================================
# VolatilityResult tests
# ===========================================================================


class TestVolatilityResult:
    """Tests for VolatilityResult frozen dataclass."""

    def test_creation(self) -> None:
        """Result can be created with valid data."""
        result = VolatilityResult(
            regime=VolatilityRegime.NORMAL,
            current_volatility=2.0,
            threshold_used=1.0,
            is_tradeable=True,
            position_multiplier=1.0,
        )
        assert result.regime == VolatilityRegime.NORMAL
        assert result.is_tradeable is True

    def test_frozen(self) -> None:
        """Result fields cannot be modified."""
        result = VolatilityResult(
            regime=VolatilityRegime.LOW,
            current_volatility=0.5,
            threshold_used=1.0,
            is_tradeable=True,
            position_multiplier=1.0,
        )
        with pytest.raises(AttributeError):
            result.is_tradeable = False  # type: ignore[misc]

    def test_validation_rejects_nan(self) -> None:
        """Result rejects NaN current_volatility."""
        with pytest.raises(ValueError, match="current_volatility cannot be NaN"):
            VolatilityResult(
                regime=VolatilityRegime.LOW,
                current_volatility=float("nan"),
                threshold_used=1.0,
                is_tradeable=True,
                position_multiplier=1.0,
            )

    def test_validation_rejects_inf(self) -> None:
        """Result rejects Infinity current_volatility."""
        with pytest.raises(
            ValueError, match="current_volatility cannot be Infinity"
        ):
            VolatilityResult(
                regime=VolatilityRegime.LOW,
                current_volatility=float("inf"),
                threshold_used=1.0,
                is_tradeable=True,
                position_multiplier=1.0,
            )

    def test_validation_rejects_nan_multiplier(self) -> None:
        """Result rejects NaN position_multiplier."""
        with pytest.raises(
            ValueError, match="position_multiplier cannot be NaN"
        ):
            VolatilityResult(
                regime=VolatilityRegime.LOW,
                current_volatility=0.5,
                threshold_used=1.0,
                is_tradeable=True,
                position_multiplier=float("nan"),
            )


# ===========================================================================
# VolatilityAnalyzer tests
# ===========================================================================


class TestVolatilityAnalyzer:
    """Tests for VolatilityAnalyzer."""

    def test_classify_low_volatility(self, fixed_now: datetime) -> None:
        """Volatility below normal_threshold is LOW regime."""
        analyzer = VolatilityAnalyzer()
        result = analyzer.analyze(0.5, now=fixed_now)
        assert result.regime == VolatilityRegime.LOW
        assert result.is_tradeable is True
        assert result.position_multiplier == 1.0

    def test_classify_normal_volatility(self, fixed_now: datetime) -> None:
        """Volatility between normal and high is NORMAL regime."""
        analyzer = VolatilityAnalyzer()
        result = analyzer.analyze(2.0, now=fixed_now)
        assert result.regime == VolatilityRegime.NORMAL
        assert result.is_tradeable is True
        assert result.position_multiplier == 1.0

    def test_classify_high_volatility(self, fixed_now: datetime) -> None:
        """Volatility between high and extreme is HIGH regime."""
        analyzer = VolatilityAnalyzer()
        result = analyzer.analyze(4.0, now=fixed_now)
        assert result.regime == VolatilityRegime.HIGH
        assert result.is_tradeable is True
        assert result.position_multiplier == 0.5

    def test_classify_extreme_volatility(self, fixed_now: datetime) -> None:
        """Volatility above extreme threshold is EXTREME regime."""
        analyzer = VolatilityAnalyzer()
        result = analyzer.analyze(6.0, now=fixed_now)
        assert result.regime == VolatilityRegime.EXTREME
        assert result.is_tradeable is False
        assert result.position_multiplier == 0.0

    def test_position_multiplier_normal(self, fixed_now: datetime) -> None:
        """NORMAL regime has full position multiplier."""
        analyzer = VolatilityAnalyzer()
        result = analyzer.analyze(1.5, now=fixed_now)
        assert result.position_multiplier == 1.0

    def test_position_multiplier_high_reduces(
        self, fixed_now: datetime
    ) -> None:
        """HIGH regime reduces position size to 50%."""
        analyzer = VolatilityAnalyzer()
        result = analyzer.analyze(3.5, now=fixed_now)
        assert result.position_multiplier == 0.5

    def test_position_multiplier_extreme_zero(
        self, fixed_now: datetime
    ) -> None:
        """EXTREME regime blocks all trading (multiplier=0)."""
        analyzer = VolatilityAnalyzer()
        result = analyzer.analyze(10.0, now=fixed_now)
        assert result.position_multiplier == 0.0

    def test_cooldown_after_extreme(self, fixed_now: datetime) -> None:
        """After EXTREME event, cooldown blocks trading."""
        analyzer = VolatilityAnalyzer(cooldown_minutes=30)

        # Trigger extreme
        analyzer.analyze(6.0, now=fixed_now)

        # 10 minutes later, volatility normalizes but cooldown active
        later = fixed_now + timedelta(minutes=10)
        result = analyzer.analyze(1.5, now=later)
        assert result.regime == VolatilityRegime.NORMAL
        assert result.is_tradeable is False  # Cooldown blocks it
        assert result.position_multiplier == 0.0

    def test_cooldown_expires(self, fixed_now: datetime) -> None:
        """After cooldown expires, trading resumes."""
        analyzer = VolatilityAnalyzer(cooldown_minutes=30)

        # Trigger extreme
        analyzer.analyze(6.0, now=fixed_now)

        # 31 minutes later, cooldown expired
        after_cooldown = fixed_now + timedelta(minutes=31)
        result = analyzer.analyze(1.5, now=after_cooldown)
        assert result.regime == VolatilityRegime.NORMAL
        assert result.is_tradeable is True
        assert result.position_multiplier == 1.0

    def test_rejects_negative_volatility(self, fixed_now: datetime) -> None:
        """Negative volatility raises ValueError."""
        analyzer = VolatilityAnalyzer()
        with pytest.raises(ValueError, match="non-negative"):
            analyzer.analyze(-1.0, now=fixed_now)

    def test_rejects_nan_volatility(self, fixed_now: datetime) -> None:
        """NaN volatility raises ValueError."""
        analyzer = VolatilityAnalyzer()
        with pytest.raises(ValueError, match="NaN"):
            analyzer.analyze(float("nan"), now=fixed_now)

    def test_rejects_inf_volatility(self, fixed_now: datetime) -> None:
        """Infinity volatility raises ValueError."""
        analyzer = VolatilityAnalyzer()
        with pytest.raises(ValueError, match="Infinity"):
            analyzer.analyze(float("inf"), now=fixed_now)

    def test_invalid_threshold_order(self) -> None:
        """Thresholds must be in ascending order."""
        with pytest.raises(ValueError, match="ascending"):
            VolatilityAnalyzer(
                extreme_threshold=2.0,
                high_threshold=5.0,
                normal_threshold=1.0,
            )

    def test_is_in_cooldown_no_extreme(self, fixed_now: datetime) -> None:
        """is_in_cooldown returns False when no extreme event occurred."""
        analyzer = VolatilityAnalyzer()
        assert analyzer.is_in_cooldown(fixed_now) is False

    def test_zero_volatility(self, fixed_now: datetime) -> None:
        """Zero volatility is classified as LOW."""
        analyzer = VolatilityAnalyzer()
        result = analyzer.analyze(0.0, now=fixed_now)
        assert result.regime == VolatilityRegime.LOW
        assert result.is_tradeable is True

    def test_boundary_at_normal_threshold(
        self, fixed_now: datetime
    ) -> None:
        """Volatility exactly at normal_threshold is NORMAL."""
        analyzer = VolatilityAnalyzer(normal_threshold=1.0)
        result = analyzer.analyze(1.0, now=fixed_now)
        assert result.regime == VolatilityRegime.NORMAL


# ===========================================================================
# TimeFilterResult tests
# ===========================================================================


class TestTimeFilterResult:
    """Tests for TimeFilterResult frozen dataclass."""

    def test_creation(self, fixed_now: datetime) -> None:
        """Result can be created with valid data."""
        result = TimeFilterResult(
            is_tradeable=True,
            reason="",
            filter_name="weekend_holiday",
            current_time=fixed_now,
        )
        assert result.is_tradeable is True

    def test_frozen(self, fixed_now: datetime) -> None:
        """Result fields cannot be modified."""
        result = TimeFilterResult(
            is_tradeable=True,
            reason="",
            filter_name="test",
            current_time=fixed_now,
        )
        with pytest.raises(AttributeError):
            result.is_tradeable = False  # type: ignore[misc]


# ===========================================================================
# WeekendHolidayFilter tests
# ===========================================================================


class TestWeekendHolidayFilter:
    """Tests for WeekendHolidayFilter."""

    def test_weekday_is_tradeable(self, fixed_now: datetime) -> None:
        """Weekday trading is always allowed."""
        filt = WeekendHolidayFilter(block_weekends=True)
        result = filt.check(fixed_now)
        assert result.is_tradeable is True

    def test_weekend_blocked_when_enabled(
        self, saturday: datetime
    ) -> None:
        """Weekend trading blocked when block_weekends=True."""
        filt = WeekendHolidayFilter(block_weekends=True)
        result = filt.check(saturday)
        assert result.is_tradeable is False
        assert "Weekend" in result.reason

    def test_weekend_allowed_when_disabled(
        self, saturday: datetime
    ) -> None:
        """Weekend trading allowed by default (block_weekends=False)."""
        filt = WeekendHolidayFilter(block_weekends=False)
        result = filt.check(saturday)
        assert result.is_tradeable is True

    def test_holiday_blocked(self, fixed_now: datetime) -> None:
        """Trading blocked on configured holidays."""
        filt = WeekendHolidayFilter(
            holidays=(date(2026, 2, 11),)  # Same as fixed_now
        )
        result = filt.check(fixed_now)
        assert result.is_tradeable is False
        assert "Holiday" in result.reason

    def test_blocked_hour(self) -> None:
        """Trading blocked during configured hours."""
        # 3 AM UTC
        time_3am = datetime(2026, 2, 11, 3, 0, 0, tzinfo=timezone.utc)
        filt = WeekendHolidayFilter(blocked_hours=(2, 3, 4))
        result = filt.check(time_3am)
        assert result.is_tradeable is False
        assert "Blocked hour" in result.reason

    def test_all_clear(self, fixed_now: datetime) -> None:
        """No restrictions returns tradeable."""
        filt = WeekendHolidayFilter()
        result = filt.check(fixed_now)
        assert result.is_tradeable is True
        assert result.reason == ""

    def test_is_weekend_saturday(self, saturday: datetime) -> None:
        """Saturday is detected as weekend."""
        filt = WeekendHolidayFilter()
        assert filt.is_weekend(saturday) is True

    def test_is_weekend_sunday(self, sunday: datetime) -> None:
        """Sunday is detected as weekend."""
        filt = WeekendHolidayFilter()
        assert filt.is_weekend(sunday) is True

    def test_is_weekend_weekday(self, fixed_now: datetime) -> None:
        """Weekday is not weekend."""
        filt = WeekendHolidayFilter()
        assert filt.is_weekend(fixed_now) is False

    def test_is_holiday_match(self) -> None:
        """Date matching a holiday returns True."""
        filt = WeekendHolidayFilter(
            holidays=(date(2026, 12, 25),)
        )
        xmas = datetime(2026, 12, 25, 10, 0, 0, tzinfo=timezone.utc)
        assert filt.is_holiday(xmas) is True

    def test_is_holiday_no_match(self, fixed_now: datetime) -> None:
        """Date not matching any holiday returns False."""
        filt = WeekendHolidayFilter(
            holidays=(date(2026, 12, 25),)
        )
        assert filt.is_holiday(fixed_now) is False

    def test_is_blocked_hour_match(self) -> None:
        """Hour matching blocked_hours returns True."""
        filt = WeekendHolidayFilter(blocked_hours=(3, 4))
        time_3am = datetime(2026, 2, 11, 3, 30, 0, tzinfo=timezone.utc)
        assert filt.is_blocked_hour(time_3am) is True

    def test_is_blocked_hour_no_match(self, fixed_now: datetime) -> None:
        """Hour not matching blocked_hours returns False."""
        filt = WeekendHolidayFilter(blocked_hours=(3, 4))
        assert filt.is_blocked_hour(fixed_now) is False

    def test_invalid_blocked_hour_raises(self) -> None:
        """Hour values outside 0-23 raise ValueError."""
        with pytest.raises(ValueError, match="0-23"):
            WeekendHolidayFilter(blocked_hours=(25,))


# ===========================================================================
# TradingEvent tests
# ===========================================================================


class TestTradingEvent:
    """Tests for TradingEvent frozen dataclass."""

    def test_creation(self, fixed_now: datetime) -> None:
        """Event can be created with valid data."""
        event = TradingEvent(
            name="FOMC Rate Decision",
            event_time=fixed_now,
        )
        assert event.name == "FOMC Rate Decision"
        assert event.block_before_minutes == 30
        assert event.block_after_minutes == 30

    def test_frozen(self, fixed_now: datetime) -> None:
        """Event fields cannot be modified."""
        event = TradingEvent(name="CPI", event_time=fixed_now)
        with pytest.raises(AttributeError):
            event.name = "Other"  # type: ignore[misc]

    def test_requires_timezone_aware_datetime(self) -> None:
        """Naive datetime raises ValueError."""
        naive = datetime(2026, 2, 11, 14, 0, 0)  # No tzinfo
        with pytest.raises(ValueError, match="timezone-aware"):
            TradingEvent(name="Test", event_time=naive)

    def test_empty_name_raises(self, fixed_now: datetime) -> None:
        """Empty name raises ValueError."""
        with pytest.raises(ValueError, match="name is required"):
            TradingEvent(name="", event_time=fixed_now)

    def test_negative_block_before_raises(
        self, fixed_now: datetime
    ) -> None:
        """Negative block_before_minutes raises ValueError."""
        with pytest.raises(ValueError, match="block_before_minutes"):
            TradingEvent(
                name="Test",
                event_time=fixed_now,
                block_before_minutes=-1,
            )

    def test_negative_block_after_raises(
        self, fixed_now: datetime
    ) -> None:
        """Negative block_after_minutes raises ValueError."""
        with pytest.raises(ValueError, match="block_after_minutes"):
            TradingEvent(
                name="Test",
                event_time=fixed_now,
                block_after_minutes=-1,
            )

    def test_invalid_severity_raises(self, fixed_now: datetime) -> None:
        """Invalid severity raises ValueError."""
        with pytest.raises(ValueError, match="severity"):
            TradingEvent(
                name="Test",
                event_time=fixed_now,
                severity="critical",
            )


# ===========================================================================
# EventFilterResult tests
# ===========================================================================


class TestEventFilterResult:
    """Tests for EventFilterResult frozen dataclass."""

    def test_creation(self) -> None:
        """Result can be created with valid data."""
        result = EventFilterResult(
            is_tradeable=True,
            blocking_event=None,
            reason="",
            filter_name="event",
        )
        assert result.is_tradeable is True

    def test_frozen(self) -> None:
        """Result fields cannot be modified."""
        result = EventFilterResult(
            is_tradeable=True,
            blocking_event=None,
            reason="",
            filter_name="event",
        )
        with pytest.raises(AttributeError):
            result.is_tradeable = False  # type: ignore[misc]


# ===========================================================================
# EventFilter tests
# ===========================================================================


class TestEventFilter:
    """Tests for EventFilter."""

    def test_no_events_is_tradeable(self, fixed_now: datetime) -> None:
        """Trading allowed when no events registered."""
        filt = EventFilter()
        result = filt.check(fixed_now)
        assert result.is_tradeable is True

    def test_blocked_before_event(self, fixed_now: datetime) -> None:
        """Trading blocked in pre-event window."""
        event_time = fixed_now + timedelta(minutes=15)
        event = TradingEvent(
            name="FOMC",
            event_time=event_time,
            block_before_minutes=30,
            block_after_minutes=30,
        )
        filt = EventFilter(events=(event,))
        result = filt.check(fixed_now)
        assert result.is_tradeable is False
        assert result.blocking_event == event
        assert "before" in result.reason

    def test_blocked_after_event(self, fixed_now: datetime) -> None:
        """Trading blocked in post-event window."""
        event_time = fixed_now - timedelta(minutes=15)
        event = TradingEvent(
            name="CPI Release",
            event_time=event_time,
            block_before_minutes=30,
            block_after_minutes=30,
        )
        filt = EventFilter(events=(event,))
        result = filt.check(fixed_now)
        assert result.is_tradeable is False
        assert "after" in result.reason

    def test_tradeable_outside_window(self, fixed_now: datetime) -> None:
        """Trading allowed outside blocking window."""
        event_time = fixed_now + timedelta(hours=2)
        event = TradingEvent(
            name="FOMC",
            event_time=event_time,
            block_before_minutes=30,
            block_after_minutes=30,
        )
        filt = EventFilter(events=(event,))
        result = filt.check(fixed_now)
        assert result.is_tradeable is True

    def test_add_event(self, fixed_now: datetime) -> None:
        """Events can be added dynamically."""
        filt = EventFilter()
        assert len(filt.events) == 0

        event = TradingEvent(name="Test", event_time=fixed_now)
        filt.add_event(event)
        assert len(filt.events) == 1

    def test_remove_expired_events(self, fixed_now: datetime) -> None:
        """Expired events are removed."""
        past_event = TradingEvent(
            name="Past",
            event_time=fixed_now - timedelta(hours=2),
            block_after_minutes=30,
        )
        future_event = TradingEvent(
            name="Future",
            event_time=fixed_now + timedelta(hours=2),
        )
        filt = EventFilter(events=(past_event, future_event))
        removed = filt.remove_expired_events(fixed_now)
        assert removed == 1
        assert len(filt.events) == 1
        assert filt.events[0].name == "Future"

    def test_get_upcoming_events(self, fixed_now: datetime) -> None:
        """Get events within specified time window."""
        soon = TradingEvent(
            name="Soon",
            event_time=fixed_now + timedelta(hours=1),
        )
        far = TradingEvent(
            name="Far",
            event_time=fixed_now + timedelta(hours=48),
        )
        filt = EventFilter(events=(soon, far))
        upcoming = filt.get_upcoming_events(hours=24, now=fixed_now)
        assert len(upcoming) == 1
        assert upcoming[0].name == "Soon"

    def test_get_upcoming_events_sorted(
        self, fixed_now: datetime
    ) -> None:
        """Upcoming events are sorted by time."""
        later = TradingEvent(
            name="Later",
            event_time=fixed_now + timedelta(hours=3),
        )
        sooner = TradingEvent(
            name="Sooner",
            event_time=fixed_now + timedelta(hours=1),
        )
        filt = EventFilter(events=(later, sooner))
        upcoming = filt.get_upcoming_events(hours=24, now=fixed_now)
        assert upcoming[0].name == "Sooner"
        assert upcoming[1].name == "Later"

    def test_events_property_returns_copy(
        self, fixed_now: datetime
    ) -> None:
        """events property returns a copy, not the internal list."""
        event = TradingEvent(name="Test", event_time=fixed_now)
        filt = EventFilter(events=(event,))
        returned = filt.events
        returned.clear()
        assert len(filt.events) == 1  # Internal unchanged

    def test_blocked_at_exact_event_time(
        self, fixed_now: datetime
    ) -> None:
        """Trading blocked at exact event time."""
        event = TradingEvent(
            name="Test",
            event_time=fixed_now,
            block_before_minutes=0,
            block_after_minutes=30,
        )
        filt = EventFilter(events=(event,))
        result = filt.check(fixed_now)
        assert result.is_tradeable is False
