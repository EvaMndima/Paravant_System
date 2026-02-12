"""Caching infrastructure for market data and indicators.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-10-004 - Async-first architecture
Decision: DEC-2026-02-11-003 - Three-layer caching architecture

Provides async-safe caching with TTL support to minimize API calls and
improve performance. Reduces 500ms API calls to <1ms cache lookups.

Cache Strategy:
    - InMemoryCache: Dict-based with TTL tracking and periodic cleanup
    - CacheManager: High-level API with key generation and get_or_set
    - TTL by timeframe: 1m=30s, 5m=60s, 1h=300s, 1d=1800s

Target: >80% cache hit rate across OHLCV and indicator calculations.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class CacheBackend(ABC):
    """Abstract cache backend interface.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Defines the contract for cache implementations. All methods are async
    for consistency with the system's async-first architecture.
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found or expired.
        """
        pass

    @abstractmethod
    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds (None = no expiration).

        Returns:
            True if set successfully.
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key.

        Returns:
            True if deleted, False if not found.
        """
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all values from cache.

        Returns:
            True if cleared successfully.
        """
        pass


class InMemoryCache(CacheBackend):
    """In-memory cache with TTL support.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage
    Decision: DEC-2026-02-10-004 - Async-safe with asyncio.Lock

    Dict-based cache with expiration tracking. Thread-safe for async usage
    via asyncio.Lock. Supports periodic cleanup of expired entries.

    Attributes:
        _cache: Dict mapping keys to (value, expiry_time) tuples.
        _lock: Async lock for thread-safe operations.

    Example:
        >>> cache = InMemoryCache()
        >>> await cache.set("key", "value", ttl=60)  # 60 second TTL
        >>> value = await cache.get("key")
        >>> print(value)  # "value"
        >>> await asyncio.sleep(61)
        >>> value = await cache.get("key")
        >>> print(value)  # None (expired)
    """

    def __init__(self, max_size: int = 10000) -> None:
        """Initialize in-memory cache.

        Args:
            max_size: Maximum number of entries before eviction (default 10000).
                     Set to 0 for unlimited (not recommended in production).
        """
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
        self._max_size = max_size

        logger.info("in_memory_cache_initialized", max_size=max_size)

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache, checking TTL expiration.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found or expired.

        Example:
            >>> cache = InMemoryCache()
            >>> await cache.set("user:123", {"name": "Alice"}, ttl=60)
            >>> data = await cache.get("user:123")
            >>> print(data)  # {"name": "Alice"}
        """
        async with self._lock:
            if key not in self._cache:
                logger.debug("cache_miss", key=key)
                return None

            value, expiry = self._cache[key]

            # Check if expired
            if expiry > 0 and time.time() > expiry:
                # Remove expired entry
                del self._cache[key]
                logger.debug("cache_expired", key=key)
                return None

            logger.debug("cache_hit", key=key)
            return value

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL.

        Args:
            key: Cache key.
            value: Value to cache (any serializable type).
            ttl: Time-to-live in seconds (None = no expiration, 0 = immediate expiration).

        Returns:
            True if set successfully.

        Example:
            >>> cache = InMemoryCache()
            >>> # No expiration
            >>> await cache.set("config", {"theme": "dark"})
            >>> # 5 minute expiration
            >>> await cache.set("ohlcv:BTCUSDT:1h", series, ttl=300)
        """
        async with self._lock:
            if ttl is None:
                expiry = 0.0  # 0 = no expiration
            elif ttl == 0:
                # TTL=0 means immediate expiration (don't cache)
                logger.debug("cache_set_skipped_zero_ttl", key=key)
                return False
            elif ttl < 0:
                logger.warning("cache_set_negative_ttl", key=key, ttl=ttl)
                return False
            else:
                expiry = time.time() + ttl

            # Evict expired entries if at capacity
            if (
                self._max_size > 0
                and key not in self._cache
                and len(self._cache) >= self._max_size
            ):
                current_time = time.time()
                # First try evicting expired entries
                expired_keys = [
                    k
                    for k, (_, exp) in self._cache.items()
                    if exp > 0 and current_time > exp
                ]
                for k in expired_keys:
                    del self._cache[k]

                # If still at capacity, evict oldest entry
                if len(self._cache) >= self._max_size:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                    logger.debug("cache_evicted", evicted_key=oldest_key)

            self._cache[key] = (value, expiry)
            logger.debug("cache_set", key=key, ttl=ttl)
            return True

    async def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key.

        Returns:
            True if deleted, False if not found.

        Example:
            >>> cache = InMemoryCache()
            >>> await cache.set("temp", "data")
            >>> deleted = await cache.delete("temp")
            >>> print(deleted)  # True
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug("cache_deleted", key=key)
                return True
            return False

    async def clear(self) -> bool:
        """Clear all values from cache.

        Returns:
            True if cleared successfully.

        Example:
            >>> cache = InMemoryCache()
            >>> await cache.set("key1", "value1")
            >>> await cache.set("key2", "value2")
            >>> await cache.clear()
            >>> print(await cache.size())  # 0
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info("cache_cleared", entries_removed=count)
            return True

    async def cleanup_expired(self) -> int:
        """Remove expired entries from cache.

        Should be called periodically (e.g., every 60 seconds) to prevent
        memory accumulation from expired entries.

        Returns:
            Number of expired entries removed.

        Example:
            >>> cache = InMemoryCache()
            >>> # ... add entries with TTL ...
            >>> await asyncio.sleep(65)
            >>> removed = await cache.cleanup_expired()
            >>> print(f"Removed {removed} expired entries")
        """
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, (_, expiry) in self._cache.items()
                if expiry > 0 and current_time > expiry
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.info("cache_cleanup", expired_count=len(expired_keys))

            return len(expired_keys)

    async def size(self) -> int:
        """Get number of entries in cache.

        Returns:
            Number of cached entries (including expired but not yet cleaned).

        Example:
            >>> cache = InMemoryCache()
            >>> await cache.set("key1", "value1")
            >>> await cache.set("key2", "value2")
            >>> size = await cache.size()
            >>> print(size)  # 2
        """
        async with self._lock:
            return len(self._cache)

    async def keys(self) -> list[str]:
        """Get all keys in cache.

        Returns:
            List of cache keys (including expired but not yet cleaned).

        Example:
            >>> cache = InMemoryCache()
            >>> await cache.set("key1", "value1")
            >>> await cache.set("key2", "value2")
            >>> keys = await cache.keys()
            >>> print(keys)  # ["key1", "key2"]
        """
        async with self._lock:
            return list(self._cache.keys())


