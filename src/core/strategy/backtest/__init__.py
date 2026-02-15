"""Backtest engine package for historical strategy simulation.

Provides deterministic backtesting with realistic fill simulation,
commission/slippage modeling, and comprehensive performance metrics.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-007 - Input validation at boundaries
"""
from src.core.strategy.backtest.engine import BacktestEngine
from src.core.strategy.backtest.metrics import (
    BacktestMetrics,
    BacktestMetricsCalculator,
)
from src.core.strategy.backtest.portfolio import PortfolioState
from src.core.strategy.backtest.result import BacktestResult
from src.core.strategy.backtest.trader import SimulatedTrader
from src.core.strategy.backtest.types import (
    BacktestConfig,
    EquityPoint,
    TradeRecord,
)
from src.core.strategy.backtest.validator import (
    BacktestValidator,
    ValidationThresholds,
)

__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestMetrics",
    "BacktestMetricsCalculator",
    "BacktestResult",
    "BacktestValidator",
    "EquityPoint",
    "PortfolioState",
    "SimulatedTrader",
    "TradeRecord",
    "ValidationThresholds",
]
