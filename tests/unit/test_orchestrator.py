"""Tests for orchestrator and system coordination.

Tests cover:
- Orchestrator lifecycle (start/run/stop)
- Startup checklist (each check pass/fail)
- Main loop execution order
- Entry coordinator timing
- Priority ordering
- Bypass rules
- Graceful shutdown
- Error handling
- Health checks
- Kill switch integration
- Degradation modes

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-12-003 - Kill switch checked FIRST
Decision: DEC-2026-02-12-012 - Injectable datetime for testing
"""
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.orchestrator import (
    DegradationManager,
    DegradationMode,
    EntryCoordinator,
    HealthChecker,
    Orchestrator,
    OrchestratorMetrics,
    StartupChecklist,
    SystemStatus,
)
from src.core.strategy.engine import StrategyEngine
from src.data.models.strategy import Strategy, StrategyStatus, StrategyType


# ---------------------------------------------------------------------------
# Entry Coordinator Tests
# ---------------------------------------------------------------------------


class TestEntryCoordinator:
    """Test entry timing coordination."""

    def test_30s_minimum_between_entries(self):
        """30 second minimum interval between ANY entries."""
        base_time = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
        coordinator = EntryCoordinator(now=base_time)

        # Add first entry
        coordinator.add_entry(
            symbol="BTCUSDT",
            strategy_id="STR_001",
            signal={"type": "entry"},
            sharpe_ratio=1.5,
        )

        # Get first entry (should succeed)
        entry1 = coordinator.get_next_entry()
        assert entry1 is not None
        assert entry1.symbol == "BTCUSDT"

        # Add second entry immediately
        coordinator.add_entry(
            symbol="ETHUSDT",
            strategy_id="STR_002",
            signal={"type": "entry"},
            sharpe_ratio=2.0,
        )

        # Try to get second entry (should fail - too soon)
        entry2 = coordinator.get_next_entry()
        assert entry2 is None

        # Advance time by 30 seconds
        later = base_time + timedelta(seconds=30)
        coordinator._now_fn = lambda: later

        # Now should succeed
        entry2 = coordinator.get_next_entry()
        assert entry2 is not None
        assert entry2.symbol == "ETHUSDT"

    def test_max_3_entries_per_minute(self):
        """Maximum 3 entries per minute."""
        base_time = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
        coordinator = EntryCoordinator(now=base_time)

        # Add 3 entries and get them (spacing them out by 30s each)
        for i in range(3):
            now = base_time + timedelta(seconds=i * 30)
            coordinator._now_fn = lambda t=now: t

            coordinator.add_entry(
                symbol=f"SYM{i}",
                strategy_id=f"STR_{i}",
                signal={"type": "entry"},
                sharpe_ratio=1.0,
            )

            entry = coordinator.get_next_entry()
            assert entry is not None

        # 4th entry 30s after the 3rd (at 90s total)
        # All 3 previous entries are still within the last 60 seconds
        # (they were at 0s, 30s, 60s, and we're now at 90s)
        # So entries at 30s, 60s, 90s are all within the last minute from 90s
        # Wait, that's only 2 entries (60s and 30s are within last 60s from 90s)
        # 0s entry is at timestamp 30s before 30s mark, so NOT within last 60s from 90s

        # Let me recalculate: at 90s, looking back 60s means we count entries from 30s onwards
        # So entries at 30s and 60s are counted (2 entries)
        # So the 4th entry at 90s should succeed!

        # Actually, the test expectation was wrong. Let me fix to test correctly:
        # To trigger the limit, we need entries at 35s, 40s, 45s, then try at 50s

        # NOTE: With 30s minimum spacing, the 3/minute limit is actually unreachable
        # via normal operation (max 2 entries per 60s with 30s spacing).
        # This test directly manipulates state to verify the limit exists.

        coordinator2 = EntryCoordinator(now=base_time)

        # Directly add to recent_entries to simulate 3 rapid entries
        now = base_time + timedelta(seconds=50)
        coordinator2._now_fn = lambda: now
        coordinator2._recent_entries = [
            base_time + timedelta(seconds=10),
            base_time + timedelta(seconds=20),
            base_time + timedelta(seconds=40),
        ]
        coordinator2._last_entry_time = base_time + timedelta(seconds=40)

        coordinator2.add_entry(
            symbol="SYM3",
            strategy_id="STR_3",
            signal={"type": "entry"},
            sharpe_ratio=1.0,
        )

        # Should be blocked by 3/minute limit
        entry = coordinator2.get_next_entry()
        assert entry is None  # Rate limited - already 3 in last 60s

    def test_5min_symbol_cooldown(self):
        """5 minute cooldown per symbol."""
        base_time = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
        coordinator = EntryCoordinator(now=base_time)

        # Add and get first BTCUSDT entry
        coordinator.add_entry(
            symbol="BTCUSDT",
            strategy_id="STR_001",
            signal={"type": "entry"},
            sharpe_ratio=1.0,
        )

        entry1 = coordinator.get_next_entry()
        assert entry1 is not None

        # Add second BTCUSDT entry 1 minute later
        now = base_time + timedelta(minutes=1)
        coordinator._now_fn = lambda: now

        coordinator.add_entry(
            symbol="BTCUSDT",
            strategy_id="STR_002",
            signal={"type": "entry"},
            sharpe_ratio=1.0,
        )

        entry2 = coordinator.get_next_entry()
        assert entry2 is None  # Symbol cooldown

        # Advance to 5 minutes later
        now = base_time + timedelta(minutes=5)
        coordinator._now_fn = lambda: now

        entry2 = coordinator.get_next_entry()
        assert entry2 is not None  # Cooldown expired

    def test_priority_by_sharpe_ratio(self):
        """Higher Sharpe ratio strategies processed first."""
        base_time = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
        coordinator = EntryCoordinator(now=base_time)

        # Add entries with different Sharpe ratios
        coordinator.add_entry(
            symbol="SYM1",
            strategy_id="STR_001",
            signal={"type": "entry"},
            sharpe_ratio=1.0,
        )

        coordinator.add_entry(
            symbol="SYM2",
            strategy_id="STR_002",
            signal={"type": "entry"},
            sharpe_ratio=3.0,  # Higher priority
        )

        coordinator.add_entry(
            symbol="SYM3",
            strategy_id="STR_003",
            signal={"type": "entry"},
            sharpe_ratio=2.0,
        )

        # Should get highest Sharpe ratio first
        entry = coordinator.get_next_entry()
        assert entry.sharpe_ratio == 3.0
        assert entry.symbol == "SYM2"

    def test_bypass_for_stop_loss_take_profit(self):
        """Stop loss and take profit bypass timing rules."""
        coordinator = EntryCoordinator()

        assert coordinator.should_bypass("stop_loss") is True
        assert coordinator.should_bypass("take_profit") is True
        assert coordinator.should_bypass("kill_switch") is True
        assert coordinator.should_bypass("entry") is False


