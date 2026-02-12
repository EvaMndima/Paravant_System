"""Binance-specific exceptions.

This module defines exceptions specific to Binance broker integration,
extending the base exception hierarchy from src.core.exceptions.

Decision: DEC-2026-02-08-007 (Comprehensive error handling)
"""

from typing import Any

from src.core.exceptions import BrokerConnectionError, MarketDataError


class BinanceConnectionError(BrokerConnectionError):
    """Binance connection error.

    Raised when connection to Binance API fails.
    """

    def __init__(self, reason: str, details: dict[str, Any] | None = None) -> None:
        """Initialize Binance connection error.

        Args:
            reason: Human-readable error reason.
            details: Additional error context.
        """
        super().__init__(
            broker="binance",
            reason=reason,
            details=details or {},
        )


class BinanceAPIError(MarketDataError):
    """Binance API error.

    Raised when Binance API returns an error response.
    """

    def __init__(
        self,
        symbol: str,
        api_code: int,
        api_message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize Binance API error.

        Args:
            symbol: Trading pair symbol.
            api_code: Binance API error code.
            api_message: Binance API error message.
            details: Additional error context.
        """
        error_details = details or {}
        error_details["api_code"] = api_code
        error_details["api_message"] = api_message

        super().__init__(
            symbol=symbol,
            reason=f"Binance API error {api_code}: {api_message}",
            details=error_details,
        )

        self.api_code = api_code
        self.api_message = api_message


class BinanceRateLimitError(BinanceConnectionError):
    """Binance rate limit exceeded.

    Raised when Binance rate limits are exceeded despite rate limiting.
    This indicates a bug in the rate limiter implementation.
    """

    def __init__(
        self,
        limit_type: str,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize Binance rate limit error.

        Args:
            limit_type: Type of limit exceeded (e.g., "REQUEST_WEIGHT", "ORDERS").
            retry_after: Seconds to wait before retrying (if provided by API).
            details: Additional error context.
        """
        error_details = details or {}
        error_details["limit_type"] = limit_type

        if retry_after is not None:
            error_details["retry_after"] = retry_after

        reason = f"Rate limit exceeded: {limit_type}"
        if retry_after:
            reason += f" (retry after {retry_after}s)"

        super().__init__(
            reason=reason,
            details=error_details,
        )

        self.limit_type = limit_type
        self.retry_after = retry_after


class BinanceAuthenticationError(BinanceConnectionError):
    """Binance authentication error.

    Raised when API key or signature is invalid.
    """

    def __init__(self, reason: str, details: dict[str, Any] | None = None) -> None:
        """Initialize Binance authentication error.

        Args:
            reason: Human-readable error reason.
            details: Additional error context.
        """
        super().__init__(
            reason=f"Authentication failed: {reason}",
            details=details or {},
        )
