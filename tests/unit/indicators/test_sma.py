"""Tests for SMA (Simple Moving Average) indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.indicators import SMA
from src.data.market_data import OHLCVSeries
from tests.unit.indicators.conftest import (assert_array_not_all_nan,
                                            assert_first_n_nan)


class TestSMA:
    """Tests for SMA indicator."""

    def test_init_default_period(self):
        """Test SMA initialization with default period."""
        sma = SMA()

        assert sma.period == 20

    def test_init_custom_period(self):
        """Test SMA initialization with custom period."""
        sma = SMA(period=50)

        assert sma.period == 50

    def test_init_invalid_period_raises(self):
        """Test SMA raises ValueError for invalid period."""
        with pytest.raises(ValueError, match=r"(?:SMA )?[Pp]eriod must be >= 1"):
            SMA(period=0)

    def test_calculate_basic(self, sample_ohlcv_series: OHLCVSeries):
        """Test basic SMA calculation."""
        sma = SMA(period=20)
        result = sma.calculate(sample_ohlcv_series)

        # Check result structure
        assert result.name == "SMA_20"
        assert len(result.values) == len(sample_ohlcv_series)
        assert result.params == {"period": 20}

        # Check NaN pattern (first period-1 values should be NaN)
        assert_first_n_nan(result.values, 19, "SMA warmup")

        # Check valid values exist
        assert_array_not_all_nan(result.values, "SMA")

    def test_calculate_is_true_average(self, sample_ohlcv_series: OHLCVSeries):
        """Test SMA is true simple moving average of closes."""
        period = 5  # Small period for easy validation
        sma = SMA(period=period)
        result = sma.calculate(sample_ohlcv_series)

        closes = sample_ohlcv_series.closes

        # Manually calculate SMA for a specific point
        test_idx = period  # First valid SMA value
        expected_sma = np.mean(closes[test_idx - period + 1 : test_idx + 1])
        actual_sma = result.values[test_idx]

        # Should match exactly (simple average)
        np.testing.assert_almost_equal(
            actual_sma,
            expected_sma,
            decimal=6,
            err_msg="SMA should be exact simple moving average",
        )

    def test_calculate_insufficient_data_raises(self, minimal_series: OHLCVSeries):
        """Test SMA raises ValueError with insufficient data."""
        sma = SMA(period=20)

        with pytest.raises(ValueError, match="requires at least 20 bars"):
            sma.calculate(minimal_series)

    def test_sma_is_smoother_than_price(self, sample_ohlcv_series: OHLCVSeries):
        """Test SMA is smoother (less volatile) than raw prices."""
        sma = SMA(period=20)
        result = sma.calculate(sample_ohlcv_series)

        closes = sample_ohlcv_series.closes
        valid_sma = result.values[~np.isnan(result.values)]

        # Calculate volatility (std dev) of prices vs SMA
        # Get overlapping range
        start_idx = 20 - 1  # First valid SMA
        price_volatility = np.std(closes[start_idx:])
        sma_volatility = np.std(valid_sma)

        # SMA should be smoother (lower volatility) than raw prices
        assert sma_volatility < price_volatility, "SMA should smooth out price volatility"

    def test_flat_prices_constant_sma(self, flat_price_series: OHLCVSeries):
        """Test SMA with flat prices produces constant value."""
        sma = SMA(period=10)
        result = sma.calculate(flat_price_series)

        valid_sma = result.values[~np.isnan(result.values)]

        # All SMA values should be exactly the flat price
        expected_price = flat_price_series.closes[0]
        np.testing.assert_array_almost_equal(
            valid_sma,
            expected_price,
            decimal=6,
            err_msg="SMA of flat prices should be constant",
        )

    def test_current_and_previous(self, sample_ohlcv_series: OHLCVSeries):
        """Test current and previous properties."""
        sma = SMA(period=20)
        result = sma.calculate(sample_ohlcv_series)

        current = result.current
        previous = result.previous

        assert isinstance(current, float)
        assert isinstance(previous, float)

    def test_repr(self):
        """Test string representation."""
        sma = SMA(period=20)

        repr_str = repr(sma)

        assert "SMA" in repr_str
        assert "20" in repr_str
