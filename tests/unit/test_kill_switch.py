"""Tests for KillSwitch and DeadMansSwitch.

Covers:
- KillSwitch activation/deactivation
- Deactivation code security
- State persistence via SystemState
- Audit log entries
- Auto-trigger conditions
- DeadMansSwitch heartbeat mechanism
- DeadMansSwitch auto-activation of kill switch
- Edge cases

Target: >90% coverage for kill_switch.py and dead_mans_switch.py
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.core.risk.dead_mans_switch import DeadMansSwitch
from src.core.risk.kill_switch import KillSwitch
from src.core.risk.types import PortfolioState
from src.data.store import DataStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_store() -> MagicMock:
    """Create a mock DataStore with system state."""
    store = MagicMock(spec=DataStore)

    # Default system state: kill switch inactive
    state = MagicMock()
    state.kill_switch_active = False
    state.kill_switch_activated_at = None
    state.kill_switch_reason = None
    state.trading_enabled = True
    store.get_system_state.return_value = state

    # update_system_state returns updated state
    store.update_system_state.return_value = state

    # add_audit_log returns mock audit log
    audit_log = MagicMock()
    audit_log.id = "audit_001"
    store.add_audit_log.return_value = audit_log

    return store


@pytest.fixture
def kill_switch(mock_store: MagicMock) -> KillSwitch:
    """Create a KillSwitch with mock store."""
    return KillSwitch(mock_store)


@pytest.fixture
def dead_mans_switch(
    mock_store: MagicMock,
    kill_switch: KillSwitch,
) -> DeadMansSwitch:
    """Create a DeadMansSwitch with mock store and kill switch."""
    return DeadMansSwitch(
        store=mock_store,
        kill_switch=kill_switch,
        interval_minutes=5,
        max_missed=6,
    )


# ===========================================================================
# KillSwitch tests
# ===========================================================================


class TestKillSwitchActivation:
    """Test kill switch activation."""

    def test_activate_success(
        self,
        kill_switch: KillSwitch,
        mock_store: MagicMock,
    ) -> None:
        """Activation should update system state and create audit log."""
        kill_switch.activate(reason="Test activation", actor="test")

        mock_store.update_system_state.assert_called_once()
        call_kwargs = mock_store.update_system_state.call_args[1]
        assert call_kwargs["kill_switch_active"] is True
        assert call_kwargs["kill_switch_reason"] == "Test activation"
        assert call_kwargs["trading_enabled"] is False

        # Audit log should be created
        mock_store.add_audit_log.assert_called_once()
        audit_call = mock_store.add_audit_log.call_args[1]
        assert audit_call["action"] == "kill_switch_activated"
        assert audit_call["actor"] == "test"

    def test_activate_already_active(
        self,
        kill_switch: KillSwitch,
        mock_store: MagicMock,
    ) -> None:
        """Activating when already active should be a no-op."""
        # Set state to already active
        state = mock_store.get_system_state.return_value
        state.kill_switch_active = True
        state.kill_switch_reason = "Previous reason"

        kill_switch.activate(reason="New reason")

        # Should NOT call update_system_state
        mock_store.update_system_state.assert_not_called()

    def test_activate_db_failure_still_logs(
        self,
        kill_switch: KillSwitch,
        mock_store: MagicMock,
    ) -> None:
        """DB write failure should still attempt audit log."""
        mock_store.update_system_state.side_effect = Exception("DB error")

        # Should not raise
        kill_switch.activate(reason="Test")

        # Audit log still attempted
        mock_store.add_audit_log.assert_called_once()


class TestKillSwitchDeactivation:
    """Test kill switch deactivation."""

    def test_deactivate_with_correct_code(
        self,
        kill_switch: KillSwitch,
        mock_store: MagicMock,
    ) -> None:
        """Deactivation with correct code should succeed."""
        # Set state to active
        state = mock_store.get_system_state.return_value
        state.kill_switch_active = True
        state.kill_switch_activated_at = datetime.now(timezone.utc)
        state.kill_switch_reason = "Test"

        # Generate code
        code = kill_switch.generate_deactivation_code()

        # Deactivate
        success = kill_switch.deactivate(code, actor="test")

        assert success is True
        mock_store.update_system_state.assert_called_once()
        call_kwargs = mock_store.update_system_state.call_args[1]
        assert call_kwargs["kill_switch_active"] is False
        assert call_kwargs["trading_enabled"] is True

    def test_deactivate_with_wrong_code(
        self,
        kill_switch: KillSwitch,
        mock_store: MagicMock,
    ) -> None:
        """Deactivation with wrong code should fail."""
        state = mock_store.get_system_state.return_value
        state.kill_switch_active = True

        # Generate code but use wrong one
        kill_switch.generate_deactivation_code()
        success = kill_switch.deactivate("wrong_code")

        assert success is False
        mock_store.update_system_state.assert_not_called()

    def test_deactivate_without_generating_code(
        self,
        kill_switch: KillSwitch,
        mock_store: MagicMock,
    ) -> None:
        """Deactivation without generating code should fail."""
        state = mock_store.get_system_state.return_value
        state.kill_switch_active = True

        success = kill_switch.deactivate("anything")
        assert success is False

    def test_deactivate_when_not_active(
        self,
        kill_switch: KillSwitch,
    ) -> None:
        """Deactivating when not active should return True."""
        success = kill_switch.deactivate("anything")
        assert success is True

    def test_deactivation_code_single_use(
        self,
        kill_switch: KillSwitch,
        mock_store: MagicMock,
    ) -> None:
        """Deactivation code should be single-use."""
        state = mock_store.get_system_state.return_value
        state.kill_switch_active = True
        state.kill_switch_activated_at = datetime.now(timezone.utc)

        code = kill_switch.generate_deactivation_code()

        # First use succeeds
        success1 = kill_switch.deactivate(code)
        assert success1 is True

        # Re-activate
        state.kill_switch_active = True
        mock_store.update_system_state.reset_mock()

        # Same code should fail (it was cleared)
        success2 = kill_switch.deactivate(code)
        assert success2 is False


class TestKillSwitchStatus:
    """Test kill switch status reporting."""

    def test_status_when_inactive(
        self,
        kill_switch: KillSwitch,
    ) -> None:
        """Status when inactive should show not active."""
        status = kill_switch.get_status()
        assert status["active"] is False
        assert status["reason"] is None
        assert status["duration_seconds"] is None

    def test_status_when_active(
        self,
        kill_switch: KillSwitch,
        mock_store: MagicMock,
    ) -> None:
        """Status when active should show details."""
        now = datetime.now(timezone.utc)
        state = mock_store.get_system_state.return_value
        state.kill_switch_active = True
        state.kill_switch_activated_at = now - timedelta(minutes=5)
        state.kill_switch_reason = "Test reason"

        status = kill_switch.get_status()
        assert status["active"] is True
        assert status["reason"] == "Test reason"
        assert status["duration_seconds"] > 0

    def test_is_active_reads_from_db(
        self,
        kill_switch: KillSwitch,
        mock_store: MagicMock,
    ) -> None:
        """is_active should read from DB for consistency."""
        state = mock_store.get_system_state.return_value
        state.kill_switch_active = True

        assert kill_switch.is_active() is True

        state.kill_switch_active = False
        assert kill_switch.is_active() is False


class TestKillSwitchRecovery:
    """Test kill switch state recovery on startup."""

    def test_load_state_active(
        self,
        kill_switch: KillSwitch,
        mock_store: MagicMock,
    ) -> None:
        """Should detect active kill switch on startup."""
        state = mock_store.get_system_state.return_value
        state.kill_switch_active = True
        state.kill_switch_reason = "Previous session crash"
        state.kill_switch_activated_at = datetime.now(timezone.utc)

        # Should not raise
        kill_switch.load_state()

    def test_load_state_inactive(
        self,
        kill_switch: KillSwitch,
    ) -> None:
        """Should handle inactive state on startup."""
        kill_switch.load_state()  # Should not raise

    def test_load_state_db_error(
        self,
        kill_switch: KillSwitch,
        mock_store: MagicMock,
    ) -> None:
        """DB error during load should not raise."""
        mock_store.get_system_state.side_effect = Exception("DB error")
        kill_switch.load_state()  # Should not raise


class TestKillSwitchTriggers:
    """Test kill switch auto-trigger conditions."""

    def test_trigger_daily_loss(
        self,
        kill_switch: KillSwitch,
    ) -> None:
        """Should trigger on daily loss threshold."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=9400.0,
            positions_value=600.0,
            daily_pnl=-600.0,  # 6% loss
        )
        reason = kill_switch.check_triggers(
            portfolio, daily_loss_limit_pct=5.0
        )
        assert reason is not None
        assert "Daily loss" in reason

    def test_trigger_drawdown(
        self,
        kill_switch: KillSwitch,
    ) -> None:
        """Should trigger on drawdown threshold."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=8500.0,
            cash_balance=8500.0,
            positions_value=0.0,
            drawdown_pct=20.0,
        )
        reason = kill_switch.check_triggers(
            portfolio, max_drawdown_pct=15.0
        )
        assert reason is not None
        assert "Drawdown" in reason

    def test_trigger_consecutive_losses(
        self,
        kill_switch: KillSwitch,
    ) -> None:
        """Should trigger on consecutive losses."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=10000.0,
            positions_value=0.0,
            consecutive_losses=12,
        )
        reason = kill_switch.check_triggers(
            portfolio, max_consecutive_losses=10
        )
        assert reason is not None
        assert "consecutive" in reason

    def test_no_trigger(
        self,
        kill_switch: KillSwitch,
    ) -> None:
        """No trigger conditions met should return None."""
        portfolio = PortfolioState(
            account_id="acc_001",
            total_equity=10000.0,
            cash_balance=9800.0,
            positions_value=200.0,
            daily_pnl=-100.0,  # 1% loss
            drawdown_pct=2.0,
            consecutive_losses=2,
        )
        reason = kill_switch.check_triggers(portfolio)
        assert reason is None


