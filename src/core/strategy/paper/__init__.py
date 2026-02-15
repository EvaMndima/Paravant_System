"""Paper trading package for strategy validation before live deployment.

Provides simulated and live paper trading modes to validate strategies
in near-real-time conditions without risking real capital.

Decision: DEC-2026-02-14-001 - Strategy status transitions (SIMULATED_PAPER, LIVE_PAPER)
"""
from src.core.strategy.paper.engine import PaperTradingEngine
from src.core.strategy.paper.manager import PaperTradingManager
from src.core.strategy.paper.types import PaperTradingMode, PaperTradingStatus
from src.core.strategy.paper.validator import PaperTradingThresholds, PaperTradingValidator

__all__ = [
    "PaperTradingEngine",
    "PaperTradingManager",
    "PaperTradingMode",
    "PaperTradingStatus",
    "PaperTradingThresholds",
    "PaperTradingValidator",
]
