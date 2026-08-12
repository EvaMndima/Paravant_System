"""Additional tests to improve order_manager coverage.

Targets specific uncovered lines identified in coverage report:
- get_open_orders() method
- start_reconciliation_loop() method
- Duplicate monitoring detection
- Monitor without external_id error handling
- Exchange cancel failure handling
- cancel_order when update returns None
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import OrderNotFoundError
from src.core.execution.interface import Balance, ExecutionEngine, OrderResult
from src.core.execution.order_manager import OrderManager
from src.data.models.order import Order, OrderSide, OrderStatus, OrderType
from src.data.store import DataStore


@pytest.fixture
def mock_execution_engine():
    """Mock execution engine."""
    engine = AsyncMock(spec=ExecutionEngine)
    engine.submit_order.return_value = OrderResult(
        order_id="test_id",
        external_id="binance_123",
        symbol="BTCUSDT",
        side="buy",
        order_type="market",
        quantity=0.1,
        filled_quantity=0.1,
        price=50000.0,
        filled_price=50000.0,
        status="filled",
        commission=0.1,
        timestamp=MagicMock(),
    )
    engine.get_account_balance.return_value = [
        Balance(asset="BTC", free=1.0, locked=0.0, total=1.0),
        Balance(asset="USDT", free=10000.0, locked=0.0, total=10000.0),
    ]
    return engine


@pytest.fixture
def mock_data_store():
    """Mock data store."""
    store = MagicMock(spec=DataStore)

    def create_order(order):
        """Helper to create order with minimal fields."""
        return order

    store.save_order.side_effect = create_order
    return store


@pytest.fixture
def order_manager(mock_execution_engine, mock_data_store):
    """OrderManager instance with mocked dependencies."""
    return OrderManager(
        execution_engine=mock_execution_engine,
        data_store=mock_data_store,
        risk_controller=None,
        monitoring_timeout=1800,
        reconciliation_interval=60,
    )


class TestGetOpenOrders:
    """Test get_open_orders() method (line 353)."""

    @pytest.mark.asyncio
    async def test_get_open_orders_returns_submitted_orders(
        self, order_manager, mock_data_store
    ):
        """Test that get_open_orders returns only SUBMITTED status orders."""
        # Arrange
        mock_orders = [
            Order(
                id="ord_1",
                account_id="test_account",
                strategy_id="test_strategy",
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                quantity=0.1,
                price=50000.0,
                status=OrderStatus.SUBMITTED,
            ),
        ]

        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = mock_orders

            # Act
            result = await order_manager.get_open_orders("test_account")

            # Assert
            assert result == mock_orders
            mock_to_thread.assert_called_once()
            # Verify it's calling get_orders_by_account_and_status with SUBMITTED
            call_args = mock_to_thread.call_args
            assert call_args[0][0] == mock_data_store.get_orders_by_account_and_status
            assert call_args[0][1] == "test_account"
            assert call_args[0][2] == OrderStatus.SUBMITTED


class TestStartReconciliationLoop:
    """Test start_reconciliation_loop() method (lines 450-454)."""

    @pytest.mark.asyncio
    async def test_start_reconciliation_loop_creates_task(self, order_manager):
        """Test that start_reconciliation_loop creates background task."""
        # Act
        await order_manager.start_reconciliation_loop()

        # Assert
        assert order_manager._reconciliation_task is not None
        assert not order_manager._reconciliation_task.done()

        # Cleanup
        await order_manager.shutdown()


class TestDuplicateMonitoring:
    """Test duplicate monitoring detection (lines 570-574)."""

    @pytest.mark.asyncio
    async def test_start_monitoring_detects_duplicate(self, order_manager):
        """Test that starting monitoring for same order twice is detected."""
        # Arrange
        order_id = "ord_123"
        symbol = "BTCUSDT"

        # Create a fake existing task
        fake_task = MagicMock()
        order_manager._monitoring_tasks[order_id] = fake_task

        # Act
        await order_manager._start_monitoring(order_id, symbol)

        # Assert - task count should still be 1 (no duplicate created)
        assert len(order_manager._monitoring_tasks) == 1
        # Original task should still be there (not replaced)
        assert order_manager._monitoring_tasks[order_id] is fake_task


class TestMonitorWithoutExternalId:
    """Test monitoring without external_id (lines 624-629)."""

    @pytest.mark.asyncio
    async def test_monitor_exits_if_no_external_id(self, order_manager, mock_data_store):
        """Test that _monitor_order exits early if order has no external_id."""
        # Arrange
        order_id = "ord_123"
        symbol = "BTCUSDT"

        # Create order without external_id
        order_without_external = Order(
            id=order_id,
            account_id="test_account",
            strategy_id="test_strategy",
            symbol=symbol,
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=0.1,
            price=50000.0,
            status=OrderStatus.PENDING,
            external_id=None,  # Missing external_id
        )

        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = order_without_external

            # Act
            await order_manager._monitor_order(order_id, symbol)

            # Assert - should have exited early without polling
            order_manager.execution_engine.get_order_status.assert_not_called()


class TestCancelOrderEdgeCases:
    """Test cancel_order edge cases (lines 300-301, 329)."""

    @pytest.mark.asyncio
    async def test_cancel_order_handles_exchange_failure(self, order_manager, mock_data_store):
        """Test that cancel_order logs but continues if exchange cancel fails (line 300-301)."""
        # Arrange
        order_id = "ord_123"
        order = Order(
            id=order_id,
            account_id="test_account",
            strategy_id="test_strategy",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=0.1,
            price=50000.0,
            status=OrderStatus.SUBMITTED,
            external_id="binance_456",
        )

        # Mock to simulate exchange failure
        order_manager.execution_engine.cancel_order.side_effect = Exception(
            "Exchange connection error"
        )

        # Create updated order (cancelled locally despite exchange failure)
        cancelled_order = Order(
            id=order_id,
            account_id="test_account",
            strategy_id="test_strategy",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=0.1,
            price=50000.0,
            status=OrderStatus.CANCELLED,
            external_id="binance_456",
        )

        with patch("asyncio.to_thread") as mock_to_thread:
            # First call: get_order returns submitted order
            # Second call: update_order returns cancelled order
            mock_to_thread.side_effect = [order, cancelled_order]

            # Act
            result = await order_manager.cancel_order(order_id)

            # Assert - should still return cancelled order despite exchange failure
            assert result.status == OrderStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_order_raises_if_update_returns_none(
        self, order_manager, mock_data_store
    ):
        """Test that cancel_order raises OrderNotFoundError if update returns None (line 329)."""
        # Arrange
        order_id = "ord_nonexistent"
        order = Order(
            id=order_id,
            account_id="test_account",
            strategy_id="test_strategy",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=0.1,
            price=50000.0,
            status=OrderStatus.SUBMITTED,
            external_id="binance_456",
        )

        with patch("asyncio.to_thread") as mock_to_thread:
            # First call: get_order returns order
            # Second call: update_order returns None (DB update failed somehow)
            mock_to_thread.side_effect = [order, None]

            # Act & Assert
            with pytest.raises(OrderNotFoundError) as exc_info:
                await order_manager.cancel_order(order_id)

            # OrderNotFoundError stores order_id in details dict, not as direct attribute
            assert exc_info.value.details["order_id"] == order_id


class TestReconciliationTaskCancellation:
    """Test reconciliation task cancellation in shutdown (lines 479-483)."""

    @pytest.mark.asyncio
    async def test_shutdown_cancels_reconciliation_task(self, order_manager):
        """Test that shutdown() cancels the reconciliation background task."""
        # Arrange - start reconciliation loop
        await order_manager.start_reconciliation_loop()
        assert order_manager._reconciliation_task is not None
        assert not order_manager._reconciliation_task.done()

        # Act
        await order_manager.shutdown()

        # Assert - task should be cancelled
        assert order_manager._reconciliation_task.cancelled() or order_manager._reconciliation_task.done()
