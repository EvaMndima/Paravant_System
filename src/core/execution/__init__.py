"""Order execution module.

Provides the execution engine interface, adapter implementations,
order lifecycle management, position tracking, and execution quality monitoring.

Phase 4A: Execution Infrastructure
Phase 4B: Position Tracking & Execution Quality
"""
from src.core.execution.interface import Balance, ExecutionEngine, OrderResult
from src.core.execution.order_manager import OrderManager
from src.core.execution.position_tracker import (PositionSyncResult,
                                                 PositionTracker,
                                                 StalenessResult)
from src.core.execution.quality import (ExecutionReportGenerator,
                                        FillRateTracker, SlippageEstimator,
                                        SlippageTracker)

__all__ = [
    # Phase 4A
    "Balance",
    "ExecutionEngine",
    "OrderManager",
    "OrderResult",
    # Phase 4B - Position Tracking
    "PositionTracker",
    "PositionSyncResult",
    "StalenessResult",
    # Phase 4B - Execution Quality
    "SlippageTracker",
    "SlippageEstimator",
    "FillRateTracker",
    "ExecutionReportGenerator",
]
