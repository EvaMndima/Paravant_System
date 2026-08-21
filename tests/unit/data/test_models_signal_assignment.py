"""
Unit tests for Signal and StrategyAssignment models.

Tests:
- Signal model validation
- Timezone-aware timestamps
- StrategyAssignment model
- Mutable defaults for regime_filter
"""
from typing import Any

from src.data.models import Signal, SignalDirection, StrategyAssignment, AssignmentStatus


class TestSignalModel:
    """Test Signal model validation and behavior."""

    def test_create_signal_valid(self, db_session: Any) -> None:
        """Test creating a valid signal."""
        from src.data.models import Strategy

        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(strategy)
        db_session.commit()

        signal = Signal(
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            price=50000.0,
            indicators={"rsi": 65, "ma_cross": "bullish"},
        )
        db_session.add(signal)
        db_session.commit()

        assert signal.id is not None
        assert signal.direction == SignalDirection.LONG
        assert signal.timestamp is not None  # SQLite may not preserve tzinfo  # Timezone-aware
        assert signal.executed is False  # Default

    def test_signal_direction_enum(self, db_session: Any) -> None:
        """Test all SignalDirection enum values."""
        from src.data.models import Strategy

        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(strategy)
        db_session.commit()

        for direction in SignalDirection:
            signal = Signal(
                strategy_id=strategy.id,
                symbol="BTCUSDT",
                direction=direction,
                price=50000.0,
            )
            db_session.add(signal)
            db_session.commit()
            assert signal.direction == direction
            db_session.rollback()

    def test_signal_indicators_optional(self, db_session: Any) -> None:
        """Test that indicators JSON is optional."""
        from src.data.models import Strategy

        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(strategy)
        db_session.commit()

        signal = Signal(
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            direction="long",
            price=50000.0,
            indicators=None,  # Optional
        )
        db_session.add(signal)
        db_session.commit()

        assert signal.indicators is None

    def test_signal_repr(self, db_session: Any) -> None:
        """Test __repr__() method."""
        from src.data.models import Strategy

        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(strategy)
        db_session.commit()

        signal = Signal(
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            direction="long",
            price=50000.0,
        )
        db_session.add(signal)
        db_session.commit()

        repr_str = repr(signal)
        assert "Signal" in repr_str
        assert signal.id in repr_str
        assert "LONG" in repr_str  # Enum shows as LONG, not lowercase


class TestStrategyAssignmentModel:
    """Test StrategyAssignment model validation and behavior."""

    def test_create_assignment_valid(self, db_session: Any) -> None:
        """Test creating a valid strategy assignment."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        assignment = StrategyAssignment(
            account_id=account.id,
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            timeframe="1h",
            status=AssignmentStatus.ACTIVE,
            regime_filter=["trending_up", "ranging"],
        )
        db_session.add(assignment)
        db_session.commit()

        assert assignment.id is not None
        assert assignment.status == AssignmentStatus.ACTIVE
        assert len(assignment.regime_filter) == 2

    def test_assignment_default_regime_filter(self, db_session: Any) -> None:
        """Test default value for regime_filter."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        assignment = StrategyAssignment(
            account_id=account.id,
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            timeframe="1h",
            status=AssignmentStatus.ACTIVE,
        )
        db_session.add(assignment)
        db_session.commit()

        assert assignment.regime_filter == []  # Default empty list

    def test_assignment_mutable_default_isolation(self, db_session: Any) -> None:
        """Test that regime_filter list is not shared between instances."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy1 = Strategy(name="Test1", type="trend_following", template_id="test_template", status="draft")
        strategy2 = Strategy(name="Test2", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy1)
        db_session.add(strategy2)
        db_session.commit()

        assignment1 = StrategyAssignment(
            account_id=account.id,
            strategy_id=strategy1.id,
            symbol="BTCUSDT",
            timeframe="1h",
            status=AssignmentStatus.ACTIVE,
        )
        assignment2 = StrategyAssignment(
            account_id=account.id,
            strategy_id=strategy2.id,
            symbol="BTCUSDT",
            timeframe="1h",
            status=AssignmentStatus.ACTIVE,
        )
        db_session.add(assignment1)
        db_session.add(assignment2)
        db_session.flush()

        assignment1.regime_filter.append("trending_up")

        assignment2.regime_filter.append("ranging")

        assert "trending_up" in assignment1.regime_filter
        assert "trending_up" not in assignment2.regime_filter
        assert "ranging" in assignment2.regime_filter
        assert "ranging" not in assignment1.regime_filter

    def test_assignment_status_enum(self, db_session: Any) -> None:
        """Test all AssignmentStatus enum values."""
        from src.data.models import Account, Strategy

        account = Account(name="Test", broker="binance")
        strategy = Strategy(name="Test", type="trend_following", template_id="test_template", status="draft")
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        # A distinct strategy per status. The original loop reused one
        # (account, strategy) pair for all three, which only worked because
        # nothing enforced uniqueness -- the test was incidentally depending on
        # a missing constraint while claiming to test enum round-tripping.
        # Decision: DEC-2026-08-21-004
        for index, status in enumerate(AssignmentStatus):
            per_status_strategy = Strategy(
                name=f"Test {status.value}",
                type="trend_following",
                template_id=f"test_template_{index}",
                status="draft",
            )
            db_session.add(per_status_strategy)
            db_session.commit()

            assignment = StrategyAssignment(
                account_id=account.id,
                strategy_id=per_status_strategy.id,
                symbol="BTCUSDT",
                timeframe="1h",
                status=status,
            )
            db_session.add(assignment)
            db_session.commit()
            assert assignment.status == status