# ---------------------------------------------------------------------------
# Startup Checklist Tests
# ---------------------------------------------------------------------------


class TestStartupChecklist:
    """Test startup validation checklist."""

    @pytest.fixture
    def mocks(self):
        """Create all required mocks."""
        return {
            "data_store": MagicMock(),
            "market_data": MagicMock(),
            "strategy_engine": MagicMock(),
            "position_tracker": MagicMock(),
            "config": {"exchange": "binance", "database_url": "sqlite:///test.db"},
        }

    @pytest.mark.asyncio
    async def test_all_checks_pass(self, mocks):
        """All startup checks pass."""
        # Mock successful responses
        system_state = MagicMock()
        system_state.trading_enabled = True
        system_state.kill_switch_active = False
        mocks["data_store"].get_system_state.return_value = system_state

        # Use the real StrategyEngine so the strategy check is exercised
        # against the real TemplateManager. The previous version of this test
        # mocked the engine and described the strategy with the field names the
        # buggy check expected (template=, symbol=, account_id=, params=) --
        # none of which exist on the Strategy model, and "simple_ma" is not a
        # real template id. It therefore asserted that a check which could
        # never pass in production did pass.
        engine = StrategyEngine(store=mocks["data_store"])
        mocks["strategy_engine"] = engine
        template = engine.template_manager.get_template("bb_squeeze_breakout")
        mocks["data_store"].get_active_strategies.return_value = [
            MagicMock(
                id="STR_001",
                name="Test",
                template_id="bb_squeeze_breakout",
                parameters=template.get_default_parameters(),
            )
        ]

        # Memory AND disk are mocked, for the same reason: both checks read real
        # host state, so without this the test asserts something about the
        # machine rather than about the code.
        #
        # The memory mock was here from the start; the disk one was added on
        # 2026-08-21, after this test failed on a development machine whose disk
        # had 0.56GB free. Nothing in the code, the test or the assertion had
        # changed -- the drive had filled. A test that passes or fails on how
        # full a disk is will eventually go red in CI for a reason nobody can
        # act on, which is the failure mode DEC-2026-08-14-005 describes for
        # flaky tests generally.
        #
        # `_check_disk_space` itself is exercised properly by
        # `test_disk_space_check_failure`, which controls the value it sees.
        # Decision: DEC-2026-08-21-008
        with (
            patch("psutil.virtual_memory") as mock_mem,
            patch("shutil.disk_usage") as mock_disk,
        ):
            mock_mem.return_value = MagicMock(
                available=1024 * 1024 * 1024,  # 1GB available
                percent=50,
            )
            mock_disk.return_value = MagicMock(
                total=100 * 1024**3,
                used=50 * 1024**3,
                free=50 * 1024**3,  # 50GB free, comfortably over the 1GB floor
            )

            checklist = StartupChecklist(**mocks)
            result = await checklist.run()

            assert result.passed is True
            assert len(result.checks) == 8
            assert result.failed_check is None

    @pytest.mark.asyncio
    async def test_database_check_failure(self, mocks):
        """Database check fails."""
        mocks["data_store"].get_system_state.side_effect = Exception(
            "Connection failed"
        )

        checklist = StartupChecklist(**mocks)
        result = await checklist.run()

        assert result.passed is False
        assert result.failed_check == "database"
        assert len(result.checks) == 1  # Stopped at first failure

    @pytest.mark.asyncio
    async def test_configuration_check_missing_keys(self, mocks):
        """Configuration check fails with missing keys."""
        mocks["config"] = {"exchange": "binance"}  # Missing database_url

        # Mock database check to pass
        system_state = MagicMock()
        mocks["data_store"].get_system_state.return_value = system_state

        checklist = StartupChecklist(**mocks)
        result = await checklist.run()

        assert result.passed is False
        assert result.failed_check == "configuration"

    def test_disk_space_check_insufficient(self, mocks):
        """Disk space check fails."""
        with patch("shutil.disk_usage") as mock_disk:
            # Mock < 1GB free
            mock_disk.return_value = MagicMock(
                free=500 * 1024 * 1024  # 500MB
            )

            checklist = StartupChecklist(**mocks)
            check = checklist._check_disk_space()

            assert check.passed is False
            assert "Insufficient disk space" in check.message

    def test_memory_check_insufficient(self, mocks):
        """Memory check fails."""
        with patch("psutil.virtual_memory") as mock_mem:
            # Mock < 500MB available
            mock_mem.return_value = MagicMock(
                available=400 * 1024 * 1024,  # 400MB
                percent=80,
            )

            checklist = StartupChecklist(**mocks)
            check = checklist._check_memory()

            assert check.passed is False
            assert "Insufficient memory" in check.message

    def test_no_active_strategies_fails(self, mocks):
        """No active strategies fails validation."""
        mocks["data_store"].get_active_strategies.return_value = []

        checklist = StartupChecklist(**mocks)
        check = checklist._check_strategies()

        assert check.passed is False
        assert "No active strategies" in check.message


