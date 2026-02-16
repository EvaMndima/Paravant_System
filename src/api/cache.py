"""Simple in-memory TTL cache for dashboard API endpoints.

Provides time-based cache invalidation without external dependencies.
Uses time.monotonic() for accurate TTL measurement immune to clock drift.

Recommended TTL values:
- Dashboard summary: 10s (near real-time, reduces DB load)
- Equity curve: 60s per time_range (changes slowly)
- Performance metrics: 30s (moderate frequency)
- Positions/trades: NO CACHE (real-time critical)

Decision: DEC-2026-01-15-005 - Monolithic architecture (no Redis)
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

import threading
import time
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)


class TTLCache:
    """Thread-safe in-memory cache with per-entry TTL expiration.

    Usage:
        cache = TTLCache()
        cache.set("dashboard_summary", data, ttl=10.0)
        result = cache.get("dashboard_summary")  # None if expired
    """

    def __init__(self) -> None:
        """Initialize the cache with empty storage."""
        # {key: (value, expiry_monotonic)}
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock: threading.Lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        """Get a cached value if it exists and has not expired.

        Args:
            key: Cache key to look up.

        Returns:
            Cached value or None if missing/expired.
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expiry = entry
            if time.monotonic() > expiry:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: float) -> None:
        """Store a value with a TTL (time-to-live) in seconds.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds (must be positive).

        Raises:
            ValueError: If ttl is not positive.
        """
        if ttl <= 0:
            raise ValueError(f"TTL must be positive, got {ttl}")
        expiry = time.monotonic() + ttl
        with self._lock:
            self._store[key] = (value, expiry)

    def invalidate(self, key: str) -> bool:
        """Remove a specific entry from the cache.

        Args:
            key: Cache key to remove.

        Returns:
            True if entry was found and removed, False otherwise.
        """
        with self._lock:
            return self._store.pop(key, None) is not None

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all entries whose key starts with the given prefix.

        Useful for invalidating all equity curve entries when new data arrives:
            cache.invalidate_prefix("equity:")

        Args:
            prefix: Key prefix to match.

        Returns:
            Number of entries removed.
        """
        with self._lock:
            keys_to_remove = [k for k in self._store if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._store[key]
            return len(keys_to_remove)

    def clear(self) -> int:
        """Remove all entries from the cache.

        Returns:
            Number of entries removed.
        """
        with self._lock:
            count = len(self._store)
            self._store.clear()
            return count

    @property
    def size(self) -> int:
        """Get the number of entries in the cache (including expired).

        Returns:
            Number of entries.
        """
        with self._lock:
            return len(self._store)
