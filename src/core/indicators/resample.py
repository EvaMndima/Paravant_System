"""OHLCV series resampling utility for multi-timeframe analysis.

Converts a lower-timeframe OHLCVSeries (e.g., 1H) into a higher-timeframe
series (e.g., 4H or Daily) by aggregating candles at UTC-aligned boundaries.

This enables multi-timeframe strategies within the existing single-series
generator interface: generators resample internally, avoiding changes to
the backtest engine or factory.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from src.data.market_data import OHLCV, OHLCVSeries
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Number of source bars per target bar for supported conversions.
# Only 1H -> 4H and 1H -> 1D are supported.
_BARS_PER_TARGET: dict[tuple[str, str], int] = {
    ("1h", "4h"): 4,
    ("1h", "1d"): 24,
}

# Hours at which 4H candles open (UTC).
_4H_BOUNDARIES: frozenset[int] = frozenset({0, 4, 8, 12, 16, 20})


def _bucket_key_4h(ts: datetime) -> datetime:
    """Return the 4H boundary that contains this timestamp.

    4H boundaries are 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC.
    A candle at 05:00 belongs to the 04:00-08:00 bucket.

    Args:
        ts: Timezone-aware UTC timestamp.

    Returns:
        Start-of-period timestamp for the 4H bucket.
    """
    hour = ts.hour
    bucket_hour = (hour // 4) * 4
    return ts.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)


def _bucket_key_1d(ts: datetime) -> datetime:
    """Return the daily boundary that contains this timestamp.

    Daily boundaries are at 00:00 UTC.

    Args:
        ts: Timezone-aware UTC timestamp.

    Returns:
        Start-of-day timestamp.
    """
    return ts.replace(hour=0, minute=0, second=0, microsecond=0)


def resample_ohlcv(
    series: OHLCVSeries,
    target_timeframe: str,
) -> OHLCVSeries:
    """Resample an OHLCVSeries to a higher timeframe.

    Aggregates candles using standard OHLCV rules:
    - Open = open of the first candle in the period
    - High = max of all highs in the period
    - Low = min of all lows in the period
    - Close = close of the last candle in the period
    - Volume = sum of all volumes in the period

    Only COMPLETE periods are included. The last group is dropped if it
    contains fewer candles than expected, preventing lookahead bias from
    partial periods.

    Args:
        series: Source OHLCVSeries (must be "1h" timeframe).
        target_timeframe: Target timeframe ("4h" or "1d").

    Returns:
        New OHLCVSeries at the target timeframe with the same symbol.

    Raises:
        ValueError: If source timeframe is not "1h", target is unsupported,
                    or there are not enough candles for at least one
                    complete target period.
    """
    source_tf = series.timeframe
    key = (source_tf, target_timeframe)

    if key not in _BARS_PER_TARGET:
        supported = ", ".join(
            f"{s}->{t}" for s, t in sorted(_BARS_PER_TARGET.keys())
        )
        raise ValueError(
            f"Unsupported resampling: {source_tf} -> {target_timeframe}. "
            f"Supported conversions: {supported}"
        )

    bars_per_target = _BARS_PER_TARGET[key]

    if len(series) < bars_per_target:
        raise ValueError(
            f"Need at least {bars_per_target} bars for one complete "
            f"{target_timeframe} period, got {len(series)}"
        )

    # Choose bucket function based on target timeframe
    bucket_fn = _bucket_key_4h if target_timeframe == "4h" else _bucket_key_1d

    # Group candles by their target-period bucket
    buckets: dict[datetime, list[OHLCV]] = defaultdict(list)
    for candle in series.candles:
        bucket_ts = bucket_fn(candle.timestamp)
        buckets[bucket_ts].append(candle)

    # Sort buckets by timestamp and aggregate only complete periods
    resampled: list[OHLCV] = []
    for bucket_ts in sorted(buckets.keys()):
        group = buckets[bucket_ts]

        # Drop incomplete periods (fewer candles than expected)
        if len(group) < bars_per_target:
            continue

        # Sort group by timestamp to ensure correct open/close ordering
        group.sort(key=lambda c: c.timestamp)

        resampled.append(
            OHLCV(
                timestamp=bucket_ts,
                open=group[0].open,
                high=max(c.high for c in group),
                low=min(c.low for c in group),
                close=group[-1].close,
                volume=sum(c.volume for c in group),
            )
        )

    if not resampled:
        raise ValueError(
            f"No complete {target_timeframe} periods found in {len(series)} "
            f"{source_tf} candles (need {bars_per_target} per period)"
        )

    logger.debug(
        "ohlcv_resampled",
        symbol=series.symbol,
        source_tf=source_tf,
        target_tf=target_timeframe,
        source_bars=len(series),
        target_bars=len(resampled),
    )

    return OHLCVSeries(
        candles=resampled,
        symbol=series.symbol,
        timeframe=target_timeframe,
    )
