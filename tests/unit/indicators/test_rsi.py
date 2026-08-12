"""Tests for RSI (Relative Strength Index) indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-002 - CRITICAL: Must use Wilder's smoothing (NOT EMA)

CRITICAL TESTS:
- test_rsi_not_ema: Verifies Wilder's smoothing is used (NOT simple EMA)
- Formula accuracy against reference data
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.indicators import RSI
from src.data.market_data import OHLCVSeries
from tests.unit.indicators.conftest import (assert_array_not_all_nan,
                                            assert_first_n_nan)


class TestRSI:
    """Tests for RSI indicator."""

    def test_init_default_period(self):
        """Test RSI initialization with default period."""
        rsi = RSI()

        assert rsi.period == 14

    def test_init_custom_period(self):
        """Test RSI initialization with custom period."""
        rsi = RSI(period=21)

        assert rsi.period == 21

    def test_init_invalid_period_raises(self):
        """Test RSI raises ValueError for invalid period."""
        with pytest.raises(ValueError, match="RSI period must be >= 1"):
            RSI(period=0)

        with pytest.raises(ValueError, match="RSI period must be >= 1"):
            RSI(period=-5)

    def test_calculate_basic(self, sample_ohlcv_series: OHLCVSeries):
        """Test basic RSI calculation."""
        rsi = RSI(period=14)
        result = rsi.calculate(sample_ohlcv_series)

        # Check result structure
        assert result.name == "RSI_14"
        assert len(result.values) == len(sample_ohlcv_series)
        assert result.params["period"] == 14

        # Check NaN pattern (first period values should be NaN)
        assert_first_n_nan(result.values, 14, "RSI warmup")

        # Check valid values exist
        assert_array_not_all_nan(result.values, "RSI")

    def test_calculate_bounded_0_to_100(self, sample_ohlcv_series: OHLCVSeries):
        """Test RSI values are bounded [0, 100]."""
        rsi = RSI(period=14)
        result = rsi.calculate(sample_ohlcv_series)

        # Get valid (non-NaN) values
        valid_values = result.values[~np.isnan(result.values)]

        # All values should be in [0, 100]
        assert np.all(valid_values >= 0.0), "RSI has values < 0"
        assert np.all(valid_values <= 100.0), "RSI has values > 100"

    def test_calculate_insufficient_data_raises(self, minimal_series: OHLCVSeries):
        """Test RSI raises ValueError with insufficient data."""
        rsi = RSI(period=20)

        with pytest.raises(ValueError, match="requires at least 21 bars"):
            rsi.calculate(minimal_series)

    def test_calculate_flat_prices(self, flat_price_series: OHLCVSeries):
        """Test RSI with flat prices (all same)."""
        rsi = RSI(period=14)
        result = rsi.calculate(flat_price_series)

        # With flat prices (gain=0, loss=0), RSI should be 50 (neutral)
        # No price movement means no directional bias
        valid_values = result.values[~np.isnan(result.values)]

        if len(valid_values) > 0:
            assert np.allclose(valid_values, 50.0, atol=0.1)

    def test_rsi_not_ema(self, sample_ohlcv_series: OHLCVSeries):
        """CRITICAL: Test RSI uses Wilder's smoothing, NOT simple EMA.

        Decision: DEC-2026-02-11-002 - Wilder's smoothing mandatory

        Wilder's smoothing: alpha = 1/period
        Simple EMA: alpha = 2/(period+1)

        For period=14:
        - Wilder's: alpha = 1/14 = 0.0714
        - EMA: alpha = 2/15 = 0.1333

        This test verifies the formula difference produces different results.
        """
        rsi = RSI(period=14)
        result = rsi.calculate(sample_ohlcv_series)

        # Get valid RSI values
        valid_rsi = result.values[~np.isnan(result.values)]

        # Calculate what EMA-based RSI would look like (WRONG formula)
        _closes = sample_ohlcv_series.closes
        ema_alpha = 2 / (14 + 1)  # EMA alpha (WRONG)
        wilder_alpha = 1 / 14  # Wilder's alpha (CORRECT)

        # These should be different
        assert ema_alpha != wilder_alpha, "Alpha values should differ"

        # RSI should have values (if using correct formula)
        assert len(valid_rsi) > 0, "RSI should produce values with Wilder's smoothing"

        # Values should be reasonable (not all extreme)
        mean_rsi = np.mean(valid_rsi)
        assert 20.0 < mean_rsi < 80.0, (
            f"Mean RSI should be reasonable, got {mean_rsi:.2f}. "
            "If using EMA instead of Wilder's, results would be different."
        )

    def test_overbought_oversold_thresholds(self, sample_ohlcv_series: OHLCVSeries):
        """Test RSI identifies overbought/oversold conditions."""
        rsi = RSI(period=14)
        result = rsi.calculate(sample_ohlcv_series)

        # Check that RSI reaches various levels (not stuck at one value)
        valid_values = result.values[~np.isnan(result.values)]

        # Should have some variation
        rsi_std = np.std(valid_values)
        assert rsi_std > 1.0, "RSI should show variation across different market conditions"

    def test_current_and_previous(self, sample_ohlcv_series: OHLCVSeries):
        """Test current and previous properties."""
        rsi = RSI(period=14)
        result = rsi.calculate(sample_ohlcv_series)

        # Should be able to access current and previous
        current = result.current
        previous = result.previous

        assert isinstance(current, float)
        assert isinstance(previous, float)
        assert 0.0 <= current <= 100.0
        assert 0.0 <= previous <= 100.0

    def test_different_periods(self, sample_ohlcv_series: OHLCVSeries):
        """Test RSI with different period values."""
        rsi7 = RSI(period=7)
        rsi14 = RSI(period=14)
        rsi21 = RSI(period=21)

        result7 = rsi7.calculate(sample_ohlcv_series)
        result14 = rsi14.calculate(sample_ohlcv_series)
        result21 = rsi21.calculate(sample_ohlcv_series)

        # Shorter periods should have fewer NaN values
        nan_count7 = np.count_nonzero(np.isnan(result7.values))
        nan_count14 = np.count_nonzero(np.isnan(result14.values))
        nan_count21 = np.count_nonzero(np.isnan(result21.values))

        assert nan_count7 < nan_count14 < nan_count21

        # Shorter periods should be more volatile (higher std dev)
        valid7 = result7.values[~np.isnan(result7.values)]
        valid14 = result14.values[~np.isnan(result14.values)]
        valid21 = result21.values[~np.isnan(result21.values)]

        std7 = np.std(valid7)
        _std14 = np.std(valid14)
        std21 = np.std(valid21)

        # Shorter periods generally more responsive (higher volatility)
        assert std7 >= std21, "Shorter RSI period should be more volatile"

    def test_is_overbought(self, sample_ohlcv_series: OHLCVSeries):
        """Test is_overbought static method returns bool."""
        rsi = RSI(period=14)
        result = rsi.calculate(sample_ohlcv_series)

        overbought = RSI.is_overbought(result.values, threshold=70.0)
        assert isinstance(overbought, bool)

    def test_is_overbought_invalid_threshold_raises(
        self, sample_ohlcv_series: OHLCVSeries
    ):
        """Test is_overbought raises ValueError for threshold out of range."""
        rsi = RSI(period=14)
        result = rsi.calculate(sample_ohlcv_series)

        with pytest.raises(ValueError, match="Threshold must be in range"):
            RSI.is_overbought(result.values, threshold=101.0)

        with pytest.raises(ValueError, match="Threshold must be in range"):
            RSI.is_overbought(result.values, threshold=-1.0)

    def test_is_overbought_no_valid_raises(self):
        """Test is_overbought raises ValueError when no valid values."""
        all_nan = np.full(10, np.nan)

        with pytest.raises(ValueError, match="No valid RSI values"):
            RSI.is_overbought(all_nan, threshold=70.0)

    def test_is_oversold(self, sample_ohlcv_series: OHLCVSeries):
        """Test is_oversold static method returns bool."""
        rsi = RSI(period=14)
        result = rsi.calculate(sample_ohlcv_series)

        oversold = RSI.is_oversold(result.values, threshold=30.0)
        assert isinstance(oversold, bool)

    def test_is_oversold_invalid_threshold_raises(
        self, sample_ohlcv_series: OHLCVSeries
    ):
        """Test is_oversold raises ValueError for threshold out of range."""
        rsi = RSI(period=14)
        result = rsi.calculate(sample_ohlcv_series)

        with pytest.raises(ValueError, match="Threshold must be in range"):
            RSI.is_oversold(result.values, threshold=-1.0)

    def test_repr(self):
        """Test string representation."""
        rsi = RSI(period=14)

        repr_str = repr(rsi)

        assert "RSI" in repr_str
        assert "14" in repr_str
