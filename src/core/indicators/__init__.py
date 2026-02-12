"""Technical indicators module.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-001 - Compute-on-demand indicator strategy
Decision: DEC-2026-02-11-002 - Wilder's smoothing for RSI/ATR

This module provides production-grade technical indicators for the PARAVANT
Trading System. All indicators are:
- Formula-accurate (validated against TradingView)
- Fully type-hinted (100% coverage)
- Optimized for performance (<30ms for 10k bars)
- Comprehensively tested (>90% coverage)

Available Indicators:
    Moving Averages:
        - EMA: Exponential Moving Average
        - SMA: Simple Moving Average

    Momentum Oscillators:
        - RSI: Relative Strength Index (Wilder's smoothing)
        - MACD: Moving Average Convergence Divergence

    Volatility Indicators:
        - ATR: Average True Range (Wilder's smoothing)
        - BollingerBands: Bollinger Bands with squeeze detection

    Trend Indicators:
        - DonchianChannel: Donchian Channels with breakout detection
        - SuperTrend: SuperTrend with trend flip detection
        - ADX: Average Directional Index with +DI/-DI

    Volume Indicators:
        - VWAP: Volume Weighted Average Price
        - VolumeAverage: Volume moving average with spike detection

Usage:
    >>> from src.core.indicators import RSI, EMA, IndicatorFactory, CachedIndicatorCalculator
    >>> from src.data.service import MarketDataService
    >>> from src.data.cache import CacheManager, InMemoryCache
    >>>
    >>> # Direct indicator usage
    >>> service = MarketDataService()
    >>> series, _ = await service.get_ohlcv("BTCUSDT", "1h", limit=100)
    >>>
    >>> rsi = RSI(period=14)
    >>> result = rsi.calculate(series)
    >>> print(f"RSI: {result.current:.2f}")
    >>>
    >>> # Factory pattern
    >>> factory = IndicatorFactory()
    >>> ema = factory.create("ema", period=20)
    >>> result = ema.calculate(series)
    >>>
    >>> # Cached indicators (recommended for production)
    >>> cache = CacheManager(InMemoryCache())
    >>> cached_rsi = CachedIndicatorCalculator(rsi, cache)
    >>> result = await cached_rsi.calculate(series, "BTCUSDT", "1h")  # Cache miss
    >>> result = await cached_rsi.calculate(series, "BTCUSDT", "1h")  # Cache hit (<1ms)
"""

from __future__ import annotations

from src.core.indicators import utils
from src.core.indicators.adx import ADX, ADXResult
from src.core.indicators.atr import ATR
from src.core.indicators.base import Indicator, IndicatorResult
from src.core.indicators.bollinger import BollingerBands, BollingerResult
from src.core.indicators.cached import CachedIndicatorCalculator
from src.core.indicators.donchian import DonchianChannel, DonchianResult
from src.core.indicators.ema import EMA
from src.core.indicators.factory import IndicatorFactory
from src.core.indicators.macd import MACD, MACDResult
from src.core.indicators.rsi import RSI
from src.core.indicators.sma import SMA
from src.core.indicators.supertrend import SuperTrend, SuperTrendResult
from src.core.indicators.volume import VolumeAverage
from src.core.indicators.vwap import VWAP, VWAPResult

__all__ = [
    # Base classes
    "Indicator",
    "IndicatorResult",
    # Moving averages
    "EMA",
    "SMA",
    # Momentum oscillators
    "RSI",
    "MACD",
    "MACDResult",
    # Volatility indicators
    "ATR",
    "BollingerBands",
    "BollingerResult",
    # Trend indicators
    "DonchianChannel",
    "DonchianResult",
    "SuperTrend",
    "SuperTrendResult",
    "ADX",
    "ADXResult",
    # Volume indicators
    "VWAP",
    "VWAPResult",
    "VolumeAverage",
    # Infrastructure
    "IndicatorFactory",
    "CachedIndicatorCalculator",
    "utils",
]

__version__ = "1.0.0"
