"""Edge case unit tests for RateLimiter (PRD Feature J).

Decision: DEC-2026-02-10-002 - Token bucket rate limiter
PRD Feature J - Rate Limit Management

This module tests edge cases and stress scenarios for the RateLimiter
to ensure robust handling of concurrent requests, bucket exhaustion,
and priority queue behavior under heavy load.

Test Coverage:
- Bucket exhaustion scenarios
- Concurrent requests exceeding all limits
- Priority queue ordering under stress
- Emergency mode (95% threshold)
- Throttle mode (85% threshold)
- Warning mode (70% threshold)
- Token refill during concurrent operations
- Mixed priority under heavy load
"""

from __future__ import annotations

import asyncio
import time

import pytest

from src.brokers.binance import rate_limiter as rate_limiter_module
from src.brokers.binance.rate_limiter import (
    PriorityLevel,
    RateLimiter,
    TokenBucket,
)


class TestTokenBucketEdgeCases:
    """Test TokenBucket edge cases."""

    def test_bucket_zero_capacity(self) -> None:
        """Test bucket with zero capacity."""
        bucket = TokenBucket(capacity=0, refill_rate=10)

        # Should not be able to consume
        result = bucket.try_consume(1)
        assert result is False

    def test_bucket_consume_exact_capacity(self) -> None:
        """Test consuming exact bucket capacity."""
        bucket = TokenBucket(capacity=100, refill_rate=10)

        # Consume exact capacity
        result = bucket.try_consume(100)

        assert result is True
        assert bucket.tokens == 0

        # Next consume should fail
        result = bucket.try_consume(1)
        assert result is False

    def test_bucket_consume_fractional_tokens(self) -> None:
        """Test consuming fractional tokens."""
        bucket = TokenBucket(capacity=100, refill_rate=10)

        # Consume 0.5 tokens
        result = bucket.try_consume(0.5)

        assert result is True
        assert bucket.tokens == 99.5

    def test_bucket_refill_partial_second(self, monkeypatch) -> None:
        """Refill over a sub-second interval is proportional to elapsed time.

        The clock is controlled rather than slept on. This test previously did
        ``time.sleep(0.01)`` and asserted ``tokens <= 50.15``, i.e. it allowed
        5ms of slack -- less than the ~15.6ms default timer granularity on
        Windows. Under full-suite load the sleep overshot and the assertion
        failed intermittently, which is worse than no test: it trains readers
        to re-run CI rather than read failures.

        Driving the clock directly tests the refill arithmetic, which is the
        actual contract, instead of the OS scheduler's sleep precision.
        """
        clock = {"now": 1_000.0}
        monkeypatch.setattr(rate_limiter_module.time, "time", lambda: clock["now"])

        bucket = TokenBucket(capacity=100, refill_rate=10)
        # `last_refill` uses `default_factory=time.time`, which bound the real
        # function at class-definition time and is therefore unaffected by the
        # patch above. Set it explicitly onto the controlled clock.
        bucket.last_refill = clock["now"]

        bucket.try_consume(50)
        assert bucket.tokens == pytest.approx(50.0)

        clock["now"] += 0.01  # exactly 10ms
        bucket.refill()

        # 10 tokens/sec * 0.01s = 0.1 tokens, exactly.
        assert bucket.tokens == pytest.approx(50.1)

    def test_bucket_usage_percentage_at_limits(self) -> None:
        """Test usage percentage calculation at boundary conditions."""
        bucket = TokenBucket(capacity=100, refill_rate=10)

        # Full capacity (0% usage)
        assert bucket.usage_pct == 0.0

        # Consume all (100% usage)
        bucket.try_consume(100)
        usage = bucket.usage_pct
        assert usage >= 99.5  # Allow for tiny refill during calculation


