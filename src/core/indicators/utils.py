"""Utility functions for technical indicators.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage

Common helper functions for indicator calculations and analysis:
- Crossover detection (bullish/bearish crosses)
- Slope calculation (trend strength)
- Rising/falling detection (momentum)
- Highest/lowest values (support/resistance)

These utilities are used across multiple indicators and strategies.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def calculate_slope(values: NDArray[np.float64], lookback: int = 5) -> float:
    """Calculate linear regression slope over lookback period.

    Measures the rate of change (trend strength) of an indicator or price.
    Positive slope = uptrend, negative = downtrend.

    Args:
        values: Array of indicator values.
        lookback: Number of periods for slope calculation (default 5).

    Returns:
        Slope (change per bar). Units match input values.

    Raises:
        ValueError: If insufficient data or all values are NaN.

    Example:
        >>> ema_values = ema.calculate(series).values
        >>> slope = calculate_slope(ema_values, lookback=10)
        >>> if slope > 0:
        ...     print(f"Uptrend: +{slope:.2f} per bar")
    """
    if lookback < 2:
        raise ValueError(f"Lookback must be >= 2, got {lookback}")

    # Find valid (non-NaN) values
    valid_indices = np.where(~np.isnan(values))[0]

    if len(valid_indices) < lookback:
        raise ValueError(
            f"Need at least {lookback} valid values for slope, "
            f"got {len(valid_indices)}"
        )

    # Get last 'lookback' valid values
    last_valid_idx = valid_indices[-1]
    start_idx = max(0, last_valid_idx - lookback + 1)
    window = values[start_idx : last_valid_idx + 1]

    # Remove any remaining NaN values
    window = window[~np.isnan(window)]

    if len(window) < 2:
        raise ValueError("Insufficient non-NaN values in window for slope")

    # Use numpy polyfit for linear regression (degree=1)
    x = np.arange(len(window))
    slope, _ = np.polyfit(x, window, deg=1)

    return float(slope)


def calculate_normalized_slope(
    values: NDArray[np.float64], lookback: int = 5
) -> float:
    """Calculate slope normalized as percentage of current value.

    Normalizes slope by current value to compare across different scales.
    Useful for comparing trend strength across different assets or indicators.

    Args:
        values: Array of indicator values.
        lookback: Number of periods for slope calculation (default 5).

    Returns:
        Normalized slope as percentage (e.g., 0.5 = 0.5% increase per bar).

    Raises:
        ValueError: If insufficient data or current value is zero.

    Example:
        >>> rsi_values = rsi.calculate(series).values
        >>> norm_slope = calculate_normalized_slope(rsi_values, lookback=5)
        >>> print(f"RSI changing by {norm_slope:.2f}% per bar")
    """
    slope = calculate_slope(values, lookback)

    # Find last valid value for normalization
    valid_indices = np.where(~np.isnan(values))[0]

    if len(valid_indices) == 0:
        raise ValueError("No valid values for normalization")

    current_value = values[valid_indices[-1]]

    if current_value == 0:
        raise ValueError("Cannot normalize: current value is zero")

    # Return slope as percentage of current value
    return float((slope / current_value) * 100.0)


def is_rising(values: NDArray[np.float64], periods: int = 3) -> bool:
    """Check if values are consistently rising over last N periods.

    All of the last N valid values must be higher than their predecessor.

    Args:
        values: Array of indicator values.
        periods: Number of periods to check (default 3).

    Returns:
        True if all last N values are rising.

    Raises:
        ValueError: If insufficient valid values.

    Example:
        >>> macd_hist = macd.calculate(series).histogram
        >>> if is_rising(macd_hist, periods=3):
        ...     print("Momentum accelerating for 3 bars")
    """
    if periods < 2:
        raise ValueError(f"Periods must be >= 2, got {periods}")

    # Find valid values
    valid_indices = np.where(~np.isnan(values))[0]

    if len(valid_indices) < periods:
        raise ValueError(
            f"Need at least {periods} valid values, got {len(valid_indices)}"
        )

    # Get last 'periods' valid values
    last_values = values[valid_indices[-(periods):]]

    # Check if each value > previous value
    for i in range(1, len(last_values)):
        if last_values[i] <= last_values[i - 1]:
            return False

    return True


def is_falling(values: NDArray[np.float64], periods: int = 3) -> bool:
    """Check if values are consistently falling over last N periods.

    All of the last N valid values must be lower than their predecessor.

    Args:
        values: Array of indicator values.
        periods: Number of periods to check (default 3).

    Returns:
        True if all last N values are falling.

    Raises:
        ValueError: If insufficient valid values.

    Example:
        >>> adx_values = adx.calculate(series).adx
        >>> if is_falling(adx_values, periods=3):
        ...     print("Trend weakening for 3 bars")
    """
    if periods < 2:
        raise ValueError(f"Periods must be >= 2, got {periods}")

    # Find valid values
    valid_indices = np.where(~np.isnan(values))[0]

    if len(valid_indices) < periods:
        raise ValueError(
            f"Need at least {periods} valid values, got {len(valid_indices)}"
        )

    # Get last 'periods' valid values
    last_values = values[valid_indices[-(periods):]]

    # Check if each value < previous value
    for i in range(1, len(last_values)):
        if last_values[i] >= last_values[i - 1]:
            return False

    return True


def crossover(
    fast: NDArray[np.float64], slow: NDArray[np.float64]
) -> bool:
    """Check if fast just crossed above slow (bullish crossover).

    Crossover occurs when:
    - Previous: fast <= slow
    - Current: fast > slow

    Args:
        fast: Fast-moving array (e.g., short EMA, MACD line).
        slow: Slow-moving array (e.g., long EMA, signal line).

    Returns:
        True if fast just crossed above slow in the last bar.

    Raises:
        ValueError: If arrays have different lengths or insufficient values.

    Example:
        >>> ema_fast = EMA(12).calculate(series).values
        >>> ema_slow = EMA(26).calculate(series).values
        >>> if crossover(ema_fast, ema_slow):
        ...     print("Golden cross: bullish signal")
    """
    if len(fast) != len(slow):
        raise ValueError(f"Arrays must have same length: {len(fast)} != {len(slow)}")

    # Find indices where both are valid
    valid_mask = ~np.isnan(fast) & ~np.isnan(slow)
    valid_indices = np.where(valid_mask)[0]

    if len(valid_indices) < 2:
        raise ValueError("Need at least 2 valid pairs for crossover detection")

    # Get last two valid indices
    curr_idx = valid_indices[-1]
    prev_idx = valid_indices[-2]

    # Check crossover: was below or equal, now above
    was_below_or_equal = fast[prev_idx] <= slow[prev_idx]
    is_above = fast[curr_idx] > slow[curr_idx]

    return bool(was_below_or_equal and is_above)


def crossunder(
    fast: NDArray[np.float64], slow: NDArray[np.float64]
) -> bool:
    """Check if fast just crossed below slow (bearish crossover).

    Crossunder occurs when:
    - Previous: fast >= slow
    - Current: fast < slow

    Args:
        fast: Fast-moving array (e.g., short EMA, MACD line).
        slow: Slow-moving array (e.g., long EMA, signal line).

    Returns:
        True if fast just crossed below slow in the last bar.

    Raises:
        ValueError: If arrays have different lengths or insufficient values.

    Example:
        >>> ema_fast = EMA(12).calculate(series).values
        >>> ema_slow = EMA(26).calculate(series).values
        >>> if crossunder(ema_fast, ema_slow):
        ...     print("Death cross: bearish signal")
    """
    if len(fast) != len(slow):
        raise ValueError(f"Arrays must have same length: {len(fast)} != {len(slow)}")

    # Find indices where both are valid
    valid_mask = ~np.isnan(fast) & ~np.isnan(slow)
    valid_indices = np.where(valid_mask)[0]

    if len(valid_indices) < 2:
        raise ValueError("Need at least 2 valid pairs for crossunder detection")

    # Get last two valid indices
    curr_idx = valid_indices[-1]
    prev_idx = valid_indices[-2]

    # Check crossunder: was above or equal, now below
    was_above_or_equal = fast[prev_idx] >= slow[prev_idx]
    is_below = fast[curr_idx] < slow[curr_idx]

    return bool(was_above_or_equal and is_below)


def highest(values: NDArray[np.float64], period: int) -> float:
    """Get highest value over last N periods.

    Args:
        values: Array of values.
        period: Number of periods to look back.

    Returns:
        Highest value in last N valid periods.

    Raises:
        ValueError: If insufficient valid values.

    Example:
        >>> closes = series.closes
        >>> resistance = highest(closes, period=20)
        >>> print(f"20-bar high: {resistance:.2f}")
    """
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}")

    # Find valid values
    valid_indices = np.where(~np.isnan(values))[0]

    if len(valid_indices) < period:
        raise ValueError(
            f"Need at least {period} valid values, got {len(valid_indices)}"
        )

    # Get last 'period' valid values
    last_values = values[valid_indices[-(period):]]

    return float(np.max(last_values))


def lowest(values: NDArray[np.float64], period: int) -> float:
    """Get lowest value over last N periods.

    Args:
        values: Array of values.
        period: Number of periods to look back.

    Returns:
        Lowest value in last N valid periods.

    Raises:
        ValueError: If insufficient valid values.

    Example:
        >>> closes = series.closes
        >>> support = lowest(closes, period=20)
        >>> print(f"20-bar low: {support:.2f}")
    """
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}")

    # Find valid values
    valid_indices = np.where(~np.isnan(values))[0]

    if len(valid_indices) < period:
        raise ValueError(
            f"Need at least {period} valid values, got {len(valid_indices)}"
        )

    # Get last 'period' valid values
    last_values = values[valid_indices[-(period):]]

    return float(np.min(last_values))
