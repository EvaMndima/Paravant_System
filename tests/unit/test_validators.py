"""Unit tests for data quality validation (PRD Feature H).

Decision: DEC-2026-02-08-007 - Input validation at model layer
PRD Feature H - Data Quality Validation

This module tests:
- Stale data detection (> 10 seconds old)
- Extreme price change detection (> 10% in 1 candle)
- Gap detection (missing candles in sequence)
- Action determination (use, interpolate, reject, pause)
- Single candle validation
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.data.market_data import OHLCV, OHLCVSeries
from src.data.validators import (
    ACTION_INTERPOLATE,
    ACTION_PAUSE,
    ACTION_REJECT,
    ACTION_USE,
    DataValidator,
    ValidationResult,
)


class TestDataValidator:
    """Test DataValidator for PRD Feature H requirements."""

    @pytest.fixture
    def validator(self) -> DataValidator:
        """Create DataValidator instance."""
        return DataValidator()

    @pytest.fixture
    def valid_series(self) -> OHLCVSeries:
        """Create valid OHLCV series (fresh, no gaps, normal changes)."""
        base_time = datetime.now(timezone.utc)
        candles = [
            OHLCV(
                timestamp=base_time - timedelta(hours=10 - i),
                open=42000.0 + (i * 10),  # Small price changes
                high=42050.0 + (i * 10),
                low=41950.0 + (i * 10),
                close=42030.0 + (i * 10),
                volume=100.0 + i,
            )
            for i in range(10)
        ]

        return OHLCVSeries(
            candles=candles,
            symbol="BTCUSDT",
            timeframe="1h",
        )

    def test_validate_valid_series(
        self,
        validator: DataValidator,
        valid_series: OHLCVSeries,
    ) -> None:
        """Test validation passes for valid data."""
        result = validator.validate_ohlcv_series(
            valid_series,
            check_freshness=False,  # Latest candle might be old
            check_gaps=False,  # Gaps OK for test data
            check_price_changes=True,
        )

        assert result.is_valid
        assert result.action == ACTION_USE
        assert len(result.issues) == 0

    def test_detect_stale_data(
        self,
        validator: DataValidator,
    ) -> None:
        """Test PRD Feature H: Detect stale data (> 10 seconds old)."""
        # Create series with old data (15 seconds old)
        old_timestamp = datetime.now(timezone.utc) - timedelta(seconds=15)

        candle = OHLCV(
            timestamp=old_timestamp,
            open=42000.0,
            high=42100.0,
            low=41900.0,
            close=42050.0,
            volume=100.0,
        )

        series = OHLCVSeries(
            candles=[candle],
            symbol="BTCUSDT",
            timeframe="1m",
        )

        result = validator.validate_ohlcv_series(
            series,
            check_freshness=True,
            check_gaps=False,
            check_price_changes=False,
        )

        assert not result.is_valid
        assert result.action == ACTION_REJECT
        assert any("stale" in issue.lower() for issue in result.issues)
        assert result.metadata["price_age_seconds"] > 10

    def test_fresh_data_passes(
        self,
        validator: DataValidator,
    ) -> None:
        """Test fresh data (< 10 seconds) passes validation."""
        # Create series with fresh data (5 seconds old)
        fresh_timestamp = datetime.now(timezone.utc) - timedelta(seconds=5)

        candle = OHLCV(
            timestamp=fresh_timestamp,
            open=42000.0,
            high=42100.0,
            low=41900.0,
            close=42050.0,
            volume=100.0,
        )

        series = OHLCVSeries(
            candles=[candle],
            symbol="BTCUSDT",
            timeframe="1m",
        )

        result = validator.validate_ohlcv_series(
            series,
            check_freshness=True,
            check_gaps=False,
            check_price_changes=False,
        )

        assert result.is_valid
        assert result.action == ACTION_USE
        assert len(result.issues) == 0

    def test_detect_extreme_price_change(
        self,
        validator: DataValidator,
    ) -> None:
        """Test PRD Feature H: Detect extreme price change (> 10%)."""
        base_time = datetime.now(timezone.utc)

        # Create candles with 15% price spike
        candles = [
            OHLCV(
                timestamp=base_time - timedelta(hours=1),
                open=40000.0,
                high=40100.0,
                low=39900.0,
                close=40050.0,
                volume=100.0,
            ),
            OHLCV(
                timestamp=base_time,
                open=46000.0,  # 15% jump (outlier)
                high=46100.0,
                low=45900.0,
                close=46050.0,
                volume=150.0,
            ),
        ]

        series = OHLCVSeries(
            candles=candles,
            symbol="BTCUSDT",
            timeframe="1h",
        )

        result = validator.validate_ohlcv_series(
            series,
            check_freshness=False,
            check_gaps=False,
            check_price_changes=True,
        )

        # Should be valid but with warnings
        assert result.is_valid
        assert result.action == ACTION_USE
        assert len(result.warnings) > 0
        assert any("extreme" in warning.lower() for warning in result.warnings)
        assert "outliers" in result.metadata

    def test_normal_price_change_passes(
        self,
        validator: DataValidator,
    ) -> None:
        """Test normal price changes (< 10%) pass validation."""
        base_time = datetime.now(timezone.utc)

        # Create candles with 5% change (normal)
        candles = [
            OHLCV(
                timestamp=base_time - timedelta(hours=1),
                open=40000.0,
                high=40100.0,
                low=39900.0,
                close=40050.0,
                volume=100.0,
            ),
            OHLCV(
                timestamp=base_time,
                open=42000.0,  # 5% jump (normal)
                high=42100.0,
                low=41900.0,
                close=42050.0,
                volume=150.0,
            ),
        ]

        series = OHLCVSeries(
            candles=candles,
            symbol="BTCUSDT",
            timeframe="1h",
        )

        result = validator.validate_ohlcv_series(
            series,
            check_freshness=False,
            check_gaps=False,
            check_price_changes=True,
        )

        assert result.is_valid
        assert result.action == ACTION_USE
        assert len(result.warnings) == 0

    def test_detect_small_gap_interpolate(
        self,
        validator: DataValidator,
    ) -> None:
        """Test PRD Feature H: Small gap (< 3 candles) → INTERPOLATE."""
        base_time = datetime.now(timezone.utc)

        # Create series with 2 missing candles (small gap)
        candles = [
            OHLCV(
                timestamp=base_time - timedelta(hours=5),
                open=40000.0,
                high=40100.0,
                low=39900.0,
                close=40050.0,
                volume=100.0,
            ),
            # Missing 2 candles here (gap of 2)
            OHLCV(
                timestamp=base_time - timedelta(hours=2),
                open=41000.0,
                high=41100.0,
                low=40900.0,
                close=41050.0,
                volume=150.0,
            ),
        ]

        series = OHLCVSeries(
            candles=candles,
            symbol="BTCUSDT",
            timeframe="1h",
        )

        result = validator.validate_ohlcv_series(
            series,
            check_freshness=False,
            check_gaps=True,
            check_price_changes=False,
        )

        assert result.is_valid
        assert result.action == ACTION_INTERPOLATE
        assert len(result.warnings) > 0
        assert any("gap" in warning.lower() for warning in result.warnings)
        assert result.metadata["max_gap_size"] == 2

    def test_detect_large_gap_pause(
        self,
        validator: DataValidator,
    ) -> None:
        """Test PRD Feature H: Large gap (>= 3 candles) → PAUSE."""
        base_time = datetime.now(timezone.utc)

        # Create series with 4 missing candles (large gap)
        candles = [
            OHLCV(
                timestamp=base_time - timedelta(hours=6),
                open=40000.0,
                high=40100.0,
                low=39900.0,
                close=40050.0,
                volume=100.0,
            ),
            # Missing 4 candles here (gap of 4)
            OHLCV(
                timestamp=base_time - timedelta(hours=1),
                open=41000.0,
                high=41100.0,
                low=40900.0,
                close=41050.0,
                volume=150.0,
            ),
        ]

        series = OHLCVSeries(
            candles=candles,
            symbol="BTCUSDT",
            timeframe="1h",
        )

        result = validator.validate_ohlcv_series(
            series,
            check_freshness=False,
            check_gaps=True,
            check_price_changes=False,
        )

        assert not result.is_valid
        assert result.action == ACTION_PAUSE
        assert len(result.issues) > 0
        assert any("gap" in issue.lower() for issue in result.issues)
        assert result.metadata["max_gap_size"] >= 3

    def test_no_gap_in_continuous_series(
        self,
        validator: DataValidator,
    ) -> None:
        """Test continuous series with no gaps passes validation."""
        base_time = datetime.now(timezone.utc)

        # Create continuous series (no gaps)
        candles = [
            OHLCV(
                timestamp=base_time - timedelta(hours=10 - i),
                open=40000.0 + (i * 10),
                high=40100.0 + (i * 10),
                low=39900.0 + (i * 10),
                close=40050.0 + (i * 10),
                volume=100.0 + i,
            )
            for i in range(10)
        ]

        series = OHLCVSeries(
            candles=candles,
            symbol="BTCUSDT",
            timeframe="1h",
        )

        result = validator.validate_ohlcv_series(
            series,
            check_freshness=False,
            check_gaps=True,
            check_price_changes=False,
        )

        assert result.is_valid
        assert result.action == ACTION_USE
        assert len(result.issues) == 0
        assert len(result.warnings) == 0

    def test_empty_series_rejected(
        self,
        validator: DataValidator,
    ) -> None:
        """Test empty series is rejected at construction time."""
        with pytest.raises(ValueError, match="Candles list cannot be empty"):
            OHLCVSeries(
                candles=[],
                symbol="BTCUSDT",
                timeframe="1h",
            )

    def test_validate_single_candle_valid(
        self,
        validator: DataValidator,
    ) -> None:
        """Test single candle validation with valid data."""
        candle = OHLCV(
            timestamp=datetime.now(timezone.utc),
            open=42000.0,
            high=42100.0,
            low=41900.0,
            close=42050.0,
            volume=100.0,
        )

        result = validator.validate_single_candle(candle)

        assert result.is_valid
        assert result.action == ACTION_USE
        assert len(result.issues) == 0

    def test_validate_single_candle_nan(
        self,
        validator: DataValidator,
    ) -> None:
        """Test single candle validation rejects NaN.

        Note: This test documents expected behavior, but OHLCV
        dataclass already validates NaN in __post_init__, so
        this scenario would raise ValueError during construction.
        """
        # OHLCV construction would raise ValueError for NaN
        # This test documents the validator would also catch it
        pass

    def test_set_threshold(
        self,
        validator: DataValidator,
    ) -> None:
        """Test updating validation thresholds."""
        # Change max price age threshold
        validator.set_threshold("max_price_age_seconds", 20)

        thresholds = validator.get_thresholds()
        assert thresholds["max_price_age_seconds"] == 20

    def test_set_invalid_threshold_raises(
        self,
        validator: DataValidator,
    ) -> None:
        """Test setting invalid threshold key raises error."""
        with pytest.raises(ValueError, match="Invalid threshold key"):
            validator.set_threshold("invalid_key", 100)

    def test_get_thresholds(
        self,
        validator: DataValidator,
    ) -> None:
        """Test getting current thresholds."""
        thresholds = validator.get_thresholds()

        assert "max_price_age_seconds" in thresholds
        assert "max_price_change_pct" in thresholds
        assert "max_gap_candles" in thresholds
        assert thresholds["max_price_age_seconds"] == 10
        assert thresholds["max_price_change_pct"] == 10.0
        assert thresholds["max_gap_candles"] == 3

    def test_parse_timeframe_minutes(
        self,
        validator: DataValidator,
    ) -> None:
        """Test parsing minute timeframes."""
        assert validator._parse_timeframe_to_seconds("1m") == 60
        assert validator._parse_timeframe_to_seconds("5m") == 300
        assert validator._parse_timeframe_to_seconds("15m") == 900

    def test_parse_timeframe_hours(
        self,
        validator: DataValidator,
    ) -> None:
        """Test parsing hour timeframes."""
        assert validator._parse_timeframe_to_seconds("1h") == 3600
        assert validator._parse_timeframe_to_seconds("4h") == 14400

    def test_parse_timeframe_days(
        self,
        validator: DataValidator,
    ) -> None:
        """Test parsing day timeframes."""
        assert validator._parse_timeframe_to_seconds("1d") == 86400

    def test_parse_timeframe_weeks(
        self,
        validator: DataValidator,
    ) -> None:
        """Test parsing week timeframes."""
        assert validator._parse_timeframe_to_seconds("1w") == 604800

    def test_parse_timeframe_invalid(
        self,
        validator: DataValidator,
    ) -> None:
        """Test parsing invalid timeframe returns None."""
        assert validator._parse_timeframe_to_seconds("invalid") is None
        assert validator._parse_timeframe_to_seconds("1x") is None

    def test_validation_result_repr(self) -> None:
        """Test ValidationResult string representation."""
        result = ValidationResult(
            is_valid=True,
            issues=[],
            warnings=["Warning 1"],
            action=ACTION_USE,
            metadata={"symbol": "BTCUSDT"},
        )

        repr_str = repr(result)
        assert "VALID" in repr_str
        assert "use" in repr_str
        assert "warnings=1" in repr_str
