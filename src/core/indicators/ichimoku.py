"""Ichimoku Cloud (Ichimoku Kinko Hyo) indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-001 - Compute-on-demand indicator strategy

Ichimoku is a comprehensive trend system with five components that provide
support/resistance levels, trend direction, and momentum simultaneously.

Crypto-adjusted defaults (20/60/120/30) replace traditional (9/26/52/26)
because crypto markets trade 24/7, providing more bars per calendar period.

Formula:
    Tenkan-sen  = (highest(H, tenkan_period) + lowest(L, tenkan_period)) / 2
    Kijun-sen   = (highest(H, kijun_period)  + lowest(L, kijun_period))  / 2
    Senkou A    = (Tenkan + Kijun) / 2, evaluated at bar[i - displacement]
    Senkou B    = (highest(H, senkou_b_period) + lowest(L, senkou_b_period)) / 2,
                  evaluated at bar[i - displacement]
    Chikou Span = close[i - displacement]

Note on displacement for backtesting:
    In live charting, Senkou spans are "projected forward" (drawn at i + displacement).
    For backtesting at bar[i], the cloud at bar[i] was computed from data at
    bar[i - displacement]. This module stores values at their COMPUTATION index,
    so the generator accesses senkou_a[i] which represents the cloud projected
    from bar[i - displacement] to bar[i]. No lookahead.

Reference: Goichi Hosoda (1969), adapted for crypto by multiple practitioners
"""
from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from src.core.indicators.base import Indicator, IndicatorResult
from src.data.market_data import OHLCVSeries


class IchimokuResult(IndicatorResult[float]):
    """Ichimoku Cloud result with all five components.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Attributes:
        tenkan_sen: Conversion line (short-term midpoint).
        kijun_sen: Base line (medium-term midpoint).
        senkou_span_a: Leading Span A (Tenkan/Kijun avg, shifted for cloud).
        senkou_span_b: Leading Span B (long-term midpoint, shifted for cloud).
        chikou_span: Lagging Span (close shifted backward).
    """

    def __init__(
        self,
        name: str,
        tenkan_sen: NDArray[np.float64],
        kijun_sen: NDArray[np.float64],
        senkou_span_a: NDArray[np.float64],
        senkou_span_b: NDArray[np.float64],
        chikou_span: NDArray[np.float64],
        params: dict[str, Any],
    ) -> None:
        """Initialize Ichimoku result.

        Args:
            name: Indicator name (e.g., "Ichimoku_20_60_120_30").
            tenkan_sen: Tenkan-sen values array.
            kijun_sen: Kijun-sen values array.
            senkou_span_a: Senkou Span A values (cloud, at computation index).
            senkou_span_b: Senkou Span B values (cloud, at computation index).
            chikou_span: Chikou Span values (lagging close).
            params: Parameters dict.
        """
        # Tenkan-sen as primary values for base class
        super().__init__(name, tenkan_sen, params)

        self.tenkan_sen = tenkan_sen
        self.kijun_sen = kijun_sen
        self.senkou_span_a = senkou_span_a
        self.senkou_span_b = senkou_span_b
        self.chikou_span = chikou_span

    def is_price_above_cloud(self, index: int = -1) -> bool:
        """Check if the cloud top at index is below the Tenkan (proxy for price).

        For signal generators, compare actual close price against the cloud
        directly rather than using this convenience method.

        Args:
            index: Array index to check (default -1 = latest).

        Returns:
            True if Tenkan is above both Senkou spans at the given index.
        """
        try:
            sa = self.senkou_span_a[index]
            sb = self.senkou_span_b[index]
            tk = self.tenkan_sen[index]
        except IndexError:
            return False

        if np.isnan(sa) or np.isnan(sb) or np.isnan(tk):
            return False

        cloud_top = max(sa, sb)
        return bool(tk > cloud_top)

    def is_price_below_cloud(self, index: int = -1) -> bool:
        """Check if the cloud bottom at index is above the Tenkan.

        Args:
            index: Array index to check (default -1 = latest).

        Returns:
            True if Tenkan is below both Senkou spans.
        """
        try:
            sa = self.senkou_span_a[index]
            sb = self.senkou_span_b[index]
            tk = self.tenkan_sen[index]
        except IndexError:
            return False

        if np.isnan(sa) or np.isnan(sb) or np.isnan(tk):
            return False

        cloud_bottom = min(sa, sb)
        return bool(tk < cloud_bottom)

    def is_cloud_green(self, index: int = -1) -> bool:
        """Check if the cloud is bullish (Senkou A > Senkou B).

        Args:
            index: Array index to check (default -1 = latest).

        Returns:
            True if Senkou Span A > Senkou Span B (bullish cloud).
        """
        try:
            sa = self.senkou_span_a[index]
            sb = self.senkou_span_b[index]
        except IndexError:
            return False

        if np.isnan(sa) or np.isnan(sb):
            return False

        return bool(sa > sb)

    def tk_cross_bullish(self) -> bool:
        """Check if Tenkan just crossed above Kijun (bullish TK cross).

        Returns:
            True if Tenkan crossed above Kijun in the last bar.
        """
        valid_tk = ~np.isnan(self.tenkan_sen) & ~np.isnan(self.kijun_sen)
        valid_indices = np.where(valid_tk)[0]

        if len(valid_indices) < 2:
            return False

        curr = valid_indices[-1]
        prev = valid_indices[-2]

        was_below = self.tenkan_sen[prev] <= self.kijun_sen[prev]
        is_above = self.tenkan_sen[curr] > self.kijun_sen[curr]

        return bool(was_below and is_above)

    def tk_cross_bearish(self) -> bool:
        """Check if Tenkan just crossed below Kijun (bearish TK cross).

        Returns:
            True if Tenkan crossed below Kijun in the last bar.
        """
        valid_tk = ~np.isnan(self.tenkan_sen) & ~np.isnan(self.kijun_sen)
        valid_indices = np.where(valid_tk)[0]

        if len(valid_indices) < 2:
            return False

        curr = valid_indices[-1]
        prev = valid_indices[-2]

        was_above = self.tenkan_sen[prev] >= self.kijun_sen[prev]
        is_below = self.tenkan_sen[curr] < self.kijun_sen[curr]

        return bool(was_above and is_below)

    def __repr__(self) -> str:
        """String representation of Ichimoku result.

        Returns:
            String with indicator name and valid value count.
        """
        valid_count = np.count_nonzero(~np.isnan(self.tenkan_sen))
        return f"IchimokuResult(name={self.name}, values={valid_count})"


