"""Unit tests for market data module (OHLCV structures and fetching).

Decision: DEC-2026-02-10-001 - Use python-binance SDK wrapper
Decision: DEC-2026-02-08-003 - Timezone-aware timestamps

This module tests:
- OHLCV dataclass validation (NaN, Infinity, OHLC relationships)
- OHLCVSeries properties and methods
- MarketDataFetcher with mocked Binance responses
- Historical data pagination and deduplication
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from src.brokers.binance.client import BinanceClient
from src.data.market_data import OHLCV, OHLCVSeries, MarketDataFetcher


class TestOHLCV:
    """Test OHLCV dataclass validation."""

    def test_valid_ohlcv_creation(self) -> None:
        """Test creating valid OHLCV candle."""
        candle = OHLCV(
            timestamp=datetime.now(timezone.utc),
            open=42000.0,
            high=42100.0,
            low=41900.0,
            close=42050.0,
            volume=100.5,
        )

        assert candle.open == 42000.0
        assert candle.high == 42100.0
        assert candle.low == 41900.0
        assert candle.close == 42050.0
        assert candle.volume == 100.5
        assert candle.timestamp.tzinfo is not None  # Timezone-aware

    def test_ohlcv_rejects_nan_values(self) -> None:
        """Test OHLCV rejects NaN values."""
        with pytest.raises(ValueError, match="cannot be NaN"):
            OHLCV(
                timestamp=datetime.now(timezone.utc),
                open=math.nan,  # Invalid
                high=42100.0,
                low=41900.0,
                close=42050.0,
                volume=100.0,
            )

    def test_ohlcv_rejects_infinity_values(self) -> None:
        """Test OHLCV rejects Infinity values."""
        with pytest.raises(ValueError, match="cannot be Infinity"):
            OHLCV(
                timestamp=datetime.now(timezone.utc),
                open=42000.0,
                high=math.inf,  # Invalid
                low=41900.0,
                close=42050.0,
                volume=100.0,
            )

    def test_ohlcv_rejects_negative_values(self) -> None:
        """Test OHLCV rejects negative prices."""
        with pytest.raises(ValueError, match="must be non-negative"):
            OHLCV(
                timestamp=datetime.now(timezone.utc),
                open=-42000.0,  # Invalid
                high=42100.0,
                low=41900.0,
                close=42050.0,
                volume=100.0,
            )

    def test_ohlcv_validates_high_low_relationship(self) -> None:
        """Test OHLCV validates high >= low."""
        with pytest.raises(ValueError, match="cannot be less than Low"):
            OHLCV(
                timestamp=datetime.now(timezone.utc),
                open=42000.0,
                high=41900.0,  # High < low (invalid)
                low=42100.0,
                close=42050.0,
                volume=100.0,
            )

    def test_ohlcv_validates_open_within_range(self) -> None:
        """Test OHLCV validates open is within high/low."""
        with pytest.raises(ValueError, match="Open .* must be between Low .* and High"):
            OHLCV(
                timestamp=datetime.now(timezone.utc),
                open=43000.0,  # Open > high (invalid)
                high=42100.0,
                low=41900.0,
                close=42050.0,
                volume=100.0,
            )

    def test_ohlcv_validates_close_within_range(self) -> None:
        """Test OHLCV validates close is within high/low."""
        with pytest.raises(ValueError, match="Close .* must be between Low .* and High"):
            OHLCV(
                timestamp=datetime.now(timezone.utc),
                open=42000.0,
                high=42100.0,
                low=41900.0,
                close=41800.0,  # Close < low (invalid)
                volume=100.0,
            )

    def test_ohlcv_requires_timezone_aware_timestamp(self) -> None:
        """Test OHLCV requires timezone-aware timestamp.

        Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
        """
        # Naive timestamp (no timezone) should raise error
        with pytest.raises(ValueError, match="must be timezone-aware"):
            OHLCV(
                timestamp=datetime.now(),  # Naive timestamp (invalid)
                open=42000.0,
                high=42100.0,
                low=41900.0,
                close=42050.0,
                volume=100.0,
            )


class TestOHLCVSeries:
    """Test OHLCVSeries properties and methods."""

    @pytest.fixture
    def sample_series(self) -> OHLCVSeries:
        """Create sample OHLCV series for testing."""
        base_time = datetime.now(timezone.utc)
        candles = [
            OHLCV(
                timestamp=base_time + timedelta(hours=i),
                open=40000.0 + (i * 100),
                high=40100.0 + (i * 100),
                low=39900.0 + (i * 100),
                close=40050.0 + (i * 100),
                volume=100.0 + i,
            )
            for i in range(10)
        ]

        return OHLCVSeries(
            candles=candles,
            symbol="BTCUSDT",
            timeframe="1h",
        )

    def test_series_len(self, sample_series: OHLCVSeries) -> None:
        """Test series length."""
        assert len(sample_series) == 10

    def test_series_closes_property(self, sample_series: OHLCVSeries) -> None:
        """Test closes property returns numpy array."""
        closes = sample_series.closes

        assert len(closes) == 10
        assert closes[0] == 40050.0
        assert closes[-1] == 40950.0

    def test_series_highs_property(self, sample_series: OHLCVSeries) -> None:
        """Test highs property returns numpy array."""
        highs = sample_series.highs

        assert len(highs) == 10
        assert highs[0] == 40100.0
        assert highs[-1] == 41000.0

    def test_series_lows_property(self, sample_series: OHLCVSeries) -> None:
        """Test lows property returns numpy array."""
        lows = sample_series.lows

        assert len(lows) == 10
        assert lows[0] == 39900.0
        assert lows[-1] == 40800.0

    def test_series_volumes_property(self, sample_series: OHLCVSeries) -> None:
        """Test volumes property returns numpy array."""
        volumes = sample_series.volumes

        assert len(volumes) == 10
        assert volumes[0] == 100.0
        assert volumes[-1] == 109.0

    def test_series_hl2_property(self, sample_series: OHLCVSeries) -> None:
        """Test HL2 (high+low)/2 property."""
        hl2 = sample_series.hl2

        # HL2 = (high + low) / 2
        expected_first = (40100.0 + 39900.0) / 2
        assert hl2[0] == expected_first

    def test_series_hlc3_property(self, sample_series: OHLCVSeries) -> None:
        """Test HLC3 (high+low+close)/3 property."""
        hlc3 = sample_series.hlc3

        # HLC3 = (high + low + close) / 3
        expected_first = (40100.0 + 39900.0 + 40050.0) / 3
        assert abs(hlc3[0] - expected_first) < 0.01  # Float precision

    def test_series_ohlc4_property(self, sample_series: OHLCVSeries) -> None:
        """Test OHLC4 (open+high+low+close)/4 property."""
        ohlc4 = sample_series.ohlc4

        # OHLC4 = (open + high + low + close) / 4
        expected_first = (40000.0 + 40100.0 + 39900.0 + 40050.0) / 4
        assert abs(ohlc4[0] - expected_first) < 0.01  # Float precision

    def test_series_empty(self) -> None:
        """Test empty series raises ValueError."""
        with pytest.raises(ValueError, match="Candles list cannot be empty"):
            OHLCVSeries(candles=[], symbol="BTCUSDT", timeframe="1h")


class TestMarketDataFetcher:
    """Test MarketDataFetcher with mocked Binance client."""

    @pytest.fixture
    def mock_binance_client(self) -> AsyncMock:
        """Create mock Binance client."""
        client = AsyncMock(spec=BinanceClient)
        return client

    @pytest.fixture
    def fetcher(self, mock_binance_client: AsyncMock) -> MarketDataFetcher:
        """Create MarketDataFetcher with mock client."""
        return MarketDataFetcher(client=mock_binance_client)

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_success(
        self,
        fetcher: MarketDataFetcher,
        mock_binance_client: AsyncMock,
    ) -> None:
        """Test successful OHLCV fetch."""
        # Mock response from Binance
        mock_binance_client.get_klines.return_value = [
            {
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                "open": 42000.0,
                "high": 42100.0,
                "low": 41900.0,
                "close": 42050.0,
                "volume": 100.0,
            },
            {
                "timestamp": int(
                    (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp() * 1000
                ),
                "open": 42050.0,
                "high": 42200.0,
                "low": 42000.0,
                "close": 42150.0,
                "volume": 150.0,
            },
        ]

        series = await fetcher.fetch_ohlcv(
            symbol="BTCUSDT",
            timeframe="1h",
            limit=2,
        )

        assert len(series) == 2
        assert series.symbol == "BTCUSDT"
        assert series.timeframe == "1h"
        assert series.candles[0].open == 42000.0
        assert series.candles[1].open == 42050.0

        # Verify client was called correctly
        mock_binance_client.get_klines.assert_called_once_with(
            symbol="BTCUSDT",
            interval="1h",
            limit=2,
            start_time=None,
            end_time=None,
        )

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_with_time_range(
        self,
        fetcher: MarketDataFetcher,
        mock_binance_client: AsyncMock,
    ) -> None:
        """Test OHLCV fetch with start/end time."""
        start_time = datetime.now(timezone.utc) - timedelta(days=1)
        end_time = datetime.now(timezone.utc)

        # Return valid data so OHLCVSeries construction succeeds
        mock_binance_client.get_klines.return_value = [
            {
                "timestamp": int(start_time.timestamp() * 1000),
                "open": 42000.0,
                "high": 42100.0,
                "low": 41900.0,
                "close": 42050.0,
                "volume": 100.0,
            },
        ]

        await fetcher.fetch_ohlcv(
            symbol="BTCUSDT",
            timeframe="1h",
            limit=10,
            start_time=start_time,
            end_time=end_time,
        )

        # Verify start/end time converted to milliseconds
        call_kwargs = mock_binance_client.get_klines.call_args.kwargs
        assert call_kwargs["start_time"] == int(start_time.timestamp() * 1000)
        assert call_kwargs["end_time"] == int(end_time.timestamp() * 1000)

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_sorts_by_timestamp(
        self,
        fetcher: MarketDataFetcher,
        mock_binance_client: AsyncMock,
    ) -> None:
        """Test OHLCV data is sorted by timestamp."""
        base_time = datetime.now(timezone.utc)

        # Return data out of order
        mock_binance_client.get_klines.return_value = [
            {
                "timestamp": int((base_time + timedelta(hours=2)).timestamp() * 1000),
                "open": 42200.0,
                "high": 42300.0,
                "low": 42100.0,
                "close": 42250.0,
                "volume": 200.0,
            },
            {
                "timestamp": int(base_time.timestamp() * 1000),
                "open": 42000.0,
                "high": 42100.0,
                "low": 41900.0,
                "close": 42050.0,
                "volume": 100.0,
            },
        ]

        series = await fetcher.fetch_ohlcv(
            symbol="BTCUSDT",
            timeframe="1h",
            limit=2,
        )

        # Should be sorted by timestamp (oldest first)
        assert series.candles[0].open == 42000.0  # Earlier candle
        assert series.candles[1].open == 42200.0  # Later candle

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_deduplicates(
        self,
        fetcher: MarketDataFetcher,
        mock_binance_client: AsyncMock,
    ) -> None:
        """Test OHLCV data deduplication."""
        base_time = datetime.now(timezone.utc)
        timestamp_ms = int(base_time.timestamp() * 1000)

        # Return duplicate timestamps
        mock_binance_client.get_klines.return_value = [
            {
                "timestamp": timestamp_ms,
                "open": 42000.0,
                "high": 42100.0,
                "low": 41900.0,
                "close": 42050.0,
                "volume": 100.0,
            },
            {
                "timestamp": timestamp_ms,  # Duplicate
                "open": 42000.0,
                "high": 42100.0,
                "low": 41900.0,
                "close": 42050.0,
                "volume": 100.0,
            },
        ]

        series = await fetcher.fetch_ohlcv(
            symbol="BTCUSDT",
            timeframe="1h",
            limit=2,
        )

        # Should deduplicate
        assert len(series) == 1

    @pytest.mark.asyncio
    async def test_fetch_historical_ohlcv_pagination(
        self,
        fetcher: MarketDataFetcher,
        mock_binance_client: AsyncMock,
    ) -> None:
        """Test historical fetch with pagination (>1000 candles).
        
        Binance limits to 1000 candles per request.
        """
        # Base time for test data (60 days ago)
        base_time = datetime.now(timezone.utc) - timedelta(days=60)
        
        # First batch (1000 candles) starting from base_time
        first_batch = [
            {
                "timestamp": int(
                    (base_time + timedelta(hours=i)).timestamp() * 1000
                ),
                "open": 42000.0 + i,
                "high": 42100.0 + i,
                "low": 41900.0 + i,
                "close": 42050.0 + i,
                "volume": 100.0 + i,
            }
            for i in range(1000)
        ]

        # Second batch (remaining 500 candles)
        second_batch = [
            {
                "timestamp": int(
                    (base_time + timedelta(hours=1000 + i)).timestamp()
                    * 1000
                ),
                "open": 42000.0 + 1000 + i,
                "high": 42100.0 + 1000 + i,
                "low": 41900.0 + 1000 + i,
                "close": 42050.0 + 1000 + i,
                "volume": 100.0 + 1000 + i,
            }
            for i in range(500)
        ]

        # Mock returns batches
        mock_binance_client.get_klines.side_effect = [first_batch, second_batch]

        start_date = base_time
        end_date = datetime.now(timezone.utc)

        series = await fetcher.fetch_historical_ohlcv(
            symbol="BTCUSDT",
            timeframe="1h",
            start_date=start_date,
            end_date=end_date,
        )

        # Should make 2 requests and combine results
        assert mock_binance_client.get_klines.call_count == 2
        assert len(series) == 1500  # 1000 + 500

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_empty_response(
        self,
        fetcher: MarketDataFetcher,
        mock_binance_client: AsyncMock,
    ) -> None:
        """Test OHLCV fetch with empty response raises ValueError."""
        mock_binance_client.get_klines.return_value = []

        with pytest.raises(ValueError, match="Candles list cannot be empty"):
            await fetcher.fetch_ohlcv(
                symbol="BTCUSDT",
                timeframe="1h",
                limit=10,
            )
