"""Tests for MACD (Moving Average Convergence Divergence) indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.indicators import MACD
from src.core.indicators.macd import MACDResult
from src.data.market_data import OHLCVSeries
from tests.unit.indicators.conftest import (assert_array_not_all_nan,
                                            assert_first_n_nan)


class TestMACD:
    """Tests for MACD indicator."""

    def test_init_default_periods(self) -> None:
        """Test MACD initialization with default periods."""
        macd = MACD()

        assert macd.fast_period == 12
        assert macd.slow_period == 26
        assert macd.signal_period == 9

    def test_init_custom_periods(self) -> None:
        """Test MACD initialization with custom periods."""
        macd = MACD(fast_period=8, slow_period=21, signal_period=5)

        assert macd.fast_period == 8
        assert macd.slow_period == 21
        assert macd.signal_period == 5

    def test_init_invalid_fast_period_raises(self) -> None:
        """Test MACD raises ValueError for invalid fast period."""
        with pytest.raises(ValueError, match="Fast period must be >= 1"):
            MACD(fast_period=0)

    def test_init_invalid_slow_period_raises(self) -> None:
        """Test MACD raises ValueError for invalid slow period."""
        with pytest.raises(ValueError, match="Slow period must be >= 1"):
            MACD(slow_period=0)

    def test_init_invalid_signal_period_raises(self) -> None:
        """Test MACD raises ValueError for invalid signal period."""
        with pytest.raises(ValueError, match="Signal period must be >= 1"):
            MACD(signal_period=0)

    def test_init_slow_not_greater_than_fast_raises(self) -> None:
        """Test MACD raises ValueError when slow_period <= fast_period."""
        with pytest.raises(ValueError, match="Slow period.*must be > fast period"):
            MACD(fast_period=26, slow_period=12)

    def test_init_slow_equal_fast_raises(self) -> None:
        """Test MACD raises ValueError when slow_period == fast_period."""
        with pytest.raises(ValueError, match="Slow period.*must be > fast period"):
            MACD(fast_period=12, slow_period=12)

    def test_calculate_basic(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test basic MACD calculation returns correct structure."""
        macd = MACD()
        result = macd.calculate(sample_ohlcv_series)

        assert isinstance(result, MACDResult)
        assert result.name == "MACD_12_26_9"
        assert len(result.macd_line) == len(sample_ohlcv_series)
        assert len(result.signal_line) == len(sample_ohlcv_series)
        assert len(result.histogram) == len(sample_ohlcv_series)
        assert result.params["fast_period"] == 12
        assert result.params["slow_period"] == 26
        assert result.params["signal_period"] == 9

    def test_calculate_macd_line_has_valid_values(
        self, sample_ohlcv_series: OHLCVSeries
    ) -> None:
        """Test MACD line contains non-NaN values after warmup."""
        macd = MACD()
        result = macd.calculate(sample_ohlcv_series)

        # MACD line valid after slow_period - 1 bars
        assert_first_n_nan(result.macd_line, 25, "MACD line warmup")
        assert_array_not_all_nan(result.macd_line, "MACD line")

    def test_calculate_signal_line_has_valid_values(
        self, sample_ohlcv_series: OHLCVSeries
    ) -> None:
        """Test signal line contains non-NaN values after warmup."""
        macd = MACD()
        result = macd.calculate(sample_ohlcv_series)

        # Signal starts after slow_period - 1 + signal_period - 1 = 25 + 8 = 33
        assert_array_not_all_nan(result.signal_line, "Signal line")

        # First signal value should appear at index slow_period - 1 + signal_period - 1 = 33
        signal_start = 25 + 8  # slow_period - 1 + signal_period - 1
        assert_first_n_nan(result.signal_line, signal_start, "Signal warmup")

    def test_calculate_histogram_equals_macd_minus_signal(
        self, sample_ohlcv_series: OHLCVSeries
    ) -> None:
        """Test histogram = MACD line - Signal line."""
        macd = MACD()
        result = macd.calculate(sample_ohlcv_series)

        # Where both are valid, histogram should equal macd - signal
        valid = ~np.isnan(result.macd_line) & ~np.isnan(result.signal_line)
        np.testing.assert_allclose(
            result.histogram[valid],
            result.macd_line[valid] - result.signal_line[valid],
            atol=1e-10,
        )

    def test_calculate_insufficient_data_raises(
        self, minimal_series: OHLCVSeries
    ) -> None:
        """Test MACD raises ValueError with insufficient data."""
        macd = MACD()  # Needs slow(26) + signal(9) = 35 bars

        with pytest.raises(ValueError, match="requires at least 35 bars"):
            macd.calculate(minimal_series)

    def test_is_bullish_crossover(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test bullish crossover detection returns bool."""
        macd = MACD()
        result = macd.calculate(sample_ohlcv_series)

        # Should return a boolean without raising
        crossover = result.is_bullish_crossover()
        assert isinstance(crossover, bool)

    def test_is_bearish_crossover(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test bearish crossover detection returns bool."""
        macd = MACD()
        result = macd.calculate(sample_ohlcv_series)

        crossover = result.is_bearish_crossover()
        assert isinstance(crossover, bool)

    def test_crossovers_mutually_exclusive(
        self, sample_ohlcv_series: OHLCVSeries
    ) -> None:
        """Test bullish and bearish crossovers cannot both be True."""
        macd = MACD()
        result = macd.calculate(sample_ohlcv_series)

        bullish = result.is_bullish_crossover()
        bearish = result.is_bearish_crossover()

        # Cannot have both crossovers at the same time
        assert not (bullish and bearish)

    def test_histogram_rising(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test histogram_rising returns bool."""
        macd = MACD()
        result = macd.calculate(sample_ohlcv_series)

        rising = result.histogram_rising()
        assert isinstance(rising, bool)

    def test_histogram_falling(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test histogram_falling returns bool."""
        macd = MACD()
        result = macd.calculate(sample_ohlcv_series)

        falling = result.histogram_falling()
        assert isinstance(falling, bool)

    def test_histogram_rising_falling_mutually_exclusive(
        self, sample_ohlcv_series: OHLCVSeries
    ) -> None:
        """Test histogram cannot be both rising and falling."""
        macd = MACD()
        result = macd.calculate(sample_ohlcv_series)

        rising = result.histogram_rising()
        falling = result.histogram_falling()

        # Cannot be both at the same time
        assert not (rising and falling)

    def test_current_and_previous(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test current and previous properties."""
        macd = MACD()
        result = macd.calculate(sample_ohlcv_series)

        current = result.current
        previous = result.previous

        assert isinstance(current, float)
        assert isinstance(previous, float)

    def test_required_periods(self) -> None:
        """Test required_periods static method."""
        # Default: slow(26) + signal(9) = 35
        assert MACD.required_periods() == 35

        # Custom periods
        assert MACD.required_periods(fast=8, slow=21, signal=5) == 26

    def test_repr(self) -> None:
        """Test string representation."""
        macd = MACD(fast_period=8, slow_period=21, signal_period=5)
        repr_str = repr(macd)

        assert "MACD" in repr_str
        assert "8" in repr_str
        assert "21" in repr_str
        assert "5" in repr_str

    def test_result_repr(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test MACDResult string representation."""
        macd = MACD()
        result = macd.calculate(sample_ohlcv_series)
        repr_str = repr(result)

        assert "MACDResult" in repr_str
        assert "MACD_12_26_9" in repr_str
