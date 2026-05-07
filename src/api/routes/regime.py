"""Regime detection API endpoints.

Exposes the current auto-detected market regime written by RegimeRouter into
SystemState.circuit_breakers["auto_regime"], and a summary of all persisted
paper trading sessions for the monitoring dashboard.

Decision: DEC-2026-05-04-001 - Dual-EMA composite regime detection
Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.utils.logging import get_logger

# A session is considered active if its last DB write was within this window.
# Set just above the 15-minute (900 s) polling interval used by the engine.
_ACTIVE_WINDOW_SECONDS = 1500

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class RegimeCurrentResponse(BaseModel):
    """Current auto-detected regime state."""

    state: str = Field(
        ...,
        description=(
            "RegimeState value: strong_bull | pullback_bull | "
            "bounce_bear | strong_bear | unknown"
        ),
    )
    updated_at: str | None = Field(
        default=None,
        description="ISO 8601 UTC timestamp of last regime change",
    )
    source: str = Field(
        default="unknown",
        description="'auto' when written by RegimeRouter, 'unknown' if never set",
    )
    fetched_at: str = Field(
        ...,
        description="ISO 8601 UTC timestamp when this response was generated",
    )


# ---------------------------------------------------------------------------
# Module-level dependency — injected during API startup
# ---------------------------------------------------------------------------

_store: Any | None = None


def init_regime_routes(store: Any) -> None:
    """Inject the DataStore dependency.

    Called from src.api.main during startup_event.

    Args:
        store: DataStore instance shared across the API.
    """
    global _store
    _store = store


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/current", response_model=RegimeCurrentResponse)
async def get_current_regime() -> RegimeCurrentResponse:
    """Return the latest auto-detected regime written by RegimeRouter.

    Reads SystemState.circuit_breakers["auto_regime"] from the database.
    Returns state "unknown" if RegimeRouter has not run yet or has not
    written a regime (e.g. system just started).

    Returns:
        RegimeCurrentResponse with current regime state and metadata.
    """
    fetched_at = datetime.now(timezone.utc).isoformat()

    if _store is None:
        logger.warning("regime_route_store_not_initialized")
        return RegimeCurrentResponse(
            state="unknown",
            updated_at=None,
            source="unknown",
            fetched_at=fetched_at,
        )

    try:
        state = _store.get_system_state()
        auto_regime: dict[str, Any] = state.circuit_breakers.get("auto_regime", {})

        if not auto_regime:
            return RegimeCurrentResponse(
                state="unknown",
                updated_at=None,
                source="unknown",
                fetched_at=fetched_at,
            )

        return RegimeCurrentResponse(
            state=auto_regime.get("state", "unknown"),
            updated_at=auto_regime.get("updated_at"),
            source="auto",
            fetched_at=fetched_at,
        )

    except Exception as exc:
        logger.error("regime_current_fetch_failed", error=str(exc))
        return RegimeCurrentResponse(
            state="unknown",
            updated_at=None,
            source="unknown",
            fetched_at=fetched_at,
        )


# ---------------------------------------------------------------------------
# Paper sessions endpoint
# ---------------------------------------------------------------------------


class PaperSessionSummary(BaseModel):
    """Per-session summary derived from DB state."""

    session_id: str
    template_id: str
    symbol: str
    initial_capital: float
    current_equity: float
    pnl_usdt: float
    pnl_pct: float
    pnl_day_usdt: float
    total_trades: int
    is_active: bool
    started_at: str
    last_updated: str
    sparkline: list[float] = Field(default_factory=list)


class PaperSessionsResponse(BaseModel):
    """All persisted paper trading sessions."""

    sessions: list[PaperSessionSummary]
    fetched_at: str


def _extract_sparkline(equity_curve: list[dict[str, Any]], n: int = 10) -> list[float]:
    """Extract the last n equity values from the stored equity_curve JSON."""
    points = equity_curve[-n:] if len(equity_curve) >= n else equity_curve
    return [float(p.get("equity", 0.0)) for p in points]


def _pnl_day(equity_curve: list[dict[str, Any]], current_equity: float) -> float:
    """Return P&L vs. the equity curve point closest to 24 hours ago."""
    if not equity_curve:
        return 0.0

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    baseline: float | None = None

    for pt in equity_curve:
        try:
            ts = datetime.fromisoformat(pt["timestamp"])
            if ts <= cutoff:
                baseline = float(pt["equity"])
        except (KeyError, ValueError):
            continue

    if baseline is None:
        baseline = float(equity_curve[0].get("equity", current_equity))

    return current_equity - baseline


@router.get("/paper-sessions", response_model=PaperSessionsResponse)
async def get_paper_sessions() -> PaperSessionsResponse:
    """Return a summary of all persisted paper trading sessions.

    Reads PaperTradingSession rows written by PaperTradingEngine after each
    poll cycle. A session is considered active when its last DB write occurred
    within the past 25 minutes (just above the 15-minute engine poll interval).

    Returns:
        PaperSessionsResponse with per-session P&L, sparkline, and status.
    """
    fetched_at = datetime.now(timezone.utc).isoformat()

    if _store is None:
        logger.warning("regime_route_store_not_initialized")
        return PaperSessionsResponse(sessions=[], fetched_at=fetched_at)

    try:
        rows = _store.list_paper_sessions()
        active_cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=_ACTIVE_WINDOW_SECONDS
        )

        summaries: list[PaperSessionSummary] = []
        for row in rows:
            equity_curve: list[dict[str, Any]] = row.equity_curve or []
            current_equity = (
                float(equity_curve[-1]["equity"])
                if equity_curve
                else row.cash
            )
            pnl_usdt = current_equity - row.initial_capital
            pnl_pct = (pnl_usdt / row.initial_capital * 100.0) if row.initial_capital else 0.0

            updated_at = row.updated_at
            is_active = updated_at.tzinfo is not None and updated_at >= active_cutoff

            summaries.append(
                PaperSessionSummary(
                    session_id=row.session_id,
                    template_id=row.template_id,
                    symbol=row.symbol,
                    initial_capital=row.initial_capital,
                    current_equity=current_equity,
                    pnl_usdt=round(pnl_usdt, 2),
                    pnl_pct=round(pnl_pct, 2),
                    pnl_day_usdt=round(_pnl_day(equity_curve, current_equity), 2),
                    total_trades=row.total_trades,
                    is_active=is_active,
                    started_at=row.started_at.isoformat(),
                    last_updated=updated_at.isoformat(),
                    sparkline=_extract_sparkline(equity_curve),
                )
            )

        return PaperSessionsResponse(sessions=summaries, fetched_at=fetched_at)

    except Exception as exc:
        logger.error("paper_sessions_fetch_failed", error=str(exc))
        return PaperSessionsResponse(sessions=[], fetched_at=fetched_at)
