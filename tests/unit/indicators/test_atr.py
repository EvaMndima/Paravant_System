"""Tests for ATR (Average True Range) indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-002 - Wilder's smoothing for ATR
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.indicators import ATR
from src.data.market_data import OHLCVSeries
from tests.unit.indicators.conftest import (assert_array_not_all_nan,
                                            assert_first_n_nan)


class TestATR:
    """Tests for ATR indicator."""

    def test_init_default_period(self):
        """Test ATR initialization with default period."""
        atr = ATR()

        assert atr.period == 14

    def test_init_custom_period(self):
        """Test ATR initialization with custom period."""
        atr = ATR(period=21)

        assert atr.period == 21

    def test_init_invalid_period_raises(self):
        """Test ATR raises ValueError for invalid period."""
        with pytest.raises(ValueError, match="ATR period must be >= 1"):
            ATR(period=0)

    def test_calculate_basic(self, sample_ohlcv_series: OHLCVSeries):
        """Test basic ATR calculation."""
        atr = ATR(period=14)
        result = atr.calculate(sample_ohlcv_series)

        # Check result structure
        assert result.name == "ATR_14"
        assert len(result.values) == len(sample_ohlcv_series)
        assert result.params["period"] == 14

        # Check NaN pattern (first period values should be NaN)
        assert_first_n_nan(result.values, 14, "ATR warmup")

        # Check valid values exist
        assert_array_not_all_nan(result.values, "ATR")

    def test_calculate_positive_values(self, sample_ohlcv_series: OHLCVSeries):
        """Test ATR produces only positive values."""
        atr = ATR(period=14)
        result = atr.calculate(sample_ohlcv_series)

        valid_atr = result.values[~np.isnan(result.values)]

        # ATR is always non-negative (measures volatility)
        assert np.all(valid_atr >= 0.0), "ATR should be non-negative"

    def test_calculate_stores_tr_values(self, sample_ohlcv_series: OHLCVSeries):
        """Test ATR stores TR (True Range) values in params."""
        atr = ATR(period=14)
        result = atr.calculate(sample_ohlcv_series)

        # TR values should be stored for dependent indicators
        assert "tr_values" in result.params
        tr_values = result.params["tr_values"]

        assert isinstance(tr_values, np.ndarray)
        assert len(tr_values) == len(sample_ohlcv_series)

    def test_tr_values_positive(self, sample_ohlcv_series: OHLCVSeries):
        """Test True Range values are non-negative."""
        atr = ATR(period=14)
        result = atr.calculate(sample_ohlcv_series)

        tr_values = result.params["tr_values"]

        # TR should be non-negative (skip first NaN)
        valid_tr = tr_values[~np.isnan(tr_values)]
        assert np.all(valid_tr >= 0.0), "True Range should be non-negative"

    def test_calculate_insufficient_data_raises(self, minimal_series: OHLCVSeries):
        """Test ATR raises ValueError with insufficient data."""
        atr = ATR(period=20)

        with pytest.raises(ValueError, match="requires at least 21 bars"):
            atr.calculate(minimal_series)

    def test_volatile_series_higher_atr(
        self,
        sample_ohlcv_series: OHLCVSeries,
        volatile_series: OHLCVSeries,
    ):
        """Test volatile series produces higher ATR."""
        atr = ATR(period=14)

        result_normal = atr.calculate(sample_ohlcv_series)
        result_volatile = atr.calculate(volatile_series)

        # Get mean ATR for comparison
        mean_atr_normal = np.nanmean(result_normal.values)
        mean_atr_volatile = np.nanmean(result_volatile.values)

        # Volatile series should have higher ATR
        assert mean_atr_volatile > mean_atr_normal, (
            "Volatile series should have higher ATR"
        )

    def test_flat_prices_zero_atr(self, flat_price_series: OHLCVSeries):
        """Test ATR with flat prices is near zero."""
        atr = ATR(period=14)
        result = atr.calculate(flat_price_series)

        valid_atr = result.values[~np.isnan(result.values)]

        # Flat prices should produce ATR near zero
        assert np.all(valid_atr < 1.0), "ATR of flat prices should be near zero"

    def test_gap_series_high_tr(self, gap_series: OHLCVSeries):
        """Test gaps produce high True Range values."""
        atr = ATR(period=14)
        result = atr.calculate(gap_series)

        tr_values = result.params["tr_values"]

        # At gap points (10, 25, 40), TR should be elevated
        # Check TR values around those points
        if len(tr_values) > 10:
            tr_at_gap = tr_values[10:12]  # Around first gap
            mean_tr = np.nanmean(tr_values)

            # TR at gap should be higher than mean
            assert np.nanmean(tr_at_gap) > mean_tr, (
                "TR should be elevated at gap points"
            )

    def test_current_and_previous(self, sample_ohlcv_series: OHLCVSeries):
        """Test current and previous properties."""
        atr = ATR(period=14)
        result = atr.calculate(sample_ohlcv_series)

        current = result.current
        previous = result.previous

        assert isinstance(current, float)
        assert isinstance(previous, float)
        assert current >= 0.0
        assert previous >= 0.0

    def test_required_periods(self):
        """Test required_periods static method."""
        periods = ATR.required_periods(14)

        assert periods == 14 + 1

    def test_volatility_ratio(self, sample_ohlcv_series: OHLCVSeries):
        """Test volatility_ratio static method returns percentage."""
        atr = ATR(period=14)
        result = atr.calculate(sample_ohlcv_series)

        ratio = ATR.volatility_ratio(result.values, sample_ohlcv_series.closes)

        assert isinstance(ratio, float)
        assert ratio > 0, "Volatility ratio should be positive"

    def test_volatility_ratio_no_valid_raises(self):
        """Test volatility_ratio raises ValueError when no valid ATR values."""
        all_nan = np.full(10, np.nan)
        closes = np.full(10, 40000.0)

        with pytest.raises(ValueError, match="No valid ATR values"):
            ATR.volatility_ratio(all_nan, closes)

    def test_volatility_ratio_zero_close_raises(self, sample_ohlcv_series: OHLCVSeries):
        """Test volatility_ratio raises ValueError when close is zero."""
        atr = ATR(period=14)
        result = atr.calculate(sample_ohlcv_series)

        # Create closes array with zero at the last valid ATR position
        closes = sample_ohlcv_series.closes.copy()
        valid_atr_indices = np.where(~np.isnan(result.values))[0]
        closes[valid_atr_indices[-1]] = 0.0

        with pytest.raises(ValueError, match="Close price is zero"):
            ATR.volatility_ratio(result.values, closes)

    def test_repr(self):
        """Test string representation."""
        atr = ATR(period=14)

        repr_str = repr(atr)

        assert "ATR" in repr_str
        assert "14" in repr_str
