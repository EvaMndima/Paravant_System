"""Relative Strength Index (RSI) indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-002 - Wilder's smoothing for RSI (CRITICAL)

RSI is a momentum oscillator that measures the speed and magnitude of price changes.
Values range from 0 to 100, with >70 indicating overbought and <30 indicating oversold.

⚠️ CRITICAL: RSI uses Wilder's smoothing (α = 1/period), NOT simple EMA (α = 2/(period+1)).
Using the wrong smoothing method produces incorrect RSI values.

Formula (Wilder's Smoothing):
    UpMove[t] = max(Close[t] - Close[t-1], 0)
    DnMove[t] = max(Close[t-1] - Close[t], 0)

    AvgUp[0] = SMA(UpMove[0:period])  # Initial value
    AvgDn[0] = SMA(DnMove[0:period])

    AvgUp[t] = (AvgUp[t-1] * (period - 1) + UpMove[t]) / period  # Wilder's smoothing
    AvgDn[t] = (AvgDn[t-1] * (period - 1) + DnMove[t]) / period

    RS = AvgUp / AvgDn
    RSI = 100 - (100 / (1 + RS))

Reference: TradingView RSI indicator, Wilder (1978)
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from src.core.indicators.base import Indicator, IndicatorResult
from src.data.market_data import OHLCVSeries


class RSI(Indicator):
    """Relative Strength Index indicator.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage
    Decision: DEC-2026-02-11-002 - Wilder's smoothing (NOT simple EMA)

    ⚠️ CRITICAL: This implementation uses Wilder's smoothing method.
    Do NOT change to simple EMA - it will produce incorrect values.

    Momentum oscillator measuring price change magnitude and speed.
    Values are bounded [0, 100]:
    - RSI > 70: Overbought (potential reversal down)
    - RSI < 30: Oversold (potential reversal up)
    - RSI ~ 50: Neutral momentum

    Attributes:
        period: Number of periods for RSI calculation (default 14).

    Example:
        >>> from src.data.service import MarketDataService
        >>> service = MarketDataService()
        >>> series, _ = await service.get_ohlcv("BTCUSDT", "1h", limit=100)
        >>>
        >>> rsi = RSI(period=14)
        >>> result = rsi.calculate(series)
        >>> print(f"Current RSI: {result.current:.2f}")
        >>>
        >>> if RSI.is_overbought(result.values):
        ...     print("Overbought: RSI > 70")
        >>> elif RSI.is_oversold(result.values):
        ...     print("Oversold: RSI < 30")
    """

    def __init__(self, period: int = 14) -> None:
        """Initialize RSI indicator.

        Args:
            period: Number of periods for RSI calculation (default 14).
                   Common values: 9, 14, 21, 25.

        Raises:
            ValueError: If period < 1.
        """
        if period < 1:
            raise ValueError(f"RSI period must be >= 1, got {period}")

        self.period = period

    def calculate(self, series: OHLCVSeries) -> IndicatorResult[float]:
        """Calculate RSI values from OHLCV series.

        Decision: DEC-2026-02-11-002 - Wilder's smoothing (CRITICAL)

        ⚠️ CRITICAL IMPLEMENTATION NOTE:
        This uses Wilder's smoothing: AvgUp[t] = (AvgUp[t-1] * (period-1) + UpMove[t]) / period
        This is equivalent to EMA with α = 1/period (NOT α = 2/(period+1)).

        Simple EMA would be: AvgUp[t] = α * UpMove[t] + (1 - α) * AvgUp[t-1] where α = 2/(period+1)
        Using simple EMA produces INCORRECT RSI values.

        Args:
            series: OHLCV series from Session 1 market data layer.

        Returns:
            IndicatorResult with RSI values (NaN for first 'period' bars).
            Values are bounded [0, 100].

        Raises:
            ValueError: If series has insufficient data (need at least 'period+1' bars).

        Example:
            >>> series = OHLCVSeries(candles=[...], symbol="BTCUSDT", timeframe="1h")
            >>> rsi = RSI(period=14)
            >>> result = rsi.calculate(series)
            >>> result.current  # Latest RSI value (0-100)
        """
        if len(series) < self.period + 1:
            raise ValueError(
                f"RSI({self.period}) requires at least {self.period + 1} bars, "
                f"got {len(series)}"
            )

        closes = series.closes
        rsi_values: NDArray[np.float64] = np.full(len(closes), np.nan, dtype=np.float64)

        # Calculate price changes
        deltas = np.diff(closes)

        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        # Initialize first average gain/loss as SMA of first 'period' values
        avg_gain = np.mean(gains[: self.period])
        avg_loss = np.mean(losses[: self.period])

        # Calculate first RSI value
        if avg_gain == 0 and avg_loss == 0:
            # No price movement - RSI is neutral (50)
            rsi_values[self.period] = 50.0
        elif avg_loss == 0:
            # All gains, no losses - RSI = 100
            rsi_values[self.period] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_values[self.period] = 100.0 - (100.0 / (1.0 + rs))

        # Apply Wilder's smoothing from period+1 onwards
        # CRITICAL: This is Wilder's smoothing (α = 1/period), NOT simple EMA (α = 2/(period+1))
        # Formula: AvgGain[t] = (AvgGain[t-1] * (period - 1) + Gain[t]) / period
        for i in range(self.period, len(deltas)):
            avg_gain = (avg_gain * (self.period - 1) + gains[i]) / self.period
            avg_loss = (avg_loss * (self.period - 1) + losses[i]) / self.period

            if avg_gain == 0 and avg_loss == 0:
                # No price movement - RSI is neutral (50)
                rsi_values[i + 1] = 50.0
            elif avg_loss == 0:
                # All gains, no losses - RSI = 100
                rsi_values[i + 1] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_values[i + 1] = 100.0 - (100.0 / (1.0 + rs))

        return IndicatorResult(
            name=f"RSI_{self.period}",
            values=rsi_values,
            params={
                "period": self.period,
                "smoothing": "wilder",  # Explicitly document smoothing method
            },
        )

    @staticmethod
    def is_oversold(values: NDArray[np.float64], threshold: float = 30.0) -> bool:
        """Check if current RSI indicates oversold condition.

        Args:
            values: RSI values array (from IndicatorResult.values).
            threshold: Oversold threshold (default 30.0).
                      Common values: 20, 25, 30.

        Returns:
            True if current RSI < threshold (oversold).

        Raises:
            ValueError: If no valid RSI values or threshold out of range.

        Example:
            >>> result = rsi.calculate(series)
            >>> if RSI.is_oversold(result.values, threshold=30):
            ...     print("Oversold: potential bounce expected")
        """
        if not 0 <= threshold <= 100:
            raise ValueError(
                f"Threshold must be in range [0, 100], got {threshold}"
            )

        # Find last valid RSI value
        valid_indices = np.where(~np.isnan(values))[0]
        if len(valid_indices) == 0:
            raise ValueError("No valid RSI values available")

        current_rsi = values[valid_indices[-1]]
        return bool(current_rsi < threshold)

    @staticmethod
    def is_overbought(values: NDArray[np.float64], threshold: float = 70.0) -> bool:
        """Check if current RSI indicates overbought condition.

        Args:
            values: RSI values array (from IndicatorResult.values).
            threshold: Overbought threshold (default 70.0).
                      Common values: 70, 75, 80.

        Returns:
            True if current RSI > threshold (overbought).

        Raises:
            ValueError: If no valid RSI values or threshold out of range.

        Example:
            >>> result = rsi.calculate(series)
            >>> if RSI.is_overbought(result.values, threshold=70):
            ...     print("Overbought: potential pullback expected")
        """
        if not 0 <= threshold <= 100:
            raise ValueError(
                f"Threshold must be in range [0, 100], got {threshold}"
            )

        # Find last valid RSI value
        valid_indices = np.where(~np.isnan(values))[0]
        if len(valid_indices) == 0:
            raise ValueError("No valid RSI values available")

        current_rsi = values[valid_indices[-1]]
        return bool(current_rsi > threshold)

    @staticmethod
    def required_periods(period: int) -> int:
        """Return minimum bars needed before first valid RSI value.

        RSI needs period+1 bars (1 for first delta, then 'period' for first average).

        Args:
            period: RSI period parameter.

        Returns:
            Minimum number of bars required (period + 1).
        """
        return period + 1

    def __repr__(self) -> str:
        """String representation of RSI indicator.

        Returns:
            String with RSI period and smoothing method.
        """
        return f"RSI(period={self.period}, smoothing='wilder')"
