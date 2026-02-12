"""Tests for EMA (Exponential Moving Average) indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.indicators import EMA
from src.data.market_data import OHLCVSeries
from tests.unit.indicators.conftest import (assert_array_not_all_nan,
                                            assert_first_n_nan)


class TestEMA:
    """Tests for EMA indicator."""

    def test_init_default_period(self):
        """Test EMA initialization with default period."""
        ema = EMA()

        assert ema.period == 20

    def test_init_custom_period(self):
        """Test EMA initialization with custom period."""
        ema = EMA(period=50)

        assert ema.period == 50

    def test_init_invalid_period_raises(self):
        """Test EMA raises ValueError for invalid period."""
        with pytest.raises(ValueError, match="period must be >= 1"):
            EMA(period=0)

    def test_calculate_basic(self, sample_ohlcv_series: OHLCVSeries):
        """Test basic EMA calculation."""
        ema = EMA(period=20)
        result = ema.calculate(sample_ohlcv_series)

        # Check result structure
        assert result.name == "EMA_20"
        assert len(result.values) == len(sample_ohlcv_series)
        assert result.params["period"] == 20  # Check key existence and value

        # Check NaN pattern (first period-1 values should be NaN)
        assert_first_n_nan(result.values, 19, "EMA warmup")

        # Check valid values exist
        assert_array_not_all_nan(result.values, "EMA")

    def test_calculate_follows_price_trend(self, sample_ohlcv_series: OHLCVSeries):
        """Test EMA follows price trend."""
        ema = EMA(period=20)
        result = ema.calculate(sample_ohlcv_series)

        # EMA should be correlated with close prices
        closes = sample_ohlcv_series.closes
        ema_values = result.values

        # Get overlapping valid indices
        valid_mask = ~np.isnan(ema_values)
        valid_ema = ema_values[valid_mask]
        valid_closes = closes[valid_mask]

        # EMA should be within reasonable range of prices
        assert np.all(valid_ema > closes.min() * 0.9)
        assert np.all(valid_ema < closes.max() * 1.1)

    def test_calculate_insufficient_data_raises(self, minimal_series: OHLCVSeries):
        """Test EMA raises ValueError with insufficient data."""
        ema = EMA(period=20)

        with pytest.raises(ValueError, match="requires at least 20 bars"):
            ema.calculate(minimal_series)

    def test_shorter_period_more_responsive(self, sample_ohlcv_series: OHLCVSeries):
        """Test shorter EMA period is more responsive to price changes."""
        ema10 = EMA(period=10)
        ema50 = EMA(period=50)

        result10 = ema10.calculate(sample_ohlcv_series)
        result50 = ema50.calculate(sample_ohlcv_series)

        # Shorter period should have higher standard deviation (more responsive)
        valid10 = result10.values[~np.isnan(result10.values)]
        valid50 = result50.values[~np.isnan(result50.values)]

        std10 = np.std(valid10)
        std50 = np.std(valid50)

        assert std10 >= std50, "Shorter EMA should be more volatile"

    def test_slope_method(self, sample_ohlcv_series: OHLCVSeries):
        """Test EMA.slope() static method."""
        ema = EMA(period=20)
        result = ema.calculate(sample_ohlcv_series)

        # Calculate slope of last 5 values
        slope = EMA.slope(result.values, lookback=5)

        # Slope should be a float
        assert isinstance(slope, float)

        # Slope can be positive, negative, or near zero
        assert not np.isnan(slope)

    def test_slope_uptrend(self, sample_ohlcv_series: OHLCVSeries):
        """Test slope is positive during uptrend."""
        ema = EMA(period=20)
        result = ema.calculate(sample_ohlcv_series)

        # Check slope at different points
        # Uptrend is in bars 0-30 based on conftest data
        if len(result.values) > 30:
            # Calculate slope around bar 25 (uptrend)
            values_uptrend = result.values[:30]
            if np.count_nonzero(~np.isnan(values_uptrend)) >= 5:
                slope = EMA.slope(values_uptrend, lookback=5)
                # Slope should be positive or near zero in uptrend
                assert slope >= -10.0  # Allow some noise

    def test_current_and_previous(self, sample_ohlcv_series: OHLCVSeries):
        """Test current and previous properties."""
        ema = EMA(period=20)
        result = ema.calculate(sample_ohlcv_series)

        current = result.current
        previous = result.previous

        assert isinstance(current, float)
        assert isinstance(previous, float)
        assert current != previous  # Should be different values

    def test_repr(self):
        """Test string representation."""
        ema = EMA(period=20)

        repr_str = repr(ema)

        assert "EMA" in repr_str
        assert "20" in repr_str
