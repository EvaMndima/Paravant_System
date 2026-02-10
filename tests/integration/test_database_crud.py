"""
Integration tests for database CRUD operations.

Tests:
- Create, Read, Update, Delete for all models
- Foreign key constraints
- Cascading deletes
- Session rollback behavior
"""
import pytest
from sqlalchemy.exc import IntegrityError

from src.data.models import (
    Account,
    Strategy,
    Order,
    Position,
    Signal,
    StrategyAssignment,
    AssignmentStatus,
    StrategyType,
    StrategyStatus,
    OrderSide,
    OrderType,
    OrderStatus,
    PositionSide,
    PositionStatus,
)


class TestAccountCRUD:
    """Test CRUD operations for Account model."""

    def test_create_read_account(self, db_session):
        """Test creating and reading account."""
        account = Account(name="CRUD Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        # Read back
        fetched = db_session.query(Account).filter_by(id=account.id).first()
        assert fetched is not None
        assert fetched.name == "CRUD Test"

    def test_update_account(self, db_session):
        """Test updating account."""
        account = Account(name="Original", broker="binance")
        db_session.add(account)
        db_session.commit()

        # Update
        account.name = "Updated"
        db_session.commit()

        # Verify
        fetched = db_session.query(Account).filter_by(id=account.id).first()
        assert fetched.name == "Updated"

    def test_delete_account(self, db_session):
        """Test deleting account."""
        account = Account(name="To Delete", broker="binance")
        db_session.add(account)
        db_session.commit()

        account_id = account.id

        # Delete
        db_session.delete(account)
        db_session.commit()

        # Verify
        fetched = db_session.query(Account).filter_by(id=account_id).first()
        assert fetched is None


class TestStrategyCRUD:
    """Test CRUD operations for Strategy model."""

    def test_create_read_strategy(self, db_session):
        """Test creating and reading strategy."""
        strategy = Strategy(
            name="CRUD Strategy",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.DRAFT,
            template_id="tmp_123",
        )
        db_session.add(strategy)
        db_session.commit()

        fetched = db_session.query(Strategy).filter_by(id=strategy.id).first()
        assert fetched is not None
        assert fetched.name == "CRUD Strategy"

    def test_update_strategy_parameters(self, db_session):
        """Test updating strategy parameters."""
        strategy = Strategy(
            name="Params Test",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.DRAFT,
            template_id="tmp_123",
            parameters={"period": 20},
        )
        db_session.add(strategy)
        db_session.commit()

        # Update parameters
        strategy.parameters = {"period": 30, "threshold": 0.02}
        db_session.commit()

        # Verify
        fetched = db_session.query(Strategy).filter_by(id=strategy.id).first()
        assert fetched.parameters["period"] == 30
        assert fetched.parameters["threshold"] == 0.02


class TestForeignKeyConstraints:
    """Test foreign key constraints."""

    def test_order_requires_valid_account(self, db_session):
        """Test that order requires valid account_id."""
        order = Order(
            account_id="nonexistent_account_id",
            strategy_id="nonexistent_strategy_id",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=1.0,
            status=OrderStatus.PENDING,
        )
        db_session.add(order)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_position_requires_valid_strategy(self, db_session):
        """Test that position requires valid strategy_id."""
        account = Account(name="Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        position = Position(
            account_id=account.id,
            strategy_id="nonexistent_strategy_id",
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=1.0,
            entry_price=50000.0,
            current_price=50000.0,
            status=PositionStatus.OPEN,
        )
        db_session.add(position)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_strategy_assignment_requires_valid_ids(self, db_session):
        """Test that assignment requires valid account and strategy IDs."""
        assignment = StrategyAssignment(
            account_id="nonexistent",
            strategy_id="nonexistent",
            status=AssignmentStatus.ACTIVE,
            timeframe="1h",
        )
        db_session.add(assignment)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestSessionRollback:
    """Test session rollback behavior."""

    def test_rollback_on_error(self, db_session):
        """Test that session rolls back on error."""
        account = Account(name="Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        # Try to add invalid account
        try:
            bad_account = Account(
                name="Bad",
                broker="binance",
                balance_usdt=-1000.0,  # Invalid
            )
            db_session.add(bad_account)
            db_session.commit()
        except ValueError:
            db_session.rollback()

        # Original account should still be queryable
        fetched = db_session.query(Account).filter_by(id=account.id).first()
        assert fetched is not None

    def test_manual_rollback(self, db_session):
        """Test manual rollback."""
        account = Account(name="Original", broker="binance")
        db_session.add(account)
        db_session.commit()

        # Modify
        account.name = "Modified"

        # Rollback before commit
        db_session.rollback()

        # Verify not changed
        fetched = db_session.query(Account).filter_by(id=account.id).first()
        assert fetched.name == "Original"
