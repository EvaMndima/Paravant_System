"""Time utilities for the PARAVANT Trading System.

This module provides timezone-aware datetime utilities for consistent
time handling across the application.
"""
from datetime import datetime, date, time, timedelta, timezone
import time as time_module


def utc_now() -> datetime:
    """
    Get current UTC time with timezone awareness.

    This is the standard way to get current time in the application.
    Always use this instead of datetime.utcnow() which is deprecated.

    Returns:
        Current UTC datetime with timezone information
    """
    return datetime.now(timezone.utc)


def utc_today() -> date:
    """
    Get current UTC date.

    Returns:
        Current date in UTC
    """
    return utc_now().date()


def unix_timestamp_now() -> int:
    """
    Get current Unix timestamp in milliseconds.

    This is useful for Binance API which uses millisecond timestamps.

    Returns:
        Current time as Unix timestamp in milliseconds
    """
    return int(utc_now().timestamp() * 1000)


def unix_timestamp_from_datetime(dt: datetime) -> int:
    """
    Convert datetime to Unix timestamp in milliseconds.

    Args:
        dt: Datetime to convert (timezone-aware or naive)

    Returns:
        Unix timestamp in milliseconds
    """
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def datetime_from_unix_timestamp(timestamp_ms: int) -> datetime:
    """
    Convert Unix timestamp (milliseconds) to timezone-aware datetime.

    Args:
        timestamp_ms: Unix timestamp in milliseconds

    Returns:
        Timezone-aware datetime in UTC
    """
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)


def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S UTC") -> str:
    """
    Format datetime as human-readable string.

    Args:
        dt: Datetime to format
        format: strftime format string

    Returns:
        Formatted datetime string
    """
    return dt.strftime(format)


def format_date(d: date, format: str = "%Y-%m-%d") -> str:
    """
    Format date as human-readable string.

    Args:
        d: Date to format
        format: strftime format string

    Returns:
        Formatted date string
    """
    return d.strftime(format)


def parse_datetime(date_string: str, format: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    Parse datetime string to timezone-aware datetime.

    Args:
        date_string: String representation of datetime
        format: strftime format string used to parse

    Returns:
        Timezone-aware datetime in UTC
    """
    dt = datetime.strptime(date_string, format)
    # Add UTC timezone if naive
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def is_market_open(
    dt: datetime | None = None,
    market_open_time: time = time(0, 0),
    market_close_time: time = time(23, 59, 59)
) -> bool:
    """
    Check if the market is open at a given time.

    For crypto markets (24/7), this always returns True.
    For traditional markets, implement specific logic.

    Args:
        dt: Datetime to check (default: current UTC time)
        market_open_time: Market opening time
        market_close_time: Market closing time

    Returns:
        True if market is open, False otherwise
    """
    # Crypto markets are 24/7
    return True


def is_weekend(dt: datetime | None = None) -> bool:
    """
    Check if a given datetime is on a weekend (Saturday or Sunday).

    Args:
        dt: Datetime to check (default: current UTC time)

    Returns:
        True if weekend, False otherwise
    """
    if dt is None:
        dt = utc_now()
    # Monday is 0, Sunday is 6
    return dt.weekday() >= 5


def time_until(target: datetime) -> timedelta:
    """
    Calculate time remaining until a target datetime.

    Args:
        target: Target datetime

    Returns:
        Timedelta representing time until target
    """
    now = utc_now()
    return target - now


def seconds_until(target: datetime) -> float:
    """
    Calculate seconds remaining until a target datetime.

    Args:
        target: Target datetime

    Returns:
        Seconds until target (negative if in past)
    """
    return time_until(target).total_seconds()


def humanize_timedelta(td: timedelta) -> str:
    """
    Convert timedelta to human-readable string.

    Args:
        td: Timedelta to humanize

    Returns:
        Human-readable string (e.g., "2h 30m", "5d 3h")
    """
    total_seconds = int(td.total_seconds())

    if total_seconds < 0:
        return "expired"

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 and days == 0:  # Don't show minutes if days are shown
        parts.append(f"{minutes}m")
    if seconds > 0 and days == 0 and hours == 0:  # Only show seconds for very short durations
        parts.append(f"{seconds}s")

    return " ".join(parts) if parts else "0s"


def sleep_until(target: datetime, check_interval: float = 1.0) -> None:
    """
    Sleep until a target datetime, waking periodically to check.

    Args:
        target: Target datetime to sleep until
        check_interval: How often to wake and check (seconds)
    """
    while True:
        remaining = seconds_until(target)
        if remaining <= 0:
            break

        # Sleep for the minimum of remaining time and check interval
        sleep_duration = min(remaining, check_interval)
        time_module.sleep(sleep_duration)


def get_trading_day_start(dt: datetime | None = None) -> datetime:
    """
    Get the start of the trading day (00:00 UTC).

    Args:
        dt: Reference datetime (default: current UTC time)

    Returns:
        Datetime at 00:00 UTC on the same day
    """
    if dt is None:
        dt = utc_now()
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def get_trading_day_end(dt: datetime | None = None) -> datetime:
    """
    Get the end of the trading day (23:59:59 UTC).

    Args:
        dt: Reference datetime (default: current UTC time)

    Returns:
        Datetime at 23:59:59 UTC on the same day
    """
    if dt is None:
        dt = utc_now()
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


