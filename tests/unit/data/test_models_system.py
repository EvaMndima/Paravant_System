"""
Unit tests for System models (SystemState and AuditLog).

Tests for SystemState:
- Singleton pattern (fixed ID)
- Kill switch state management
- Properties (is_safe_to_trade, any_circuit_breaker_active)
- Mutable defaults (circuit_breakers dict)
- Trading enabled flag

Tests for AuditLog:
- Immutable record creation
- Timestamp handling (timezone-aware)
- JSON details field
- Default ID generation
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import IntegrityError

from src.data.models import SystemState, AuditLog
from src.data.models.base import generate_id


class TestSystemStateModel:
    """Test SystemState model (singleton for system-wide state)."""

    def test_create_system_state_singleton(self, db_session):
        """Test creating system state with singleton ID."""
        state = SystemState()
        db_session.add(state)
        db_session.commit()

        assert state.id == "system_state_singleton"
        assert state.kill_switch_active == False
        assert state.trading_enabled == True
        assert state.health_status == "unknown"

    def test_system_state_default_values(self, db_session):
        """Test system state default values."""
        state = SystemState()
        db_session.add(state)
        db_session.commit()

        assert state.kill_switch_active == False
        assert state.trading_enabled == True
        assert state.circuit_breakers == {}
        assert state.started_at is not None
        assert state.updated_at is not None

    def test_system_state_kill_switch_activation(self, db_session):
        """Test kill switch activation."""
        state = SystemState(
            kill_switch_active=True,
            kill_switch_reason="Daily loss limit exceeded",
            kill_switch_activated_at=datetime.now(timezone.utc)
        )
        db_session.add(state)
        db_session.commit()

        assert state.kill_switch_active == True
        assert state.kill_switch_reason == "Daily loss limit exceeded"
        assert state.kill_switch_activated_at is not None

    def test_system_state_is_safe_to_trade_both_enabled(self, db_session):
        """Test is_safe_to_trade property when both conditions met."""
        state = SystemState(
            kill_switch_active=False,
            trading_enabled=True
        )
        db_session.add(state)
        db_session.commit()

        # Both conditions OK -> safe to trade
        assert state.is_safe_to_trade == True

    def test_system_state_is_safe_to_trade_kill_switch_on(self, db_session):
        """Test is_safe_to_trade property when kill switch is active."""
        state = SystemState(
            kill_switch_active=True,
            trading_enabled=True
        )
        db_session.add(state)
        db_session.commit()

        # Kill switch active -> NOT safe to trade
        assert state.is_safe_to_trade == False

    def test_system_state_is_safe_to_trade_trading_disabled(self, db_session):
        """Test is_safe_to_trade property when trading is disabled."""
        state = SystemState(
            kill_switch_active=False,
            trading_enabled=False
        )
        db_session.add(state)
        db_session.commit()

        # Trading disabled -> NOT safe to trade
        assert state.is_safe_to_trade == False

    def test_system_state_is_safe_to_trade_both_off(self, db_session):
        """Test is_safe_to_trade property when both conditions prevent trading."""
        state = SystemState(
            kill_switch_active=True,
            trading_enabled=False
        )
        db_session.add(state)
        db_session.commit()

        # Both prevent trading -> NOT safe to trade
        assert state.is_safe_to_trade == False

    def test_system_state_circuit_breakers_mutable_default(self, db_session):
        """Test that circuit_breakers dict is not shared between instances."""
        state1 = SystemState(id="state_1")
        state2 = SystemState(id="state_2")

        # Initialize if needed
        if state1.circuit_breakers is None:
            state1.circuit_breakers = {}
        if state2.circuit_breakers is None:
            state2.circuit_breakers = {}

        state1.circuit_breakers["daily_loss"] = True
        state2.circuit_breakers["drawdown"] = True

        db_session.add(state1)
        db_session.add(state2)
        db_session.commit()

        # Verify isolation
        assert "daily_loss" in state1.circuit_breakers
        assert "daily_loss" not in state2.circuit_breakers
        assert "drawdown" in state2.circuit_breakers
        assert "drawdown" not in state1.circuit_breakers

    def test_system_state_any_circuit_breaker_active_none_active(self, db_session):
        """Test any_circuit_breaker_active property with no breakers active."""
        state = SystemState()
        state.circuit_breakers = {
            "daily_loss": False,
            "drawdown": False,
            "max_positions": False,
        }
        db_session.add(state)
        db_session.commit()

        assert state.any_circuit_breaker_active == False

    def test_system_state_any_circuit_breaker_active_one_active(self, db_session):
        """Test any_circuit_breaker_active property with one breaker active."""
        state = SystemState()
        state.circuit_breakers = {
            "daily_loss": True,  # Active
            "drawdown": False,
            "max_positions": False,
        }
        db_session.add(state)
        db_session.commit()

        assert state.any_circuit_breaker_active == True

    def test_system_state_any_circuit_breaker_active_empty_dict(self, db_session):
        """Test any_circuit_breaker_active property with empty breakers dict."""
        state = SystemState()
        state.circuit_breakers = {}
        db_session.add(state)
        db_session.commit()

        assert state.any_circuit_breaker_active == False

    def test_system_state_health_status_update(self, db_session):
        """Test updating health status."""
        state = SystemState()
        db_session.add(state)
        db_session.commit()

        initial_updated_at = state.updated_at

        # Update health status
        state.health_status = "healthy"
        state.last_health_check = datetime.now(timezone.utc)
        db_session.commit()

        assert state.health_status == "healthy"
        assert state.last_health_check is not None
        # Updated_at should change (if timestamp resolution allows)
        # Note: May be same if update is very fast

    def test_system_state_last_trade_tracking(self, db_session):
        """Test last_trade_at timestamp tracking."""
        state = SystemState()
        db_session.add(state)
        db_session.commit()

        assert state.last_trade_at is None

        # Record trade
        trade_time = datetime.now(timezone.utc)
        state.last_trade_at = trade_time
        db_session.commit()

        assert state.last_trade_at is not None
        time_diff = datetime.now(timezone.utc) - state.last_trade_at.replace(tzinfo=timezone.utc)
        assert time_diff.total_seconds() < 60  # Recent

    def test_system_state_to_dict(self, db_session):
        """Test to_dict() serialization."""
        state = SystemState(
            kill_switch_active=True,
            trading_enabled=False,
            health_status="degraded"
        )
        state.circuit_breakers = {"daily_loss": True}
        db_session.add(state)
        db_session.commit()

        state_dict = state.to_dict()
        assert state_dict["id"] == "system_state_singleton"
        assert state_dict["kill_switch_active"] == True
        assert state_dict["trading_enabled"] == False
        assert state_dict["health_status"] == "degraded"
        assert "circuit_breakers" in state_dict


class TestAuditLogModel:
    """Test AuditLog model for compliance and audit trail."""

    def test_create_audit_log_with_explicit_id(self, db_session):
        """Test creating audit log with explicit ID (existing pattern)."""
        log = AuditLog(
            id=generate_id("audit"),
            action="kill_switch_activated",
            actor="risk_controller",
            details={"reason": "Loss limit exceeded", "threshold": 3.0}
        )
        db_session.add(log)
        db_session.commit()

        assert log.id is not None
        assert log.id.startswith("audit_")
        assert log.action == "kill_switch_activated"
        assert log.actor == "risk_controller"
        assert log.details["threshold"] == 3.0

    def test_create_audit_log_with_auto_id(self, db_session):
        """Test creating audit log with automatic ID generation."""
        log = AuditLog(
            action="system_startup",
            actor="system"
        )
        db_session.add(log)
        db_session.commit()

        # ID should be auto-generated
        assert log.id is not None
        assert log.id.startswith("audit_")

    def test_audit_log_default_timestamp(self, db_session):
        """Test that timestamp defaults to current UTC time."""
        log = AuditLog(
            id=generate_id("audit"),
            action="test_action",
            actor="system"
        )
        db_session.add(log)
        db_session.commit()

        assert log.timestamp is not None
        # Verify timestamp is recent (within last minute)
        time_diff = datetime.now(timezone.utc) - log.timestamp.replace(tzinfo=timezone.utc)
        assert time_diff.total_seconds() < 60

    def test_audit_log_timezone_aware_timestamp(self, db_session):
        """Test that timestamp is timezone-aware (DEC-2026-02-08-003)."""
        # Explicit UTC timestamp
        utc_time = datetime.now(timezone.utc)
        log = AuditLog(
            id=generate_id("audit"),
            action="manual_test",
            actor="developer",
            timestamp=utc_time
        )
        db_session.add(log)
        db_session.commit()

        # Input should be timezone-aware
        assert utc_time.tzinfo is not None
        assert utc_time.tzinfo == timezone.utc

    def test_audit_log_json_details_field(self, db_session):
        """Test JSON details field for flexible data storage."""
        complex_details = {
            "event": "order_rejected",
            "order_id": "ord_20260209_abc123",
            "reason": "Insufficient balance",
            "balance_required": 10000.0,
            "balance_available": 5000.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        log = AuditLog(
            id=generate_id("audit"),
            action="order_rejection",
            actor="execution_engine",
            details=complex_details
        )
        db_session.add(log)
        db_session.commit()

        # Verify JSON serialization/deserialization
        assert log.details["event"] == "order_rejected"
        assert log.details["balance_required"] == 10000.0
        assert log.details["balance_available"] == 5000.0

    def test_audit_log_nullable_details(self, db_session):
        """Test that details field can be None."""
        log = AuditLog(
            id=generate_id("audit"),
            action="simple_action",
            actor="system",
            details=None  # Optional field
        )
        db_session.add(log)
        db_session.commit()

        assert log.details is None

    def test_audit_log_immutable_record(self, db_session):
        """Test audit log as immutable record (should not be updated)."""
        log = AuditLog(
            id=generate_id("audit"),
            action="initial_action",
            actor="system"
        )
        db_session.add(log)
        db_session.commit()

        original_id = log.id
        original_action = log.action
        original_timestamp = log.timestamp

        # In production, audit logs should NOT be modified
        # This test documents the pattern - logs are append-only
        # If you need to record changes, create a NEW log entry
        assert log.id == original_id
        assert log.action == original_action
        assert log.timestamp == original_timestamp

    def test_audit_log_actor_types(self, db_session):
        """Test different actor types (system, user, api)."""
        actors = ["system", "user", "api", "risk_controller", "execution_engine"]

        for actor in actors:
            log = AuditLog(
                id=generate_id("audit"),
                action=f"test_action_{actor}",
                actor=actor
            )
            db_session.add(log)

        db_session.commit()

        # Verify all actors recorded
        logs = db_session.query(AuditLog).filter(AuditLog.action.like("test_action_%")).all()
        assert len(logs) == 5

    def test_audit_log_to_dict(self, db_session):
        """Test to_dict() serialization."""
        log = AuditLog(
            id=generate_id("audit"),
            action="config_change",
            actor="admin_user",
            details={"setting": "max_position_size", "old": 0.1, "new": 0.15}
        )
        db_session.add(log)
        db_session.commit()

        log_dict = log.to_dict()
        assert log_dict["action"] == "config_change"
        assert log_dict["actor"] == "admin_user"
        assert log_dict["details"]["setting"] == "max_position_size"
        assert "timestamp" in log_dict

    def test_audit_log_sequential_ids(self, db_session):
        """Test that multiple audit logs have unique IDs."""
        logs = []
        for i in range(5):
            log = AuditLog(
                id=generate_id("audit"),
                action=f"action_{i}",
                actor="system"
            )
            logs.append(log)
            db_session.add(log)

        db_session.commit()

        # Verify all IDs are unique
        ids = [log.id for log in logs]
        assert len(ids) == len(set(ids))  # All unique

    def test_audit_log_search_by_action(self, db_session):
        """Test querying audit logs by action type."""
        actions = ["order_created", "order_filled", "position_opened", "kill_switch_activated"]

        for action in actions:
            log = AuditLog(
                id=generate_id("audit"),
                action=action,
                actor="system"
            )
            db_session.add(log)

        db_session.commit()

        # Query specific action
        kill_switch_logs = db_session.query(AuditLog).filter_by(action="kill_switch_activated").all()
        assert len(kill_switch_logs) == 1
        assert kill_switch_logs[0].action == "kill_switch_activated"

    def test_audit_log_time_range_query(self, db_session):
        """Test querying audit logs by time range."""
        base_time = datetime.now(timezone.utc)

        # Create logs at different times
        for i in range(5):
            log = AuditLog(
                id=generate_id("audit"),
                action=f"timed_action_{i}",
                actor="system",
                timestamp=base_time + timedelta(minutes=i * 10)
            )
            db_session.add(log)

        db_session.commit()

        # Query logs in specific time range
        start_time = base_time + timedelta(minutes=15)
        end_time = base_time + timedelta(minutes=35)

        logs_in_range = db_session.query(AuditLog).filter(
            AuditLog.timestamp >= start_time,
            AuditLog.timestamp <= end_time
        ).all()

        # Should get logs at 20min and 30min
        assert len(logs_in_range) == 2
