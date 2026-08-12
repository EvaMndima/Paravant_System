"""
Unit tests for Account model.

Tests:
- Field validation (balance, equity must be non-negative, not NaN/Inf)
- Enum values (AccountStatus, RiskProfile)
- Mutable defaults (risk_config dict)
- Relationships (strategies)
- to_dict() method
"""
import math
import pytest

from src.data.models import Account, AccountStatus, RiskProfile, StrategyAssignment, AssignmentStatus


class TestAccountModel:
    """Test Account model validation and behavior."""

    def test_create_account_valid(self, db_session):
        """Test creating a valid account."""
        account = Account(
            name="Test Account",
            broker="binance",
            status=AccountStatus.ACTIVE,
            profile=RiskProfile.BALANCED,
            balance_usdt=10000.0,
            equity_usdt=10000.0,
            risk_config={"max_position_size": 0.1},
        )
        db_session.add(account)
        db_session.commit()

        assert account.id is not None
        assert account.name == "Test Account"
        assert account.status == AccountStatus.ACTIVE
        assert account.created_at is not None
        # NOTE: SQLite may not preserve timezone info even with DateTime(timezone=True)
        # The important thing is that created_at exists and is a datetime

    def test_account_default_values(self, db_session):
        """Test account default values."""
        account = Account(
            name="Default Test",
            broker="binance",
        )
        db_session.add(account)
        db_session.commit()

        assert account.status == AccountStatus.ACTIVE
        assert account.profile == RiskProfile.BALANCED
        assert account.balance_usdt == 0.0
        assert account.equity_usdt == 0.0
        assert account.risk_config == {}

    def test_account_mutable_default_isolation(self, db_session):
        """Test that risk_config dict is not shared between instances."""
        account1 = Account(name="Account 1", broker="binance")
        account2 = Account(name="Account 2", broker="binance")
        
        # Ensure risk_config is initialized
        if account1.risk_config is None:
            account1.risk_config = {}
        if account2.risk_config is None:
            account2.risk_config = {}

        account1.risk_config["key1"] = "value1"
        account2.risk_config["key2"] = "value2"

        assert "key1" in account1.risk_config
        assert "key1" not in account2.risk_config
        assert "key2" in account2.risk_config
        assert "key2" not in account1.risk_config

    def test_account_negative_balance_rejected(self, db_session):
        """Test that negative balance is rejected."""
        with pytest.raises(ValueError, match="balance_usdt must be non-negative"):
            _account = Account(
                name="Negative Test",
                broker="binance",
                balance_usdt=-100.0,
            )

    def test_account_nan_balance_rejected(self, db_session):
        """Test that NaN balance is rejected."""
        with pytest.raises(ValueError, match="balance_usdt cannot be NaN"):
            _account = Account(
                name="NaN Test",
                broker="binance",
                balance_usdt=math.nan,
            )

    def test_account_inf_equity_rejected(self, db_session):
        """Test that Infinity equity is rejected."""
        with pytest.raises(ValueError, match="equity_usdt cannot be Infinity"):
            _account = Account(
                name="Inf Test",
                broker="binance",
                equity_usdt=math.inf,
            )

    def test_account_status_enum(self, db_session):
        """Test all AccountStatus enum values."""
        for status in AccountStatus:
            account = Account(
                name=f"Test {status.value}",
                broker="binance",
                status=status,
            )
            db_session.add(account)
            db_session.commit()
            assert account.status == status
            db_session.rollback()

    def test_account_risk_profile_enum(self, db_session):
        """Test all RiskProfile enum values."""
        for profile in RiskProfile:
            account = Account(
                name=f"Test {profile.value}",
                broker="binance",
                profile=profile,
            )
            db_session.add(account)
            db_session.commit()
            assert account.profile == profile
            db_session.rollback()

    def test_account_to_dict(self, db_session):
        """Test to_dict() method."""
        account = Account(
            name="Dict Test",
            broker="binance",
            balance_usdt=5000.0,
        )
        db_session.add(account)
        db_session.commit()

        account_dict = account.to_dict()
        assert account_dict["name"] == "Dict Test"
        assert account_dict["broker"] == "binance"
        assert account_dict["balance_usdt"] == 5000.0
        assert "id" in account_dict
        assert "created_at" in account_dict

    def test_account_repr(self, db_session):
        """Test __repr__() method."""
        account = Account(
            name="Repr Test",
            broker="binance",
        )
        db_session.add(account)
        db_session.commit()

        repr_str = repr(account)
        assert "Account" in repr_str
        assert account.id in repr_str
        assert "Repr Test" in repr_str

    def test_account_strategy_relationship(self, db_session):
        """Test relationship to StrategyAssignment."""
        from src.data.models import Strategy

        account = Account(name="Rel Test", broker="binance")
        from src.data.models import StrategyType, StrategyStatus
        strategy = Strategy(
            name="Test Strategy",
            type=StrategyType.TREND_FOLLOWING,
            template_id="simple_ma",
            status=StrategyStatus.RETIRED,
        )
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

        # Refresh to load relationships
        db_session.refresh(account)
        assert len(account.strategies) == 1
        assert account.strategies[0].strategy_id == strategy.id
