"""Shared pytest fixtures."""
import pytest
from pathlib import Path


@pytest.fixture
def sample_ohlcv_data():
    """Sample OHLCV data for testing."""
    return [
        {
            "timestamp": 1704067200000,
            "open": 42000,
            "high": 42500,
            "low": 41800,
            "close": 42300,
            "volume": 100,
        },
        {
            "timestamp": 1704070800000,
            "open": 42300,
            "high": 42800,
            "low": 42100,
            "close": 42600,
            "volume": 150,
        },
        {
            "timestamp": 1704074400000,
            "open": 42600,
            "high": 42900,
            "low": 42400,
            "close": 42700,
            "volume": 120,
        },
    ]


@pytest.fixture
def test_config_path(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def mock_binance_client(mocker):
    """Mock Binance client for testing."""
    return mocker.MagicMock()
