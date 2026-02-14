"""Tests for position management API endpoints.

Tests all position routes including list, get, close, and staleness
analysis with mocked PositionTracker dependency.

Phase 4B: Position Tracking & Execution Quality
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.positions import (
    init_position_routes,
    router,
)
from src.core.execution.position_tracker import PositionTracker, StalenessResult
from src.data.models.position import PositionSide, PositionStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_position(
    symbol: str = "BTCUSDT",
    side: PositionSide = PositionSide.LONG,
    size: float = 0.5,
    entry_price: float = 45000.0,
    current_price: float = 46000.0,
    commission_paid: float = 5.0,
    pnl_usdt: float = 0.0,
    pnl_pct: float = 0.0,
    status: PositionStatus = PositionStatus.OPEN,
) -> MagicMock:
    """Create a mock position for API tests."""
    pos = MagicMock()
    pos.id = "pos_test_123"
    pos.account_id = "acc_test"
    pos.strategy_id = "strat_test"
    pos.symbol = symbol
    pos.side = side
    pos.size = size
    pos.entry_price = entry_price
    pos.current_price = current_price
    pos.commission_paid = commission_paid
    pos.pnl_usdt = pnl_usdt
    pos.pnl_pct = pnl_pct
    pos.status = status
    pos.opened_at = datetime.now(timezone.utc)
    pos.closed_at = None
    pos.exit_price = None
    return pos


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_tracker() -> MagicMock:
    """Create a mock PositionTracker."""
    tracker = MagicMock(spec=PositionTracker)
    tracker.get_all_positions = AsyncMock(return_value=[])
    tracker.get_position = AsyncMock(return_value=None)
    tracker.process_stale_positions = AsyncMock(return_value=[])
    # Static methods
    tracker.calculate_unrealized_pnl = MagicMock(return_value=500.0)
    tracker.calculate_return_pct = MagicMock(return_value=2.2)
    return tracker


@pytest.fixture
def app(mock_tracker: MagicMock) -> FastAPI:
    """Create a FastAPI test application with position routes."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/positions")
    init_position_routes(mock_tracker)
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests: List positions
# ---------------------------------------------------------------------------


class TestListPositions:
    """Tests for GET /api/v1/positions."""

    def test_list_empty(self, client: TestClient, mock_tracker: MagicMock) -> None:
        """Empty position list returns 200 with empty array."""
        mock_tracker.get_all_positions = AsyncMock(return_value=[])
        response = client.get("/api/v1/positions")
        assert response.status_code == 200
        data = response.json()
        assert data["positions"] == []
        assert data["total"] == 0

    def test_list_with_positions(self, client: TestClient, mock_tracker: MagicMock) -> None:
        """List returns positions with P&L calculations."""
        pos = _make_mock_position()
        mock_tracker.get_all_positions = AsyncMock(return_value=[pos])

        # Patch static method calls
        with patch.object(PositionTracker, "calculate_unrealized_pnl", return_value=500.0), \
             patch.object(PositionTracker, "calculate_return_pct", return_value=2.2):
            response = client.get("/api/v1/positions")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["positions"][0]["symbol"] == "BTCUSDT"

    def test_list_filter_by_symbol(self, client: TestClient, mock_tracker: MagicMock) -> None:
        """Filter positions by symbol."""
        pos1 = _make_mock_position(symbol="BTCUSDT")
        pos2 = _make_mock_position(symbol="ETHUSDT")
        mock_tracker.get_all_positions = AsyncMock(return_value=[pos1, pos2])

        with patch.object(PositionTracker, "calculate_unrealized_pnl", return_value=0.0), \
             patch.object(PositionTracker, "calculate_return_pct", return_value=0.0):
            response = client.get("/api/v1/positions?symbol=BTCUSDT")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["positions"][0]["symbol"] == "BTCUSDT"

    def test_list_filter_by_status(self, client: TestClient, mock_tracker: MagicMock) -> None:
        """Filter positions by status."""
        pos = _make_mock_position(status=PositionStatus.OPEN)
        mock_tracker.get_all_positions = AsyncMock(return_value=[pos])

        with patch.object(PositionTracker, "calculate_unrealized_pnl", return_value=0.0), \
             patch.object(PositionTracker, "calculate_return_pct", return_value=0.0):
            response = client.get("/api/v1/positions?status=open")

        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_list_invalid_status(self, client: TestClient, mock_tracker: MagicMock) -> None:
        """Invalid status filter returns 400."""
        mock_tracker.get_all_positions = AsyncMock(return_value=[])
        response = client.get("/api/v1/positions?status=invalid_status")
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Tests: Get position by symbol
# ---------------------------------------------------------------------------


