"""Unit tests for token bucket rate limiter (PRD Feature J).

Decision: DEC-2026-02-10-002 - Token bucket rate limiter
PRD Feature J - Rate Limit Management

This module tests:
- Token bucket token consumption and refill
- Priority queue ordering (P1 > P2 > P3)
- PRD Feature J thresholds (70% warning, 85% throttle, 95% emergency)
- Rate limiter integration with multiple buckets
"""

from __future__ import annotations

import asyncio
import time

import pytest

from src.brokers.binance.rate_limiter import (
    PRIORITY_ORDER,
    RATE_LIMIT_THRESHOLDS,
    PriorityLevel,
    RateLimiter,
    TokenBucket,
)


class TestTokenBucket:
    """Test TokenBucket token consumption and refill."""

    def test_bucket_initialization(self) -> None:
        """Test bucket starts with full capacity."""
        bucket = TokenBucket(capacity=100, refill_rate=10)

        assert bucket.capacity == 100
        assert bucket.refill_rate == 10
        assert bucket.tokens == 100  # Starts full

    def test_try_consume_success(self) -> None:
        """Test successful token consumption."""
        bucket = TokenBucket(capacity=100, refill_rate=10)

        # Consume 10 tokens
        result = bucket.try_consume(10)

        assert result is True
        assert bucket.tokens == 90

    def test_try_consume_failure(self) -> None:
        """Test failed consumption when not enough tokens."""
        bucket = TokenBucket(capacity=100, refill_rate=10)

        # Consume all tokens
        bucket.try_consume(100)

        # Try to consume more (should fail)
        result = bucket.try_consume(10)

        assert result is False
        assert bucket.tokens < 10  # Tiny refill might happen, but not enough

    def test_token_refill(self) -> None:
        """Test tokens refill over time."""
        bucket = TokenBucket(capacity=100, refill_rate=10)

        # Consume 50 tokens
        bucket.try_consume(50)
        assert bucket.tokens == 50

        # Wait 1 second (should refill 10 tokens)
        time.sleep(1.1)

        # Refill happens on next consume/check
        bucket.refill()

        # Should have ~60 tokens (50 + 10)
        # Allow for scheduling jitter (e.g. 1.2s sleep instead of 1.1s)
        assert bucket.tokens >= 59 and bucket.tokens <= 62

    def test_refill_respects_capacity(self) -> None:
        """Test tokens don't exceed capacity after refill."""
        bucket = TokenBucket(capacity=100, refill_rate=50)

        # Start with full capacity
        assert bucket.tokens == 100

        # Wait for refill
        time.sleep(1.1)
        bucket.refill()

        # Should not exceed capacity
        assert bucket.tokens == 100

    def test_usage_percentage(self) -> None:
        """Test usage percentage calculation."""
        bucket = TokenBucket(capacity=100, refill_rate=10)

        # Consume 70 tokens
        bucket.try_consume(70)

        # Usage should be 70%
        usage = bucket.usage_pct
        assert usage >= 69 and usage <= 71


