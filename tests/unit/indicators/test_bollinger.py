"""Tests for Bollinger Bands indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.indicators import BollingerBands
from src.core.indicators.bollinger import BollingerResult
from src.data.market_data import OHLCVSeries
from tests.unit.indicators.conftest import (assert_array_not_all_nan,
                                            assert_first_n_nan)


class TestBollingerBands:
    """Tests for Bollinger Bands indicator."""

    def test_init_default_params(self) -> None:
        """Test Bollinger Bands initialization with defaults."""
        bb = BollingerBands()

        assert bb.period == 20
        assert bb.multiplier == 2.0

    def test_init_custom_params(self) -> None:
        """Test Bollinger Bands initialization with custom params."""
        bb = BollingerBands(period=30, multiplier=2.5)

        assert bb.period == 30
        assert bb.multiplier == 2.5

    def test_init_invalid_period_raises(self) -> None:
        """Test Bollinger Bands raises ValueError for period < 2."""
        with pytest.raises(ValueError, match="Period must be >= 2"):
            BollingerBands(period=1)

    def test_init_invalid_multiplier_raises(self) -> None:
        """Test Bollinger Bands raises ValueError for multiplier <= 0."""
        with pytest.raises(ValueError, match="Multiplier must be > 0"):
            BollingerBands(multiplier=0)

    def test_init_negative_multiplier_raises(self) -> None:
        """Test Bollinger Bands raises ValueError for negative multiplier."""
        with pytest.raises(ValueError, match="Multiplier must be > 0"):
            BollingerBands(multiplier=-1.0)

    def test_calculate_basic(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test basic Bollinger Bands calculation."""
        bb = BollingerBands()
        result = bb.calculate(sample_ohlcv_series)

        assert isinstance(result, BollingerResult)
        assert result.name == "BB_20_2.0"
        assert len(result.upper) == len(sample_ohlcv_series)
        assert len(result.middle) == len(sample_ohlcv_series)
        assert len(result.lower) == len(sample_ohlcv_series)
        assert len(result.width) == len(sample_ohlcv_series)
        assert len(result.percent_b) == len(sample_ohlcv_series)

    def test_calculate_warmup_period(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test NaN warmup for first period-1 values."""
        bb = BollingerBands(period=20)
        result = bb.calculate(sample_ohlcv_series)

        assert_first_n_nan(result.middle, 19, "BB middle warmup")
        assert_first_n_nan(result.upper, 19, "BB upper warmup")
        assert_first_n_nan(result.lower, 19, "BB lower warmup")
        assert_array_not_all_nan(result.middle, "BB middle")

    def test_band_ordering(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test upper > middle > lower for all valid values."""
        bb = BollingerBands()
        result = bb.calculate(sample_ohlcv_series)

        valid = (
            ~np.isnan(result.upper)
            & ~np.isnan(result.middle)
            & ~np.isnan(result.lower)
        )

        # Upper must always be above middle
        assert np.all(result.upper[valid] >= result.middle[valid])
        # Middle must always be above lower
        assert np.all(result.middle[valid] >= result.lower[valid])

    def test_width_positive(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test band width is non-negative."""
        bb = BollingerBands()
        result = bb.calculate(sample_ohlcv_series)

        valid_widths = result.width[~np.isnan(result.width)]
        assert np.all(valid_widths >= 0)

    def test_flat_prices_zero_std(self, flat_price_series: OHLCVSeries) -> None:
        """Test Bollinger Bands with flat prices produce zero-width bands."""
        bb = BollingerBands(period=20)
        result = bb.calculate(flat_price_series)

        valid = ~np.isnan(result.upper) & ~np.isnan(result.lower)

        # With constant prices, std dev = 0 but ddof=1 may give NaN for small windows
        # Upper should equal lower (or very close) for flat prices
        # Since ddof=1 with N=period gives non-zero only if there's variance
        # For truly flat data, all values in window are identical -> std = 0
        np.testing.assert_allclose(
            result.upper[valid],
            result.lower[valid],
            atol=1e-6,
            err_msg="Flat prices should produce zero-width bands",
        )

    def test_is_squeezed(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test squeeze detection returns bool."""
        bb = BollingerBands()
        result = bb.calculate(sample_ohlcv_series)

        squeezed = result.is_squeezed(percentile=10)
        assert isinstance(squeezed, bool)

    def test_is_squeezed_invalid_percentile_raises(
        self, sample_ohlcv_series: OHLCVSeries
    ) -> None:
        """Test squeeze raises ValueError for invalid percentile."""
        bb = BollingerBands()
        result = bb.calculate(sample_ohlcv_series)

        with pytest.raises(ValueError, match="Percentile must be in"):
            result.is_squeezed(percentile=0)

        with pytest.raises(ValueError, match="Percentile must be in"):
            result.is_squeezed(percentile=101)

    def test_is_at_upper(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test upper band detection returns bool."""
        bb = BollingerBands()
        result = bb.calculate(sample_ohlcv_series)

        at_upper = result.is_at_upper()
        assert isinstance(at_upper, bool)

    def test_is_at_lower(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test lower band detection returns bool."""
        bb = BollingerBands()
        result = bb.calculate(sample_ohlcv_series)

        at_lower = result.is_at_lower()
        assert isinstance(at_lower, bool)

    def test_calculate_insufficient_data_raises(
        self, minimal_series: OHLCVSeries
    ) -> None:
        """Test Bollinger Bands raises ValueError with insufficient data."""
        bb = BollingerBands(period=20)

        with pytest.raises(ValueError, match="requires at least 20 bars"):
            bb.calculate(minimal_series)

    def test_current_and_previous(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test current and previous properties (based on middle band)."""
        bb = BollingerBands()
        result = bb.calculate(sample_ohlcv_series)

        current = result.current
        previous = result.previous

        assert isinstance(current, float)
        assert isinstance(previous, float)

    def test_repr(self) -> None:
        """Test string representation."""
        bb = BollingerBands(period=30, multiplier=2.5)
        repr_str = repr(bb)

        assert "BollingerBands" in repr_str
        assert "30" in repr_str
        assert "2.5" in repr_str

    def test_result_repr(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test BollingerResult string representation."""
        bb = BollingerBands()
        result = bb.calculate(sample_ohlcv_series)
        repr_str = repr(result)

        assert "BollingerResult" in repr_str
        assert "BB_20_2.0" in repr_str
