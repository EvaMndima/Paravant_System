"""Tests for indicator utility functions.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.indicators import utils


class TestCalculateSlope:
    """Tests for calculate_slope function."""

    def test_uptrend_positive_slope(self):
        """Test positive slope for uptrend."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)

        slope = utils.calculate_slope(values, lookback=5)

        assert slope > 0, "Uptrend should have positive slope"
        np.testing.assert_almost_equal(slope, 1.0, decimal=2)

    def test_downtrend_negative_slope(self):
        """Test negative slope for downtrend."""
        values = np.array([5.0, 4.0, 3.0, 2.0, 1.0], dtype=np.float64)

        slope = utils.calculate_slope(values, lookback=5)

        assert slope < 0, "Downtrend should have negative slope"
        np.testing.assert_almost_equal(slope, -1.0, decimal=2)

    def test_flat_near_zero_slope(self):
        """Test near-zero slope for flat values."""
        values = np.array([5.0, 5.0, 5.0, 5.0, 5.0], dtype=np.float64)

        slope = utils.calculate_slope(values, lookback=5)

        np.testing.assert_almost_equal(slope, 0.0, decimal=2)

    def test_insufficient_lookback_raises(self):
        """Test invalid lookback raises ValueError."""
        values = np.array([1.0, 2.0, 3.0], dtype=np.float64)

        with pytest.raises(ValueError, match="Lookback must be >= 2"):
            utils.calculate_slope(values, lookback=1)

    def test_insufficient_data_raises(self):
        """Test insufficient data raises ValueError."""
        values = np.array([1.0, 2.0], dtype=np.float64)

        with pytest.raises(ValueError, match="Need at least 5 valid values"):
            utils.calculate_slope(values, lookback=5)


class TestCalculateNormalizedSlope:
    """Tests for calculate_normalized_slope function."""

    def test_normalized_slope_percentage(self):
        """Test normalized slope returns percentage."""
        values = np.array([100.0, 101.0, 102.0, 103.0, 104.0], dtype=np.float64)

        norm_slope = utils.calculate_normalized_slope(values, lookback=5)

        # Slope of 1 per bar on base of 104 = ~0.96% per bar
        assert 0.5 < norm_slope < 1.5

    def test_zero_current_value_raises(self):
        """Test zero current value raises ValueError."""
        values = np.array([5.0, 4.0, 3.0, 2.0, 1.0, 0.0], dtype=np.float64)

        with pytest.raises(ValueError, match="current value is zero"):
            utils.calculate_normalized_slope(values, lookback=5)


class TestIsRising:
    """Tests for is_rising function."""

    def test_rising_values_true(self):
        """Test rising values return True."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)

        assert utils.is_rising(values, periods=3) is True

    def test_falling_values_false(self):
        """Test falling values return False."""
        values = np.array([5.0, 4.0, 3.0, 2.0, 1.0], dtype=np.float64)

        assert utils.is_rising(values, periods=3) is False

    def test_flat_values_false(self):
        """Test flat values return False."""
        values = np.array([5.0, 5.0, 5.0, 5.0], dtype=np.float64)

        assert utils.is_rising(values, periods=3) is False

    def test_mixed_values_false(self):
        """Test mixed up/down values return False."""
        values = np.array([1.0, 3.0, 2.0, 4.0], dtype=np.float64)

        assert utils.is_rising(values, periods=3) is False

    def test_insufficient_periods_raises(self):
        """Test insufficient periods raises ValueError."""
        values = np.array([1.0, 2.0], dtype=np.float64)

        with pytest.raises(ValueError, match="Periods must be >= 2"):
            utils.is_rising(values, periods=1)


class TestIsFalling:
    """Tests for is_falling function."""

    def test_falling_values_true(self):
        """Test falling values return True."""
        values = np.array([5.0, 4.0, 3.0, 2.0, 1.0], dtype=np.float64)

        assert utils.is_falling(values, periods=3) is True

    def test_rising_values_false(self):
        """Test rising values return False."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)

        assert utils.is_falling(values, periods=3) is False


