"""Tests for CachedIndicatorCalculator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-003 - Three-layer caching architecture
"""

from __future__ import annotations

import pytest

from src.core.indicators import EMA, MACD, RSI, BollingerBands
from src.core.indicators.cached import (INDICATOR_CACHE_TTLS,
                                        CachedIndicatorCalculator)
from src.data.cache import CacheManager, InMemoryCache
from src.data.market_data import OHLCVSeries


@pytest.fixture
def cache_manager() -> CacheManager:
    """Create CacheManager with InMemoryCache for testing."""
    return CacheManager(InMemoryCache())


class TestCachedIndicatorCalculator:
    """Tests for CachedIndicatorCalculator."""

    def test_init(self, cache_manager: CacheManager) -> None:
        """Test CachedIndicatorCalculator initialization."""
        rsi = RSI(period=14)
        cached = CachedIndicatorCalculator(rsi, cache_manager)

        assert cached.indicator is rsi
        assert cached.cache_manager is cache_manager

    def test_generate_params_hash_deterministic(self) -> None:
        """Test params hash is deterministic for same input."""
        params = {"period": 14, "multiplier": 2.0}
        hash1 = CachedIndicatorCalculator._generate_params_hash(params)
        hash2 = CachedIndicatorCalculator._generate_params_hash(params)

        assert hash1 == hash2, "Same params should produce same hash"

    def test_generate_params_hash_different_for_different_params(self) -> None:
        """Test params hash differs for different input."""
        hash1 = CachedIndicatorCalculator._generate_params_hash({"period": 14})
        hash2 = CachedIndicatorCalculator._generate_params_hash({"period": 20})

        assert hash1 != hash2, "Different params should produce different hash"

    def test_generate_cache_key_format(self, cache_manager: CacheManager) -> None:
        """Test cache key follows expected format."""
        rsi = RSI(period=14)
        cached = CachedIndicatorCalculator(rsi, cache_manager)

        key = cached._generate_cache_key("BTCUSDT", "1h", {"period": 14})

        assert key.startswith("indicator:RSI:BTCUSDT:1h:")
        assert len(key.split(":")) == 5

    def test_different_indicators_different_keys(
        self, cache_manager: CacheManager
    ) -> None:
        """Test different indicator types produce different cache keys."""
        rsi = RSI(period=14)
        ema = EMA(period=14)

        cached_rsi = CachedIndicatorCalculator(rsi, cache_manager)
        cached_ema = CachedIndicatorCalculator(ema, cache_manager)

        key_rsi = cached_rsi._generate_cache_key("BTCUSDT", "1h", {"period": 14})
        key_ema = cached_ema._generate_cache_key("BTCUSDT", "1h", {"period": 14})

        assert key_rsi != key_ema, "Different indicators should produce different keys"

    def test_extract_indicator_params_rsi(
        self, cache_manager: CacheManager
    ) -> None:
        """Test param extraction for RSI (single period param)."""
        rsi = RSI(period=14)
        cached = CachedIndicatorCalculator(rsi, cache_manager)

        params = cached._extract_indicator_params()

        assert params["period"] == 14

    def test_extract_indicator_params_macd(
        self, cache_manager: CacheManager
    ) -> None:
        """Test param extraction for MACD includes fast/slow/signal periods.

        This is a critical test verifying the bug fix: MACD uses fast_period,
        slow_period, signal_period attributes (not fast, slow, signal).
        """
        macd = MACD(fast_period=8, slow_period=21, signal_period=5)
        cached = CachedIndicatorCalculator(macd, cache_manager)

        params = cached._extract_indicator_params()

        assert params["fast_period"] == 8
        assert params["slow_period"] == 21
        assert params["signal_period"] == 5

    def test_macd_different_configs_different_keys(
        self, cache_manager: CacheManager
    ) -> None:
        """Test MACD with different configs produce different cache keys.

        Regression test for cache key collision bug: MACD(8,21,5) and
        MACD(12,26,9) must produce different keys.
        """
        macd1 = MACD(fast_period=8, slow_period=21, signal_period=5)
        macd2 = MACD(fast_period=12, slow_period=26, signal_period=9)

        cached1 = CachedIndicatorCalculator(macd1, cache_manager)
        cached2 = CachedIndicatorCalculator(macd2, cache_manager)

        key1 = cached1._generate_cache_key(
            "BTCUSDT", "1h", cached1._extract_indicator_params()
        )
        key2 = cached2._generate_cache_key(
            "BTCUSDT", "1h", cached2._extract_indicator_params()
        )

        assert key1 != key2, (
            "Different MACD configs must produce different cache keys"
        )

    def test_extract_indicator_params_bollinger(
        self, cache_manager: CacheManager
    ) -> None:
        """Test param extraction for BollingerBands (period + multiplier)."""
        bb = BollingerBands(period=20, multiplier=2.5)
        cached = CachedIndicatorCalculator(bb, cache_manager)

        params = cached._extract_indicator_params()

        assert params["period"] == 20
        assert params["multiplier"] == 2.5

    @pytest.mark.asyncio
    async def test_calculate_cache_miss(
        self, sample_ohlcv_series: OHLCVSeries, cache_manager: CacheManager
    ) -> None:
        """Test first calculation is a cache miss (calculates)."""
        rsi = RSI(period=14)
        cached = CachedIndicatorCalculator(rsi, cache_manager)

        result = await cached.calculate(sample_ohlcv_series, "BTCUSDT", "1h")

        assert result is not None
        assert result.name == "RSI_14"

    @pytest.mark.asyncio
    async def test_calculate_cache_hit(
        self, sample_ohlcv_series: OHLCVSeries, cache_manager: CacheManager
    ) -> None:
        """Test second calculation returns cached result (cache hit)."""
        rsi = RSI(period=14)
        cached = CachedIndicatorCalculator(rsi, cache_manager)

        result1 = await cached.calculate(sample_ohlcv_series, "BTCUSDT", "1h")
        result2 = await cached.calculate(sample_ohlcv_series, "BTCUSDT", "1h")

        # Both should return valid results
        assert result1 is not None
        assert result2 is not None
        # Second call should return the same cached object
        assert result1 is result2

    @pytest.mark.asyncio
    async def test_calculate_cache_disabled(
        self, sample_ohlcv_series: OHLCVSeries, cache_manager: CacheManager
    ) -> None:
        """Test calculation with cache disabled (always calculates)."""
        rsi = RSI(period=14)
        cached = CachedIndicatorCalculator(rsi, cache_manager)

        result = await cached.calculate(
            sample_ohlcv_series, "BTCUSDT", "1h", use_cache=False
        )

        assert result is not None
        assert result.name == "RSI_14"

    @pytest.mark.asyncio
    async def test_invalidate_cache(
        self, sample_ohlcv_series: OHLCVSeries, cache_manager: CacheManager
    ) -> None:
        """Test cache invalidation deletes entry."""
        rsi = RSI(period=14)
        cached = CachedIndicatorCalculator(rsi, cache_manager)

        # First call populates cache
        await cached.calculate(sample_ohlcv_series, "BTCUSDT", "1h")

        # Invalidate
        deleted = await cached.invalidate_cache("BTCUSDT", "1h")
        assert deleted is True

        # Second invalidation should return False (not found)
        deleted_again = await cached.invalidate_cache("BTCUSDT", "1h")
        assert deleted_again is False

    def test_indicator_cache_ttls_structure(self) -> None:
        """Test INDICATOR_CACHE_TTLS has expected timeframes."""
        assert "1m" in INDICATOR_CACHE_TTLS
        assert "5m" in INDICATOR_CACHE_TTLS
        assert "15m" in INDICATOR_CACHE_TTLS
        assert "1h" in INDICATOR_CACHE_TTLS
        assert "4h" in INDICATOR_CACHE_TTLS
        assert "1d" in INDICATOR_CACHE_TTLS

        # TTLs should be positive integers
        for timeframe, ttl in INDICATOR_CACHE_TTLS.items():
            assert ttl > 0, f"TTL for {timeframe} should be positive"

    def test_repr(self, cache_manager: CacheManager) -> None:
        """Test string representation."""
        rsi = RSI(period=14)
        cached = CachedIndicatorCalculator(rsi, cache_manager)
        repr_str = repr(cached)

        assert "CachedIndicatorCalculator" in repr_str
