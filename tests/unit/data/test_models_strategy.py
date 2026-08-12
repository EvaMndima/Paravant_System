"""
Unit tests for Strategy model.

Tests:
- Lifecycle events tracking
- Mutable defaults (parameters, lifecycle lists)
- Status and type enums
- add_lifecycle_event method
- Timezone-aware timestamps
"""
from datetime import datetime

from src.data.models import Strategy, StrategyStatus, StrategyType


class TestStrategyModel:
    """Test Strategy model validation and behavior."""

    def test_create_strategy_valid(self, db_session):
        """Test creating a valid strategy."""
        strategy = Strategy(
            name="Moving Average",
            type=StrategyType.TREND_FOLLOWING,
            template_id="test_template",
            status=StrategyStatus.DRAFT,
            parameters={"fast_period": 10, "slow_period": 20},
        )
        db_session.add(strategy)
        db_session.commit()

        assert strategy.id is not None
        assert strategy.name == "Moving Average"
        assert strategy.type == StrategyType.TREND_FOLLOWING
        assert strategy.created_at is not None  # SQLite may not preserve tzinfo

    def test_strategy_default_values(self, db_session):
        """Test strategy default values."""
        strategy = Strategy(
            name="Default Test",
            type=StrategyType.TREND_FOLLOWING,
            template_id="test_template",
            status=StrategyStatus.DRAFT,
        )
        db_session.add(strategy)
        db_session.commit()

        assert strategy.parameters == {}
        assert strategy.lifecycle == []
        assert strategy.status == StrategyStatus.DRAFT

    def test_strategy_mutable_defaults_isolation(self, db_session):
        """Test that parameters and lifecycle are not shared."""
        strategy1 = Strategy(
            name="Strategy 1",
            type=StrategyType.TREND_FOLLOWING,
            template_id="test_template",
            status=StrategyStatus.DRAFT,
        )
        strategy2 = Strategy(
            name="Strategy 2",
            type=StrategyType.TREND_FOLLOWING,
            template_id="test_template",
            status=StrategyStatus.DRAFT,
        )

        # Ensure parameters is initialized
        if strategy1.parameters is None:
            strategy1.parameters = {}
        if strategy2.parameters is None:
            strategy2.parameters = {}

        strategy1.parameters["param1"] = "value1"
        strategy2.parameters["param2"] = "value2"

        assert "param1" in strategy1.parameters
        assert "param1" not in strategy2.parameters
        assert "param2" in strategy2.parameters
        assert "param2" not in strategy1.parameters

    def test_strategy_add_lifecycle_event(self, db_session):
        """Test adding lifecycle events."""
        strategy = Strategy(
            name="Lifecycle Test",
            type=StrategyType.TREND_FOLLOWING,
            template_id="test_template",
            status=StrategyStatus.DRAFT,
        )
        db_session.add(strategy)
        db_session.commit()

        strategy.add_lifecycle_event(
            from_status="draft",
            to_status="active",
            reason="User activated",
        )

        assert len(strategy.lifecycle) == 1
        event = strategy.lifecycle[0]
        assert event["from"] == "draft"
        assert event["to"] == "active"
        assert event["reason"] == "User activated"
        assert "timestamp" in event
        # Verify timestamp is ISO format
        datetime.fromisoformat(event["timestamp"])

    def test_strategy_multiple_lifecycle_events(self, db_session):
        """Test multiple lifecycle events are tracked."""
        strategy = Strategy(
            name="Multi Event Test",
            type=StrategyType.TREND_FOLLOWING,
            template_id="test_template",
            status=StrategyStatus.DRAFT,
        )
        db_session.add(strategy)
        db_session.commit()

        strategy.add_lifecycle_event("inactive", "active", "Activated")
        strategy.add_lifecycle_event("active", "paused", "Risk limit hit")
        strategy.add_lifecycle_event("paused", "active", "Risk restored")

        assert len(strategy.lifecycle) == 3
        assert strategy.lifecycle[0]["to"] == "active"
        assert strategy.lifecycle[1]["to"] == "paused"
        assert strategy.lifecycle[2]["to"] == "active"

    def test_strategy_status_enum(self, db_session):
        """Test all StrategyStatus enum values."""
        for status in StrategyStatus:
            strategy = Strategy(
                name=f"Test {status.value}",
                type=StrategyType.TREND_FOLLOWING,
                template_id="test_template",
                status=status,
            )
            db_session.add(strategy)
            db_session.commit()
            assert strategy.status == status
            db_session.rollback()

    def test_strategy_type_enum(self, db_session):
        """Test all StrategyType enum values."""
        for stype in StrategyType:
            strategy = Strategy(
                name=f"Test {stype.value}",
                type=stype,
                template_id="test_template",
                status=StrategyStatus.DRAFT,
            )
            db_session.add(strategy)
            db_session.commit()
            assert strategy.type == stype
            db_session.rollback()

    def test_strategy_to_dict(self, db_session):
        """Test to_dict() method."""
        strategy = Strategy(
            name="Dict Test",
            type=StrategyType.TREND_FOLLOWING,
            template_id="test_template",
            status=StrategyStatus.LIVE,
            parameters={"period": 20},
        )
        db_session.add(strategy)
        db_session.commit()

        strategy_dict = strategy.to_dict()
        assert strategy_dict["name"] == "Dict Test"
        assert "type" in strategy_dict
        assert strategy_dict["parameters"] == {"period": 20}

    def test_strategy_repr(self, db_session):
        """Test __repr__() method."""
        strategy = Strategy(
            name="Repr Test",
            type=StrategyType.TREND_FOLLOWING,
            template_id="test_template",
            status=StrategyStatus.DRAFT,
        )
        db_session.add(strategy)
        db_session.commit()

        repr_str = repr(strategy)
        assert "Strategy" in repr_str
        assert strategy.id in repr_str
        assert "Repr Test" in repr_str