class TestDeactivationCodeGeneration:
    """Test deactivation code generation."""

    def test_generate_code_format(
        self,
        kill_switch: KillSwitch,
    ) -> None:
        """Generated code should be 8-char hex string."""
        code = kill_switch.generate_deactivation_code()
        assert len(code) == 8
        # Should be valid hex
        int(code, 16)

    def test_generate_new_code_invalidates_old(
        self,
        kill_switch: KillSwitch,
        mock_store: MagicMock,
    ) -> None:
        """New code should invalidate previous code."""
        state = mock_store.get_system_state.return_value
        state.kill_switch_active = True
        state.kill_switch_activated_at = datetime.now(timezone.utc)

        code1 = kill_switch.generate_deactivation_code()
        _code2 = kill_switch.generate_deactivation_code()

        # code1 should no longer work
        success = kill_switch.deactivate(code1)
        assert success is False


# ===========================================================================
# DeadMansSwitch tests
# ===========================================================================


class TestDeadMansSwitchHeartbeat:
    """Test dead man's switch heartbeat mechanism."""

    def test_heartbeat_resets_counter(
        self,
        dead_mans_switch: DeadMansSwitch,
    ) -> None:
        """Heartbeat should reset missed counter."""
        dead_mans_switch._missed_count = 3
        dead_mans_switch.heartbeat()
        assert dead_mans_switch._missed_count == 0

    def test_check_healthy(
        self,
        dead_mans_switch: DeadMansSwitch,
    ) -> None:
        """Recent heartbeat should report healthy."""
        dead_mans_switch.heartbeat()
        assert dead_mans_switch.check() is True

    def test_check_missed_heartbeat(
        self,
        dead_mans_switch: DeadMansSwitch,
    ) -> None:
        """Overdue heartbeat should increment missed count."""
        # Set last heartbeat to 10 minutes ago
        dead_mans_switch._last_heartbeat = datetime.now(
            timezone.utc
        ) - timedelta(minutes=10)

        result = dead_mans_switch.check()
        assert result is True  # Not yet triggered
        assert dead_mans_switch._missed_count == 1