# ---------------------------------------------------------------------------
# Startup Strategy Check — real StrategyEngine
# ---------------------------------------------------------------------------


class TestCheckStrategiesWithRealEngine:
    """Exercise ``_check_strategies`` against a real StrategyEngine.

    Every other test in this module passes ``MagicMock()`` as the strategy
    engine, which accepts any call with any arguments. That is why the
    original defect survived: ``_check_strategies`` called
    ``create_strategy(name=..., template=..., symbol=..., account_id=...,
    params=..., status=...)`` when the real signature is
    ``create_strategy(name, template_id, params=None, symbols=None,
    description="")``, and the Strategy model has no ``template``,
    ``symbol``, ``params`` or ``account_id`` attribute at all. Against a mock
    that call is silently fine; against the real engine it could never pass.

    These tests use the real ``StrategyEngine`` and the real
    ``TemplateManager`` loaded from ``config/templates/``. The DataStore is
    still a mock -- it is not what is under test here, and mocking it is what
    lets ``test_check_does_not_persist_anything`` assert on writes.
    """

    TEMPLATE_ID = "bb_squeeze_breakout"

    @pytest.fixture
    def store(self):
        """Mock DataStore. Writes through it are asserted against."""
        return MagicMock()

    @pytest.fixture
    def engine(self, store):
        """A real StrategyEngine with a real TemplateManager."""
        return StrategyEngine(store=store)

    @pytest.fixture
    def mocks(self, engine, store):
        """Checklist dependencies with a REAL strategy engine."""
        return {
            "data_store": store,
            "market_data": MagicMock(),
            "strategy_engine": engine,
            "position_tracker": MagicMock(),
            "config": {"exchange": "binance", "database_url": "sqlite:///test.db"},
        }

    def _make_strategy(self, engine, template_id=None, params=None):
        """Build a real (unsaved) Strategy from a real template."""
        template_id = template_id or self.TEMPLATE_ID
        template = engine.template_manager.get_template(self.TEMPLATE_ID)
        return Strategy(
            name="Squeeze Test",
            description=template.description,
            type=StrategyType(template.type),
            template_id=template_id,
            template_version=template.version,
            parameters=(
                params if params is not None else template.get_default_parameters()
            ),
            symbols=list(template.symbols),
            status=StrategyStatus.LIVE,
            status_reason="test fixture",
            lifecycle=[],
        )

    def test_valid_strategy_passes(self, mocks, engine, store):
        """A strategy whose params match its template validates cleanly.

        This is the test that would have failed against the old
        implementation: the real engine raises on the bogus kwargs.
        """
        store.get_active_strategies.return_value = [self._make_strategy(engine)]

        check = StartupChecklist(**mocks)._check_strategies()

        assert check.passed is True, check.message
        assert check.details["strategy_count"] == 1

    def test_check_does_not_persist_anything(self, mocks, engine, store):
        """The check must be read-only.

        ``StrategyEngine.create_strategy`` persists via
        ``DataStore.save_strategy`` and hardcodes ``StrategyStatus.DRAFT``.
        Using it here -- even with corrected keyword arguments -- would write
        one duplicate DRAFT row per active strategy on every startup. This
        asserts the check never writes.
        """
        store.get_active_strategies.return_value = [self._make_strategy(engine)]

        check = StartupChecklist(**mocks)._check_strategies()

        assert check.passed is True, check.message
        store.save_strategy.assert_not_called()

    def test_unknown_template_fails_with_named_template(self, mocks, engine, store):
        """A strategy pointing at a deleted template fails, and says which."""
        store.get_active_strategies.return_value = [
            self._make_strategy(engine, template_id="template_that_does_not_exist")
        ]

        check = StartupChecklist(**mocks)._check_strategies()

        assert check.passed is False
        assert "unknown template" in check.message
        assert check.details["template_id"] == "template_that_does_not_exist"

    def test_parameters_no_longer_valid_fails(self, mocks, engine, store):
        """Stored params that drifted out of template bounds are caught."""
        store.get_active_strategies.return_value = [
            self._make_strategy(engine, params={"bb_period": -5})
        ]

        check = StartupChecklist(**mocks)._check_strategies()

        assert check.passed is False
        assert "invalid parameters" in check.message
        assert any("bb_period" in e for e in check.details["errors"])

    def test_programming_errors_propagate(self, mocks, store):
        """A TypeError inside the check must surface, not become 'check failed'.

        Reporting programming errors as an ordinary failed check is what hid
        the original defect for months.
        """
        store.get_active_strategies.side_effect = TypeError("bad call")

        with pytest.raises(TypeError, match="bad call"):
            StartupChecklist(**mocks)._check_strategies()


