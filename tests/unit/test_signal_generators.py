"""Unit tests for signal generators and factory.

Tests cover:
- TradingSignal validation
- SignalGeneratorFactory registration and lookup
- Individual generator signal generation with synthetic data
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest

from src.core.exceptions import SignalGenerationError, TemplateNotFoundError
from src.core.strategy.factory import SignalGeneratorFactory
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCV, OHLCVSeries
from src.data.models.signal import SignalDirection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_series(
    n_bars: int = 100,
    base_price: float = 42000.0,
    trend: float = 0.001,
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
) -> OHLCVSeries:
    """Create a synthetic OHLCVSeries for testing.

    Generates a trending price series with realistic OHLC relationships
    and sufficient data for all indicator warmup periods.

    Args:
        n_bars: Number of bars to generate.
        base_price: Starting price.
        trend: Per-bar trend factor (positive = uptrend).
        symbol: Trading symbol.
        timeframe: Candle timeframe.

    Returns:
        Synthetic OHLCVSeries.
    """
    candles: list[OHLCV] = []
    price = base_price

    for i in range(n_bars):
        # Add slight trend and noise
        price = price * (1 + trend + np.random.uniform(-0.005, 0.005))

        open_price = price
        high = price * (1 + np.random.uniform(0.001, 0.01))
        low = price * (1 - np.random.uniform(0.001, 0.01))
        close = price * (1 + np.random.uniform(-0.005, 0.005))
        volume = float(np.random.uniform(50, 200))

        # Ensure OHLC relationships hold
        high = max(high, open_price, close)
        low = min(low, open_price, close)

        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)

        candles.append(
            OHLCV(
                timestamp=ts,
                open=round(open_price, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=round(volume, 4),
            )
        )

    return OHLCVSeries(candles=candles, symbol=symbol, timeframe=timeframe)


# ---------------------------------------------------------------------------
# TradingSignal Tests
# ---------------------------------------------------------------------------


class TestTradingSignal:
    """Tests for TradingSignal dataclass validation."""

    def test_valid_signal(self):
        """Test creating a valid TradingSignal."""
        signal = TradingSignal(
            direction=SignalDirection.LONG,
            symbol="BTCUSDT",
            price=42000.0,
            strength=0.8,
            stop_loss=41000.0,
            take_profit=43000.0,
            indicators={"rsi": 55.0},
        )

        assert signal.direction == SignalDirection.LONG
        assert signal.symbol == "BTCUSDT"
        assert signal.price == 42000.0
        assert signal.strength == 0.8

    def test_empty_symbol_raises(self):
        """Test that empty symbol raises ValueError."""
        with pytest.raises(ValueError, match="symbol cannot be empty"):
            TradingSignal(
                direction=SignalDirection.LONG,
                symbol="",
                price=42000.0,
            )

    def test_negative_price_raises(self):
        """Test that negative price raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            TradingSignal(
                direction=SignalDirection.LONG,
                symbol="BTCUSDT",
                price=-1.0,
            )

    def test_nan_price_raises(self):
        """Test that NaN price raises ValueError."""
        with pytest.raises(ValueError, match="finite"):
            TradingSignal(
                direction=SignalDirection.LONG,
                symbol="BTCUSDT",
                price=float("nan"),
            )

    def test_strength_out_of_range_raises(self):
        """Test that strength outside [0, 1] raises ValueError."""
        with pytest.raises(ValueError, match="strength"):
            TradingSignal(
                direction=SignalDirection.LONG,
                symbol="BTCUSDT",
                price=42000.0,
                strength=1.5,
            )

    def test_naive_timestamp_raises(self):
        """Test that naive timestamp raises ValueError."""
        with pytest.raises(ValueError, match="timezone-aware"):
            TradingSignal(
                direction=SignalDirection.LONG,
                symbol="BTCUSDT",
                price=42000.0,
                timestamp=datetime(2024, 1, 1),  # No timezone
            )

    def test_frozen_immutability(self):
        """Test that TradingSignal is immutable (frozen dataclass)."""
        signal = TradingSignal(
            direction=SignalDirection.LONG,
            symbol="BTCUSDT",
            price=42000.0,
        )

        with pytest.raises(AttributeError):
            signal.price = 43000.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SignalGeneratorFactory Tests
# ---------------------------------------------------------------------------


