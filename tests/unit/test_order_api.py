"""Comprehensive tests for order management API endpoints.

Tests all order API endpoints with various scenarios:
- Submit order endpoint (success, validation errors, submission errors)
- Get order endpoint (success, not found)
- List orders endpoint (with/without filters, invalid status)
- Cancel order endpoint (success, not found, invalid state)
- Reconcile orders endpoint (success, empty result)

Uses FastAPI TestClient for integration-level API testing.

Decision: DEC-2026-02-08-008 - Structured logging
Phase 4A: Execution Infrastructure
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.exceptions import (
    InvalidStateTransitionError,
    OrderNotFoundError,
    OrderSubmissionError,
)
from src.data.models.order import OrderSide, OrderStatus, OrderType


@pytest.fixture
def test_client() -> TestClient:
    """Create FastAPI test client with orders router."""
    from src.api.routes.orders import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/orders")

    return TestClient(app)


@pytest.fixture
def mock_order_manager() -> MagicMock:
    """Create mock OrderManager for isolated testing."""
    manager = MagicMock()
    # Make it awaitable for async methods
    manager.submit_order = AsyncMock()
    manager.get_order = AsyncMock()
    manager.cancel_order = AsyncMock()
    manager.reconcile_orders = AsyncMock()
    return manager


@pytest.fixture
def sample_order() -> MagicMock:
    """Create a sample Order model instance."""
    order = MagicMock()
    order.id = "ord_test_123"
    order.external_id = "EX_12345"
    order.account_id = "acc_test_456"
    order.strategy_id = "strat_test_789"
    order.symbol = "BTCUSDT"
    order.side = OrderSide.BUY
    order.type = OrderType.MARKET
    order.quantity = 0.1
    order.price = 45000.0
    order.status = OrderStatus.FILLED
    order.filled_quantity = 0.1
    order.filled_price = 45000.0
    order.filled_at = datetime.now(timezone.utc)
    order.submitted_at = datetime.now(timezone.utc)
    order.rejection_reason = None
    order.created_at = datetime.now(timezone.utc)
    order.updated_at = datetime.now(timezone.utc)
    return order


# ===========================================================================
# POST /orders tests (submit order)
# ===========================================================================


class TestSubmitOrderEndpoint:
    """Test order submission endpoint."""

    def test_submit_order_success(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
        sample_order: MagicMock,
    ) -> None:
        """Submit order endpoint should create and return order."""
        mock_order_manager.submit_order.return_value = sample_order

        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.post(
                "/api/v1/orders",
                json={
                    "account_id": "acc_test_456",
                    "strategy_id": "strat_test_789",
                    "symbol": "BTCUSDT",
                    "side": "buy",
                    "quantity": 0.1,
                    "price": 45000.0,
                    "order_type": "market",
                    "reason": "Test order",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "ord_test_123"
        assert data["symbol"] == "BTCUSDT"
        assert data["side"] == "buy"
        assert data["status"] == "filled"
        mock_order_manager.submit_order.assert_called_once()

    def test_submit_order_missing_required_field(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
    ) -> None:
        """Submit order should reject request missing required fields."""
        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.post(
                "/api/v1/orders",
                json={
                    "account_id": "acc_test_456",
                    # Missing strategy_id, symbol, side, quantity, price
                },
            )

        assert response.status_code == 422  # Unprocessable entity

    def test_submit_order_invalid_side(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
    ) -> None:
        """Submit order should reject invalid side value."""
        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.post(
                "/api/v1/orders",
                json={
                    "account_id": "acc_test_456",
                    "strategy_id": "strat_test_789",
                    "symbol": "BTCUSDT",
                    "side": "invalid_side",  # Must be "buy" or "sell"
                    "quantity": 0.1,
                    "price": 45000.0,
                },
            )

        assert response.status_code == 422

    def test_submit_order_negative_quantity(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
    ) -> None:
        """Submit order should reject negative quantity."""
        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.post(
                "/api/v1/orders",
                json={
                    "account_id": "acc_test_456",
                    "strategy_id": "strat_test_789",
                    "symbol": "BTCUSDT",
                    "side": "buy",
                    "quantity": -0.1,  # Must be > 0
                    "price": 45000.0,
                },
            )

        assert response.status_code == 422

    def test_submit_order_submission_error(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
    ) -> None:
        """Submit order should handle OrderSubmissionError."""
        mock_order_manager.submit_order.side_effect = OrderSubmissionError(
            order_id="ord_test",
            symbol="BTCUSDT",
            reason="Exchange rejected",
        )

        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.post(
                "/api/v1/orders",
                json={
                    "account_id": "acc_test_456",
                    "strategy_id": "strat_test_789",
                    "symbol": "BTCUSDT",
                    "side": "buy",
                    "quantity": 0.1,
                    "price": 45000.0,
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_submit_order_value_error(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
    ) -> None:
        """Submit order should handle ValueError as 400."""
        mock_order_manager.submit_order.side_effect = ValueError("Invalid price")

        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.post(
                "/api/v1/orders",
                json={
                    "account_id": "acc_test_456",
                    "strategy_id": "strat_test_789",
                    "symbol": "BTCUSDT",
                    "side": "buy",
                    "quantity": 0.1,
                    "price": 45000.0,
                },
            )

        assert response.status_code == 400

    def test_submit_order_manager_not_initialized(
        self,
        test_client: TestClient,
    ) -> None:
        """Submit order should return 503 if manager not initialized."""
        # Don't patch get_order_manager — let it fail naturally
        from src.api.routes import orders

        # Reset the singleton
        orders._order_manager = None

        response = test_client.post(
            "/api/v1/orders",
            json={
                "account_id": "acc_test_456",
                "strategy_id": "strat_test_789",
                "symbol": "BTCUSDT",
                "side": "buy",
                "quantity": 0.1,
                "price": 45000.0,
            },
        )

        assert response.status_code == 503
        data = response.json()
        assert "not initialized" in data["detail"]


# ===========================================================================
# GET /orders/{order_id} tests
# ===========================================================================


class TestGetOrderEndpoint:
    """Test get order by ID endpoint."""

    def test_get_order_success(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
        sample_order: MagicMock,
    ) -> None:
        """Get order endpoint should return order details."""
        mock_order_manager.get_order.return_value = sample_order

        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.get("/api/v1/orders/ord_test_123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "ord_test_123"
        assert data["symbol"] == "BTCUSDT"
        mock_order_manager.get_order.assert_called_once_with("ord_test_123")

    def test_get_order_not_found(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
    ) -> None:
        """Get order should return 404 if order doesn't exist."""
        mock_order_manager.get_order.return_value = None

        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.get("/api/v1/orders/ord_nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


# ===========================================================================
# GET /orders tests (list orders)
# ===========================================================================


class TestListOrdersEndpoint:
    """Test list orders endpoint."""

    def test_list_orders_success(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
        sample_order: MagicMock,
    ) -> None:
        """List orders should return orders for account."""
        mock_store = MagicMock()
        mock_store.get_orders_by_account_and_status.return_value = [sample_order]
        mock_order_manager.data_store = mock_store

        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.get(
                "/api/v1/orders",
                params={"account_id": "acc_test_456"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["orders"]) == 1
        assert data["orders"][0]["id"] == "ord_test_123"

    def test_list_orders_with_status_filter(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
        sample_order: MagicMock,
    ) -> None:
        """List orders should filter by status."""
        mock_store = MagicMock()
        mock_store.get_orders_by_account_and_status.return_value = [sample_order]
        mock_order_manager.data_store = mock_store

        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.get(
                "/api/v1/orders",
                params={"account_id": "acc_test_456", "status": "filled"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_list_orders_invalid_status(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
    ) -> None:
        """List orders should reject invalid status value."""
        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.get(
                "/api/v1/orders",
                params={"account_id": "acc_test_456", "status": "invalid_status"},
            )

        assert response.status_code == 400
        data = response.json()
        assert "Invalid status" in data["detail"]

    def test_list_orders_empty_result(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
    ) -> None:
        """List orders should return empty list if no orders."""
        mock_store = MagicMock()
        mock_store.get_orders_by_account_and_status.return_value = []
        mock_order_manager.data_store = mock_store

        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.get(
                "/api/v1/orders",
                params={"account_id": "acc_test_456"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["orders"]) == 0

    def test_list_orders_missing_account_id(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
    ) -> None:
        """List orders should require account_id parameter."""
        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.get("/api/v1/orders")

        assert response.status_code == 422  # Missing required query param


# ===========================================================================
# DELETE /orders/{order_id} tests (cancel order)
# ===========================================================================


class TestCancelOrderEndpoint:
    """Test cancel order endpoint."""

    def test_cancel_order_success(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
        sample_order: MagicMock,
    ) -> None:
        """Cancel order endpoint should cancel and return order."""
        cancelled_order = sample_order
        cancelled_order.status = OrderStatus.CANCELLED
        mock_order_manager.cancel_order.return_value = cancelled_order

        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.delete("/api/v1/orders/ord_test_123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "ord_test_123"
        assert data["status"] == "cancelled"
        mock_order_manager.cancel_order.assert_called_once_with("ord_test_123")

    def test_cancel_order_not_found(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
    ) -> None:
        """Cancel order should return 404 if order doesn't exist."""
        mock_order_manager.cancel_order.side_effect = OrderNotFoundError(
            order_id="ord_nonexistent"
        )

        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.delete("/api/v1/orders/ord_nonexistent")

        assert response.status_code == 404

    def test_cancel_order_invalid_state(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
    ) -> None:
        """Cancel order should return 409 for invalid state transition."""
        mock_order_manager.cancel_order.side_effect = InvalidStateTransitionError(
            order_id="ord_test_123",
            current_status="filled",
            requested_status="cancelled",
        )

        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.delete("/api/v1/orders/ord_test_123")

        assert response.status_code == 409  # Conflict
        data = response.json()
        assert "detail" in data


# ===========================================================================
# POST /orders/reconcile tests
# ===========================================================================


class TestReconcileOrdersEndpoint:
    """Test order reconciliation endpoint."""

    def test_reconcile_orders_success(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
        sample_order: MagicMock,
    ) -> None:
        """Reconcile orders should return updated orders."""
        order2 = MagicMock()
        order2.id = "ord_test_456"
        mock_order_manager.reconcile_orders.return_value = [sample_order, order2]

        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.post("/api/v1/orders/reconcile")

        assert response.status_code == 200
        data = response.json()
        assert data["orders_updated"] == 2
        assert "ord_test_123" in data["updated_order_ids"]
        assert "ord_test_456" in data["updated_order_ids"]
        assert "timestamp" in data

    def test_reconcile_orders_no_updates(
        self,
        test_client: TestClient,
        mock_order_manager: MagicMock,
    ) -> None:
        """Reconcile orders should handle empty result."""
        mock_order_manager.reconcile_orders.return_value = []

        with patch(
            "src.api.routes.orders.get_order_manager",
            return_value=mock_order_manager,
        ):
            response = test_client.post("/api/v1/orders/reconcile")

        assert response.status_code == 200
        data = response.json()
        assert data["orders_updated"] == 0
        assert len(data["updated_order_ids"]) == 0


# ===========================================================================
# Helper function tests
# ===========================================================================


class TestOrderToResponse:
    """Test _order_to_response helper function."""

    def test_order_to_response_conversion(
        self,
        sample_order: MagicMock,
    ) -> None:
        """Order should be correctly converted to response."""
        from src.api.routes.orders import _order_to_response

        response = _order_to_response(sample_order)

        assert response.id == "ord_test_123"
        assert response.symbol == "BTCUSDT"
        assert response.side == "buy"
        assert response.status == "filled"
        assert response.quantity == 0.1

    def test_order_to_response_handles_none_timestamps(self) -> None:
        """Order with None timestamps should serialize correctly."""
        from src.api.routes.orders import _order_to_response

        order = MagicMock()
        order.id = "ord_test"
        order.external_id = None
        order.account_id = "acc_test"
        order.strategy_id = None
        order.symbol = "BTCUSDT"
        order.side = OrderSide.BUY
        order.type = OrderType.MARKET
        order.quantity = 0.1
        order.price = 45000.0
        order.status = OrderStatus.PENDING
        order.filled_quantity = 0.0
        order.filled_price = None
        order.filled_at = None
        order.submitted_at = None
        order.rejection_reason = None
        order.created_at = None
        order.updated_at = None

        response = _order_to_response(order)

        assert response.id == "ord_test"
        assert response.filled_at is None
        assert response.submitted_at is None
        assert response.created_at is None
        assert response.updated_at is None


# ===========================================================================
# Initialization tests
# ===========================================================================


class TestInitialization:
    """Test module initialization."""

    def test_init_order_routes(self) -> None:
        """init_order_routes should set global singleton."""
        from src.api.routes import orders

        mock_manager = MagicMock()
        orders.init_order_routes(mock_manager)

        assert orders._order_manager is mock_manager

    def test_get_order_manager_raises_if_not_initialized(self) -> None:
        """get_order_manager should raise HTTPException if not initialized."""
        from src.api.routes import orders
        from fastapi import HTTPException

        # Reset singleton
        orders._order_manager = None

        with pytest.raises(HTTPException) as exc_info:
            orders.get_order_manager()

        assert exc_info.value.status_code == 503
        assert "not initialized" in exc_info.value.detail