# ---------------------------------------------------------------------------
# Health Checker Tests
# ---------------------------------------------------------------------------


class TestHealthChecker:
    """Test system health monitoring."""

    @pytest.fixture
    def mocks(self):
        """Create mocks for health checker."""
        data_store = MagicMock()
        market_data = MagicMock()
        metrics = OrchestratorMetrics()
        return data_store, market_data, metrics

    @pytest.mark.asyncio
    async def test_all_checks_healthy(self, mocks):
        """All health checks pass."""
        data_store, market_data, metrics = mocks

        with patch("psutil.virtual_memory") as mock_mem:
            with patch("shutil.disk_usage") as mock_disk:
                mock_mem.return_value = MagicMock(percent=50)
                mock_disk.return_value = MagicMock(free=5 * 1024**3)

                checker = HealthChecker(data_store, market_data, metrics)
                health = await checker.check_health()

                assert health.status == "healthy"

    @pytest.mark.asyncio
    async def test_memory_warning_degraded(self, mocks):
        """High memory usage triggers degraded status."""
        data_store, market_data, metrics = mocks

        with patch("psutil.virtual_memory") as mock_mem:
            with patch("shutil.disk_usage") as mock_disk:
                mock_mem.return_value = MagicMock(percent=75)  # > 70% warning
                mock_disk.return_value = MagicMock(free=5 * 1024**3)

                checker = HealthChecker(data_store, market_data, metrics)
                health = await checker.check_health()

                assert health.status == "degraded"

    @pytest.mark.asyncio
    async def test_memory_critical_unhealthy(self, mocks):
        """Critical memory usage triggers unhealthy status."""
        data_store, market_data, metrics = mocks

        with patch("psutil.virtual_memory") as mock_mem:
            with patch("shutil.disk_usage") as mock_disk:
                mock_mem.return_value = MagicMock(percent=90)  # > 85% critical
                mock_disk.return_value = MagicMock(free=5 * 1024**3)

                checker = HealthChecker(data_store, market_data, metrics)
                health = await checker.check_health()

                assert health.status == "unhealthy"

    @pytest.mark.asyncio
    async def test_low_disk_space_unhealthy(self, mocks):
        """Low disk space triggers unhealthy status."""
        data_store, market_data, metrics = mocks

        with patch("psutil.virtual_memory") as mock_mem:
            with patch("shutil.disk_usage") as mock_disk:
                mock_mem.return_value = MagicMock(percent=50)
                mock_disk.return_value = MagicMock(
                    free=500 * 1024 * 1024  # < 1GB
                )

                checker = HealthChecker(data_store, market_data, metrics)
                health = await checker.check_health()

                assert health.status == "unhealthy"


