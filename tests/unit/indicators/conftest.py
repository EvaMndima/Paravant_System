"""Pytest fixtures for indicator tests.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage

Provides shared test fixtures for indicator testing:
- Sample OHLCV data (realistic patterns)
- TradingView reference values for validation
- Edge case test data (flat prices, gaps, volatility)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from src.data.market_data import OHLCV, OHLCVSeries


@pytest.fixture
def sample_ohlcv_data() -> list[OHLCV]:
    """Generate sample OHLCV data with realistic price action.

    Creates 100 candles with:
    - Uptrend (bars 0-30)
    - Ranging (bars 30-60)
    - Downtrend (bars 60-90)
    - Volatile (bars 90-100)

    This pattern allows testing indicators across different market conditions.

    Returns:
        List of 100 OHLCV candles.
    """
    # Seed random for deterministic test data across runs
    np.random.seed(42)

    candles: list[OHLCV] = []
    base_price = 40000.0
    base_volume = 100.0
    base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    for i in range(100):
        timestamp = base_time + timedelta(hours=i)

        # Uptrend (0-30): Price increases
        if i < 30:
            trend = i * 50
            close = base_price + trend
            open_price = close - 50
            # Ensure OHLCV validity: High >= max(Open, Close), Low <= min(Open, Close)
            high = max(open_price, close) + 100
            low = min(open_price, close) - 100

        # Ranging (30-60): Price oscillates
        elif i < 60:
            oscillation = np.sin((i - 30) * 0.3) * 200
            close = base_price + 1500 + oscillation
            open_price = base_price + 1500 + np.sin((i - 30) * 0.5) * 100
            # Ensure OHLCV validity
            high = max(open_price, close) + 150
            low = min(open_price, close) - 150

        # Downtrend (60-90): Price decreases
        elif i < 90:
            trend = (i - 60) * -40
            close = base_price + 1500 + trend
            open_price = close + 40
            # Ensure OHLCV validity
            high = max(open_price, close) + 80
            low = min(open_price, close) - 80

        # Volatile (90-100): Large swings
        else:
            volatility = np.random.uniform(-500, 500)
            close = base_price + 300 + volatility
            open_price = base_price + 300 + np.random.uniform(-300, 300)
            # Ensure OHLCV validity
            high = max(open_price, close) + np.random.uniform(200, 400)
            low = min(open_price, close) - np.random.uniform(200, 400)

        # Volume varies with volatility
        volume = base_volume * (1 + abs(np.random.normal(0, 0.3)))

        candle = OHLCV(
            timestamp=timestamp,
            open=float(open_price),
            high=float(high),
            low=float(low),
            close=float(close),
            volume=float(volume),
        )
        candles.append(candle)

    return candles


@pytest.fixture
def sample_ohlcv_series(sample_ohlcv_data: list[OHLCV]) -> OHLCVSeries:
    """Create OHLCVSeries from sample OHLCV data.

    Args:
        sample_ohlcv_data: List of OHLCV candles from fixture.

    Returns:
        OHLCVSeries instance for indicator calculations.
    """
    return OHLCVSeries(
        candles=sample_ohlcv_data,
        symbol="BTCUSDT",
        timeframe="1h",
    )


@pytest.fixture
def flat_price_series() -> OHLCVSeries:
    """Create OHLCV series with flat prices (all same).

    Edge case: Tests indicators when price doesn't move.

    Returns:
        OHLCVSeries with constant price = 50000.0
    """
    candles: list[OHLCV] = []
    base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    price = 50000.0
    volume = 100.0

    for i in range(50):
        timestamp = base_time + timedelta(hours=i)
        candle = OHLCV(
            timestamp=timestamp,
            open=price,
            high=price,
            low=price,
            close=price,
            volume=volume,
        )
        candles.append(candle)

    return OHLCVSeries(candles=candles, symbol="BTCUSDT", timeframe="1h")


@pytest.fixture
def gap_series() -> OHLCVSeries:
    """Create OHLCV series with price gaps.

    Edge case: Tests indicators when price gaps up/down.

    Returns:
        OHLCVSeries with several price gaps.
    """
    # Seed random for deterministic test data across runs
    np.random.seed(43)

    candles: list[OHLCV] = []
    base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    price = 40000.0

    for i in range(50):
        timestamp = base_time + timedelta(hours=i)

        # Create gaps at specific points
        if i == 10:
            price += 2000  # Gap up
        elif i == 25:
            price -= 1500  # Gap down
        elif i == 40:
            price += 1000  # Another gap up

        # Normal price movement
        close = price + np.random.uniform(-100, 100)
        open_price = price
        # Ensure OHLCV validity
        high = max(open_price, close) + abs(np.random.uniform(50, 150))
        low = min(open_price, close) - abs(np.random.uniform(50, 150))

        candle = OHLCV(
            timestamp=timestamp,
            open=float(open_price),
            high=float(high),
            low=float(low),
            close=float(close),
            volume=100.0,
        )
        candles.append(candle)

        price = close

    return OHLCVSeries(candles=candles, symbol="BTCUSDT", timeframe="1h")


@pytest.fixture
def volatile_series() -> OHLCVSeries:
    """Create OHLCV series with high volatility.

    Edge case: Tests indicators with large price swings.

    Returns:
        OHLCVSeries with extreme volatility.
    """
    # Seed random for deterministic test data across runs
    np.random.seed(44)

    candles: list[OHLCV] = []
    base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    price = 40000.0

    for i in range(50):
        timestamp = base_time + timedelta(hours=i)

        # Large random movements
        change = np.random.uniform(-2000, 2000)
        close = price + change
        open_price = price
        # Ensure OHLCV validity
        high = max(open_price, close) + abs(np.random.uniform(500, 1500))
        low = min(open_price, close) - abs(np.random.uniform(500, 1500))

        candle = OHLCV(
            timestamp=timestamp,
            open=float(open_price),
            high=float(high),
            low=float(low),
            close=float(close),
            volume=float(100.0 * (1 + abs(change) / 1000)),
        )
        candles.append(candle)

        price = close

    return OHLCVSeries(candles=candles, symbol="BTCUSDT", timeframe="1h")


@pytest.fixture
def minimal_series() -> OHLCVSeries:
    """Create minimal OHLCV series (15 candles).

    Edge case: Tests minimum data requirements for indicators.

    Returns:
        OHLCVSeries with only 15 candles.
    """
    candles: list[OHLCV] = []
    base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    base_price = 40000.0

    for i in range(15):
        timestamp = base_time + timedelta(hours=i)
        close = base_price + i * 100
        high = close + 50
        low = close - 50
        open_price = close - 25

        candle = OHLCV(
            timestamp=timestamp,
            open=float(open_price),
            high=float(high),
            low=float(low),
            close=float(close),
            volume=100.0,
        )
        candles.append(candle)

    return OHLCVSeries(candles=candles, symbol="BTCUSDT", timeframe="1h")


# TradingView Reference Values
# These would typically come from actual TradingView chart validation
# For now, we use expected values based on formula calculations

@pytest.fixture
def tradingview_reference() -> dict[str, Any]:
    """TradingView reference values for validation.

    Note: In production, these would be captured from actual TradingView charts.
    For testing, we use expected values based on known-good calculations.

    Returns:
        Dictionary with reference values for various indicators.
    """
    return {
        "rsi_14": {
            "last_value": None,  # Would be validated against TradingView
            "tolerance": 0.01,  # ±0.01 for RSI
        },
        "ema_20": {
            "last_value": None,
            "tolerance": 0.0001,  # ±0.0001% for prices
        },
        "macd_12_26_9": {
            "last_macd": None,
            "last_signal": None,
            "last_histogram": None,
            "tolerance": 0.0001,
        },
        "atr_14": {
            "last_value": None,
            "tolerance": 0.0001,
        },
        "bollinger_20_2": {
            "last_upper": None,
            "last_middle": None,
            "last_lower": None,
            "tolerance": 0.0001,
        },
    }


def assert_close(
    actual: float,
    expected: float,
    tolerance: float = 0.01,
    msg: str = "",
) -> None:
    """Assert two values are close within tolerance.

    Helper function for validating indicator values against reference data.

    Args:
        actual: Actual calculated value.
        expected: Expected reference value.
        tolerance: Tolerance for comparison (default 0.01 = 1%).
        msg: Optional message for assertion failure.

    Raises:
        AssertionError: If values differ by more than tolerance.
    """
    if abs(actual - expected) > tolerance:
        error_msg = (
            f"{msg}\n"
            f"Expected: {expected:.6f}\n"
            f"Actual: {actual:.6f}\n"
            f"Difference: {abs(actual - expected):.6f}\n"
            f"Tolerance: {tolerance}"
        )
        raise AssertionError(error_msg)


def assert_array_not_all_nan(arr: NDArray[np.float64], name: str = "") -> None:
    """Assert array contains at least some non-NaN values.

    Args:
        arr: Numpy array to check.
        name: Optional name for error message.

    Raises:
        AssertionError: If all values are NaN.
    """
    valid_count = np.count_nonzero(~np.isnan(arr))
    if valid_count == 0:
        raise AssertionError(f"{name}: All values are NaN (expected some valid values)")


def assert_first_n_nan(arr: NDArray[np.float64], n: int, name: str = "") -> None:
    """Assert first N values are NaN (warmup period).

    Args:
        arr: Numpy array to check.
        n: Number of values that should be NaN.
        name: Optional name for error message.

    Raises:
        AssertionError: If first N values are not all NaN.
    """
    first_n = arr[:n]
    nan_count = np.count_nonzero(np.isnan(first_n))

    if nan_count != n:
        raise AssertionError(
            f"{name}: Expected first {n} values to be NaN, "
            f"but only {nan_count} are NaN"
        )
