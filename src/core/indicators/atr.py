"""Average True Range (ATR) indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-002 - Wilder's smoothing for ATR

ATR measures market volatility by calculating the average of true ranges.
It's a critical dependency for SuperTrend, VWAP, and ADX indicators.

Formula:
    TR[t] = max(
        High[t] - Low[t],
        |High[t] - Close[t-1]|,
        |Low[t] - Close[t-1]|
    )
    ATR[0] = SMA(TR, period)  # Initial value
    ATR[t] = (ATR[t-1] * (period - 1) + TR[t]) / period  # Wilder's smoothing

Reference: TradingView ATR indicator
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from src.core.indicators.base import Indicator, IndicatorResult
from src.data.market_data import OHLCVSeries


class ATR(Indicator):
    """Average True Range indicator.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage
    Decision: DEC-2026-02-11-002 - Wilder's smoothing (NOT simple EMA)

    Measures volatility by averaging true ranges. Higher ATR indicates
    higher volatility. Used as a dependency for SuperTrend, VWAP, and ADX.

    Attributes:
        period: Number of periods for ATR calculation (default 14).

    Example:
        >>> from src.data.service import MarketDataService
        >>> service = MarketDataService()
        >>> series, _ = await service.get_ohlcv("BTCUSDT", "1h", limit=100)
        >>>
        >>> atr = ATR(period=14)
        >>> result = atr.calculate(series)
        >>> print(f"Current ATR: {result.current:.2f}")
        >>> print(f"Volatility: {atr.volatility_ratio(result.values, series.closes):.2f}%")
    """

    def __init__(self, period: int = 14) -> None:
        """Initialize ATR indicator.

        Args:
            period: Number of periods for ATR calculation (default 14).
                   Common values: 7, 14, 21.

        Raises:
            ValueError: If period < 1.
        """
        if period < 1:
            raise ValueError(f"ATR period must be >= 1, got {period}")

        self.period = period

    def calculate(self, series: OHLCVSeries) -> IndicatorResult[float]:
        """Calculate ATR values from OHLCV series.

        Decision: DEC-2026-02-11-002 - Wilder's smoothing for ATR

        True Range (TR) considers three scenarios:
        1. Current high - current low (normal volatility)
        2. Current high - previous close (gap up)
        3. Previous close - current low (gap down)

        ATR smooths TR using Wilder's method (α = 1/period).

        Args:
            series: OHLCV series from Session 1 market data layer.

        Returns:
            IndicatorResult with ATR values (NaN for first 'period' bars).
            TR values stored in result.params["tr_values"] for dependent indicators.

        Raises:
            ValueError: If series has insufficient data (need at least 'period+1' bars).

        Example:
            >>> series = OHLCVSeries(candles=[...], symbol="BTCUSDT", timeframe="1h")
            >>> atr = ATR(period=14)
            >>> result = atr.calculate(series)
            >>> result.current  # Latest ATR value
            >>> result.params["tr_values"]  # Access TR for SuperTrend/ADX
        """
        if len(series) < self.period + 1:
            raise ValueError(
                f"ATR({self.period}) requires at least {self.period + 1} bars, "
                f"got {len(series)}"
            )

        highs = series.highs
        lows = series.lows
        closes = series.closes

        # Calculate True Range for each bar
        tr_values: NDArray[np.float64] = np.full(len(closes), np.nan, dtype=np.float64)

        # First bar: TR = High - Low (no previous close)
        tr_values[0] = highs[0] - lows[0]

        # Subsequent bars: max of three scenarios
        for i in range(1, len(closes)):
            tr1 = highs[i] - lows[i]  # Normal range
            tr2 = abs(highs[i] - closes[i - 1])  # Gap up scenario
            tr3 = abs(lows[i] - closes[i - 1])  # Gap down scenario

            tr_values[i] = max(tr1, tr2, tr3)

        # Calculate ATR using Wilder's smoothing
        atr_values: NDArray[np.float64] = np.full(len(closes), np.nan, dtype=np.float64)

        # Initialize first ATR as SMA of first 'period' TR values
        atr_values[self.period] = np.mean(tr_values[1 : self.period + 1])

        # Apply Wilder's smoothing from period+1 onwards
        # Formula: ATR[t] = (ATR[t-1] * (period - 1) + TR[t]) / period
        for i in range(self.period + 1, len(closes)):
            atr_values[i] = (
                atr_values[i - 1] * (self.period - 1) + tr_values[i]
            ) / self.period

        return IndicatorResult(
            name=f"ATR_{self.period}",
            values=atr_values,
            params={
                "period": self.period,
                "tr_values": tr_values,  # Store TR for dependent indicators
            },
        )

    @staticmethod
    def volatility_ratio(
        atr_values: NDArray[np.float64], closes: NDArray[np.float64]
    ) -> float:
        """Calculate current ATR as percentage of current close price.

        Normalizes ATR by price to compare volatility across different assets
        or time periods. Higher percentage indicates higher relative volatility.

        Args:
            atr_values: ATR values array (from IndicatorResult.values).
            closes: Close prices array (from OHLCVSeries.closes).

        Returns:
            Volatility ratio as percentage (ATR / Close * 100).

        Raises:
            ValueError: If no valid ATR values or close price is zero.

        Example:
            >>> result = atr.calculate(series)
            >>> vol_ratio = ATR.volatility_ratio(result.values, series.closes)
            >>> if vol_ratio > 2.0:
            ...     print("High volatility (>2%)")
        """
        # Find last valid ATR value
        valid_indices = np.where(~np.isnan(atr_values))[0]
        if len(valid_indices) == 0:
            raise ValueError("No valid ATR values available")

        last_idx = valid_indices[-1]
        current_atr = atr_values[last_idx]
        current_close = closes[last_idx]

        if current_close == 0:
            raise ValueError("Close price is zero, cannot calculate volatility ratio")

        if math.isnan(current_atr):
            raise ValueError("Current ATR is NaN")

        return float((current_atr / current_close) * 100.0)

    @staticmethod
    def required_periods(period: int) -> int:
        """Return minimum bars needed before first valid ATR value.

        ATR needs period+1 bars (1 for first TR, then 'period' for first ATR).

        Args:
            period: ATR period parameter.

        Returns:
            Minimum number of bars required (period + 1).
        """
        return period + 1

    def __repr__(self) -> str:
        """String representation of ATR indicator.

        Returns:
            String with ATR period.
        """
        return f"ATR(period={self.period})"
