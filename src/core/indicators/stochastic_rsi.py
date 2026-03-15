"""Stochastic RSI indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-001 - Compute-on-demand indicator strategy

Stochastic RSI applies the Stochastic oscillator formula to RSI values
instead of price. This creates a more sensitive momentum oscillator that
reaches overbought/oversold extremes more frequently than plain RSI.

Formula:
    1. RSI = RSI(close, rsi_period)
    2. StochK_raw = (RSI - lowest(RSI, stoch_period)) /
                    (highest(RSI, stoch_period) - lowest(RSI, stoch_period)) * 100
    3. K = SMA(StochK_raw, k_smooth)
    4. D = SMA(K, d_smooth)

Reference: Tushard Chande & Stanley Kroll (1994), "The New Technical Trader"
"""
from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from src.core.indicators.base import Indicator, IndicatorResult
from src.core.indicators.rsi import RSI
from src.data.market_data import OHLCVSeries


class StochasticRSIResult(IndicatorResult[float]):
    """Stochastic RSI result with K and D lines.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Extends IndicatorResult to provide K-line (fast) and D-line (signal).

    Attributes:
        k_line: %K values (fast stochastic of RSI, 0-100).
        d_line: %D values (smoothed K, signal line, 0-100).
    """

    def __init__(
        self,
        name: str,
        k_line: NDArray[np.float64],
        d_line: NDArray[np.float64],
        params: dict[str, Any],
    ) -> None:
        """Initialize Stochastic RSI result.

        Args:
            name: Indicator name (e.g., "StochRSI_14_14_3_3").
            k_line: %K values array.
            d_line: %D values array.
            params: Parameters (rsi_period, stoch_period, k_smooth, d_smooth).
        """
        # Store K line as primary values for base class
        super().__init__(name, k_line, params)

        self.k_line = k_line
        self.d_line = d_line

    def is_overbought(self, threshold: float = 80.0) -> bool:
        """Check if current K value indicates overbought condition.

        Args:
            threshold: Overbought threshold (default 80.0).

        Returns:
            True if current K > threshold.

        Raises:
            ValueError: If no valid K values.
        """
        valid_k = self.k_line[~np.isnan(self.k_line)]
        if len(valid_k) == 0:
            raise ValueError("No valid StochRSI K values")
        return bool(valid_k[-1] > threshold)

    def is_oversold(self, threshold: float = 20.0) -> bool:
        """Check if current K value indicates oversold condition.

        Args:
            threshold: Oversold threshold (default 20.0).

        Returns:
            True if current K < threshold.

        Raises:
            ValueError: If no valid K values.
        """
        valid_k = self.k_line[~np.isnan(self.k_line)]
        if len(valid_k) == 0:
            raise ValueError("No valid StochRSI K values")
        return bool(valid_k[-1] < threshold)

    def __repr__(self) -> str:
        """String representation of Stochastic RSI result.

        Returns:
            String with indicator name and valid value count.
        """
        valid_count = np.count_nonzero(~np.isnan(self.k_line))
        return f"StochasticRSIResult(name={self.name}, values={valid_count})"


