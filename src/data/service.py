"""High-level market data service.

Decision: DEC-2026-02-10-001 - Use python-binance SDK wrapper
Decision: DEC-2026-02-10-004 - Async-first architecture
Decision: DEC-2026-02-11-003 - Three-layer caching architecture
PRD Feature H - Data Quality Validation

This module provides a high-level market data service that combines
fetching, validation, and caching for a clean API.

Features:
- Single and multi-symbol OHLCV fetching
- Automatic data quality validation (PRD Feature H)
- OHLCV caching with TTL strategy by timeframe
- Current price fetching
- Historical data with pagination
- Concurrent multi-symbol fetching
- Validation can be disabled for testing

Cache Strategy:
- TTL by timeframe: 1m=30s, 5m=60s, 1h=300s, 1d=1800s
- Cache key format: "ohlcv:{symbol}:{timeframe}:{limit}"
- Cache-aside pattern with get_or_set
- Target: >90% cache hit rate
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from src.brokers.binance.client import BinanceClient
from src.core.exceptions import MarketDataError
from src.data.cache import CacheManager, InMemoryCache
from src.data.market_data import MarketDataFetcher, OHLCV, OHLCVSeries
from src.data.validators import DataValidator, ValidationResult, ACTION_REJECT
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Cache TTL strategy by timeframe (seconds)
# Decision: DEC-2026-02-11-003 - TTL aligned with data freshness requirements
OHLCV_CACHE_TTLS = {
    "1m": 30,      # 30 seconds for 1-minute candles
    "5m": 60,      # 1 minute for 5-minute candles
    "15m": 180,    # 3 minutes for 15-minute candles
    "1h": 300,     # 5 minutes for 1-hour candles
    "4h": 900,     # 15 minutes for 4-hour candles
    "1d": 1800,    # 30 minutes for daily candles
}


class MarketDataService:
    """High-level market data service.

    Decision: DEC-2026-02-10-001 - Use python-binance SDK wrapper
    Decision: DEC-2026-02-11-003 - Three-layer caching architecture
    PRD Feature H - Data Quality Validation

    This service provides a clean API for fetching and validating market data.
    It combines MarketDataFetcher, DataValidator, and CacheManager for a
    unified interface with caching support.

    Features:
    - Automatic validation (PRD Feature H)
    - OHLCV caching with TTL strategy (>90% hit rate target)
    - Multi-symbol concurrent fetching
    - Current price fetching
    - Historical data with pagination
    - Configurable validation

    Attributes:
        fetcher: MarketDataFetcher instance.
        validator: DataValidator instance.
        cache_manager: CacheManager instance (optional).
        client: BinanceClient instance (direct access if needed).
    """

    def __init__(
        self,
        client: BinanceClient | None = None,
        validator: DataValidator | None = None,
        cache_manager: CacheManager | None = None,
        enable_cache: bool = True,
    ) -> None:
        """Initialize market data service.

        Decision: DEC-2026-02-11-003 - Cache layer integration

        Args:
            client: BinanceClient instance (creates new if None).
            validator: DataValidator instance (creates new if None).
            cache_manager: CacheManager instance (creates new InMemoryCache if None and enable_cache=True).
            enable_cache: Whether to enable caching (default True).
        """
        self.client = client or BinanceClient(testnet=True)
        self.fetcher = MarketDataFetcher(client=self.client)
        self.validator = validator or DataValidator()

        # Initialize cache if enabled
        if enable_cache:
            if cache_manager is None:
                # Create default in-memory cache
                backend = InMemoryCache()
                self.cache_manager: Optional[CacheManager] = CacheManager(backend)
            else:
                self.cache_manager = cache_manager
        else:
            self.cache_manager = None

        logger.info(
            "market_data_service_initialized",
            cache_enabled=self.cache_manager is not None,
        )

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
        validate: bool = True,
        check_freshness: bool = True,
        use_cache: bool = True,
    ) -> tuple[OHLCVSeries, ValidationResult | None]:
        """Fetch OHLCV data with optional validation and caching.

        Decision: DEC-2026-02-11-003 - Three-layer caching architecture
        PRD Feature H - Data Quality Validation enabled by default.

        Cache Strategy:
        - Cache key: "ohlcv:{symbol}:{timeframe}:{limit}"
        - TTL by timeframe (see OHLCV_CACHE_TTLS)
        - Cache-aside pattern: check cache → fetch if miss → cache result

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT").
            timeframe: Candlestick timeframe (e.g., "1m", "5m", "1h", "1d").
            limit: Number of candles to fetch (max 1000, default 500).
            validate: Whether to validate data quality (default True).
            check_freshness: Whether to check price age (default True).
            use_cache: Whether to use cache (default True, ignored if cache disabled).

        Returns:
            Tuple of (OHLCVSeries, ValidationResult or None).
            ValidationResult is None if validate=False.

        Raises:
            MarketDataError: If fetch fails or validation rejects data.

        Example:
            >>> service = MarketDataService()
            >>> # First call - cache miss (fetches from API, ~500ms)
            >>> series1, result1 = await service.get_ohlcv("BTCUSDT", "1h", limit=100)
            >>> # Second call - cache hit (<1ms)
            >>> series2, result2 = await service.get_ohlcv("BTCUSDT", "1h", limit=100)
        """
        logger.info(
            "fetching_ohlcv",
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            validate=validate,
            use_cache=use_cache and self.cache_manager is not None,
        )

        try:
            # Check if caching is enabled and requested
            if use_cache and self.cache_manager is not None:
                # Generate cache key
                cache_key = f"ohlcv:{symbol}:{timeframe}:{limit}"

                # Get TTL for this timeframe (default to 60s if not found)
                ttl = OHLCV_CACHE_TTLS.get(timeframe, 60)

                # Define factory function for cache-aside pattern
                async def fetch_and_validate() -> tuple[OHLCVSeries, ValidationResult | None]:
                    """Fetch data from API and validate."""
                    # Fetch data
                    series = await self.fetcher.fetch_ohlcv(
                        symbol=symbol,
                        timeframe=timeframe,
                        limit=limit,
                    )

                    # Validate if requested
                    validation_result = None
                    if validate:
                        validation_result = self.validator.validate_ohlcv_series(
                            series=series,
                            check_freshness=check_freshness,
                            check_gaps=True,
                            check_price_changes=True,
                        )

                        # Check if validation rejects data
                        if validation_result.action == ACTION_REJECT:
                            logger.error(
                                "data_validation_rejected",
                                symbol=symbol,
                                timeframe=timeframe,
                                issues=validation_result.issues,
                            )
                            raise MarketDataError(
                                symbol=symbol,
                                reason=f"Data validation failed: {', '.join(validation_result.issues)}",
                                details=validation_result.metadata,
                            )

                        logger.debug(
                            "data_validated",
                            symbol=symbol,
                            timeframe=timeframe,
                            action=validation_result.action,
                            warnings_count=len(validation_result.warnings),
                        )

                    logger.debug(
                        "ohlcv_fetched_from_api",
                        symbol=symbol,
                        timeframe=timeframe,
                        count=len(series),
                    )

                    return series, validation_result

                # Use cache-aside pattern: get from cache or compute
                result = await self.cache_manager.get_or_set(
                    key=cache_key,
                    factory=fetch_and_validate,
                    ttl=ttl,
                )

                logger.info(
                    "ohlcv_fetched_successfully",
                    symbol=symbol,
                    timeframe=timeframe,
                    count=len(result[0]),
                    validated=validate,
                    cached=True,
                )

                return result

            else:
                # Cache disabled or not requested - fetch directly
                series = await self.fetcher.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=limit,
                )

                # Validate if requested
                validation_result = None
                if validate:
                    validation_result = self.validator.validate_ohlcv_series(
                        series=series,
                        check_freshness=check_freshness,
                        check_gaps=True,
                        check_price_changes=True,
                    )

                    # Check if validation rejects data
                    if validation_result.action == ACTION_REJECT:
                        logger.error(
                            "data_validation_rejected",
                            symbol=symbol,
                            timeframe=timeframe,
                            issues=validation_result.issues,
                        )
                        raise MarketDataError(
                            symbol=symbol,
                            reason=f"Data validation failed: {', '.join(validation_result.issues)}",
                            details=validation_result.metadata,
                        )

                    logger.info(
                        "data_validated",
                        symbol=symbol,
                        timeframe=timeframe,
                        action=validation_result.action,
                        warnings_count=len(validation_result.warnings),
                    )

                logger.info(
                    "ohlcv_fetched_successfully",
                    symbol=symbol,
                    timeframe=timeframe,
                    count=len(series),
                    validated=validate,
                    cached=False,
                )

                return series, validation_result

        except Exception as e:
            logger.error(
                "ohlcv_fetch_failed",
                symbol=symbol,
                timeframe=timeframe,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_multiple_ohlcv(
        self,
        symbols: list[str],
        timeframe: str,
        limit: int = 500,
        validate: bool = True,
    ) -> dict[str, tuple[OHLCVSeries, ValidationResult | None]]:
        """Fetch OHLCV data for multiple symbols concurrently.

        Decision: DEC-2026-02-10-004 - Async-first architecture

        This method fetches data for multiple symbols in parallel for
        better performance.

        Args:
            symbols: List of trading pair symbols (e.g., ["BTCUSDT", "ETHUSDT"]).
            timeframe: Candlestick timeframe (e.g., "1h").
            limit: Number of candles to fetch per symbol (max 1000).
            validate: Whether to validate data quality (default True).

        Returns:
            Dictionary mapping symbol to (OHLCVSeries, ValidationResult or None).
            Symbols that failed to fetch are excluded.

        Raises:
            ValueError: If symbols list is empty.
        """
        if not symbols:
            raise ValueError("Symbols list cannot be empty")

        logger.info(
            "fetching_multiple_ohlcv",
            symbols=symbols,
            symbols_count=len(symbols),
            timeframe=timeframe,
            limit=limit,
        )

        # Create tasks for concurrent fetching
        tasks = [
            self.get_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                validate=validate,
                check_freshness=False,  # Skip freshness for batch fetches
            )
            for symbol in symbols
        ]

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        data: dict[str, tuple[OHLCVSeries, ValidationResult | None]] = {}
        failed: list[str] = []

        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.warning(
                    "symbol_fetch_failed",
                    symbol=symbol,
                    error=str(result),
                )
                failed.append(symbol)
            else:
                data[symbol] = result

        logger.info(
            "multiple_ohlcv_fetched",
            symbols_count=len(symbols),
            success_count=len(data),
            failed_count=len(failed),
            failed_symbols=failed if failed else None,
        )

        return data

    async def get_prices(
        self,
        symbols: list[str],
    ) -> dict[str, float]:
        """Get current prices for multiple symbols.

        This is a convenience method that fetches the most recent
        candle close price for each symbol.

        Args:
            symbols: List of trading pair symbols (e.g., ["BTCUSDT", "ETHUSDT"]).

        Returns:
            Dictionary mapping symbol to current price.
            Symbols that failed to fetch are excluded.

        Raises:
            ValueError: If symbols list is empty.
        """
        if not symbols:
            raise ValueError("Symbols list cannot be empty")

        logger.info(
            "fetching_current_prices",
            symbols=symbols,
            symbols_count=len(symbols),
        )

        # Fetch 1 candle per symbol (most recent)
        data = await self.get_multiple_ohlcv(
            symbols=symbols,
            timeframe="1m",
            limit=1,
            validate=False,  # Skip validation for price queries
        )

        # Extract close prices
        prices: dict[str, float] = {}
        for symbol, (series, _) in data.items():
            if len(series) > 0:
                prices[symbol] = series.candles[-1].close

        logger.info(
            "current_prices_fetched",
            symbols_count=len(prices),
            prices=prices,
        )

        return prices

    async def get_historical(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime | None = None,
        validate: bool = True,
    ) -> tuple[OHLCVSeries, ValidationResult | None]:
        """Fetch historical OHLCV data with pagination.

        Decision: DEC-2026-02-08-003 - Timezone-aware timestamps

        This method automatically handles pagination for large date ranges.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT").
            timeframe: Candlestick timeframe (e.g., "1h", "4h", "1d").
            start_date: Start date (timezone-aware).
            end_date: End date (timezone-aware, defaults to now).
            validate: Whether to validate data quality (default True).

        Returns:
            Tuple of (OHLCVSeries, ValidationResult or None).

        Raises:
            MarketDataError: If fetch fails or validation rejects data.
            ValueError: If dates invalid or not timezone-aware.
        """
        # Default end_date to now if not provided
        if end_date is None:
            end_date = datetime.now(timezone.utc)

        logger.info(
            "fetching_historical_data",
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            validate=validate,
        )

        try:
            # Fetch historical data with pagination
            series = await self.fetcher.fetch_historical_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
            )

            # Validate if requested
            validation_result = None
            if validate:
                validation_result = self.validator.validate_ohlcv_series(
                    series=series,
                    check_freshness=False,  # Historical data won't be fresh
                    check_gaps=True,
                    check_price_changes=True,
                )

                # Check if validation rejects data
                if validation_result.action == ACTION_REJECT:
                    logger.error(
                        "historical_validation_rejected",
                        symbol=symbol,
                        timeframe=timeframe,
                        issues=validation_result.issues,
                    )
                    raise MarketDataError(
                        symbol=symbol,
                        reason=f"Historical data validation failed: {', '.join(validation_result.issues)}",
                        details=validation_result.metadata,
                    )

                logger.info(
                    "historical_data_validated",
                    symbol=symbol,
                    timeframe=timeframe,
                    action=validation_result.action,
                    warnings_count=len(validation_result.warnings),
                )

            logger.info(
                "historical_data_fetched_successfully",
                symbol=symbol,
                timeframe=timeframe,
                count=len(series),
                validated=validate,
            )

            return series, validation_result

        except Exception as e:
            logger.error(
                "historical_fetch_failed",
                symbol=symbol,
                timeframe=timeframe,
                error=str(e),
                exc_info=True,
            )
            raise

    def set_validation_threshold(self, key: str, value: float | int | str) -> None:
        """Update a validation threshold.

        Convenience method to update DataValidator thresholds.

        Args:
            key: Threshold key (e.g., "max_price_age_seconds").
            value: New threshold value.

        Raises:
            ValueError: If key is invalid.
        """
        self.validator.set_threshold(key, value)

        logger.info(
            "validation_threshold_updated",
            key=key,
            value=value,
        )

    def get_validation_thresholds(self) -> dict[str, float | int | str]:
        """Get current validation thresholds.

        Returns:
            Dictionary of threshold key-value pairs.
        """
        return self.validator.get_thresholds()

    def get_rate_limit_stats(self) -> dict[str, float | int]:
        """Get current rate limit usage statistics.

        Returns:
            Dictionary with rate limit statistics from BinanceClient.
        """
        return self.client.get_rate_limit_stats()

    async def get_cache_stats(self) -> dict[str, int] | None:
        """Get cache statistics.

        Decision: DEC-2026-02-11-003 - Cache observability

        Returns:
            Dictionary with cache statistics (size, keys) or None if cache disabled.

        Example:
            >>> service = MarketDataService()
            >>> stats = await service.get_cache_stats()
            >>> print(f"Cache size: {stats['size']} entries")
        """
        if self.cache_manager is None:
            return None

        # Access InMemoryCache backend for stats
        backend = self.cache_manager.backend
        if hasattr(backend, "size") and hasattr(backend, "keys"):
            size = await backend.size()
            keys = await backend.keys()

            logger.debug("cache_stats_retrieved", size=size, keys_count=len(keys))

            return {
                "size": size,
                "keys_count": len(keys),
            }

        return None

    async def clear_cache(self) -> bool:
        """Clear all cached data.

        Decision: DEC-2026-02-11-003 - Cache management

        Returns:
            True if cache cleared, False if cache disabled.

        Example:
            >>> service = MarketDataService()
            >>> await service.clear_cache()
            True
        """
        if self.cache_manager is None:
            return False

        # Clear cache backend
        result = await self.cache_manager.backend.clear()

        logger.info("cache_cleared")

        return result
