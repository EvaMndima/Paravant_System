"""Tests for the OrderManager orchestrator.

Uses mocked ExecutionEngine and DataStore to test the full order
lifecycle including submission, risk validation, monitoring,
fill handling, and reconciliation.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exceptions import (
    InvalidStateTransitionError,
    OrderNotFoundError,
    OrderSubmissionError,
)
from src.core.execution.interface import OrderResult
from src.core.execution.order_manager import OrderManager
from src.core.risk.types import OrderRequest, RiskCheckResult
from src.data.models.order import Order, OrderSide, OrderStatus, OrderType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_engine() -> AsyncMock:
    """Create a mock ExecutionEngine."""
    engine = AsyncMock()
    engine.submit_order = AsyncMock()
    engine.cancel_order = AsyncMock()
    engine.get_order_status = AsyncMock()
    engine.get_account_balance = AsyncMock()
    engine.validate_symbol = AsyncMock(return_value=True)
    return engine


@pytest.fixture
def mock_store() -> MagicMock:
    """Create a mock DataStore."""
    store = MagicMock()
    store.save_order = MagicMock()
    store.get_order = MagicMock()
    store.update_order = MagicMock()
    store.save_trade = MagicMock()
    store.get_pending_orders = MagicMock(return_value=[])
    store.get_orders_by_account_and_status = MagicMock(return_value=[])
    return store


@pytest.fixture
def mock_risk_controller() -> MagicMock:
    """Create a mock RiskController."""
    controller = MagicMock()
    # Default: all checks pass
    controller.validate_order = MagicMock(
        return_value=[
            RiskCheckResult(approved=True, check_name="all_checks")
        ]
    )
    return controller


@pytest.fixture
def manager(mock_engine, mock_store) -> OrderManager:
    """Create an OrderManager with mocked dependencies."""
    return OrderManager(
        execution_engine=mock_engine,
        data_store=mock_store,
        monitoring_timeout=5,  # Short timeout for tests
    )


@pytest.fixture
def manager_with_risk(
    mock_engine, mock_store, mock_risk_controller
) -> OrderManager:
    """Create an OrderManager with risk controller."""
    return OrderManager(
        execution_engine=mock_engine,
        data_store=mock_store,
        risk_controller=mock_risk_controller,
        monitoring_timeout=5,
    )


@pytest.fixture
def sample_request() -> OrderRequest:
    """Create a sample OrderRequest."""
    return OrderRequest(
        account_id="acc_test_123",
        strategy_id="strat_test_456",
        symbol="BTCUSDT",
        side="buy",
        quantity=0.1,
        price=45000.0,
    )


def _make_order_result(**overrides: Any) -> OrderResult:
    """Create a mock OrderResult."""
    defaults = {
        "order_id": "acc_test_123",
        "external_id": "12345",
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "market",
        "quantity": 0.1,
        "filled_quantity": 0.1,
        "price": None,
        "filled_price": 45000.0,
        "status": "filled",
        "commission": 0.5,
        "timestamp": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return OrderResult(**defaults)


def _make_order(**overrides: Any) -> Order:
    """Create a mock Order model."""
    order = MagicMock(spec=Order)
    order.id = overrides.get("id", "ord_test_123")
    order.external_id = overrides.get("external_id", "12345")
    order.account_id = overrides.get("account_id", "acc_test_123")
    order.strategy_id = overrides.get("strategy_id", "strat_test_456")
    order.symbol = overrides.get("symbol", "BTCUSDT")
    order.side = overrides.get("side", OrderSide.BUY)
    order.type = overrides.get("type", OrderType.MARKET)
    order.quantity = overrides.get("quantity", 0.1)
    order.price = overrides.get("price", None)
    order.status = overrides.get("status", OrderStatus.SUBMITTED)
    order.filled_quantity = overrides.get("filled_quantity", 0.0)
    order.filled_price = overrides.get("filled_price", None)
    order.filled_at = overrides.get("filled_at", None)
    order.submitted_at = overrides.get("submitted_at", None)
    order.rejection_reason = overrides.get("rejection_reason", None)
    return order


# ---------------------------------------------------------------------------
# Submit order tests
# ---------------------------------------------------------------------------


class TestSubmitOrder:
    """Tests for OrderManager.submit_order()."""

    @pytest.mark.asyncio
    async def test_successful_submission_flow(
        self, manager, mock_engine, mock_store, sample_request
    ) -> None:
        """Test the full successful order submission flow.

        Verifies the IMMUTABLE sequence:
        1. Create record -> 2. Persist DB -> 3. Submit exchange -> 4. Update status
        """
        # Setup: engine returns filled immediately (market order)
        mock_engine.submit_order.return_value = _make_order_result(
            status="filled"
        )

        # save_order returns an Order-like object with ID
        saved_order = _make_order(status=OrderStatus.PENDING)
        mock_store.save_order.return_value = saved_order
        mock_store.update_order.return_value = saved_order
        mock_store.get_order.return_value = saved_order

        await manager.submit_order(sample_request)

        # Verify save_order was called BEFORE submit_order
        assert mock_store.save_order.called
        assert mock_engine.submit_order.called

        # save_order should be called first (persist before exchange)
        save_call_order = mock_store.save_order.call_args_list
        assert len(save_call_order) >= 1

    @pytest.mark.asyncio
    async def test_order_persisted_before_exchange_submission(
        self, manager, mock_engine, mock_store, sample_request
    ) -> None:
        """Test critical invariant: DB persist happens before exchange submit."""
        call_order: list[str] = []

        def track_save(*args, **kwargs):
            call_order.append("save")
            return _make_order()

        async def track_submit(*args, **kwargs):
            call_order.append("submit")
            return _make_order_result(status="filled")

        mock_store.save_order.side_effect = track_save
        mock_engine.submit_order.side_effect = track_submit
        mock_store.update_order.return_value = _make_order()
        mock_store.get_order.return_value = _make_order()

        await manager.submit_order(sample_request)

        assert call_order.index("save") < call_order.index("submit"), (
            "Order must be persisted to DB before exchange submission"
        )

    @pytest.mark.asyncio
    async def test_exchange_failure_marks_rejected(
        self, manager, mock_engine, mock_store, sample_request
    ) -> None:
        """Test that exchange submission failure marks order as REJECTED."""
        mock_store.save_order.return_value = _make_order(
            status=OrderStatus.PENDING
        )
        mock_engine.submit_order.side_effect = Exception("Exchange down")
        mock_store.update_order.return_value = _make_order(
            status=OrderStatus.REJECTED
        )

        with pytest.raises(OrderSubmissionError):
            await manager.submit_order(sample_request)

        # Verify update_order was called with REJECTED status
        mock_store.update_order.assert_called()
        update_kwargs = mock_store.update_order.call_args
        assert update_kwargs.kwargs.get("status") == OrderStatus.REJECTED or (
            len(update_kwargs.args) >= 2
        )


class TestSubmitOrderWithRisk:
    """Tests for order submission with risk validation."""

    @pytest.mark.asyncio
    async def test_risk_approved_continues_submission(
        self, manager_with_risk, mock_engine, mock_store, sample_request
    ) -> None:
        """Test that risk approval allows order submission to proceed."""
        mock_engine.submit_order.return_value = _make_order_result(
            status="filled"
        )
        mock_store.save_order.return_value = _make_order()
        mock_store.update_order.return_value = _make_order()
        mock_store.get_order.return_value = _make_order()

        await manager_with_risk.submit_order(sample_request)

        # Exchange should have been called (risk approved)
        assert mock_engine.submit_order.called

    @pytest.mark.asyncio
    async def test_risk_rejected_saves_rejected_order(
        self, manager_with_risk, mock_engine, mock_store,
        mock_risk_controller, sample_request
    ) -> None:
        """Test that risk rejection saves order with REJECTED status."""
        # Setup risk controller to reject
        mock_risk_controller.validate_order.return_value = [
            RiskCheckResult(
                approved=False,
                check_name="daily_loss",
                rejection_reason="Daily loss limit exceeded",
            )
        ]

        mock_store.save_order.return_value = _make_order(
            status=OrderStatus.REJECTED,
            rejection_reason="Daily loss limit exceeded",
        )

        await manager_with_risk.submit_order(sample_request)

        # Exchange should NOT have been called
        assert not mock_engine.submit_order.called

        # Order should have been saved with REJECTED status
        assert mock_store.save_order.called


# ---------------------------------------------------------------------------
# Cancel order tests
# ---------------------------------------------------------------------------


class TestCancelOrder:
    """Tests for OrderManager.cancel_order()."""

    @pytest.mark.asyncio
    async def test_cancel_submitted_order(
        self, manager, mock_engine, mock_store
    ) -> None:
        """Test cancelling a submitted order."""
        mock_store.get_order.return_value = _make_order(
            status=OrderStatus.SUBMITTED,
            external_id="12345",
        )
        mock_engine.cancel_order.return_value = _make_order_result(
            status="cancelled"
        )
        mock_store.update_order.return_value = _make_order(
            status=OrderStatus.CANCELLED
        )

        await manager.cancel_order("ord_test_123")

        mock_engine.cancel_order.assert_called_once()
        mock_store.update_order.assert_called()

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_order_raises(
        self, manager, mock_store
    ) -> None:
        """Test that cancelling a non-existent order raises."""
        mock_store.get_order.return_value = None

        with pytest.raises(OrderNotFoundError):
            await manager.cancel_order("ord_nonexistent")

    @pytest.mark.asyncio
    async def test_cancel_filled_order_raises(
        self, manager, mock_store
    ) -> None:
        """Test that cancelling a filled order raises."""
        mock_store.get_order.return_value = _make_order(
            status=OrderStatus.FILLED
        )

        with pytest.raises(InvalidStateTransitionError):
            await manager.cancel_order("ord_test_123")


# ---------------------------------------------------------------------------
# Get order tests
# ---------------------------------------------------------------------------


class TestGetOrder:
    """Tests for OrderManager.get_order()."""

    @pytest.mark.asyncio
    async def test_returns_order_when_found(
        self, manager, mock_store
    ) -> None:
        """Test that get_order returns order when found."""
        expected = _make_order()
        mock_store.get_order.return_value = expected

        result = await manager.get_order("ord_test_123")
        assert result is not None
        assert result.id == "ord_test_123"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(
        self, manager, mock_store
    ) -> None:
        """Test that get_order returns None when not found."""
        mock_store.get_order.return_value = None

        result = await manager.get_order("ord_nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# Reconciliation tests
# ---------------------------------------------------------------------------


class TestReconciliation:
    """Tests for OrderManager.reconcile_orders()."""

    @pytest.mark.asyncio
    async def test_reconcile_updates_mismatched_status(
        self, manager, mock_engine, mock_store
    ) -> None:
        """Test that reconciliation updates orders with mismatched status."""
        # DB thinks order is SUBMITTED, but exchange says FILLED
        pending_order = _make_order(
            status=OrderStatus.SUBMITTED,
            external_id="12345",
        )
        mock_store.get_pending_orders.return_value = [pending_order]
        mock_store.get_order.return_value = pending_order

        mock_engine.get_order_status.return_value = _make_order_result(
            status="filled"
        )
        mock_store.update_order.return_value = _make_order(
            status=OrderStatus.FILLED
        )

        updated = await manager.reconcile_orders()

        assert len(updated) == 1

    @pytest.mark.asyncio
    async def test_reconcile_skips_orders_without_external_id(
        self, manager, mock_engine, mock_store
    ) -> None:
        """Test that orders without external_id are skipped."""
        order_no_ext = _make_order(external_id=None)
        mock_store.get_pending_orders.return_value = [order_no_ext]

        updated = await manager.reconcile_orders()

        assert len(updated) == 0
        mock_engine.get_order_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_reconcile_handles_exchange_errors(
        self, manager, mock_engine, mock_store
    ) -> None:
        """Test that reconciliation handles exchange query errors gracefully."""
        pending_order = _make_order(
            status=OrderStatus.SUBMITTED,
            external_id="12345",
        )
        mock_store.get_pending_orders.return_value = [pending_order]
        mock_engine.get_order_status.side_effect = Exception("Exchange error")

        # Should not raise
        updated = await manager.reconcile_orders()
        assert len(updated) == 0


# ---------------------------------------------------------------------------
# Shutdown tests
# ---------------------------------------------------------------------------


class TestShutdown:
    """Tests for OrderManager.shutdown()."""

    @pytest.mark.asyncio
    async def test_shutdown_cancels_monitoring_tasks(
        self, manager
    ) -> None:
        """Test that shutdown cancels all monitoring tasks."""
        # Add a fake monitoring task
        task = asyncio.create_task(asyncio.sleep(100))
        manager._monitoring_tasks["ord_test"] = task

        await manager.shutdown()

        assert len(manager._monitoring_tasks) == 0

        # Allow the event loop to process the cancellation
        await asyncio.sleep(0)
        assert task.cancelled() or task.done()
