"""Cached indicator calculator wrapper.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-003 - Three-layer caching architecture
Decision: DEC-2026-02-11-001 - Compute-on-demand indicator strategy

Provides caching wrapper for indicator calculations to minimize redundant
computation. Uses the same TTL strategy as OHLCV cache.

Cache Strategy:
- Key format: "indicator:{name}:{symbol}:{timeframe}:{params_hash}"
- TTL matches OHLCV TTL for same timeframe
- Cache hit reduces calculation from ~20ms to <1ms
- Target: >80% cache hit rate

Example:
    >>> from src.core.indicators import RSI
    >>> from src.data.cache import CacheManager, InMemoryCache
    >>> from src.data.service import MarketDataService
    >>>
    >>> # Setup
    >>> cache = CacheManager(InMemoryCache())
    >>> rsi = RSI(period=14)
    >>> cached_rsi = CachedIndicatorCalculator(rsi, cache)
    >>> service = MarketDataService()
    >>>
    >>> # Fetch data
    >>> series, _ = await service.get_ohlcv("BTCUSDT", "1h", limit=100)
    >>>
    >>> # First call - cache miss (calculates)
    >>> result1 = await cached_rsi.calculate(series, symbol="BTCUSDT", timeframe="1h")
    >>>
    >>> # Second call - cache hit (instant)
    >>> result2 = await cached_rsi.calculate(series, symbol="BTCUSDT", timeframe="1h")
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.core.indicators.base import Indicator, IndicatorResult
from src.data.cache import CacheManager
from src.data.market_data import OHLCVSeries
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Cache TTL strategy by timeframe (seconds)
# Decision: DEC-2026-02-11-003 - Same TTL as OHLCV cache for consistency
INDICATOR_CACHE_TTLS = {
    "1m": 30,      # 30 seconds for 1-minute candles
    "5m": 60,      # 1 minute for 5-minute candles
    "15m": 180,    # 3 minutes for 15-minute candles
    "1h": 300,     # 5 minutes for 1-hour candles
    "4h": 900,     # 15 minutes for 4-hour candles
    "1d": 1800,    # 30 minutes for daily candles
}


class CachedIndicatorCalculator:
    """Cached indicator calculator wrapper.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage
    Decision: DEC-2026-02-11-003 - Indicator caching layer

    Wraps any Indicator implementation with caching support. Uses cache-aside
    pattern: check cache → calculate if miss → cache result.

    Cache key includes indicator name, symbol, timeframe, and parameter hash
    to ensure correct cache isolation across different configurations.

    Attributes:
        indicator: Wrapped indicator instance.
        cache_manager: CacheManager for storing results.

    Example:
        >>> rsi = RSI(period=14)
        >>> cached_rsi = CachedIndicatorCalculator(rsi, cache_manager)
        >>>
        >>> # Calculate (cache miss)
        >>> result1 = await cached_rsi.calculate(series, "BTCUSDT", "1h")
        >>>
        >>> # Calculate (cache hit - instant)
        >>> result2 = await cached_rsi.calculate(series, "BTCUSDT", "1h")
    """

    def __init__(
        self,
        indicator: Indicator,
        cache_manager: CacheManager,
    ) -> None:
        """Initialize cached indicator calculator.

        Args:
            indicator: Indicator instance to wrap.
            cache_manager: CacheManager for caching results.

        Example:
            >>> from src.core.indicators import EMA
            >>> from src.data.cache import CacheManager, InMemoryCache
            >>>
            >>> cache = CacheManager(InMemoryCache())
            >>> ema = EMA(period=20)
            >>> cached_ema = CachedIndicatorCalculator(ema, cache)
        """
        self.indicator = indicator
        self.cache_manager = cache_manager

        logger.info(
            "cached_indicator_calculator_initialized",
            indicator=indicator.__class__.__name__,
        )

    @staticmethod
    def _generate_params_hash(params: dict[str, Any]) -> str:
        """Generate deterministic hash from indicator parameters.

        Uses MD5 hash of JSON-serialized parameters for consistent cache keys.

        Args:
            params: Indicator parameters dictionary.

        Returns:
            Hexadecimal hash string.

        Example:
            >>> params = {"period": 14, "multiplier": 2.0}
            >>> hash1 = CachedIndicatorCalculator._generate_params_hash(params)
            >>> hash2 = CachedIndicatorCalculator._generate_params_hash(params)
            >>> assert hash1 == hash2  # Deterministic
        """
        # Serialize to JSON (sorted keys for determinism)
        json_str = json.dumps(params, sort_keys=True, default=str)

        # Generate MD5 hash
        hash_obj = hashlib.md5(json_str.encode())

        return hash_obj.hexdigest()[:16]  # Use first 16 chars (64-bit keyspace)

    def _generate_cache_key(
        self,
        symbol: str,
        timeframe: str,
        params: dict[str, Any],
    ) -> str:
        """Generate cache key for indicator result.

        Key format: "indicator:{name}:{symbol}:{timeframe}:{params_hash}"

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT").
            timeframe: Candlestick timeframe (e.g., "1h").
            params: Indicator parameters.

        Returns:
            Cache key string.

        Example:
            >>> calculator = CachedIndicatorCalculator(RSI(period=14), cache)
            >>> key = calculator._generate_cache_key("BTCUSDT", "1h", {"period": 14})
            >>> print(key)  # "indicator:RSI:BTCUSDT:1h:abc12345"
        """
        indicator_name = self.indicator.__class__.__name__
        params_hash = self._generate_params_hash(params)

        return f"indicator:{indicator_name}:{symbol}:{timeframe}:{params_hash}"

    async def calculate(
        self,
        series: OHLCVSeries,
        symbol: str,
        timeframe: str,
        use_cache: bool = True,
    ) -> IndicatorResult[float]:
        """Calculate indicator with caching.

        Decision: DEC-2026-02-11-003 - Cache-aside pattern

        Cache-aside pattern:
        1. Generate cache key from symbol/timeframe/params
        2. Check cache for existing result
        3. If cache hit, return cached result (skip calculation)
        4. If cache miss, calculate indicator
        5. Cache result with TTL based on timeframe
        6. Return result

        Args:
            series: OHLCV series from MarketDataService.
            symbol: Trading pair symbol (e.g., "BTCUSDT").
            timeframe: Candlestick timeframe (e.g., "1h").
            use_cache: Whether to use cache (default True).

        Returns:
            IndicatorResult with calculated or cached values.

        Raises:
            ValueError: If indicator calculation fails.

        Example:
            >>> service = MarketDataService()
            >>> series, _ = await service.get_ohlcv("BTCUSDT", "1h", limit=100)
            >>>
            >>> rsi = RSI(period=14)
            >>> cached_rsi = CachedIndicatorCalculator(rsi, cache_manager)
            >>>
            >>> # First call - cache miss (~15ms)
            >>> result1 = await cached_rsi.calculate(series, "BTCUSDT", "1h")
            >>> print(f"RSI: {result1.current}")
            >>>
            >>> # Second call - cache hit (<1ms)
            >>> result2 = await cached_rsi.calculate(series, "BTCUSDT", "1h")
            >>> print(f"RSI: {result2.current}")  # Same value, much faster
        """
        indicator_name = self.indicator.__class__.__name__

        logger.debug(
            "calculating_indicator",
            indicator=indicator_name,
            symbol=symbol,
            timeframe=timeframe,
            use_cache=use_cache,
        )

        if not use_cache:
            # Cache disabled - calculate directly
            logger.debug(
                "cache_disabled",
                indicator=indicator_name,
                symbol=symbol,
                timeframe=timeframe,
            )

            result = self.indicator.calculate(series)

            logger.debug(
                "indicator_calculated",
                indicator=indicator_name,
                symbol=symbol,
                timeframe=timeframe,
                cached=False,
            )

            return result

        # Get indicator parameters for cache key
        # Dynamically extract params from indicator instance
        params = self._extract_indicator_params()

        # Generate cache key
        cache_key = self._generate_cache_key(symbol, timeframe, params)

        # Get TTL for this timeframe (default to 60s if not found)
        ttl = INDICATOR_CACHE_TTLS.get(timeframe, 60)

        # Define factory function for cache-aside pattern
        def calculate_indicator() -> IndicatorResult[float]:
            """Calculate indicator (cache miss path)."""
            logger.debug(
                "indicator_cache_miss",
                indicator=indicator_name,
                symbol=symbol,
                timeframe=timeframe,
                cache_key=cache_key,
            )

            return self.indicator.calculate(series)

        # Use cache-aside pattern: get from cache or compute
        cached_result: IndicatorResult[float] = await self.cache_manager.get_or_set(
            key=cache_key,
            factory=calculate_indicator,
            ttl=ttl,
        )

        logger.debug(
            "indicator_calculated",
            indicator=indicator_name,
            symbol=symbol,
            timeframe=timeframe,
            cached=True,
        )

        return cached_result

    def _extract_indicator_params(self) -> dict[str, Any]:
        """Extract indicator parameters for cache key.

        Dynamically introspects indicator instance to find relevant parameters.
        Looks for common parameter attributes: period, multiplier, fast, slow, signal.

        Returns:
            Dictionary of indicator parameters.

        Example:
            >>> rsi = RSI(period=14)
            >>> calculator = CachedIndicatorCalculator(rsi, cache)
            >>> params = calculator._extract_indicator_params()
            >>> print(params)  # {"period": 14}
        """
        params: dict[str, Any] = {}

        # Common indicator parameters
        param_names = [
            "period",
            "multiplier",
            "fast",
            "slow",
            "signal",
            "fast_period",      # MACD
            "slow_period",      # MACD
            "signal_period",    # MACD
            "deviation",
            "atr_period",
            "atr_multiplier",
        ]

        for param_name in param_names:
            if hasattr(self.indicator, param_name):
                params[param_name] = getattr(self.indicator, param_name)

        return params

    async def invalidate_cache(
        self,
        symbol: str,
        timeframe: str,
    ) -> bool:
        """Invalidate cached result for specific symbol/timeframe.

        Useful for forcing recalculation when data changes unexpectedly.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT").
            timeframe: Candlestick timeframe (e.g., "1h").

        Returns:
            True if cache entry deleted, False if not found.

        Example:
            >>> cached_rsi = CachedIndicatorCalculator(rsi, cache_manager)
            >>> await cached_rsi.invalidate_cache("BTCUSDT", "1h")
            True
        """
        params = self._extract_indicator_params()
        cache_key = self._generate_cache_key(symbol, timeframe, params)

        result = await self.cache_manager.delete(cache_key)

        logger.info(
            "indicator_cache_invalidated",
            indicator=self.indicator.__class__.__name__,
            symbol=symbol,
            timeframe=timeframe,
            deleted=result,
        )

        return result

    def __repr__(self) -> str:
        """String representation of cached indicator calculator.

        Returns:
            String with indicator name.
        """
        return f"CachedIndicatorCalculator({self.indicator!r})"
