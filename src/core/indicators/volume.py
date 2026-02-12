"""Volume Average indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-001 - Compute-on-demand indicator strategy

Volume Average calculates the simple moving average of volume to identify
volume spikes and measure trading activity trends.

Formula:
    Volume Average = SMA(Volume, period)

Reference: TradingView Volume indicator
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from src.core.indicators.base import Indicator, IndicatorResult
from src.data.market_data import OHLCVSeries


class VolumeAverage(Indicator):
    """Volume Average indicator.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Calculates the simple moving average of volume. Used to identify
    volume spikes (current volume significantly above average) and
    measure trading activity trends.

    Attributes:
        period: Period for volume average (default 20).

    Example:
        >>> from src.data.service import MarketDataService
        >>> service = MarketDataService()
        >>> series, _ = await service.get_ohlcv("BTCUSDT", "1h", limit=100)
        >>>
        >>> vol_avg = VolumeAverage(period=20)
        >>> result = vol_avg.calculate(series)
        >>> print(f"Current Volume: {series.volumes[-1]:.0f}")
        >>> print(f"Average Volume: {result.current:.0f}")
        >>>
        >>> if VolumeAverage.is_volume_spike(series.volumes, result.values, multiplier=2.0):
        ...     print("Volume spike: 2x average!")
    """

    def __init__(self, period: int = 20) -> None:
        """Initialize Volume Average indicator.

        Args:
            period: Period for volume average (default 20).
                   Common values: 10, 20, 50.

        Raises:
            ValueError: If period < 1.
        """
        if period < 1:
            raise ValueError(f"Period must be >= 1, got {period}")

        self.period = period

    def calculate(self, series: OHLCVSeries) -> IndicatorResult[float]:
        """Calculate volume average from OHLCV series.

        Uses simple moving average applied to volume instead of price.

        Args:
            series: OHLCV series from Session 1 market data layer.

        Returns:
            IndicatorResult with volume average values (NaN for first 'period-1' bars).

        Raises:
            ValueError: If series has insufficient data.

        Example:
            >>> series = OHLCVSeries(candles=[...], symbol="BTCUSDT", timeframe="1h")
            >>> vol_avg = VolumeAverage(period=20)
            >>> result = vol_avg.calculate(series)
            >>> result.current  # Latest volume average
        """
        if len(series) < self.period:
            raise ValueError(
                f"VolumeAverage({self.period}) requires at least {self.period} bars, "
                f"got {len(series)}"
            )

        volumes = series.volumes
        vol_avg: NDArray[np.float64] = np.full(len(volumes), np.nan, dtype=np.float64)

        # Calculate SMA of volume using rolling window
        weights = np.ones(self.period) / self.period
        vol_avg_result = np.convolve(volumes, weights, mode="valid")

        # Place results starting at index period-1
        vol_avg[self.period - 1 :] = vol_avg_result

        return IndicatorResult(
            name=f"VOL_AVG_{self.period}",
            values=vol_avg,
            params={"period": self.period},
        )

    @staticmethod
    def is_volume_spike(
        volumes: NDArray[np.float64],
        avg_volumes: NDArray[np.float64],
        multiplier: float = 1.5,
    ) -> bool:
        """Check if current volume is significantly above average (spike).

        Args:
            volumes: Volume array (from OHLCVSeries.volumes).
            avg_volumes: Volume average array (from IndicatorResult.values).
            multiplier: Spike threshold multiplier (default 1.5 = 50% above average).
                       Common values: 1.5, 2.0, 3.0.

        Returns:
            True if current volume > average * multiplier.

        Raises:
            ValueError: If insufficient valid values or multiplier <= 0.

        Example:
            >>> result = vol_avg.calculate(series)
            >>> if VolumeAverage.is_volume_spike(series.volumes, result.values, multiplier=2.0):
            ...     print("High volume: potential breakout or reversal")
        """
        if multiplier <= 0:
            raise ValueError(f"Multiplier must be > 0, got {multiplier}")

        # Find last valid average volume
        valid_indices = np.where(~np.isnan(avg_volumes))[0]

        if len(valid_indices) == 0:
            raise ValueError("No valid volume average values available")

        last_idx = valid_indices[-1]
        current_volume = volumes[last_idx]
        avg_volume = avg_volumes[last_idx]

        if avg_volume == 0:
            raise ValueError("Average volume is zero")

        return bool(current_volume > (avg_volume * multiplier))

    @staticmethod
    def volume_ratio(current: float, avg: float) -> float:
        """Calculate ratio of current volume to average volume.

        Args:
            current: Current volume.
            avg: Average volume.

        Returns:
            Ratio (e.g., 2.0 means current is 2x average).

        Raises:
            ValueError: If avg is zero.

        Example:
            >>> result = vol_avg.calculate(series)
            >>> ratio = VolumeAverage.volume_ratio(series.volumes[-1], result.current)
            >>> print(f"Volume is {ratio:.1f}x average")
        """
        if avg == 0:
            raise ValueError("Average volume cannot be zero")

        return current / avg

    def __repr__(self) -> str:
        """String representation of Volume Average indicator.

        Returns:
            String with period.
        """
        return f"VolumeAverage(period={self.period})"