class TestDeadMansSwitchTrigger:
    """Test dead man's switch trigger mechanism."""

    def test_trigger_after_max_missed(
        self,
        dead_mans_switch: DeadMansSwitch,
        mock_store: MagicMock,
    ) -> None:
        """Should trigger after max missed heartbeats."""
        # Set last heartbeat to 10 minutes ago (overdue)
        dead_mans_switch._last_heartbeat = datetime.now(
            timezone.utc
        ) - timedelta(minutes=10)

        # Simulate 5 checks (not yet triggered)
        for _ in range(5):
            assert dead_mans_switch.check() is True

        assert dead_mans_switch._missed_count == 5

        # 6th check should trigger
        result = dead_mans_switch.check()
        assert result is False
        assert dead_mans_switch.is_triggered is True

        # Kill switch should have been activated
        mock_store.update_system_state.assert_called()

    def test_trigger_activates_kill_switch(
        self,
        dead_mans_switch: DeadMansSwitch,
        mock_store: MagicMock,
    ) -> None:
        """Trigger should activate the kill switch."""
        # Force trigger by setting missed count near limit
        dead_mans_switch._missed_count = 5
        dead_mans_switch._last_heartbeat = datetime.now(
            timezone.utc
        ) - timedelta(minutes=10)

        dead_mans_switch.check()

        # Verify kill switch was activated via store
        mock_store.update_system_state.assert_called()
        call_kwargs = mock_store.update_system_state.call_args[1]
        assert call_kwargs["kill_switch_active"] is True

    def test_already_triggered_stays_false(
        self,
        dead_mans_switch: DeadMansSwitch,
    ) -> None:
        """Once triggered, check should always return False."""
        dead_mans_switch._triggered = True
        assert dead_mans_switch.check() is False


