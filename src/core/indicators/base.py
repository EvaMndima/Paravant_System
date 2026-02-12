"""Base classes for technical indicators.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-001 - Compute-on-demand indicator strategy

This module provides the foundation for all technical indicators:
- IndicatorResult: Generic result container with NaN-safe value access
- Indicator: Abstract base class enforcing calculate() contract

All indicators accept OHLCVSeries (from Session 1) and return IndicatorResult
with numpy arrays.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

import numpy as np
from numpy.typing import NDArray

from src.data.market_data import OHLCVSeries

T = TypeVar("T")


class IndicatorResult(Generic[T]):
    """Generic indicator result container with NaN-safe value access.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Provides safe access to current/previous values, automatically skipping
    NaN values from the indicator warmup period. All indicators return results
    in this container for consistent handling.

    Attributes:
        name: Indicator name with parameters (e.g., "RSI_14", "EMA_20").
        values: Numpy array of indicator values (may contain NaN during warmup).
        params: Parameters used for calculation (e.g., {"period": 14}).

    Example:
        >>> result = IndicatorResult("RSI_14", np.array([np.nan, 65.2, 72.1]), {"period": 14})
        >>> result.current  # Returns 72.1 (latest non-NaN)
        >>> result.previous  # Returns 65.2 (second-to-last non-NaN)
    """

    def __init__(
        self,
        name: str,
        values: NDArray[np.float64],
        params: dict[str, Any],
    ) -> None:
        """Initialize indicator result.

        Args:
            name: Indicator name with parameters (e.g., "RSI_14").
            values: Numpy array of indicator values (may contain NaN).
            params: Parameters used for calculation (e.g., {"period": 14}).

        Raises:
            ValueError: If name is empty or values is not a numpy array.
        """
        if not name or not name.strip():
            raise ValueError("Indicator name cannot be empty")

        if not isinstance(values, np.ndarray):
            raise ValueError(
                f"Values must be numpy array, got {type(values).__name__}"
            )

        self.name = name
        self.values = values
        self.params = params
        self._current_index = len(values) - 1

    @property
    def current(self) -> float:
        """Get current value (latest non-NaN value).

        Backtracks from the end of the array to find the first non-NaN value.
        This handles cases where the most recent bars may have incomplete data.

        Returns:
            Current indicator value (latest non-NaN).

        Raises:
            ValueError: If no valid values available (all NaN).

        Example:
            >>> result = IndicatorResult("EMA_20", np.array([np.nan, 42000.0, 42100.0]), {"period": 20})
            >>> result.current
            42100.0
        """
        # Backtrack from end to find first non-NaN value
        for i in range(self._current_index, -1, -1):
            if not np.isnan(self.values[i]):
                return float(self.values[i])

        raise ValueError(f"{self.name}: No valid values available (all NaN)")

    @property
    def previous(self) -> float:
        """Get previous value (second-to-last non-NaN value).

        Backtracks from the end of the array to find the second non-NaN value.
        Useful for detecting crossovers, trend changes, and momentum shifts.

        Returns:
            Previous indicator value (second-to-last non-NaN).

        Raises:
            ValueError: If insufficient valid values (need at least 2 non-NaN).

        Example:
            >>> result = IndicatorResult("RSI_14", np.array([np.nan, 65.2, 72.1]), {"period": 14})
            >>> result.previous
            65.2
        """
        found_count = 0
        for i in range(self._current_index, -1, -1):
            if not np.isnan(self.values[i]):
                found_count += 1
                if found_count == 2:
                    return float(self.values[i])

        raise ValueError(
            f"{self.name}: Insufficient valid values for previous "
            f"(need 2 non-NaN values, found {found_count})"
        )

    def to_list(self) -> list[float]:
        """Convert values to Python list.

        Returns:
            List of indicator values (includes NaN values from warmup period).

        Example:
            >>> result = IndicatorResult("SMA_20", np.array([np.nan, 42000.0, 42100.0]), {"period": 20})
            >>> result.to_list()
            [nan, 42000.0, 42100.0]
        """
        result: list[float] = self.values.tolist()
        return result

    def __len__(self) -> int:
        """Get number of values in result.

        Returns:
            Number of values (including NaN).
        """
        return len(self.values)

    def __repr__(self) -> str:
        """String representation of indicator result.

        Returns:
            String with indicator name, value count, and parameters.
        """
        valid_count = np.count_nonzero(~np.isnan(self.values))
        return (
            f"IndicatorResult(name={self.name}, "
            f"values={len(self.values)} ({valid_count} valid), "
            f"params={self.params})"
        )


class Indicator(ABC):
    """Abstract base class for all technical indicators.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage
    Decision: DEC-2026-02-11-001 - Compute-on-demand indicator strategy

    All indicators accept OHLCVSeries (from Session 1) and return IndicatorResult
    with numpy arrays. Indicators are stateless - each calculate() call is independent.

    Subclasses must implement:
    - calculate(): Compute indicator values from OHLCV series

    Example:
        >>> class EMA(Indicator):
        ...     def __init__(self, period: int = 20):
        ...         self.period = period
        ...
        ...     def calculate(self, series: OHLCVSeries) -> IndicatorResult:
        ...         # Calculate EMA values
        ...         values = ...  # numpy array
        ...         return IndicatorResult(f"EMA_{self.period}", values, {"period": self.period})
    """

    @abstractmethod
    def calculate(self, series: OHLCVSeries) -> IndicatorResult[float]:
        """Calculate indicator values from OHLCV series.

        Args:
            series: OHLCV series from Session 1 market data layer.
                   Provides .opens, .highs, .lows, .closes, .volumes as numpy arrays.

        Returns:
            IndicatorResult with calculated values (may contain NaN during warmup).

        Raises:
            ValueError: If series has insufficient data for calculation.

        Example:
            >>> series = OHLCVSeries(candles=[...], symbol="BTCUSDT", timeframe="1h")
            >>> ema = EMA(period=20)
            >>> result = ema.calculate(series)
            >>> result.current  # Latest EMA value
        """
        pass

    @staticmethod
    def required_periods(period: int) -> int:
        """Return minimum bars needed before first valid value.

        Most indicators need 'period' bars before producing the first valid value.
        Some complex indicators (like MACD, ADX) may need more.

        Args:
            period: Primary indicator period parameter.

        Returns:
            Minimum number of bars required for first valid indicator value.

        Example:
            >>> EMA.required_periods(20)  # Need 20 bars for first EMA(20) value
            20
            >>> MACD.required_periods(12)  # Need 26 + 9 = 35 bars (slow EMA + signal)
            35
        """
        return period

    def __repr__(self) -> str:
        """String representation of indicator.

        Returns:
            String with indicator class name and parameters.
        """
        return f"{self.__class__.__name__}()"
