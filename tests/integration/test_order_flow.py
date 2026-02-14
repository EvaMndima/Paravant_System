"""Integration tests for the order execution flow.

Tests the full order lifecycle with a real database (in-memory SQLite)
and mocked exchange adapter. Validates the persist-before-submit
invariant, state transitions, and trade creation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.core.execution.interface import OrderResult
from src.core.execution.order_manager import OrderManager
from src.core.risk.types import OrderRequest
from src.data.models.base import Base
from src.data.store import DataStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def integration_engine():
    """Create an in-memory SQLite engine for integration tests.

    Uses StaticPool to ensure a single shared connection across all threads.
    This is critical because OrderManager uses asyncio.to_thread() for
    DataStore calls, and in-memory SQLite databases are per-connection.
    Without StaticPool, each thread would get an empty database.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def integration_store(integration_engine, monkeypatch):
    """Create a DataStore using the in-memory engine.

    Monkeypatches both the DataStore instance and the module-level
    engine to ensure all session creation uses the test database.
    """
    # Patch the module-level engine before creating DataStore
    import src.data.database
    monkeypatch.setattr(src.data.database, "engine", integration_engine)

    store = DataStore()
    # Also override instance engine in case it was cached
    store.engine = integration_engine
    return store


@pytest.fixture
def mock_exchange() -> AsyncMock:
    """Create a mock exchange that simulates filled market orders."""
    exchange = AsyncMock()

    async def simulate_fill(request: OrderRequest) -> OrderResult:
        return OrderResult(
            order_id=request.account_id,
            external_id="EX_12345",
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            filled_quantity=request.quantity,
            price=None,
            filled_price=request.price,
            status="filled",
            commission=request.price * request.quantity * 0.001,
            timestamp=datetime.now(timezone.utc),
        )

    exchange.submit_order = AsyncMock(side_effect=simulate_fill)
    exchange.cancel_order = AsyncMock()
    exchange.get_order_status = AsyncMock()
    exchange.get_account_balance = AsyncMock(return_value=[])
    exchange.validate_symbol = AsyncMock(return_value=True)
    return exchange