class CacheManager:
    """High-level cache manager with key generation and get_or_set pattern.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage
    Decision: DEC-2026-02-11-003 - Deterministic key generation

    Provides convenient caching interface with:
    - Deterministic key generation from args/kwargs
    - get_or_set pattern (cache-aside)
    - Support for sync and async factory functions

    Attributes:
        backend: Cache backend instance (e.g., InMemoryCache).

    Example:
        >>> cache = InMemoryCache()
        >>> manager = CacheManager(cache)
        >>>
        >>> # Generate deterministic key
        >>> key = manager.generate_key("BTCUSDT", "1h", limit=100)
        >>>
        >>> # Get or compute
        >>> async def fetch_data():
        ...     return await fetch_ohlcv("BTCUSDT", "1h", 100)
        >>>
        >>> data = await manager.get_or_set(key, fetch_data, ttl=300)
    """

    def __init__(self, backend: CacheBackend) -> None:
        """Initialize cache manager.

        Args:
            backend: Cache backend instance.
        """
        self.backend = backend

        logger.info("cache_manager_initialized", backend=backend.__class__.__name__)

    @staticmethod
    def generate_key(*args: Any, **kwargs: Any) -> str:
        """Generate deterministic cache key from args and kwargs.

        Uses MD5 hash of JSON-serialized args/kwargs for consistent keys.
        Same input always produces same key.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Cache key string (format: "cache:{md5_hash}").

        Example:
            >>> key1 = CacheManager.generate_key("BTCUSDT", "1h", limit=100)
            >>> key2 = CacheManager.generate_key("BTCUSDT", "1h", limit=100)
            >>> assert key1 == key2  # Deterministic
            >>>
            >>> key3 = CacheManager.generate_key("BTCUSDT", "1h", limit=200)
            >>> assert key1 != key3  # Different params = different key
        """
        # Create dict with args and kwargs
        data = {"args": args, "kwargs": kwargs}

        # Serialize to JSON (sorted keys for determinism)
        json_str = json.dumps(data, sort_keys=True, default=str)

        # Generate MD5 hash
        hash_obj = hashlib.md5(json_str.encode())
        hash_hex = hash_obj.hexdigest()

        return f"cache:{hash_hex}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found.
        """
        return await self.backend.get(key)

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds.

        Returns:
            True if set successfully.
        """
        return await self.backend.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key.

        Returns:
            True if deleted.
        """
        return await self.backend.delete(key)

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]] | Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> Any:
        """Get from cache or compute if missing (cache-aside pattern).

        If value exists in cache, returns it immediately.
        If not, calls factory function, caches result, and returns it.

        Factory can be sync or async function.

        Args:
            key: Cache key.
            factory: Function to compute value if not cached (sync or async).
            ttl: Time-to-live for cached value (seconds).

        Returns:
            Cached or computed value.

        Example:
            >>> manager = CacheManager(InMemoryCache())
            >>>
            >>> # Async factory
            >>> async def fetch_data():
            ...     return await api.get_data()
            >>>
            >>> data = await manager.get_or_set("key", fetch_data, ttl=300)
            >>>
            >>> # Sync factory
            >>> def compute():
            ...     return 42
            >>>
            >>> result = await manager.get_or_set("answer", compute)
        """
        # Try to get from cache
        value = await self.backend.get(key)

        if value is not None:
            logger.debug("cache_hit_get_or_set", key=key)
            return value

        # Cache miss - compute value
        logger.debug("cache_miss_get_or_set", key=key)

        # Call factory (handle both sync and async)
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()

        # Cache the result
        await self.backend.set(key, value, ttl)

        return value
