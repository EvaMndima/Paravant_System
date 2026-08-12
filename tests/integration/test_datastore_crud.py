"""Integration tests for DataStore CRUD operations.

Tests the full DataStore repository pattern with real database operations.
"""
from datetime import datetime, timezone
from decimal import Decimal

from src.data.store import DataStore
from src.data.models import (
    Account, AccountStatus, RiskProfile,
    Strategy, StrategyStatus, StrategyType,
    Order, OrderSide, OrderType, OrderStatus,
    Position, PositionSide, PositionStatus,
    Trade,
)


class TestDataStoreAccounts:
    """Test account CRUD operations."""

    def test_save_and_get_account(self, test_db):
        """Test saving and retrieving an account."""
        store = DataStore()
        store.engine = test_db
        
        account = Account(
            name="Test Account",
            broker="binance",
            status=AccountStatus.ACTIVE,
            profile=RiskProfile.BALANCED,
            balance_usdt=Decimal("10000.0"),
            equity_usdt=Decimal("10000.0"),
        )
        
        # Save account
        saved = store.save_account(account)
        saved_id = saved.id  # Access ID before detachment
        assert saved_id is not None  # Auto-generated ID
        assert saved.created_at is not None
        
        # Retrieve account
        retrieved = store.get_account(saved_id)
        # Access all attributes IMMEDIATELY to avoid detachment
        retrieved_name = retrieved.name if retrieved else None
        retrieved_balance = retrieved.balance_usdt if retrieved else None
        assert retrieved is not None
        assert retrieved_name == "Test Account"
        assert retrieved_balance == Decimal("10000.0")

    def test_get_all_accounts(self, test_db):
        """Test retrieving all accounts."""
        store = DataStore()
        store.engine = test_db
        
        # Create multiple accounts
        for i in range(3):
            account = Account(
                name=f"Account {i}",
                broker="binance",
                balance_usdt=Decimal("5000.0"),
            )
            store.save_account(account)
        
        accounts = store.get_all_accounts()
        assert len(accounts) >= 3

    def test_get_active_accounts(self, test_db):
        """Test filtering accounts by status."""
        store = DataStore()
        store.engine = test_db
        
        # Create active and paused accounts
        active = Account(
            name="Active",
            broker="binance",
            status=AccountStatus.ACTIVE,
            balance_usdt=Decimal("5000.0"),
        )
        paused = Account(
            name="Paused",
            broker="binance",
            status=AccountStatus.PAUSED,
            balance_usdt=Decimal("5000.0"),
        )
        
        store.save_account(active)
        store.save_account(paused)
        
        active_accounts = store.get_active_accounts()
        # Access all attributes IMMEDIATELY for all items in list
        assert len(active_accounts) >= 1
        for acc in active_accounts:
            _ = acc.id  # Trigger load
            acc_status = acc.status
            assert acc_status == AccountStatus.ACTIVE


class TestDataStoreStrategies:
    """Test strategy CRUD operations."""

    def test_save_and_get_strategy(self, test_db):
        """Test saving and retrieving a strategy."""
        store = DataStore()
        store.engine = test_db
        
        strategy = Strategy(
            name="Test Strategy",
            template_id="test_template",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.DRAFT,
            parameters={"fast_ema": 12, "slow_ema": 26},
            symbols=["BTCUSDT"],
        )
        
        saved = store.save_strategy(strategy)
        saved_id = saved.id  # Access ID before detachment
        assert saved_id is not None  # Auto-generated
        
        retrieved = store.get_strategy(saved_id)
        # Access all attributes IMMEDIATELY
        retrieved_name = retrieved.name if retrieved else None
        retrieved_params = retrieved.parameters if retrieved else None
        assert retrieved is not None
        assert retrieved_name == "Test Strategy"
        assert retrieved_params["fast_ema"] == 12

    def test_get_active_strategies(self, test_db):
        """Test filtering strategies by status."""
        store = DataStore()
        store.engine = test_db
        
        # Create live and paused strategies
        live = Strategy(
            name="Live Strategy",
            template_id="test_template",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.LIVE,
            symbols=["BTCUSDT"],
        )
        paused = Strategy(
            name="Paused Strategy",
            template_id="test_template",
            type=StrategyType.MEAN_REVERSION,
            status=StrategyStatus.PAUSED,
            symbols=["ETHUSDT"],
        )
        
        store.save_strategy(live)
        store.save_strategy(paused)
        
        active_strategies = store.get_active_strategies()
        # Access all attributes IMMEDIATELY for all items
        assert len(active_strategies) >= 1
        for strat in active_strategies:
            _ = strat.id  # Trigger load
            strat_status = strat.status
            assert strat_status == StrategyStatus.LIVE


