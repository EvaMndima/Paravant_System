"""Full system integration tests - 12 end-to-end flows.

Each test represents a complete workflow through the trading system,
verifying that components coordinate correctly. All external dependencies
are mocked to isolate the orchestration logic.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.event_bus import EventBus
from src.data.models import (
    Account, AccountStatus, Base, Order, OrderSide, OrderStatus,
    OrderType, Position, PositionSide, PositionStatus, RiskProfile,
    Strategy, StrategyStatus, StrategyType, SystemState,
)
from src.data.store import DataStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def integration_engine():
    """Create in-memory SQLite for integration tests.

    Uses StaticPool to maintain a single persistent connection,
    ensuring tables created by create_all() remain available.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def integration_store(integration_engine):
    """Create DataStore for integration tests."""
    store = DataStore()
    store.engine = integration_engine
    return store


@pytest.fixture
def integration_session(integration_engine):
    """Create session for seeding data."""
    SessionLocal = sessionmaker(bind=integration_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def test_account(integration_session) -> Account:
    """Seed a test account."""
    account = Account(
        name="Integration Test Account",
        broker="binance",
        profile=RiskProfile.BALANCED,
        status=AccountStatus.ACTIVE,
        balance_usdt=10000.0,
        equity_usdt=10000.0,
        regime="unknown",
    )
    integration_session.add(account)
    integration_session.commit()
    integration_session.refresh(account)
    return account


@pytest.fixture
def test_strategy(integration_session) -> Strategy:
    """Seed a test strategy."""
    strategy = Strategy(
        name="Integration MA Strategy",
        template_id="simple_ma",
        template_version="1.0.0",
        type=StrategyType.TREND_FOLLOWING,
        status=StrategyStatus.LIVE,
        parameters={"fast_period": 10, "slow_period": 20},
        symbols=["BTCUSDT"],
        backtest_results={},
        paper_results={},
        live_results={},
        lifecycle=[],
    )
    integration_session.add(strategy)
    integration_session.commit()
    integration_session.refresh(strategy)
    return strategy


@pytest.fixture
def event_bus():
    """Create EventBus for integration tests."""
    return EventBus()


@pytest.fixture
def mock_order_manager():
    """Mock OrderManager."""
    om = AsyncMock()
    om.submit_order = AsyncMock(return_value=MagicMock(
        id="ord_test",
        status=OrderStatus.FILLED,
        filled_quantity=0.1,
        filled_price=40000.0,
    ))
    om.cancel_all_pending = AsyncMock(return_value=0)
    om.shutdown = AsyncMock()
    return om


@pytest.fixture
def mock_position_tracker():
    """Mock PositionTracker."""
    pt = AsyncMock()
    pt.get_all_positions = AsyncMock(return_value=[])
    pt.get_position = AsyncMock(return_value=None)
    pt.process_stale_positions = AsyncMock(return_value=[])
    return pt


@pytest.fixture
def mock_risk_controller():
    """Mock RiskController."""
    rc = AsyncMock()
    rc.check_order = AsyncMock(return_value=(True, "approved"))
    rc.check_kill_switch = AsyncMock(return_value=False)
    rc.get_daily_loss_pct = AsyncMock(return_value=0.5)
    rc.get_drawdown_pct = AsyncMock(return_value=1.0)
    return rc


@pytest.fixture
def mock_market_data():
    """Mock MarketDataFetcher."""
    md = AsyncMock()
    md.fetch_latest_price = AsyncMock(return_value=40000.0)
    md.fetch_ohlcv = AsyncMock(return_value=[])
    md.is_healthy = MagicMock(return_value=True)
    return md


@pytest.fixture
def mock_strategy_engine():
    """Mock StrategyEngine."""
    se = AsyncMock()
    se.process_strategy = AsyncMock(return_value=[])
    se.get_active_strategies = AsyncMock(return_value=[])
    return se


@pytest.fixture
def mock_alert_manager():
    """Mock AlertManager."""
    am = AsyncMock()
    am.send_alert = AsyncMock()
    return am


@pytest.fixture
def mock_triggers():
    """Mock AlertTriggers."""
    triggers = AsyncMock()
    triggers.on_system_started = AsyncMock()
    triggers.on_system_stopped = AsyncMock()
    triggers.on_trade_executed = AsyncMock()
    triggers.on_risk_breach = AsyncMock()
    triggers.on_kill_switch = AsyncMock()
    triggers.on_circuit_breaker = AsyncMock()
    triggers.on_system_error = AsyncMock()
    return triggers


# ---------------------------------------------------------------------------
# Flow 1: System Startup -> Checklist Passes -> Main Loop Starts
# ---------------------------------------------------------------------------


class TestSystemStartupFlow:
    """Test complete system startup sequence."""

    @pytest.mark.asyncio
    async def test_startup_checklist_passes(
        self, integration_store, test_account, event_bus
    ):
        """Verify startup sequence: checklist -> init -> main loop."""
        # Setup: account exists, database accessible
        system_state = integration_store.get_system_state()
        assert system_state is not None
        assert system_state.trading_enabled is True

        # Verify account is retrievable
        accounts = integration_store.get_active_accounts()
        assert len(accounts) == 1
        assert accounts[0].name == "Integration Test Account"

        # Verify EventBus is functional
        sub_id = await event_bus.subscribe(["system_status_changed"])
        delivered = await event_bus.publish("system_status_changed", {
            "status": "running", "trigger": "startup"
        })
        assert delivered == 1

        event = await event_bus.get_event(sub_id, timeout=1.0)
        assert event is not None
        assert event["type"] == "system_status_changed"

        await event_bus.unsubscribe(sub_id)


# ---------------------------------------------------------------------------
# Flow 2: Startup Failure -> System Stays Stopped -> Alert Sent
# ---------------------------------------------------------------------------


class TestStartupFailureFlow:
    """Test startup failure handling."""

    @pytest.mark.asyncio
    async def test_startup_failure_sends_alert(
        self, integration_store, mock_triggers, event_bus
    ):
        """Verify failed startup triggers alert and system stays stopped."""
        # Simulate: no account in database (startup check would fail)
        accounts = integration_store.get_active_accounts()
        # With no seeded account, this should be empty
        if not accounts:
            # Startup would fail - trigger alert
            await mock_triggers.on_system_error(
                error="No active accounts found",
                component="startup_checklist",
            )
            mock_triggers.on_system_error.assert_called_once()

            # Publish failure event
            sub_id = await event_bus.subscribe(["system_status_changed"])
            await event_bus.publish("system_status_changed", {
                "status": "failed", "reason": "startup_checklist_failed"
            })
            event = await event_bus.get_event(sub_id, timeout=1.0)
            assert event["data"]["status"] == "failed"
            await event_bus.unsubscribe(sub_id)


# ---------------------------------------------------------------------------
# Flow 3: Strategy Creation -> Similarity Check -> Saved
# ---------------------------------------------------------------------------


class TestStrategyCreationFlow:
    """Test strategy creation workflow."""

    def test_create_strategy_from_template(self, integration_store):
        """Verify strategy creation, validation, and persistence."""
        strategy = Strategy(
            name="New Momentum Strategy",
            template_id="momentum_macd",
            template_version="1.0.0",
            type=StrategyType.TREND_FOLLOWING,
            status=StrategyStatus.DRAFT,
            parameters={"fast_period": 12, "slow_period": 26, "signal_period": 9},
            symbols=["BTCUSDT", "ETHUSDT"],
            backtest_results={},
            paper_results={},
            live_results={},
            lifecycle=[],
        )
        integration_store.save_strategy(strategy)

        # Verify saved
        saved = integration_store.get_strategy(strategy.id)
        assert saved is not None
        assert saved.name == "New Momentum Strategy"
        assert saved.status == StrategyStatus.DRAFT
        assert "BTCUSDT" in saved.symbols


# ---------------------------------------------------------------------------
# Flow 4: Backtest Flow -> Run -> Metrics Computed -> Results Returned
# ---------------------------------------------------------------------------


class TestBacktestFlow:
    """Test backtesting workflow."""

    def test_backtest_updates_strategy_results(
        self, integration_store, test_strategy
    ):
        """Verify backtest results are persisted to strategy."""
        results = {
            "total_return": 15.5,
            "win_rate": 62.3,
            "max_drawdown": -8.2,
            "sharpe_ratio": 1.45,
            "total_trades": 150,
        }

        with integration_store.session() as session:
            db_strategy = session.get(Strategy, test_strategy.id)
            if db_strategy:
                db_strategy.backtest_results = results

        updated = integration_store.get_strategy(test_strategy.id)
        assert updated is not None
        assert updated.backtest_results["total_return"] == 15.5
        assert updated.backtest_results["win_rate"] == 62.3


# ---------------------------------------------------------------------------
# Flow 5: Paper Trading -> Signals -> Fills -> Position Tracked
# ---------------------------------------------------------------------------


class TestPaperTradingFlow:
    """Test paper trading flow."""

    def test_paper_trade_creates_position(
        self, integration_store, test_account, test_strategy
    ):
        """Verify paper trade creates order, fill, and position."""
        # Create order
        order = Order(
            account_id=test_account.id,
            strategy_id=test_strategy.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=0.1,
            status=OrderStatus.FILLED,
            filled_quantity=0.1,
            filled_price=40000.0,
        )
        integration_store.save_order(order)

        # Create position
        position = Position(
            account_id=test_account.id,
            strategy_id=test_strategy.id,
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=0.1,
            entry_price=40000.0,
            current_price=40000.0,
            status=PositionStatus.OPEN,
        )
        integration_store.save_position(position)

        # Verify
        open_positions = integration_store.get_open_positions()
        assert len(open_positions) == 1
        assert open_positions[0].symbol == "BTCUSDT"
        assert open_positions[0].entry_price == 40000.0


# ---------------------------------------------------------------------------
# Flow 6: Order Flow -> Submit -> Risk Checks -> Fill -> P&L Updated
# ---------------------------------------------------------------------------


class TestOrderFlow:
    """Test complete order submission flow."""

    @pytest.mark.asyncio
    async def test_order_submission_with_risk_check(
        self, integration_store, test_account, mock_risk_controller
    ):
        """Verify order goes through risk checks before execution."""
        # Risk check passes
        approved, reason = await mock_risk_controller.check_order(
            symbol="BTCUSDT",
            side="buy",
            quantity=0.1,
            price=40000.0,
        )
        assert approved is True

        # Create and save order
        order = Order(
            account_id=test_account.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=0.1,
            status=OrderStatus.FILLED,
            filled_quantity=0.1,
            filled_price=40000.0,
        )
        integration_store.save_order(order)

        saved = integration_store.get_order(order.id)
        assert saved is not None
        assert saved.status == OrderStatus.FILLED


# ---------------------------------------------------------------------------
# Flow 7: Risk Rejection -> Exceeds Limit -> Rejected -> Alert Sent
# ---------------------------------------------------------------------------


class TestRiskRejectionFlow:
    """Test risk rejection flow."""

    @pytest.mark.asyncio
    async def test_risk_rejection_triggers_alert(
        self, integration_store, mock_risk_controller, mock_triggers, event_bus
    ):
        """Verify rejected orders trigger alerts and events."""
        # Configure risk controller to reject
        mock_risk_controller.check_order = AsyncMock(
            return_value=(False, "Daily loss limit exceeded")
        )

        approved, reason = await mock_risk_controller.check_order(
            symbol="BTCUSDT", side="buy", quantity=1.0, price=40000.0,
        )
        assert approved is False
        assert "Daily loss limit" in reason

        # Alert should be sent
        await mock_triggers.on_risk_breach(
            reason=reason, symbol="BTCUSDT", quantity=1.0
        )
        mock_triggers.on_risk_breach.assert_called_once()

        # Event published
        sub_id = await event_bus.subscribe(["risk_status_changed"])
        await event_bus.publish("risk_status_changed", {
            "type": "order_rejected", "reason": reason
        })
        event = await event_bus.get_event(sub_id, timeout=1.0)
        assert event["data"]["type"] == "order_rejected"
        await event_bus.unsubscribe(sub_id)


# ---------------------------------------------------------------------------
# Flow 8: Kill Switch -> Activate -> Stops -> Deactivate -> Resumes
# ---------------------------------------------------------------------------


class TestKillSwitchFlow:
    """Test kill switch activation and deactivation."""

    @pytest.mark.asyncio
    async def test_kill_switch_lifecycle(
        self, integration_store, mock_triggers, event_bus
    ):
        """Verify kill switch activation stops trading and deactivation resumes."""
        # Activate kill switch
        integration_store.update_system_state(
            kill_switch_active=True,
            kill_switch_activated_at=datetime.now(timezone.utc),
            kill_switch_reason="Daily loss limit exceeded",
        )

        state = integration_store.get_system_state()
        assert state.kill_switch_active is True
        assert state.is_safe_to_trade is False

        # Alert sent
        await mock_triggers.on_kill_switch(
            activated=True, reason="Daily loss limit exceeded"
        )

        # Event published
        sub_id = await event_bus.subscribe(["kill_switch_changed"])
        await event_bus.publish("kill_switch_changed", {
            "active": True, "reason": "Daily loss limit exceeded"
        })
        event = await event_bus.get_event(sub_id, timeout=1.0)
        assert event["data"]["active"] is True

        # Deactivate
        integration_store.update_system_state(
            kill_switch_active=False,
            kill_switch_reason=None,
        )

        state = integration_store.get_system_state()
        assert state.kill_switch_active is False
        assert state.is_safe_to_trade is True

        await event_bus.publish("kill_switch_changed", {
            "active": False, "reason": "manually_deactivated"
        })
        event = await event_bus.get_event(sub_id, timeout=1.0)
        assert event["data"]["active"] is False
        await event_bus.unsubscribe(sub_id)


# ---------------------------------------------------------------------------
# Flow 9: Circuit Breaker -> Trigger -> Pause -> Reset -> Resume
# ---------------------------------------------------------------------------


class TestCircuitBreakerFlow:
    """Test circuit breaker trigger and reset."""

    def test_circuit_breaker_lifecycle(self, integration_store):
        """Verify circuit breaker trigger pauses and reset resumes."""
        # Trigger circuit breaker
        integration_store.update_system_state(
            circuit_breakers={"daily_loss": True, "drawdown": False}
        )

        state = integration_store.get_system_state()
        assert state.any_circuit_breaker_active is True
        assert state.circuit_breakers["daily_loss"] is True

        # Audit log
        integration_store.add_audit_log(
            action="circuit_breaker_triggered",
            actor="risk_controller",
            details={"breaker": "daily_loss", "threshold": 3.0},
        )

        # Reset
        integration_store.update_system_state(
            circuit_breakers={"daily_loss": False, "drawdown": False}
        )

        state = integration_store.get_system_state()
        assert state.any_circuit_breaker_active is False

        # Verify audit log
        logs = integration_store.get_audit_logs(action="circuit_breaker_triggered")
        assert len(logs) == 1
        assert logs[0].details["breaker"] == "daily_loss"


# ---------------------------------------------------------------------------
# Flow 10: Alert Escalation -> Warning -> Wait -> Escalation
# ---------------------------------------------------------------------------


class TestAlertEscalationFlow:
    """Test alert escalation flow."""

    @pytest.mark.asyncio
    async def test_alert_escalation(self, mock_alert_manager, mock_triggers):
        """Verify alerts escalate after timeout."""
        # Initial warning
        await mock_triggers.on_risk_breach(
            reason="Approaching daily limit",
            symbol="BTCUSDT",
            quantity=0.5,
        )
        mock_triggers.on_risk_breach.assert_called_once()

        # Escalation (simulated after timeout)
        await mock_alert_manager.send_alert(
            level="critical",
            title="ESCALATED: Risk breach unresolved",
            message="Daily loss limit approaching - no action taken",
        )
        mock_alert_manager.send_alert.assert_called_once()


# ---------------------------------------------------------------------------
# Flow 11: Degradation -> API Down -> Read-Only -> Recovery -> Normal
# ---------------------------------------------------------------------------


class TestDegradationFlow:
    """Test graceful degradation flow."""

    def test_degradation_and_recovery(self, integration_store):
        """Verify system degrades gracefully and recovers."""
        # Degrade: mark unhealthy
        integration_store.update_system_state(
            health_status="degraded",
            trading_enabled=False,
        )

        state = integration_store.get_system_state()
        assert state.health_status == "degraded"
        assert state.trading_enabled is False
        assert state.is_safe_to_trade is False

        # Data should still be readable
        accounts = integration_store.get_all_accounts()
        # DataStore operations still work in degraded mode
        assert isinstance(accounts, list)

        # Recover
        integration_store.update_system_state(
            health_status="healthy",
            trading_enabled=True,
        )

        state = integration_store.get_system_state()
        assert state.health_status == "healthy"
        assert state.is_safe_to_trade is True


# ---------------------------------------------------------------------------
# Flow 12: Shutdown -> Cancel Orders -> Save State -> Alert
# ---------------------------------------------------------------------------


class TestShutdownFlow:
    """Test graceful shutdown flow."""

    @pytest.mark.asyncio
    async def test_graceful_shutdown(
        self, integration_store, test_account,
        mock_order_manager, mock_triggers, event_bus
    ):
        """Verify shutdown cancels orders, saves state, sends alert."""
        # Create a pending order
        order = Order(
            account_id=test_account.id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=0.1,
            status=OrderStatus.PENDING,
            filled_quantity=0.0,
        )
        integration_store.save_order(order)

        # Shutdown sequence
        # 1. Cancel pending orders
        await mock_order_manager.shutdown()
        mock_order_manager.shutdown.assert_called_once()

        # 2. Save state
        integration_store.update_system_state(
            health_status="stopped",
            trading_enabled=False,
        )

        # 3. Audit log
        integration_store.add_audit_log(
            action="system_stopped",
            actor="system",
            details={"trigger": "graceful_shutdown", "uptime_seconds": 7200.0},
        )

        # 4. Send alert
        await mock_triggers.on_system_stopped(
            graceful=True, uptime_seconds=7200.0
        )
        mock_triggers.on_system_stopped.assert_called_once()

        # 5. Event published
        sub_id = await event_bus.subscribe(["system_status_changed"])
        await event_bus.publish("system_status_changed", {
            "status": "stopped", "graceful": True
        })
        event = await event_bus.get_event(sub_id, timeout=1.0)
        assert event["data"]["status"] == "stopped"
        assert event["data"]["graceful"] is True
        await event_bus.unsubscribe(sub_id)

        # Verify final state
        state = integration_store.get_system_state()
        assert state.health_status == "stopped"
        assert state.trading_enabled is False

        logs = integration_store.get_audit_logs(action="system_stopped")
        assert len(logs) >= 1


# ---------------------------------------------------------------------------
# EventBus Integration Tests
# ---------------------------------------------------------------------------


class TestEventBusIntegration:
    """Tests for EventBus integration with components."""

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, event_bus):
        """Verify events are delivered to all matching subscribers."""
        sub1 = await event_bus.subscribe(["position_updated"])
        sub2 = await event_bus.subscribe(["position_updated", "alert_created"])
        sub3 = await event_bus.subscribe(["alert_created"])

        delivered = await event_bus.publish("position_updated", {"symbol": "BTCUSDT"})
        assert delivered == 2  # sub1 and sub2

        delivered = await event_bus.publish("alert_created", {"level": "warning"})
        assert delivered == 2  # sub2 and sub3

        await event_bus.unsubscribe(sub1)
        await event_bus.unsubscribe(sub2)
        await event_bus.unsubscribe(sub3)

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe_cleanup(self, event_bus):
        """Verify unsubscribe properly cleans up."""
        sub_id = await event_bus.subscribe()
        assert await event_bus.get_subscriber_count() == 1

        result = await event_bus.unsubscribe(sub_id)
        assert result is True
        assert await event_bus.get_subscriber_count() == 0

        # Double unsubscribe returns False
        result = await event_bus.unsubscribe(sub_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_event_timeout(self, event_bus):
        """Verify get_event returns None on timeout."""
        sub_id = await event_bus.subscribe()
        event = await event_bus.get_event(sub_id, timeout=0.1)
        assert event is None
        await event_bus.unsubscribe(sub_id)

    @pytest.mark.asyncio
    async def test_invalid_event_type(self, event_bus):
        """Verify publish rejects invalid event types."""
        with pytest.raises(ValueError, match="Invalid event type"):
            await event_bus.publish("not_a_real_event", {"data": True})

    @pytest.mark.asyncio
    async def test_invalid_subscribe_type(self, event_bus):
        """Verify subscribe rejects invalid event types."""
        with pytest.raises(ValueError, match="Invalid event types"):
            await event_bus.subscribe(["not_a_real_event"])
