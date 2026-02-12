"""Average Directional Index (ADX) indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-002 - Wilder's smoothing for ADX components

ADX measures trend strength (not direction). It's derived from the directional
movement system (+DI/-DI) and uses Wilder's smoothing throughout.

Formula (Complex - 6 steps):
    1. +DM = max(High[t] - High[t-1], 0) if positive
       -DM = max(Low[t-1] - Low[t], 0) if positive
       (both 0 if high-low change is greater)

    2. Smooth +DM and -DM using Wilder's method
       Smoothed+DM[t] = (Smoothed+DM[t-1] * (period-1) + +DM[t]) / period

    3. Calculate +DI and -DI
       +DI = 100 * Smoothed+DM / ATR
       -DI = 100 * Smoothed-DM / ATR

    4. Calculate DX
       DX = 100 * |+DI - -DI| / (+DI + -DI)

    5. Calculate ADX (Wilder's smooth of DX)
       ADX[0] = average of first 'period' DX values
       ADX[t] = (ADX[t-1] * (period-1) + DX[t]) / period

Reference: TradingView ADX indicator, Wilder (1978)
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from src.core.indicators.atr import ATR
from src.core.indicators.base import Indicator, IndicatorResult
from src.data.market_data import OHLCVSeries


class ADXResult(IndicatorResult[float]):
    """ADX-specific result with directional indicators.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Extends IndicatorResult to provide direct access to ADX and DI components.

    Attributes:
        adx: ADX values (trend strength, 0-100).
        plus_di: +DI values (bullish directional indicator).
        minus_di: -DI values (bearish directional indicator).
    """

    def __init__(
        self,
        name: str,
        adx: NDArray[np.float64],
        plus_di: NDArray[np.float64],
        minus_di: NDArray[np.float64],
        params: dict[str, Any],
    ) -> None:
        """Initialize ADX result.

        Args:
            name: Indicator name (e.g., "ADX_14").
            adx: ADX values array.
            plus_di: +DI values array.
            minus_di: -DI values array.
            params: Parameters (period).
        """
        # Store ADX as primary values for base class
        super().__init__(name, adx, params)

        self.adx = adx
        self.plus_di = plus_di
        self.minus_di = minus_di

    def is_trending(self, threshold: float = 25.0) -> bool:
        """Check if ADX indicates a trending market.

        Args:
            threshold: ADX threshold for trend (default 25.0).
                      Common values: 20, 25, 30.

        Returns:
            True if current ADX > threshold (trending).

        Raises:
            ValueError: If no valid ADX values.

        Example:
            >>> result = adx.calculate(series)
            >>> if result.is_trending(threshold=25):
            ...     print("Strong trend detected")
        """
        valid_indices = np.where(~np.isnan(self.adx))[0]

        if len(valid_indices) == 0:
            raise ValueError("No valid ADX values available")

        current_adx = self.adx[valid_indices[-1]]
        return bool(current_adx > threshold)

    def is_ranging(self, threshold: float = 20.0) -> bool:
        """Check if ADX indicates a ranging market.

        Args:
            threshold: ADX threshold for range (default 20.0).
                      Common values: 15, 20, 25.

        Returns:
            True if current ADX < threshold (ranging).

        Raises:
            ValueError: If no valid ADX values.

        Example:
            >>> result = adx.calculate(series)
            >>> if result.is_ranging(threshold=20):
            ...     print("Ranging market detected")
        """
        valid_indices = np.where(~np.isnan(self.adx))[0]

        if len(valid_indices) == 0:
            raise ValueError("No valid ADX values available")

        current_adx = self.adx[valid_indices[-1]]
        return bool(current_adx < threshold)

    @property
    def trend_direction(self) -> int:
        """Get trend direction based on +DI/-DI comparison.

        Returns:
            +1 if +DI > -DI (bullish), -1 if +DI < -DI (bearish), 0 if equal.

        Example:
            >>> result = adx.calculate(series)
            >>> if result.is_trending() and result.trend_direction == 1:
            ...     print("Strong bullish trend")
        """
        valid_plus = np.where(~np.isnan(self.plus_di))[0]
        valid_minus = np.where(~np.isnan(self.minus_di))[0]

        if len(valid_plus) == 0 or len(valid_minus) == 0:
            return 0

        last_idx = min(valid_plus[-1], valid_minus[-1])

        plus_val = self.plus_di[last_idx]
        minus_val = self.minus_di[last_idx]

        if plus_val > minus_val:
            return 1
        elif plus_val < minus_val:
            return -1
        else:
            return 0

    def __repr__(self) -> str:
        """String representation of ADX result.

        Returns:
            String with ADX name, value count, and trend direction.
        """
        valid_count = np.count_nonzero(~np.isnan(self.adx))
        return (
            f"ADXResult(name={self.name}, values={valid_count}, "
            f"direction={self.trend_direction})"
        )


class ADX(Indicator):
    """Average Directional Index indicator.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage
    Decision: DEC-2026-02-11-002 - Wilder's smoothing for all ADX components

    Measures trend strength (not direction). Higher ADX indicates stronger trend.
    Uses directional movement system (+DI/-DI) with Wilder's smoothing.

    ADX ranges 0-100:
    - ADX > 25: Strong trend
    - ADX 20-25: Moderate trend
    - ADX < 20: Weak trend or ranging

    Attributes:
        period: Period for all smoothing operations (default 14).

    Example:
        >>> from src.data.service import MarketDataService
        >>> service = MarketDataService()
        >>> series, _ = await service.get_ohlcv("BTCUSDT", "1h", limit=100)
        >>>
        >>> adx = ADX(period=14)
        >>> result = adx.calculate(series)
        >>> print(f"ADX: {result.current:.2f}")
        >>> print(f"+DI: {result.plus_di[-1]:.2f}")
        >>> print(f"-DI: {result.minus_di[-1]:.2f}")
        >>>
        >>> if result.is_trending() and result.trend_direction == 1:
        ...     print("Strong bullish trend")
    """

    def __init__(self, period: int = 14) -> None:
        """Initialize ADX indicator.

        Args:
            period: Period for smoothing (default 14).
                   Common values: 7, 14, 21.

        Raises:
            ValueError: If period < 1.
        """
        if period < 1:
            raise ValueError(f"Period must be >= 1, got {period}")

        self.period = period
        self.atr = ATR(period=period)

    def calculate(self, series: OHLCVSeries) -> ADXResult:
        """Calculate ADX from OHLCV series.

        Decision: DEC-2026-02-11-002 - Wilder's smoothing throughout

        Complex calculation with 6 steps:
        1. Calculate +DM and -DM (directional movements)
        2. Smooth +DM and -DM with Wilder's method
        3. Calculate +DI and -DI using ATR
        4. Calculate DX from +DI and -DI
        5. Smooth DX with Wilder's method to get ADX
        6. Return ADX with +DI and -DI

        Args:
            series: OHLCV series from Session 1 market data layer.

        Returns:
            ADXResult with ADX, +DI, -DI (NaN for first ~2*period bars).

        Raises:
            ValueError: If series has insufficient data.

        Example:
            >>> series = OHLCVSeries(candles=[...], symbol="BTCUSDT", timeframe="1h")
            >>> adx = ADX(period=14)
            >>> result = adx.calculate(series)
        """
        min_bars = 2 * self.period + 1
        if len(series) < min_bars:
            raise ValueError(
                f"ADX({self.period}) requires at least {min_bars} bars, "
                f"got {len(series)}"
            )

        highs = series.highs
        lows = series.lows
        n = len(highs)

        # Step 1: Calculate +DM and -DM
        plus_dm: NDArray[np.float64] = np.zeros(n, dtype=np.float64)
        minus_dm: NDArray[np.float64] = np.zeros(n, dtype=np.float64)

        for i in range(1, n):
            high_diff = highs[i] - highs[i - 1]
            low_diff = lows[i - 1] - lows[i]

            # +DM when high move > low move and positive
            if high_diff > low_diff and high_diff > 0:
                plus_dm[i] = high_diff

            # -DM when low move > high move and positive
            if low_diff > high_diff and low_diff > 0:
                minus_dm[i] = low_diff

        # Step 2: Smooth +DM and -DM using Wilder's method
        smoothed_plus_dm: NDArray[np.float64] = np.full(n, np.nan, dtype=np.float64)
        smoothed_minus_dm: NDArray[np.float64] = np.full(n, np.nan, dtype=np.float64)

        # Initialize with sum of first 'period' values
        smoothed_plus_dm[self.period] = np.sum(plus_dm[1 : self.period + 1])
        smoothed_minus_dm[self.period] = np.sum(minus_dm[1 : self.period + 1])

        # Apply Wilder's smoothing
        for i in range(self.period + 1, n):
            smoothed_plus_dm[i] = (
                smoothed_plus_dm[i - 1] * (self.period - 1) + plus_dm[i]
            ) / self.period
            smoothed_minus_dm[i] = (
                smoothed_minus_dm[i - 1] * (self.period - 1) + minus_dm[i]
            ) / self.period

        # Step 3: Calculate +DI and -DI using ATR
        atr_result = self.atr.calculate(series)
        atr_values = atr_result.values

        plus_di: NDArray[np.float64] = np.full(n, np.nan, dtype=np.float64)
        minus_di: NDArray[np.float64] = np.full(n, np.nan, dtype=np.float64)

        # Calculate DI values where ATR is valid
        valid_atr = ~np.isnan(atr_values) & (atr_values != 0)
        plus_di[valid_atr] = 100 * smoothed_plus_dm[valid_atr] / atr_values[valid_atr]
        minus_di[valid_atr] = 100 * smoothed_minus_dm[valid_atr] / atr_values[valid_atr]

        # Step 4: Calculate DX
        dx: NDArray[np.float64] = np.full(n, np.nan, dtype=np.float64)

        di_sum = plus_di + minus_di
        valid_di = ~np.isnan(plus_di) & ~np.isnan(minus_di) & (di_sum != 0)
        dx[valid_di] = 100 * np.abs(plus_di[valid_di] - minus_di[valid_di]) / di_sum[valid_di]

        # Step 5: Calculate ADX (Wilder's smooth of DX)
        adx: NDArray[np.float64] = np.full(n, np.nan, dtype=np.float64)

        # Find first valid DX index (should be around period + period)
        first_dx_idx = self.period + self.period

        if first_dx_idx < n:
            # Initialize first ADX as average of first 'period' DX values
            valid_dx_start = first_dx_idx - self.period + 1
            if valid_dx_start >= 0 and valid_dx_start + self.period <= n:
                first_dx_values = dx[valid_dx_start : valid_dx_start + self.period]
                if not np.all(np.isnan(first_dx_values)):
                    adx[first_dx_idx] = np.nanmean(first_dx_values)

                    # Apply Wilder's smoothing to ADX
                    for i in range(first_dx_idx + 1, n):
                        if not np.isnan(dx[i]) and not np.isnan(adx[i - 1]):
                            adx[i] = (adx[i - 1] * (self.period - 1) + dx[i]) / self.period

        return ADXResult(
            name=f"ADX_{self.period}",
            adx=adx,
            plus_di=plus_di,
            minus_di=minus_di,
            params={"period": self.period},
        )

    @staticmethod
    def required_periods(period: int) -> int:
        """Return minimum bars needed before first valid ADX value.

        ADX requires approximately 2*period bars due to double smoothing.

        Args:
            period: ADX period parameter.

        Returns:
            Minimum number of bars required (2 * period + 1).
        """
        return 2 * period + 1

    def __repr__(self) -> str:
        """String representation of ADX indicator.

        Returns:
            String with period.
        """
        return f"ADX(period={self.period})"