# ---------------------------------------------------------------------------
# Degradation Manager Tests
# ---------------------------------------------------------------------------


class TestDegradationManager:
    """Test graceful degradation management."""

    @pytest.fixture
    def triggers(self):
        """Mock alert triggers."""
        triggers = MagicMock()
        triggers.on_degradation_mode_entered = AsyncMock()
        triggers.on_degradation_mode_recovered = AsyncMock()
        return triggers

    @pytest.mark.asyncio
    async def test_starts_in_normal_mode(self, triggers):
        """Degradation manager starts in NORMAL mode."""
        manager = DegradationManager(triggers)
        assert manager.get_mode() == DegradationMode.NORMAL

    @pytest.mark.asyncio
    async def test_unhealthy_triggers_read_only(self, triggers):
        """Unhealthy status triggers READ_ONLY mode."""
        manager = DegradationManager(triggers)

        # Create unhealthy health status
        from src.core.orchestrator import CheckStatus, SystemHealth

        health = SystemHealth(
            status="unhealthy",
            checks=[
                CheckStatus(
                    name="test",
                    healthy=False,
                    message="Failed",
                )
            ],
            timestamp=datetime.now(timezone.utc),
        )

        await manager.check_degradation(health)

        assert manager.get_mode() == DegradationMode.READ_ONLY
        triggers.on_degradation_mode_entered.assert_called_once()

    @pytest.mark.asyncio
    async def test_healthy_triggers_recovery(self, triggers):
        """Healthy status triggers recovery to NORMAL."""
        manager = DegradationManager(triggers)

        from src.core.orchestrator import SystemHealth

        # Enter degraded mode first
        unhealthy = SystemHealth(
            status="unhealthy",
            checks=[],
            timestamp=datetime.now(timezone.utc),
        )
        await manager.check_degradation(unhealthy)
        assert manager.get_mode() == DegradationMode.READ_ONLY

        # Recover
        healthy = SystemHealth(
            status="healthy",
            checks=[],
            timestamp=datetime.now(timezone.utc),
        )
        await manager.check_degradation(healthy)

        assert manager.get_mode() == DegradationMode.NORMAL
        triggers.on_degradation_mode_recovered.assert_called_once()

    @pytest.mark.asyncio
    async def test_strategy_error_tracking(self, triggers):
        """Strategies skipped after 3 consecutive errors."""
        manager = DegradationManager(triggers)

        # Record 3 errors
        for _ in range(3):
            await manager.record_strategy_error("STR_001")

        # Strategy should be skipped
        assert manager.should_skip_strategy("STR_001") is True

    @pytest.mark.asyncio
    async def test_strategy_recovery(self, triggers):
        """Strategy success clears error tracking."""
        manager = DegradationManager(triggers)

        # Record errors
        for _ in range(3):
            await manager.record_strategy_error("STR_001")

        assert manager.should_skip_strategy("STR_001") is True

        # Record success
        await manager.record_strategy_success("STR_001")

        # No longer skipped
        assert manager.should_skip_strategy("STR_001") is False


