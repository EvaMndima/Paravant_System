"""Integration tests for risk controls with real database.

Tests the risk management system with actual database operations:
- Kill switch state persistence across restarts
- Order validation with real portfolio data
- Position sizing with real account profiles

These tests use a temporary SQLite database for isolation.

Decision: DEC-2026-02-12-008 - Test coverage threshold 90% per file
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.core.config.risk_profiles import RiskProfileManager
from src.core.risk.controller import RiskController
from src.core.risk.kill_switch import KillSwitch
from src.core.risk.types import OrderRequest
from src.data.database import Base
from src.data.models.account import Account, AccountStatus, RiskProfile
from src.data.models.system import SystemState
from src.data.store import DataStore


@pytest.fixture
def temp_db_path() -> str:
    """Create temporary database path."""
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_integration.db"
        yield f"sqlite:///{db_path}"


@pytest.fixture
def data_store(temp_db_path: str) -> DataStore:
    """Create DataStore with temporary database."""
    # Create engine and tables
    engine = create_engine(temp_db_path)
    Base.metadata.create_all(engine)

    # Create store
    store = DataStore()
    store.engine = engine  # Override the global engine with test engine

    # Initialize system state
    with Session(engine) as session:
        system_state = SystemState(
            kill_switch_active=False,
            kill_switch_reason=None,
            kill_switch_activated_at=None,
            trading_enabled=True,
        )
        session.add(system_state)
        session.commit()

    yield store

    # Cleanup: Dispose engine to close all connections
    store.engine.dispose()


@pytest.fixture
def test_account(data_store: DataStore) -> Account:
    """Create test account with balanced profile."""
    with Session(data_store.engine) as session:
        account = Account(
            id="INT_TEST_001",
            name="Integration Test Account",
            broker="binance_testnet",
            balance_usdt=10000.0,
            equity_usdt=10000.0,
            profile=RiskProfile.BALANCED,
            regime="trending_up",
            status=AccountStatus.ACTIVE,
        )
        session.add(account)
        session.commit()
        session.refresh(account)
        return account


# ===========================================================================
# Kill Switch Integration Tests
# ===========================================================================


class TestKillSwitchIntegration:
    """Test kill switch with real database persistence."""

    def test_kill_switch_persists_across_restarts(
        self,
        data_store: DataStore,
    ) -> None:
        """Kill switch state should survive system restart."""
        # Create first kill switch instance and activate
        ks1 = KillSwitch(data_store)
        ks1.activate("Integration test", actor="test")

        assert ks1.is_active() is True

        # Simulate restart: create new kill switch instance
        ks2 = KillSwitch(data_store)
        ks2.load_state()

        # State should be preserved
        assert ks2.is_active() is True
        status = ks2.get_status()
        assert status["reason"] == "Integration test"

    def test_kill_switch_deactivation_persists(
        self,
        data_store: DataStore,
    ) -> None:
        """Kill switch deactivation should persist to database."""
        ks = KillSwitch(data_store)
        ks.activate("Test activation", actor="test")

        # Generate and use deactivation code
        code = ks.generate_deactivation_code()
        success = ks.deactivate(code, actor="test")

        assert success is True
        assert ks.is_active() is False

        # Verify persistence
        state = data_store.get_system_state()
        assert state.kill_switch_active is False


# ===========================================================================
# Risk Controller Integration Tests
# ===========================================================================


class TestRiskControllerIntegration:
    """Test risk controller with real database and profiles."""

    def test_validate_order_with_real_account(
        self,
        data_store: DataStore,
        test_account: Account,
    ) -> None:
        """Order validation should work with real account data."""
        profile_manager = RiskProfileManager()
        controller = RiskController(
            store=data_store,
            profile_manager=profile_manager,
        )

        # Create valid order
        order = OrderRequest(
            account_id="INT_TEST_001",
            strategy_id="INT_STRAT_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.001,  # Small quantity
            price=50000.0,
        )

        # Validate order
        results = controller.validate_order(order)

        # All checks should pass
        assert all(r.approved for r in results)
        assert len(results) == 7  # All 7 checks ran

    def test_validate_order_rejected_by_kill_switch(
        self,
        data_store: DataStore,
        test_account: Account,
    ) -> None:
        """Order should be rejected when kill switch is active."""
        # Activate kill switch
        ks = KillSwitch(data_store)
        ks.activate("Testing rejection", actor="test")

        # Create controller
        profile_manager = RiskProfileManager()
        controller = RiskController(
            store=data_store,
            profile_manager=profile_manager,
        )

        # Create order
        order = OrderRequest(
            account_id="INT_TEST_001",
            strategy_id="INT_STRAT_001",
            symbol="BTCUSDT",
            side="buy",
            quantity=0.001,
            price=50000.0,
        )

        # Validate order
        results = controller.validate_order(order)

        # Should fail at kill switch check
        assert len(results) == 1
        assert results[0].check_name == "kill_switch"
        assert not results[0].approved

    def test_position_sizing_with_real_profile(
        self,
        data_store: DataStore,
        test_account: Account,
    ) -> None:
        """Position sizing should work with real account and profile."""
        profile_manager = RiskProfileManager()
        controller = RiskController(
            store=data_store,
            profile_manager=profile_manager,
        )

        # Calculate position size
        result = controller.calculate_position_size(
            account_id="INT_TEST_001",
            symbol="BTCUSDT",
            side="buy",
            entry_price=50000.0,
            stop_loss_price=49000.0,
            method="fixed_risk",
        )

        # Should return valid result
        assert result.quantity > 0
        assert result.notional_value > 0
        assert result.risk_pct > 0
        assert result.sizing_method == "fixed_risk"


# ===========================================================================
# Portfolio State Integration Tests
# ===========================================================================


class TestPortfolioStateIntegration:
    """Test portfolio state building with real data."""

    def test_portfolio_state_from_real_account(
        self,
        data_store: DataStore,
        test_account: Account,
    ) -> None:
        """Portfolio state should be built from real account data."""
        profile_manager = RiskProfileManager()
        controller = RiskController(
            store=data_store,
            profile_manager=profile_manager,
        )

        # Get portfolio state
        portfolio = controller.get_portfolio_state("INT_TEST_001")

        # Verify data matches account
        assert portfolio.account_id == "INT_TEST_001"
        assert portfolio.total_equity == 10000.0
        assert portfolio.cash_balance == 10000.0
        assert portfolio.regime == "trending_up"
