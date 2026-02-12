"""Tests for VWAP (Volume Weighted Average Price) indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.indicators import VWAP
from src.core.indicators.vwap import VWAPResult
from src.data.market_data import OHLCVSeries
from tests.unit.indicators.conftest import (assert_array_not_all_nan,
                                            assert_first_n_nan)


class TestVWAP:
    """Tests for VWAP indicator."""

    def test_init_default_params(self) -> None:
        """Test VWAP initialization with defaults."""
        vwap = VWAP()

        assert vwap.period == 20
        assert vwap.multiplier == 2.0

    def test_init_custom_params(self) -> None:
        """Test VWAP initialization with custom params."""
        vwap = VWAP(period=50, multiplier=1.5)

        assert vwap.period == 50
        assert vwap.multiplier == 1.5

    def test_init_invalid_period_raises(self) -> None:
        """Test VWAP raises ValueError for period < 1."""
        with pytest.raises(ValueError, match="Period must be >= 1"):
            VWAP(period=0)

    def test_init_invalid_multiplier_raises(self) -> None:
        """Test VWAP raises ValueError for multiplier <= 0."""
        with pytest.raises(ValueError, match="Multiplier must be > 0"):
            VWAP(multiplier=0)

    def test_init_negative_multiplier_raises(self) -> None:
        """Test VWAP raises ValueError for negative multiplier."""
        with pytest.raises(ValueError, match="Multiplier must be > 0"):
            VWAP(multiplier=-1.0)

    def test_calculate_basic(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test basic VWAP calculation."""
        vwap = VWAP()
        result = vwap.calculate(sample_ohlcv_series)

        assert isinstance(result, VWAPResult)
        assert result.name == "VWAP_20_2.0"
        assert len(result.vwap) == len(sample_ohlcv_series)
        assert len(result.upper_band) == len(sample_ohlcv_series)
        assert len(result.lower_band) == len(sample_ohlcv_series)

    def test_calculate_warmup_period(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test NaN warmup for first period-1 values."""
        vwap = VWAP(period=20)
        result = vwap.calculate(sample_ohlcv_series)

        assert_first_n_nan(result.vwap, 19, "VWAP warmup")
        assert_array_not_all_nan(result.vwap, "VWAP")

    def test_vwap_within_price_range(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test VWAP values are within the high-low price range."""
        vwap = VWAP()
        result = vwap.calculate(sample_ohlcv_series)

        valid = ~np.isnan(result.vwap)
        lows = sample_ohlcv_series.lows
        highs = sample_ohlcv_series.highs

        # VWAP should be within the overall price range
        price_min = float(np.min(lows))
        price_max = float(np.max(highs))

        valid_vwap = result.vwap[valid]
        assert np.all(valid_vwap >= price_min * 0.95), "VWAP below price range"
        assert np.all(valid_vwap <= price_max * 1.05), "VWAP above price range"

    def test_band_ordering(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test upper_band >= vwap >= lower_band."""
        vwap = VWAP()
        result = vwap.calculate(sample_ohlcv_series)

        valid = (
            ~np.isnan(result.vwap)
            & ~np.isnan(result.upper_band)
            & ~np.isnan(result.lower_band)
        )

        assert np.all(result.upper_band[valid] >= result.vwap[valid])
        assert np.all(result.vwap[valid] >= result.lower_band[valid])

    def test_is_at_vwap(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test is_at_vwap returns bool."""
        vwap = VWAP()
        result = vwap.calculate(sample_ohlcv_series)

        at_vwap = result.is_at_vwap(tolerance=0.05)
        assert isinstance(at_vwap, bool)

    def test_is_at_vwap_invalid_tolerance_zero_raises(
        self, sample_ohlcv_series: OHLCVSeries
    ) -> None:
        """Test is_at_vwap raises ValueError for tolerance = 0."""
        vwap = VWAP()
        result = vwap.calculate(sample_ohlcv_series)

        with pytest.raises(ValueError, match="Tolerance must be in"):
            result.is_at_vwap(tolerance=0)

    def test_is_at_vwap_invalid_tolerance_negative_raises(
        self, sample_ohlcv_series: OHLCVSeries
    ) -> None:
        """Test is_at_vwap raises ValueError for negative tolerance."""
        vwap = VWAP()
        result = vwap.calculate(sample_ohlcv_series)

        with pytest.raises(ValueError, match="Tolerance must be in"):
            result.is_at_vwap(tolerance=-0.1)

    def test_calculate_insufficient_data_raises(
        self, minimal_series: OHLCVSeries
    ) -> None:
        """Test VWAP raises ValueError with insufficient data."""
        vwap = VWAP(period=20)

        with pytest.raises(ValueError, match="requires at least"):
            vwap.calculate(minimal_series)

    def test_required_periods(self) -> None:
        """Test required_periods static method."""
        assert VWAP.required_periods(20) == 20
        assert VWAP.required_periods(50) == 50

    def test_current_and_previous(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test current and previous properties."""
        vwap = VWAP()
        result = vwap.calculate(sample_ohlcv_series)

        current = result.current
        previous = result.previous

        assert isinstance(current, float)
        assert isinstance(previous, float)

    def test_repr(self) -> None:
        """Test string representation."""
        vwap = VWAP(period=50, multiplier=1.5)
        repr_str = repr(vwap)

        assert "VWAP" in repr_str
        assert "50" in repr_str
        assert "1.5" in repr_str

    def test_result_repr(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test VWAPResult string representation."""
        vwap = VWAP()
        result = vwap.calculate(sample_ohlcv_series)
        repr_str = repr(result)

        assert "VWAPResult" in repr_str
        assert "VWAP_20_2.0" in repr_str
