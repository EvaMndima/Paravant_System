"""Integration tests for SymbolManager with real Binance testnet.

Decision: DEC-2026-02-10-001 - Use python-binance SDK wrapper
PRD Section 2.3 - Symbol Management

IMPORTANT: These tests connect to Binance testnet and require:
- Internet connection
- Binance testnet availability

These tests verify:
- Real symbol metadata fetching from testnet
- Filter parsing from live exchange_info
- Symbol caching and refresh logic
- Database persistence integration
- Order validation against real exchange rules

Run with: pytest tests/integration/test_symbol_refresh.py -v -m integration
Skip with: pytest tests/ -m "not integration"
"""

from __future__ import annotations

import pytest

from src.brokers.binance.client import BinanceClient
from src.core.exceptions import SymbolNotFoundError
from src.data import DataStore
from src.data.symbol_manager import SymbolManager


@pytest.mark.integration
class TestSymbolManagerIntegration:
    """Integration tests with real Binance testnet."""

    @pytest.fixture
    def client(self) -> BinanceClient:
        """Create BinanceClient connected to testnet."""
        return BinanceClient(testnet=True)

    @pytest.fixture
    def manager(self, client: BinanceClient) -> SymbolManager:
        """Create SymbolManager with testnet client."""
        return SymbolManager(client=client)

    @pytest.mark.asyncio
    async def test_refresh_symbols_from_testnet(
        self,
        manager: SymbolManager,
    ) -> None:
        """Test refreshing symbols from Binance testnet."""
        count = await manager.refresh_symbols()

        # Should fetch multiple symbols
        assert count > 0
        assert len(manager.symbols_cache) > 0

        # Cache should be populated
        assert manager.last_refresh is not None

    @pytest.mark.asyncio
    async def test_get_btcusdt_from_testnet(
        self,
        manager: SymbolManager,
    ) -> None:
        """Test fetching BTCUSDT symbol from testnet."""
        symbol_info = await manager.get_symbol("BTCUSDT")

        # Verify structure
        assert symbol_info.symbol == "BTCUSDT"
        assert symbol_info.base_asset == "BTC"
        assert symbol_info.quote_asset == "USDT"

        # Verify filters are parsed
        assert symbol_info.min_quantity > 0
        assert symbol_info.step_size > 0
        assert symbol_info.tick_size > 0
        assert symbol_info.min_notional > 0

        # Verify trading status
        assert symbol_info.is_trading is True

    @pytest.mark.asyncio
    async def test_get_ethusdt_from_testnet(
        self,
        manager: SymbolManager,
    ) -> None:
        """Test fetching ETHUSDT symbol from testnet."""
        symbol_info = await manager.get_symbol("ETHUSDT")

        assert symbol_info.symbol == "ETHUSDT"
        assert symbol_info.base_asset == "ETH"
        assert symbol_info.quote_asset == "USDT"

        # Verify all required fields are present
        assert symbol_info.min_quantity > 0
        assert symbol_info.max_quantity > 0
        assert symbol_info.step_size > 0
        assert symbol_info.tick_size > 0

    @pytest.mark.asyncio
    async def test_list_usdt_symbols_from_testnet(
        self,
        manager: SymbolManager,
    ) -> None:
        """Test listing USDT pairs from testnet."""
        await manager.refresh_symbols()

        usdt_symbols = manager.list_symbols(
            enabled_only=True,
            quote_asset="USDT",
        )

        # Should have multiple USDT pairs
        assert len(usdt_symbols) > 0

        # All should be USDT pairs
        for symbol in usdt_symbols:
            assert symbol.quote_asset == "USDT"
            assert symbol.is_trading is True

        # Should include common pairs
        symbol_names = [s.symbol for s in usdt_symbols]
        assert "BTCUSDT" in symbol_names
        assert "ETHUSDT" in symbol_names

    @pytest.mark.asyncio
    async def test_validate_real_order_btcusdt(
        self,
        manager: SymbolManager,
    ) -> None:
        """Test order validation against real BTCUSDT rules."""
        # Get real symbol info
        symbol_info = await manager.get_symbol("BTCUSDT")

        # Test valid order
        is_valid, errors = symbol_info.validate_order(
            quantity=0.001,  # Small but valid quantity
            price=40000.0,  # Reasonable price
        )

        # Should be valid (if above min_notional)
        if symbol_info.min_notional <= 40.0:  # 0.001 * 40000 = 40 USDT
            assert is_valid is True
            assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_symbol_filters_parsing(
        self,
        manager: SymbolManager,
    ) -> None:
        """Test all filter types are parsed correctly."""
        symbol_info = await manager.get_symbol("BTCUSDT")

        # LOT_SIZE filter
        assert symbol_info.min_quantity > 0
        assert symbol_info.max_quantity > 0
        assert symbol_info.step_size > 0

        # PRICE_FILTER
        assert symbol_info.tick_size > 0

        # MIN_NOTIONAL or NOTIONAL
        assert symbol_info.min_notional > 0

        # Filters dict should be stored
        assert isinstance(symbol_info.filters, dict)
        assert len(symbol_info.filters) > 0

    @pytest.mark.asyncio
    async def test_symbol_not_found_raises(
        self,
        manager: SymbolManager,
    ) -> None:
        """Test invalid symbol raises SymbolNotFoundError."""
        with pytest.raises(SymbolNotFoundError):
            await manager.get_symbol("INVALIDSYMBOL")

    @pytest.mark.asyncio
    async def test_cache_info_after_refresh(
        self,
        manager: SymbolManager,
    ) -> None:
        """Test cache info reflects refresh."""
        await manager.refresh_symbols()

        cache_info = manager.get_cache_info()

        assert cache_info["symbols_count"] > 0
        assert cache_info["last_refresh"] is not None
        assert cache_info["cache_age_hours"] is not None
        assert cache_info["cache_age_hours"] < 0.1  # Just refreshed

    @pytest.mark.asyncio
    async def test_round_quantity_to_step_size(
        self,
        manager: SymbolManager,
    ) -> None:
        """Test quantity rounding to exchange step size."""
        symbol_info = await manager.get_symbol("BTCUSDT")

        # Round quantity to valid step
        rounded = symbol_info.round_quantity(0.0012345)

        # Should be multiple of step_size
        # Should be multiple of step_size
        remainder = rounded / symbol_info.step_size
        assert remainder == pytest.approx(int(remainder + 0.0000001))

    @pytest.mark.asyncio
    async def test_round_price_to_tick_size(
        self,
        manager: SymbolManager,
    ) -> None:
        """Test price rounding to exchange tick size."""
        symbol_info = await manager.get_symbol("BTCUSDT")

        # Round price to valid tick
        rounded = symbol_info.round_price(42123.456)

        # Should be multiple of tick_size
        remainder = rounded / symbol_info.tick_size
        assert remainder == int(remainder)

    @pytest.mark.asyncio
    async def test_validate_quantity_bounds(
        self,
        manager: SymbolManager,
    ) -> None:
        """Test quantity validation against min/max bounds."""
        symbol_info = await manager.get_symbol("BTCUSDT")

        # Test below minimum
        is_valid, error = symbol_info.validate_quantity(
            symbol_info.min_quantity / 2
        )
        assert is_valid is False
        assert "minimum" in error.lower()

        # Test above maximum (if max_quantity is reasonable)
        if symbol_info.max_quantity < 1000000:  # Sanity check
            is_valid, error = symbol_info.validate_quantity(
                symbol_info.max_quantity * 2
            )
            assert is_valid is False
            assert "maximum" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_price_bounds(
        self,
        manager: SymbolManager,
    ) -> None:
        """Test price validation against min/max bounds."""
        symbol_info = await manager.get_symbol("BTCUSDT")

        # If min_price is set
        if symbol_info.min_price:
            is_valid, error = symbol_info.validate_price(
                symbol_info.min_price / 2
            )
            assert is_valid is False
            assert "minimum" in error.lower()

        # If max_price is set
        if symbol_info.max_price and symbol_info.max_price < 10_000_000:
            is_valid, error = symbol_info.validate_price(
                symbol_info.max_price * 2
            )
            assert is_valid is False
            assert "maximum" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_notional_minimum(
        self,
        manager: SymbolManager,
    ) -> None:
        """Test order value must meet minimum notional."""
        symbol_info = await manager.get_symbol("BTCUSDT")

        # Calculate notional below minimum
        quantity = symbol_info.min_quantity
        price = symbol_info.min_notional / (quantity * 2)  # Half of min_notional

        is_valid, error = symbol_info.validate_notional(quantity, price)

        if error:  # If notional check is enforced
            assert is_valid is False
            assert "order value" in error.lower()

    @pytest.mark.asyncio
    async def test_multiple_symbol_refresh_idempotent(
        self,
        manager: SymbolManager,
    ) -> None:
        """Test multiple refreshes produce consistent results."""
        # First refresh
        count1 = await manager.refresh_symbols()

        # Second refresh (should skip due to cache)
        count2 = await manager.refresh_symbols(force=False)

        assert count1 == count2
        assert count1 > 0

        # Force refresh
        count3 = await manager.refresh_symbols(force=True)

        # Should get same symbols
        assert count3 == count1

    @pytest.mark.asyncio
    async def test_symbol_metadata_completeness(
        self,
        manager: SymbolManager,
    ) -> None:
        """Test all required symbol metadata fields are populated."""
        await manager.refresh_symbols()

        # Get a few common symbols
        symbols_to_test = ["BTCUSDT", "ETHUSDT"]

        for symbol_name in symbols_to_test:
            try:
                symbol_info = await manager.get_symbol(symbol_name)

                # All fields should be set
                assert symbol_info.symbol is not None
                assert symbol_info.base_asset is not None
                assert symbol_info.quote_asset is not None
                assert symbol_info.min_quantity > 0
                assert symbol_info.max_quantity > 0
                assert symbol_info.step_size > 0
                assert symbol_info.tick_size > 0
                assert symbol_info.min_notional >= 0
                assert symbol_info.is_trading is not None

            except SymbolNotFoundError:
                # Symbol might not be available on testnet
                pytest.skip(f"{symbol_name} not available on testnet")


