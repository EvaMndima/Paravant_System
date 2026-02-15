"""Unit tests for PaperTradingManager."""
from __future__ import annotations


from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import PaperTradingError
from src.core.strategy.paper.engine import PaperTradingEngine
from src.core.strategy.paper.manager import PaperTradingManager
from src.core.strategy.paper.types import PaperTradingMode, PaperTradingStatus
from src.data.models import Strategy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_strategy() -> Strategy:
    """Create a mock strategy."""
    strategy = MagicMock(spec=Strategy)
    strategy.id = "test-strat-1"
    strategy.name = "Test Strategy"
    strategy.template_id = "SMACross"
    strategy.symbols = ["BTCUSDT"]
    strategy.parameters = {}
    return strategy


@pytest.fixture
def manager() -> Generator[PaperTradingManager, None, None]:
    """Create a PaperTradingManager instance."""
    # We need to mock SignalGeneratorFactory inside the manager or instantiate one?
    # The manager creates it in __init__. We can patch the class.
    with patch("src.core.strategy.paper.manager.SignalGeneratorFactory") as MockFactory:
         # Mock series provider as well
         mock_provider = AsyncMock()
         mock_factory = MockFactory.return_value
         with patch("src.core.strategy.paper.manager.DataStore") as MockDataStore:
             mock_data_store = MockDataStore.return_value
             mgr = PaperTradingManager(
                 signal_generator_factory=mock_factory,
                 series_provider=mock_provider,
                 data_store=mock_data_store,
             )
             yield mgr


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPaperTradingManager:
    """Tests for PaperTradingManager."""

    @pytest.mark.asyncio
    async def test_start_session(
        self,
        manager: PaperTradingManager,
        mock_strategy: Strategy,
    ) -> None:
        """Should start a new session."""
        with patch("src.core.strategy.paper.manager.PaperTradingEngine") as MockEngine:
            # Setup mock engine
            mock_engine_instance = AsyncMock(spec=PaperTradingEngine)
            mock_engine_instance.strategy_id = mock_strategy.id
            mock_engine_instance.is_running = True
            mock_engine_instance.get_status.return_value = PaperTradingStatus(
                mode=PaperTradingMode.SIMULATED,
                strategy_id=mock_strategy.id,
                strategy_name="Test",
            )
            
            MockEngine.return_value = mock_engine_instance

            status = await manager.start_session(
                strategy=mock_strategy,
                mode=PaperTradingMode.SIMULATED,
            )

            assert status.strategy_id == mock_strategy.id
            mock_engine_instance.start.assert_awaited_once()
            
            # Verify session is stored
            assert manager.get_session_status(mock_strategy.id) is not None

    @pytest.mark.asyncio
    async def test_start_duplicate_session(
        self,
        manager: PaperTradingManager,
        mock_strategy: Strategy,
    ) -> None:
        """Starting session for existing strategy should raise error."""
        # Inject an existing session
        mock_engine = AsyncMock(spec=PaperTradingEngine)
        manager._sessions[mock_strategy.id] = mock_engine

        with pytest.raises(PaperTradingError) as exc:
            await manager.start_session(mock_strategy, PaperTradingMode.SIMULATED)
            
        assert "Strategy already has an active paper trading session" in str(exc.value)

    @pytest.mark.asyncio
    async def test_stop_session_success(
        self,
        manager: PaperTradingManager,
    ) -> None:
        """Stopping existing session should succeed."""
        strat_id = "test-strat-1"
        mock_engine = AsyncMock(spec=PaperTradingEngine)
        mock_engine.is_running = True
        
        manager._sessions[strat_id] = mock_engine
        
        status = await manager.stop_session(strat_id)
        
        mock_engine.stop.assert_awaited_once()
        assert status is not None
        # Should NOT remove from sessions immediately? 
        # The manager keeps stopped sessions until restart or cleanup?
        # Check implementation: stop_session returns status but kept in dict?
        assert strat_id in manager._sessions 

    @pytest.mark.asyncio
    async def test_stop_session_not_found(
        self,
        manager: PaperTradingManager,
    ) -> None:
        """Stopping non-existent session should raise error."""
        with pytest.raises(PaperTradingError) as exc:
            await manager.stop_session("missing-id")
        
        assert "No paper trading session found" in str(exc.value)

    def test_get_session_status_found(self, manager: PaperTradingManager) -> None:
        """Should return status if session exists."""
        strat_id = "s1"
        mock_engine = MagicMock(spec=PaperTradingEngine)
        expected_status = PaperTradingStatus(
             mode=PaperTradingMode.SIMULATED,
             strategy_id=strat_id,
             strategy_name="Test",
        )
        mock_engine.get_status.return_value = expected_status
        manager._sessions[strat_id] = mock_engine
        
        status = manager.get_session_status(strat_id)
        assert status == expected_status

    def test_get_session_status_missing(self, manager: PaperTradingManager) -> None:
        """Should return None if session missing."""
        assert manager.get_session_status("missing") is None

    def test_get_session_snapshot(self, manager: PaperTradingManager) -> None:
        """Should return snapshot if session exists."""
        strat_id = "s1"
        mock_engine = MagicMock(spec=PaperTradingEngine)
        mock_engine.get_state_snapshot.return_value = {"foo": "bar"}
        manager._sessions[strat_id] = mock_engine
        
        snap = manager.get_session_snapshot(strat_id)
        assert snap == {"foo": "bar"}

    def test_get_all_sessions(self, manager: PaperTradingManager) -> None:
        """Should list all sessions."""
        m1 = MagicMock()
        m1.get_status.return_value = MagicMock(strategy_id="s1")
        m2 = MagicMock()
        m2.get_status.return_value = MagicMock(strategy_id="s2")
        
        manager._sessions["s1"] = m1
        manager._sessions["s2"] = m2
        
        sessions = manager.get_all_sessions()
        assert len(sessions) == 2
        ids = sorted([s.strategy_id for s in sessions])
        assert "s1" in ids
        assert "s2" in ids