class TestCrossover:
    """Tests for crossover function (bullish)."""

    def test_bullish_crossover_true(self):
        """Test bullish crossover detection."""
        # Fast crosses above slow ONLY at the last step
        fast = np.array([1.0, 2.0, 3.0, 3.0, 4.0], dtype=np.float64)
        slow = np.array([3.0, 3.0, 3.0, 3.0, 3.0], dtype=np.float64)

        # Index 3: fast=3, slow=3 (equal)
        # Index 4: fast=4, slow=3 (above) -> Crossover
        assert utils.crossover(fast, slow) == True

    def test_no_crossover_false(self):
        """Test no crossover returns False."""
        fast = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
        slow = np.array([6.0, 6.0, 6.0, 6.0, 6.0], dtype=np.float64)

        # Fast never crosses above slow
        assert utils.crossover(fast, slow) == False

    def test_already_above_false(self):
        """Test already above returns False."""
        fast = np.array([5.0, 5.0, 5.0, 5.0, 5.0], dtype=np.float64)
        slow = np.array([3.0, 3.0, 3.0, 3.0, 3.0], dtype=np.float64)

        # Fast already above slow
        assert utils.crossover(fast, slow) == False

    def test_different_length_raises(self):
        """Test different array lengths raise ValueError."""
        fast = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        slow = np.array([1.0, 2.0], dtype=np.float64)

        with pytest.raises(ValueError, match="must have same length"):
            utils.crossover(fast, slow)


class TestCrossunder:
    """Tests for crossunder function (bearish)."""

    def test_bearish_crossunder_true(self):
        """Test bearish crossunder detection."""
        # Fast crosses below slow ONLY at the last step
        fast = np.array([5.0, 4.0, 3.0, 3.0, 2.0], dtype=np.float64)
        slow = np.array([3.0, 3.0, 3.0, 3.0, 3.0], dtype=np.float64)

        # Index 3: fast=3, slow=3 (equal)
        # Index 4: fast=2, slow=3 (below) -> Crossunder
        assert utils.crossunder(fast, slow) == True

    def test_no_crossunder_false(self):
        """Test no crossunder returns False."""
        fast = np.array([5.0, 5.0, 5.0, 5.0, 5.0], dtype=np.float64)
        slow = np.array([3.0, 3.0, 3.0, 3.0, 3.0], dtype=np.float64)

        # Fast stays above slow
        assert utils.crossunder(fast, slow) == False


class TestHighest:
    """Tests for highest function."""

    def test_highest_value(self):
        """Test finding highest value."""
        values = np.array([1.0, 5.0, 3.0, 7.0, 2.0], dtype=np.float64)

        highest = utils.highest(values, period=5)

        assert highest == 7.0

    def test_highest_partial_period(self):
        """Test highest with period smaller than array."""
        values = np.array([1.0, 5.0, 3.0, 7.0, 2.0], dtype=np.float64)

        highest = utils.highest(values, period=3)

        # Last 3 values: [3.0, 7.0, 2.0] -> max = 7.0
        assert highest == 7.0

    def test_insufficient_data_raises(self):
        """Test insufficient data raises ValueError."""
        values = np.array([1.0, 2.0], dtype=np.float64)

        with pytest.raises(ValueError, match="Need at least 5 valid values"):
            utils.highest(values, period=5)


class TestLowest:
    """Tests for lowest function."""

    def test_lowest_value(self):
        """Test finding lowest value."""
        values = np.array([5.0, 2.0, 7.0, 1.0, 9.0], dtype=np.float64)

        lowest = utils.lowest(values, period=5)

        assert lowest == 1.0

    def test_lowest_partial_period(self):
        """Test lowest with period smaller than array."""
        values = np.array([5.0, 2.0, 7.0, 1.0, 9.0], dtype=np.float64)

        lowest = utils.lowest(values, period=3)

        # Last 3 values: [7.0, 1.0, 9.0] -> min = 1.0
        assert lowest == 1.0