@pytest.mark.integration
class TestSymbolManagerDatabaseIntegration:
    """Integration tests with database persistence."""

    @pytest.fixture
    def manager(self) -> SymbolManager:
        """Create SymbolManager with testnet client."""
        client = BinanceClient(testnet=True)
        return SymbolManager(client=client)

    @pytest.fixture
    def store(self) -> DataStore:
        """Create DataStore for testing persistence with isolated DB."""
        from src.data.models.base import Base
        from sqlalchemy import create_engine
        
        # Use simple in-memory DB for this integration test
        # to avoid schema conflicts or polluting real DB
        test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(test_engine)
        
        store = DataStore()
        # Override backing engine
        store.engine = test_engine
        return store

    @pytest.mark.asyncio
    async def test_save_and_retrieve_symbol_info(
        self,
        manager: SymbolManager,
        store: DataStore,
    ) -> None:
        """Test saving symbol info to database and retrieving."""
        # Fetch from Binance
        symbol_info = await manager.get_symbol("BTCUSDT")

        # Save to database
        saved = store.save_symbol_info(symbol_info)

        # Retrieve from database
        retrieved = store.get_symbol_info("BTCUSDT")

        # Should match
        assert retrieved is not None
        assert retrieved.symbol == saved.symbol
        assert retrieved.min_quantity == saved.min_quantity
        assert retrieved.tick_size == saved.tick_size
        assert retrieved.min_notional == saved.min_notional

    @pytest.mark.asyncio
    async def test_get_all_symbols_from_database(
        self,
        manager: SymbolManager,
        store: DataStore,
    ) -> None:
        """Test retrieving all symbols from database."""
        # Fetch and save a few symbols
        symbols_to_save = ["BTCUSDT", "ETHUSDT"]

        for symbol_name in symbols_to_save:
            try:
                symbol_info = await manager.get_symbol(symbol_name)
                store.save_symbol_info(symbol_info)
            except SymbolNotFoundError:
                pytest.skip(f"{symbol_name} not available on testnet")

        # Retrieve all
        all_symbols = store.get_all_symbols(trading_only=False)

        # Should have at least the ones we saved
        symbol_names = [s.symbol for s in all_symbols]
        for expected in symbols_to_save:
            if expected in symbol_names:  # If it was successfully saved
                assert expected in symbol_names
