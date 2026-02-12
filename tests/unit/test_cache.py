"""Tests for caching infrastructure.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-003 - Three-layer caching architecture

Tests for InMemoryCache, CacheManager, and cache integration.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from src.data.cache import CacheBackend, InMemoryCache, CacheManager


class TestInMemoryCache:
    """Tests for InMemoryCache."""

    @pytest.mark.asyncio
    async def test_init(self):
        """Test InMemoryCache initialization."""
        cache = InMemoryCache()

        size = await cache.size()
        assert size == 0

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = InMemoryCache()

        # Set value
        result = await cache.set("key1", "value1")
        assert result is True

        # Get value
        value = await cache.get("key1")
        assert value == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self):
        """Test getting nonexistent key returns None."""
        cache = InMemoryCache()

        value = await cache.get("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_set_with_ttl(self):
        """Test setting value with TTL."""
        cache = InMemoryCache()

        # Set with 1 second TTL
        await cache.set("key1", "value1", ttl=1)

        # Should be available immediately
        value = await cache.get("key1")
        assert value == "value1"

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired
        value = await cache.get("key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_set_zero_ttl_skips_caching(self):
        """Test setting value with TTL=0 skips caching."""
        cache = InMemoryCache()

        result = await cache.set("key1", "value1", ttl=0)
        assert result is False

        # Value should not be cached
        value = await cache.get("key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_set_negative_ttl_fails(self):
        """Test setting value with negative TTL fails."""
        cache = InMemoryCache()

        result = await cache.set("key1", "value1", ttl=-5)
        assert result is False

    @pytest.mark.asyncio
    async def test_set_no_ttl_never_expires(self):
        """Test setting value with no TTL never expires."""
        cache = InMemoryCache()

        await cache.set("key1", "value1", ttl=None)

        # Wait a bit
        await asyncio.sleep(0.5)

        # Should still be available
        value = await cache.get("key1")
        assert value == "value1"

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting cached value."""
        cache = InMemoryCache()

        await cache.set("key1", "value1")

        # Delete
        result = await cache.delete("key1")
        assert result is True

        # Should be gone
        value = await cache.get("key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self):
        """Test deleting nonexistent key returns False."""
        cache = InMemoryCache()

        result = await cache.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing all cached values."""
        cache = InMemoryCache()

        # Add multiple values
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Clear
        result = await cache.clear()
        assert result is True

        # All should be gone
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") is None

        # Size should be zero
        size = await cache.size()
        assert size == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = InMemoryCache()

        # Add entries with different TTLs
        await cache.set("key1", "value1", ttl=1)  # Expires in 1s
        await cache.set("key2", "value2", ttl=10)  # Expires in 10s
        await cache.set("key3", "value3", ttl=None)  # Never expires

        # Wait for first to expire
        await asyncio.sleep(1.1)

        # Cleanup
        removed = await cache.cleanup_expired()
        assert removed == 1

        # Check which values remain
        assert await cache.get("key1") is None  # Expired
        assert await cache.get("key2") == "value2"  # Still valid
        assert await cache.get("key3") == "value3"  # Never expires

    @pytest.mark.asyncio
    async def test_size(self):
        """Test getting cache size."""
        cache = InMemoryCache()

        assert await cache.size() == 0

        await cache.set("key1", "value1")
        assert await cache.size() == 1

        await cache.set("key2", "value2")
        assert await cache.size() == 2

        await cache.delete("key1")
        assert await cache.size() == 1

    @pytest.mark.asyncio
    async def test_keys(self):
        """Test getting all cache keys."""
        cache = InMemoryCache()

        # Add keys
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Get keys
        keys = await cache.keys()
        assert set(keys) == {"key1", "key2", "key3"}

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test concurrent get/set operations are thread-safe."""
        cache = InMemoryCache()

        # Run concurrent operations
        async def set_value(key: str, value: str) -> None:
            await cache.set(key, value)

        async def get_value(key: str) -> Any:
            return await cache.get(key)

        # Set values concurrently
        await asyncio.gather(
            set_value("key1", "value1"),
            set_value("key2", "value2"),
            set_value("key3", "value3"),
        )

        # Get values concurrently
        results = await asyncio.gather(
            get_value("key1"),
            get_value("key2"),
            get_value("key3"),
        )

        assert results == ["value1", "value2", "value3"]


class TestCacheManager:
    """Tests for CacheManager."""

    @pytest.mark.asyncio
    async def test_init(self):
        """Test CacheManager initialization."""
        backend = InMemoryCache()
        manager = CacheManager(backend)

        assert manager.backend == backend

    def test_generate_key_deterministic(self):
        """Test generate_key produces deterministic keys."""
        key1 = CacheManager.generate_key("arg1", "arg2", kwarg1="value1")
        key2 = CacheManager.generate_key("arg1", "arg2", kwarg1="value1")

        # Same inputs = same key
        assert key1 == key2

    def test_generate_key_different_args(self):
        """Test generate_key produces different keys for different args."""
        key1 = CacheManager.generate_key("arg1", "arg2")
        key2 = CacheManager.generate_key("arg1", "arg3")

        # Different args = different keys
        assert key1 != key2

    def test_generate_key_different_kwargs(self):
        """Test generate_key produces different keys for different kwargs."""
        key1 = CacheManager.generate_key(kwarg1="value1")
        key2 = CacheManager.generate_key(kwarg1="value2")

        # Different kwargs = different keys
        assert key1 != key2

    @pytest.mark.asyncio
    async def test_get_and_set(self):
        """Test basic get and set through manager."""
        backend = InMemoryCache()
        manager = CacheManager(backend)

        await manager.set("key1", "value1")
        value = await manager.get("key1")

        assert value == "value1"

    @pytest.mark.asyncio
    async def test_get_or_set_cache_hit(self):
        """Test get_or_set with cache hit."""
        backend = InMemoryCache()
        manager = CacheManager(backend)

        # Pre-populate cache
        await manager.set("key1", "cached_value")

        # Factory should not be called on cache hit
        factory_called = False

        def factory() -> str:
            nonlocal factory_called
            factory_called = True
            return "computed_value"

        # Get from cache
        value = await manager.get_or_set("key1", factory)

        assert value == "cached_value"
        assert factory_called is False  # Factory not called

    @pytest.mark.asyncio
    async def test_get_or_set_cache_miss(self):
        """Test get_or_set with cache miss."""
        backend = InMemoryCache()
        manager = CacheManager(backend)

        # Factory should be called on cache miss
        factory_called = False

        def factory() -> str:
            nonlocal factory_called
            factory_called = True
            return "computed_value"

        # Cache miss - factory called
        value = await manager.get_or_set("key1", factory)

        assert value == "computed_value"
        assert factory_called is True

        # Value should now be cached
        cached_value = await manager.get("key1")
        assert cached_value == "computed_value"

    @pytest.mark.asyncio
    async def test_get_or_set_async_factory(self):
        """Test get_or_set with async factory function."""
        backend = InMemoryCache()
        manager = CacheManager(backend)

        async def async_factory() -> str:
            await asyncio.sleep(0.01)
            return "async_value"

        # Cache miss - async factory called
        value = await manager.get_or_set("key1", async_factory)

        assert value == "async_value"

    @pytest.mark.asyncio
    async def test_get_or_set_with_ttl(self):
        """Test get_or_set caches value with TTL."""
        backend = InMemoryCache()
        manager = CacheManager(backend)

        def factory() -> str:
            return "value"

        # Cache with 1 second TTL
        await manager.get_or_set("key1", factory, ttl=1)

        # Should be available immediately
        value = await manager.get("key1")
        assert value == "value"

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired
        value = await manager.get("key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting through manager."""
        backend = InMemoryCache()
        manager = CacheManager(backend)

        await manager.set("key1", "value1")
        result = await manager.delete("key1")

        assert result is True
        assert await manager.get("key1") is None


class TestCacheIntegration:
    """Integration tests for caching with real usage patterns."""

    @pytest.mark.asyncio
    async def test_indicator_caching_pattern(self):
        """Test typical indicator caching pattern."""
        backend = InMemoryCache()
        manager = CacheManager(backend)

        # Simulate indicator calculation caching
        calculation_count = 0

        def expensive_calculation() -> float:
            nonlocal calculation_count
            calculation_count += 1
            return 42.0

        # Generate cache key for indicator
        symbol = "BTCUSDT"
        timeframe = "1h"
        params = {"period": 14}
        cache_key = f"indicator:RSI:{symbol}:{timeframe}:{params}"

        # First call - cache miss
        result1 = await manager.get_or_set(cache_key, expensive_calculation, ttl=300)
        assert result1 == 42.0
        assert calculation_count == 1

        # Second call - cache hit
        result2 = await manager.get_or_set(cache_key, expensive_calculation, ttl=300)
        assert result2 == 42.0
        assert calculation_count == 1  # Not recalculated

    @pytest.mark.asyncio
    async def test_ohlcv_caching_pattern(self):
        """Test typical OHLCV data caching pattern."""
        backend = InMemoryCache()
        manager = CacheManager(backend)

        # Simulate OHLCV fetching
        fetch_count = 0

        async def fetch_ohlcv() -> dict[str, Any]:
            nonlocal fetch_count
            fetch_count += 1
            await asyncio.sleep(0.01)  # Simulate network delay
            return {"symbol": "BTCUSDT", "data": [1, 2, 3]}

        # Generate cache key
        cache_key = "ohlcv:BTCUSDT:1h:100"

        # First call - API fetch
        data1 = await manager.get_or_set(cache_key, fetch_ohlcv, ttl=60)
        assert data1["symbol"] == "BTCUSDT"
        assert fetch_count == 1

        # Second call - cached
        data2 = await manager.get_or_set(cache_key, fetch_ohlcv, ttl=60)
        assert data2["symbol"] == "BTCUSDT"
        assert fetch_count == 1  # Not fetched again

    @pytest.mark.asyncio
    async def test_cache_key_isolation(self):
        """Test different cache keys don't interfere."""
        backend = InMemoryCache()
        manager = CacheManager(backend)

        # Different symbols should have different cache keys
        await manager.set("ohlcv:BTCUSDT:1h:100", "btc_data")
        await manager.set("ohlcv:ETHUSDT:1h:100", "eth_data")

        # Should retrieve correct values
        btc = await manager.get("ohlcv:BTCUSDT:1h:100")
        eth = await manager.get("ohlcv:ETHUSDT:1h:100")

        assert btc == "btc_data"
        assert eth == "eth_data"

    @pytest.mark.asyncio
    async def test_ttl_strategy_by_timeframe(self):
        """Test TTL varies by timeframe."""
        backend = InMemoryCache()
        manager = CacheManager(backend)

        # Simulate different TTLs for different timeframes
        ttl_strategy = {
            "1m": 30,
            "1h": 300,
            "1d": 1800,
        }

        # Cache with appropriate TTLs
        await manager.set("ohlcv:BTCUSDT:1m:100", "1m_data", ttl=ttl_strategy["1m"])
        await manager.set("ohlcv:BTCUSDT:1h:100", "1h_data", ttl=ttl_strategy["1h"])
        await manager.set("ohlcv:BTCUSDT:1d:100", "1d_data", ttl=ttl_strategy["1d"])

        # All should be available
        assert await manager.get("ohlcv:BTCUSDT:1m:100") == "1m_data"
        assert await manager.get("ohlcv:BTCUSDT:1h:100") == "1h_data"
        assert await manager.get("ohlcv:BTCUSDT:1d:100") == "1d_data"