class TestSignalGeneratorFactory:
    """Tests for SignalGeneratorFactory."""

    def test_get_all_builtin_generators(self):
        """Test that all registered generators are present."""
        factory = SignalGeneratorFactory()
        template_ids = factory.list_template_ids()

        expected = [
            "adx_directional_thrust",
            "bb_squeeze_breakout",
            "bb_squeeze_momentum",
            "bear_trend_follower",
            "bull_trend_pullback",
            "cascading_momentum_filter",
            "crypto_wick_reversal",
            "donchian_atr",
            "ema_ribbon_expansion",
            "ema_trend_rsi",
            "heikin_ashi_trend_pulse",
            "ichimoku_cloud_trend",
            "keltner_channel_continuation",
            "keltner_fade_adx",
            "macd_pullback",
            "multi_tf_confluence",
            "obv_trend_divergence",
            "realized_vol_compression_breakout",
            "regime_aware_mean_reversion",
            "roc_momentum_surge",
            "rsi_bb_mean_reversion",
            "rsi_divergence_reversal",
            "stoch_rsi_bull_cross",
            "supertrend_volume_macd",
            "trend_acceleration_momentum",
            "volatility_regime_breakout",
            "volume_balance_breakout",
            "vpt_momentum",
            "vwap_pullback_volume",
        ]

        assert template_ids == expected

    def test_get_generator_returns_correct_type(self):
        """Test that factory returns correct generator type."""
        factory = SignalGeneratorFactory()
        generator = factory.get_generator("ema_trend_rsi")

        assert isinstance(generator, SignalGenerator)
        assert generator.template_id == "ema_trend_rsi"

    def test_get_nonexistent_generator_raises(self):
        """Test that missing template raises TemplateNotFoundError."""
        factory = SignalGeneratorFactory()

        with pytest.raises(TemplateNotFoundError):
            factory.get_generator("nonexistent")

    def test_register_custom_generator(self):
        """Test registering a custom generator."""
        factory = SignalGeneratorFactory()

        class CustomGenerator(SignalGenerator):
            @property
            def template_id(self) -> str:
                return "custom"

            @property
            def min_bars_required(self) -> int:
                return 10

            def generate(self, series, params, symbol):
                return None

        factory.register_generator("custom", CustomGenerator)

        assert factory.has_generator("custom")
        gen = factory.get_generator("custom")
        assert gen.template_id == "custom"

    def test_register_invalid_class_raises(self):
        """Test that registering a non-SignalGenerator raises."""
        factory = SignalGeneratorFactory()

        with pytest.raises(ValueError, match="SignalGenerator subclass"):
            factory.register_generator("bad", str)  # type: ignore[arg-type]

    def test_has_generator(self):
        """Test has_generator check."""
        factory = SignalGeneratorFactory()
        assert factory.has_generator("ema_trend_rsi") is True
        assert factory.has_generator("nonexistent") is False


# ---------------------------------------------------------------------------
# Individual Generator Tests
# ---------------------------------------------------------------------------


class TestEmaTrendRsiGenerator:
    """Tests for EMA Trend + RSI generator."""

    def test_generator_properties(self):
        """Test generator template_id and min_bars."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("ema_trend_rsi")
        assert gen.template_id == "ema_trend_rsi"
        assert gen.min_bars_required > 0

    def test_insufficient_data_returns_none(self):
        """Test that insufficient data returns None."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("ema_trend_rsi")

        # Only 5 bars - not enough
        series = _make_series(n_bars=5)
        params = {
            "fast_ema_period": 12,
            "slow_ema_period": 26,
            "rsi_period": 14,
            "rsi_buy_threshold": 45.0,
            "rsi_sell_threshold": 55.0,
            "rsi_overbought": 75.0,
            "rsi_oversold": 25.0,
            "atr_multiplier": 2.0,
            "atr_period": 14,
        }

        result = gen.generate(series, params, "BTCUSDT")
        assert result is None

    def test_generate_with_sufficient_data(self):
        """Test signal generation with enough data (may or may not signal)."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("ema_trend_rsi")

        series = _make_series(n_bars=250, trend=0.002)
        params = {
            "fast_ema_period": 12,
            "slow_ema_period": 26,
            "rsi_period": 14,
            "rsi_buy_threshold": 45.0,
            "rsi_sell_threshold": 55.0,
            "rsi_overbought": 75.0,
            "rsi_oversold": 25.0,
            "atr_multiplier": 2.0,
            "atr_period": 14,
        }

        # Should not raise - result can be None or TradingSignal
        result = gen.generate(series, params, "BTCUSDT")
        if result is not None:
            assert isinstance(result, TradingSignal)
            assert result.symbol == "BTCUSDT"
            assert result.price > 0

    def test_missing_param_raises_signal_error(self):
        """Test that missing parameters raise SignalGenerationError."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator("ema_trend_rsi")

        series = _make_series(n_bars=250)
        params = {"fast_ema_period": 12}  # Missing most params

        with pytest.raises(SignalGenerationError):
            gen.generate(series, params, "BTCUSDT")


class TestAllGenerators:
    """Smoke tests for all generators."""

    @pytest.mark.parametrize(
        "template_id",
        [
            "ema_trend_rsi",
            "bb_squeeze_breakout",
            "macd_pullback",
            "rsi_bb_mean_reversion",
            "supertrend_volume_macd",
            "donchian_atr",
            "vwap_pullback_volume",
        ],
    )
    def test_generator_exists_and_has_properties(self, template_id):
        """Test that each generator has required properties."""
        factory = SignalGeneratorFactory()
        gen = factory.get_generator(template_id)

        assert gen.template_id == template_id
        assert gen.min_bars_required > 0
        assert repr(gen)  # Should not raise
