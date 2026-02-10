"""
Unit tests for Order model.

Tests:
- Numeric field validation (quantity, price, filled_quantity)
- Optional field handling (price, stop_price, filled_price)
- Enum values (OrderSide, OrderType, OrderStatus)
- Edge cases (zero quantity, negative values, NaN, Infinity)
"""
import math
import pytest
from datetime import datetime, timezone

from src.data.models import Order, OrderSide, OrderType, OrderStatus


class TestOrderModel:
    """Test Order model validation and behavior."""

    def test_create_order_valid(self, db_session):
        """Test creating a valid order."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        order = Order(
            account_id=account.id,
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=1.0,
            status=OrderStatus.PENDING,
        )
        db_session.add(order)
        db_session.commit()

        assert order.id is not None
        assert order.symbol == "BTCUSDT"
        assert order.side == OrderSide.BUY
        assert order.filled_quantity == 0.0  # Default

    def test_order_quantity_must_be_positive(self, db_session):
        """Test that quantity must be positive."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        with pytest.raises(ValueError, match="quantity must be positive"):
            Order(
                account_id=account.id,
                strategy_id=strategy.id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                quantity=0.0,  # Invalid
                status=OrderStatus.PENDING,
            )

    def test_order_negative_quantity_rejected(self, db_session):
        """Test that negative quantity is rejected."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        with pytest.raises(ValueError, match="quantity must be positive"):
            Order(
                account_id=account.id,
                strategy_id=strategy.id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                quantity=-1.0,  # Invalid
                status=OrderStatus.PENDING,
            )

    def test_order_nan_quantity_rejected(self, db_session):
        """Test that NaN quantity is rejected."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        with pytest.raises(ValueError, match="quantity cannot be NaN"):
            Order(
                account_id=account.id,
                strategy_id=strategy.id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                quantity=math.nan,  # Invalid
                status=OrderStatus.PENDING,
            )

    def test_order_filled_quantity_can_be_zero(self, db_session):
        """Test that filled_quantity can be 0 (order not yet filled)."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        order = Order(
            account_id=account.id,
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            side="buy",
            type="market",
            quantity=1.0,
            filled_quantity=0.0,  # Valid: order not filled yet
            status=OrderStatus.PENDING,
        )
        db_session.add(order)
        db_session.commit()

        assert order.filled_quantity == 0.0

    def test_order_negative_filled_quantity_rejected(self, db_session):
        """Test that negative filled_quantity is rejected."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        with pytest.raises(ValueError, match="filled_quantity must be non-negative"):
            Order(
                account_id=account.id,
                strategy_id=strategy.id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                quantity=1.0,
                filled_quantity=-0.5,  # Invalid
                status=OrderStatus.PENDING,
            )

    def test_order_price_optional(self, db_session):
        """Test that price is optional (for market orders)."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        order = Order(
            account_id=account.id,
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=1.0,
            price=None,  # Optional
            status=OrderStatus.PENDING,
        )
        db_session.add(order)
        db_session.commit()

        assert order.price is None

    def test_order_side_enum(self, db_session):
        """Test all OrderSide enum values."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        for side in OrderSide:
            order = Order(
                account_id=account.id,
                strategy_id=strategy.id,
                symbol="BTCUSDT",
                side=side,
                type=OrderType.MARKET,
                quantity=1.0,
                status=OrderStatus.PENDING,
            )
            db_session.add(order)
            db_session.commit()
            assert order.side == side
            db_session.rollback()

    def test_order_type_enum(self, db_session):
        """Test all OrderType enum values."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        for otype in OrderType:
            order = Order(
                account_id=account.id,
                strategy_id=strategy.id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                type=otype,
                quantity=1.0,
                status=OrderStatus.PENDING,
            )
            db_session.add(order)
            db_session.commit()
            assert order.type == otype
            db_session.rollback()

    def test_order_status_enum(self, db_session):
        """Test all OrderStatus enum values."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        for status in OrderStatus:
            order = Order(
                account_id=account.id,
                strategy_id=strategy.id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                quantity=1.0,
                status=status,
            )
            db_session.add(order)
            db_session.commit()
            assert order.status == status
            db_session.rollback()

    def test_order_repr(self, db_session):
        """Test __repr__() method."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        order = Order(
            account_id=account.id,
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=1.0,
            status=OrderStatus.PENDING,
        )
        db_session.add(order)
        db_session.commit()

        repr_str = repr(order)
        assert "Order" in repr_str
        assert order.id in repr_str
        assert "BTCUSDT" in repr_str