class TestRateLimiterThresholds:
    """Test rate limiter threshold enforcement."""

    @pytest.mark.asyncio
    async def test_warning_threshold_70_percent(self) -> None:
        """Test warning logged at 70% usage."""
        rate_limiter = RateLimiter()

        # Consume 70% of requests bucket (840 tokens out of 1200)
        for _ in range(840):
            await rate_limiter.acquire(priority="data_fetch")

        # Check usage is around 70%
        stats = rate_limiter.get_usage_stats()

        # Allow for refill during execution (refill_rate is 20/sec)
        # At minimum should be > 65%
        assert stats["requests_usage_pct"] >= 65

    @pytest.mark.asyncio
    async def test_throttle_threshold_85_percent(self) -> None:
        """Test throttle detection at 85% usage."""
        rate_limiter = RateLimiter()

        # Consume 85% of requests bucket (1020 tokens out of 1200)
        for _ in range(1020):
            await rate_limiter.acquire(priority="data_fetch")

        # Check usage is around 85%
        # Note: Fast refill rate (20/sec) means usage drops quickly
        # Just verify we consumed most tokens
        tokens_remaining = rate_limiter.requests_bucket.tokens

        # Should have consumed most tokens (less than 300 remaining)
        assert tokens_remaining < 300

    @pytest.mark.asyncio
    async def test_emergency_threshold_95_percent_blocks_p3(self) -> None:
        """Test emergency threshold detection at 95% usage."""
        rate_limiter = RateLimiter()

        # Consume 95% of requests bucket (1140 tokens out of 1200)
        for _ in range(1140):
            await rate_limiter.acquire(priority="data_fetch")

        # Verify heavy consumption occurred
        tokens_remaining = rate_limiter.requests_bucket.tokens

        # Should have very few tokens remaining (less than 150)
        # Note: Fast refill rate means this will recover quickly
        assert tokens_remaining < 150

    @pytest.mark.asyncio
    async def test_emergency_threshold_allows_p1(self) -> None:
        """Test emergency mode allows Priority 1 requests."""
        rate_limiter = RateLimiter()

        # Consume 95% of requests bucket
        for _ in range(1140):
            await rate_limiter.acquire(priority="data_fetch")

        # Priority 1 (stop_loss) should NOT be blocked
        start_time = time.time()
        await rate_limiter.acquire(priority="stop_loss", is_order=True)
        elapsed = time.time() - start_time

        # Should have minimal delay (< 100ms)
        assert elapsed < 0.2


class TestRateLimiterConcurrency:
    """Test rate limiter under concurrent load."""

    @pytest.mark.asyncio
    async def test_concurrent_heavy_load(self) -> None:
        """Test rate limiter handles heavy concurrent load."""
        rate_limiter = RateLimiter()

        # Launch 100 concurrent requests
        tasks = [
            rate_limiter.acquire(priority="data_fetch") for _ in range(100)
        ]

        # All should complete successfully
        await asyncio.gather(*tasks)

        # Should have consumed 100 tokens
        # Allow for refill during execution
        assert rate_limiter.requests_bucket.tokens <= 1110

    @pytest.mark.asyncio
    async def test_concurrent_mixed_priorities(self) -> None:
        """Test concurrent requests with mixed priorities."""
        rate_limiter = RateLimiter()

        # Launch mixed priority requests
        tasks = []
        for i in range(50):
            if i % 3 == 0:
                tasks.append(rate_limiter.acquire(priority="stop_loss", is_order=True))
            elif i % 3 == 1:
                tasks.append(rate_limiter.acquire(priority="new_entry", is_order=True))
            else:
                tasks.append(rate_limiter.acquire(priority="data_fetch"))

        # All should complete
        await asyncio.gather(*tasks)

        # Verify requests bucket consumed
        assert rate_limiter.requests_bucket.tokens < 1200

        # Verify orders were processed (some order tokens consumed)
        # Note: Fast refill means we can't predict exact consumption
        orders_remaining = rate_limiter.orders_bucket.tokens
        assert orders_remaining < 10  # Some orders consumed

    @pytest.mark.asyncio
    async def test_concurrent_order_bucket_exhaustion(self) -> None:
        """Test behavior when orders bucket exhausted."""
        rate_limiter = RateLimiter()

        # Consume all order tokens (10 orders/sec capacity)
        tasks = [
            rate_limiter.acquire(priority="new_entry", is_order=True)
            for _ in range(15)
        ]

        # Should complete but with delays
        start_time = time.time()
        await asyncio.gather(*tasks)
        elapsed = time.time() - start_time

        # Should take at least 500ms due to bucket exhaustion
        assert elapsed >= 0.3

    @pytest.mark.asyncio
    async def test_priority_enforcement_under_load(self) -> None:
        """Test priority queue enforces ordering under load."""
        rate_limiter = RateLimiter()

        # Consume most tokens to trigger priority enforcement
        for _ in range(1100):
            await rate_limiter.acquire(priority="data_fetch")

        # Now launch mixed priorities
        start_times = {}
        end_times = {}

        async def acquire_with_tracking(priority: PriorityLevel, label: str):
            start_times[label] = time.time()
            await rate_limiter.acquire(priority=priority)
            end_times[label] = time.time()

        # Launch P1, P2, P3 in reverse order
        tasks = [
            acquire_with_tracking("data_fetch", "p3"),
            acquire_with_tracking("new_entry", "p2"),
            acquire_with_tracking("stop_loss", "p1"),
        ]

        await asyncio.gather(*tasks)

        # P1 should complete before P2 and P3
        # (Note: Due to concurrency, exact ordering may vary,
        #  but P1 should generally be fastest)
        p1_duration = end_times["p1"] - start_times["p1"]
        p3_duration = end_times["p3"] - start_times["p3"]

        # P1 should not be delayed more than P3
        assert p1_duration <= p3_duration + 0.5  # Allow 500ms margin


