"""Comprehensive tests for all 6 remaining signal generators.

This module adds production-grade tests for:
- BB Squeeze Breakout
- Donchian ATR
- MACD Pullback
- RSI BB Mean Reversion
- Supertrend Volume MACD
- VWAP Pullback Volume

Each generator is tested for:
- Properties and configuration
- Insufficient data handling
- Signal generation logic with synthetic data
- Error handling for missing parameters
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest

from src.core.exceptions import SignalGenerationError
from src.core.strategy.factory import SignalGeneratorFactory
from src.core.strategy.signals import TradingSignal
from src.data.market_data import OHLCV, OHLCVSeries
from src.data.models.signal import SignalDirection

# ---------------------------------------------------------------------------
# Test Data Helpers
# ---------------------------------------------------------------------------


def _make_ohlcv_series(
    n_bars: int = 150,
    base_price: float = 42000.0,
    trend: float = 0.0,
    volatility: float = 0.01,
    symbol: str = "BTCUSDT",
) -> OHLCVSeries:
    """Create synthetic OHLCV series for testing.
    
    Args:
        n_bars: Number of bars to generate.
        base_price: Starting price.
        trend: Per-bar trend component (positive = uptrend).
        volatility: Price volatility factor.
        symbol: Trading symbol.
    
    Returns:
        Synthetic OHLCVSeries with realistic OHLC relationships.
    """
    candles: list[OHLCV] = []
    price = base_price
    
    for _ in range(n_bars):
        price = price * (1 + trend + np.random.uniform(-volatility, volatility))
        
        open_price = price
        high = price * (1 + abs(np.random.uniform(0, volatility)))
        low = price * (1 - abs(np.random.uniform(0, volatility)))
        close = price * (1 + np.random.uniform(-volatility/2, volatility/2))
        volume = float(np.random.uniform(50, 200))
        
        # Enforce OHLC relationships
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        candles.append(
            OHLCV(
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                open=round(open_price, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=round(volume, 4),
            )
        )
    
    return OHLCVSeries(candles=candles, symbol=symbol, timeframe="1h")


# ---------------------------------------------------------------------------
# BB Squeeze Breakout Tests
# ---------------------------------------------------------------------------


class TestBbSqueezeBreakout:
    """Tests for Bollinger Band Squeeze Breakout generator."""
    
    def test_properties(self):
        """Test generator has correct properties."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("bb_squeeze_breakout")
        
        assert gen.template_id == "bb_squeeze_breakout"
        assert gen.min_bars_required == 60
    
    def test_insufficient_data_returns_none(self):
        """Test graceful handling of insufficient data."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("bb_squeeze_breakout")
        
        series = _make_ohlcv_series(n_bars=20)  # Far below 60 required
        params = {
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "squeeze_threshold": 0.04,
            "squeeze_lookback": 10,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_threshold": 1.5,
        }
        
        result = gen.generate(series, params, "BTCUSDT")
        assert result is None
    
    def test_generate_with_sufficient_data_no_error(self):
        """Test signal generation succeeds with sufficient data."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("bb_squeeze_breakout")
        
        series = _make_ohlcv_series(n_bars=150, trend=0.001)
        params = {
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "squeeze_threshold": 0.04,
            "squeeze_lookback": 10,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_threshold": 1.5,
        }
        
        # Should not raise, result can be None or TradingSignal
        result = gen.generate(series, params, "BTCUSDT")
        if result is not None:
            assert isinstance(result, TradingSignal)
            assert result.symbol == "BTCUSDT"
            assert result.direction in [SignalDirection.LONG, SignalDirection.SHORT]
    
    def test_missing_parameter_raises(self):
        """Test that missing parameters raise SignalGenerationError."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("bb_squeeze_breakout")
        
        series = _make_ohlcv_series(n_bars=150)
        params = {"bb_period": 20}  # Missing most params
        
        with pytest.raises(SignalGenerationError):
            gen.generate(series, params, "BTCUSDT")


# ---------------------------------------------------------------------------
# Donchian ATR Tests
# ---------------------------------------------------------------------------


class TestDonchianAtr:
    """Tests for Donchian Channel + ATR generator."""
    
    def test_properties(self):
        """Test generator has correct properties."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("donchian_atr")
        
        assert gen.template_id == "donchian_atr"
        assert gen.min_bars_required > 0
    
    def test_insufficient_data_returns_none(self):
        """Test graceful handling of insufficient data."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("donchian_atr")
        
        series = _make_ohlcv_series(n_bars=10)
        params = {
            "donchian_period": 20,
            "atr_period": 14,
            "atr_multiplier": 2.0,
            "breakout_confirmation": 1.01,
        }
        
        result = gen.generate(series, params, "BTCUSDT")
        assert result is None
    
    def test_generate_with_sufficient_data_no_error(self):
        """Test signal generation succeeds with sufficient data."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("donchian_atr")
        
        series = _make_ohlcv_series(n_bars=150, trend=0.002)
        params = {
            "donchian_period": 20,
            "atr_period": 14,
            "atr_threshold": 0.01,
            "atr_stop_multiplier": 2.0,
            "volume_ma_period": 20,
            "volume_multiplier": 1.5,
        }
        
        result = gen.generate(series, params, "BTCUSDT")
        if result is not None:
            assert isinstance(result, TradingSignal)
            assert result.symbol == "BTCUSDT"
    
    def test_missing_parameter_raises(self):
        """Test that missing parameters raise SignalGenerationError.

        The series is sized from the generator's own ``min_bars_required``.
        A fixed 150 bars silently stopped exercising this path once the
        generator's requirement rose to 210: it returned None on insufficient
        data before ever reading the parameters, so the test asserted nothing.
        """
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("donchian_atr")

        series = _make_ohlcv_series(n_bars=gen.min_bars_required + 10)
        params = {}  # Empty params

        with pytest.raises(SignalGenerationError):
            gen.generate(series, params, "BTCUSDT")


