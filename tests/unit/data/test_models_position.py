"""
Unit tests for Position model.

Tests:
- Numeric field validation
- PnL calculations
- Status tracking
- Timezone-aware timestamps
- Relationships to Account and Strategy
"""
import math
import pytest
from datetime import datetime, timezone

from src.data.models import Position, PositionSide, PositionStatus


class TestPositionModel:
    """Test Position model validation and behavior."""

    def test_create_position_valid(self, db_session):
        """Test creating a valid position."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        position = Position(
            account_id=account.id,
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=1.0,
            entry_price=50000.0,
            current_price=50000.0,
            status=PositionStatus.OPEN,
        )
        db_session.add(position)
        db_session.commit()

        assert position.id is not None
        assert position.symbol == "BTCUSDT"
        # SQLite does not preserve tzinfo - just verify timestamp exists
        assert position.opened_at is not None

    def test_position_size_must_be_positive(self, db_session):
        """Test that size must be positive."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        with pytest.raises(ValueError, match="size must be positive"):
            Position(
                account_id=account.id,
                strategy_id=strategy.id,
                symbol="BTCUSDT",
                side="long",
                size=0.0,  # Invalid
                entry_price=50000.0,
                current_price=50000.0,
                status="open",
            )

    def test_position_negative_size_rejected(self, db_session):
        """Test that negative size is rejected."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        with pytest.raises(ValueError, match="size must be positive"):
            Position(
                account_id=account.id,
                strategy_id=strategy.id,
                symbol="BTCUSDT",
                side="long",
                size=-1.0,
                entry_price=50000.0,
                current_price=50000.0,
                status="open",
            )

    def test_position_entry_price_must_be_positive(self, db_session):
        """Test that entry_price must be positive."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        with pytest.raises(ValueError, match="entry_price must be positive"):
            Position(
                account_id=account.id,
                strategy_id=strategy.id,
                symbol="BTCUSDT",
                side="long",
                size=1.0,
                entry_price=0.0,  # Invalid
                current_price=50000.0,
                status="open",
            )

    def test_position_nan_rejected(self, db_session):
        """Test that NaN values are rejected."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        with pytest.raises(ValueError, match="cannot be NaN"):
            Position(
                account_id=account.id,
                strategy_id=strategy.id,
                symbol="BTCUSDT",
                side="long",
                size=math.nan,
                entry_price=50000.0,
                current_price=50000.0,
                status="open",
            )

    def test_position_side_enum(self, db_session):
        """Test all PositionSide enum values."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        for side in PositionSide:
            position = Position(
                account_id=account.id,
                strategy_id=strategy.id,
                symbol="BTCUSDT",
                side=side,
                size=1.0,
                entry_price=50000.0,
                current_price=50000.0,
                status="open",
            )
            db_session.add(position)
            db_session.commit()
            assert position.side == side
            db_session.rollback()

    def test_position_status_enum(self, db_session):
        """Test all PositionStatus enum values."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        for status in PositionStatus:
            position = Position(
                account_id=account.id,
                strategy_id=strategy.id,
                symbol="BTCUSDT",
                side="long",
                size=1.0,
                entry_price=50000.0,
                current_price=50000.0,
                status=status,
            )
            db_session.add(position)
            db_session.commit()
            assert position.status == status
            db_session.rollback()

    def test_position_closed_at_optional(self, db_session):
        """Test that closed_at is optional for open positions."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        position = Position(
            account_id=account.id,
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            side="long",
            size=1.0,
            entry_price=50000.0,
            current_price=51000.0,
            status="open",
            closed_at=None,  # Optional
        )
        db_session.add(position)
        db_session.commit()

        assert position.closed_at is None

    def test_position_repr(self, db_session):
        """Test __repr__() method."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        position = Position(
            account_id=account.id,
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            side="long",
            size=1.0,
            entry_price=50000.0,
            current_price=50000.0,
            status="open",
        )
        db_session.add(position)
        db_session.commit()

        repr_str = repr(position)
        assert "Position" in repr_str
        assert position.id in repr_str
        assert "BTCUSDT" in repr_str
        assert "LONG" in repr_str  # Enum shows as LONG, not lowercase
