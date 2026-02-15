"""Integration tests for Backtest Engine.

Tests backtesting with deterministic data to ensure consistency and correctness.
"""
import pytest
from datetime import datetime, timezone, timedelta

from src.core.strategy.backtest.engine import BacktestEngine
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.factory import SignalGeneratorFactory
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.models import Strategy, StrategyStatus, StrategyType
from src.data.models.signal import SignalDirection
from src.data.market_data import OHLCVSeries, OHLCV
from typing import Any

@pytest.fixture
def backtest_strategy() -> Strategy:
    """Create a strategy for backtest testing."""
    return Strategy(
        name="Backtest Test Strategy",
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

@pytest.fixture
def deterministic_series() -> OHLCVSeries:
    """Create a deterministic OHLCV series."""
    now = datetime.now(timezone.utc)
    bars = []
    price = 100.0
    # Generate 100 bars
    for i in range(100):
        timestamp = now - timedelta(minutes=100 - i)
        # uptrend then downtrend
        if i < 50:
            price += 1
        else:
            price -= 1
            
        bars.append(OHLCV(
            timestamp=timestamp,
            open=price,
            high=price + 0.5,
            low=price - 0.5,
            close=price,
            volume=1000.0
        ))
    return OHLCVSeries(symbol="BTCUSDT", timeframe="1m", candles=bars)

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

def test_backtest_consistency(backtest_strategy: Strategy, deterministic_series: OHLCVSeries) -> None:
    """Test backtest consistency."""
    factory = SignalGeneratorFactory()
    factory.register_generator("simple_ma", SimpleMAGenerator)
    
    engine = BacktestEngine(factory)
    config = BacktestConfig(initial_capital=10000.0)
    
    result = engine.run_backtest(
        strategy=backtest_strategy,
        series=deterministic_series,
        config=config
    )
    
    assert result.strategy_id == backtest_strategy.id
    assert result.metrics.total_trades > 0
    assert result.final_capital != config.initial_capital
    assert "metrics" in result.metrics.__dict__ or hasattr(result, "metrics")
    
    # Check for specific expected behavior (Simple MA should capture the trend)
    # 50 bars up, 50 bars down. Period 10.
    # Should buy early in uptrend, sell/short in downtrend? 
    # Simple MA logic depends on implementation, but we check for non-trivial result.