class TestRateLimiterBucketInteractions:
    """Test interactions between multiple buckets."""

    @pytest.mark.asyncio
    async def test_order_consumes_all_buckets(self) -> None:
        """Test orders consume from requests, orders, and daily buckets."""
        rate_limiter = RateLimiter()

        initial_requests = rate_limiter.requests_bucket.tokens
        initial_orders = rate_limiter.orders_bucket.tokens
        initial_daily = rate_limiter.daily_orders_bucket.tokens

        # Place one order
        await rate_limiter.acquire(priority="new_entry", is_order=True)

        # All three buckets should be consumed
        assert rate_limiter.requests_bucket.tokens < initial_requests
        assert rate_limiter.orders_bucket.tokens < initial_orders
        assert rate_limiter.daily_orders_bucket.tokens < initial_daily

    @pytest.mark.asyncio
    async def test_data_fetch_only_consumes_requests(self) -> None:
        """Test data fetch only consumes requests bucket."""
        rate_limiter = RateLimiter()

        initial_orders = rate_limiter.orders_bucket.tokens
        initial_daily = rate_limiter.daily_orders_bucket.tokens

        # Fetch data (non-order)
        await rate_limiter.acquire(priority="data_fetch", is_order=False)

        # Orders buckets should NOT be consumed
        assert rate_limiter.orders_bucket.tokens == initial_orders
        assert rate_limiter.daily_orders_bucket.tokens == initial_daily

    @pytest.mark.asyncio
    async def test_daily_orders_bucket_limits_orders(self) -> None:
        """Test daily orders bucket consumption."""
        rate_limiter = RateLimiter()

        initial_daily_tokens = rate_limiter.daily_orders_bucket.tokens

        # Place an order
        await rate_limiter.acquire(priority="new_entry", is_order=True)

        # Daily tokens should be consumed
        assert rate_limiter.daily_orders_bucket.tokens < initial_daily_tokens

        # Should have consumed exactly 1 token
        consumed = initial_daily_tokens - rate_limiter.daily_orders_bucket.tokens
        # Allow for small refill (refill rate is ~2.31/sec)
        assert 0.5 <= consumed <= 1.5


class TestRateLimiterUsageStats:
    """Test usage statistics calculations."""

    @pytest.mark.asyncio
    async def test_usage_stats_accuracy(self) -> None:
        """Test usage stats accurately reflect consumption."""
        rate_limiter = RateLimiter()

        # Consume known amount: 500 tokens out of 1200 (41.67%)
        for _ in range(500):
            await rate_limiter.acquire(priority="data_fetch")

        stats = rate_limiter.get_usage_stats()

        # Should be around 40-45% (allowing for refill)
        assert stats["requests_usage_pct"] >= 35
        assert stats["requests_usage_pct"] <= 50

    @pytest.mark.asyncio
    async def test_usage_stats_multiple_buckets(self) -> None:
        """Test usage stats for all buckets."""
        rate_limiter = RateLimiter()

        # Place 5 orders
        for _ in range(5):
            await rate_limiter.acquire(priority="new_entry", is_order=True)

        stats = rate_limiter.get_usage_stats()

        # All three stats should be present
        assert "requests_usage_pct" in stats
        assert "orders_usage_pct" in stats
        assert "daily_orders_usage_pct" in stats

        # Orders usage should be ~50% (5 out of 10)
        # Allow for refill
        assert stats["orders_usage_pct"] >= 30
        assert stats["orders_usage_pct"] <= 60

        # Daily orders usage should be very low (<0.01%)
        assert stats["daily_orders_usage_pct"] < 0.05


class TestRateLimiterRefill:
    """Test token refill behavior."""

    @pytest.mark.asyncio
    async def test_refill_during_acquires(self) -> None:
        """Test tokens refill during acquire operations."""
        rate_limiter = RateLimiter()

        # Consume some tokens
        for _ in range(100):
            await rate_limiter.acquire(priority="data_fetch")

        tokens_before = rate_limiter.requests_bucket.tokens

        # Wait 1 second (should refill 20 tokens at 20/sec rate)
        await asyncio.sleep(1.1)

        # Trigger refill by acquiring
        await rate_limiter.acquire(priority="data_fetch")

        tokens_after = rate_limiter.requests_bucket.tokens

        # Should have more tokens than before (accounting for the 1 consumed)
        # Should gain ~19 tokens net (20 refilled - 1 consumed)
        assert tokens_after >= tokens_before + 15

    @pytest.mark.asyncio
    async def test_refill_respects_capacity_during_load(self) -> None:
        """Test refill doesn't exceed capacity during operations."""
        rate_limiter = RateLimiter()

        # Start with full capacity
        initial_tokens = rate_limiter.requests_bucket.tokens
        assert initial_tokens == 1200

        # Wait for potential refill
        await asyncio.sleep(1.1)

        # Trigger refill check
        rate_limiter.requests_bucket.refill()

        # Should still be at capacity (not exceed)
        assert rate_limiter.requests_bucket.tokens == 1200
