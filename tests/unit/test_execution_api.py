"""Tests for execution quality API endpoints.

Tests all execution quality routes including stats, slippage analysis,
slippage estimation, and report generation with mocked dependencies.

Phase 4B: Position Tracking & Execution Quality
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.execution import (
    init_execution_routes,
    router,
)
from src.core.execution.quality import (
    ExecutionReport,
    ExecutionReportGenerator,
    FillRateStats,
    FillRateTracker,
    SlippageEstimate,
    SlippageEstimator,
    SlippageStats,
    SlippageTracker,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_slippage_tracker() -> MagicMock:
    """Create a mock SlippageTracker."""
    tracker = MagicMock(spec=SlippageTracker)
    tracker.get_slippage_stats = MagicMock(return_value=SlippageStats())
    tracker.get_average_slippage = MagicMock(return_value=0.0)
    return tracker


@pytest.fixture
def mock_slippage_estimator() -> MagicMock:
    """Create a mock SlippageEstimator."""
    estimator = MagicMock(spec=SlippageEstimator)
    estimator.estimate_slippage = MagicMock(
        return_value=SlippageEstimate(
            estimated_slippage_pct=0.08,
            components={"base": 0.05, "size": 0.01, "volatility": 0.01, "spread": 0.01},
            should_warn=False,
            should_block=False,
            recommended_action="PROCEED",
            recommendation="Estimated slippage 0.08% is within acceptable range.",
        )
    )
    return estimator


@pytest.fixture
def mock_fill_rate_tracker() -> MagicMock:
    """Create a mock FillRateTracker."""
    tracker = MagicMock(spec=FillRateTracker)
    tracker.get_stats = MagicMock(return_value=FillRateStats())
    return tracker


@pytest.fixture
def mock_report_generator() -> MagicMock:
    """Create a mock ExecutionReportGenerator."""
    gen = MagicMock(spec=ExecutionReportGenerator)
    now = datetime.now(timezone.utc)
    gen.generate_report = MagicMock(
        return_value=ExecutionReport(
            period_start=now - timedelta(days=1),
            period_end=now,
        )
    )
    return gen


@pytest.fixture
def app(
    mock_slippage_tracker: MagicMock,
    mock_slippage_estimator: MagicMock,
    mock_fill_rate_tracker: MagicMock,
    mock_report_generator: MagicMock,
) -> FastAPI:
    """Create a FastAPI test application with execution routes."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/execution")
    init_execution_routes(
        slippage_tracker=mock_slippage_tracker,
        slippage_estimator=mock_slippage_estimator,
        fill_rate_tracker=mock_fill_rate_tracker,
        report_generator=mock_report_generator,
    )
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests: Execution stats
# ---------------------------------------------------------------------------


