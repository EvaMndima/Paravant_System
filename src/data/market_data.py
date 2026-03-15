"""Market data structures and fetching.

Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
Decision: DEC-2026-02-08-007 - Input validation at model layer
Decision: DEC-2026-02-10-001 - Use python-binance SDK wrapper

This module provides OHLCV (Open, High, Low, Close, Volume) data structures
and market data fetching functionality with comprehensive validation.

Features:
- OHLCV dataclass with validation (NaN, Infinity, OHLC relationships)
- OHLCVSeries with numpy array properties for indicator calculations
- MarketDataFetcher for real-time and historical data
- Pagination support for large historical data requests
- Deduplication and sorting
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from src.brokers.binance.client import BinanceClient
from src.core.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OHLCV:
    """Single candlestick with OHLCV data.

    Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
    Decision: DEC-2026-02-08-007 - Input validation at construction

    This dataclass represents a single candlestick (OHLCV bar) with
    comprehensive validation to prevent data corruption.

    Attributes:
        timestamp: Candle open time (timezone-aware UTC).
        open: Open price.
        high: High price.
        low: Low price.
        close: Close price.
        volume: Volume in base asset.

    Raises:
        ValueError: If any validation fails (NaN, Infinity, negative, OHLC relationships).
    """

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        """Validate OHLCV data on initialization.

        Decision: DEC-2026-02-08-007 - Input validation at model layer

        Validates:
        - No NaN values
        - No Infinity values
        - No negative values
        - Valid OHLC relationships (high >= low, open/close within range)
        - Timezone-aware timestamp
        """
        # Validate numeric fields for NaN, Infinity, negative
        for field_name in ["open", "high", "low", "close", "volume"]:
            value = getattr(self, field_name)

            if value is None:
                raise ValueError(f"{field_name} cannot be None")

            if math.isnan(value):
                raise ValueError(f"{field_name} cannot be NaN")

            if math.isinf(value):
                raise ValueError(f"{field_name} cannot be Infinity")

            if value < 0:
                raise ValueError(
                    f"{field_name} must be non-negative (got {value})"
                )

        # Validate OHLC relationships
        if self.high < self.low:
            raise ValueError(
                f"High ({self.high}) cannot be less than Low ({self.low})"
            )

        if self.open < self.low or self.open > self.high:
            raise ValueError(
                f"Open ({self.open}) must be between Low ({self.low}) "
                f"and High ({self.high})"
            )

        if self.close < self.low or self.close > self.high:
            raise ValueError(
                f"Close ({self.close}) must be between Low ({self.low}) "
                f"and High ({self.high})"
            )

        # Validate timestamp is timezone-aware
        # Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
        if self.timestamp.tzinfo is None:
            raise ValueError(
                "timestamp must be timezone-aware (use datetime.now(timezone.utc))"
            )

    @property
    def hl2(self) -> float:
        """Calculate (High + Low) / 2.

        Returns:
            Average of high and low prices.
        """
        return (self.high + self.low) / 2.0

    @property
    def hlc3(self) -> float:
        """Calculate (High + Low + Close) / 3.

        Returns:
            Average of high, low, and close prices.
        """
        return (self.high + self.low + self.close) / 3.0

    @property
    def ohlc4(self) -> float:
        """Calculate (Open + High + Low + Close) / 4.

        Returns:
            Average of open, high, low, and close prices.
        """
        return (self.open + self.high + self.low + self.close) / 4.0

    @property
    def typical_price(self) -> float:
        """Calculate typical price (HLC3).

        Alias for hlc3 property.

        Returns:
            Typical price (high + low + close) / 3.
        """
        return self.hlc3

    def __repr__(self) -> str:
        """String representation of OHLCV.

        Returns:
            String with timestamp and OHLCV values.
        """
        return (
            f"OHLCV(timestamp={self.timestamp.isoformat()}, "
            f"O={self.open:.2f}, H={self.high:.2f}, L={self.low:.2f}, "
            f"C={self.close:.2f}, V={self.volume:.2f})"
        )


class OHLCVSeries:
    """Collection of OHLCV candles with convenience methods.

    Provides numpy array access and pandas DataFrame conversion
    for indicator calculations.

    Attributes:
        candles: List of OHLCV objects (sorted by timestamp).
        symbol: Trading pair symbol.
        timeframe: Candlestick timeframe.
    """

    def __init__(
        self,
        candles: list[OHLCV],
        symbol: str,
        timeframe: str,
    ) -> None:
        """Initialize OHLCV series.

        Args:
            candles: List of OHLCV objects (will be sorted by timestamp).
            symbol: Trading pair symbol (e.g., "BTCUSDT").
            timeframe: Candlestick timeframe (e.g., "1m", "5m", "1h", "1d").

        Raises:
            ValueError: If candles list is empty.
        """
        if not candles:
            raise ValueError("Candles list cannot be empty")

        # Sort candles by timestamp
        self.candles = sorted(candles, key=lambda c: c.timestamp)
        self.symbol = symbol
        self.timeframe = timeframe

        logger.debug(
            "ohlcv_series_created",
            symbol=symbol,
            timeframe=timeframe,
            count=len(candles),
            start_time=self.candles[0].timestamp.isoformat() if candles else "N/A",
            end_time=self.candles[-1].timestamp.isoformat() if candles else "N/A",
        )

    def __len__(self) -> int:
        """Get number of candles.

        Returns:
            Number of candles in series.
        """
        return len(self.candles)

    def __getitem__(self, index: int) -> OHLCV:
        """Get candle by index.

        Args:
            index: Candle index (supports negative indexing).

        Returns:
            OHLCV candle at index.
        """
        return self.candles[index]

    @property
    def opens(self) -> NDArray[np.float64]:
        """Get open prices as numpy array.

        Returns:
            Numpy array of open prices (float64).
        """
        return np.array([c.open for c in self.candles], dtype=np.float64)

    @property
    def highs(self) -> NDArray[np.float64]:
        """Get high prices as numpy array.

        Returns:
            Numpy array of high prices (float64).
        """
        return np.array([c.high for c in self.candles], dtype=np.float64)

    @property
    def lows(self) -> NDArray[np.float64]:
        """Get low prices as numpy array.

        Returns:
            Numpy array of low prices (float64).
        """
        return np.array([c.low for c in self.candles], dtype=np.float64)

    @property
    def closes(self) -> NDArray[np.float64]:
        """Get close prices as numpy array.

        Returns:
            Numpy array of close prices (float64).
        """
        return np.array([c.close for c in self.candles], dtype=np.float64)

    @property
    def volumes(self) -> NDArray[np.float64]:
        """Get volumes as numpy array.

        Returns:
            Numpy array of volumes (float64).
        """
        return np.array([c.volume for c in self.candles], dtype=np.float64)

    @property
    def timestamps(self) -> NDArray[np.datetime64]:
        """Get timestamps as numpy array.

        Returns:
            Numpy array of timestamps (datetime64[ms]).
        """
        return np.array(
            [c.timestamp for c in self.candles],
            dtype="datetime64[ms]",
        )

    @property
    def hl2(self) -> NDArray[np.float64]:
        """Get (High + Low) / 2 as numpy array.

        Returns:
            Numpy array of HL2 values (float64).
        """
        return (self.highs + self.lows) / 2.0

    @property
    def hlc3(self) -> NDArray[np.float64]:
        """Get (High + Low + Close) / 3 as numpy array.

        Returns:
            Numpy array of HLC3 values (float64).
        """
        return (self.highs + self.lows + self.closes) / 3.0

    @property
    def ohlc4(self) -> NDArray[np.float64]:
        """Get (Open + High + Low + Close) / 4 as numpy array.

        Returns:
            Numpy array of OHLC4 values (float64).
        """
        return (self.opens + self.highs + self.lows + self.closes) / 4.0

    @property
    def typical_price(self) -> NDArray[np.float64]:
        """Get typical price (HLC3) as numpy array.

        Alias for hlc3 property.

        Returns:
            Numpy array of typical prices (float64).
        """
        return self.hlc3

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame.

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume.
            Index is set to timestamp.
        """
        df = pd.DataFrame(
            {
                "timestamp": [c.timestamp for c in self.candles],
                "open": [c.open for c in self.candles],
                "high": [c.high for c in self.candles],
                "low": [c.low for c in self.candles],
                "close": [c.close for c in self.candles],
                "volume": [c.volume for c in self.candles],
            }
        )
        df.set_index("timestamp", inplace=True)
        return df

    def slice(self, start: int | None = None, end: int | None = None) -> OHLCVSeries:
        """Get a slice of the series.

        Args:
            start: Start index (inclusive, optional).
            end: End index (exclusive, optional).

        Returns:
            New OHLCVSeries with sliced candles.
        """
        sliced_candles = self.candles[start:end]
        return OHLCVSeries(
            candles=sliced_candles,
            symbol=self.symbol,
            timeframe=self.timeframe,
        )

    def __repr__(self) -> str:
        """String representation of series.

        Returns:
            String with symbol, timeframe, and candle count.
        """
        return (
            f"OHLCVSeries(symbol={self.symbol}, timeframe={self.timeframe}, "
            f"count={len(self.candles)})"
        )


