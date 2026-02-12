"""Tests for SuperTrend indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.indicators import SuperTrend
from src.core.indicators.supertrend import SuperTrendResult
from src.data.market_data import OHLCVSeries
from tests.unit.indicators.conftest import assert_array_not_all_nan


class TestSuperTrend:
    """Tests for SuperTrend indicator."""

    def test_init_default_params(self) -> None:
        """Test SuperTrend initialization with defaults."""
        st = SuperTrend()

        assert st.period == 10
        assert st.multiplier == 3.0

    def test_init_custom_params(self) -> None:
        """Test SuperTrend initialization with custom params."""
        st = SuperTrend(period=14, multiplier=2.0)

        assert st.period == 14
        assert st.multiplier == 2.0

    def test_init_invalid_period_raises(self) -> None:
        """Test SuperTrend raises ValueError for period < 1."""
        with pytest.raises(ValueError, match="Period must be >= 1"):
            SuperTrend(period=0)

    def test_init_invalid_multiplier_raises(self) -> None:
        """Test SuperTrend raises ValueError for multiplier <= 0."""
        with pytest.raises(ValueError, match="Multiplier must be > 0"):
            SuperTrend(multiplier=0)

    def test_init_negative_multiplier_raises(self) -> None:
        """Test SuperTrend raises ValueError for negative multiplier."""
        with pytest.raises(ValueError, match="Multiplier must be > 0"):
            SuperTrend(multiplier=-1.0)

    def test_calculate_basic(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test basic SuperTrend calculation."""
        st = SuperTrend()
        result = st.calculate(sample_ohlcv_series)

        assert isinstance(result, SuperTrendResult)
        assert result.name == "ST_10_3.0"
        assert len(result.supertrend) == len(sample_ohlcv_series)
        assert len(result.trend) == len(sample_ohlcv_series)
        assert len(result.upper_band) == len(sample_ohlcv_series)
        assert len(result.lower_band) == len(sample_ohlcv_series)
        assert result.params["period"] == 10
        assert result.params["multiplier"] == 3.0

    def test_calculate_has_valid_values(
        self, sample_ohlcv_series: OHLCVSeries
    ) -> None:
        """Test SuperTrend has valid values after warmup."""
        st = SuperTrend()
        result = st.calculate(sample_ohlcv_series)

        assert_array_not_all_nan(result.supertrend, "SuperTrend")
        assert_array_not_all_nan(result.upper_band, "Upper band")
        assert_array_not_all_nan(result.lower_band, "Lower band")

    def test_trend_values_are_valid(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test trend array contains only 0, +1, -1."""
        st = SuperTrend()
        result = st.calculate(sample_ohlcv_series)

        unique_values = set(np.unique(result.trend))
        assert unique_values.issubset({-1, 0, 1}), (
            f"Trend values should be -1, 0, or 1, got {unique_values}"
        )

    def test_trend_has_nonzero_values(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test trend array has actual trend values (not all zeros)."""
        st = SuperTrend()
        result = st.calculate(sample_ohlcv_series)

        nonzero_count = np.count_nonzero(result.trend)
        assert nonzero_count > 0, "Trend should have non-zero values after warmup"

    def test_just_flipped_bullish(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test bullish flip detection returns bool."""
        st = SuperTrend()
        result = st.calculate(sample_ohlcv_series)

        flipped = result.just_flipped_bullish()
        assert isinstance(flipped, bool)

    def test_just_flipped_bearish(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test bearish flip detection returns bool."""
        st = SuperTrend()
        result = st.calculate(sample_ohlcv_series)

        flipped = result.just_flipped_bearish()
        assert isinstance(flipped, bool)

    def test_flips_mutually_exclusive(
        self, sample_ohlcv_series: OHLCVSeries
    ) -> None:
        """Test bullish and bearish flips cannot both be True."""
        st = SuperTrend()
        result = st.calculate(sample_ohlcv_series)

        bullish = result.just_flipped_bullish()
        bearish = result.just_flipped_bearish()

        assert not (bullish and bearish)

    def test_current_trend(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test current_trend property returns valid direction."""
        st = SuperTrend()
        result = st.calculate(sample_ohlcv_series)

        trend = result.current_trend
        assert trend in {-1, 0, 1}

    def test_calculate_insufficient_data_raises(
        self, minimal_series: OHLCVSeries
    ) -> None:
        """Test SuperTrend raises ValueError with insufficient data."""
        st = SuperTrend(period=20)

        with pytest.raises(ValueError, match="requires at least"):
            st.calculate(minimal_series)

    def test_required_periods(self) -> None:
        """Test required_periods static method."""
        assert SuperTrend.required_periods(10) == 11
        assert SuperTrend.required_periods(14) == 15

    def test_repr(self) -> None:
        """Test string representation."""
        st = SuperTrend(period=14, multiplier=2.0)
        repr_str = repr(st)

        assert "SuperTrend" in repr_str
        assert "14" in repr_str
        assert "2.0" in repr_str

    def test_result_repr(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test SuperTrendResult string representation."""
        st = SuperTrend()
        result = st.calculate(sample_ohlcv_series)
        repr_str = repr(result)

        assert "SuperTrendResult" in repr_str
        assert "ST_10_3.0" in repr_str