class TestExecutionStats:
    """Tests for GET /api/v1/execution/stats."""

    def test_stats_empty(self, client: TestClient) -> None:
        """Empty stats returns 200 with zero values."""
        response = client.get("/api/v1/execution/stats")
        assert response.status_code == 200
        data = response.json()
        assert "slippage" in data
        assert "fill_rate" in data
        assert "timestamp" in data
        assert data["slippage"]["total_orders"] == 0
        assert data["fill_rate"]["total_orders"] == 0

    def test_stats_with_data(
        self,
        client: TestClient,
        mock_slippage_tracker: MagicMock,
        mock_fill_rate_tracker: MagicMock,
    ) -> None:
        """Stats with data returns populated response."""
        mock_slippage_tracker.get_slippage_stats = MagicMock(
            return_value=SlippageStats(
                total_orders=10,
                average_slippage_pct=0.15,
                average_slippage_bps=15.0,
            )
        )
        mock_fill_rate_tracker.get_stats = MagicMock(
            return_value=FillRateStats(
                total_orders=10,
                filled_orders=9,
                fill_rate_pct=90.0,
            )
        )

        response = client.get("/api/v1/execution/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["slippage"]["total_orders"] == 10
        assert data["fill_rate"]["filled_orders"] == 9


# ---------------------------------------------------------------------------
# Tests: Slippage analysis
# ---------------------------------------------------------------------------


class TestSlippageAnalysis:
    """Tests for GET /api/v1/execution/slippage."""

    def test_slippage_no_filter(self, client: TestClient) -> None:
        """Slippage analysis without filter."""
        response = client.get("/api/v1/execution/slippage")
        assert response.status_code == 200
        data = response.json()
        assert "average_slippage_pct" in data
        assert "timestamp" in data

    def test_slippage_with_symbol_filter(
        self, client: TestClient, mock_slippage_tracker: MagicMock
    ) -> None:
        """Slippage analysis filtered by symbol."""
        mock_slippage_tracker.get_average_slippage = MagicMock(return_value=0.15)
        mock_slippage_tracker.get_slippage_stats = MagicMock(
            return_value=SlippageStats(
                total_orders=5,
                slippage_by_symbol={"BTCUSDT": 0.15, "ETHUSDT": 0.25},
                slippage_by_side={"buy": 0.1, "sell": 0.2},
            )
        )

        response = client.get("/api/v1/execution/slippage?symbol=BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        assert abs(data["average_slippage_pct"] - 0.15) < 0.01
        # Should only show BTCUSDT in breakdown
        assert "BTCUSDT" in data["slippage_by_symbol"]


# ---------------------------------------------------------------------------
# Tests: Slippage estimation (PRD Feature F)
# ---------------------------------------------------------------------------


class TestSlippageEstimation:
    """Tests for GET /api/v1/execution/slippage/estimate."""

    def test_estimate_basic(self, client: TestClient) -> None:
        """Basic slippage estimation."""
        response = client.get(
            "/api/v1/execution/slippage/estimate"
            "?symbol=BTCUSDT&order_size_usd=10000"
        )
        assert response.status_code == 200
        data = response.json()
        assert "estimated_slippage_pct" in data
        assert "components" in data
        assert "recommended_action" in data
        assert data["recommended_action"] == "PROCEED"

    def test_estimate_with_volume(self, client: TestClient) -> None:
        """Estimation with average daily volume."""
        response = client.get(
            "/api/v1/execution/slippage/estimate"
            "?symbol=BTCUSDT&order_size_usd=10000&avg_daily_volume_usd=1000000000"
        )
        assert response.status_code == 200

    def test_estimate_missing_required_params(self, client: TestClient) -> None:
        """Missing required parameters returns 422."""
        response = client.get("/api/v1/execution/slippage/estimate")
        assert response.status_code == 422

    def test_estimate_invalid_size(self, client: TestClient) -> None:
        """Negative order size returns 422."""
        response = client.get(
            "/api/v1/execution/slippage/estimate"
            "?symbol=BTCUSDT&order_size_usd=-100"
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests: Execution report
# ---------------------------------------------------------------------------


class TestExecutionReport:
    """Tests for GET /api/v1/execution/report."""

    def test_report_basic(self, client: TestClient) -> None:
        """Basic report generation."""
        response = client.get(
            "/api/v1/execution/report"
            "?start_date=2026-02-01T00:00:00Z&end_date=2026-02-13T23:59:59Z"
        )
        assert response.status_code == 200
        data = response.json()
        assert "period_start" in data
        assert "period_end" in data
        assert "recommendations" in data

    def test_report_invalid_date(self, client: TestClient) -> None:
        """Invalid date format returns 400."""
        response = client.get(
            "/api/v1/execution/report"
            "?start_date=not-a-date&end_date=2026-02-13T23:59:59Z"
        )
        assert response.status_code == 400

    def test_report_end_before_start(self, client: TestClient) -> None:
        """End date before start date returns 400."""
        response = client.get(
            "/api/v1/execution/report"
            "?start_date=2026-02-13T00:00:00Z&end_date=2026-02-01T00:00:00Z"
        )
        assert response.status_code == 400

    def test_report_missing_params(self, client: TestClient) -> None:
        """Missing required parameters returns 422."""
        response = client.get("/api/v1/execution/report")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests: Service unavailable
# ---------------------------------------------------------------------------


class TestServiceUnavailable:
    """Tests for 503 when dependencies not initialized."""

    def test_uninitialized_returns_503(self) -> None:
        """Routes return 503 when not initialized."""
        test_app = FastAPI()
        test_app.include_router(router, prefix="/api/v1/execution")

        import src.api.routes.execution as exec_module
        originals = (
            exec_module._slippage_tracker,
            exec_module._slippage_estimator,
            exec_module._fill_rate_tracker,
            exec_module._report_generator,
        )
        exec_module._slippage_tracker = None
        exec_module._slippage_estimator = None
        exec_module._fill_rate_tracker = None
        exec_module._report_generator = None

        try:
            client = TestClient(test_app)
            response = client.get("/api/v1/execution/stats")
            assert response.status_code == 503
        finally:
            (
                exec_module._slippage_tracker,
                exec_module._slippage_estimator,
                exec_module._fill_rate_tracker,
                exec_module._report_generator,
            ) = originals
