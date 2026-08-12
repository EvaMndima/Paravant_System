"""Tests for indicator base classes.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage

Tests for IndicatorResult and Indicator abstract base class.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.indicators.base import Indicator, IndicatorResult
from src.data.market_data import OHLCVSeries


class TestIndicatorResult:
    """Tests for IndicatorResult class."""

    def test_init(self):
        """Test IndicatorResult initialization."""
        values = np.array([np.nan, np.nan, 1.0, 2.0, 3.0], dtype=np.float64)
        params = {"period": 2}

        result = IndicatorResult(
            name="TEST",
            values=values,
            params=params,
        )

        assert result.name == "TEST"
        assert len(result.values) == 5
        assert result.params == {"period": 2}

    def test_current_property(self):
        """Test current property returns last non-NaN value."""
        values = np.array([np.nan, np.nan, 1.0, 2.0, 3.0], dtype=np.float64)
        result = IndicatorResult("TEST", values, {})

        assert result.current == 3.0

    def test_current_with_trailing_nan(self):
        """Test current skips trailing NaN values."""
        values = np.array([1.0, 2.0, 3.0, np.nan, np.nan], dtype=np.float64)
        result = IndicatorResult("TEST", values, {})

        assert result.current == 3.0

    def test_current_all_nan_raises(self):
        """Test current raises ValueError if all NaN."""
        values = np.array([np.nan, np.nan, np.nan], dtype=np.float64)
        result = IndicatorResult("TEST", values, {})

        with pytest.raises(ValueError, match="No valid values available"):
            _ = result.current

    def test_previous_property(self):
        """Test previous property returns second-to-last non-NaN value."""
        values = np.array([np.nan, np.nan, 1.0, 2.0, 3.0], dtype=np.float64)
        result = IndicatorResult("TEST", values, {})

        assert result.previous == 2.0

    def test_previous_insufficient_values_raises(self):
        """Test previous raises ValueError if insufficient values."""
        values = np.array([np.nan, np.nan, np.nan, 1.0], dtype=np.float64)
        result = IndicatorResult("TEST", values, {})

        with pytest.raises(ValueError, match="Insufficient valid values"):
            _ = result.previous

    def test_to_list(self):
        """Test to_list converts to Python list."""
        values = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        result = IndicatorResult("TEST", values, {})

        result_list = result.to_list()

        assert isinstance(result_list, list)
        assert len(result_list) == 3
        assert result_list == [1.0, 2.0, 3.0]


class ConcreteIndicator(Indicator):
    """Concrete implementation for testing abstract base class."""

    def calculate(self, series: OHLCVSeries) -> IndicatorResult:
        """Simple test implementation."""
        values = np.full(len(series), 42.0, dtype=np.float64)
        return IndicatorResult("CONCRETE", values, {})


class TestIndicator:
    """Tests for Indicator abstract base class."""

    def test_cannot_instantiate_abstract(self):
        """Test cannot instantiate Indicator directly."""
        with pytest.raises(TypeError):
            _ = Indicator()  # type: ignore

    def test_concrete_implementation(self, sample_ohlcv_series: OHLCVSeries):
        """Test concrete implementation works."""
        indicator = ConcreteIndicator()
        result = indicator.calculate(sample_ohlcv_series)

        assert isinstance(result, IndicatorResult)
        assert result.name == "CONCRETE"
        assert len(result.values) == len(sample_ohlcv_series)
        assert result.current == 42.0

    def test_required_periods_default(self):
        """Test required_periods static method."""
        periods = Indicator.required_periods(14)

        assert periods == 14
