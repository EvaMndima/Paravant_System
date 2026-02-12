"""Exponential Moving Average (EMA) indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-001 - Compute-on-demand indicator strategy

EMA applies exponential smoothing to price data, giving more weight to recent
prices. It's more responsive to price changes than SMA and is used as a
foundation for MACD, VWAP, and other indicators.

Formula:
    α = 2 / (period + 1)
    EMA[0] = SMA(prices[0:period])  # Initial value
    EMA[t] = α * Price[t] + (1 - α) * EMA[t-1]

Reference: TradingView EMA indicator
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from src.core.indicators.base import Indicator, IndicatorResult
from src.data.market_data import OHLCVSeries


class EMA(Indicator):
    """Exponential Moving Average indicator.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Applies exponential smoothing to close prices, giving more weight to
    recent data. More responsive than SMA.

    Attributes:
        period: Number of periods for EMA calculation (default 20).

    Example:
        >>> from src.data.service import MarketDataService
        >>> service = MarketDataService()
        >>> series, _ = await service.get_ohlcv("BTCUSDT", "1h", limit=100)
        >>>
        >>> ema = EMA(period=20)
        >>> result = ema.calculate(series)
        >>> print(f"Current EMA: {result.current}")
        >>> print(f"Trend: {ema.slope(result.values, lookback=5):.2f}% per bar")
    """

    def __init__(self, period: int = 20) -> None:
        """Initialize EMA indicator.

        Args:
            period: Number of periods for EMA calculation (default 20).
                   Common values: 9, 12, 20, 26, 50, 200.

        Raises:
            ValueError: If period < 1.
        """
        if period < 1:
            raise ValueError(f"EMA period must be >= 1, got {period}")

        self.period = period
        self.alpha = 2.0 / (period + 1)

    def calculate(self, series: OHLCVSeries) -> IndicatorResult[float]:
        """Calculate EMA values from OHLCV series.

        Uses close prices for calculation. First value is SMA of first 'period'
        bars for stable initialization, then applies exponential smoothing.

        Args:
            series: OHLCV series from Session 1 market data layer.

        Returns:
            IndicatorResult with EMA values (NaN for first 'period-1' bars).

        Raises:
            ValueError: If series has insufficient data (need at least 'period' bars).

        Example:
            >>> series = OHLCVSeries(candles=[...], symbol="BTCUSDT", timeframe="1h")
            >>> ema = EMA(period=20)
            >>> result = ema.calculate(series)
            >>> result.current  # Latest EMA value
        """
        if len(series) < self.period:
            raise ValueError(
                f"EMA({self.period}) requires at least {self.period} bars, "
                f"got {len(series)}"
            )

        closes = series.closes
        ema_values: NDArray[np.float64] = np.full(len(closes), np.nan, dtype=np.float64)

        # Initialize first EMA value as SMA of first 'period' bars
        ema_values[self.period - 1] = np.mean(closes[: self.period])

        # Apply exponential smoothing from period onwards
        for i in range(self.period, len(closes)):
            ema_values[i] = (
                self.alpha * closes[i] + (1 - self.alpha) * ema_values[i - 1]
            )

        return IndicatorResult(
            name=f"EMA_{self.period}",
            values=ema_values,
            params={"period": self.period, "alpha": self.alpha},
        )

    @staticmethod
    def slope(values: NDArray[np.float64], lookback: int = 5) -> float:
        """Calculate EMA slope over lookback period (% change per bar).

        Useful for detecting trend strength and direction. Positive slope
        indicates uptrend, negative indicates downtrend.

        Args:
            values: EMA values array (from IndicatorResult.values).
            lookback: Number of periods to calculate slope over (default 5).

        Returns:
            Slope as percentage change per bar.
            Example: 0.15 means EMA increasing by 0.15% per bar.

        Raises:
            ValueError: If lookback < 2, insufficient data, NaN in range,
                       or start value is zero.

        Example:
            >>> result = ema.calculate(series)
            >>> trend = ema.slope(result.values, lookback=5)
            >>> if trend > 0.1:
            ...     print("Strong uptrend")
            ... elif trend < -0.1:
            ...     print("Strong downtrend")
        """
        if lookback < 2:
            raise ValueError(f"Lookback must be >= 2, got {lookback}")

        # Find last non-NaN value
        valid_indices = np.where(~np.isnan(values))[0]
        if len(valid_indices) < lookback:
            raise ValueError(
                f"Need at least {lookback} valid values for slope, "
                f"got {len(valid_indices)}"
            )

        # Get last 'lookback' valid values
        last_valid_idx = valid_indices[-1]
        start_idx = max(0, last_valid_idx - lookback + 1)

        # Calculate percentage change per bar
        start_value = values[start_idx]
        end_value = values[last_valid_idx]

        if np.isnan(start_value) or np.isnan(end_value):
            raise ValueError("Cannot calculate slope: NaN values in range")

        if start_value == 0:
            raise ValueError("Cannot calculate slope: start value is zero")

        pct_change = ((end_value - start_value) / start_value) * 100
        slope_per_bar = pct_change / lookback

        return float(slope_per_bar)

    def __repr__(self) -> str:
        """String representation of EMA indicator.

        Returns:
            String with EMA period and alpha.
        """
        return f"EMA(period={self.period}, alpha={self.alpha:.4f})"
