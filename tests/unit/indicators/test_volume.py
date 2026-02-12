"""Tests for Volume Average indicator.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.indicators import VolumeAverage
from src.data.market_data import OHLCVSeries
from tests.unit.indicators.conftest import (assert_array_not_all_nan,
                                            assert_first_n_nan)


class TestVolumeAverage:
    """Tests for Volume Average indicator."""

    def test_init_default_period(self) -> None:
        """Test Volume Average initialization with default period."""
        vol = VolumeAverage()

        assert vol.period == 20

    def test_init_custom_period(self) -> None:
        """Test Volume Average initialization with custom period."""
        vol = VolumeAverage(period=50)

        assert vol.period == 50

    def test_init_invalid_period_raises(self) -> None:
        """Test Volume Average raises ValueError for invalid period."""
        with pytest.raises(ValueError, match="Period must be >= 1"):
            VolumeAverage(period=0)

    def test_calculate_basic(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test basic Volume Average calculation."""
        vol = VolumeAverage()
        result = vol.calculate(sample_ohlcv_series)

        assert result.name == "VOL_AVG_20"
        assert len(result.values) == len(sample_ohlcv_series)
        assert result.params["period"] == 20

    def test_calculate_warmup_period(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test NaN warmup for first period-1 values."""
        vol = VolumeAverage(period=20)
        result = vol.calculate(sample_ohlcv_series)

        assert_first_n_nan(result.values, 19, "VolumeAverage warmup")
        assert_array_not_all_nan(result.values, "VolumeAverage")

    def test_calculate_is_sma_of_volume(
        self, sample_ohlcv_series: OHLCVSeries
    ) -> None:
        """Test volume average equals SMA of volume (manual verification)."""
        vol = VolumeAverage(period=5)
        result = vol.calculate(sample_ohlcv_series)

        volumes = sample_ohlcv_series.volumes

        # Manually verify a few values
        for i in range(4, min(10, len(volumes))):
            expected_avg = np.mean(volumes[i - 4 : i + 1])
            assert result.values[i] == pytest.approx(expected_avg, rel=1e-6), (
                f"Vol avg[{i}] should be SMA of volume"
            )

    def test_positive_values(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test volume average values are positive."""
        vol = VolumeAverage()
        result = vol.calculate(sample_ohlcv_series)

        valid = result.values[~np.isnan(result.values)]
        assert np.all(valid > 0), "Volume average should be positive"

    def test_is_volume_spike(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test volume spike detection returns bool."""
        vol = VolumeAverage()
        result = vol.calculate(sample_ohlcv_series)

        spike = VolumeAverage.is_volume_spike(
            sample_ohlcv_series.volumes, result.values, multiplier=1.5
        )
        assert isinstance(spike, bool)

    def test_is_volume_spike_invalid_multiplier_raises(
        self, sample_ohlcv_series: OHLCVSeries
    ) -> None:
        """Test volume spike raises ValueError for invalid multiplier."""
        vol = VolumeAverage()
        result = vol.calculate(sample_ohlcv_series)

        with pytest.raises(ValueError, match="Multiplier must be > 0"):
            VolumeAverage.is_volume_spike(
                sample_ohlcv_series.volumes, result.values, multiplier=0
            )

    def test_is_volume_spike_no_valid_raises(self) -> None:
        """Test volume spike raises ValueError when no valid averages."""
        volumes = np.array([100.0, 200.0, 300.0])
        avg_volumes = np.array([np.nan, np.nan, np.nan])

        with pytest.raises(ValueError, match="No valid volume average"):
            VolumeAverage.is_volume_spike(volumes, avg_volumes, multiplier=1.5)

    def test_volume_ratio(self) -> None:
        """Test volume ratio calculation."""
        ratio = VolumeAverage.volume_ratio(current=200.0, avg=100.0)

        assert ratio == pytest.approx(2.0)

    def test_volume_ratio_zero_avg_raises(self) -> None:
        """Test volume ratio raises ValueError for zero average."""
        with pytest.raises(ValueError, match="Average volume cannot be zero"):
            VolumeAverage.volume_ratio(current=100.0, avg=0)

    def test_calculate_insufficient_data_raises(
        self, minimal_series: OHLCVSeries
    ) -> None:
        """Test Volume Average raises ValueError with insufficient data."""
        vol = VolumeAverage(period=20)

        with pytest.raises(ValueError, match="requires at least 20 bars"):
            vol.calculate(minimal_series)

    def test_current_and_previous(self, sample_ohlcv_series: OHLCVSeries) -> None:
        """Test current and previous properties."""
        vol = VolumeAverage()
        result = vol.calculate(sample_ohlcv_series)

        current = result.current
        previous = result.previous

        assert isinstance(current, float)
        assert isinstance(previous, float)

    def test_repr(self) -> None:
        """Test string representation."""
        vol = VolumeAverage(period=50)
        repr_str = repr(vol)

        assert "VolumeAverage" in repr_str
        assert "50" in repr_str
