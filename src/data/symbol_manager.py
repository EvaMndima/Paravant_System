"""Symbol manager for fetching and caching symbol metadata.

Decision: DEC-2026-02-10-001 - Use python-binance SDK wrapper
Decision: DEC-2026-02-08-003 - Timezone-aware timestamps

This module provides the SymbolManager class for fetching trading pair
metadata from Binance and caching it in the database.

Features:
- Fetch exchange info from Binance
- Parse lot size, price, and notional filters
- 24-hour cache refresh
- Order validation
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.brokers.binance.client import BinanceClient
from src.core.exceptions import SymbolNotFoundError
from src.data.models.symbol import SymbolInfo
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Cache duration (24 hours)
CACHE_DURATION_HOURS = 24


class SymbolManager:
    """Manage trading pair metadata from exchange.

    Decision: DEC-2026-02-10-001 - Use python-binance SDK wrapper

    This class fetches symbol information from Binance and caches it
    for efficient order validation.

    Features:
    - Fetch all USDT pairs from Binance
    - Parse exchange filters (LOT_SIZE, PRICE_FILTER, MIN_NOTIONAL)
    - 24-hour cache refresh
    - Order validation against exchange rules

    Attributes:
        client: BinanceClient instance.
        symbols_cache: In-memory cache of symbol info.
        last_refresh: Timestamp of last cache refresh.
    """

    def __init__(self, client: BinanceClient | None = None) -> None:
        """Initialize symbol manager.

        Args:
            client: BinanceClient instance (creates new if None).
        """
        self.client = client or BinanceClient(testnet=True)
        self.symbols_cache: dict[str, SymbolInfo] = {}
        self.last_refresh: datetime | None = None

        logger.info("symbol_manager_initialized")

    async def refresh_symbols(self, force: bool = False) -> int:
        """Refresh symbol metadata from exchange.

        Decision: DEC-2026-02-08-003 - Timezone-aware timestamps

        Fetches exchange info from Binance and updates cache.
        By default, only refreshes if cache is older than 24 hours.

        Args:
            force: Force refresh even if cache is fresh (default False).

        Returns:
            Number of symbols refreshed.

        Raises:
            BinanceConnectionError: If fetch fails.
        """
        # Check if refresh needed
        if not force and self.last_refresh is not None:
            age = datetime.now(timezone.utc) - self.last_refresh
            if age < timedelta(hours=CACHE_DURATION_HOURS):
                logger.debug(
                    "symbol_cache_fresh",
                    age_hours=age.total_seconds() / 3600,
                    cache_duration_hours=CACHE_DURATION_HOURS,
                )
                return len(self.symbols_cache)

        logger.info(
            "refreshing_symbols",
            force=force,
            cached_count=len(self.symbols_cache),
        )

        try:
            # Fetch exchange info
            exchange_info = await self.client.get_exchange_info()

            # Parse symbols
            symbols_data = exchange_info.get("symbols", [])
            refreshed_count = 0

            for symbol_data in symbols_data:
                try:
                    # Parse symbol info
                    symbol_info = self._parse_symbol_data(symbol_data)

                    # Add to cache
                    self.symbols_cache[symbol_info.symbol] = symbol_info
                    refreshed_count += 1

                except Exception as e:
                    logger.warning(
                        "symbol_parse_failed",
                        symbol=symbol_data.get("symbol", "unknown"),
                        error=str(e),
                        exc_info=True,
                    )
                    continue

            # Update refresh timestamp
            self.last_refresh = datetime.now(timezone.utc)

            logger.info(
                "symbols_refreshed",
                count=refreshed_count,
                cache_size=len(self.symbols_cache),
                timestamp=self.last_refresh.isoformat(),
            )

            return refreshed_count

        except Exception as e:
            logger.error(
                "symbol_refresh_failed",
                error=str(e),
                exc_info=True,
            )
            raise

    def _parse_symbol_data(self, symbol_data: dict[str, Any]) -> SymbolInfo:
        """Parse Binance symbol data to SymbolInfo.

        Args:
            symbol_data: Symbol dictionary from Binance exchange_info.

        Returns:
            SymbolInfo object.

        Raises:
            ValueError: If required fields missing or invalid.
        """
        symbol = symbol_data["symbol"]
        base_asset = symbol_data["baseAsset"]
        quote_asset = symbol_data["quoteAsset"]

        # Parse filters
        filters = {f["filterType"]: f for f in symbol_data.get("filters", [])}

        # Lot size filter (quantity constraints)
        lot_size = filters.get("LOT_SIZE", {})
        min_quantity = float(lot_size.get("minQty", 0))
        max_quantity = float(lot_size.get("maxQty", 0))
        step_size = float(lot_size.get("stepSize", 0))

        # Price filter (price constraints)
        price_filter = filters.get("PRICE_FILTER", {})
        tick_size = float(price_filter.get("tickSize", 0))
        min_price = price_filter.get("minPrice")
        max_price = price_filter.get("maxPrice")

        # Convert to float if present, else None
        min_price = float(min_price) if min_price and float(min_price) > 0 else None
        max_price = float(max_price) if max_price and float(max_price) > 0 else None

        # Min notional filter (minimum order value)
        # Try both NOTIONAL and MIN_NOTIONAL (Binance uses different names)
        notional_filter = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL", {})
        min_notional = float(notional_filter.get("minNotional", 0))

        # Trading status
        is_trading = symbol_data.get("status") == "TRADING"
        is_spot_trading_allowed = symbol_data.get("isSpotTradingAllowed", False)
        is_margin_trading_allowed = symbol_data.get("isMarginTradingAllowed", False)
        # Create SymbolInfo
        symbol_info = SymbolInfo(
            symbol=symbol,
            base_asset=base_asset,
            quote_asset=quote_asset,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            step_size=step_size,
            tick_size=tick_size,
            min_price=min_price,
            max_price=max_price,
            min_notional=min_notional,
            is_trading=is_trading,
            is_spot_trading_allowed=is_spot_trading_allowed,
            is_margin_trading_allowed=is_margin_trading_allowed,
            filters=filters,  # Store all filters for reference
        )

        return symbol_info

    async def get_symbol(self, symbol: str) -> SymbolInfo:
        """Get symbol info with auto-refresh if needed.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT").

        Returns:
            SymbolInfo object.

        Raises:
            SymbolNotFoundError: If symbol not found after refresh.
        """
        # Check cache first
        if symbol in self.symbols_cache:
            return self.symbols_cache[symbol]

        # Not in cache, refresh
        logger.info(
            "symbol_not_in_cache",
            symbol=symbol,
            action="refreshing",
        )

        await self.refresh_symbols()

        # Check again after refresh
        if symbol in self.symbols_cache:
            return self.symbols_cache[symbol]

        # Still not found
        logger.error(
            "symbol_not_found",
            symbol=symbol,
        )
        raise SymbolNotFoundError(symbol=symbol)

    def list_symbols(
        self,
        enabled_only: bool = True,
        quote_asset: str | None = None,
    ) -> list[SymbolInfo]:
        """List all cached symbols.

        Args:
            enabled_only: Only return symbols where is_trading=True (default True).
            quote_asset: Filter by quote asset (e.g., "USDT", default None).

        Returns:
            List of SymbolInfo objects matching filters.
        """
        symbols = list(self.symbols_cache.values())

        # Filter by trading status
        if enabled_only:
            symbols = [s for s in symbols if s.is_trading]

        # Filter by quote asset
        if quote_asset:
            symbols = [s for s in symbols if s.quote_asset == quote_asset]

        return symbols

    async def validate_order(
        self,
        symbol: str,
        quantity: float,
        price: float,
    ) -> tuple[bool, list[str]]:
        """Validate order against exchange rules.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT").
            quantity: Order quantity.
            price: Order price.

        Returns:
            Tuple of (is_valid, error_messages).
            error_messages list is empty if valid.

        Raises:
            SymbolNotFoundError: If symbol not found.
        """
        # Get symbol info (auto-refreshes if needed)
        symbol_info = await self.get_symbol(symbol)

        # Validate order
        is_valid, errors = symbol_info.validate_order(quantity, price)

        if not is_valid:
            logger.warning(
                "order_validation_failed",
                symbol=symbol,
                quantity=quantity,
                price=price,
                errors=errors,
            )
        else:
            logger.debug(
                "order_validated",
                symbol=symbol,
                quantity=quantity,
                price=price,
            )

        return is_valid, errors

    def get_cache_info(self) -> dict[str, Any]:
        """Get cache information.

        Returns:
            Dictionary with cache statistics.
        """
        return {
            "symbols_count": len(self.symbols_cache),
            "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None,
            "cache_age_hours": (datetime.now(timezone.utc) - self.last_refresh).total_seconds() / 3600
            if self.last_refresh
            else None,
            "cache_duration_hours": CACHE_DURATION_HOURS,
        }