class TestRateLimiter:
    """Test RateLimiter with priority queue."""

    @pytest.fixture
    def rate_limiter(self) -> RateLimiter:
        """Create RateLimiter instance."""
        return RateLimiter()

    @pytest.mark.asyncio
    async def test_acquire_data_fetch_priority(
        self,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test acquiring tokens for data fetch (Priority 3)."""
        # Acquire for data fetch
        await rate_limiter.acquire(priority="data_fetch", is_order=False)

        # Should consume 1 token from requests bucket
        assert rate_limiter.requests_bucket.tokens < 1200

    @pytest.mark.asyncio
    async def test_acquire_new_entry_priority(
        self,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test acquiring tokens for new entry (Priority 2)."""
        # Acquire for new entry order
        await rate_limiter.acquire(priority="new_entry", is_order=True)

        # Should consume tokens from all buckets
        assert rate_limiter.requests_bucket.tokens < 1200
        assert rate_limiter.orders_bucket.tokens < 10
        assert rate_limiter.daily_orders_bucket.tokens < 200000

    @pytest.mark.asyncio
    async def test_acquire_stop_loss_priority(
        self,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test acquiring tokens for stop loss (Priority 1 - highest)."""
        # Acquire for stop loss order
        await rate_limiter.acquire(priority="stop_loss", is_order=True)

        # Should consume tokens
        assert rate_limiter.requests_bucket.tokens < 1200
        assert rate_limiter.orders_bucket.tokens < 10

    @pytest.mark.asyncio
    async def test_priority_order_constants(self) -> None:
        """Test priority ordering is correct.

        PRD Feature J: Priority 1 > Priority 2 > Priority 3
        """
        # Priority 1 (highest)
        assert PRIORITY_ORDER["stop_loss"] == 1
        assert PRIORITY_ORDER["take_profit"] == 1
        assert PRIORITY_ORDER["kill_switch"] == 1

        # Priority 2 (medium)
        assert PRIORITY_ORDER["new_entry"] == 2

        # Priority 3 (lowest)
        assert PRIORITY_ORDER["data_fetch"] == 3

    @pytest.mark.asyncio
    async def test_rate_limit_thresholds(self) -> None:
        """Test PRD Feature J thresholds are correct."""
        assert RATE_LIMIT_THRESHOLDS["warning_pct"] == 70
        assert RATE_LIMIT_THRESHOLDS["throttle_pct"] == 85
        assert RATE_LIMIT_THRESHOLDS["emergency_pct"] == 95

    @pytest.mark.asyncio
    async def test_multiple_acquires_sequential(
        self,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test multiple sequential acquires."""
        # Acquire 5 times
        for _ in range(5):
            await rate_limiter.acquire(priority="data_fetch")

        # Should have consumed 5 tokens
        # Allow small refill
        assert rate_limiter.requests_bucket.tokens <= 1196

    @pytest.mark.asyncio
    async def test_order_bucket_consumption(
        self,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test orders consume from both requests and orders buckets."""
        initial_requests = rate_limiter.requests_bucket.tokens
        initial_orders = rate_limiter.orders_bucket.tokens

        # Acquire for order
        await rate_limiter.acquire(priority="new_entry", is_order=True)

        # Both buckets should be consumed
        assert rate_limiter.requests_bucket.tokens < initial_requests
        assert rate_limiter.orders_bucket.tokens < initial_orders

    @pytest.mark.asyncio
    async def test_get_usage_stats(
        self,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test getting rate limit usage statistics."""
        stats = rate_limiter.get_usage_stats()

        assert "requests_usage_pct" in stats
        assert "orders_usage_pct" in stats
        assert "daily_orders_usage_pct" in stats

        # Should start near 0% usage
        assert stats["requests_usage_pct"] < 1
        assert stats["orders_usage_pct"] < 1
        assert stats["daily_orders_usage_pct"] < 0.01

    @pytest.mark.asyncio
    async def test_requests_bucket_capacity(
        self,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test requests bucket has correct Binance capacity (1200 req/min)."""
        assert rate_limiter.requests_bucket.capacity == 1200

        # Refill rate should be 20 tokens/second (1200/60)
        assert rate_limiter.requests_bucket.refill_rate == 20

    @pytest.mark.asyncio
    async def test_orders_bucket_capacity(
        self,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test orders bucket has correct Binance capacity (10 orders/sec)."""
        assert rate_limiter.orders_bucket.capacity == 10

        # Refill rate should be 10 tokens/second
        assert rate_limiter.orders_bucket.refill_rate == 10

    @pytest.mark.asyncio
    async def test_daily_orders_bucket_capacity(
        self,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test daily orders bucket has correct Binance capacity (200k/day)."""
        assert rate_limiter.daily_orders_bucket.capacity == 200_000

        # Refill rate should be ~2.31 tokens/second (200000/86400)
        expected_rate = 200_000 / 86400
        assert abs(rate_limiter.daily_orders_bucket.refill_rate - expected_rate) < 0.01


class TestRateLimiterIntegration:
    """Test RateLimiter integration scenarios."""

    @pytest.fixture
    def rate_limiter(self) -> RateLimiter:
        """Create RateLimiter instance."""
        return RateLimiter()

    @pytest.mark.asyncio
    async def test_concurrent_acquires(
        self,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test concurrent token acquisition."""
        # Launch 10 concurrent acquires
        tasks = [
            rate_limiter.acquire(priority="data_fetch") for _ in range(10)
        ]

        # Should all complete successfully
        await asyncio.gather(*tasks)

        # Should have consumed 10 tokens
        # Should have consumed 10 tokens
        # Allow for small refill during execution (refill_rate is 20/sec)
        # Even 100ms would add 2 tokens
        assert rate_limiter.requests_bucket.tokens <= 1195

    @pytest.mark.asyncio
    async def test_usage_stats_after_activity(
        self,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test usage stats reflect activity."""
        # Consume some tokens
        for _ in range(100):
            await rate_limiter.acquire(priority="data_fetch")

        stats = rate_limiter.get_usage_stats()

        # Usage should be around 8-9% (100/1200)
        assert stats["requests_usage_pct"] > 5
        assert stats["requests_usage_pct"] < 15

    @pytest.mark.asyncio
    async def test_mixed_priority_acquires(
        self,
        rate_limiter: RateLimiter,
    ) -> None:
        """Test mixed priority acquires work correctly."""
        # Acquire with different priorities
        await rate_limiter.acquire(priority="stop_loss", is_order=True)  # P1
        await rate_limiter.acquire(priority="new_entry", is_order=True)  # P2
        await rate_limiter.acquire(priority="data_fetch", is_order=False)  # P3

        # All should succeed
        stats = rate_limiter.get_usage_stats()
        assert stats["requests_usage_pct"] < 1  # Very low usage
        assert stats["orders_usage_pct"] < 25  # 2 orders consumed
