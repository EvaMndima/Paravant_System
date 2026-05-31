"""Unit tests for PaperTradingEngine."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from src.core.exceptions import PaperTradingError
from src.core.strategy.backtest.metrics import BacktestMetrics
from src.core.strategy.backtest.portfolio import OpenPosition
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.factory import SignalGeneratorFactory
from src.core.strategy.paper.engine import PaperTradingEngine
from src.core.strategy.paper.types import PaperTradingMode, PaperTradingStatus
from src.data.market_data import OHLCV, OHLCVSeries
from src.core.strategy.signals import TradingSignal
from src.data.models import Strategy, StrategyStatus
from src.data.models.signal import SignalDirection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_series(length: int = 100, start_price: float = 10000.0) -> OHLCVSeries:
    """Create a dummy OHLCVSeries."""
    candles = []
    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for i in range(length):
        candles.append(
            OHLCV(
                timestamp=base_time + timedelta(hours=i),
                open=start_price,
                high=start_price + 100.0,
                low=start_price - 100.0,
                close=start_price,
                volume=1000.0,
            )
        )
    return OHLCVSeries(candles, symbol="BTCUSDT", timeframe="1h")


@pytest.fixture
def mock_strategy() -> Strategy:
    """Create a mock strategy."""
    return Strategy(
        id="test-strategy-001",
        name="Test Strategy",
        template_id="TestTemplate",
        symbols=["BTCUSDT"],
        status=StrategyStatus.BACKTEST,
        parameters={"period": 14, "timeframe": "1h"},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_factory() -> MagicMock:
    """Create a mock SignalGeneratorFactory."""
    factory = MagicMock(spec=SignalGeneratorFactory)
    generator = Mock()
    generator.min_bars_required = 10
    
    # helper to generate a signal occasionally
    def generate_signal(series, params, symbol):
        # Generate a BUY signal on the 10th bar, SELL on 20th
        if len(series) > 10 and len(series) % 20 == 10:
             return TradingSignal(
                 symbol="BTCUSDT",
                 direction=SignalDirection.LONG,
                 timestamp=series[-1].timestamp,
                 price=series[-1].close,
             )
        if len(series) > 20 and len(series) % 20 == 0:
             return TradingSignal(
                 symbol="BTCUSDT",
                 direction=SignalDirection.SHORT,
                 timestamp=series[-1].timestamp,
                 price=series[-1].close,
             )
        return None

    generator.generate.side_effect = generate_signal
    factory.get_generator.return_value = generator
    return factory


@pytest.fixture
def mock_series_provider() -> AsyncMock:
    """Create a mock series provider."""
    provider = AsyncMock()
    # Default behavior: return enough data
    provider.return_value = _make_series(length=100)
    return provider


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPaperTradingEngine:
    """Tests for PaperTradingEngine."""

    @pytest.mark.asyncio
    async def test_initialization(
        self,
        mock_strategy: Strategy,
        mock_factory: MagicMock,
        mock_series_provider: AsyncMock,
    ) -> None:
        """Engine should initialize in valid state."""
        engine = PaperTradingEngine(
            strategy=mock_strategy,
            signal_generator_factory=mock_factory,
            series_provider=mock_series_provider,
            mode=PaperTradingMode.SIMULATED,
        )
        assert engine.strategy_id == "test-strategy-001"
        assert engine.is_running is False
        assert engine.mode == PaperTradingMode.SIMULATED
        assert engine.portfolio.cash == 10000.0  # Default capital

    @pytest.mark.asyncio
    async def test_start_simulated_success(
        self,
        mock_strategy: Strategy,
        mock_factory: MagicMock,
        mock_series_provider: AsyncMock,
    ) -> None:
        """Simulated mode should run to completion."""
        # Setup provider to return data
        series = _make_series(length=50)
        mock_series_provider.return_value = series

        engine = PaperTradingEngine(
            strategy=mock_strategy,
            signal_generator_factory=mock_factory,
            series_provider=mock_series_provider,
            mode=PaperTradingMode.SIMULATED,
        )

        await engine.start()

        assert engine.is_running is False  # Should finish
        assert len(engine.portfolio.equity_curve) > 0
        # Check that we processed bars (generator called)
        mock_factory.get_generator.return_value.generate.assert_called()

        status = engine.get_status()
        assert status.mode == PaperTradingMode.SIMULATED
        assert status.days_elapsed > 0


    @pytest.mark.asyncio
    async def test_start_simulated_insufficient_data(
        self,
        mock_strategy: Strategy,
        mock_factory: MagicMock,
        mock_series_provider: AsyncMock,
    ) -> None:
        """Should raise error if insufficient data."""
        # Return only 5 bars, need 10+2=12
        mock_series_provider.return_value = _make_series(length=5)

        engine = PaperTradingEngine(
            strategy=mock_strategy,
            signal_generator_factory=mock_factory,
            series_provider=mock_series_provider,
            mode=PaperTradingMode.SIMULATED,
        )

        with pytest.raises(PaperTradingError) as exc:
            await engine.start()
        
        assert "Insufficient data" in str(exc.value)

    @pytest.mark.asyncio
    async def test_start_live_flow(
        self,
        mock_strategy: Strategy,
        mock_factory: MagicMock,
        mock_series_provider: AsyncMock,
    ) -> None:
        """Live mode should loop until stopped."""
        # We need to control the loop.
        # Can't easily count loops inside start(), but we can stop it from outside.
        # We'll spawn start() as a task, wait a bit, then stop().
        
        engine = PaperTradingEngine(
            strategy=mock_strategy,
            signal_generator_factory=mock_factory,
            series_provider=mock_series_provider,
            mode=PaperTradingMode.LIVE,
        )

        # Mock the polling interval to be very short for test
        # Note: changing constant in module might affect other tests potentially, 
        # but here we can patch it or rely on fast execution.
        # Better: just set stop event quickly.
        
        task = asyncio.create_task(engine.start())
        
        # Wait for engine to start running
        for _ in range(10):
            if engine.is_running:
                break
            await asyncio.sleep(0.01)
        
        assert engine.is_running is True
        
        # Stop it
        await engine.stop()
        await task  # Should return
        
        assert engine.is_running is False
        assert engine.get_status().stopped_at is not None

    @pytest.mark.asyncio
    async def test_start_already_running(
        self,
        mock_strategy: Strategy,
        mock_factory: MagicMock,
        mock_series_provider: AsyncMock,
    ) -> None:
        """Starting twice should raise error."""
        engine = PaperTradingEngine(
            strategy=mock_strategy,
            signal_generator_factory=mock_factory,
            series_provider=mock_series_provider,
            mode=PaperTradingMode.LIVE,
        )
        
        task = asyncio.create_task(engine.start())
        await asyncio.sleep(0.01) # let it start
        
        with pytest.raises(PaperTradingError) as exc:
            await engine.start()
            
        assert "already running" in str(exc.value)
        
        await engine.stop()
        await task

    @pytest.mark.asyncio
    async def test_get_metrics(
        self,
        mock_strategy: Strategy,
        mock_factory: MagicMock,
        mock_series_provider: AsyncMock,
    ) -> None:
        """get_metrics should return calculated metrics."""
        engine = PaperTradingEngine(
            strategy=mock_strategy,
            signal_generator_factory=mock_factory,
            series_provider=mock_series_provider,
            mode=PaperTradingMode.SIMULATED,
        )
        
        # Manually inject some history
        engine.portfolio.record_equity(datetime.now(timezone.utc), 10100.0)
        
        metrics = engine.get_metrics()
        assert isinstance(metrics, dict)
        assert "total_return_pct" in metrics
        
    @pytest.mark.asyncio
    async def test_state_snapshot(
        self,
        mock_strategy: Strategy,
        mock_factory: MagicMock,
        mock_series_provider: AsyncMock,
    ) -> None:
        """get_state_snapshot should return serializable dict."""
        engine = PaperTradingEngine(
            strategy=mock_strategy,
            signal_generator_factory=mock_factory,
            series_provider=mock_series_provider,
            mode=PaperTradingMode.SIMULATED,
        )
        
        snap = engine.get_state_snapshot()
        assert snap["strategy_id"] == "test-strategy-001"
        assert snap["mode"] == "simulated"
        assert snap["initial_capital"] == 10000.0
        assert "trade_log" in snap
        assert "equity_curve" in snap

    @pytest.mark.asyncio
    async def test_live_force_close_uses_last_close_price(
        self,
        mock_strategy: Strategy,
        mock_factory: MagicMock,
        mock_series_provider: AsyncMock,
    ) -> None:
        """PARA-02 regression: force-close on stop must book the open position
        at the last observed market close, not the dimensionless
        equity/position_value ratio (~$11) the old code produced.
        """
        engine = PaperTradingEngine(
            strategy=mock_strategy,
            signal_generator_factory=mock_factory,
            series_provider=mock_series_provider,
            mode=PaperTradingMode.LIVE,
        )

        # Inject an open LONG position, as an in-flight/restored session holds.
        last_close = 10000.0
        engine._portfolio._position = OpenPosition(
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            quantity=0.1,
            entry_price=9500.0,
            entry_commission=0.95,
            entry_slippage=0.5,
            entry_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        # Record an equity point so the OLD guard would pass and the OLD code
        # would compute its ratio (equity 11000 / position_value 1000 = 11.0) —
        # this is what makes the test a true regression for the price bug.
        engine._portfolio.record_equity(
            timestamp=datetime(2025, 1, 1, 1, tzinfo=timezone.utc),
            current_price=last_close,
        )
        # The engine has "seen" the market close this run.
        engine._last_close_price = last_close

        # Pre-signal stop so the polling loop body is skipped and only the
        # force-close path runs (deterministic, no async timing).
        engine._stop_event.set()
        await engine._run_live()

        assert len(engine.portfolio.trade_log) == 1
        trade = engine.portfolio.trade_log[-1]
        # Real market price (minus sell-side slippage), NOT the ~$11 ratio.
        assert trade.exit_price > 100.0
        assert trade.exit_price == pytest.approx(last_close, rel=0.01)

    @pytest.mark.asyncio
    async def test_live_force_close_falls_back_to_entry_price(
        self,
        mock_strategy: Strategy,
        mock_factory: MagicMock,
        mock_series_provider: AsyncMock,
    ) -> None:
        """PARA-02: when no live bar was processed this run (last close is
        None), force-close falls back to the position's entry price — a real,
        positive price — rather than fabricating one.
        """
        engine = PaperTradingEngine(
            strategy=mock_strategy,
            signal_generator_factory=mock_factory,
            series_provider=mock_series_provider,
            mode=PaperTradingMode.LIVE,
        )

        entry_price = 9500.0
        engine._portfolio._position = OpenPosition(
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            quantity=0.1,
            entry_price=entry_price,
            entry_commission=0.95,
            entry_slippage=0.5,
            entry_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        # _last_close_price is intentionally left at its None default.
        assert engine._last_close_price is None

        engine._stop_event.set()
        await engine._run_live()

        assert len(engine.portfolio.trade_log) == 1
        trade = engine.portfolio.trade_log[-1]
        assert trade.exit_price == pytest.approx(entry_price, rel=0.01)
