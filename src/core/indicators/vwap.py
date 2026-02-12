"""Volume Weighted Average Price (VWAP) indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-001 - Compute-on-demand indicator strategy

VWAP is a volume-weighted average of price, giving more weight to prices
with higher trading volume. Used by institutional traders as a benchmark.

Formula:
    TypicalPrice = (High + Low + Close) / 3
    VWAP = Σ(TypicalPrice * Volume) / Σ(Volume)

For crypto (24/7 markets), we use a rolling window approach rather than
daily resets.

Reference: TradingView VWAP indicator
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from src.core.indicators.atr import ATR
from src.core.indicators.base import Indicator, IndicatorResult
from src.data.market_data import OHLCVSeries


class VWAPResult(IndicatorResult[float]):
    """VWAP-specific result with bands.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Extends IndicatorResult to provide direct access to VWAP and its bands.

    Attributes:
        vwap: VWAP values.
        upper_band: Upper band (VWAP + ATR * multiplier).
        lower_band: Lower band (VWAP - ATR * multiplier).
    """

    def __init__(
        self,
        name: str,
        vwap: NDArray[np.float64],
        upper_band: NDArray[np.float64],
        lower_band: NDArray[np.float64],
        params: dict[str, Any],
    ) -> None:
        """Initialize VWAP result.

        Args:
            name: Indicator name (e.g., "VWAP_20_2.0").
            vwap: VWAP values array.
            upper_band: Upper band values array.
            lower_band: Lower band values array.
            params: Parameters (period, multiplier).
        """
        # Store VWAP as primary values for base class
        super().__init__(name, vwap, params)

        self.vwap = vwap
        self.upper_band = upper_band
        self.lower_band = lower_band

    def is_at_vwap(self, tolerance: float = 0.05) -> bool:
        """Check if price is within tolerance of VWAP.

        Args:
            tolerance: Tolerance as decimal (default 0.05 = 5%).
                      Range: (0, 1].

        Returns:
            True if price within tolerance of VWAP.

        Raises:
            ValueError: If no valid VWAP values or tolerance out of range.

        Example:
            >>> result = vwap.calculate(series)
            >>> if result.is_at_vwap(tolerance=0.01):
            ...     print("Price within 1% of VWAP")
        """
        if not 0 < tolerance <= 1:
            raise ValueError(f"Tolerance must be in (0, 1], got {tolerance}")

        valid_indices = np.where(~np.isnan(self.vwap))[0]

        if len(valid_indices) == 0:
            raise ValueError("No valid VWAP values available")

        # Need closes to check distance
        if "closes" not in self.params:
            raise ValueError("Closes not stored in result params")

        closes: NDArray[np.float64] = self.params["closes"]
        last_idx = valid_indices[-1]

        vwap_val = self.vwap[last_idx]
        close_val = closes[last_idx]

        if vwap_val == 0:
            raise ValueError("VWAP value is zero, cannot calculate distance")

        # Calculate percentage distance
        pct_distance = abs(close_val - vwap_val) / vwap_val

        return bool(pct_distance <= tolerance)

    def __repr__(self) -> str:
        """String representation of VWAP result.

        Returns:
            String with VWAP name and value count.
        """
        valid_count = np.count_nonzero(~np.isnan(self.vwap))
        return f"VWAPResult(name={self.name}, values={valid_count})"


class VWAP(Indicator):
    """Volume Weighted Average Price indicator.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Volume-weighted average price over a rolling window. Gives more weight
    to prices with higher trading volume. Used as institutional benchmark.

    For crypto (24/7 markets), uses rolling window instead of daily reset.

    Attributes:
        period: Rolling window period (default 20 for ~1 day on 1H charts).
        multiplier: ATR multiplier for bands (default 2.0).

    Example:
        >>> from src.data.service import MarketDataService
        >>> service = MarketDataService()
        >>> series, _ = await service.get_ohlcv("BTCUSDT", "1h", limit=100)
        >>>
        >>> vwap = VWAP(period=20, multiplier=2.0)
        >>> result = vwap.calculate(series)
        >>> print(f"VWAP: {result.current:.2f}")
        >>> print(f"Upper Band: {result.upper_band[-1]:.2f}")
        >>>
        >>> if result.is_at_vwap(tolerance=0.01):
        ...     print("Price near VWAP (within 1%)")
    """

    def __init__(self, period: int = 20, multiplier: float = 2.0) -> None:
        """Initialize VWAP indicator.

        Args:
            period: Rolling window period (default 20).
                   For 1H charts: 20 ≈ 1 day, 168 ≈ 1 week.
            multiplier: ATR multiplier for bands (default 2.0).

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

    def calculate(self, series: OHLCVSeries) -> VWAPResult:
        """Calculate VWAP from OHLCV series.

        Uses rolling window approach for crypto (24/7 markets). Typical price
        is weighted by volume, then averaged over the rolling window.

        Args:
            series: OHLCV series from Session 1 market data layer.

        Returns:
            VWAPResult with VWAP and bands (NaN during warmup).

        Raises:
            ValueError: If series has insufficient data.

        Example:
            >>> series = OHLCVSeries(candles=[...], symbol="BTCUSDT", timeframe="1h")
            >>> vwap = VWAP(period=20, multiplier=2.0)
            >>> result = vwap.calculate(series)
        """
        min_bars = max(self.period, self.atr.period + 1)
        if len(series) < min_bars:
            raise ValueError(
                f"VWAP({self.period}) requires at least {min_bars} bars, "
                f"got {len(series)}"
            )

        # Get price and volume data
        highs = series.highs
        lows = series.lows
        closes = series.closes
        volumes = series.volumes

        # Calculate typical price (HLC3)
        typical_price = (highs + lows + closes) / 3.0

        # Calculate volume-weighted typical price
        vw_price = typical_price * volumes

        # Initialize VWAP array
        n = len(closes)
        vwap: NDArray[np.float64] = np.full(n, np.nan, dtype=np.float64)

        # Calculate rolling VWAP
        for i in range(self.period - 1, n):
            window_start = i - self.period + 1
            window_end = i + 1

            # Sum of (typical_price * volume) over window
            vw_sum = np.sum(vw_price[window_start:window_end])

            # Sum of volume over window
            vol_sum = np.sum(volumes[window_start:window_end])

            if vol_sum > 0:
                vwap[i] = vw_sum / vol_sum
            elif i > 0 and not np.isnan(vwap[i - 1]):
                # Zero volume: carry forward previous VWAP for continuity
                vwap[i] = vwap[i - 1]
            else:
                # First bar with zero volume: use typical price as fallback
                vwap[i] = typical_price[i]

        # Calculate ATR for bands
        atr_result = self.atr.calculate(series)
        atr_values = atr_result.values

        # Calculate bands (VWAP ± ATR * multiplier)
        upper_band = vwap + (atr_values * self.multiplier)
        lower_band = vwap - (atr_values * self.multiplier)

        return VWAPResult(
            name=f"VWAP_{self.period}_{self.multiplier}",
            vwap=vwap,
            upper_band=upper_band,
            lower_band=lower_band,
            params={
                "period": self.period,
                "multiplier": self.multiplier,
                "closes": closes,  # Store for is_at_vwap()
            },
        )

    @staticmethod
    def required_periods(period: int) -> int:
        """Return minimum bars needed before first valid VWAP value.

        Args:
            period: VWAP period parameter.

        Returns:
            Minimum number of bars required (period).
        """
        return period

    def __repr__(self) -> str:
        """String representation of VWAP indicator.

        Returns:
            String with period and multiplier.
        """
        return f"VWAP(period={self.period}, multiplier={self.multiplier})"
