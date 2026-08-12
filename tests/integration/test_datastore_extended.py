"""Extended integration tests for DataStore coverage.

Tests previously uncovered methods:
- PnL history and records
- Equity snapshots
- Audit log retrieval
- Strategy assignments and signals
- Order/Trade/Position filtering methods
"""
from datetime import datetime, timezone, timedelta

from src.data.store import DataStore
from src.data.models import (
    PnLRecord, EquitySnapshot,
    StrategyAssignment, AssignmentStatus,
    Signal, SignalDirection
)

class TestDataStorePnL:
    """Test PnL and Equity Snapshot operations."""

    def test_save_and_get_pnl_history(self, test_db, sample_account):
        """Test saving PnL records and retrieving history."""
        store = DataStore()
        store.engine = test_db

        # Create 5 days of PnL history
        base_date = datetime.now(timezone.utc).date()
        for i in range(5):
            record_date = base_date - timedelta(days=i)
            pnl = PnLRecord(
                account_id=sample_account.id,
                record_date=record_date,
                realized_pnl=100.0 * (i + 1),
                unrealized_pnl=50.0,
                total_pnl=150.0 * (i + 1),
                portfolio_value=10000.0 + (150.0 * (i + 1)),
                cash_balance=5000.0,
                position_value=5000.0 + (150.0 * (i + 1)),
            )
            store.save_pnl_record(pnl)

        # Get history (last 3 days)
        # Note: get_pnl_history doesn't support limit or ordering by default, 
        # it returns all records in range.
        history = store.get_pnl_history(sample_account.id)
        # We created 5 records.
        assert len(history) == 5
        
        for record in history:
            assert record.account_id == sample_account.id
            assert record.total_pnl > 0

        # Get specific date
        specific_date = base_date - timedelta(days=1)
        record = store.get_pnl_for_date(sample_account.id, specific_date)
        assert record is not None
        assert record.record_date == specific_date

    def test_save_and_get_equity_snapshots(self, test_db, sample_account):
        """Test equity snapshot operations."""
        store = DataStore()
        store.engine = test_db

        # Create snapshots
        now = datetime.now(timezone.utc)
        for i in range(3):
            snapshot = EquitySnapshot(
                account_id=sample_account.id,
                timestamp=now - timedelta(hours=i),
                equity=10000.0 + (i * 100),
                cash=5000.0,
                positions_value=5000.0 + (i * 100),
            )
            store.save_equity_snapshot(snapshot)

        # Retrieve snapshots
        # get_equity_snapshots only supports start_time and limit
        snapshots = store.get_equity_snapshots(
            sample_account.id,
            start_time=now - timedelta(days=1),
            limit=10
        )
        assert len(snapshots) == 3
        assert snapshots[0].account_id == sample_account.id


class TestDataStoreAssignments:
    """Test Strategy Assignment operations."""

    def test_save_and_get_assignments(self, test_db, sample_account, sample_strategy):
        """Test strategy assignment lifecycle."""
        store = DataStore()
        store.engine = test_db

        # Create assignment
        assignment = StrategyAssignment(
            account_id=sample_account.id,
            strategy_id=sample_strategy.id,
            status=AssignmentStatus.ACTIVE,
            symbol="BTCUSDT",
            timeframe="1h",
            regime_filter=["trending_up"]
        )
        saved = store.save_assignment(assignment)
        assert saved.id is not None

        # Get active assignments
        active = store.get_active_assignments(sample_account.id)
        assert len(active) == 1
        assert active[0].strategy_id == sample_strategy.id
        assert active[0].status == AssignmentStatus.ACTIVE

        # Get all assignments
        all_assigns = store.get_assignments_for_account(sample_account.id)
        assert len(all_assigns) >= 1

        # Terminate assignment
        assignment.status = AssignmentStatus.STOPPED
        store.save_assignment(assignment)

        # Verify no longer active
        active_after = store.get_active_assignments(sample_account.id)
        assert len(active_after) == 0


class TestDataStoreSignals:
    """Test Signal operations."""

    def test_signal_lifecycle(self, test_db, sample_strategy):
        """Test signal creation, retrieval, and filtering."""
        store = DataStore()
        store.engine = test_db

        # Create signals
        signals_data = [
            (SignalDirection.LONG, False),   # Unexecuted
            (SignalDirection.SHORT, True),   # Executed
            (SignalDirection.LONG, False),   # Unexecuted
        ]

        for direction, executed in signals_data:
            signal = Signal(
                strategy_id=sample_strategy.id,
                symbol="BTCUSDT",
                direction=direction,
                price=50000.0,
                timestamp=datetime.now(timezone.utc),
                indicators={"rsi": 30},
                executed=executed
            )
            store.save_signal(signal)

        # Get unexecuted signals
        unexecuted = store.get_unexecuted_signals(sample_strategy.id)
        assert len(unexecuted) == 2
        for sig in unexecuted:
            assert sig.executed is False
            assert sig.strategy_id == sample_strategy.id

        # Get all signals for strategy
        all_signals = store.get_signals_for_strategy(sample_strategy.id)
        assert len(all_signals) == 3


class TestDataStoreAudit:
    """Test Audit Log retrieval."""

    def test_get_audit_logs(self, test_db):
        """Test retrieving audit logs with filters."""
        store = DataStore()
        store.engine = test_db

        # Create logs
        actions = ["LOGIN", "TRADE", "LOGOUT"]
        
        for i, action in enumerate(actions):
            store.add_audit_log(
                action=action,
                actor="user",
                details={"index": i}
            )

        # Test limit
        logs_limit = store.get_audit_logs(limit=2)
        assert len(logs_limit) == 2

        # Test actor filter (add a different actor)
        store.add_audit_log("SYSTEM_ACTION", "system", {})
        
        user_logs = store.get_audit_logs(actor="user")
        assert len(user_logs) == 3  # The original 3
        system_logs = store.get_audit_logs(actor="system")
        assert len(system_logs) == 1

        # Test action filter
        trade_logs = store.get_audit_logs(action="TRADE")
        # Ensure we have at least one TRADE log
        assert len(trade_logs) >= 1
        assert trade_logs[0].action == "TRADE"