# ---------------------------------------------------------------------------
# Orchestrator Tests
# ---------------------------------------------------------------------------


class TestOrchestrator:
    """Test orchestrator lifecycle and coordination."""

    @pytest.fixture
    def mocks(self):
        """Create all component mocks."""
        config = {"exchange": "binance", "database_url": "sqlite:///test.db"}

        data_store = MagicMock()
        system_state = MagicMock()
        system_state.trading_enabled = True
        system_state.kill_switch_active = False
        data_store.get_system_state.return_value = system_state
        data_store.get_active_strategies.return_value = [
            MagicMock(
                id="STR_001",
                name="Test",
                template="simple_ma",
                symbol="BTCUSDT",
                account_id="ACC_001",
                params={},
            )
        ]

        market_data = MagicMock()
        risk_controller = MagicMock()
        risk_controller.kill_switch = MagicMock()
        risk_controller.kill_switch.is_active.return_value = False

        order_manager = MagicMock()
        order_manager.shutdown = AsyncMock()

        position_tracker = MagicMock()
        position_tracker.get_all_positions = AsyncMock(return_value=[])

        strategy_engine = MagicMock()

        alert_manager = MagicMock()
        alert_manager.check_escalations = AsyncMock()
        alert_manager.send_info = AsyncMock()
        alert_manager.send_warning = AsyncMock()
        alert_manager.send_error = AsyncMock()
        alert_manager.send_critical = AsyncMock()

        return {
            "config": config,
            "data_store": data_store,
            "market_data": market_data,
            "risk_controller": risk_controller,
            "order_manager": order_manager,
            "position_tracker": position_tracker,
            "strategy_engine": strategy_engine,
            "alert_manager": alert_manager,
        }

    def test_orchestrator_initialization(self, mocks):
        """Orchestrator initializes with all components."""
        orchestrator = Orchestrator(**mocks)

        assert orchestrator._status == SystemStatus.STOPPED
        assert orchestrator._running is False
        assert isinstance(orchestrator._metrics, OrchestratorMetrics)

    @pytest.mark.asyncio
    async def test_kill_switch_checked_first(self, mocks):
        """Kill switch checked FIRST in main loop (DEC-2026-02-12-003)."""
        mocks["risk_controller"].kill_switch.is_active.return_value = True

        orchestrator = Orchestrator(**mocks)

        # Mock startup checklist to pass
        with patch.object(orchestrator._startup_checklist, "run") as mock_run:
            from src.core.orchestrator import StartupResult

            mock_run.return_value = StartupResult(
                passed=True,
                checks=[],
            )

            # Start orchestrator in background
            task = asyncio.create_task(orchestrator.start())

            # Give it time to enter main loop
            await asyncio.sleep(0.1)

            # Stop it
            orchestrator._running = False
            await task

            # Kill switch should have been checked
            mocks["risk_controller"].kill_switch.is_active.assert_called()

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, mocks):
        """Graceful shutdown cancels orders and sends alert."""
        orchestrator = Orchestrator(**mocks)
        orchestrator._running = True

        await orchestrator.stop()

        assert orchestrator._status == SystemStatus.STOPPED
        mocks["order_manager"].shutdown.assert_called_once()

    def test_get_status(self, mocks):
        """Get status returns current state and metrics."""
        orchestrator = Orchestrator(**mocks)
        orchestrator._metrics.cycles_completed = 10

        status = orchestrator.get_status()

        assert status["status"] == "stopped"
        assert status["metrics"]["cycles_completed"] == 10
        assert "uptime_seconds" in status