class TestDataStoreOrders:
    """Test order CRUD operations."""

    def test_save_and_get_order(self, test_db, sample_account, sample_strategy):
        """Test saving and retrieving an order."""
        store = DataStore()
        store.engine = test_db
        
        order = Order(
            account_id=sample_account.id,
            strategy_id=sample_strategy.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            status=OrderStatus.PENDING,
            quantity=Decimal("0.1"),
        )
        
        saved = store.save_order(order)
        saved_id = saved.id  # Access ID before detachment
        assert saved_id is not None  # Auto-generated
        
        retrieved = store.get_order(saved_id)
        # Access all attributes IMMEDIATELY
        retrieved_symbol = retrieved.symbol if retrieved else None
        retrieved_qty = retrieved.quantity if retrieved else None
        assert retrieved is not None
        assert retrieved_symbol == "BTCUSDT"
        # Compare using the pre-accessed value, not retrieved.quantity
        assert float(retrieved_qty) == float(Decimal("0.1"))

    def test_get_pending_orders(self, test_db, sample_account, sample_strategy):
        """Test retrieving pending orders."""
        store = DataStore()
        store.engine = test_db
        
        # Create pending and filled orders
        pending = Order(
            account_id=sample_account.id,
            strategy_id=sample_strategy.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            status=OrderStatus.PENDING,
            quantity=Decimal("0.1"),
        )
        filled = Order(
            account_id=sample_account.id,
            strategy_id=sample_strategy.id,
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            type=OrderType.MARKET,
            status=OrderStatus.FILLED,
            quantity=Decimal("1.0"),
        )
        
        store.save_order(pending)
        store.save_order(filled)
        
        pending_orders = store.get_pending_orders()
        # Access all attributes IMMEDIATELY for all items
        assert len(pending_orders) >= 1
        for order in pending_orders:
            _ = order.id  # Trigger load
            order_status = order.status
            assert order_status == OrderStatus.PENDING


class TestDataStorePositions:
    """Test position CRUD operations."""

    def test_save_and_get_position(self, test_db, sample_account, sample_strategy):
        """Test saving and retrieving a position."""
        store = DataStore()
        store.engine = test_db
        
        position = Position(
            account_id=sample_account.id,
            strategy_id=sample_strategy.id,
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            status=PositionStatus.OPEN,
            size=Decimal("0.5"),
            entry_price=Decimal("50000.0"),
            current_price=Decimal("50000.0"),
        )
        
        saved = store.save_position(position)
        saved_id = saved.id  # Access ID before detachment
        assert saved_id is not None
        
        # Retrieve position
        retrieved = store.get_position(saved_id)
        # Access all attributes IMMEDIATELY
        retrieved_symbol = retrieved.symbol if retrieved else None
        retrieved_size = retrieved.size if retrieved else None
        assert retrieved is not None
        assert retrieved_symbol == "BTCUSDT"
        assert retrieved_size == Decimal("0.5")  # Fixed: was quantity

    def test_get_open_positions(self, test_db, sample_account, sample_strategy):
        """Test retrieving open positions."""
        store = DataStore()
        store.engine = test_db
        
        # Create open and closed positions
        open_pos = Position(
            account_id=sample_account.id,
            strategy_id=sample_strategy.id,
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            status=PositionStatus.OPEN,
            size=Decimal("0.5"),
            entry_price=Decimal("50000.0"),
            current_price=Decimal("50000.0"),
        )
        closed_pos = Position(
            account_id=sample_account.id,
            strategy_id=sample_strategy.id,
            symbol="ETHUSDT",
            side=PositionSide.SHORT,
            status=PositionStatus.CLOSED,
            size=Decimal("1.0"),
            entry_price=Decimal("3000.0"),
            current_price=Decimal("2900.0"),
            exit_price=Decimal("2900.0"),
        )
        
        store.save_position(open_pos)
        store.save_position(closed_pos)
        
        open_positions = store.get_open_positions()
        assert len(open_positions) >= 1
        # Access status to avoid detachment issues
        for pos in open_positions:
            _ = pos.id  # Eager load
            assert pos.status == PositionStatus.OPEN

    def test_get_open_position_for_symbol(self, test_db, sample_account, sample_strategy):
        """Test retrieving specific open position by symbol."""
        store = DataStore()
        store.engine = test_db
        
        position = Position(
            account_id=sample_account.id,
            strategy_id=sample_strategy.id,
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            status=PositionStatus.OPEN,
            size=Decimal("0.5"),
            entry_price=Decimal("50000.0"),
            current_price=Decimal("50000.0"),
        )
        
        store.save_position(position)
        
        retrieved = store.get_position_by_symbol(sample_account.id, "BTCUSDT")
        # Access all attributes IMMEDIATELY
        retrieved_symbol = retrieved.symbol if retrieved else None
        assert retrieved is not None
        assert retrieved_symbol == "BTCUSDT"


