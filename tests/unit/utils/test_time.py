"""Unit tests for time utilities."""
from datetime import datetime, date, time, timedelta, timezone
from src.utils.time import (
    utc_now, utc_today, unix_timestamp_now,
    unix_timestamp_from_datetime, datetime_from_unix_timestamp,
    format_datetime, format_date, parse_datetime,
    is_market_open, is_weekend,
    time_until, seconds_until, humanize_timedelta,
    get_trading_day_start, get_trading_day_end
)

class TestTimeCalculations:
    """Test time calculation functions."""

    def test_utc_now_is_timezone_aware(self):
        """utc_now() returns a timezone-aware datetime in UTC."""
        dt = utc_now()
        assert dt.tzinfo == timezone.utc
        # Sanity check: shouldn't be too far from system time
        sys_now = datetime.now(timezone.utc)
        assert abs((sys_now - dt).total_seconds()) < 5

    def test_utc_today_returns_date(self):
        """utc_today() returns a date object."""
        d = utc_today()
        assert isinstance(d, date)
        assert d == datetime.now(timezone.utc).date()

    def test_unix_timestamp_conversions(self):
        """Test roundtrip conversion between datetime and timestamp."""
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        ts = unix_timestamp_from_datetime(dt)
        
        # 1672574400000
        assert ts == 1672574400000
        
        dt_back = datetime_from_unix_timestamp(ts)
        assert dt_back == dt

    def test_unix_timestamp_from_naive_datetime(self):
        """Naive datetime is assumed to be UTC."""
        dt_naive = datetime(2023, 1, 1, 12, 0, 0)
        ts = unix_timestamp_from_datetime(dt_naive)
        assert ts == 1672574400000
        
    def test_unix_timestamp_now(self):
        """unix_timestamp_now() returns valid int ms timestamp."""
        ts = unix_timestamp_now()
        assert isinstance(ts, int)
        assert ts > 1672574400000  # > Jan 1 2023

    def test_format_datetime(self):
        """Test datetime formatting."""
        dt = datetime(2023, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        assert format_datetime(dt) == "2023-01-01 12:30:45 UTC"
        assert format_datetime(dt, "%H:%M") == "12:30"

    def test_format_date(self):
        """Test date formatting."""
        d = date(2023, 1, 1)
        assert format_date(d) == "2023-01-01"
        assert format_date(d, "%d/%m/%Y") == "01/01/2023"

    def test_parse_datetime(self):
        """Test datetime parsing."""
        dt = parse_datetime("2023-01-01 12:30:45")
        assert dt.year == 2023
        assert dt.month == 1
        assert dt.hour == 12
        assert dt.tzinfo == timezone.utc

    def test_market_status(self):
        """Test market open/close logic."""
        # Crypto is 24/7
        assert is_market_open() is True
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert is_market_open(dt) is True

    def test_is_weekend(self):
        """Test weekend detection."""
        # Jan 1 2023 was a Sunday
        sunday = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert is_weekend(sunday) is True
        
        # Jan 2 2023 was a Monday
        monday = datetime(2023, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        assert is_weekend(monday) is False

        # Test default (now) - smoke test only as it depends on run time
        is_weekend() 

    def test_time_until_and_seconds_until(self):
        """Test duration calculations."""
        now = utc_now()
        future = now + timedelta(seconds=60)
        
        # Test time_until
        diff = time_until(future)
        assert 59 <= diff.total_seconds() <= 60
        
        # Test seconds_until
        secs = seconds_until(future)
        assert 59 <= secs <= 60
        
        # Test past
        past = now - timedelta(seconds=60)
        assert seconds_until(past) <= -60

    def test_humanize_timedelta(self):
        """Test human readable durations."""
        assert humanize_timedelta(timedelta(seconds=45)) == "45s"
        assert humanize_timedelta(timedelta(minutes=2, seconds=30)) == "2m 30s"
        assert humanize_timedelta(timedelta(hours=1)) == "1h"
        assert humanize_timedelta(timedelta(hours=25)) == "1d 1h"
        assert humanize_timedelta(timedelta(days=2)) == "2d"
        
        # Zero/Negative
        assert humanize_timedelta(timedelta(seconds=0)) == "0s"
        assert humanize_timedelta(timedelta(seconds=-1)) == "expired"

    def test_trading_day_boundaries(self):
        """Test day start/end calculations."""
        dt = datetime(2023, 1, 1, 15, 30, 0, tzinfo=timezone.utc)
        
        start = get_trading_day_start(dt)
        assert start == datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        end = get_trading_day_end(dt)
        # Microsecond precision check
        assert end.year == 2023
        assert end.hour == 23
        assert end.minute == 59
        assert end.second == 59
        assert end.microsecond == 999999

        # Test defaults (now)
        start_now = get_trading_day_start()
        end_now = get_trading_day_end()
        assert start_now.date() == utc_today()
        assert end_now.date() == utc_today()