@pytest.fixture
def sample_account(integration_engine):
    """Create a sample account in the test database."""
    from src.data.models import Account, AccountStatus, RiskProfile

    session = Session(integration_engine)
    account = Account(
        name="Integration Test Account",
        broker="binance",
        profile=RiskProfile.BALANCED,
        status=AccountStatus.ACTIVE,
        balance_usdt=10000.0,
        equity_usdt=10000.0,
        regime="unknown",
        risk_config={},
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    session.expunge(account)
    session.close()
    return account


@pytest.fixture
def sample_strategy(integration_engine):
    """Create a sample strategy in the test database."""
    from src.data.models import Strategy, StrategyStatus, StrategyType

    session = Session(integration_engine)
    strategy = Strategy(
        name="Integration Test Strategy",
        template_id="test_template",
        template_version="1.0.0",
        type=StrategyType.TREND_FOLLOWING,
        status=StrategyStatus.DRAFT,
        parameters={"period": 10},
        symbols=["BTCUSDT"],
        backtest_results={},
        paper_results={},
        live_results={},
        lifecycle=[],
    )
    session.add(strategy)
    session.commit()
    session.refresh(strategy)
    session.expunge(strategy)
    session.close()
    return strategy


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestOrderSubmissionFlow:
    """Integration tests for the full order submission flow."""

    @pytest.mark.asyncio
    async def test_submit_order_creates_db_records(
        self, integration_store, mock_exchange, sample_account, sample_strategy
    ) -> None:
        """Test that submitting an order creates proper DB records."""
        manager = OrderManager(
            execution_engine=mock_exchange,
            data_store=integration_store,
            monitoring_timeout=5,
        )

        request = OrderRequest(
            account_id=sample_account.id,
            strategy_id=sample_strategy.id,
            symbol="BTCUSDT",
            side="buy",
            quantity=0.1,
            price=45000.0,
        )

        order = await manager.submit_order(request)

        # Order should exist in DB
        assert order is not None
        assert order.symbol == "BTCUSDT"

        # Verify order can be retrieved from DB
        db_order = integration_store.get_order(order.id)
        assert db_order is not None
        assert db_order.id == order.id

        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_filled_order_creates_trade_record(
        self, integration_store, mock_exchange, sample_account, sample_strategy
    ) -> None:
        """Test that a filled order creates a Trade record."""
        manager = OrderManager(
            execution_engine=mock_exchange,
            data_store=integration_store,
            monitoring_timeout=5,
        )

        request = OrderRequest(
            account_id=sample_account.id,
            strategy_id=sample_strategy.id,
            symbol="BTCUSDT",
            side="buy",
            quantity=0.1,
            price=45000.0,
        )

        order = await manager.submit_order(request)

        # Check that a trade was created
        trades = integration_store.get_trades_for_order(order.id)
        assert len(trades) >= 1

        trade = trades[0]
        assert trade.symbol == "BTCUSDT"
        assert trade.quantity == 0.1

        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_exchange_failure_leaves_order_in_rejected_state(
        self, integration_store, mock_exchange, sample_account, sample_strategy
    ) -> None:
        """Test that exchange failure results in REJECTED order in DB."""
        mock_exchange.submit_order.side_effect = Exception("Exchange down")

        manager = OrderManager(
            execution_engine=mock_exchange,
            data_store=integration_store,
            monitoring_timeout=5,
        )

        request = OrderRequest(
            account_id=sample_account.id,
            strategy_id=sample_strategy.id,
            symbol="BTCUSDT",
            side="buy",
            quantity=0.1,
            price=45000.0,
        )

        from src.core.exceptions import OrderSubmissionError

        with pytest.raises(OrderSubmissionError):
            await manager.submit_order(request)

        # Order should exist in DB with REJECTED status
        # (We need to find it since we don't have the ID directly)
        orders = integration_store.get_orders_for_account(sample_account.id)
        assert len(orders) >= 1

        rejected_order = orders[-1]
        status_value = (
            rejected_order.status.value
            if hasattr(rejected_order.status, "value")
            else str(rejected_order.status)
        )
        assert status_value == "rejected"

        await manager.shutdown()


class TestOrderCancellationFlow:
    """Integration tests for order cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_order_updates_db(
        self, integration_store, mock_exchange, sample_account, sample_strategy
    ) -> None:
        """Test that cancelling an order updates its DB status."""
        # First, create a submitted order that doesn't immediately fill
        async def simulate_new(request: OrderRequest) -> OrderResult:
            return OrderResult(
                order_id=request.account_id,
                external_id="EX_67890",
                symbol=request.symbol,
                side=request.side,
                order_type=request.order_type,
                quantity=request.quantity,
                filled_quantity=0.0,
                price=request.price,
                filled_price=None,
                status="submitted",
                commission=0.0,
                timestamp=datetime.now(timezone.utc),
            )

        mock_exchange.submit_order.side_effect = simulate_new
        mock_exchange.cancel_order.return_value = OrderResult(
            order_id="test",
            external_id="EX_67890",
            symbol="BTCUSDT",
            side="buy",
            order_type="market",
            quantity=0.1,
            filled_quantity=0.0,
            price=None,
            filled_price=None,
            status="cancelled",
            commission=0.0,
            timestamp=datetime.now(timezone.utc),
        )

        manager = OrderManager(
            execution_engine=mock_exchange,
            data_store=integration_store,
            monitoring_timeout=5,
        )

        request = OrderRequest(
            account_id=sample_account.id,
            strategy_id=sample_strategy.id,
            symbol="BTCUSDT",
            side="buy",
            quantity=0.1,
            price=45000.0,
        )

        order = await manager.submit_order(request)

        # Cancel the order
        cancelled = await manager.cancel_order(order.id)

        status_value = (
            cancelled.status.value
            if hasattr(cancelled.status, "value")
            else str(cancelled.status)
        )
        assert status_value == "cancelled"

        await manager.shutdown()
