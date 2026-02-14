"""Market data quality validation.

PRD Feature H - Data Quality Validation
Decision: DEC-2026-02-08-007 - Input validation

This module implements comprehensive data quality validation per PRD Feature H
to prevent trading on bad data (stale prices, extreme outliers, missing candles).

Validation checks:
- Price age (< 10 seconds for live data)
- Price change (flag if > 10% in single candle)
- Missing candles (gaps in data)
- OHLC relationships
- Required fields present
- No NaN/Infinity values

Actions on data issues:
- Stale data (> 10s): Use last known good, alert operator
- Extreme outlier (> 10% change): Ignore candle, log for review
- Small gap (< 3 candles): Interpolate linearly
- Large gap (>= 3 candles): Pause strategy, alert operator
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.data.market_data import OHLCV, OHLCVSeries
from src.utils.logging import get_logger

logger = get_logger(__name__)

# PRD Feature H - Data Quality Validation thresholds
DATA_QUALITY_THRESHOLDS: dict[str, float | int | str] = {
    "max_price_age_seconds": 10,      # Reject if price > 10s old
    "max_price_change_pct": 10.0,     # Flag if > 10% change in 1 candle
    "max_gap_candles": 3,             # Max missing candles before pause
    "interpolation_method": "linear",  # For small gaps
}

# Required OHLCV fields
REQUIRED_FIELDS = ["open", "high", "low", "close", "volume"]

# Action types for validation results
ACTION_USE = "use"                    # Data is valid, use as-is
ACTION_INTERPOLATE = "interpolate"    # Small gap, interpolate missing data
ACTION_REJECT = "reject"              # Data invalid, reject
ACTION_PAUSE = "pause"                # Large gap, pause strategy


@dataclass
class ValidationResult:
    """Result of data quality validation.

    Attributes:
        is_valid: Whether data passes validation (no blocking issues).
        issues: List of validation issues found (blocking).
        warnings: List of non-critical warnings.
        action: Recommended action ("use", "interpolate", "reject", "pause").
        metadata: Additional context about validation.
    """

    is_valid: bool
    issues: list[str]
    warnings: list[str]
    action: str  # "use", "interpolate", "reject", "pause"
    metadata: dict[str, Any]

    def __repr__(self) -> str:
        """String representation of validation result.

        Returns:
            String with validation status.
        """
        status = "VALID" if self.is_valid else "INVALID"
        return (
            f"ValidationResult(status={status}, action={self.action}, "
            f"issues={len(self.issues)}, warnings={len(self.warnings)})"
        )


class DataValidator:
    """Validate market data quality per PRD Feature H.

    PRD Feature H - Data Quality Validation

    This validator performs comprehensive checks on market data
    to prevent trading on bad data.

    Checks:
    - Price age (< 10 seconds old for live data)
    - Price change (< 10% per candle)
    - Missing candles (gaps in timestamp sequence)
    - OHLC relationships (high >= low, etc.)
    - Required fields present
    - No NaN/Infinity values
    """

    def __init__(self) -> None:
        """Initialize data validator with PRD Feature H thresholds."""
        self.thresholds: dict[str, float | int | str] = DATA_QUALITY_THRESHOLDS.copy()

        logger.info(
            "data_validator_initialized",
            thresholds=self.thresholds,
        )

    def validate_ohlcv_series(
        self,
        series: OHLCVSeries,
        check_freshness: bool = True,
        check_gaps: bool = True,
        check_price_changes: bool = True,
    ) -> ValidationResult:
        """Validate an OHLCV series for data quality.

        PRD Feature H implementation.

        Args:
            series: OHLCV series to validate.
            check_freshness: Whether to check if data is fresh (< 10s old).
            check_gaps: Whether to check for missing candles.
            check_price_changes: Whether to check for extreme price changes.

        Returns:
            ValidationResult with validation status and recommended action.
        """
        issues: list[str] = []
        warnings: list[str] = []
        metadata: dict[str, Any] = {
            "symbol": series.symbol,
            "timeframe": series.timeframe,
            "candle_count": len(series),
        }

        # Check minimum data
        if len(series) == 0:
            issues.append("No data provided")
            return ValidationResult(
                is_valid=False,
                issues=issues,
                warnings=warnings,
                action=ACTION_REJECT,
                metadata=metadata,
            )

        # PRD Feature H: Check price age (< 10 seconds old)
        if check_freshness:
            freshness_result = self._check_price_freshness(series)
            if freshness_result["is_stale"]:
                issues.append(freshness_result["message"])
                metadata["price_age_seconds"] = freshness_result["age_seconds"]

                logger.warning(
                    "stale_price_detected",
                    symbol=series.symbol,
                    age_seconds=freshness_result["age_seconds"],
                    threshold=self.thresholds["max_price_age_seconds"],
                )

        # PRD Feature H: Check for extreme price changes (> 10%)
        if check_price_changes:
            price_change_results = self._check_price_changes(series)
            if price_change_results["has_outliers"]:
                for outlier in price_change_results["outliers"]:
                    warnings.append(
                        f"Extreme price change detected: {outlier['change_pct']:.1f}% "
                        f"at candle index {outlier['index']}"
                    )
                    logger.warning(
                        "extreme_price_change",
                        symbol=series.symbol,
                        candle_index=outlier["index"],
                        change_pct=outlier["change_pct"],
                        threshold=self.thresholds["max_price_change_pct"],
                        timestamp=series.candles[outlier["index"]].timestamp.isoformat(),
                    )

                metadata["outliers"] = price_change_results["outliers"]

        # PRD Feature H: Check for gaps in timestamps
        if check_gaps:
            gap_result = self._check_gaps(series)
            if gap_result["has_gaps"]:
                max_gap = gap_result["max_gap_size"]
                metadata["gaps"] = gap_result["gaps"]
                metadata["max_gap_size"] = max_gap

                if max_gap >= self.thresholds["max_gap_candles"]:
                    # Large gap - pause strategy
                    issues.append(
                        f"Large gap detected: {max_gap} missing candles "
                        f"(threshold: {self.thresholds['max_gap_candles']})"
                    )

                    logger.error(
                        "large_gap_detected",
                        symbol=series.symbol,
                        gap_size=max_gap,
                        threshold=self.thresholds["max_gap_candles"],
                        action="pause_strategy",
                    )

                    return ValidationResult(
                        is_valid=False,
                        issues=issues,
                        warnings=warnings,
                        action=ACTION_PAUSE,  # PRD Feature H: Pause on large gap
                        metadata=metadata,
                    )
                else:
                    # Small gap - interpolate
                    warnings.append(
                        f"Small gap detected: {max_gap} missing candles "
                        f"(will interpolate)"
                    )

                    logger.info(
                        "small_gap_detected",
                        symbol=series.symbol,
                        gap_size=max_gap,
                        action="interpolate",
                    )

                    return ValidationResult(
                        is_valid=True,
                        issues=issues,
                        warnings=warnings,
                        action=ACTION_INTERPOLATE,  # PRD Feature H: Interpolate small gaps
                        metadata=metadata,
                    )

        # Determine final action
        if issues:
            action = ACTION_REJECT
            is_valid = False
        elif warnings:
            action = ACTION_USE  # Warnings don't block usage
            is_valid = True
        else:
            action = ACTION_USE
            is_valid = True

        logger.debug(
            "validation_completed",
            symbol=series.symbol,
            is_valid=is_valid,
            action=action,
            issues_count=len(issues),
            warnings_count=len(warnings),
        )

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            warnings=warnings,
            action=action,
            metadata=metadata,
        )

    def _check_price_freshness(self, series: OHLCVSeries) -> dict[str, Any]:
        """Check if price data is fresh (< 10 seconds old).

        PRD Feature H: Stale data check.

        Args:
            series: OHLCV series to check.

        Returns:
            Dictionary with keys:
            - is_stale (bool): Whether data is stale
            - age_seconds (float): Age of latest candle in seconds
            - message (str): Error message if stale
        """
        latest_candle = series.candles[-1]
        now = datetime.now(timezone.utc)
        age = now - latest_candle.timestamp
        age_seconds = age.total_seconds()

        is_stale = age_seconds > float(self.thresholds["max_price_age_seconds"])

        message = ""
        if is_stale:
            message = (
                f"Price is stale ({age_seconds:.1f}s old, "
                f"max {self.thresholds['max_price_age_seconds']}s)"
            )

        return {
            "is_stale": is_stale,
            "age_seconds": age_seconds,
            "message": message,
        }

    def _check_price_changes(self, series: OHLCVSeries) -> dict[str, Any]:
        """Check for extreme price changes (> 10% in single candle).

        PRD Feature H: Outlier detection.

        Args:
            series: OHLCV series to check.

        Returns:
            Dictionary with keys:
            - has_outliers (bool): Whether outliers found
            - outliers (list): List of outlier dictionaries
        """
        outliers: list[dict[str, Any]] = []

        # Check price changes between consecutive candles
        for i in range(1, len(series)):
            prev_close = series.candles[i - 1].close
            curr_open = series.candles[i].open

            if prev_close <= 0:
                # Skip if previous close is zero or negative
                continue

            # Calculate percentage change
            change_pct = abs((curr_open - prev_close) / prev_close) * 100.0

            if change_pct > float(self.thresholds["max_price_change_pct"]):
                outliers.append(
                    {
                        "index": i,
                        "prev_close": prev_close,
                        "curr_open": curr_open,
                        "change_pct": round(change_pct, 2),
                        "timestamp": series.candles[i].timestamp.isoformat(),
                    }
                )

        return {
            "has_outliers": len(outliers) > 0,
            "outliers": outliers,
        }

    def _check_gaps(self, series: OHLCVSeries) -> dict[str, Any]:
        """Check for gaps in timestamp sequence.

        PRD Feature H: Gap detection.

        This method estimates expected candle intervals based on timeframe
        and checks for missing candles.

        Args:
            series: OHLCV series to check.

        Returns:
            Dictionary with keys:
            - has_gaps (bool): Whether gaps found
            - gaps (list): List of gap dictionaries
            - max_gap_size (int): Size of largest gap in candles
        """
        if len(series) < 2:
            # Need at least 2 candles to check gaps
            return {
                "has_gaps": False,
                "gaps": [],
                "max_gap_size": 0,
            }

        # Parse timeframe to get expected interval
        expected_interval = self._parse_timeframe_to_seconds(series.timeframe)

        if expected_interval is None:
            # Unknown timeframe, skip gap detection
            logger.warning(
                "unknown_timeframe_for_gap_detection",
                timeframe=series.timeframe,
            )
            return {
                "has_gaps": False,
                "gaps": [],
                "max_gap_size": 0,
            }

        gaps: list[dict[str, Any]] = []
        max_gap_size = 0

        # Check intervals between consecutive candles
        for i in range(1, len(series)):
            prev_candle = series.candles[i - 1]
            curr_candle = series.candles[i]

            # Calculate actual interval
            actual_interval = (curr_candle.timestamp - prev_candle.timestamp).total_seconds()

            # Calculate missing candles (allowing 10% tolerance for timing variations)
            tolerance = expected_interval * 0.1
            if actual_interval > expected_interval + tolerance:
                missing_candles = int(round(actual_interval / expected_interval)) - 1

                if missing_candles > 0:
                    gaps.append(
                        {
                            "before_index": i - 1,
                            "after_index": i,
                            "gap_size": missing_candles,
                            "before_timestamp": prev_candle.timestamp.isoformat(),
                            "after_timestamp": curr_candle.timestamp.isoformat(),
                            "actual_interval_seconds": actual_interval,
                            "expected_interval_seconds": expected_interval,
                        }
                    )

                    max_gap_size = max(max_gap_size, missing_candles)

        return {
            "has_gaps": len(gaps) > 0,
            "gaps": gaps,
            "max_gap_size": max_gap_size,
        }

    def _parse_timeframe_to_seconds(self, timeframe: str) -> int | None:
        """Parse timeframe string to seconds.

        Supports: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w

        Args:
            timeframe: Timeframe string (e.g., "1m", "1h", "1d").

        Returns:
            Interval in seconds, or None if parsing fails.
        """
        timeframe = timeframe.lower()

        # Minutes
        if timeframe.endswith("m"):
            try:
                minutes = int(timeframe[:-1])
                return minutes * 60
            except ValueError:
                return None

        # Hours
        if timeframe.endswith("h"):
            try:
                hours = int(timeframe[:-1])
                return hours * 3600
            except ValueError:
                return None

        # Days
        if timeframe.endswith("d"):
            try:
                days = int(timeframe[:-1])
                return days * 86400
            except ValueError:
                return None

        # Weeks
        if timeframe.endswith("w"):
            try:
                weeks = int(timeframe[:-1])
                return weeks * 604800
            except ValueError:
                return None

        return None

    def validate_single_candle(self, candle: OHLCV) -> ValidationResult:
        """Validate a single OHLCV candle.

        Checks:
        - Required fields present
        - No NaN/Infinity values
        - Valid OHLC relationships

        Note: The OHLCV dataclass already validates these on construction,
        so this method mainly provides a standardized ValidationResult.

        Args:
            candle: OHLCV candle to validate.

        Returns:
            ValidationResult indicating if candle is valid.
        """
        issues: list[str] = []
        warnings: list[str] = []

        # Check for NaN values
        for field_name in REQUIRED_FIELDS:
            value = getattr(candle, field_name)

            if value is None:
                issues.append(f"{field_name} is None")
            elif math.isnan(value):
                issues.append(f"{field_name} is NaN")
            elif math.isinf(value):
                issues.append(f"{field_name} is Infinity")
            elif value < 0:
                issues.append(f"{field_name} is negative ({value})")

        # Check OHLC relationships (already validated by dataclass, but double-check)
        if candle.high < candle.low:
            issues.append(f"High ({candle.high}) < Low ({candle.low})")

        if candle.open < candle.low or candle.open > candle.high:
            issues.append(f"Open ({candle.open}) outside High/Low range")

        if candle.close < candle.low or candle.close > candle.high:
            issues.append(f"Close ({candle.close}) outside High/Low range")

        is_valid = len(issues) == 0

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            warnings=warnings,
            action=ACTION_USE if is_valid else ACTION_REJECT,
            metadata={
                "timestamp": candle.timestamp.isoformat(),
            },
        )

    def set_threshold(self, key: str, value: float | int | str) -> None:
        """Update a validation threshold.

        Args:
            key: Threshold key (e.g., "max_price_age_seconds").
            value: New threshold value.

        Raises:
            ValueError: If key is invalid.
        """
        if key not in self.thresholds:
            raise ValueError(
                f"Invalid threshold key: {key}. "
                f"Valid keys: {list(self.thresholds.keys())}"
            )

        old_value = self.thresholds[key]
        self.thresholds[key] = value

        logger.info(
            "threshold_updated",
            key=key,
            old_value=old_value,
            new_value=value,
        )

    def get_thresholds(self) -> dict[str, float | int | str]:
        """Get current validation thresholds.

        Returns:
            Dictionary of threshold key-value pairs.
        """
        return self.thresholds.copy()
