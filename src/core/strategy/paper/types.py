"""Paper trading data types.

Enum and dataclass for paper trading mode and status tracking.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-14-001 - Strategy lifecycle state machine
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class PaperTradingMode(str, enum.Enum):
    """Paper trading operation mode.

    SIMULATED: Runs on recent historical data (last 21 days).
    LIVE: Runs on real-time data with polling loop (7+ days).
    """

    SIMULATED = "simulated"
    LIVE = "live"


@dataclass(frozen=True)
class PaperTradingStatus:
    """Current status of a paper trading session.

    Provides a real-time snapshot of the paper trading engine's state,
    including performance metrics and validation status.

    Attributes:
        mode: Paper trading mode (SIMULATED or LIVE).
        strategy_id: ID of the strategy under paper trading.
        strategy_name: Name of the strategy.
        is_running: Whether the engine is currently active.
        started_at: Timezone-aware UTC start timestamp.
        stopped_at: Timezone-aware UTC stop timestamp (None if running).
        current_equity: Current portfolio equity value.
        initial_capital: Starting portfolio capital.
        current_pnl: Current cumulative P&L.
        current_pnl_pct: Current P&L as percentage of initial capital.
        num_trades: Number of completed trades so far.
        days_elapsed: Calendar days since start.
        validation_passed: Whether validation criteria are met.
        validation_errors: List of validation failures (empty if passed).
    """

    mode: PaperTradingMode
    strategy_id: str
    strategy_name: str
    is_running: bool = False
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    current_equity: float = 0.0
    initial_capital: float = 10_000.0
    current_pnl: float = 0.0
    current_pnl_pct: float = 0.0
    num_trades: int = 0
    days_elapsed: float = 0.0
    validation_passed: bool = False
    validation_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for API responses.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return {
            "mode": self.mode.value,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "is_running": self.is_running,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "current_equity": round(self.current_equity, 4),
            "initial_capital": self.initial_capital,
            "current_pnl": round(self.current_pnl, 4),
            "current_pnl_pct": round(self.current_pnl_pct, 4),
            "num_trades": self.num_trades,
            "days_elapsed": round(self.days_elapsed, 2),
            "validation_passed": self.validation_passed,
            "validation_errors": self.validation_errors,
        }