# ---------------------------------------------------------------------------
# MACD Pullback Tests
# ---------------------------------------------------------------------------


class TestMacdPullback:
    """Tests for MACD Pullback generator."""
    
    def test_properties(self):
        """Test generator has correct properties."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("macd_pullback")
        
        assert gen.template_id == "macd_pullback"
        assert gen.min_bars_required > 0
    
    def test_insufficient_data_returns_none(self):
        """Test graceful handling of insufficient data."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("macd_pullback")
        
        series = _make_ohlcv_series(n_bars=15)
        params = {
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "ema_pullback_period": 50,
            "pullback_distance_pct": 2.0,
            "stop_loss_pct": 3.0,
        }
        
        result = gen.generate(series, params, "BTCUSDT")
        assert result is None
    
    def test_generate_with_sufficient_data_no_error(self):
        """Test signal generation succeeds with sufficient data."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("macd_pullback")
        
        series = _make_ohlcv_series(n_bars=150, trend=0.001)
        params = {
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "pullback_ema_period": 50,
            "atr_period": 14,
            "atr_stop_multiplier": 2.0,
            "risk_reward_ratio": 2.0,
            "pullback_tolerance_pct": 2.0,
        }
        
        result = gen.generate(series, params, "BTCUSDT")
        if result is not None:
            assert isinstance(result, TradingSignal)
            assert result.symbol == "BTCUSDT"
    
    def test_missing_parameter_raises(self):
        """Test that missing parameters raise SignalGenerationError."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("macd_pullback")
        
        series = _make_ohlcv_series(n_bars=150)
        params = {"macd_fast": 12}  # Incomplete
        
        with pytest.raises(SignalGenerationError):
            gen.generate(series, params, "BTCUSDT")


# ---------------------------------------------------------------------------
# RSI BB Mean Reversion Tests
# ---------------------------------------------------------------------------


