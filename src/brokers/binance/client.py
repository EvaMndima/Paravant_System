"""Binance REST API client with rate limiting and error handling.

Decision: DEC-2026-02-10-001 - Use python-binance SDK wrapper
Decision: DEC-2026-02-08-008 - Structured logging

This module provides an async wrapper around the python-binance Client
with integrated rate limiting, error handling, and structured logging.

Features:
- Automatic testnet/mainnet switching
- Rate limit enforcement with priority queuing (PRD Feature J)
- Comprehensive error handling and retry logic
- Structured logging with sensitive data masking
- Async I/O with asyncio.to_thread() for blocking calls
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from binance.client import Client
from binance.exceptions import (
    BinanceAPIException,
    BinanceOrderException,
    BinanceRequestException,
)

from src.brokers.binance.exceptions import (
    BinanceAPIError,
    BinanceAuthenticationError,
    BinanceConnectionError,
    BinanceRateLimitError,
)
from src.brokers.binance.rate_limiter import RateLimiter
from src.core.config.settings import get_settings
from src.core.exceptions import SymbolNotFoundError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BinanceClient:
    """Async wrapper around python-binance Client.

    Decision: DEC-2026-02-10-001 - Use python-binance SDK wrapper

    This class wraps the python-binance Client to provide:
    - Async I/O operations (using asyncio.to_thread)
    - Automatic rate limiting (PRD Feature J)
    - Structured error handling and logging
    - Testnet/mainnet switching
    - Security best practices (API key masking)

    Attributes:
        client: Underlying python-binance Client instance.
        rate_limiter: Rate limiter for API calls.
        testnet: Whether using testnet (True) or mainnet (False).
        api_key: Binance API key (masked in logs).
        secret_key: Binance secret key (never logged).
    """

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        testnet: bool = True,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        """Initialize Binance client.

        Decision: DEC-2026-02-08-003 - Timezone-aware timestamps

        Args:
            api_key: Binance API key (uses settings if None).
            secret_key: Binance secret key (uses settings if None).
            testnet: Use testnet (True) or mainnet (False). Default True for safety.
            rate_limiter: Rate limiter instance (creates default if None).

        Raises:
            BinanceAuthenticationError: If API keys missing when required.
        """
        settings = get_settings()

        # Get API keys from settings if not provided
        self.api_key = api_key or settings.binance_api_key
        self.secret_key = secret_key or settings.binance_secret_key
        self.testnet = testnet

        # CRITICAL SECURITY: Never log full API keys
        # Decision: DEC-2026-02-09-006 - Sensitive data masking
        logger.info(
            "binance_client_initialized",
            testnet=testnet,
            environment="TESTNET" if testnet else "PRODUCTION",
            api_key_present=bool(self.api_key),
            api_key_suffix=self.api_key[-4:] if self.api_key else None,
        )

        # CRITICAL: Warn if production mode
        if not testnet:
            logger.critical(
                "production_mode_active",
                warning="REAL MONEY AT RISK",
                message="Production trading mode is active",
            )

        # Initialize python-binance client
        self.client = Client(
            api_key=self.api_key,
            api_secret=self.secret_key,
            testnet=testnet,
        )

        # Initialize rate limiter
        # Decision: DEC-2026-02-10-002 - Token bucket rate limiter
        self.rate_limiter = rate_limiter or RateLimiter()

    async def ping(self) -> dict[str, Any]:
        """Test connectivity to Binance API.

        Returns:
            Empty dict if successful.

        Raises:
            BinanceConnectionError: If ping fails.
        """
        await self.rate_limiter.acquire(priority="data_fetch")

        try:
            logger.debug("binance_ping")

            # Wrap blocking call in thread
            result = await asyncio.to_thread(self.client.ping)

            logger.debug("binance_ping_success")
            return result

        except BinanceRequestException as e:
            logger.error(
                "binance_ping_failed",
                error=str(e),
                exc_info=True,
            )
            raise BinanceConnectionError(
                reason="Ping failed",
                details={"error": str(e)},
            ) from e

    async def get_server_time(self) -> datetime:
        """Get Binance server time.

        Decision: DEC-2026-02-08-003 - Timezone-aware timestamps

        Returns:
            Timezone-aware datetime of server time.

        Raises:
            BinanceConnectionError: If request fails.
        """
        await self.rate_limiter.acquire(priority="data_fetch")

        try:
            logger.debug("fetching_server_time")

            # Wrap blocking call in thread
            result = await asyncio.to_thread(self.client.get_server_time)

            # Convert milliseconds to datetime (timezone-aware)
            server_time = datetime.fromtimestamp(
                result["serverTime"] / 1000, tz=timezone.utc
            )

            logger.debug("server_time_fetched", server_time=server_time.isoformat())
            return server_time

        except BinanceRequestException as e:
            logger.error(
                "server_time_fetch_failed",
                error=str(e),
                exc_info=True,
            )
            raise BinanceConnectionError(
                reason="Failed to fetch server time",
                details={"error": str(e)},
            ) from e

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch OHLCV candlestick data.

        Decision: DEC-2026-02-10-002 - Token bucket rate limiter
        PRD Feature J - Rate limiting with priority queue

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT").
            interval: Timeframe (e.g., "1m", "5m", "1h", "4h", "1d").
            limit: Number of candles to fetch (max 1000, default 500).
            start_time: Start timestamp in milliseconds (optional).
            end_time: End timestamp in milliseconds (optional).

        Returns:
            List of OHLCV dictionaries with keys:
            - timestamp (int): Open time in milliseconds
            - open (float): Open price
            - high (float): High price
            - low (float): Low price
            - close (float): Close price
            - volume (float): Volume in base asset

        Raises:
            BinanceAPIError: If API returns an error.
            BinanceConnectionError: If request fails.
            SymbolNotFoundError: If symbol not found.
        """
        # Validate limit
        if limit < 1 or limit > 1000:
            raise ValueError(f"Limit must be between 1 and 1000 (got {limit})")

        # Rate limiting (PRD Feature J)
        await self.rate_limiter.acquire(priority="data_fetch")

        try:
            logger.info(
                "fetching_klines",
                symbol=symbol,
                interval=interval,
                limit=limit,
                has_start_time=start_time is not None,
                has_end_time=end_time is not None,
            )

            # Wrap blocking python-binance call in thread
            # Decision: DEC-2026-02-10-004 - Async-first architecture
            klines = await asyncio.to_thread(
                self.client.get_klines,
                symbol=symbol,
                interval=interval,
                limit=limit,
                startTime=start_time,
                endTime=end_time,
            )

            # Parse Binance response format
            # Format: [timestamp, open, high, low, close, volume, ...]
            parsed = [
                {
                    "timestamp": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
                for k in klines
            ]

            logger.info(
                "klines_fetched",
                symbol=symbol,
                interval=interval,
                count=len(parsed),
            )

            return parsed

        except BinanceAPIException as e:
            logger.error(
                "binance_api_error",
                symbol=symbol,
                interval=interval,
                code=e.code,
                message=e.message,
                exc_info=True,
            )

            # Check if symbol not found
            if e.code == -1121:  # Invalid symbol
                raise SymbolNotFoundError(symbol=symbol) from e

            # Check if rate limit exceeded
            if e.code == -1003 or e.code == 429:
                raise BinanceRateLimitError(
                    limit_type="REQUEST_WEIGHT",
                    retry_after=int(e.message.split("Retry-After: ")[1])
                    if "Retry-After" in e.message
                    else None,
                ) from e

            raise BinanceAPIError(
                symbol=symbol,
                api_code=e.code,
                api_message=e.message,
            ) from e

        except BinanceRequestException as e:
            logger.error(
                "binance_request_error",
                symbol=symbol,
                interval=interval,
                error=str(e),
                exc_info=True,
            )
            raise BinanceConnectionError(
                reason="Request failed",
                details={"symbol": symbol, "interval": interval, "error": str(e)},
            ) from e

    async def get_exchange_info(self, symbol: str | None = None) -> dict[str, Any]:
        """Get exchange trading rules and symbol information.

        Args:
            symbol: Specific symbol to get info for (optional).
                   If None, returns info for all symbols.

        Returns:
            Exchange info dictionary with keys:
            - timezone (str): Exchange timezone
            - serverTime (int): Server time in milliseconds
            - symbols (list): List of symbol info dictionaries

        Raises:
            BinanceAPIError: If API returns an error.
            BinanceConnectionError: If request fails.
        """
        await self.rate_limiter.acquire(priority="data_fetch")

        try:
            logger.info(
                "fetching_exchange_info",
                symbol=symbol if symbol else "all",
            )

            # Wrap blocking call in thread
            if symbol:
                result = await asyncio.to_thread(
                    self.client.get_symbol_info, symbol=symbol
                )
                if result is None:
                    raise SymbolNotFoundError(symbol=symbol)
            else:
                result = await asyncio.to_thread(self.client.get_exchange_info)

            logger.info(
                "exchange_info_fetched",
                symbol=symbol if symbol else "all",
                symbols_count=len(result.get("symbols", []))
                if not symbol
                else 1,
            )

            return result

        except BinanceAPIException as e:
            logger.error(
                "exchange_info_fetch_failed",
                symbol=symbol,
                code=e.code,
                message=e.message,
                exc_info=True,
            )

            if e.code == -1121:  # Invalid symbol
                raise SymbolNotFoundError(symbol=symbol or "unknown") from e

            raise BinanceAPIError(
                symbol=symbol or "unknown",
                api_code=e.code,
                api_message=e.message,
            ) from e

        except BinanceRequestException as e:
            logger.error(
                "exchange_info_request_failed",
                symbol=symbol,
                error=str(e),
                exc_info=True,
            )
            raise BinanceConnectionError(
                reason="Failed to fetch exchange info",
                details={"symbol": symbol, "error": str(e)},
            ) from e

    async def get_account(self) -> dict[str, Any]:
        """Get account information including balances.

        Requires authentication (API key + secret).

        Returns:
            Account info dictionary with keys:
            - balances (list): List of asset balances
            - canTrade (bool): Whether account can trade
            - canWithdraw (bool): Whether account can withdraw
            - canDeposit (bool): Whether account can deposit

        Raises:
            BinanceAuthenticationError: If authentication fails.
            BinanceAPIError: If API returns an error.
            BinanceConnectionError: If request fails.
        """
        # Check authentication
        if not self.api_key or not self.secret_key:
            raise BinanceAuthenticationError(
                reason="API key and secret required for authenticated endpoints",
            )

        # Rate limiting for authenticated request
        await self.rate_limiter.acquire(priority="data_fetch")

        try:
            logger.info("fetching_account_info")

            # Wrap blocking call in thread
            result = await asyncio.to_thread(self.client.get_account)

            logger.info(
                "account_info_fetched",
                can_trade=result.get("canTrade", False),
                balances_count=len(result.get("balances", [])),
            )

            return result

        except BinanceAPIException as e:
            logger.error(
                "account_info_fetch_failed",
                code=e.code,
                message=e.message,
                exc_info=True,
            )

            # Check for authentication errors
            if e.code == -2015 or e.code == -2014:
                raise BinanceAuthenticationError(
                    reason=e.message,
                    details={"code": e.code},
                ) from e

            raise BinanceAPIError(
                symbol="N/A",
                api_code=e.code,
                api_message=e.message,
            ) from e

        except BinanceRequestException as e:
            logger.error(
                "account_info_request_failed",
                error=str(e),
                exc_info=True,
            )
            raise BinanceConnectionError(
                reason="Failed to fetch account info",
                details={"error": str(e)},
            ) from e

    def get_rate_limit_stats(self) -> dict[str, float | int]:
        """Get current rate limit usage statistics.

        Returns:
            Dictionary with rate limit statistics from RateLimiter.
        """
        return self.rate_limiter.get_usage_stats()
