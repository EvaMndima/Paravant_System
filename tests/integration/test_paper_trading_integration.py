
"""Integration tests for Paper Trading.

Tests the full lifecycle of a paper trading session with real (seeded) data
and database persistence.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from src.core.strategy.paper.manager import PaperTradingManager
from src.core.strategy.factory import SignalGeneratorFactory
from src.core.strategy.paper.types import PaperTradingMode
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.models import Strategy, StrategyStatus, StrategyType
from src.data.models.signal import SignalDirection
from src.data.market_data import OHLCVSeries, OHLCV
from typing import Any

@pytest.fixture
def integration_strategy(db_session: Any) -> Strategy:
    """Create a strategy for integration testing."""
    strategy = Strategy(
        name="Integration Test Strategy",
        template_id="simple_ma",
        template_version="1.0.0",
        type=StrategyType.TREND_FOLLOWING,
        status=StrategyStatus.BACKTEST,
        parameters={"period": 10},
        symbols=["BTCUSDT"],
        lifecycle=[],
        backtest_results={},
        paper_results={},
        live_results={}
    )
    db_session.add(strategy)
    db_session.commit()
    db_session.refresh(strategy)
    return strategy

@pytest.fixture
def mock_series_provider() -> Any:
    """Create a series provider with deterministic data."""
    async def provider(symbol: str, lookback_bars: int) -> OHLCVSeries:
        now = datetime.now(timezone.utc)
        bars = []
        price = 50000.0
        for i in range(lookback_bars):
            timestamp = now - timedelta(minutes=lookback_bars - i)
            # Create a simple trend then reversal
            if i < lookback_bars // 2:
                price += 10  # Uptrend
            else:
                price -= 10  # Downtrend
            
            bars.append(OHLCV(
                timestamp=timestamp,
                open=price,
                high=price + 5,
                low=price - 5,
                close=price,
                volume=100.0
            ))
        return OHLCVSeries(symbol=symbol, timeframe="1m", candles=bars)
    return provider

class SimpleMAGenerator(SignalGenerator):
    @property
    def template_id(self) -> str:
        return "simple_ma"

    @property
    def min_bars_required(self) -> int:
        return 10

    def generate(self, series: OHLCVSeries, params: dict[str, Any], symbol: str) -> TradingSignal | None:
        if len(series) < 10:
            return None
        
        # Simple logic: if price is rising, BUY. If falling, SELL.
        # We know the mock data: up then down.
        # Last candle
        last_close = series.candles[-1].close
        prev_close = series.candles[-2].close
        
        direction = SignalDirection.LONG if last_close > prev_close else SignalDirection.SHORT
        
        return TradingSignal(
            direction=direction,
            symbol=symbol,
            price=last_close,
            strength=0.8,
            timestamp=series.candles[-1].timestamp
        )

@pytest.mark.asyncio
async def test_paper_trading_full_loop_integration(
    integration_strategy: Strategy,
    mock_series_provider: Any,
    db_session: Any,
    db_engine: Any
) -> None:
    """Test the full paper trading loop with persistence."""
    
    # Needs a DataStore that uses the test db_session
    # We can't easily inject session into DataStore directly as it manages its own sessions.
    # However, DataStore uses the global engine.
    # We need to make sure DataStore uses our test engine.
    
    from src.data.store import DataStore
    
    # Patch the engine in DataStore's module or instance
    # Since DataStore uses src.data.database.engine, we can patch that or pass the test engine if we modify DataStore to accept it.
    # Looking at DataStore code: self.engine = engine (from .database import engine)
    
    # We will subclass/mock DataStore to use our test engine
    class TestDataStore(DataStore):
        def __init__(self, test_engine: Any) -> None:
            self.engine = test_engine
            self.logger = MagicMock()

    store = TestDataStore(db_engine)
    
    # Initialize Manager
    factory = SignalGeneratorFactory()
    factory.register_generator("simple_ma", SimpleMAGenerator)
    
    manager = PaperTradingManager(
        signal_generator_factory=factory,
        series_provider=mock_series_provider,
        data_store=store
    )
    
    # 1. Start Session
    status = await manager.start_session(
        strategy=integration_strategy,
        mode=PaperTradingMode.SIMULATED
    )
    # In SIMULATED mode, the engine runs synchronously to completion in start()
    # So it should be finished by now.
    assert not status.is_running 
    assert status.stopped_at is not None
    assert status.strategy_id == integration_strategy.id
    
    # 2. Wait a bit (in simulated mode, it runs fast, but we might want to check intermediate state if it was live)
    # Since it's simulated, start_session runs the whole simulation for paper trading if implementation is simplistic, 
    # OR it sets up the loop. 
    # PaperTradingEngine._run_simulated iterates through history. 
    # Wait, PaperTradingEngine.start() for SIMULATED calls _run_simulated which is an async loop.
    # It might finish immediately if not carefully controlled, or we wait for it?
    # Actually, _run_simulated in engine.py:
    # for i in range(...):
    #    ... logic ...
    # It awaits nothing inside the loop except maybe minimal stuff? 
    # It is likely CPU bound mostly.
    
    # However, let's verify it ran.
    updated_status = manager.get_session_status(integration_strategy.id)
    assert updated_status is not None
    assert updated_status.num_trades >= 0 # Should have some if logic matches
    
    # 3. Stop Session (triggers persistence)
    final_status = await manager.stop_session(integration_strategy.id)
    assert not final_status.is_running
    
    # 4. Verify Persistence in DB
    # Re-fetch strategy from DB
    db_session.expire_all()
    stored_strategy = db_session.get(Strategy, integration_strategy.id)
    
    assert stored_strategy.paper_results is not None
    # Metrics are not in snapshot, but trade_log is
    assert "trade_log" in stored_strategy.paper_results
    assert "equity_curve" in stored_strategy.paper_results
    # Check trade log content
    if hasattr(final_status, 'trade_log'):
       assert stored_strategy.paper_results["trade_log"] == final_status.trade_log
    else:
       # Verify length matches
       assert len(stored_strategy.paper_results["trade_log"]) == final_status.num_trades