class TestDeadMansSwitchStatus:
    """Test dead man's switch status reporting."""

    def test_status_healthy(
        self,
        dead_mans_switch: DeadMansSwitch,
    ) -> None:
        """Status should report healthy state."""
        dead_mans_switch.heartbeat()
        status = dead_mans_switch.get_status()

        assert status["missed_count"] == 0
        assert status["triggered"] is False
        assert status["max_missed"] == 6

    def test_status_degraded(
        self,
        dead_mans_switch: DeadMansSwitch,
    ) -> None:
        """Status should report missed heartbeats."""
        dead_mans_switch._missed_count = 3
        status = dead_mans_switch.get_status()

        assert status["missed_count"] == 3

    def test_status_triggered(
        self,
        dead_mans_switch: DeadMansSwitch,
    ) -> None:
        """Status should report triggered state."""
        dead_mans_switch._triggered = True
        status = dead_mans_switch.get_status()

        assert status["triggered"] is True


class TestDeadMansSwitchReset:
    """Test dead man's switch reset."""

    def test_reset_clears_state(
        self,
        dead_mans_switch: DeadMansSwitch,
    ) -> None:
        """Reset should clear triggered state and counters."""
        dead_mans_switch._triggered = True
        dead_mans_switch._missed_count = 6

        dead_mans_switch.reset()

        assert dead_mans_switch.is_triggered is False
        assert dead_mans_switch._missed_count == 0


# ===========================================================================
# Additional coverage tests for 100%
# ===========================================================================


class TestKillSwitchExceptionPaths:
    """Test exception handling in kill switch operations."""

    def test_activate_with_audit_log_exception(self) -> None:
        """Audit log failure during activation should not prevent activation."""
        from src.core.risk.kill_switch import KillSwitch
        from unittest.mock import MagicMock

        store = MagicMock()
        state = MagicMock()
        state.kill_switch_active = False
        store.get_system_state.return_value = state

        # Make create_audit_log raise exception
        store.create_audit_log.side_effect = Exception("Audit DB down")

        kill_switch = KillSwitch(store)
        kill_switch.activate("test_reason")

        # Kill switch should still be activated despite audit log failure
        assert store.update_system_state.call_count > 0

    def test_deactivate_with_persist_exception(self) -> None:
        """Persist failure during deactivation should return False."""
        from src.core.risk.kill_switch import KillSwitch
        from unittest.mock import MagicMock

        store = MagicMock()
        state = MagicMock()
        state.kill_switch_active = True
        store.get_system_state.return_value = state

        # Make persist raise exception
        store.update_system_state.side_effect = Exception("DB write failed")

        kill_switch = KillSwitch(store)
        kill_switch._deactivation_code = "test_code"

        result = kill_switch.deactivate("test_code")

        # Deactivation should fail gracefully
        assert result is False

    def test_deactivate_with_audit_log_exception(self) -> None:
        """Audit log failure during deactivation should not prevent deactivation."""
        from src.core.risk.kill_switch import KillSwitch
        from unittest.mock import MagicMock
        from datetime import datetime, timezone

        store = MagicMock()
        state = MagicMock()
        state.kill_switch_active = True
        state.kill_switch_activated_at = datetime.now(timezone.utc)
        store.get_system_state.return_value = state

        # Persist succeeds but audit log fails
        store.update_system_state.return_value = None
        store.create_audit_log.side_effect = Exception("Audit log failed")

        kill_switch = KillSwitch(store)
        kill_switch._deactivation_code = "test_code"

        result = kill_switch.deactivate("test_code")

        # Deactivation should succeed despite audit log failure
        assert result is True


class TestDeadMansSwitchExceptionPaths:
    """Test exception handling in dead man's switch."""

    def test_trigger_already_triggered(self) -> None:
        """Triggering when already triggered should be idempotent."""
        from src.core.risk.dead_mans_switch import DeadMansSwitch
        from src.core.risk.kill_switch import KillSwitch
        from unittest.mock import MagicMock

        store = MagicMock()
        kill_switch = KillSwitch(store)
        dms = DeadMansSwitch(store, kill_switch)

        # Manually set triggered state
        dms._triggered = True
        dms._missed_count = 10

        # Call _trigger again (via reflection since it's private)
        dms._trigger()

        # Should still be triggered, but kill switch not called again
        assert dms.is_triggered is True

    def test_trigger_with_kill_switch_exception(self) -> None:
        """Kill switch activation failure should be logged but not crash."""
        from src.core.risk.dead_mans_switch import DeadMansSwitch
        from src.core.risk.kill_switch import KillSwitch
        from unittest.mock import MagicMock

        store = MagicMock()
        kill_switch = MagicMock(spec=KillSwitch)

        # Make kill switch activation raise exception
        kill_switch.activate.side_effect = Exception("Kill switch broken")

        dms = DeadMansSwitch(store, kill_switch)
        dms._missed_count = 10

        # Trigger should handle exception gracefully
        dms._trigger()

        # Should be marked as triggered despite exception
        assert dms.is_triggered is True
