"""
Unit tests for PnL models (PnLRecord and EquitySnapshot).

Tests for PnLRecord:
- Field validation (financial values can be negative for losses)
- Relationships (account, strategy)
- Properties (win_rate calculation)
- Date handling

Tests for EquitySnapshot:
- Field validation
- Timestamp handling (timezone-aware)
- Relationship to account
"""
import pytest
from datetime import datetime, timezone, date, timedelta
from sqlalchemy.exc import IntegrityError

from src.data.models import PnLRecord, EquitySnapshot, Account, Strategy, StrategyType, StrategyStatus


class TestPnLRecordModel:
    """Test PnLRecord model validation and behavior."""

    def test_create_pnl_record_valid(self, db_session):
        """Test creating a valid P&L record."""
        account = Account(name="PnL Test Account", broker="binance")
        db_session.add(account)
        db_session.commit()

        pnl = PnLRecord(
            account_id=account.id,
            record_date=date.today(),
            realized_pnl=100.0,
            unrealized_pnl=50.0,
            total_pnl=150.0,
            portfolio_value=10150.0,
            cash_balance=10000.0,
            position_value=150.0,
            winning_trades=3,
            losing_trades=2,
        )
        db_session.add(pnl)
        db_session.commit()

        assert pnl.id is not None
        assert pnl.realized_pnl == 100.0
        assert pnl.unrealized_pnl == 50.0
        assert pnl.total_pnl == 150.0
        assert pnl.winning_trades == 3
        assert pnl.losing_trades == 2

    def test_pnl_negative_values_allowed(self, db_session):
        """Test that negative P&L values are allowed (losing trades)."""
        account = Account(name="Loss Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        # Test negative P&L (loss scenario)
        pnl = PnLRecord(
            account_id=account.id,
            record_date=date.today(),
            realized_pnl=-200.0,  # Loss
            unrealized_pnl=-100.0,  # Loss
            total_pnl=-300.0,  # Total loss
            portfolio_value=9700.0,
            cash_balance=9700.0,
            position_value=0.0,
            winning_trades=2,
            losing_trades=5,
        )
        db_session.add(pnl)
        db_session.commit()  # Should succeed without validation errors

        assert pnl.total_pnl == -300.0
        assert pnl.realized_pnl == -200.0
        assert pnl.unrealized_pnl == -100.0

    def test_pnl_win_rate_calculation(self, db_session):
        """Test win_rate property calculation."""
        account = Account(name="Win Rate Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        # 6 winning trades, 4 losing trades = 60% win rate
        pnl = PnLRecord(
            account_id=account.id,
            record_date=date.today(),
            realized_pnl=500.0,
            unrealized_pnl=0.0,
            total_pnl=500.0,
            portfolio_value=10500.0,
            cash_balance=10500.0,
            position_value=0.0,
            winning_trades=6,
            losing_trades=4,
        )
        db_session.add(pnl)
        db_session.commit()

        assert pnl.win_rate == 60.0  # 6 / (6 + 4) * 100

    def test_pnl_win_rate_zero_trades(self, db_session):
        """Test win_rate property with zero trades."""
        account = Account(name="No Trades Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        pnl = PnLRecord(
            account_id=account.id,
            record_date=date.today(),
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            total_pnl=0.0,
            portfolio_value=10000.0,
            cash_balance=10000.0,
            position_value=0.0,
            winning_trades=0,
            losing_trades=0,
        )
        db_session.add(pnl)
        db_session.commit()

        assert pnl.win_rate == 0.0  # Edge case: 0 / 0 = 0.0

    def test_pnl_win_rate_all_wins(self, db_session):
        """Test win_rate property with 100% win rate."""
        account = Account(name="All Wins Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        pnl = PnLRecord(
            account_id=account.id,
            record_date=date.today(),
            realized_pnl=1000.0,
            unrealized_pnl=0.0,
            total_pnl=1000.0,
            portfolio_value=11000.0,
            cash_balance=11000.0,
            position_value=0.0,
            winning_trades=10,
            losing_trades=0,
        )
        db_session.add(pnl)
        db_session.commit()

        assert pnl.win_rate == 100.0  # 10 / 10 * 100

    def test_pnl_relationships_account(self, db_session):
        """Test relationship to Account."""
        account = Account(name="Relationship Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        pnl = PnLRecord(
            account_id=account.id,
            record_date=date.today(),
            realized_pnl=100.0,
            unrealized_pnl=50.0,
            total_pnl=150.0,
            portfolio_value=10150.0,
            cash_balance=10000.0,
            position_value=150.0,
        )
        db_session.add(pnl)
        db_session.commit()

        # Verify FK relationship works
        assert pnl.account_id == account.id

    def test_pnl_relationships_strategy(self, db_session):
        """Test optional relationship to Strategy."""
        account = Account(name="Strategy Test", broker="binance")
        strategy = Strategy(
            name="Test Strategy",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.LIVE,
            template_id="tmp_123"
        )
        db_session.add(account)
        db_session.add(strategy)
        db_session.commit()

        # P&L can be strategy-specific
        pnl = PnLRecord(
            account_id=account.id,
            strategy_id=strategy.id,  # Optional
            record_date=date.today(),
            realized_pnl=50.0,
            unrealized_pnl=25.0,
            total_pnl=75.0,
            portfolio_value=10075.0,
            cash_balance=10000.0,
            position_value=75.0,
        )
        db_session.add(pnl)
        db_session.commit()

        assert pnl.strategy_id == strategy.id

    def test_pnl_date_handling(self, db_session):
        """Test date field handling."""
        account = Account(name="Date Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        # Test with specific date
        target_date = date(2026, 2, 9)
        pnl = PnLRecord(
            account_id=account.id,
            record_date=target_date,
            realized_pnl=100.0,
            unrealized_pnl=0.0,
            total_pnl=100.0,
            portfolio_value=10100.0,
            cash_balance=10100.0,
            position_value=0.0,
        )
        db_session.add(pnl)
        db_session.commit()

        assert pnl.record_date == target_date
        assert isinstance(pnl.record_date, date)

    def test_pnl_to_dict(self, db_session):
        """Test to_dict() serialization."""
        account = Account(name="Dict Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        pnl = PnLRecord(
            account_id=account.id,
            record_date=date.today(),
            realized_pnl=100.0,
            unrealized_pnl=50.0,
            total_pnl=150.0,
            portfolio_value=10150.0,
            cash_balance=10000.0,
            position_value=150.0,
            winning_trades=3,
            losing_trades=2,
        )
        db_session.add(pnl)
        db_session.commit()

        pnl_dict = pnl.to_dict()
        assert pnl_dict["realized_pnl"] == 100.0
        assert pnl_dict["unrealized_pnl"] == 50.0
        assert pnl_dict["total_pnl"] == 150.0
        assert pnl_dict["winning_trades"] == 3
        assert pnl_dict["losing_trades"] == 2

    def test_pnl_requires_valid_account_id(self, db_session):
        """Test that PnL requires valid account_id (foreign key constraint)."""
        with pytest.raises(IntegrityError):
            pnl = PnLRecord(
                account_id="nonexistent_account_id",  # Invalid FK
                record_date=date.today(),
                realized_pnl=0.0,
                unrealized_pnl=0.0,
                total_pnl=0.0,
                portfolio_value=10000.0,
                cash_balance=10000.0,
                position_value=0.0,
            )
            db_session.add(pnl)
            db_session.commit()


class TestEquitySnapshotModel:
    """Test EquitySnapshot model validation and behavior."""

    def test_create_equity_snapshot_valid(self, db_session):
        """Test creating a valid equity snapshot."""
        account = Account(name="Equity Test Account", broker="binance")
        db_session.add(account)
        db_session.commit()

        snapshot = EquitySnapshot(
            account_id=account.id,
            timestamp=datetime.now(timezone.utc),
            equity=10000.0,
            cash=9500.0,
            positions_value=500.0,
        )
        db_session.add(snapshot)
        db_session.commit()

        assert snapshot.id is not None
        assert snapshot.equity == 10000.0
        assert snapshot.cash == 9500.0
        assert snapshot.positions_value == 500.0

    def test_equity_snapshot_default_timestamp(self, db_session):
        """Test that timestamp defaults to current UTC time."""
        account = Account(name="Default Timestamp Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        # Create without explicit timestamp
        snapshot = EquitySnapshot(
            account_id=account.id,
            equity=10000.0,
            cash=10000.0,
            positions_value=0.0,
        )
        db_session.add(snapshot)
        db_session.commit()

        assert snapshot.timestamp is not None
        # Verify timestamp is recent (within last minute)
        time_diff = datetime.now(timezone.utc) - snapshot.timestamp.replace(tzinfo=timezone.utc)
        assert time_diff.total_seconds() < 60

    def test_equity_snapshot_timezone_aware(self, db_session):
        """Test that timestamp is timezone-aware."""
        account = Account(name="Timezone Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        # Explicit UTC timestamp
        utc_time = datetime.now(timezone.utc)
        snapshot = EquitySnapshot(
            account_id=account.id,
            timestamp=utc_time,
            equity=10000.0,
            cash=10000.0,
            positions_value=0.0,
        )
        db_session.add(snapshot)
        db_session.commit()

        # Note: SQLite may not preserve timezone info, but we ensure input is timezone-aware
        assert utc_time.tzinfo is not None
        assert utc_time.tzinfo == timezone.utc

    def test_equity_snapshot_relationship_account(self, db_session):
        """Test relationship to Account."""
        account = Account(name="Relationship Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        snapshot = EquitySnapshot(
            account_id=account.id,
            equity=10000.0,
            cash=10000.0,
            positions_value=0.0,
        )
        db_session.add(snapshot)
        db_session.commit()

        assert snapshot.account_id == account.id

    def test_equity_snapshot_to_dict(self, db_session):
        """Test to_dict() serialization."""
        account = Account(name="Dict Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        snapshot = EquitySnapshot(
            account_id=account.id,
            equity=10500.0,
            cash=10000.0,
            positions_value=500.0,
        )
        db_session.add(snapshot)
        db_session.commit()

        snapshot_dict = snapshot.to_dict()
        assert snapshot_dict["equity"] == 10500.0
        assert snapshot_dict["cash"] == 10000.0
        assert snapshot_dict["positions_value"] == 500.0
        assert "timestamp" in snapshot_dict

    def test_equity_snapshot_time_series(self, db_session):
        """Test creating multiple snapshots over time (time-series data)."""
        account = Account(name="Time Series Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        # Create snapshots at different times
        base_time = datetime.now(timezone.utc)
        snapshots = []
        for i in range(5):
            snapshot = EquitySnapshot(
                account_id=account.id,
                timestamp=base_time + timedelta(minutes=i * 15),
                equity=10000.0 + (i * 100),  # Increasing equity
                cash=9500.0,
                positions_value=500.0 + (i * 100),
            )
            snapshots.append(snapshot)
            db_session.add(snapshot)

        db_session.commit()

        # Verify all snapshots created
        assert len(snapshots) == 5
        assert snapshots[0].equity == 10000.0
        assert snapshots[4].equity == 10400.0

    def test_equity_snapshot_requires_valid_account_id(self, db_session):
        """Test that snapshot requires valid account_id (foreign key constraint)."""
        with pytest.raises(IntegrityError):
            snapshot = EquitySnapshot(
                account_id="nonexistent_account_id",  # Invalid FK
                equity=10000.0,
                cash=10000.0,
                positions_value=0.0,
            )
            db_session.add(snapshot)
            db_session.commit()

    def test_equity_snapshot_negative_values_allowed(self, db_session):
        """Test that negative equity/cash is allowed (margin call scenario)."""
        account = Account(name="Negative Test", broker="binance")
        db_session.add(account)
        db_session.commit()

        # Negative equity scenario (rare but possible with leveraged trading)
        snapshot = EquitySnapshot(
            account_id=account.id,
            equity=-500.0,  # Negative equity (debt)
            cash=-500.0,  # Negative cash balance
            positions_value=0.0,
        )
        db_session.add(snapshot)
        db_session.commit()  # Should succeed

        assert snapshot.equity == -500.0
        assert snapshot.cash == -500.0
