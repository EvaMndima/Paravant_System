"""Comprehensive unit tests for PaperTradingThresholds and PaperTradingValidator."""
from __future__ import annotations

import pytest

from src.core.strategy.paper.validator import PaperTradingThresholds


# ---------------------------------------------------------------------------
# PaperTradingThresholds Tests
# ---------------------------------------------------------------------------


class TestPaperTradingThresholds:
    """Tests for PaperTradingThresholds."""

    def test_default_values(self) -> None:
        """Default thresholds should be more lenient than backtest."""
        t = PaperTradingThresholds()
        assert t.min_sharpe_ratio == 0.3
        assert t.max_drawdown_pct == 20.0
        assert t.min_win_rate_pct == 30.0
        assert t.min_num_trades == 10
        assert t.min_days_simulated == 14.0
        assert t.min_days_live == 7.0

    def test_custom_values(self) -> None:
        """Custom thresholds should be accepted."""
        t = PaperTradingThresholds(
            min_sharpe_ratio=0.5,
            max_drawdown_pct=10.0,
            min_num_trades=20,
        )
        assert t.min_sharpe_ratio == 0.5
        assert t.max_drawdown_pct == 10.0
        assert t.min_num_trades == 20

    def test_frozen(self) -> None:
        """Thresholds should be immutable."""
        t = PaperTradingThresholds()
        with pytest.raises(AttributeError):
            t.min_sharpe_ratio = 99.0  # type: ignore[misc]

    def test_simulated_stricter_than_live_on_duration(self) -> None:
        """Simulated min days should be greater than live min days."""
        t = PaperTradingThresholds()
        assert t.min_days_simulated > t.min_days_live


# Note: PaperTradingValidator.validate requires a fully constructed
# PaperTradingEngine with a running session, which is complex to set up
# as a unit test. The validator logic is exercised through the backtest
# metrics calculator tests and integration tests.
# Here we focus on threshold behavior and data types.
