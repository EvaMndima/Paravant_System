"""Integration tests for BinanceClient with real Binance testnet.

Decision: DEC-2026-02-10-001 - Use python-binance SDK wrapper
Decision: DEC-2026-02-08-003 - Timezone-aware timestamps

IMPORTANT: These tests connect to Binance testnet and require:
- Internet connection
- Valid Binance testnet API keys (optional for public endpoints)
- Binance testnet availability

These tests verify:
- Real API connectivity and authentication
- OHLCV data fetching from live testnet
- Exchange info fetching
- Error handling for invalid symbols
- Rate limiting with real requests

Run with: pytest tests/integration/test_binance_client.py -v -m integration
Skip with: pytest tests/ -m "not integration"
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.brokers.binance.client import BinanceClient
from src.core.exceptions import SymbolNotFoundError


@pytest.mark.integration
class TestBinanceClientIntegration:
    """Integration tests with real Binance testnet."""

    @pytest.fixture
    def client(self) -> BinanceClient:
        """Create BinanceClient connected to testnet.

        Note: API keys are optional for public endpoints like ping, get_klines.
        """
        return BinanceClient(testnet=True)

    @pytest.mark.asyncio
    async def test_ping_testnet(self, client: BinanceClient) -> None:
        """Test ping connectivity to Binance testnet."""
        result = await client.ping()

        # Ping returns empty dict on success
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_server_time(self, client: BinanceClient) -> None:
        """Test fetching server time from Binance testnet.

        Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
        """
        server_time = await client.get_server_time()

        # Should be timezone-aware datetime
        assert server_time.tzinfo is not None

        # Should be close to current time (within 1 minute)
        now = datetime.now(timezone.utc)
        time_diff = abs((server_time - now).total_seconds())
        assert time_diff < 60, f"Server time differs by {time_diff}s"

    @pytest.mark.asyncio
    async def test_get_klines_btcusdt(self, client: BinanceClient) -> None:
        """Test fetching OHLCV data for BTCUSDT from testnet."""
        klines = await client.get_klines(
            symbol="BTCUSDT",
            interval="1h",
            limit=10,
        )

        # Should return exactly 10 candles
        assert len(klines) == 10

        # Verify structure of first candle
        first_candle = klines[0]
        assert "timestamp" in first_candle
        assert "open" in first_candle
        assert "high" in first_candle
        assert "low" in first_candle
        assert "close" in first_candle
        assert "volume" in first_candle

        # Verify OHLC relationships
        assert first_candle["high"] >= first_candle["low"]
        assert first_candle["open"] >= first_candle["low"]
        assert first_candle["open"] <= first_candle["high"]
        assert first_candle["close"] >= first_candle["low"]
        assert first_candle["close"] <= first_candle["high"]

    @pytest.mark.asyncio
    async def test_get_klines_ethusdt(self, client: BinanceClient) -> None:
        """Test fetching OHLCV data for ETHUSDT from testnet."""
        klines = await client.get_klines(
            symbol="ETHUSDT",
            interval="1h",
            limit=5,
        )

        # Should return exactly 5 candles
        assert len(klines) == 5

        # All candles should have valid data
        for candle in klines:
            assert candle["open"] > 0
            assert candle["high"] > 0
            assert candle["low"] > 0
            assert candle["close"] > 0
            assert candle["volume"] >= 0

    @pytest.mark.asyncio
    async def test_get_klines_invalid_symbol(self, client: BinanceClient) -> None:
        """Test fetching OHLCV for invalid symbol raises SymbolNotFoundError."""
        with pytest.raises(SymbolNotFoundError):
            await client.get_klines(
                symbol="INVALIDSYMBOL",
                interval="1h",
                limit=10,
            )

    @pytest.mark.asyncio
    async def test_get_klines_different_intervals(
        self,
        client: BinanceClient,
    ) -> None:
        """Test fetching data with different timeframes."""
        intervals = ["1m", "5m", "15m", "1h", "4h", "1d"]

        for interval in intervals:
            klines = await client.get_klines(
                symbol="BTCUSDT",
                interval=interval,
                limit=3,
            )

            assert len(klines) == 3, f"Failed for interval {interval}"

    @pytest.mark.asyncio
    async def test_get_exchange_info_all(self, client: BinanceClient) -> None:
        """Test fetching exchange info for all symbols."""
        exchange_info = await client.get_exchange_info()

        # Should have symbols list
        assert "symbols" in exchange_info
        assert len(exchange_info["symbols"]) > 0

        # Verify structure of first symbol
        first_symbol = exchange_info["symbols"][0]
        assert "symbol" in first_symbol
        assert "baseAsset" in first_symbol
        assert "quoteAsset" in first_symbol
        assert "filters" in first_symbol

    @pytest.mark.asyncio
    async def test_get_exchange_info_specific_symbol(
        self,
        client: BinanceClient,
    ) -> None:
        """Test fetching exchange info for specific symbol."""
        exchange_info = await client.get_exchange_info(symbol="BTCUSDT")

        # Should have BTCUSDT data
        assert "symbol" in exchange_info or "symbols" in exchange_info

        # Verify filters are present
        if "filters" in exchange_info:
            filters = exchange_info["filters"]
        else:
            filters = exchange_info["symbols"][0]["filters"]

        # Should have LOT_SIZE, PRICE_FILTER, MIN_NOTIONAL
        filter_types = [f["filterType"] for f in filters]
        assert "LOT_SIZE" in filter_types
        assert "PRICE_FILTER" in filter_types
        assert ("MIN_NOTIONAL" in filter_types or "NOTIONAL" in filter_types)

    @pytest.mark.asyncio
    async def test_get_exchange_info_invalid_symbol(
        self,
        client: BinanceClient,
    ) -> None:
        """Test fetching exchange info for invalid symbol raises error."""
        with pytest.raises(SymbolNotFoundError):
            await client.get_exchange_info(symbol="INVALIDSYMBOL")

    @pytest.mark.asyncio
    async def test_get_account_with_auth(self, client: BinanceClient) -> None:
        """Test fetching account info with authentication.

        IMPORTANT: This test requires valid Binance testnet API keys.
        Skip this test if keys are not configured.

        To enable: Remove @pytest.mark.skipif and configure keys in .env
        """
        account_info = await client.get_account()

        # Should have account data
        assert "balances" in account_info
        assert "canTrade" in account_info

        # Balances should be a list
        assert isinstance(account_info["balances"], list)

    @pytest.mark.asyncio
    async def test_rate_limit_stats(self, client: BinanceClient) -> None:
        """Test rate limit statistics tracking."""
        # Make a request
        await client.get_klines(
            symbol="BTCUSDT",
            interval="1h",
            limit=10,
        )

        # Get stats
        stats = client.get_rate_limit_stats()

        # Stats should be updated
        assert "requests_usage_pct" in stats
        assert "orders_usage_pct" in stats
        assert "daily_orders_usage_pct" in stats

        # Usage should be very low (< 1%)
        assert stats["requests_usage_pct"] < 1

    @pytest.mark.asyncio
    async def test_multiple_sequential_requests(
        self,
        client: BinanceClient,
    ) -> None:
        """Test multiple sequential requests work correctly."""
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

        for symbol in symbols:
            klines = await client.get_klines(
                symbol=symbol,
                interval="1h",
                limit=5,
            )

            assert len(klines) == 5
            assert all(k["open"] > 0 for k in klines)

        # Rate limiter should handle multiple requests
        stats = client.get_rate_limit_stats()
        assert stats["requests_usage_pct"] < 5  # Very low usage

    @pytest.mark.asyncio
    async def test_klines_with_time_range(self, client: BinanceClient) -> None:
        """Test fetching OHLCV with start/end time."""
        # Fetch data from 24 hours ago to now
        now = datetime.now(timezone.utc)
        start_ms = int((now.timestamp() - 86400) * 1000)  # 24 hours ago
        end_ms = int(now.timestamp() * 1000)

        klines = await client.get_klines(
            symbol="BTCUSDT",
            interval="1h",
            limit=24,
            start_time=start_ms,
            end_time=end_ms,
        )

        # Should return ~24 candles (1 per hour)
        assert len(klines) > 0
        assert len(klines) <= 24

        # Verify timestamps are within range
        for candle in klines:
            timestamp_ms = candle["timestamp"]
            assert start_ms <= timestamp_ms <= end_ms

    @pytest.mark.asyncio
    async def test_error_handling_network_timeout(
        self,
        client: BinanceClient,
    ) -> None:
        """Test error handling for network issues.

        Note: This test is difficult to reliably trigger without
        mocking, so it documents expected behavior.
        """
        # In production, network errors would raise BinanceConnectionError
        # This is tested in unit tests with mocked responses
        pass

    @pytest.mark.asyncio
    async def test_client_initialization_testnet(self) -> None:
        """Test client initializes correctly in testnet mode."""
        client = BinanceClient(testnet=True)

        assert client.testnet is True
        assert client.client is not None
        assert client.rate_limiter is not None

    @pytest.mark.asyncio
    async def test_klines_data_quality(self, client: BinanceClient) -> None:
        """Test fetched klines have good data quality."""
        klines = await client.get_klines(
            symbol="BTCUSDT",
            interval="1h",
            limit=100,
        )

        # Verify all candles have valid OHLCV data
        for i, candle in enumerate(klines):
            # Prices should be positive
            assert candle["open"] > 0, f"Candle {i}: open price is invalid"
            assert candle["high"] > 0, f"Candle {i}: high price is invalid"
            assert candle["low"] > 0, f"Candle {i}: low price is invalid"
            assert candle["close"] > 0, f"Candle {i}: close price is invalid"

            # Volume can be zero but not negative
            assert candle["volume"] >= 0, f"Candle {i}: volume is negative"

            # OHLC relationships
            assert (
                candle["high"] >= candle["low"]
            ), f"Candle {i}: high < low"
            assert (
                candle["open"] >= candle["low"]
            ), f"Candle {i}: open < low"
            assert (
                candle["open"] <= candle["high"]
            ), f"Candle {i}: open > high"
            assert (
                candle["close"] >= candle["low"]
            ), f"Candle {i}: close < low"
            assert (
                candle["close"] <= candle["high"]
            ), f"Candle {i}: close > high"

        # Verify timestamps are sequential (ascending order)
        for i in range(1, len(klines)):
            assert (
                klines[i]["timestamp"] > klines[i - 1]["timestamp"]
            ), f"Timestamps not sequential at index {i}"
