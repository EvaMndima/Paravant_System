"""Donchian Channels indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-001 - Compute-on-demand indicator strategy

Donchian Channels plot the highest high and lowest low over a specified period.
They're used to identify breakouts and measure trend strength.

Formula:
    Upper Channel = Highest High over last N periods
    Lower Channel = Lowest Low over last N periods
    Middle Channel = (Upper + Lower) / 2

Reference: TradingView Donchian Channels indicator
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from src.core.indicators.base import Indicator, IndicatorResult
from src.data.market_data import OHLCVSeries


class DonchianResult(IndicatorResult[float]):
    """Donchian Channels-specific result with three channels.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Extends IndicatorResult to provide direct access to all Donchian components
    and breakout detection methods.

    Attributes:
        upper: Upper channel values (highest high).
        middle: Middle channel values (average of upper/lower).
        lower: Lower channel values (lowest low).
    """

    def __init__(
        self,
        name: str,
        upper: NDArray[np.float64],
        middle: NDArray[np.float64],
        lower: NDArray[np.float64],
        params: dict[str, Any],
    ) -> None:
        """Initialize Donchian Channels result.

        Args:
            name: Indicator name (e.g., "DC_20").
            upper: Upper channel values array.
            middle: Middle channel values array.
            lower: Lower channel values array.
            params: Parameters (period).
        """
        # Store middle channel as primary values for base class
        super().__init__(name, middle, params)

        self.upper = upper
        self.middle = middle
        self.lower = lower

    def is_breakout_up(self) -> bool:
        """Check if price broke above upper channel (bullish breakout).

        Returns:
            True if most recent close > upper channel.

        Raises:
            ValueError: If insufficient valid values.

        Example:
            >>> result = dc.calculate(series)
            >>> if result.is_breakout_up():
            ...     print("Bullish breakout: price exceeded recent high")
        """
        valid_indices = np.where(~np.isnan(self.upper))[0]

        if len(valid_indices) == 0:
            raise ValueError("No valid upper channel values available")

        # Need closes to check breakout
        # Store closes in params during calculation
        if "closes" not in self.params:
            raise ValueError("Closes not stored in result params")

        closes: NDArray[np.float64] = self.params["closes"]
        last_idx = valid_indices[-1]

        return bool(closes[last_idx] > self.upper[last_idx])

    def is_breakout_down(self) -> bool:
        """Check if price broke below lower channel (bearish breakout).

        Returns:
            True if most recent close < lower channel.

        Raises:
            ValueError: If insufficient valid values.

        Example:
            >>> result = dc.calculate(series)
            >>> if result.is_breakout_down():
            ...     print("Bearish breakout: price fell below recent low")
        """
        valid_indices = np.where(~np.isnan(self.lower))[0]

        if len(valid_indices) == 0:
            raise ValueError("No valid lower channel values available")

        # Need closes to check breakout
        if "closes" not in self.params:
            raise ValueError("Closes not stored in result params")

        closes: NDArray[np.float64] = self.params["closes"]
        last_idx = valid_indices[-1]

        return bool(closes[last_idx] < self.lower[last_idx])

    def __repr__(self) -> str:
        """String representation of Donchian Channels result.

        Returns:
            String with DC name and component counts.
        """
        valid_count = np.count_nonzero(~np.isnan(self.middle))
        return f"DonchianResult(name={self.name}, values={valid_count})"


class DonchianChannel(Indicator):
    """Donchian Channels indicator.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Plots highest high and lowest low over a specified period. Breakouts
    above the upper channel or below the lower channel indicate potential
    trend changes.

    Attributes:
        period: Lookback period for highest/lowest (default 20).

    Example:
        >>> from src.data.service import MarketDataService
        >>> service = MarketDataService()
        >>> series, _ = await service.get_ohlcv("BTCUSDT", "1h", limit=100)
        >>>
        >>> dc = DonchianChannel(period=20)
        >>> result = dc.calculate(series)
        >>> print(f"Upper: {result.upper[-1]:.2f}")
        >>> print(f"Middle: {result.middle[-1]:.2f}")
        >>> print(f"Lower: {result.lower[-1]:.2f}")
        >>>
        >>> if result.is_breakout_up():
        ...     print("Bullish breakout detected")
    """

    def __init__(self, period: int = 20) -> None:
        """Initialize Donchian Channels indicator.

        Args:
            period: Lookback period for highest/lowest (default 20).
                   Common values: 10, 20, 50, 100.

        Raises:
            ValueError: If period < 1.
        """
        if period < 1:
            raise ValueError(f"Period must be >= 1, got {period}")

        self.period = period

    def calculate(self, series: OHLCVSeries) -> DonchianResult:
        """Calculate Donchian Channels from OHLCV series.

        Calculates three components:
        1. Upper Channel = Highest high over period
        2. Lower Channel = Lowest low over period
        3. Middle Channel = (Upper + Lower) / 2

        Args:
            series: OHLCV series from Session 1 market data layer.

        Returns:
            DonchianResult with all three channels (NaN for first 'period-1' bars).

        Raises:
            ValueError: If series has insufficient data.

        Example:
            >>> series = OHLCVSeries(candles=[...], symbol="BTCUSDT", timeframe="1h")
            >>> dc = DonchianChannel(period=20)
            >>> result = dc.calculate(series)
        """
        if len(series) < self.period:
            raise ValueError(
                f"Donchian({self.period}) requires at least {self.period} bars, "
                f"got {len(series)}"
            )

        highs = series.highs
        lows = series.lows
        closes = series.closes

        # Initialize arrays
        upper: NDArray[np.float64] = np.full(len(highs), np.nan, dtype=np.float64)
        lower: NDArray[np.float64] = np.full(len(lows), np.nan, dtype=np.float64)

        # Calculate rolling highest high and lowest low
        for i in range(self.period - 1, len(highs)):
            window_start = i - self.period + 1
            window_end = i + 1

            upper[i] = np.max(highs[window_start:window_end])
            lower[i] = np.min(lows[window_start:window_end])

        # Calculate middle channel (average of upper and lower)
        middle = (upper + lower) / 2.0

        return DonchianResult(
            name=f"DC_{self.period}",
            upper=upper,
            middle=middle,
            lower=lower,
            params={
                "period": self.period,
                "closes": closes,  # Store for breakout detection
            },
        )

    def __repr__(self) -> str:
        """String representation of Donchian Channels indicator.

        Returns:
            String with period.
        """
        return f"DonchianChannel(period={self.period})"