class TestGetPosition:
    """Tests for GET /api/v1/positions/{symbol}."""

    def test_get_found(self, client: TestClient, mock_tracker: MagicMock) -> None:
        """Get existing position returns 200."""
        pos = _make_mock_position()
        mock_tracker.get_position = AsyncMock(return_value=pos)

        with patch.object(PositionTracker, "calculate_unrealized_pnl", return_value=500.0), \
             patch.object(PositionTracker, "calculate_return_pct", return_value=2.2):
            response = client.get("/api/v1/positions/BTCUSDT")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTCUSDT"

    def test_get_not_found(self, client: TestClient, mock_tracker: MagicMock) -> None:
        """Missing position returns 404."""
        mock_tracker.get_position = AsyncMock(return_value=None)
        response = client.get("/api/v1/positions/XYZUSDT")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Close position
# ---------------------------------------------------------------------------


class TestClosePosition:
    """Tests for DELETE /api/v1/positions/{symbol}."""

    def test_close_found(self, client: TestClient, mock_tracker: MagicMock) -> None:
        """Close existing position returns 200."""
        pos = _make_mock_position()
        mock_tracker.get_position = AsyncMock(return_value=pos)

        response = client.delete("/api/v1/positions/BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "BTCUSDT" in data["message"]

    def test_close_not_found(self, client: TestClient, mock_tracker: MagicMock) -> None:
        """Close missing position returns 404."""
        mock_tracker.get_position = AsyncMock(return_value=None)
        response = client.delete("/api/v1/positions/XYZUSDT")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Staleness analysis
# ---------------------------------------------------------------------------


class TestStalenessAnalysis:
    """Tests for GET /api/v1/positions/analysis/staleness."""

    def test_staleness_empty(self, client: TestClient, mock_tracker: MagicMock) -> None:
        """No positions returns empty staleness."""
        mock_tracker.process_stale_positions = AsyncMock(return_value=[])
        response = client.get("/api/v1/positions/analysis/staleness")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_staleness_with_results(self, client: TestClient, mock_tracker: MagicMock) -> None:
        """Staleness analysis returns warnings/reviews/exceeded counts."""
        results = [
            StalenessResult(
                position_id="pos_1",
                symbol="BTCUSDT",
                hold_duration=timedelta(hours=25),
                should_warn=True,
                should_review=False,
                should_close=False,
                days_remaining=1.96,
                status="WARNING",
            ),
            StalenessResult(
                position_id="pos_2",
                symbol="ETHUSDT",
                hold_duration=timedelta(hours=73),
                should_warn=True,
                should_review=True,
                should_close=True,
                days_remaining=0.0,
                status="MAX_HOLD_EXCEEDED",
            ),
        ]
        mock_tracker.process_stale_positions = AsyncMock(return_value=results)

        response = client.get("/api/v1/positions/analysis/staleness")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["warnings"] == 1
        assert data["exceeded"] == 1


# ---------------------------------------------------------------------------
# Tests: Service unavailable
# ---------------------------------------------------------------------------


class TestServiceUnavailable:
    """Tests for 503 when tracker not initialized."""

    def test_uninitialized_tracker(self) -> None:
        """Routes return 503 when tracker is not initialized."""
        test_app = FastAPI()
        test_app.include_router(router, prefix="/api/v1/positions")

        # Reset the module-level tracker to None
        import src.api.routes.positions as pos_module
        original = pos_module._position_tracker
        pos_module._position_tracker = None

        try:
            client = TestClient(test_app)
            response = client.get("/api/v1/positions")
            assert response.status_code == 503
        finally:
            pos_module._position_tracker = original
