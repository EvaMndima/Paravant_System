"""Paper trading session persistence model.

Stores the complete state of a paper trading session so it can be
restored after a Railway redeploy or container restart. One row per
strategy-symbol session (e.g., "paper_BTF_BTCUSDT").

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-007 - Input validation at boundaries
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class PaperTradingSession(Base, TimestampMixin):
    """Persisted state for a live paper trading session.

    Saved after every poll cycle so the session can resume from where it
    left off after a container restart or redeploy. The equity_curve is
    capped at 500 points to keep the row size bounded.

    Attributes:
        session_id: Unique session key (e.g. "paper_BTF_BTCUSDT").
        template_id: Strategy template (e.g. "bear_trend_follower").
        symbol: Trading symbol (e.g. "BTCUSDT").
        initial_capital: Starting capital in USDT.
        cash: Current cash balance after open-position cost deducted.
        position_data: JSON snapshot of the open position, or None.
        trade_log: JSON array of all completed TradeRecord dicts.
        equity_curve: JSON array of last 500 EquityPoint dicts.
        started_at: UTC timestamp when the session first started.
        total_trades: Cached count of completed trades.
    """

    __tablename__ = "paper_trading_sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    template_id: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    initial_capital: Mapped[float] = mapped_column(Float, nullable=False)
    cash: Mapped[float] = mapped_column(Float, nullable=False)
    position_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=lambda: None
    )
    trade_log: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=lambda: []
    )
    equity_curve: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=lambda: []
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