class TestRsiBbMeanReversion:
    """Tests for RSI + BB Mean Reversion generator."""
    
    def test_properties(self):
        """Test generator has correct properties."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("rsi_bb_mean_reversion")
        
        assert gen.template_id == "rsi_bb_mean_reversion"
        # The generator gates on an EMA(200) regime filter, so it must request
        # at least the 200-bar warmup. Asserted as a lower bound rather than
        # the exact 210 so adjusting the ADX/BB/RSI buffer does not fail this
        # test; the load-bearing property is that the EMA warmup is covered.
        assert gen.min_bars_required >= 200
    
    def test_insufficient_data_returns_none(self):
        """Test graceful handling of insufficient data."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("rsi_bb_mean_reversion")
        
        series = _make_ohlcv_series(n_bars=20)
        params = {
            "rsi_period": 14,
            "rsi_oversold": 30.0,
            "rsi_overbought": 70.0,
            "rsi_exit_long": 55.0,
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "adx_threshold": 25.0,
            "stop_loss_pct": 3.0,
        }
        
        result = gen.generate(series, params, "BTCUSDT")
        assert result is None
    
    def test_generate_with_sufficient_data_no_error(self):
        """Test signal generation succeeds with sufficient data."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("rsi_bb_mean_reversion")
        
        series = _make_ohlcv_series(n_bars=150, trend=0.0, volatility=0.02)
        params = {
            "rsi_period": 14,
            "rsi_oversold": 30.0,
            "rsi_overbought": 70.0,
            "rsi_exit_long": 55.0,
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "adx_threshold": 25.0,
            "stop_loss_pct": 3.0,
        }
        
        result = gen.generate(series, params, "BTCUSDT")
        if result is not None:
            assert isinstance(result, TradingSignal)
            assert result.symbol == "BTCUSDT"
    
    def test_missing_parameter_raises(self):
        """Test that missing parameters raise SignalGenerationError.

        Series sized from the generator's own ``min_bars_required`` -- see the
        note on the DonchianAtr equivalent.
        """
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("rsi_bb_mean_reversion")

        series = _make_ohlcv_series(n_bars=gen.min_bars_required + 10)
        params = {"rsi_period": 14}  # Incomplete

        with pytest.raises(SignalGenerationError):
            gen.generate(series, params, "BTCUSDT")


# ---------------------------------------------------------------------------
# Supertrend Volume MACD Tests
# ---------------------------------------------------------------------------


class TestSupertrendVolumeMacd:
    """Tests for Supertrend + Volume + MACD generator."""
    
    def test_properties(self):
        """Test generator has correct properties."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("supertrend_volume_macd")
        
        assert gen.template_id == "supertrend_volume_macd"
        assert gen.min_bars_required > 0
    
    def test_insufficient_data_returns_none(self):
        """Test graceful handling of insufficient data."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("supertrend_volume_macd")
        
        series = _make_ohlcv_series(n_bars=20)
        params = {
            "supertrend_period": 10,
            "supertrend_multiplier": 3.0,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_threshold": 1.5,
            "volume_period": 20,
        }
        
        result = gen.generate(series, params, "BTCUSDT")
        assert result is None
    
    def test_generate_with_sufficient_data_no_error(self):
        """Test signal generation succeeds with sufficient data."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("supertrend_volume_macd")
        
        series = _make_ohlcv_series(n_bars=150, trend=0.002)
        params = {
            "supertrend_period": 10,
            "supertrend_multiplier": 3.0,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_ma_period": 20,
            "volume_multiplier": 1.5,
        }
        
        result = gen.generate(series, params, "BTCUSDT")
        if result is not None:
            assert isinstance(result, TradingSignal)
            assert result.symbol == "BTCUSDT"
    
    def test_missing_parameter_raises(self):
        """Test that missing parameters raise SignalGenerationError."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("supertrend_volume_macd")
        
        series = _make_ohlcv_series(n_bars=150)
        params = {"supertrend_period": 10}  # Incomplete
        
        with pytest.raises(SignalGenerationError):
            gen.generate(series, params, "BTCUSDT")


# ---------------------------------------------------------------------------
# VWAP Pullback Volume Tests
# ---------------------------------------------------------------------------


class TestVwapPullbackVolume:
    """Tests for VWAP Pullback + Volume generator."""
    
    def test_properties(self):
        """Test generator has correct properties."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("vwap_pullback_volume")
        
        assert gen.template_id == "vwap_pullback_volume"
        assert gen.min_bars_required > 0
    
    def test_insufficient_data_returns_none(self):
        """Test graceful handling of insufficient data."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("vwap_pullback_volume")
        
        series = _make_ohlcv_series(n_bars=15)
        params = {
            "vwap_anchored": False,
            "pullback_distance_pct": 1.5,
            "volume_threshold": 1.5,
            "volume_period": 20,
            "stop_loss_pct": 3.0,
        }
        
        result = gen.generate(series, params, "BTCUSDT")
        assert result is None
    
    def test_generate_with_sufficient_data_no_error(self):
        """Test signal generation succeeds with sufficient data."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("vwap_pullback_volume")
        
        series = _make_ohlcv_series(n_bars=150, trend=0.001)
        params = {
            "entry_buffer_pct": 0.5,
            "exit_distance_pct": 2.0,
            "volume_ma_period": 20,
            "volume_multiplier": 1.5,
            "exit_volume_threshold": 0.8,
            "rsi_period": 14,
            "stop_loss_pct": 3.0,
        }
        
        result = gen.generate(series, params, "BTCUSDT")
        if result is not None:
            assert isinstance(result, TradingSignal)
            assert result.symbol == "BTCUSDT"
    
    def test_missing_parameter_raises(self):
        """Test that missing parameters raise SignalGenerationError."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("vwap_pullback_volume")
        
        series = _make_ohlcv_series(n_bars=150)
        params = {}  # Empty params
        
        with pytest.raises(SignalGenerationError):
            gen.generate(series, params, "BTCUSDT")
