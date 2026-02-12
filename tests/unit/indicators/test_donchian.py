"""Tests for Donchian Channels indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.indicators import DonchianChannel
from src.core.indicators.donchian import DonchianResult
from src.data.market_data import OHLCVSeries
from tests.unit.indicators.conftest import (assert_array_not_all_nan,
                                            assert_first_n_nan)


class TestDonchianChannel:
    """Tests for Donchian Channels indicator."""

    def test_init_default_period(self) -> None:
        """Test Donchian initialization with default period."""
        dc = DonchianChannel()

        assert dc.period == 20

    def test_init_custom_period(self) -> None:
        """Test Donchian initialization with custom period."""
        dc = DonchianChannel(period=50)

        assert dc.period == 50

    def test_init_invalid_period_raises(self) -> None:
        """Test Donchian raises ValueError for invalid period."""
        with pytest.raises(ValueError, match="Period must be >= 1"):
            DonchianChannel(period=0)

    def test_calculate_basic(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test basic Donchian Channel calculation."""
        dc = DonchianChannel()
        result = dc.calculate(sample_ohlcv_series)

        assert isinstance(result, DonchianResult)
        assert result.name == "DC_20"
        assert len(result.upper) == len(sample_ohlcv_series)
        assert len(result.middle) == len(sample_ohlcv_series)
        assert len(result.lower) == len(sample_ohlcv_series)
        assert result.params["period"] == 20

    def test_calculate_warmup_period(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test NaN warmup for first period-1 values."""
        dc = DonchianChannel(period=20)
        result = dc.calculate(sample_ohlcv_series)

        assert_first_n_nan(result.upper, 19, "DC upper warmup")
        assert_first_n_nan(result.lower, 19, "DC lower warmup")
        assert_array_not_all_nan(result.upper, "DC upper")

    def test_channel_ordering(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test upper >= middle >= lower for all valid values."""
        dc = DonchianChannel()
        result = dc.calculate(sample_ohlcv_series)

        valid = (
            ~np.isnan(result.upper)
            & ~np.isnan(result.middle)
            & ~np.isnan(result.lower)
        )

        assert np.all(result.upper[valid] >= result.middle[valid])
        assert np.all(result.middle[valid] >= result.lower[valid])

    def test_upper_is_highest_high(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test upper channel equals highest high over period."""
        dc = DonchianChannel(period=5)
        result = dc.calculate(sample_ohlcv_series)

        highs = sample_ohlcv_series.highs

        # Manually verify a few values
        for i in range(4, min(10, len(highs))):
            expected = np.max(highs[i - 4 : i + 1])
            assert result.upper[i] == pytest.approx(expected), (
                f"Upper[{i}] should be highest high of window"
            )

    def test_lower_is_lowest_low(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test lower channel equals lowest low over period."""
        dc = DonchianChannel(period=5)
        result = dc.calculate(sample_ohlcv_series)

        lows = sample_ohlcv_series.lows

        # Manually verify a few values
        for i in range(4, min(10, len(lows))):
            expected = np.min(lows[i - 4 : i + 1])
            assert result.lower[i] == pytest.approx(expected), (
                f"Lower[{i}] should be lowest low of window"
            )

    def test_middle_is_average_of_upper_lower(
        self, sample_ohlcv_series: OHLCVSeries
    ) -> None:
        """Test middle channel = (upper + lower) / 2."""
        dc = DonchianChannel()
        result = dc.calculate(sample_ohlcv_series)

        valid = ~np.isnan(result.upper) & ~np.isnan(result.lower)
        expected_middle = (result.upper[valid] + result.lower[valid]) / 2.0

        np.testing.assert_allclose(
            result.middle[valid], expected_middle, atol=1e-10
        )

    def test_flat_prices_zero_width(self, flat_price_series: OHLCVSeries) -> None:
        """Test flat prices produce zero-width channels."""
        dc = DonchianChannel(period=10)
        result = dc.calculate(flat_price_series)

        valid = ~np.isnan(result.upper) & ~np.isnan(result.lower)

        np.testing.assert_allclose(
            result.upper[valid],
            result.lower[valid],
            atol=1e-6,
            err_msg="Flat prices should produce zero-width channels",
        )

    def test_is_breakout_up(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test upward breakout detection returns bool."""
        dc = DonchianChannel()
        result = dc.calculate(sample_ohlcv_series)

        breakout = result.is_breakout_up()
        assert isinstance(breakout, bool)

    def test_is_breakout_down(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test downward breakout detection returns bool."""
        dc = DonchianChannel()
        result = dc.calculate(sample_ohlcv_series)

        breakout = result.is_breakout_down()
        assert isinstance(breakout, bool)

    def test_calculate_insufficient_data_raises(
        self, minimal_series: OHLCVSeries
    ) -> None:
        """Test Donchian raises ValueError with insufficient data."""
        dc = DonchianChannel(period=20)

        with pytest.raises(ValueError, match="requires at least 20 bars"):
            dc.calculate(minimal_series)

    def test_current_and_previous(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test current and previous properties."""
        dc = DonchianChannel()
        result = dc.calculate(sample_ohlcv_series)

        current = result.current
        previous = result.previous

        assert isinstance(current, float)
        assert isinstance(previous, float)

    def test_repr(self) -> None:
        """Test string representation."""
        dc = DonchianChannel(period=50)
        repr_str = repr(dc)

        assert "DonchianChannel" in repr_str
        assert "50" in repr_str

    def test_result_repr(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test DonchianResult string representation."""
        dc = DonchianChannel()
        result = dc.calculate(sample_ohlcv_series)
        repr_str = repr(result)

        assert "DonchianResult" in repr_str
        assert "DC_20" in repr_str
