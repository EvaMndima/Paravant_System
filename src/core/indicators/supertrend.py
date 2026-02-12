"""SuperTrend indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-001 - Compute-on-demand indicator strategy

SuperTrend is a trend-following indicator that uses ATR to create dynamic
support and resistance bands. It switches between bullish and bearish modes
based on price crossing the bands.

Formula:
    HL2 = (High + Low) / 2
    UpperBand = HL2 + (Multiplier * ATR)
    LowerBand = HL2 - (Multiplier * ATR)

    If Close > UpperBand[prev]: Trend = 1 (bullish)
    If Close < LowerBand[prev]: Trend = -1 (bearish)

    SuperTrend = UpperBand if Trend == -1 else LowerBand

Reference: TradingView SuperTrend indicator
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from src.core.indicators.atr import ATR
from src.core.indicators.base import Indicator, IndicatorResult
from src.data.market_data import OHLCVSeries


class SuperTrendResult(IndicatorResult[float]):
    """SuperTrend-specific result with trend tracking.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Extends IndicatorResult to provide direct access to SuperTrend components
    and trend flip detection methods.

    Attributes:
        supertrend: SuperTrend values (dynamic support/resistance).
        trend: Trend direction values (+1 bullish, -1 bearish).
        upper_band: Upper band values.
        lower_band: Lower band values.
    """

    def __init__(
        self,
        name: str,
        supertrend: NDArray[np.float64],
        trend: NDArray[np.int8],
        upper_band: NDArray[np.float64],
        lower_band: NDArray[np.float64],
        params: dict[str, Any],
    ) -> None:
        """Initialize SuperTrend result.

        Args:
            name: Indicator name (e.g., "ST_10_3.0").
            supertrend: SuperTrend values array.
            trend: Trend direction array (+1/-1).
            upper_band: Upper band values array.
            lower_band: Lower band values array.
            params: Parameters (period, multiplier).
        """
        # Store supertrend as primary values for base class
        super().__init__(name, supertrend, params)

        self.supertrend = supertrend
        self.trend = trend
        self.upper_band = upper_band
        self.lower_band = lower_band

    def just_flipped_bullish(self) -> bool:
        """Check if trend just flipped from bearish to bullish.

        Returns:
            True if trend changed from -1 to +1 in the last bar.

        Raises:
            ValueError: If insufficient valid trend values.

        Example:
            >>> result = st.calculate(series)
            >>> if result.just_flipped_bullish():
            ...     print("Bullish trend flip: potential buy signal")
        """
        valid_indices = np.where(self.trend != 0)[0]

        if len(valid_indices) < 2:
            raise ValueError("Insufficient valid trend values for flip detection")

        curr_idx = valid_indices[-1]
        prev_idx = valid_indices[-2]

        was_bearish = self.trend[prev_idx] == -1
        is_bullish = self.trend[curr_idx] == 1

        return bool(was_bearish and is_bullish)

    def just_flipped_bearish(self) -> bool:
        """Check if trend just flipped from bullish to bearish.

        Returns:
            True if trend changed from +1 to -1 in the last bar.

        Raises:
            ValueError: If insufficient valid trend values.

        Example:
            >>> result = st.calculate(series)
            >>> if result.just_flipped_bearish():
            ...     print("Bearish trend flip: potential sell signal")
        """
        valid_indices = np.where(self.trend != 0)[0]

        if len(valid_indices) < 2:
            raise ValueError("Insufficient valid trend values for flip detection")

        curr_idx = valid_indices[-1]
        prev_idx = valid_indices[-2]

        was_bullish = self.trend[prev_idx] == 1
        is_bearish = self.trend[curr_idx] == -1

        return bool(was_bullish and is_bearish)

    @property
    def current_trend(self) -> int:
        """Get current trend direction.

        Returns:
            Current trend: +1 (bullish), -1 (bearish), or 0 (no trend yet).

        Example:
            >>> result = st.calculate(series)
            >>> if result.current_trend == 1:
            ...     print("Currently in bullish trend")
        """
        valid_indices = np.where(self.trend != 0)[0]

        if len(valid_indices) == 0:
            return 0

        return int(self.trend[valid_indices[-1]])

    def __repr__(self) -> str:
        """String representation of SuperTrend result.

        Returns:
            String with ST name and current trend.
        """
        valid_count = np.count_nonzero(~np.isnan(self.supertrend))
        return (
            f"SuperTrendResult(name={self.name}, values={valid_count}, "
            f"trend={self.current_trend})"
        )


class SuperTrend(Indicator):
    """SuperTrend indicator.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Trend-following indicator using ATR-based dynamic support/resistance bands.
    Switches between bullish and bearish modes based on price crossing bands.

    Attributes:
        period: ATR period for volatility calculation (default 10).
        multiplier: ATR multiplier for band width (default 3.0).

    Example:
        >>> from src.data.service import MarketDataService
        >>> service = MarketDataService()
        >>> series, _ = await service.get_ohlcv("BTCUSDT", "1h", limit=100)
        >>>
        >>> st = SuperTrend(period=10, multiplier=3.0)
        >>> result = st.calculate(series)
        >>> print(f"SuperTrend: {result.current:.2f}")
        >>> print(f"Trend: {'Bullish' if result.current_trend == 1 else 'Bearish'}")
        >>>
        >>> if result.just_flipped_bullish():
        ...     print("Trend flip: Buy signal")
    """

    def __init__(self, period: int = 10, multiplier: float = 3.0) -> None:
        """Initialize SuperTrend indicator.

        Args:
            period: ATR period for volatility (default 10).
            multiplier: ATR multiplier for bands (default 3.0).
                       Common values: 2.0, 3.0, 4.0.

        Raises:
            ValueError: If period < 1 or multiplier <= 0.
        """
        if period < 1:
            raise ValueError(f"Period must be >= 1, got {period}")
        if multiplier <= 0:
            raise ValueError(f"Multiplier must be > 0, got {multiplier}")

        self.period = period
        self.multiplier = multiplier
        self.atr = ATR(period=period)

    def calculate(self, series: OHLCVSeries) -> SuperTrendResult:
        """Calculate SuperTrend from OHLCV series.

        Uses ATR to create dynamic bands around HL2 (average of high/low).
        Trend flips when price crosses the opposite band.

        Args:
            series: OHLCV series from Session 1 market data layer.

        Returns:
            SuperTrendResult with supertrend, trend, and bands (NaN during warmup).

        Raises:
            ValueError: If series has insufficient data.

        Example:
            >>> series = OHLCVSeries(candles=[...], symbol="BTCUSDT", timeframe="1h")
            >>> st = SuperTrend(period=10, multiplier=3.0)
            >>> result = st.calculate(series)
        """
        min_bars = self.period + 1
        if len(series) < min_bars:
            raise ValueError(
                f"SuperTrend({self.period},{self.multiplier}) requires at least "
                f"{min_bars} bars, got {len(series)}"
            )

        # Calculate ATR
        atr_result = self.atr.calculate(series)
        atr_values = atr_result.values

        # Get price data
        highs = series.highs
        lows = series.lows
        closes = series.closes

        # Calculate HL2 (average of high and low)
        hl2 = (highs + lows) / 2.0

        # Calculate basic bands
        basic_upper = hl2 + (self.multiplier * atr_values)
        basic_lower = hl2 - (self.multiplier * atr_values)

        # Initialize arrays
        n = len(closes)
        upper_band: NDArray[np.float64] = np.full(n, np.nan, dtype=np.float64)
        lower_band: NDArray[np.float64] = np.full(n, np.nan, dtype=np.float64)
        supertrend: NDArray[np.float64] = np.full(n, np.nan, dtype=np.float64)
        trend: NDArray[np.int8] = np.zeros(n, dtype=np.int8)

        # Find first valid ATR index
        first_valid = self.period  # ATR becomes valid at index period

        # Initialize first bands
        upper_band[first_valid] = basic_upper[first_valid]
        lower_band[first_valid] = basic_lower[first_valid]

        # Initialize first trend (assume bullish if close > HL2)
        if closes[first_valid] > hl2[first_valid]:
            trend[first_valid] = 1
            supertrend[first_valid] = lower_band[first_valid]
        else:
            trend[first_valid] = -1
            supertrend[first_valid] = upper_band[first_valid]

        # Calculate SuperTrend for remaining bars
        for i in range(first_valid + 1, n):
            # Update upper band (can only move up or stay same during uptrend)
            if basic_upper[i] < upper_band[i - 1] or closes[i - 1] > upper_band[i - 1]:
                upper_band[i] = basic_upper[i]
            else:
                upper_band[i] = upper_band[i - 1]

            # Update lower band (can only move down or stay same during downtrend)
            if basic_lower[i] > lower_band[i - 1] or closes[i - 1] < lower_band[i - 1]:
                lower_band[i] = basic_lower[i]
            else:
                lower_band[i] = lower_band[i - 1]

            # Determine trend
            if trend[i - 1] == 1:
                # Was bullish - check if price broke below lower band
                if closes[i] <= lower_band[i]:
                    trend[i] = -1  # Flip to bearish
                    supertrend[i] = upper_band[i]
                else:
                    trend[i] = 1  # Stay bullish
                    supertrend[i] = lower_band[i]
            else:
                # Was bearish - check if price broke above upper band
                if closes[i] >= upper_band[i]:
                    trend[i] = 1  # Flip to bullish
                    supertrend[i] = lower_band[i]
                else:
                    trend[i] = -1  # Stay bearish
                    supertrend[i] = upper_band[i]

        return SuperTrendResult(
            name=f"ST_{self.period}_{self.multiplier}",
            supertrend=supertrend,
            trend=trend,
            upper_band=upper_band,
            lower_band=lower_band,
            params={"period": self.period, "multiplier": self.multiplier},
        )

    @staticmethod
    def required_periods(period: int) -> int:
        """Return minimum bars needed before first valid SuperTrend value.

        Args:
            period: ATR period parameter.

        Returns:
            Minimum number of bars required (period + 1).
        """
        return period + 1

    def __repr__(self) -> str:
        """String representation of SuperTrend indicator.

        Returns:
            String with period and multiplier.
        """
        return f"SuperTrend(period={self.period}, multiplier={self.multiplier})"
