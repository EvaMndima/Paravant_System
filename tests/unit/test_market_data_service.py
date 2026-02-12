"""Unit tests for MarketDataService (high-level interface).

Decision: DEC-2026-02-10-001 - Use python-binance SDK wrapper
Decision: DEC-2026-02-10-004 - Async-first architecture
PRD Feature H - Data Quality Validation

This module tests the high-level MarketDataService interface with mocked
dependencies to ensure proper orchestration of fetching and validation.

Test Coverage:
- get_ohlcv with and without validation
- get_multiple_ohlcv concurrent fetching
- get_prices current price fetching
- get_historical with pagination
- Validation threshold configuration
- Rate limit stats retrieval
- Error handling and logging
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.brokers.binance.client import BinanceClient
from src.core.exceptions import MarketDataError
from src.data.market_data import OHLCV, OHLCVSeries, MarketDataFetcher
from src.data.service import MarketDataService
from src.data.validators import (
    ACTION_INTERPOLATE,
    ACTION_REJECT,
    ACTION_USE,
    DataValidator,
    ValidationResult,
)


class TestMarketDataServiceInitialization:
    """Test MarketDataService initialization."""

    def test_init_with_defaults(self) -> None:
        """Test service initializes with default dependencies."""
        with patch("src.data.service.BinanceClient") as mock_client_class:
            service = MarketDataService()

            # Should create default client
            mock_client_class.assert_called_once_with(testnet=True)
            assert service.fetcher is not None
            assert service.validator is not None

    def test_init_with_custom_client(self) -> None:
        """Test service initializes with custom client."""
        mock_client = MagicMock(spec=BinanceClient)

        service = MarketDataService(client=mock_client)

        # Should use provided client
        assert service.client is mock_client
        assert service.fetcher is not None
        assert service.validator is not None

    def test_init_with_custom_validator(self) -> None:
        """Test service initializes with custom validator."""
        mock_validator = MagicMock(spec=DataValidator)

        with patch("src.data.service.BinanceClient"):
            service = MarketDataService(validator=mock_validator)

            # Should use provided validator
            assert service.validator is mock_validator


class TestGetOHLCV:
    """Test get_ohlcv method."""

    @pytest.fixture
    def mock_fetcher(self) -> AsyncMock:
        """Create mock MarketDataFetcher."""
        return AsyncMock(spec=MarketDataFetcher)

    @pytest.fixture
    def mock_validator(self) -> MagicMock:
        """Create mock DataValidator."""
        return MagicMock(spec=DataValidator)

    @pytest.fixture
    def valid_series(self) -> OHLCVSeries:
        """Create valid OHLCV series for testing."""
        base_time = datetime.now(timezone.utc)
        candles = [
            OHLCV(
                timestamp=base_time - timedelta(hours=10 - i),
                open=42000.0 + (i * 10),
                high=42050.0 + (i * 10),
                low=41950.0 + (i * 10),
                close=42030.0 + (i * 10),
                volume=100.0 + i,
            )
            for i in range(10)
        ]
        return OHLCVSeries(candles=candles, symbol="BTCUSDT", timeframe="1h")

    @pytest.mark.asyncio
    async def test_get_ohlcv_with_validation_success(
        self,
        mock_fetcher: AsyncMock,
        mock_validator: MagicMock,
        valid_series: OHLCVSeries,
    ) -> None:
        """Test get_ohlcv with validation that passes."""
        # Mock fetcher to return valid series
        mock_fetcher.fetch_ohlcv = AsyncMock(return_value=valid_series)

        # Mock validator to return valid result
        mock_validator.validate_ohlcv_series.return_value = ValidationResult(
            is_valid=True,
            issues=[],
            warnings=[],
            action=ACTION_USE,
            metadata={},
        )

        with patch("src.data.service.BinanceClient"):
            service = MarketDataService(validator=mock_validator)
            service.fetcher = mock_fetcher

            # Call get_ohlcv
            series, validation = await service.get_ohlcv(
                symbol="BTCUSDT",
                timeframe="1h",
                limit=10,
                validate=True,
            )

            # Verify results
            assert series == valid_series
            assert validation is not None
            assert validation.is_valid is True
            assert validation.action == ACTION_USE

            # Verify fetcher was called
            mock_fetcher.fetch_ohlcv.assert_called_once_with(
                symbol="BTCUSDT",
                timeframe="1h",
                limit=10,
            )

            # Verify validator was called
            mock_validator.validate_ohlcv_series.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_ohlcv_without_validation(
        self,
        mock_fetcher: AsyncMock,
        mock_validator: MagicMock,
        valid_series: OHLCVSeries,
    ) -> None:
        """Test get_ohlcv with validation disabled."""
        mock_fetcher.fetch_ohlcv = AsyncMock(return_value=valid_series)

        with patch("src.data.service.BinanceClient"):
            service = MarketDataService(validator=mock_validator)
            service.fetcher = mock_fetcher

            # Call get_ohlcv with validate=False
            series, validation = await service.get_ohlcv(
                symbol="BTCUSDT",
                timeframe="1h",
                limit=10,
                validate=False,
            )

            # Verify results
            assert series == valid_series
            assert validation is None  # No validation when disabled

            # Verify validator was NOT called
            mock_validator.validate_ohlcv_series.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_ohlcv_validation_rejects(
        self,
        mock_fetcher: AsyncMock,
        mock_validator: MagicMock,
        valid_series: OHLCVSeries,
    ) -> None:
        """Test get_ohlcv raises error when validation rejects data."""
        mock_fetcher.fetch_ohlcv = AsyncMock(return_value=valid_series)

        # Mock validator to reject data
        mock_validator.validate_ohlcv_series.return_value = ValidationResult(
            is_valid=False,
            issues=["Data is stale (15 seconds old)"],
            warnings=[],
            action=ACTION_REJECT,
            metadata={"price_age_seconds": 15},
        )

        with patch("src.data.service.BinanceClient"):
            service = MarketDataService(validator=mock_validator)
            service.fetcher = mock_fetcher

            # Should raise MarketDataError
            with pytest.raises(MarketDataError) as exc_info:
                await service.get_ohlcv(
                    symbol="BTCUSDT",
                    timeframe="1h",
                    limit=10,
                    validate=True,
                )

            # Verify error message
            assert "Data validation failed" in str(exc_info.value)
            assert "stale" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_ohlcv_validation_interpolate(
        self,
        mock_fetcher: AsyncMock,
        mock_validator: MagicMock,
        valid_series: OHLCVSeries,
    ) -> None:
        """Test get_ohlcv accepts data with ACTION_INTERPOLATE."""
        mock_fetcher.fetch_ohlcv = AsyncMock(return_value=valid_series)

        # Mock validator to suggest interpolation
        mock_validator.validate_ohlcv_series.return_value = ValidationResult(
            is_valid=True,
            issues=[],
            warnings=["Gap of 2 candles detected"],
            action=ACTION_INTERPOLATE,
            metadata={"max_gap_size": 2},
        )

        with patch("src.data.service.BinanceClient"):
            service = MarketDataService(validator=mock_validator)
            service.fetcher = mock_fetcher

            # Should NOT raise error (interpolate is acceptable)
            series, validation = await service.get_ohlcv(
                symbol="BTCUSDT",
                timeframe="1h",
                limit=10,
                validate=True,
            )

            # Verify results
            assert series == valid_series
            assert validation.action == ACTION_INTERPOLATE
            assert len(validation.warnings) == 1


class TestGetMultipleOHLCV:
    """Test get_multiple_ohlcv concurrent fetching."""

    @pytest.fixture
    def mock_fetcher(self) -> AsyncMock:
        """Create mock MarketDataFetcher."""
        return AsyncMock(spec=MarketDataFetcher)

    @pytest.mark.asyncio
    async def test_get_multiple_ohlcv_success(
        self,
        mock_fetcher: AsyncMock,
    ) -> None:
        """Test concurrent fetching of multiple symbols."""
        # Create mock series for each symbol
        def create_series(symbol: str) -> OHLCVSeries:
            base_time = datetime.now(timezone.utc)
            candles = [
                OHLCV(
                    timestamp=base_time - timedelta(hours=5 - i),
                    open=42000.0 + (i * 10),
                    high=42050.0 + (i * 10),
                    low=41950.0 + (i * 10),
                    close=42030.0 + (i * 10),
                    volume=100.0 + i,
                )
                for i in range(5)
            ]
            return OHLCVSeries(candles=candles, symbol=symbol, timeframe="1h")

        # Mock fetcher to return different series for each symbol
        btc_series = create_series("BTCUSDT")
        eth_series = create_series("ETHUSDT")
        mock_fetcher.fetch_ohlcv = AsyncMock(side_effect=[btc_series, eth_series])

        with patch("src.data.service.BinanceClient"):
            service = MarketDataService()
            service.fetcher = mock_fetcher

            # Call get_multiple_ohlcv
            results = await service.get_multiple_ohlcv(
                symbols=["BTCUSDT", "ETHUSDT"],
                timeframe="1h",
                limit=5,
                validate=False,  # Disable validation for simplicity
            )

            # Verify results
            assert len(results) == 2
            assert "BTCUSDT" in results
            assert "ETHUSDT" in results
            assert results["BTCUSDT"][0] == btc_series
            assert results["ETHUSDT"][0] == eth_series

            # Verify fetcher was called twice
            assert mock_fetcher.fetch_ohlcv.call_count == 2

    @pytest.mark.asyncio
    async def test_get_multiple_ohlcv_partial_failure(
        self,
        mock_fetcher: AsyncMock,
    ) -> None:
        """Test concurrent fetching handles partial failures."""

        def create_series(symbol: str) -> OHLCVSeries:
            base_time = datetime.now(timezone.utc)
            candles = [
                OHLCV(
                    timestamp=base_time - timedelta(hours=5 - i),
                    open=42000.0 + (i * 10),
                    high=42050.0 + (i * 10),
                    low=41950.0 + (i * 10),
                    close=42030.0 + (i * 10),
                    volume=100.0 + i,
                )
                for i in range(5)
            ]
            return OHLCVSeries(candles=candles, symbol=symbol, timeframe="1h")

        # Mock fetcher: first succeeds, second fails
        btc_series = create_series("BTCUSDT")
        mock_fetcher.fetch_ohlcv = AsyncMock(
            side_effect=[btc_series, MarketDataError(symbol="ETHUSDT", reason="Invalid symbol")]
        )

        with patch("src.data.service.BinanceClient"):
            service = MarketDataService()
            service.fetcher = mock_fetcher

            # Call get_multiple_ohlcv
            results = await service.get_multiple_ohlcv(
                symbols=["BTCUSDT", "ETHUSDT"],
                timeframe="1h",
                limit=5,
                validate=False,
            )

            # Verify results: successful one present, failed one absent
            assert len(results) == 1
            assert "BTCUSDT" in results
            assert "ETHUSDT" not in results


class TestGetPrices:
    """Test get_prices current price fetching."""

    @pytest.fixture
    def mock_client(self) -> AsyncMock:
        """Create mock BinanceClient."""
        return AsyncMock(spec=BinanceClient)

    @pytest.mark.asyncio
    async def test_get_prices_single_symbol(
        self,
        mock_client: AsyncMock,
    ) -> None:
        """Test fetching current price for single symbol."""
        # Mock client to return recent candles
        mock_client.get_klines = AsyncMock(
            return_value=[
                {
                    "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "open": 42000.0,
                    "high": 42100.0,
                    "low": 41900.0,
                    "close": 42050.0,
                    "volume": 100.0,
                }
            ]
        )

        service = MarketDataService(client=mock_client)

        # Call get_prices
        prices = await service.get_prices(symbols=["BTCUSDT"])

        # Verify results
        assert len(prices) == 1
        assert "BTCUSDT" in prices
        assert prices["BTCUSDT"] == 42050.0  # Close price

    @pytest.mark.asyncio
    async def test_get_prices_multiple_symbols(
        self,
        mock_client: AsyncMock,
    ) -> None:
        """Test fetching current prices for multiple symbols."""
        # Mock client to return different prices for each symbol
        mock_client.get_klines = AsyncMock(
            side_effect=[
                [
                    {
                        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                        "open": 42000.0,
                        "high": 42100.0,
                        "low": 41900.0,
                        "close": 42050.0,
                        "volume": 100.0,
                    }
                ],
                [
                    {
                        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                        "open": 3000.0,
                        "high": 3050.0,
                        "low": 2950.0,
                        "close": 3020.0,
                        "volume": 200.0,
                    }
                ],
            ]
        )

        service = MarketDataService(client=mock_client)

        # Call get_prices
        prices = await service.get_prices(symbols=["BTCUSDT", "ETHUSDT"])

        # Verify results
        assert len(prices) == 2
        assert prices["BTCUSDT"] == 42050.0
        assert prices["ETHUSDT"] == 3020.0


class TestGetHistorical:
    """Test get_historical with pagination."""

    @pytest.fixture
    def mock_fetcher(self) -> AsyncMock:
        """Create mock MarketDataFetcher."""
        return AsyncMock(spec=MarketDataFetcher)

    @pytest.mark.asyncio
    async def test_get_historical_success(
        self,
        mock_fetcher: AsyncMock,
    ) -> None:
        """Test fetching historical data."""
        # Create mock historical series
        base_time = datetime.now(timezone.utc) - timedelta(days=30)
        candles = [
            OHLCV(
                timestamp=base_time + timedelta(hours=i),
                open=42000.0 + (i * 10),
                high=42050.0 + (i * 10),
                low=41950.0 + (i * 10),
                close=42030.0 + (i * 10),
                volume=100.0 + i,
            )
            for i in range(100)
        ]
        series = OHLCVSeries(candles=candles, symbol="BTCUSDT", timeframe="1h")

        mock_fetcher.fetch_historical_ohlcv = AsyncMock(return_value=series)

        with patch("src.data.service.BinanceClient"):
            service = MarketDataService()
            service.fetcher = mock_fetcher

            # Call get_historical
            start_date = base_time
            end_date = datetime.now(timezone.utc)

            result = await service.get_historical(
                symbol="BTCUSDT",
                timeframe="1h",
                start_date=start_date,
                end_date=end_date,
                validate=False,
            )

            # Verify results
            assert result[0] == series
            assert result[1] is None  # No validation

            # Verify fetcher was called
            mock_fetcher.fetch_historical_ohlcv.assert_called_once_with(
                symbol="BTCUSDT",
                timeframe="1h",
                start_date=start_date,
                end_date=end_date,
            )


class TestConfigurationMethods:
    """Test validation threshold configuration."""

    def test_set_validation_threshold(self) -> None:
        """Test setting validation thresholds."""
        with patch("src.data.service.BinanceClient"):
            service = MarketDataService()

            # Set threshold
            service.set_validation_threshold("max_price_age_seconds", 20)

            # Verify threshold was set
            thresholds = service.get_validation_thresholds()
            assert thresholds["max_price_age_seconds"] == 20

    def test_get_validation_thresholds(self) -> None:
        """Test getting validation thresholds."""
        with patch("src.data.service.BinanceClient"):
            service = MarketDataService()

            # Get thresholds
            thresholds = service.get_validation_thresholds()

            # Verify expected keys present
            assert "max_price_age_seconds" in thresholds
            assert "max_price_change_pct" in thresholds
            assert "max_gap_candles" in thresholds

    def test_get_rate_limit_stats(self) -> None:
        """Test getting rate limit stats."""
        mock_client = MagicMock(spec=BinanceClient)
        mock_client.get_rate_limit_stats.return_value = {
            "requests_usage_pct": 25.5,
            "orders_usage_pct": 10.0,
            "daily_orders_usage_pct": 0.05,
        }

        service = MarketDataService(client=mock_client)

        # Get stats
        stats = service.get_rate_limit_stats()

        # Verify stats
        assert stats["requests_usage_pct"] == 25.5
        assert stats["orders_usage_pct"] == 10.0
        assert stats["daily_orders_usage_pct"] == 0.05

        # Verify client method was called
        mock_client.get_rate_limit_stats.assert_called_once()
