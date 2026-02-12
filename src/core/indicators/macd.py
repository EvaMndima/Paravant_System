"""Moving Average Convergence Divergence (MACD) indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-001 - Compute-on-demand indicator strategy

MACD is a trend-following momentum indicator that shows the relationship
between two moving averages. It consists of three components:
- MACD Line: Fast EMA - Slow EMA
- Signal Line: EMA of MACD Line
- Histogram: MACD Line - Signal Line

Formula:
    MACD = EMA(close, fast_period) - EMA(close, slow_period)
    Signal = EMA(MACD, signal_period)
    Histogram = MACD - Signal

Reference: TradingView MACD indicator
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from src.core.indicators.base import Indicator, IndicatorResult
from src.core.indicators.ema import EMA
from src.data.market_data import OHLCVSeries


class MACDResult(IndicatorResult[float]):
    """MACD-specific result with three components.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Extends IndicatorResult to provide direct access to MACD components
    and crossover/slope detection methods.

    Attributes:
        macd_line: MACD values (fast EMA - slow EMA).
        signal_line: Signal line values (EMA of MACD).
        histogram: Histogram values (MACD - Signal).
    """

    def __init__(
        self,
        name: str,
        macd_line: NDArray[np.float64],
        signal_line: NDArray[np.float64],
        histogram: NDArray[np.float64],
        params: dict[str, Any],
    ) -> None:
        """Initialize MACD result.

        Args:
            name: Indicator name (e.g., "MACD_12_26_9").
            macd_line: MACD values array.
            signal_line: Signal line values array.
            histogram: Histogram values array.
            params: Parameters (fast, slow, signal periods).
        """
        # Store MACD line as primary values for base class
        super().__init__(name, macd_line, params)

        self.macd_line = macd_line
        self.signal_line = signal_line
        self.histogram = histogram

    def is_bullish_crossover(self) -> bool:
        """Check if MACD just crossed above signal line (bullish signal).

        Returns:
            True if MACD crossed above signal in the last bar.

        Raises:
            ValueError: If insufficient valid values for crossover detection.

        Example:
            >>> result = macd.calculate(series)
            >>> if result.is_bullish_crossover():
            ...     print("Bullish crossover: potential buy signal")
        """
        # Find last two valid indices for both MACD and signal
        valid_macd = np.where(~np.isnan(self.macd_line))[0]
        valid_signal = np.where(~np.isnan(self.signal_line))[0]

        if len(valid_macd) < 2 or len(valid_signal) < 2:
            raise ValueError("Insufficient valid values for crossover detection")

        # Get last two values
        curr_idx = valid_macd[-1]
        prev_idx = valid_macd[-2]

        # Crossover: was below, now above
        was_below = self.macd_line[prev_idx] <= self.signal_line[prev_idx]
        is_above = self.macd_line[curr_idx] > self.signal_line[curr_idx]

        return bool(was_below and is_above)

    def is_bearish_crossover(self) -> bool:
        """Check if MACD just crossed below signal line (bearish signal).

        Returns:
            True if MACD crossed below signal in the last bar.

        Raises:
            ValueError: If insufficient valid values for crossover detection.

        Example:
            >>> result = macd.calculate(series)
            >>> if result.is_bearish_crossover():
            ...     print("Bearish crossover: potential sell signal")
        """
        # Find last two valid indices for both MACD and signal
        valid_macd = np.where(~np.isnan(self.macd_line))[0]
        valid_signal = np.where(~np.isnan(self.signal_line))[0]

        if len(valid_macd) < 2 or len(valid_signal) < 2:
            raise ValueError("Insufficient valid values for crossover detection")

        # Get last two values
        curr_idx = valid_macd[-1]
        prev_idx = valid_macd[-2]

        # Crossover: was above, now below
        was_above = self.macd_line[prev_idx] >= self.signal_line[prev_idx]
        is_below = self.macd_line[curr_idx] < self.signal_line[curr_idx]

        return bool(was_above and is_below)

    def histogram_rising(self) -> bool:
        """Check if histogram is increasing (MACD accelerating).

        Returns:
            True if current histogram > previous histogram.

        Raises:
            ValueError: If insufficient valid histogram values.

        Example:
            >>> result = macd.calculate(series)
            >>> if result.histogram_rising():
            ...     print("Momentum accelerating")
        """
        valid_hist = np.where(~np.isnan(self.histogram))[0]

        if len(valid_hist) < 2:
            raise ValueError("Insufficient valid histogram values")

        curr_idx = valid_hist[-1]
        prev_idx = valid_hist[-2]

        return bool(self.histogram[curr_idx] > self.histogram[prev_idx])

    def histogram_falling(self) -> bool:
        """Check if histogram is decreasing (MACD decelerating).

        Returns:
            True if current histogram < previous histogram.

        Raises:
            ValueError: If insufficient valid histogram values.

        Example:
            >>> result = macd.calculate(series)
            >>> if result.histogram_falling():
            ...     print("Momentum decelerating")
        """
        valid_hist = np.where(~np.isnan(self.histogram))[0]

        if len(valid_hist) < 2:
            raise ValueError("Insufficient valid histogram values")

        curr_idx = valid_hist[-1]
        prev_idx = valid_hist[-2]

        return bool(self.histogram[curr_idx] < self.histogram[prev_idx])

    def __repr__(self) -> str:
        """String representation of MACD result.

        Returns:
            String with MACD name and component counts.
        """
        valid_macd = np.count_nonzero(~np.isnan(self.macd_line))
        valid_signal = np.count_nonzero(~np.isnan(self.signal_line))
        valid_hist = np.count_nonzero(~np.isnan(self.histogram))

        return (
            f"MACDResult(name={self.name}, "
            f"macd={valid_macd}, signal={valid_signal}, hist={valid_hist})"
        )


class MACD(Indicator):
    """Moving Average Convergence Divergence indicator.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Trend-following momentum indicator using two EMAs. Crossovers between
    MACD and signal line indicate potential trend changes.

    Attributes:
        fast_period: Fast EMA period (default 12).
        slow_period: Slow EMA period (default 26).
        signal_period: Signal line EMA period (default 9).

    Example:
        >>> from src.data.service import MarketDataService
        >>> service = MarketDataService()
        >>> series, _ = await service.get_ohlcv("BTCUSDT", "1h", limit=100)
        >>>
        >>> macd = MACD(fast=12, slow=26, signal=9)
        >>> result = macd.calculate(series)
        >>> print(f"MACD: {result.current:.2f}")
        >>> print(f"Signal: {result.signal_line[-1]:.2f}")
        >>>
        >>> if result.is_bullish_crossover():
        ...     print("Bullish crossover detected")
    """

    def __init__(
        self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
    ) -> None:
        """Initialize MACD indicator.

        Args:
            fast_period: Fast EMA period (default 12).
            slow_period: Slow EMA period (default 26, must be > fast_period).
            signal_period: Signal line EMA period (default 9).

        Raises:
            ValueError: If periods invalid or slow_period <= fast_period.
        """
        if fast_period < 1:
            raise ValueError(f"Fast period must be >= 1, got {fast_period}")
        if slow_period < 1:
            raise ValueError(f"Slow period must be >= 1, got {slow_period}")
        if signal_period < 1:
            raise ValueError(f"Signal period must be >= 1, got {signal_period}")
        if slow_period <= fast_period:
            raise ValueError(
                f"Slow period ({slow_period}) must be > fast period ({fast_period})"
            )

        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

        # Create EMA indicators for calculation
        self.fast_ema = EMA(period=fast_period)
        self.slow_ema = EMA(period=slow_period)
        self.signal_ema = EMA(period=signal_period)

    def calculate(self, series: OHLCVSeries) -> MACDResult:
        """Calculate MACD values from OHLCV series.

        Calculates three components:
        1. MACD Line = Fast EMA - Slow EMA
        2. Signal Line = EMA of MACD Line
        3. Histogram = MACD Line - Signal Line

        Args:
            series: OHLCV series from Session 1 market data layer.

        Returns:
            MACDResult with all three components (NaN during warmup).

        Raises:
            ValueError: If series has insufficient data.

        Example:
            >>> series = OHLCVSeries(candles=[...], symbol="BTCUSDT", timeframe="1h")
            >>> macd = MACD(fast=12, slow=26, signal=9)
            >>> result = macd.calculate(series)
            >>> result.macd_line  # MACD values
            >>> result.signal_line  # Signal values
            >>> result.histogram  # Histogram values
        """
        min_bars = self.slow_period + self.signal_period
        if len(series) < min_bars:
            raise ValueError(
                f"MACD({self.fast_period},{self.slow_period},{self.signal_period}) "
                f"requires at least {min_bars} bars, got {len(series)}"
            )

        # Calculate fast and slow EMAs
        fast_result = self.fast_ema.calculate(series)
        slow_result = self.slow_ema.calculate(series)

        # Calculate MACD line (fast EMA - slow EMA)
        macd_line = fast_result.values - slow_result.values

        # Calculate signal line (EMA of MACD)
        # Create temporary series for signal calculation
        # Signal EMA needs non-NaN MACD values
        valid_macd_start = self.slow_period - 1  # First valid MACD index

        # Initialize signal values array
        signal_line: NDArray[np.float64] = np.full(
            len(macd_line), np.nan, dtype=np.float64
        )

        # Extract valid MACD values for signal calculation
        valid_macd = macd_line[valid_macd_start:]

        if len(valid_macd) >= self.signal_period:
            # Calculate signal EMA manually
            alpha = 2.0 / (self.signal_period + 1)

            # Initialize first signal value as SMA
            signal_line[valid_macd_start + self.signal_period - 1] = np.mean(
                valid_macd[: self.signal_period]
            )

            # Apply exponential smoothing
            for i in range(self.signal_period, len(valid_macd)):
                signal_idx = valid_macd_start + i
                prev_signal_idx = signal_idx - 1

                signal_line[signal_idx] = (
                    alpha * macd_line[signal_idx]
                    + (1 - alpha) * signal_line[prev_signal_idx]
                )

        # Calculate histogram (MACD - Signal)
        histogram = macd_line - signal_line

        return MACDResult(
            name=f"MACD_{self.fast_period}_{self.slow_period}_{self.signal_period}",
            macd_line=macd_line,
            signal_line=signal_line,
            histogram=histogram,
            params={
                "fast_period": self.fast_period,
                "slow_period": self.slow_period,
                "signal_period": self.signal_period,
            },
        )

    @staticmethod
    def required_periods(fast: int = 12, slow: int = 26, signal: int = 9) -> int:
        """Return minimum bars needed before first valid MACD value.

        Args:
            fast: Fast EMA period.
            slow: Slow EMA period.
            signal: Signal EMA period.

        Returns:
            Minimum number of bars required (slow + signal).
        """
        return slow + signal

    def __repr__(self) -> str:
        """String representation of MACD indicator.

        Returns:
            String with MACD periods.
        """
        return (
            f"MACD(fast={self.fast_period}, slow={self.slow_period}, "
            f"signal={self.signal_period})"
        )
