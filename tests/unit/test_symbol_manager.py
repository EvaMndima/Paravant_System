"""Unit tests for SymbolManager (symbol metadata fetching and caching).

Decision: DEC-2026-02-10-001 - Use python-binance SDK wrapper
Decision: DEC-2026-02-08-003 - Timezone-aware timestamps

This module tests:
- Symbol metadata fetching from Binance
- Exchange filter parsing (LOT_SIZE, PRICE_FILTER, MIN_NOTIONAL)
- 24-hour cache refresh logic
- Symbol validation (quantities, prices, notional)
- Order validation against exchange rules
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.brokers.binance.client import BinanceClient
from src.core.exceptions import SymbolNotFoundError
from src.data.models.symbol import SymbolInfo
from src.data.symbol_manager import SymbolManager


class TestSymbolManager:
    """Test SymbolManager symbol fetching and caching."""

    @pytest.fixture
    def mock_binance_client(self) -> AsyncMock:
        """Create mock Binance client."""
        client = AsyncMock(spec=BinanceClient)
        return client

    @pytest.fixture
    def manager(self, mock_binance_client: AsyncMock) -> SymbolManager:
        """Create SymbolManager with mock client."""
        return SymbolManager(client=mock_binance_client)

    @pytest.fixture
    def sample_exchange_info(self) -> dict[str, list[dict]]:
        """Create sample exchange info response from Binance."""
        return {
            "symbols": [
                {
                    "symbol": "BTCUSDT",
                    "baseAsset": "BTC",
                    "quoteAsset": "USDT",
                    "status": "TRADING",
                    "isSpotTradingAllowed": True,
                    "isMarginTradingAllowed": True,
                    "filters": [
                        {
                            "filterType": "LOT_SIZE",
                            "minQty": "0.00001",
                            "maxQty": "9000.00000",
                            "stepSize": "0.00001",
                        },
                        {
                            "filterType": "PRICE_FILTER",
                            "minPrice": "0.01",
                            "maxPrice": "1000000.00",
                            "tickSize": "0.01",
                        },
                        {
                            "filterType": "MIN_NOTIONAL",
                            "minNotional": "10.00",
                        },
                    ],
                },
                {
                    "symbol": "ETHUSDT",
                    "baseAsset": "ETH",
                    "quoteAsset": "USDT",
                    "status": "TRADING",
                    "isSpotTradingAllowed": True,
                    "isMarginTradingAllowed": False,
                    "filters": [
                        {
                            "filterType": "LOT_SIZE",
                            "minQty": "0.0001",
                            "maxQty": "10000.00",
                            "stepSize": "0.0001",
                        },
                        {
                            "filterType": "PRICE_FILTER",
                            "minPrice": "0.01",
                            "maxPrice": "100000.00",
                            "tickSize": "0.01",
                        },
                        {
                            "filterType": "NOTIONAL",  # Different name
                            "minNotional": "10.00",
                        },
                    ],
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_refresh_symbols_success(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
        sample_exchange_info: dict,
    ) -> None:
        """Test successful symbol refresh from Binance."""
        mock_binance_client.get_exchange_info.return_value = sample_exchange_info

        count = await manager.refresh_symbols()

        assert count == 2  # 2 symbols refreshed
        assert len(manager.symbols_cache) == 2
        assert "BTCUSDT" in manager.symbols_cache
        assert "ETHUSDT" in manager.symbols_cache
        assert manager.last_refresh is not None

    @pytest.mark.asyncio
    async def test_refresh_symbols_parses_lot_size(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
        sample_exchange_info: dict,
    ) -> None:
        """Test LOT_SIZE filter parsing."""
        mock_binance_client.get_exchange_info.return_value = sample_exchange_info

        await manager.refresh_symbols()

        btc = manager.symbols_cache["BTCUSDT"]
        assert btc.min_quantity == 0.00001
        assert btc.max_quantity == 9000.0
        assert btc.step_size == 0.00001

    @pytest.mark.asyncio
    async def test_refresh_symbols_parses_price_filter(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
        sample_exchange_info: dict,
    ) -> None:
        """Test PRICE_FILTER parsing."""
        mock_binance_client.get_exchange_info.return_value = sample_exchange_info

        await manager.refresh_symbols()

        btc = manager.symbols_cache["BTCUSDT"]
        assert btc.tick_size == 0.01
        assert btc.min_price == 0.01
        assert btc.max_price == 1000000.0

    @pytest.mark.asyncio
    async def test_refresh_symbols_parses_min_notional(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
        sample_exchange_info: dict,
    ) -> None:
        """Test MIN_NOTIONAL and NOTIONAL filter parsing."""
        mock_binance_client.get_exchange_info.return_value = sample_exchange_info

        await manager.refresh_symbols()

        btc = manager.symbols_cache["BTCUSDT"]
        assert btc.min_notional == 10.0

        eth = manager.symbols_cache["ETHUSDT"]
        assert eth.min_notional == 10.0  # NOTIONAL variant

    @pytest.mark.asyncio
    async def test_refresh_symbols_parses_trading_status(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
        sample_exchange_info: dict,
    ) -> None:
        """Test trading status parsing."""
        mock_binance_client.get_exchange_info.return_value = sample_exchange_info

        await manager.refresh_symbols()

        btc = manager.symbols_cache["BTCUSDT"]
        assert btc.is_trading is True
        assert btc.is_spot_trading_allowed is True
        assert btc.is_margin_trading_allowed is True

        eth = manager.symbols_cache["ETHUSDT"]
        assert eth.is_trading is True
        assert eth.is_spot_trading_allowed is True
        assert eth.is_margin_trading_allowed is False

    @pytest.mark.asyncio
    async def test_refresh_symbols_skips_invalid(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
    ) -> None:
        """Test refresh skips invalid symbols."""
        # Include one valid and one invalid symbol
        mock_binance_client.get_exchange_info.return_value = {
            "symbols": [
                {
                    "symbol": "BTCUSDT",
                    "baseAsset": "BTC",
                    "quoteAsset": "USDT",
                    "status": "TRADING",
                    "filters": [
                        {
                            "filterType": "LOT_SIZE",
                            "minQty": "0.00001",
                            "maxQty": "9000.00",
                            "stepSize": "0.00001",
                        },
                        {
                            "filterType": "PRICE_FILTER",
                            "minPrice": "0.01",
                            "maxPrice": "1000000.00",
                            "tickSize": "0.01",
                        },
                        {
                            "filterType": "MIN_NOTIONAL",
                            "minNotional": "10.00",
                        },
                    ],
                },
                {
                    "symbol": "INVALID",
                    # Missing required fields (will fail parsing)
                },
            ]
        }

        count = await manager.refresh_symbols()

        # Should only add valid symbol
        assert count == 1
        assert "BTCUSDT" in manager.symbols_cache
        assert "INVALID" not in manager.symbols_cache

    @pytest.mark.asyncio
    async def test_cache_refresh_time_check(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
        sample_exchange_info: dict,
    ) -> None:
        """Test 24-hour cache refresh logic."""
        mock_binance_client.get_exchange_info.return_value = sample_exchange_info

        # First refresh
        await manager.refresh_symbols()
        first_refresh = manager.last_refresh

        # Immediate second refresh (should skip)
        count = await manager.refresh_symbols(force=False)

        assert manager.last_refresh == first_refresh  # Not refreshed
        assert count == 2  # Returns cached count

    @pytest.mark.asyncio
    async def test_force_refresh(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
        sample_exchange_info: dict,
    ) -> None:
        """Test force refresh bypasses cache time check."""
        mock_binance_client.get_exchange_info.return_value = sample_exchange_info

        # First refresh
        await manager.refresh_symbols()
        first_refresh = manager.last_refresh

        # Force refresh (should refresh even if cache fresh)
        await manager.refresh_symbols(force=True)

        assert manager.last_refresh > first_refresh  # Refreshed
        assert mock_binance_client.get_exchange_info.call_count == 2

    @pytest.mark.asyncio
    async def test_get_symbol_from_cache(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
        sample_exchange_info: dict,
    ) -> None:
        """Test get_symbol returns from cache."""
        mock_binance_client.get_exchange_info.return_value = sample_exchange_info

        # Populate cache
        await manager.refresh_symbols()

        # Get symbol from cache
        symbol_info = await manager.get_symbol("BTCUSDT")

        assert symbol_info.symbol == "BTCUSDT"
        assert symbol_info.base_asset == "BTC"
        assert symbol_info.quote_asset == "USDT"

    @pytest.mark.asyncio
    async def test_get_symbol_auto_refresh(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
        sample_exchange_info: dict,
    ) -> None:
        """Test get_symbol auto-refreshes if symbol not in cache."""
        mock_binance_client.get_exchange_info.return_value = sample_exchange_info

        # Get symbol (cache empty, should auto-refresh)
        symbol_info = await manager.get_symbol("BTCUSDT")

        assert symbol_info.symbol == "BTCUSDT"
        assert mock_binance_client.get_exchange_info.call_count == 1

    @pytest.mark.asyncio
    async def test_get_symbol_not_found(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
    ) -> None:
        """Test get_symbol raises SymbolNotFoundError."""
        # Empty exchange info
        mock_binance_client.get_exchange_info.return_value = {"symbols": []}

        with pytest.raises(SymbolNotFoundError):
            await manager.get_symbol("INVALID")

    @pytest.mark.asyncio
    async def test_list_symbols_all(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
        sample_exchange_info: dict,
    ) -> None:
        """Test list_symbols returns all symbols."""
        mock_binance_client.get_exchange_info.return_value = sample_exchange_info

        await manager.refresh_symbols()

        symbols = manager.list_symbols(enabled_only=False)

        assert len(symbols) == 2
        assert any(s.symbol == "BTCUSDT" for s in symbols)
        assert any(s.symbol == "ETHUSDT" for s in symbols)

    @pytest.mark.asyncio
    async def test_list_symbols_enabled_only(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
    ) -> None:
        """Test list_symbols filters by is_trading status."""
        # One trading, one not trading
        mock_binance_client.get_exchange_info.return_value = {
            "symbols": [
                {
                    "symbol": "BTCUSDT",
                    "baseAsset": "BTC",
                    "quoteAsset": "USDT",
                    "status": "TRADING",
                    "filters": [
                        {
                            "filterType": "LOT_SIZE",
                            "minQty": "0.00001",
                            "maxQty": "9000.00",
                            "stepSize": "0.00001",
                        },
                        {
                            "filterType": "PRICE_FILTER",
                            "minPrice": "0.01",
                            "maxPrice": "1000000.00",
                            "tickSize": "0.01",
                        },
                        {
                            "filterType": "MIN_NOTIONAL",
                            "minNotional": "10.00",
                        },
                    ],
                },
                {
                    "symbol": "ETHUSDT",
                    "baseAsset": "ETH",
                    "quoteAsset": "USDT",
                    "status": "HALT",  # Not trading
                    "filters": [
                         {
                            "filterType": "LOT_SIZE",
                            "minQty": "0.00001",
                            "maxQty": "9000.00",
                            "stepSize": "0.00001",
                        },
                        {
                            "filterType": "PRICE_FILTER",
                            "minPrice": "0.01",
                            "maxPrice": "1000000.00",
                            "tickSize": "0.01",
                        },
                        {
                            "filterType": "MIN_NOTIONAL",
                            "minNotional": "10.00",
                        },
                    ],
                },
            ]
        }

        await manager.refresh_symbols()

        symbols = manager.list_symbols(enabled_only=True)

        assert len(symbols) == 1
        assert symbols[0].symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_list_symbols_filter_by_quote(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
    ) -> None:
        """Test list_symbols filters by quote asset."""
        # One USDT, one BTC pair
        mock_binance_client.get_exchange_info.return_value = {
            "symbols": [
                {
                    "symbol": "BTCUSDT",
                    "baseAsset": "BTC",
                    "quoteAsset": "USDT",
                    "status": "TRADING",
                    "filters": [
                         {
                            "filterType": "LOT_SIZE",
                            "minQty": "0.00001",
                            "maxQty": "9000.00",
                            "stepSize": "0.00001",
                        },
                        {
                            "filterType": "PRICE_FILTER",
                            "minPrice": "0.01",
                            "maxPrice": "1000000.00",
                            "tickSize": "0.01",
                        },
                        {
                            "filterType": "MIN_NOTIONAL",
                            "minNotional": "10.00",
                        },
                    ],
                },
                {
                    "symbol": "ETHBTC",
                    "baseAsset": "ETH",
                    "quoteAsset": "BTC",
                    "status": "TRADING",
                    "filters": [
                          {
                            "filterType": "LOT_SIZE",
                            "minQty": "0.00001",
                            "maxQty": "9000.00",
                            "stepSize": "0.00001",
                        },
                        {
                            "filterType": "PRICE_FILTER",
                            "minPrice": "0.01",
                            "maxPrice": "1000000.00",
                            "tickSize": "0.01",
                        },
                        {
                            "filterType": "MIN_NOTIONAL",
                            "minNotional": "10.00",
                        },
                    ],
                },

            ]
        }

        await manager.refresh_symbols()

        usdt_symbols = manager.list_symbols(quote_asset="USDT")

        assert len(usdt_symbols) == 1
        assert usdt_symbols[0].symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_validate_order_success(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
        sample_exchange_info: dict,
    ) -> None:
        """Test order validation passes for valid order."""
        mock_binance_client.get_exchange_info.return_value = sample_exchange_info

        await manager.refresh_symbols()

        # Valid order
        is_valid, errors = await manager.validate_order(
            symbol="BTCUSDT",
            quantity=0.01,  # Valid quantity
            price=42000.0,  # Valid price
        )

        assert is_valid is True
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_validate_order_invalid_quantity(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
        sample_exchange_info: dict,
    ) -> None:
        """Test order validation fails for invalid quantity."""
        mock_binance_client.get_exchange_info.return_value = sample_exchange_info

        await manager.refresh_symbols()

        # Quantity too small
        is_valid, errors = await manager.validate_order(
            symbol="BTCUSDT",
            quantity=0.000001,  # Below min_quantity (0.00001)
            price=42000.0,
        )

        assert is_valid is False
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_validate_order_invalid_price(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
        sample_exchange_info: dict,
    ) -> None:
        """Test order validation fails for invalid price."""
        mock_binance_client.get_exchange_info.return_value = sample_exchange_info

        await manager.refresh_symbols()

        # Price not multiple of tick size
        is_valid, errors = await manager.validate_order(
            symbol="BTCUSDT",
            quantity=0.01,
            price=42000.005,  # Not multiple of tick_size (0.01)
        )

        assert is_valid is False
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_get_cache_info(
        self,
        manager: SymbolManager,
        mock_binance_client: AsyncMock,
        sample_exchange_info: dict,
    ) -> None:
        """Test get_cache_info returns cache statistics."""
        mock_binance_client.get_exchange_info.return_value = sample_exchange_info

        await manager.refresh_symbols()

        cache_info = manager.get_cache_info()

        assert cache_info["symbols_count"] == 2
        assert cache_info["last_refresh"] is not None
        assert cache_info["cache_age_hours"] is not None
        assert cache_info["cache_duration_hours"] == 24
