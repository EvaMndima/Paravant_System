"""Tests for IndicatorFactory.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
"""

from __future__ import annotations

import pytest

from src.core.indicators import (EMA, MACD, RSI, BollingerBands, Indicator,
                                 IndicatorFactory)
from src.data.market_data import OHLCVSeries


class TestIndicatorFactory:
    """Tests for IndicatorFactory."""

    def test_create_rsi(self):
        """Test creating RSI indicator."""
        factory = IndicatorFactory()

        rsi = factory.create("rsi", period=14)

        assert isinstance(rsi, RSI)
        assert rsi.period == 14

    def test_create_ema(self):
        """Test creating EMA indicator."""
        factory = IndicatorFactory()

        ema = factory.create("ema", period=20)

        assert isinstance(ema, EMA)
        assert ema.period == 20

    def test_create_macd(self):
        """Test creating MACD indicator."""
        factory = IndicatorFactory()
 
        # Update to use correct parameter names (fast_period, slow_period, signal_period)
        macd = factory.create("macd", fast_period=12, slow_period=26, signal_period=9)
 
        assert isinstance(macd, MACD)
        assert macd.fast_period == 12
        assert macd.slow_period == 26
        assert macd.signal_period == 9

    def test_create_case_insensitive(self):
        """Test indicator creation is case-insensitive."""
        factory = IndicatorFactory()

        rsi1 = factory.create("rsi")
        rsi2 = factory.create("RSI")
        rsi3 = factory.create("RsI")

        assert type(rsi1) is type(rsi2) is type(rsi3)

    def test_create_with_alias(self):
        """Test creating indicator with alias."""
        factory = IndicatorFactory()

        # "bb" is alias for "bollinger"
        bb = factory.create("bb", period=20, multiplier=2.0)

        assert isinstance(bb, BollingerBands)
        assert bb.period == 20
        assert bb.multiplier == 2.0

    def test_create_unknown_indicator_raises(self):
        """Test creating unknown indicator raises ValueError."""
        factory = IndicatorFactory()

        with pytest.raises(ValueError, match="Unknown indicator"):
            factory.create("unknown_indicator")

    def test_create_invalid_params_raises(self):
        """Test creating indicator with invalid params raises TypeError."""
        factory = IndicatorFactory()

        # RSI doesn't accept 'invalid_param'
        with pytest.raises(TypeError, match="Invalid parameters"):
            factory.create("rsi", invalid_param=123)

    def test_list_indicators(self):
        """Test listing all registered indicators."""
        factory = IndicatorFactory()

        indicators = factory.list_indicators()

        # Should return sorted list
        assert isinstance(indicators, list)
        assert len(indicators) > 0
        assert indicators == sorted(indicators)

        # Should include main indicators and aliases
        assert "rsi" in indicators
        assert "ema" in indicators
        assert "macd" in indicators
        assert "bb" in indicators  # alias
        assert "bollinger" in indicators  # full name

    def test_is_registered(self):
        """Test checking if indicator is registered."""
        factory = IndicatorFactory()

        assert factory.is_registered("rsi")
        assert factory.is_registered("RSI")  # case-insensitive
        assert factory.is_registered("bb")  # alias
        assert not factory.is_registered("unknown")

    def test_get_indicator_class(self):
        """Test getting indicator class without instantiation."""
        factory = IndicatorFactory()

        rsi_class = factory.get_indicator_class("rsi")

        assert rsi_class == RSI
        assert issubclass(rsi_class, Indicator)

    def test_get_unknown_class_raises(self):
        """Test getting unknown indicator class raises ValueError."""
        factory = IndicatorFactory()

        with pytest.raises(ValueError, match="Unknown indicator"):
            factory.get_indicator_class("unknown")

    def test_register_custom_indicator(self, sample_ohlcv_series: OHLCVSeries):
        """Test registering custom indicator."""
        from src.core.indicators.base import IndicatorResult

        class CustomIndicator(Indicator):
            def calculate(self, series: OHLCVSeries) -> IndicatorResult:
                import numpy as np
                values = np.full(len(series), 42.0, dtype=np.float64)
                return IndicatorResult("CUSTOM", values, {})

        factory = IndicatorFactory()
        factory.register("custom", CustomIndicator)

        # Should be able to create custom indicator
        assert factory.is_registered("custom")

        custom = factory.create("custom")
        assert isinstance(custom, CustomIndicator)

        # Should be able to use it
        result = custom.calculate(sample_ohlcv_series)
        assert result.name == "CUSTOM"

    def test_register_empty_name_raises(self):
        """Test registering indicator with empty name raises ValueError."""
        from src.core.indicators.base import Indicator

        class DummyIndicator(Indicator):
            def calculate(self, series):
                pass

        factory = IndicatorFactory()

        with pytest.raises(ValueError, match="name cannot be empty"):
            factory.register("", DummyIndicator)

    def test_register_non_indicator_raises(self):
        """Test registering non-Indicator class raises ValueError."""
        factory = IndicatorFactory()

        class NotAnIndicator:
            pass

        with pytest.raises(ValueError, match="must inherit from Indicator"):
            factory.register("invalid", NotAnIndicator)  # type: ignore

    def test_unregister(self):
        """Test unregistering an indicator."""
        from src.core.indicators.base import IndicatorResult

        class TempIndicator(Indicator):
            def calculate(self, series: OHLCVSeries) -> IndicatorResult:
                import numpy as np
                values = np.full(len(series), 0.0, dtype=np.float64)
                return IndicatorResult("TEMP", values, {})

        factory = IndicatorFactory()
        factory.register("temp", TempIndicator)

        assert factory.is_registered("temp")

        factory.unregister("temp")

        assert not factory.is_registered("temp")

    def test_unregister_unknown_raises(self):
        """Test unregistering unknown indicator raises ValueError."""
        factory = IndicatorFactory()

        with pytest.raises(ValueError, match="not registered"):
            factory.unregister("unknown")
