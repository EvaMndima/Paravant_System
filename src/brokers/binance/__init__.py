"""Binance broker integration.

Decision: DEC-2026-02-10-001 - Use python-binance SDK wrapper
Decision: DEC-2026-02-10-002 - Token bucket rate limiter

This package provides Binance API integration with:
- Async REST client wrapper (BinanceClient)
- Token bucket rate limiter with priority queue (RateLimiter)
- Binance-specific exceptions
- PRD Feature J (Rate Limit Management) implementation
"""

from src.brokers.binance.client import BinanceClient
from src.brokers.binance.exceptions import (BinanceAPIError,
                                            BinanceAuthenticationError,
                                            BinanceConnectionError,
                                            BinanceRateLimitError)
from src.brokers.binance.rate_limiter import (PRIORITY_ORDER,
                                              RATE_LIMIT_THRESHOLDS,
                                              PriorityLevel, RateLimiter,
                                              TokenBucket)

__all__ = [
    # Client
    "BinanceClient",
    # Rate Limiter
    "RateLimiter",
    "TokenBucket",
    "PriorityLevel",
    "PRIORITY_ORDER",
    "RATE_LIMIT_THRESHOLDS",
    # Exceptions
    "BinanceAPIError",
    "BinanceAuthenticationError",
    "BinanceConnectionError",
    "BinanceRateLimitError",
]
