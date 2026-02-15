"""Comprehensive unit tests for PaperTradingStatus and PaperTradingMode."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.strategy.paper.types import PaperTradingMode, PaperTradingStatus


# ---------------------------------------------------------------------------
# PaperTradingMode Tests
# ---------------------------------------------------------------------------


class TestPaperTradingMode:
    """Tests for PaperTradingMode enum."""

    def test_simulated_value(self) -> None:
        """SIMULATED should have string value 'simulated'."""
        assert PaperTradingMode.SIMULATED.value == "simulated"

    def test_live_value(self) -> None:
        """LIVE should have string value 'live'."""
        assert PaperTradingMode.LIVE.value == "live"

    def test_from_string(self) -> None:
        """Should be constructible from string values."""
        assert PaperTradingMode("simulated") == PaperTradingMode.SIMULATED
        assert PaperTradingMode("live") == PaperTradingMode.LIVE

    def test_invalid_mode(self) -> None:
        """Invalid mode string should raise ValueError."""
        with pytest.raises(ValueError):
            PaperTradingMode("invalid")


# ---------------------------------------------------------------------------
# PaperTradingStatus Tests
# ---------------------------------------------------------------------------


class TestPaperTradingStatus:
    """Tests for PaperTradingStatus frozen dataclass."""

    @pytest.fixture
    def running_status(self) -> PaperTradingStatus:
        """Create a running status."""
        return PaperTradingStatus(
            mode=PaperTradingMode.SIMULATED,
            strategy_id="test-001",
            strategy_name="TestStrategy",
            is_running=True,
            started_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            current_equity=10500.0,
            initial_capital=10000.0,
            current_pnl=500.0,
            current_pnl_pct=5.0,
            num_trades=10,
            days_elapsed=7.5,
        )

    @pytest.fixture
    def stopped_status(self) -> PaperTradingStatus:
        """Create a stopped status."""
        return PaperTradingStatus(
            mode=PaperTradingMode.LIVE,
            strategy_id="test-002",
            strategy_name="LiveStrategy",
            is_running=False,
            started_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            stopped_at=datetime(2025, 1, 8, 10, 0, tzinfo=timezone.utc),
            current_equity=9800.0,
            initial_capital=10000.0,
            current_pnl=-200.0,
            current_pnl_pct=-2.0,
            num_trades=5,
            days_elapsed=7.0,
        )

    def test_default_values(self) -> None:
        """Defaults should have sensible values."""
        status = PaperTradingStatus(
            mode=PaperTradingMode.SIMULATED,
            strategy_id="s1",
            strategy_name="Test",
        )
        assert status.is_running is False
        assert status.started_at is None
        assert status.stopped_at is None
        assert status.current_equity == 0.0
        assert status.initial_capital == 10_000.0
        assert status.num_trades == 0
        assert status.days_elapsed == 0.0
        assert status.validation_passed is False
        assert status.validation_errors == []

    def test_to_dict_running(self, running_status: PaperTradingStatus) -> None:
        """to_dict should serialize running status."""
        d = running_status.to_dict()
        assert d["mode"] == "simulated"
        assert d["strategy_id"] == "test-001"
        assert d["is_running"] is True
        assert d["started_at"] is not None
        assert d["stopped_at"] is None
        assert d["current_equity"] == 10500.0
        assert d["num_trades"] == 10

    def test_to_dict_stopped(self, stopped_status: PaperTradingStatus) -> None:
        """to_dict should serialize stopped status with stopped_at."""
        d = stopped_status.to_dict()
        assert d["mode"] == "live"
        assert d["is_running"] is False
        assert d["stopped_at"] is not None
        assert d["current_pnl"] == -200.0

    def test_frozen(self, running_status: PaperTradingStatus) -> None:
        """Status should be immutable."""
        with pytest.raises(AttributeError):
            running_status.is_running = False  # type: ignore[misc]

    def test_validation_errors(self) -> None:
        """Validation errors should be preserved."""
        status = PaperTradingStatus(
            mode=PaperTradingMode.SIMULATED,
            strategy_id="s1",
            strategy_name="Test",
            validation_passed=False,
            validation_errors=["Win rate too low", "Too few trades"],
        )
        assert len(status.validation_errors) == 2
        assert "Win rate too low" in status.validation_errors