def _midpoint_series(
    highs: NDArray[np.float64],
    lows: NDArray[np.float64],
    period: int,
) -> NDArray[np.float64]:
    """Calculate rolling midpoint: (highest(H, period) + lowest(L, period)) / 2.

    Used for Tenkan-sen, Kijun-sen, and Senkou Span B.

    Args:
        highs: High price array.
        lows: Low price array.
        period: Lookback period.

    Returns:
        Numpy array with midpoint values (NaN during warmup).
    """
    n = len(highs)
    result: NDArray[np.float64] = np.full(n, np.nan, dtype=np.float64)

    for i in range(period - 1, n):
        window_high = highs[i - period + 1 : i + 1]
        window_low = lows[i - period + 1 : i + 1]
        result[i] = (np.max(window_high) + np.min(window_low)) / 2.0

    return result


class IchimokuCloud(Indicator):
    """Ichimoku Cloud indicator with crypto-adjusted defaults.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Comprehensive trend system with five components providing support/resistance,
    trend direction, and momentum signals.

    Uses crypto-adjusted periods (20/60/120/30) by default. Traditional
    parameters (9/26/52/26) were designed for Japanese 6-day work weeks.

    Attributes:
        tenkan_period: Tenkan-sen (conversion line) period (default 20).
        kijun_period: Kijun-sen (base line) period (default 60).
        senkou_b_period: Senkou Span B period (default 120).
        displacement: Forward/backward shift for cloud and Chikou (default 30).

    Example:
        >>> ichi = IchimokuCloud(tenkan=20, kijun=60, senkou_b=120, displacement=30)
        >>> result = ichi.calculate(series)
        >>> if result.is_cloud_green():
        ...     print("Bullish cloud")
    """

    def __init__(
        self,
        tenkan_period: int = 20,
        kijun_period: int = 60,
        senkou_b_period: int = 120,
        displacement: int = 30,
    ) -> None:
        """Initialize Ichimoku Cloud indicator.

        Args:
            tenkan_period: Conversion line period (default 20, trad: 9).
            kijun_period: Base line period (default 60, trad: 26).
            senkou_b_period: Leading Span B period (default 120, trad: 52).
            displacement: Cloud shift / Chikou shift (default 30, trad: 26).

        Raises:
            ValueError: If any period < 1.
        """
        if tenkan_period < 1:
            raise ValueError(f"Tenkan period must be >= 1, got {tenkan_period}")
        if kijun_period < 1:
            raise ValueError(f"Kijun period must be >= 1, got {kijun_period}")
        if senkou_b_period < 1:
            raise ValueError(
                f"Senkou B period must be >= 1, got {senkou_b_period}"
            )
        if displacement < 1:
            raise ValueError(f"Displacement must be >= 1, got {displacement}")

        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period
        self.senkou_b_period = senkou_b_period
        self.displacement = displacement

    def calculate(self, series: OHLCVSeries) -> IchimokuResult:
        """Calculate Ichimoku Cloud from OHLCV series.

        Computes all five components. Senkou spans are stored at the index
        where their projected value applies (i.e., the computation happened
        `displacement` bars earlier). This makes backtesting straightforward:
        access senkou_a[i] for the cloud at bar i.

        Args:
            series: OHLCV series with sufficient data.

        Returns:
            IchimokuResult with all five components.

        Raises:
            ValueError: If series has insufficient data.
        """
        min_bars = self.required_periods(
            self.senkou_b_period, self.displacement
        )
        if len(series) < min_bars:
            raise ValueError(
                f"IchimokuCloud({self.tenkan_period},{self.kijun_period},"
                f"{self.senkou_b_period},{self.displacement}) requires at "
                f"least {min_bars} bars, got {len(series)}"
            )

        highs = series.highs
        lows = series.lows
        closes = series.closes
        n = len(highs)

        # Tenkan-sen: short-term midpoint
        tenkan = _midpoint_series(highs, lows, self.tenkan_period)

        # Kijun-sen: medium-term midpoint
        kijun = _midpoint_series(highs, lows, self.kijun_period)

        # Senkou Span B raw: long-term midpoint (before displacement)
        senkou_b_raw = _midpoint_series(highs, lows, self.senkou_b_period)

        # Senkou Span A raw: (Tenkan + Kijun) / 2 (before displacement)
        senkou_a_raw: NDArray[np.float64] = np.full(
            n, np.nan, dtype=np.float64
        )
        valid_tk = ~np.isnan(tenkan) & ~np.isnan(kijun)
        senkou_a_raw[valid_tk] = (tenkan[valid_tk] + kijun[valid_tk]) / 2.0

        # Displace Senkou spans forward by 'displacement' bars.
        # senkou_span_a[i] = senkou_a_raw[i - displacement]
        # This means at bar[i], the cloud value was computed from data
        # at bar[i - displacement], which is safe (no lookahead).
        senkou_span_a: NDArray[np.float64] = np.full(
            n, np.nan, dtype=np.float64
        )
        senkou_span_b: NDArray[np.float64] = np.full(
            n, np.nan, dtype=np.float64
        )

        for i in range(self.displacement, n):
            src = i - self.displacement
            senkou_span_a[i] = senkou_a_raw[src]
            senkou_span_b[i] = senkou_b_raw[src]

        # Chikou Span: close displaced backward by 'displacement' bars.
        # chikou_span[i] = close[i], but it's compared against price at
        # [i + displacement] in traditional charting. For backtesting,
        # the generator checks if close[i] > close[i - displacement]
        # (the price that was displacement bars ago).
        # We store close[i - displacement] so the generator can compare
        # current close vs chikou_span[i] directly.
        chikou_span: NDArray[np.float64] = np.full(
            n, np.nan, dtype=np.float64
        )
        for i in range(self.displacement, n):
            chikou_span[i] = closes[i - self.displacement]

        return IchimokuResult(
            name=(
                f"Ichimoku_{self.tenkan_period}_{self.kijun_period}"
                f"_{self.senkou_b_period}_{self.displacement}"
            ),
            tenkan_sen=tenkan,
            kijun_sen=kijun,
            senkou_span_a=senkou_span_a,
            senkou_span_b=senkou_span_b,
            chikou_span=chikou_span,
            params={
                "tenkan_period": self.tenkan_period,
                "kijun_period": self.kijun_period,
                "senkou_b_period": self.senkou_b_period,
                "displacement": self.displacement,
            },
        )

    @staticmethod
    # Not a Liskov override: required_periods is never invoked through a
    # base-typed reference. It is a per-class helper with a single-period
    # default on Indicator; this indicator genuinely takes different period
    # parameters. See DEC-2026-08-11-008.
    def required_periods(  # type: ignore[override]
        senkou_b_period: int, displacement: int
    ) -> int:
        """Return minimum bars needed before first valid cloud value.

        The cloud needs senkou_b_period for the longest midpoint calculation
        plus displacement for the forward shift.

        Args:
            senkou_b_period: Longest midpoint period.
            displacement: Forward shift period.

        Returns:
            Minimum number of bars required.
        """
        return senkou_b_period + displacement

    def __repr__(self) -> str:
        """String representation of Ichimoku Cloud indicator.

        Returns:
            String with all period parameters.
        """
        return (
            f"IchimokuCloud(tenkan={self.tenkan_period}, "
            f"kijun={self.kijun_period}, "
            f"senkou_b={self.senkou_b_period}, "
            f"displacement={self.displacement})"
        )