class MarketDataFetcher:
    """Fetch OHLCV market data from Binance.

    Decision: DEC-2026-02-10-001 - Use python-binance SDK wrapper

    This class provides high-level methods for fetching market data
    with pagination support for historical data.

    Attributes:
        client: BinanceClient instance for API calls.
    """

    def __init__(self, client: BinanceClient | None = None) -> None:
        """Initialize market data fetcher.

        Args:
            client: BinanceClient instance (creates new if None).
        """
        self.client = client or BinanceClient(testnet=get_settings().binance_testnet)

        logger.info("market_data_fetcher_initialized")

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
        start_time: datetime | int | None = None,
        end_time: datetime | int | None = None,
    ) -> OHLCVSeries:
        """Fetch recent OHLCV data.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT").
            timeframe: Candlestick timeframe (e.g., "1m", "5m", "1h", "1d").
            limit: Number of candles to fetch (max 1000, default 500).

        Returns:
            OHLCVSeries with fetched candles.

        Raises:
            MarketDataError: If fetch fails.
            ValueError: If limit invalid.
        """
        logger.info(
            "fetching_ohlcv",
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )

        try:
            # Convert datetimes to milliseconds
            start_ms = int(start_time.timestamp() * 1000) if isinstance(start_time, datetime) else start_time
            end_ms = int(end_time.timestamp() * 1000) if isinstance(end_time, datetime) else end_time

            # Fetch from Binance
            klines = await self.client.get_klines(
                symbol=symbol,
                interval=timeframe,
                limit=limit,
                start_time=start_ms,
                end_time=end_ms,
            )

            # Convert to OHLCV objects
            candles = self._parse_klines(klines)

            # Deduplicate
            candles = self._deduplicate_candles(candles)

            # Create series
            series = OHLCVSeries(
                candles=candles,
                symbol=symbol,
                timeframe=timeframe,
            )

            logger.info(
                "ohlcv_fetched",
                symbol=symbol,
                timeframe=timeframe,
                count=len(series),
            )

            return series

        except Exception as e:
            logger.error(
                "ohlcv_fetch_failed",
                symbol=symbol,
                timeframe=timeframe,
                error=str(e),
                exc_info=True,
            )
            raise

    async def fetch_historical_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime | None = None,
    ) -> OHLCVSeries:
        """Fetch historical OHLCV data with pagination.

        Binance returns max 1000 candles per request, so this method
        automatically paginates to fetch larger date ranges.

        Decision: DEC-2026-02-08-003 - Timezone-aware timestamps

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT").
            timeframe: Candlestick timeframe (e.g., "1m", "5m", "1h", "1d").
            start_date: Start date (timezone-aware).
            end_date: End date (timezone-aware, defaults to now).

        Returns:
            OHLCVSeries with all fetched candles (deduplicated and sorted).

        Raises:
            MarketDataError: If fetch fails.
            ValueError: If dates invalid or not timezone-aware.
        """
        # Validate dates are timezone-aware
        if start_date.tzinfo is None:
            raise ValueError("start_date must be timezone-aware")

        if end_date is None:
            end_date = datetime.now(timezone.utc)
        elif end_date.tzinfo is None:
            raise ValueError("end_date must be timezone-aware")

        if start_date >= end_date:
            raise ValueError("start_date must be before end_date")

        logger.info(
            "fetching_historical_ohlcv",
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        all_candles: list[OHLCV] = []
        current_start = start_date
        max_iterations = 100  # Safety limit to prevent infinite loops

        iteration = 0
        while current_start < end_date and iteration < max_iterations:
            iteration += 1

            # Convert to milliseconds for Binance API
            start_ms = int(current_start.timestamp() * 1000)
            end_ms = int(end_date.timestamp() * 1000)

            try:
                # Fetch batch (max 1000 candles)
                klines = await self.client.get_klines(
                    symbol=symbol,
                    interval=timeframe,
                    limit=1000,
                    start_time=start_ms,
                    end_time=end_ms,
                )

                if not klines:
                    # No more data available
                    break

                # Parse klines
                batch_candles = self._parse_klines(klines)
                all_candles.extend(batch_candles)

                logger.debug(
                    "historical_batch_fetched",
                    symbol=symbol,
                    batch_size=len(batch_candles),
                    iteration=iteration,
                    total_candles=len(all_candles),
                )

                # Update start time for next batch
                # Use timestamp of last candle + 1ms to avoid duplicates
                last_timestamp = batch_candles[-1].timestamp
                current_start = last_timestamp + timedelta(milliseconds=1)

                # If we got less than 1000 candles, we've reached the end
                if len(klines) < 1000:
                    break

            except Exception as e:
                logger.error(
                    "historical_batch_fetch_failed",
                    symbol=symbol,
                    iteration=iteration,
                    error=str(e),
                    exc_info=True,
                )
                raise

        if iteration >= max_iterations:
            logger.warning(
                "historical_fetch_max_iterations",
                symbol=symbol,
                max_iterations=max_iterations,
                candles_fetched=len(all_candles),
            )

        # Deduplicate and sort
        all_candles = self._deduplicate_candles(all_candles)

        logger.info(
            "historical_ohlcv_fetched",
            symbol=symbol,
            timeframe=timeframe,
            total_candles=len(all_candles),
            iterations=iteration,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        return OHLCVSeries(
            candles=all_candles,
            symbol=symbol,
            timeframe=timeframe,
        )

    def _parse_klines(self, klines: list[dict[str, Any]]) -> list[OHLCV]:
        """Parse Binance klines to OHLCV objects.

        Decision: DEC-2026-02-08-003 - Timezone-aware timestamps

        Args:
            klines: List of kline dictionaries from Binance.

        Returns:
            List of OHLCV objects.
        """
        candles: list[OHLCV] = []

        for kline in klines:
            try:
                # Convert timestamp to timezone-aware datetime
                timestamp = datetime.fromtimestamp(
                    kline["timestamp"] / 1000, tz=timezone.utc
                )

                candle = OHLCV(
                    timestamp=timestamp,
                    open=kline["open"],
                    high=kline["high"],
                    low=kline["low"],
                    close=kline["close"],
                    volume=kline["volume"],
                )

                candles.append(candle)

            except (KeyError, ValueError) as e:
                logger.warning(
                    "kline_parse_failed",
                    kline=kline,
                    error=str(e),
                )
                continue

        return candles

    def _deduplicate_candles(self, candles: list[OHLCV]) -> list[OHLCV]:
        """Remove duplicate candles and sort by timestamp.

        Args:
            candles: List of OHLCV candles (may contain duplicates).

        Returns:
            Deduplicated and sorted list of OHLCV candles.
        """
        # Use dict to deduplicate by timestamp
        unique_candles: dict[datetime, OHLCV] = {}

        for candle in candles:
            # Keep first occurrence (or could keep last, doesn't matter much)
            if candle.timestamp not in unique_candles:
                unique_candles[candle.timestamp] = candle

        # Sort by timestamp
        sorted_candles = sorted(unique_candles.values(), key=lambda c: c.timestamp)

        duplicates_removed = len(candles) - len(sorted_candles)
        if duplicates_removed > 0:
            logger.info(
                "candles_deduplicated",
                original_count=len(candles),
                unique_count=len(sorted_candles),
                duplicates_removed=duplicates_removed,
            )

        return sorted_candles
