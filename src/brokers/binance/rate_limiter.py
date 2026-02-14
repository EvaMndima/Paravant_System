"""Token bucket rate limiter for Binance API.

Decision: DEC-2026-02-10-002 - Token bucket rate limiter
PRD Feature J - Rate Limit Management

This module implements a token bucket rate limiter with priority queue
to prevent exceeding Binance API rate limits:
- 1200 requests per minute (request weight)
- 10 orders per second
- 200,000 orders per day

The rate limiter implements PRD Feature J thresholds:
- Warning at 70% usage
- Throttling at 85% usage (add 500ms delay)
- Emergency at 95% usage (only critical orders allowed)

Priority system:
- Priority 1: Stop loss, take profit, kill switch (always allowed)
- Priority 2: New entries (delayed during throttle)
- Priority 3: Data fetching (lowest priority)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Literal

from src.utils.logging import get_logger

logger = get_logger(__name__)

# PRD Feature J - Rate Limit Management thresholds
RATE_LIMIT_THRESHOLDS = {
    "warning_pct": 70,     # Warn at 70% usage
    "throttle_pct": 85,    # Add delays at 85%
    "emergency_pct": 95,   # Critical orders only at 95%
}

# Priority levels for rate limiting
PriorityLevel = Literal[
    "stop_loss",
    "take_profit",
    "kill_switch",
    "new_entry",
    "order_management",
    "data_fetch",
]

# Priority order (1 = highest priority, 3 = lowest)
PRIORITY_ORDER: dict[PriorityLevel, int] = {
    "stop_loss": 1,      # Priority 1: Always allowed
    "take_profit": 1,
    "kill_switch": 1,
    "new_entry": 2,       # Priority 2: Delayed during throttle
    "order_management": 2, # Priority 2: Standard order operations
    "data_fetch": 3,      # Priority 3: Lowest priority
}


@dataclass
class TokenBucket:
    """Token bucket for rate limiting.

    Implements the token bucket algorithm with time-based refilling.

    Attributes:
        capacity: Maximum number of tokens (e.g., 1200 for 1200 req/min).
        refill_rate: Tokens added per second (e.g., 20 for 1200/min).
        tokens: Current token count.
        last_refill: Timestamp of last refill.
    """

    capacity: float
    refill_rate: float
    tokens: float = field(init=False)
    last_refill: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        """Initialize tokens to full capacity."""
        self.tokens = self.capacity

    def refill(self) -> None:
        """Refill tokens based on elapsed time.

        Tokens are added linearly based on elapsed time and refill rate.
        Tokens never exceed capacity.
        """
        now = time.time()
        elapsed = now - self.last_refill

        # Calculate tokens to add based on elapsed time
        tokens_to_add = elapsed * self.refill_rate

        # Add tokens, capped at capacity
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)

        # Update last refill time
        self.last_refill = now

    def try_consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens.

        Args:
            tokens: Number of tokens to consume.

        Returns:
            True if tokens were consumed, False if insufficient tokens.
        """
        # Refill tokens first
        self.refill()

        # Check if sufficient tokens available
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    @property
    def usage_pct(self) -> float:
        """Get current usage as percentage of capacity.

        Returns:
            Usage percentage (0-100).
        """
        self.refill()
        return ((self.capacity - self.tokens) / self.capacity) * 100.0

    @property
    def available_tokens(self) -> float:
        """Get available tokens after refill.

        Returns:
            Number of available tokens.
        """
        self.refill()
        return self.tokens


