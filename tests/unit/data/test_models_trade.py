"""
Unit tests for Trade model.

Tests:
- Field validation (quantity, price, commission must be positive, not NaN/Inf)
- Enum values (OrderSide: BUY, SELL)
- Relationships (order back_populates)
- Properties (notional_value, total_cost)
- to_dict() method
"""
import math
import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from src.data.models import Trade, Order, Account, Strategy, StrategyType, StrategyStatus, OrderType, OrderStatus, OrderSide


class TestTradeModel:
    """Test Trade model validation and behavior."""

    def test_create_trade_valid(self, db_session):
        """Test creating a valid trade."""
        # Setup: Create dependencies (account, strategy, order)
        account = Account(name="Trade Test Account", broker="binance")
        strategy = Strategy(
            name="Trade Test Strategy",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.LIVE,
            template_id="tmp_123"
        )
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
            status=OrderStatus.FILLED
        )
        db_session.add(order)
        db_session.commit()

        # Test: Create trade
        trade = Trade(
            order_id=order.id,
            account_id=account.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=1.0,
            price=50000.0,
            commission=5.0,
            executed_at=datetime.now(timezone.utc)
        )
        db_session.add(trade)
        db_session.commit()

        assert trade.id is not None
        assert trade.symbol == "BTCUSDT"
        assert trade.quantity == 1.0
        assert trade.price == 50000.0
        assert trade.commission == 5.0
        assert trade.side == OrderSide.BUY
        assert trade.executed_at is not None

    def test_trade_default_values(self, db_session):
        """Test trade default values."""
        # Setup dependencies
        account = Account(name="Default Test", broker="binance")
        strategy = Strategy(
            name="Default Strategy",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.LIVE,
            template_id="tmp_123"
        )
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        order = Order(
            account_id=account.id,
            strategy_id=strategy.id,
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            type=OrderType.MARKET,
            quantity=10.0,
            status=OrderStatus.FILLED
        )
        db_session.add(order)
        db_session.commit()

        trade = Trade(
            order_id=order.id,
            account_id=account.id,
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            quantity=10.0,
            price=3000.0,
            executed_at=datetime.now(timezone.utc)
        )
        db_session.add(trade)
        db_session.commit()

        assert trade.commission == 0.0  # Default
        # assert trade.executed_at is not None  # Auto-generated - REMOVED because manually provided

    def test_trade_negative_quantity_rejected(self, db_session):
        """Test that negative quantity is rejected."""
        account = Account(name="Test", broker="binance")
        strategy = Strategy(
            name="Test",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.LIVE,
            template_id="tmp_123"
        )
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
            status=OrderStatus.FILLED
        )
        db_session.add(order)
        db_session.commit()

        with pytest.raises(ValueError, match="must be (positive|non-negative)"):
            trade = Trade(
                order_id=order.id,
                account_id=account.id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=-1.0,  # Invalid
                price=50000.0,
                executed_at=datetime.now(timezone.utc)
            )
            db_session.add(trade)
            db_session.flush()

    def test_trade_zero_quantity_rejected(self, db_session):
        """Test that zero quantity is rejected."""
        account = Account(name="Test", broker="binance")
        strategy = Strategy(
            name="Test",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.LIVE,
            template_id="tmp_123"
        )
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
            status=OrderStatus.FILLED
        )
        db_session.add(order)
        db_session.commit()

        with pytest.raises(ValueError, match="must be (positive|non-negative)"):
            trade = Trade(
                order_id=order.id,
                account_id=account.id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=0.0,  # Invalid
                price=50000.0
            )
            db_session.add(trade)
            db_session.flush()

    def test_trade_nan_price_rejected(self, db_session):
        """Test that NaN price is rejected."""
        account = Account(name="Test", broker="binance")
        strategy = Strategy(
            name="Test",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.LIVE,
            template_id="tmp_123"
        )
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
            status=OrderStatus.FILLED
        )
        db_session.add(order)
        db_session.commit()

        with pytest.raises(ValueError, match="price cannot be NaN"):
            trade = Trade(
                order_id=order.id,
                account_id=account.id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=1.0,
                price=math.nan  # Invalid
            )
            db_session.add(trade)
            db_session.flush()

    def test_trade_inf_price_rejected(self, db_session):
        """Test that Infinity price is rejected."""
        account = Account(name="Test", broker="binance")
        strategy = Strategy(
            name="Test",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.LIVE,
            template_id="tmp_123"
        )
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
            status=OrderStatus.FILLED
        )
        db_session.add(order)
        db_session.commit()

        with pytest.raises(ValueError, match="price cannot be Infinity"):
            trade = Trade(
                order_id=order.id,
                account_id=account.id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=1.0,
                price=math.inf  # Invalid
            )
            db_session.add(trade)
            db_session.flush()

    def test_trade_negative_commission_rejected(self, db_session):
        """Test that negative commission is rejected."""
        account = Account(name="Test", broker="binance")
        strategy = Strategy(
            name="Test",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.LIVE,
            template_id="tmp_123"
        )
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
            status=OrderStatus.FILLED
        )
        db_session.add(order)
        db_session.commit()

        with pytest.raises(ValueError, match="commission must be non-negative"):
            trade = Trade(
                order_id=order.id,
                account_id=account.id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=1.0,
                price=50000.0,
                commission=-10.0  # Invalid
            )
            db_session.add(trade)
            db_session.flush()

    def test_trade_inf_commission_rejected(self, db_session):
        """Test that Infinity commission is rejected."""
        account = Account(name="Test", broker="binance")
        strategy = Strategy(
            name="Test",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.LIVE,
            template_id="tmp_123"
        )
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
            status=OrderStatus.FILLED
        )
        db_session.add(order)
        db_session.commit()

        with pytest.raises(ValueError, match="commission cannot be Infinity"):
            trade = Trade(
                order_id=order.id,
                account_id=account.id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=1.0,
                price=50000.0,
                commission=math.inf  # Invalid
            )
            db_session.add(trade)
            db_session.flush()

    def test_trade_notional_value(self, db_session):
        """Test notional_value property (quantity * price)."""
        account = Account(name="Test", broker="binance")
        strategy = Strategy(
            name="Test",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.LIVE,
            template_id="tmp_123"
        )
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        order = Order(
            account_id=account.id,
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=2.0,
            status=OrderStatus.FILLED
        )
        db_session.add(order)
        db_session.commit()

        trade = Trade(
            order_id=order.id,
            account_id=account.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=2.0,
            price=50000.0,
            commission=10.0,
            executed_at=datetime.now(timezone.utc)
        )
        db_session.add(trade)
        db_session.commit()

        assert trade.notional_value == 100000.0  # 2.0 * 50000.0

    def test_trade_total_cost(self, db_session):
        """Test total_cost property (notional + commission)."""
        account = Account(name="Test", broker="binance")
        strategy = Strategy(
            name="Test",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.LIVE,
            template_id="tmp_123"
        )
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
            status=OrderStatus.FILLED
        )
        db_session.add(order)
        db_session.commit()

        trade = Trade(
            order_id=order.id,
            account_id=account.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=1.0,
            price=50000.0,
            commission=10.0,
            executed_at=datetime.now(timezone.utc)
        )
        db_session.add(trade)
        db_session.commit()

        assert trade.total_cost == 50010.0  # 50000 + 10

    def test_trade_order_relationship(self, db_session):
        """Test relationship to Order model."""
        account = Account(name="Test", broker="binance")
        strategy = Strategy(
            name="Test",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.LIVE,
            template_id="tmp_123"
        )
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
            status=OrderStatus.FILLED
        )
        db_session.add(order)
        db_session.commit()

        trade = Trade(
            order_id=order.id,
            account_id=account.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=1.0,
            price=50000.0,
            executed_at=datetime.now(timezone.utc)
        )
        db_session.add(trade)
        db_session.commit()

        # Refresh to load relationship
        db_session.refresh(trade)
        assert trade.order is not None
        assert trade.order.id == order.id
        assert trade.order.symbol == "BTCUSDT"

    def test_trade_to_dict(self, db_session):
        """Test to_dict() serialization."""
        account = Account(name="Test", broker="binance")
        strategy = Strategy(
            name="Test",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.LIVE,
            template_id="tmp_123"
        )
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
            status=OrderStatus.FILLED
        )
        db_session.add(order)
        db_session.commit()

        trade = Trade(
            order_id=order.id,
            account_id=account.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=1.0,
            price=50000.0,
            commission=5.0,
            executed_at=datetime.now(timezone.utc)
        )
        db_session.add(trade)
        db_session.commit()

        trade_dict = trade.to_dict()
        assert trade_dict["id"] == trade.id
        assert trade_dict["symbol"] == "BTCUSDT"
        assert trade_dict["quantity"] == 1.0
        assert trade_dict["price"] == 50000.0
        assert trade_dict["commission"] == 5.0

    def test_trade_enum_values(self, db_session):
        """Test that OrderSide enum values work correctly."""
        account = Account(name="Test", broker="binance")
        strategy = Strategy(
            name="Test",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.LIVE,
            template_id="tmp_123"
        )
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        order_buy = Order(
            account_id=account.id,
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=1.0,
            status=OrderStatus.FILLED
        )
        order_sell = Order(
            account_id=account.id,
            strategy_id=strategy.id,
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            type=OrderType.MARKET,
            quantity=10.0,
            status=OrderStatus.FILLED
        )
        db_session.add(order_buy)
        db_session.add(order_sell)
        db_session.commit()

        trade_buy = Trade(
            order_id=order_buy.id,
            account_id=account.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=1.0,
            price=50000.0,
            executed_at=datetime.now(timezone.utc)
        )
        trade_sell = Trade(
            order_id=order_sell.id,
            account_id=account.id,
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            quantity=10.0,
            price=3000.0,
            executed_at=datetime.now(timezone.utc)
        )
        db_session.add(trade_buy)
        db_session.add(trade_sell)
        db_session.commit()

        assert trade_buy.side == OrderSide.BUY
        assert trade_sell.side == OrderSide.SELL
        assert trade_buy.side.value == "buy"
        assert trade_sell.side.value == "sell"

    def test_trade_requires_valid_order_id(self, db_session):
        """Test that trade requires valid order_id (foreign key constraint)."""
        account = Account(name="Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        with pytest.raises(IntegrityError):
            trade = Trade(
                order_id="nonexistent_order_id",  # Invalid FK
                account_id=account.id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=1.0,
                price=50000.0
            )
            db_session.add(trade)
            db_session.commit()