class TestDataStoreTrades:
    """Test trade CRUD operations."""

    def test_save_and_get_trade(self, test_db, sample_account, sample_strategy, sample_order):
        """Test saving and retrieving a trade."""
        store = DataStore()
        store.engine = test_db
        
        
        trade = Trade(
            order_id=sample_order.id,
            account_id=sample_account.id,
            # strategy_id does NOT exist on Trade model - removed
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=float(Decimal("0.1")),  # Trade uses float, not Decimal
            price=float(Decimal("50000.0")),
            commission=float(Decimal("5.0")),
            executed_at=datetime.now(timezone.utc),  # REQUIRED field
        )
        
        saved = store.save_trade(trade)
        saved_id = saved.id  # Access ID before detachment
        assert saved_id is not None  # Auto-generated
        
        retrieved = store.get_trade(saved_id)
        # Access all attributes IMMEDIATELY
        retrieved_symbol = retrieved.symbol if retrieved else None
        retrieved_notional = retrieved.notional_value if retrieved else None
        assert retrieved is not None
        assert retrieved_symbol == "BTCUSDT"
        assert retrieved_notional == Decimal("5000.0")


class TestDataStoreSystemState:
    """Test system state operations."""

    def test_get_or_create_system_state(self, test_db):
        """Test system state singleton pattern."""
        store = DataStore()
        store.engine = test_db
        
        # First call creates
        state1 = store.get_system_state()
        # Access all needed attributes immediately
        state1_id = state1.id
        state1_kill_switch = state1.kill_switch_active
        assert state1_id == "system_state_singleton"
        assert state1_kill_switch is False  # Default value
        
        # Second call retrieves same instance
        state2 = store.get_system_state()
        state2_id = state2.id
        assert state2_id == state1_id
        
        # Update using correct API (keyword arguments, not state object)
        updated = store.update_system_state(kill_switch_active=True)
        updated_kill_switch = updated.kill_switch_active
        assert updated_kill_switch is True
        
        # Verify persistence
        retrieved = store.get_system_state()
        retrieved_kill_switch = retrieved.kill_switch_active
        assert retrieved_kill_switch is True


class TestDataStoreAuditLog:
    """Test audit log operations."""

    def test_save_audit_log(self, test_db):
        """Test saving audit log entries."""
        store = DataStore()
        store.engine = test_db
        
        # Use the correct API: add_audit_log(action, actor, details)
        saved = store.add_audit_log(
            action="TEST_ACTION",
            actor="system",
            details={"test": "data"}
        )
        # Access all needed attributes immediately
        saved_id = saved.id
        saved_action = saved.action
        saved_actor = saved.actor
        assert saved_id is not None
        assert saved_action == "TEST_ACTION"
        assert saved_actor == "system"


class TestDataStoreTransactions:
    """Test transaction handling and rollback."""

    def test_transaction_rollback_on_error(self, test_db):
        """Test that failed transactions roll back properly."""
        store = DataStore()
        store.engine = test_db

        try:
            with store.session() as session:
                # Create account
                account = Account(
                    id="acc_rollback",
                    name="Rollback Test",
                    broker="binance",
                    balance_usdt=Decimal("10000.0"),
                )
                session.add(account)
                session.flush()

                # FIXED: Expunge the first account from session to avoid identity map conflict
                # This prevents SAWarning when adding duplicate ID
                session.expunge(account)

                # Force an error (duplicate ID)
                duplicate = Account(
                    id="acc_rollback",  # Same ID
                    name="Duplicate",
                    broker="binance",
                    balance_usdt=Decimal("5000.0"),
                )
                session.add(duplicate)
                session.commit()
        except Exception:
            pass  # Expected to fail

        # Verify rollback - account should not exist
        retrieved = store.get_account("acc_rollback")
        assert retrieved is None
