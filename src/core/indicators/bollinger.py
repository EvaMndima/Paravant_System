"""Bollinger Bands indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-001 - Compute-on-demand indicator strategy

Bollinger Bands are volatility bands placed above and below a moving average.
The bands widen during volatile periods and contract during quiet periods.

Formula:
    Middle Band = SMA(close, period)
    Upper Band = Middle + (StdDev * multiplier)
    Lower Band = Middle - (StdDev * multiplier)
    Width = (Upper - Lower) / Middle * 100  (% of middle)
    %B = (Close - Lower) / (Upper - Lower) * 100  (position in band, 0-100)

Reference: TradingView Bollinger Bands indicator
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from src.core.indicators.base import Indicator, IndicatorResult
from src.core.indicators.sma import SMA
from src.data.market_data import OHLCVSeries

# Minimum valid width values needed for reliable percentile calculation
MIN_WIDTH_SAMPLES_FOR_PERCENTILE = 20


class BollingerResult(IndicatorResult[float]):
    """Bollinger Bands-specific result with multiple bands.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Extends IndicatorResult to provide direct access to all Bollinger components
    and squeeze/position detection methods.

    Attributes:
        upper: Upper band values.
        middle: Middle band values (SMA).
        lower: Lower band values.
        width: Band width as percentage of middle band.
        percent_b: Price position within bands (0-100).
    """

    def __init__(
        self,
        name: str,
        upper: NDArray[np.float64],
        middle: NDArray[np.float64],
        lower: NDArray[np.float64],
        width: NDArray[np.float64],
        percent_b: NDArray[np.float64],
        params: dict[str, Any],
    ) -> None:
        """Initialize Bollinger Bands result.

        Args:
            name: Indicator name (e.g., "BB_20_2.0").
            upper: Upper band values array.
            middle: Middle band (SMA) values array.
            lower: Lower band values array.
            width: Band width percentage array.
            percent_b: %B values array (0-100).
            params: Parameters (period, multiplier).
        """
        # Store middle band as primary values for base class
        super().__init__(name, middle, params)

        self.upper = upper
        self.middle = middle
        self.lower = lower
        self.width = width
        self.percent_b = percent_b

    def is_squeezed(self, percentile: int = 10) -> bool:
        """Check if bands are squeezed (low volatility).

        Squeeze occurs when band width is in the bottom N percentile of
        recent widths, indicating consolidation before potential breakout.

        Args:
            percentile: Bottom percentile threshold (default 10 = bottom 10%).
                       Range: [1, 100].

        Returns:
            True if current width is in bottom percentile (squeezed).

        Raises:
            ValueError: If insufficient valid width values or percentile out of range.

        Example:
            >>> result = bb.calculate(series)
            >>> if result.is_squeezed(percentile=10):
            ...     print("Squeeze detected: expect breakout soon")
        """
        if not 1 <= percentile <= 100:
            raise ValueError(f"Percentile must be in [1, 100], got {percentile}")

        valid_widths = self.width[~np.isnan(self.width)]

        if len(valid_widths) < MIN_WIDTH_SAMPLES_FOR_PERCENTILE:
            raise ValueError(
                f"Need at least {MIN_WIDTH_SAMPLES_FOR_PERCENTILE} valid width "
                f"values for percentile, got {len(valid_widths)}"
            )

        # Calculate percentile threshold
        threshold = np.percentile(valid_widths, percentile)
        current_width = valid_widths[-1]

        return bool(current_width <= threshold)

    def is_at_upper(self) -> bool:
        """Check if price is at or above upper band.

        Returns:
            True if most recent close >= upper band.

        Raises:
            ValueError: If insufficient valid values.

        Example:
            >>> result = bb.calculate(series)
            >>> if result.is_at_upper():
            ...     print("Price at upper band: potential reversal")
        """
        valid_indices = np.where(~np.isnan(self.percent_b))[0]

        if len(valid_indices) == 0:
            raise ValueError("No valid %B values available")

        current_pb = self.percent_b[valid_indices[-1]]
        return bool(current_pb >= 100.0)

    def is_at_lower(self) -> bool:
        """Check if price is at or below lower band.

        Returns:
            True if most recent close <= lower band.

        Raises:
            ValueError: If insufficient valid values.

        Example:
            >>> result = bb.calculate(series)
            >>> if result.is_at_lower():
            ...     print("Price at lower band: potential reversal")
        """
        valid_indices = np.where(~np.isnan(self.percent_b))[0]

        if len(valid_indices) == 0:
            raise ValueError("No valid %B values available")

        current_pb = self.percent_b[valid_indices[-1]]
        return bool(current_pb <= 0.0)

    def __repr__(self) -> str:
        """String representation of Bollinger Bands result.

        Returns:
            String with BB name and component counts.
        """
        valid_count = np.count_nonzero(~np.isnan(self.middle))
        return f"BollingerResult(name={self.name}, values={valid_count})"


class BollingerBands(Indicator):
    """Bollinger Bands indicator.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Volatility bands around a moving average. Bands expand during high
    volatility and contract during low volatility.

    Attributes:
        period: SMA period for middle band (default 20).
        multiplier: Standard deviation multiplier for bands (default 2.0).

    Example:
        >>> from src.data.service import MarketDataService
        >>> service = MarketDataService()
        >>> series, _ = await service.get_ohlcv("BTCUSDT", "1h", limit=100)
        >>>
        >>> bb = BollingerBands(period=20, multiplier=2.0)
        >>> result = bb.calculate(series)
        >>> print(f"Upper: {result.upper[-1]:.2f}")
        >>> print(f"Middle: {result.middle[-1]:.2f}")
        >>> print(f"Lower: {result.lower[-1]:.2f}")
        >>> print(f"Width: {result.width[-1]:.2f}%")
        >>>
        >>> if result.is_squeezed():
        ...     print("Squeeze: breakout imminent")
    """

    def __init__(self, period: int = 20, multiplier: float = 2.0) -> None:
        """Initialize Bollinger Bands indicator.

        Args:
            period: SMA period for middle band (default 20).
            multiplier: Standard deviation multiplier (default 2.0).
                       Common values: 1.5, 2.0, 2.5.

        Raises:
            ValueError: If period < 2 or multiplier <= 0.
        """
        if period < 2:
            raise ValueError(f"Period must be >= 2, got {period}")
        if multiplier <= 0:
            raise ValueError(f"Multiplier must be > 0, got {multiplier}")

        self.period = period
        self.multiplier = multiplier
        self.sma = SMA(period=period)

    def calculate(self, series: OHLCVSeries) -> BollingerResult:
        """Calculate Bollinger Bands from OHLCV series.

        Calculates five components:
        1. Middle Band (SMA)
        2. Upper Band (SMA + StdDev * multiplier)
        3. Lower Band (SMA - StdDev * multiplier)
        4. Width (band width as % of middle)
        5. %B (price position within bands, 0-100)

        Args:
            series: OHLCV series from Session 1 market data layer.

        Returns:
            BollingerResult with all five components (NaN during warmup).

        Raises:
            ValueError: If series has insufficient data.

        Example:
            >>> series = OHLCVSeries(candles=[...], symbol="BTCUSDT", timeframe="1h")
            >>> bb = BollingerBands(period=20, multiplier=2.0)
            >>> result = bb.calculate(series)
        """
        if len(series) < self.period:
            raise ValueError(
                f"Bollinger({self.period}) requires at least {self.period} bars, "
                f"got {len(series)}"
            )

        closes = series.closes

        # Calculate middle band (SMA)
        middle_result = self.sma.calculate(series)
        middle = middle_result.values

        # Calculate standard deviation for each window
        std_dev: NDArray[np.float64] = np.full(len(closes), np.nan, dtype=np.float64)

        for i in range(self.period - 1, len(closes)):
            window = closes[i - self.period + 1 : i + 1]
            std_dev[i] = np.std(window, ddof=1)  # Sample std dev (ddof=1)

        # Calculate upper and lower bands
        upper = middle + (std_dev * self.multiplier)
        lower = middle - (std_dev * self.multiplier)

        # Calculate band width (as % of middle)
        width: NDArray[np.float64] = np.full(len(closes), np.nan, dtype=np.float64)
        valid_indices = ~np.isnan(middle) & (middle != 0)
        width[valid_indices] = (
            (upper[valid_indices] - lower[valid_indices]) / middle[valid_indices] * 100
        )

        # Calculate %B (price position within bands, 0-100)
        percent_b: NDArray[np.float64] = np.full(len(closes), np.nan, dtype=np.float64)
        band_range = upper - lower
        valid_bands = ~np.isnan(band_range) & (band_range != 0)
        percent_b[valid_bands] = (
            (closes[valid_bands] - lower[valid_bands]) / band_range[valid_bands] * 100
        )

        return BollingerResult(
            name=f"BB_{self.period}_{self.multiplier}",
            upper=upper,
            middle=middle,
            lower=lower,
            width=width,
            percent_b=percent_b,
            params={"period": self.period, "multiplier": self.multiplier},
        )

    def __repr__(self) -> str:
        """String representation of Bollinger Bands indicator.

        Returns:
            String with period and multiplier.
        """
        return f"BollingerBands(period={self.period}, multiplier={self.multiplier})"
