"""Simple Moving Average (SMA) indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-001 - Compute-on-demand indicator strategy

SMA calculates the arithmetic mean of prices over a specified period.
It's a foundational indicator used by Bollinger Bands, ADX, and Volume Average.

Formula:
    SMA[t] = Sum(Close[t-period+1:t+1]) / period

Reference: TradingView SMA indicator
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from src.core.indicators.base import Indicator, IndicatorResult
from src.data.market_data import OHLCVSeries


class SMA(Indicator):
    """Simple Moving Average indicator.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Calculates the arithmetic mean of close prices over a specified period.
    Smoother than price action but slower to respond than EMA.

    Attributes:
        period: Number of periods for SMA calculation (default 20).

    Example:
        >>> from src.data.service import MarketDataService
        >>> service = MarketDataService()
        >>> series, _ = await service.get_ohlcv("BTCUSDT", "1h", limit=100)
        >>>
        >>> sma = SMA(period=20)
        >>> result = sma.calculate(series)
        >>> print(f"Current SMA: {result.current:.2f}")
    """

    def __init__(self, period: int = 20) -> None:
        """Initialize SMA indicator.

        Args:
            period: Number of periods for SMA calculation (default 20).
                   Common values: 9, 20, 50, 100, 200.

        Raises:
            ValueError: If period < 1.
        """
        if period < 1:
            raise ValueError(f"SMA period must be >= 1, got {period}")

        self.period = period

    def calculate(self, series: OHLCVSeries) -> IndicatorResult[float]:
        """Calculate SMA values from OHLCV series.

        Uses close prices for calculation. Simple arithmetic mean over
        rolling window of 'period' bars.

        Args:
            series: OHLCV series from Session 1 market data layer.

        Returns:
            IndicatorResult with SMA values (NaN for first 'period-1' bars).

        Raises:
            ValueError: If series has insufficient data (need at least 'period' bars).

        Example:
            >>> series = OHLCVSeries(candles=[...], symbol="BTCUSDT", timeframe="1h")
            >>> sma = SMA(period=20)
            >>> result = sma.calculate(series)
            >>> result.current  # Latest SMA value
        """
        if len(series) < self.period:
            raise ValueError(
                f"SMA({self.period}) requires at least {self.period} bars, "
                f"got {len(series)}"
            )

        closes = series.closes
        sma_values: NDArray[np.float64] = np.full(len(closes), np.nan, dtype=np.float64)

        # Calculate SMA using rolling window
        # numpy.convolve is efficient for rolling sums
        weights = np.ones(self.period) / self.period
        sma_result = np.convolve(closes, weights, mode="valid")

        # Place results starting at index period-1
        sma_values[self.period - 1 :] = sma_result

        return IndicatorResult(
            name=f"SMA_{self.period}",
            values=sma_values,
            params={"period": self.period},
        )

    def __repr__(self) -> str:
        """String representation of SMA indicator.

        Returns:
            String with SMA period.
        """
        return f"SMA(period={self.period})"