class StochasticRSI(Indicator):
    """Stochastic RSI indicator.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Applies the Stochastic oscillator to RSI values for more sensitive
    overbought/oversold detection. Values range 0-100.

    Attributes:
        rsi_period: RSI calculation period (default 14).
        stoch_period: Stochastic lookback period (default 14).
        k_smooth: K-line smoothing period (default 3).
        d_smooth: D-line smoothing period (default 3).

    Example:
        >>> stoch_rsi = StochasticRSI(rsi_period=14, stoch_period=14)
        >>> result = stoch_rsi.calculate(series)
        >>> if result.is_overbought(80):
        ...     print("Overbought")
    """

    def __init__(
        self,
        rsi_period: int = 14,
        stoch_period: int = 14,
        k_smooth: int = 3,
        d_smooth: int = 3,
    ) -> None:
        """Initialize Stochastic RSI indicator.

        Args:
            rsi_period: RSI period (default 14).
            stoch_period: Stochastic lookback (default 14).
            k_smooth: SMA smoothing for %K (default 3).
            d_smooth: SMA smoothing for %D (default 3).

        Raises:
            ValueError: If any period < 1.
        """
        if rsi_period < 1:
            raise ValueError(f"RSI period must be >= 1, got {rsi_period}")
        if stoch_period < 1:
            raise ValueError(f"Stoch period must be >= 1, got {stoch_period}")
        if k_smooth < 1:
            raise ValueError(f"K smooth must be >= 1, got {k_smooth}")
        if d_smooth < 1:
            raise ValueError(f"D smooth must be >= 1, got {d_smooth}")

        self.rsi_period = rsi_period
        self.stoch_period = stoch_period
        self.k_smooth = k_smooth
        self.d_smooth = d_smooth
        self._rsi = RSI(period=rsi_period)

    def calculate(self, series: OHLCVSeries) -> StochasticRSIResult:
        """Calculate Stochastic RSI from OHLCV series.

        Steps:
        1. Calculate RSI(rsi_period) from closes
        2. Apply Stochastic formula to RSI values over stoch_period
        3. Smooth raw %K with SMA(k_smooth)
        4. Smooth %K with SMA(d_smooth) to get %D

        Args:
            series: OHLCV series with sufficient data.

        Returns:
            StochasticRSIResult with K and D lines (NaN during warmup).

        Raises:
            ValueError: If series has insufficient data.
        """
        min_bars = self.required_periods(
            self.rsi_period, self.stoch_period, self.k_smooth, self.d_smooth
        )
        if len(series) < min_bars:
            raise ValueError(
                f"StochasticRSI({self.rsi_period},{self.stoch_period},"
                f"{self.k_smooth},{self.d_smooth}) requires at least "
                f"{min_bars} bars, got {len(series)}"
            )

        # Step 1: Calculate RSI
        rsi_result = self._rsi.calculate(series)
        rsi_values = rsi_result.values
        n = len(rsi_values)

        # Step 2: Apply Stochastic formula to RSI values
        stoch_k_raw: NDArray[np.float64] = np.full(n, np.nan, dtype=np.float64)

        for i in range(self.stoch_period - 1, n):
            window = rsi_values[i - self.stoch_period + 1 : i + 1]
            # Skip windows with NaN (RSI warmup period)
            valid_window = window[~np.isnan(window)]
            if len(valid_window) < self.stoch_period:
                continue

            highest_rsi = np.max(valid_window)
            lowest_rsi = np.min(valid_window)
            rsi_range = highest_rsi - lowest_rsi

            if rsi_range == 0:
                # All RSI values equal in window — set to 50 (midpoint)
                stoch_k_raw[i] = 50.0
            else:
                stoch_k_raw[i] = (
                    (rsi_values[i] - lowest_rsi) / rsi_range * 100.0
                )

        # Step 3: Smooth K_raw with SMA(k_smooth)
        k_line: NDArray[np.float64] = np.full(n, np.nan, dtype=np.float64)

        for i in range(n):
            if i < self.k_smooth - 1:
                continue
            window = stoch_k_raw[i - self.k_smooth + 1 : i + 1]
            valid = window[~np.isnan(window)]
            if len(valid) == self.k_smooth:
                k_line[i] = np.mean(valid)

        # Step 4: Smooth K with SMA(d_smooth) to get D
        d_line: NDArray[np.float64] = np.full(n, np.nan, dtype=np.float64)

        for i in range(n):
            if i < self.d_smooth - 1:
                continue
            window = k_line[i - self.d_smooth + 1 : i + 1]
            valid = window[~np.isnan(window)]
            if len(valid) == self.d_smooth:
                d_line[i] = np.mean(valid)

        return StochasticRSIResult(
            name=(
                f"StochRSI_{self.rsi_period}_{self.stoch_period}"
                f"_{self.k_smooth}_{self.d_smooth}"
            ),
            k_line=k_line,
            d_line=d_line,
            params={
                "rsi_period": self.rsi_period,
                "stoch_period": self.stoch_period,
                "k_smooth": self.k_smooth,
                "d_smooth": self.d_smooth,
            },
        )

    @staticmethod
    def required_periods(
        rsi_period: int,
        stoch_period: int,
        k_smooth: int,
        d_smooth: int,
    ) -> int:
        """Return minimum bars needed before first valid StochRSI value.

        Cascading warmup: RSI needs rsi_period+1, then stoch_period for
        the stochastic window, then k_smooth and d_smooth for smoothing.

        Args:
            rsi_period: RSI period.
            stoch_period: Stochastic lookback.
            k_smooth: K smoothing period.
            d_smooth: D smoothing period.

        Returns:
            Minimum number of bars required.
        """
        return rsi_period + 1 + stoch_period + k_smooth + d_smooth

    def __repr__(self) -> str:
        """String representation of Stochastic RSI indicator.

        Returns:
            String with all period parameters.
        """
        return (
            f"StochasticRSI(rsi_period={self.rsi_period}, "
            f"stoch_period={self.stoch_period}, "
            f"k_smooth={self.k_smooth}, d_smooth={self.d_smooth})"
        )