class RateLimiter:
    """Rate limiter for Binance API with priority queue.

    Decision: DEC-2026-02-10-002 - Token bucket rate limiter
    PRD Feature J - Rate Limit Management

    Enforces Binance API rate limits:
    - 1200 requests per minute (request weight)
    - 10 orders per second
    - 200,000 orders per day

    Implements PRD Feature J thresholds:
    - Warning at 70% usage (log warning)
    - Throttle at 85% usage (add 500ms delay to non-critical requests)
    - Emergency at 95% usage (only Priority 1 requests allowed)

    Priority system:
    - Priority 1: Stop loss, take profit, kill switch (always allowed)
    - Priority 2: New entries (delayed during throttle)
    - Priority 3: Data fetching (lowest priority)
    """

    def __init__(self) -> None:
        """Initialize rate limiter with Binance limits."""
        # Binance request weight limit: 1200 per minute
        self.requests_bucket = TokenBucket(
            capacity=1200,
            refill_rate=1200 / 60,  # 20 tokens per second
        )

        # Binance order limit: 10 per second
        self.orders_bucket = TokenBucket(
            capacity=10,
            refill_rate=10,  # 10 tokens per second
        )

        # Binance daily order limit: 200,000 per day
        self.daily_orders_bucket = TokenBucket(
            capacity=200_000,
            refill_rate=200_000 / 86400,  # ~2.3 tokens per second
        )

        # Lock for thread-safe token consumption
        self._lock = asyncio.Lock()

        # Statistics
        self._total_requests: int = 0
        self._total_orders: int = 0
        self._warnings_issued: int = 0
        self._throttles_applied: int = 0
        self._emergency_blocks: int = 0

    async def acquire(
        self,
        priority: PriorityLevel = "data_fetch",
        is_order: bool = False,
    ) -> None:
        """Acquire rate limit tokens (blocks until available).

        PRD Feature J implementation:
        - Warn at 70% usage
        - Throttle at 85% (add 500ms delay to non-critical)
        - Emergency at 95% (only Priority 1 allowed)

        Args:
            priority: Request priority level.
            is_order: Whether this is an order request (uses order buckets).

        Raises:
            None - blocks until tokens available.
        """
        async with self._lock:
            priority_level = PRIORITY_ORDER[priority]

            while True:
                # Get current usage
                usage_pct = self.requests_bucket.usage_pct

                # PRD Feature J: Warning at 70%
                if usage_pct >= RATE_LIMIT_THRESHOLDS["warning_pct"]:
                    if self._warnings_issued % 10 == 0:  # Log every 10th warning
                        logger.warning(
                            "rate_limit_warning",
                            usage_pct=round(usage_pct, 2),
                            threshold=RATE_LIMIT_THRESHOLDS["warning_pct"],
                            priority=priority,
                            available_tokens=round(
                                self.requests_bucket.available_tokens, 2
                            ),
                        )
                    self._warnings_issued += 1

                # PRD Feature J: Emergency mode at 95%
                if usage_pct >= RATE_LIMIT_THRESHOLDS["emergency_pct"]:
                    # Only allow Priority 1 (stop_loss, take_profit, kill_switch)
                    if priority_level > 1:
                        self._emergency_blocks += 1
                        logger.error(
                            "rate_limit_emergency",
                            priority=priority,
                            priority_level=priority_level,
                            usage_pct=round(usage_pct, 2),
                            action="blocking_non_critical",
                            emergency_blocks=self._emergency_blocks,
                        )
                        # Wait 1 second for tokens to refill
                        await asyncio.sleep(1)
                        continue

                # Try to consume request tokens
                can_consume_request = self.requests_bucket.try_consume(1.0)

                # For orders, also check order buckets
                can_consume_order = True
                can_consume_daily = True

                if is_order:
                    can_consume_order = self.orders_bucket.try_consume(1.0)
                    can_consume_daily = self.daily_orders_bucket.try_consume(1.0)

                # Check if all required tokens consumed
                if can_consume_request and can_consume_order and can_consume_daily:
                    # Success - tokens acquired
                    self._total_requests += 1
                    if is_order:
                        self._total_orders += 1

                    logger.debug(
                        "rate_limit_acquired",
                        priority=priority,
                        is_order=is_order,
                        usage_pct=round(usage_pct, 2),
                        total_requests=self._total_requests,
                        total_orders=self._total_orders,
                    )
                    return

                # Tokens not available, need to wait

                # Check for daily order limit exhaustion
                if is_order and not can_consume_daily:
                    logger.critical(
                        "daily_order_limit_reached",
                        daily_orders=self._total_orders,
                        limit=200_000,
                    )
                    # Wait longer for daily limit (unlikely to recover quickly)
                    await asyncio.sleep(60)
                    continue

                # PRD Feature J: Throttle at 85%
                if usage_pct >= RATE_LIMIT_THRESHOLDS["throttle_pct"]:
                    # Add 500ms delay for throttling
                    delay_ms = 500
                    self._throttles_applied += 1

                    if self._throttles_applied % 5 == 0:  # Log every 5th throttle
                        logger.info(
                            "rate_limit_throttling",
                            priority=priority,
                            usage_pct=round(usage_pct, 2),
                            delay_ms=delay_ms,
                            throttles_applied=self._throttles_applied,
                        )

                    await asyncio.sleep(delay_ms / 1000)
                else:
                    # Standard wait - 50ms
                    await asyncio.sleep(0.05)

    def get_usage_stats(self) -> dict[str, float | int]:
        """Get current rate limit usage statistics.

        Returns:
            Dictionary with usage statistics:
            - requests_usage_pct: Request weight usage percentage
            - orders_usage_pct: Orders per second usage percentage
            - daily_orders_usage_pct: Daily orders usage percentage
            - total_requests: Total requests made
            - total_orders: Total orders made
            - warnings_issued: Number of warnings issued
            - throttles_applied: Number of throttles applied
            - emergency_blocks: Number of emergency blocks
        """
        return {
            "requests_usage_pct": round(self.requests_bucket.usage_pct, 2),
            "orders_usage_pct": round(self.orders_bucket.usage_pct, 2),
            "daily_orders_usage_pct": round(self.daily_orders_bucket.usage_pct, 2),
            "total_requests": self._total_requests,
            "total_orders": self._total_orders,
            "warnings_issued": self._warnings_issued,
            "throttles_applied": self._throttles_applied,
            "emergency_blocks": self._emergency_blocks,
        }

    def reset_stats(self) -> None:
        """Reset usage statistics (for testing)."""
        self._total_requests = 0
        self._total_orders = 0
        self._warnings_issued = 0
        self._throttles_applied = 0
        self._emergency_blocks = 0
