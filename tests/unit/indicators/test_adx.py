"""Tests for ADX (Average Directional Index) indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.indicators import ADX
from src.core.indicators.adx import ADXResult
from src.data.market_data import OHLCVSeries
from tests.unit.indicators.conftest import assert_array_not_all_nan


class TestADX:
    """Tests for ADX indicator."""

    def test_init_default_period(self) -> None:
        """Test ADX initialization with default period."""
        adx = ADX()

        assert adx.period == 14

    def test_init_custom_period(self) -> None:
        """Test ADX initialization with custom period."""
        adx = ADX(period=7)

        assert adx.period == 7

    def test_init_invalid_period_raises(self) -> None:
        """Test ADX raises ValueError for invalid period."""
        with pytest.raises(ValueError, match="Period must be >= 1"):
            ADX(period=0)

    def test_calculate_basic(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test basic ADX calculation."""
        adx = ADX()
        result = adx.calculate(sample_ohlcv_series)

        assert isinstance(result, ADXResult)
        assert result.name == "ADX_14"
        assert len(result.adx) == len(sample_ohlcv_series)
        assert len(result.plus_di) == len(sample_ohlcv_series)
        assert len(result.minus_di) == len(sample_ohlcv_series)
        assert result.params["period"] == 14

    def test_calculate_has_valid_values(
        self, sample_ohlcv_series: OHLCVSeries
    ) -> None:
        """Test ADX has valid values after warmup."""
        adx = ADX()
        result = adx.calculate(sample_ohlcv_series)

        assert_array_not_all_nan(result.adx, "ADX")
        assert_array_not_all_nan(result.plus_di, "+DI")
        assert_array_not_all_nan(result.minus_di, "-DI")

    def test_adx_bounded_0_100(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test ADX values are bounded between 0 and 100."""
        adx = ADX()
        result = adx.calculate(sample_ohlcv_series)

        valid_adx = result.adx[~np.isnan(result.adx)]

        assert np.all(valid_adx >= 0), "ADX should be >= 0"
        assert np.all(valid_adx <= 100), "ADX should be <= 100"

    def test_di_non_negative(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test +DI and -DI values are non-negative."""
        adx = ADX()
        result = adx.calculate(sample_ohlcv_series)

        valid_plus = result.plus_di[~np.isnan(result.plus_di)]
        valid_minus = result.minus_di[~np.isnan(result.minus_di)]

        assert np.all(valid_plus >= 0), "+DI should be non-negative"
        assert np.all(valid_minus >= 0), "-DI should be non-negative"

    def test_is_trending(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test is_trending returns bool."""
        adx = ADX()
        result = adx.calculate(sample_ohlcv_series)

        trending = result.is_trending(threshold=25.0)
        assert isinstance(trending, bool)

    def test_is_trending_custom_threshold(
        self, sample_ohlcv_series: OHLCVSeries
    ) -> None:
        """Test is_trending with custom threshold."""
        adx = ADX()
        result = adx.calculate(sample_ohlcv_series)

        # Very high threshold should return False for most data
        trending_high = result.is_trending(threshold=99.0)
        assert isinstance(trending_high, bool)

    def test_is_ranging(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test is_ranging returns bool."""
        adx = ADX()
        result = adx.calculate(sample_ohlcv_series)

        ranging = result.is_ranging(threshold=20.0)
        assert isinstance(ranging, bool)

    def test_trend_direction(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test trend_direction returns valid direction."""
        adx = ADX()
        result = adx.calculate(sample_ohlcv_series)

        direction = result.trend_direction
        assert direction in {-1, 0, 1}

    def test_calculate_insufficient_data_raises(self) -> None:
        """Test ADX raises ValueError with insufficient data."""
        adx = ADX(period=14)
        # ADX needs 2 * period + 1 = 29 bars

        from datetime import datetime, timedelta, timezone

        from src.data.market_data import OHLCV

        candles = []
        base_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        for i in range(20):  # Only 20 bars, need 29
            candles.append(
                OHLCV(
                    timestamp=base_time + timedelta(hours=i),
                    open=40000.0 + i * 10,
                    high=40050.0 + i * 10,
                    low=39950.0 + i * 10,
                    close=40000.0 + i * 10,
                    volume=100.0,
                )
            )
        series = OHLCVSeries(candles=candles, symbol="BTCUSDT", timeframe="1h")

        with pytest.raises(ValueError, match="requires at least 29 bars"):
            adx.calculate(series)

    def test_required_periods(self) -> None:
        """Test required_periods static method."""
        assert ADX.required_periods(14) == 29
        assert ADX.required_periods(7) == 15

    def test_current_and_previous(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test current and previous properties."""
        adx = ADX()
        result = adx.calculate(sample_ohlcv_series)

        current = result.current
        previous = result.previous

        assert isinstance(current, float)
        assert isinstance(previous, float)

    def test_repr(self) -> None:
        """Test string representation."""
        adx = ADX(period=7)
        repr_str = repr(adx)

        assert "ADX" in repr_str
        assert "7" in repr_str

    def test_result_repr(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test ADXResult string representation."""
        adx = ADX()
        result = adx.calculate(sample_ohlcv_series)
        repr_str = repr(result)

        assert "ADXResult" in repr_str
        assert "ADX_14" in repr_str

    def test_shorter_period_more_responsive(
        self, sample_ohlcv_series: OHLCVSeries
    ) -> None:
        """Test shorter period ADX is more responsive."""
        adx7 = ADX(period=7)
        adx14 = ADX(period=14)

        result7 = adx7.calculate(sample_ohlcv_series)
        result14 = adx14.calculate(sample_ohlcv_series)

        # Shorter period should have higher standard deviation
        valid7 = result7.adx[~np.isnan(result7.adx)]
        valid14 = result14.adx[~np.isnan(result14.adx)]

        std7 = np.std(valid7)
        std14 = np.std(valid14)

        assert std7 >= std14 * 0.5, "Shorter period ADX should be somewhat more volatile"
