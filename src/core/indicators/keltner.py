"""Keltner Channel indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-001 - Compute-on-demand indicator strategy

Keltner Channels are volatility-based envelopes using EMA (center) and ATR
(band width), unlike Bollinger Bands which use SMA + standard deviation.
The ATR-based bands adapt to true range volatility rather than close-only
statistical dispersion.

Formula:
    Middle = EMA(close, ema_period)
    Upper = Middle + (multiplier * ATR(atr_period))
    Lower = Middle - (multiplier * ATR(atr_period))
    Width = (Upper - Lower) / Middle * 100  (as percentage)

Reference: Chester Keltner (1960), Linda Raschke (modern version with ATR)
"""
from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from src.core.indicators.atr import ATR
from src.core.indicators.base import Indicator, IndicatorResult
from src.core.indicators.ema import EMA
from src.data.market_data import OHLCVSeries


class KeltnerResult(IndicatorResult[float]):
    """Keltner Channel result with upper, middle, and lower bands.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Extends IndicatorResult to provide access to all Keltner components.

    Attributes:
        upper: Upper band values (EMA + mult * ATR).
        middle: Middle band values (EMA).
        lower: Lower band values (EMA - mult * ATR).
        width: Band width as percentage of middle band.
    """

    def __init__(
        self,
        name: str,
        upper: NDArray[np.float64],
        middle: NDArray[np.float64],
        lower: NDArray[np.float64],
        width: NDArray[np.float64],
        params: dict[str, Any],
    ) -> None:
        """Initialize Keltner Channel result.

        Args:
            name: Indicator name (e.g., "KC_20_14_2.0").
            upper: Upper band values array.
            middle: Middle band (EMA) values array.
            lower: Lower band values array.
            width: Band width percentage array.
            params: Parameters (ema_period, atr_period, multiplier).
        """
        # Store middle band as primary values for base class
        super().__init__(name, middle, params)

        self.upper = upper
        self.middle = middle
        self.lower = lower
        self.width = width

    def __repr__(self) -> str:
        """String representation of Keltner Channel result.

        Returns:
            String with KC name and valid value count.
        """
        valid_count = np.count_nonzero(~np.isnan(self.middle))
        return f"KeltnerResult(name={self.name}, values={valid_count})"


class KeltnerChannel(Indicator):
    """Keltner Channel indicator.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Volatility-based channel using EMA center and ATR-based bands.
    Useful for trend following and mean reversion strategies.

    BB Squeeze detection: BB inside Keltner = volatility compression.

    Attributes:
        ema_period: EMA period for the middle band (default 20).
        atr_period: ATR period for band width (default 14).
        multiplier: ATR multiplier for bands (default 2.0).

    Example:
        >>> kc = KeltnerChannel(ema_period=20, atr_period=14, multiplier=2.0)
        >>> result = kc.calculate(series)
        >>> print(f"Upper: {result.upper[-1]:.2f}")
        >>> print(f"Middle: {result.middle[-1]:.2f}")
        >>> print(f"Lower: {result.lower[-1]:.2f}")
    """

    def __init__(
        self,
        ema_period: int = 20,
        atr_period: int = 14,
        multiplier: float = 2.0,
    ) -> None:
        """Initialize Keltner Channel indicator.

        Args:
            ema_period: EMA period for center line (default 20).
            atr_period: ATR period for band width (default 14).
            multiplier: ATR multiplier for bands (default 2.0).
                       Common values: 1.0, 1.5, 2.0, 2.5.

        Raises:
            ValueError: If ema_period < 1, atr_period < 1, or multiplier <= 0.
        """
        if ema_period < 1:
            raise ValueError(f"EMA period must be >= 1, got {ema_period}")
        if atr_period < 1:
            raise ValueError(f"ATR period must be >= 1, got {atr_period}")
        if multiplier <= 0:
            raise ValueError(f"Multiplier must be > 0, got {multiplier}")

        self.ema_period = ema_period
        self.atr_period = atr_period
        self.multiplier = multiplier
        self._ema = EMA(period=ema_period)
        self._atr = ATR(period=atr_period)

    def calculate(self, series: OHLCVSeries) -> KeltnerResult:
        """Calculate Keltner Channel from OHLCV series.

        Calculates four components:
        1. Middle Band (EMA of close)
        2. Upper Band (EMA + multiplier * ATR)
        3. Lower Band (EMA - multiplier * ATR)
        4. Width (band width as % of middle)

        Args:
            series: OHLCV series with sufficient data.

        Returns:
            KeltnerResult with all four components (NaN during warmup).

        Raises:
            ValueError: If series has insufficient data.
        """
        min_bars = self.required_periods(self.ema_period, self.atr_period)
        if len(series) < min_bars:
            raise ValueError(
                f"KeltnerChannel({self.ema_period},{self.atr_period},"
                f"{self.multiplier}) requires at least {min_bars} bars, "
                f"got {len(series)}"
            )

        # Calculate EMA (middle band) and ATR (band width)
        ema_result = self._ema.calculate(series)
        atr_result = self._atr.calculate(series)

        middle = ema_result.values
        atr_values = atr_result.values

        # Calculate upper and lower bands
        upper = middle + (self.multiplier * atr_values)
        lower = middle - (self.multiplier * atr_values)

        # Calculate width as % of middle
        n = len(middle)
        width: NDArray[np.float64] = np.full(n, np.nan, dtype=np.float64)
        valid = ~np.isnan(middle) & (middle != 0) & ~np.isnan(atr_values)
        width[valid] = (upper[valid] - lower[valid]) / middle[valid] * 100

        return KeltnerResult(
            name=f"KC_{self.ema_period}_{self.atr_period}_{self.multiplier}",
            upper=upper,
            middle=middle,
            lower=lower,
            width=width,
            params={
                "ema_period": self.ema_period,
                "atr_period": self.atr_period,
                "multiplier": self.multiplier,
            },
        )

    @staticmethod
    def required_periods(ema_period: int, atr_period: int) -> int:
        """Return minimum bars needed before first valid Keltner value.

        Both EMA and ATR must be valid. ATR needs period+1 bars.

        Args:
            ema_period: EMA period parameter.
            atr_period: ATR period parameter.

        Returns:
            Minimum number of bars required.
        """
        return max(ema_period, atr_period + 1)

    def __repr__(self) -> str:
        """String representation of Keltner Channel indicator.

        Returns:
            String with ema_period, atr_period, and multiplier.
        """
        return (
            f"KeltnerChannel(ema_period={self.ema_period}, "
            f"atr_period={self.atr_period}, multiplier={self.multiplier})"
        )
