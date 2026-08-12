"""P&L tracking API endpoints.

Provides endpoints for daily/monthly P&L views, strategy-level breakdown,
symbol-level breakdown, and monthly heatmap data for frontend charting.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class DailyPnLEntry(BaseModel):
    """Single daily P&L record."""

    date: str
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    portfolio_value: float
    daily_return_pct: float | None = None
    drawdown_pct: float | None = None
    trades_count: int = 0
    winning_trades: int = 0
    losing_trades: int = 0


class DailyPnLResponse(BaseModel):
    """Daily P&L history."""

    records: list[DailyPnLEntry]
    total: int
    period_start: str
    period_end: str
    cumulative_pnl: float = 0.0


class MonthlyPnLEntry(BaseModel):
    """Monthly aggregated P&L."""

    year: int
    month: int
    month_name: str
    total_pnl: float
    return_pct: float = 0.0
    trades_count: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0


class MonthlyPnLResponse(BaseModel):
    """Monthly P&L history."""

    records: list[MonthlyPnLEntry]
    total: int


class StrategyPnLEntry(BaseModel):
    """P&L breakdown by strategy."""

    strategy_id: str
    strategy_name: str
    total_pnl: float
    return_pct: float = 0.0
    trades_count: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0


class StrategyPnLResponse(BaseModel):
    """Strategy-level P&L breakdown."""

    strategies: list[StrategyPnLEntry]
    total: int


class SymbolPnLEntry(BaseModel):
    """P&L breakdown by trading symbol."""

    symbol: str
    total_pnl: float
    trades_count: int = 0
    avg_pnl_per_trade: float = 0.0


class SymbolPnLResponse(BaseModel):
    """Symbol-level P&L breakdown."""

    symbols: list[SymbolPnLEntry]
    total: int


class HeatmapCell(BaseModel):
    """Single cell in the monthly heatmap."""

    year: int
    month: int
    return_pct: float
    trade_count: int = 0


class MonthlyHeatmapResponse(BaseModel):
    """Monthly heatmap data for charting."""

    cells: list[HeatmapCell]
    years: list[int]
    months: list[int] = Field(default_factory=lambda: list(range(1, 13)))


# Month name mapping
_MONTH_NAMES: dict[int, str] = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


# ---------------------------------------------------------------------------
# Module-level dependency injection
# ---------------------------------------------------------------------------

_store: Any | None = None


def get_store() -> Any:
    """Get the DataStore instance.

    Returns:
        DataStore instance.

    Raises:
        HTTPException: If DataStore is not initialized.
    """
    if _store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DataStore not initialized. Call init_pnl_routes() first.",
        )
    return _store


def init_pnl_routes(store: Any) -> None:
    """Initialize the P&L routes with a DataStore instance.

    Args:
        store: Configured DataStore instance.
    """
    global _store  # noqa: PLW0603
    _store = store
    logger.info("pnl_routes_initialized")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_primary_account_id(store: Any) -> str:
    """Get the primary (first active) account ID.

    Args:
        store: DataStore instance.

    Returns:
        Account ID string.

    Raises:
        HTTPException: 404 if no active account found.
    """
    accounts = store.get_active_accounts()
    if not accounts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active account found. Create an account first.",
        )
    # get_store() is declared Any (injected at startup), so Account.id
    # reads as Any here. The model declares Mapped[str].
    return cast(str, accounts[0].id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/daily",
    response_model=DailyPnLResponse,
    status_code=status.HTTP_200_OK,
    summary="Daily P&L history",
    description="Returns daily P&L records with optional date range filter.",
)
async def get_daily_pnl(
    days: int = Query(default=30, ge=1, le=365, description="Number of days of history"),
    account_id: str | None = Query(default=None, description="Account ID (defaults to primary)"),
) -> DailyPnLResponse:
    """Get daily P&L records.

    Args:
        days: Number of days to look back.
        account_id: Optional account ID (defaults to primary account).

    Returns:
        DailyPnLResponse with records and cumulative total.
    """
    store = get_store()
    acc_id = account_id or _get_primary_account_id(store)

    today = date.today()
    start_date = today - timedelta(days=days)

    records = store.get_pnl_history(acc_id, start_date=start_date, end_date=today)

    entries = [
        DailyPnLEntry(
            date=str(r.record_date),
            realized_pnl=r.realized_pnl,
            unrealized_pnl=r.unrealized_pnl,
            total_pnl=r.total_pnl,
            portfolio_value=r.portfolio_value,
            daily_return_pct=r.daily_return_pct,
            drawdown_pct=r.drawdown_pct,
            trades_count=r.trades_count,
            winning_trades=r.winning_trades,
            losing_trades=r.losing_trades,
        )
        for r in records
    ]

    cumulative_pnl = sum(r.total_pnl for r in records)

    return DailyPnLResponse(
        records=entries,
        total=len(entries),
        period_start=str(start_date),
        period_end=str(today),
        cumulative_pnl=cumulative_pnl,
    )


@router.get(
    "/monthly",
    response_model=MonthlyPnLResponse,
    status_code=status.HTTP_200_OK,
    summary="Monthly P&L summary",
    description="Returns P&L aggregated by month.",
)
async def get_monthly_pnl(
    months: int = Query(default=12, ge=1, le=36, description="Number of months to look back"),
    account_id: str | None = Query(default=None, description="Account ID (defaults to primary)"),
) -> MonthlyPnLResponse:
    """Get monthly aggregated P&L.

    Args:
        months: Number of months to look back.
        account_id: Optional account ID.

    Returns:
        MonthlyPnLResponse with monthly aggregations.
    """
    store = get_store()
    acc_id = account_id or _get_primary_account_id(store)

    today = date.today()
    start_date = today - timedelta(days=months * 30)

    records = store.get_pnl_history(acc_id, start_date=start_date, end_date=today)

    # Group by (year, month)
    monthly: dict[tuple[int, int], dict[str, Any]] = defaultdict(
        lambda: {
            "total_pnl": 0.0,
            "trades_count": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "first_value": None,
            "last_value": None,
        }
    )

    for r in records:
        key = (r.record_date.year, r.record_date.month)
        m = monthly[key]
        m["total_pnl"] += r.total_pnl
        m["trades_count"] += r.trades_count
        m["winning_trades"] += r.winning_trades
        m["losing_trades"] += r.losing_trades
        if m["first_value"] is None:
            m["first_value"] = r.portfolio_value
        m["last_value"] = r.portfolio_value

    entries = []
    for (year, month), data in sorted(monthly.items()):
        total_trades = data["trades_count"]
        win_rate = (data["winning_trades"] / total_trades * 100) if total_trades > 0 else 0.0
        return_pct = 0.0
        if data["first_value"] and data["first_value"] > 0:
            return_pct = round((data["total_pnl"] / data["first_value"]) * 100, 4)

        entries.append(MonthlyPnLEntry(
            year=year,
            month=month,
            month_name=_MONTH_NAMES.get(month, "Unknown"),
            total_pnl=data["total_pnl"],
            return_pct=return_pct,
            trades_count=total_trades,
            winning_trades=data["winning_trades"],
            losing_trades=data["losing_trades"],
            win_rate=round(win_rate, 2),
        ))

    return MonthlyPnLResponse(records=entries, total=len(entries))


@router.get(
    "/by-strategy",
    response_model=StrategyPnLResponse,
    status_code=status.HTTP_200_OK,
    summary="P&L by strategy",
    description="Returns P&L breakdown by strategy.",
)
async def get_pnl_by_strategy(
    days: int = Query(default=30, ge=1, le=365, description="Number of days"),
    account_id: str | None = Query(default=None, description="Account ID (defaults to primary)"),
) -> StrategyPnLResponse:
    """Get P&L breakdown by strategy.

    Groups PnL records by strategy_id and aggregates metrics.

    Args:
        days: Number of days to look back.
        account_id: Optional account ID.

    Returns:
        StrategyPnLResponse with per-strategy breakdown.
    """
    store = get_store()
    acc_id = account_id or _get_primary_account_id(store)

    today = date.today()
    start_date = today - timedelta(days=days)

    records = store.get_pnl_history(acc_id, start_date=start_date, end_date=today)

    # Group by strategy_id
    by_strategy: dict[str | None, dict[str, Any]] = defaultdict(
        lambda: {
            "total_pnl": 0.0,
            "trades_count": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "first_value": None,
        }
    )

    for r in records:
        sid = r.strategy_id
        s = by_strategy[sid]
        s["total_pnl"] += r.total_pnl
        s["trades_count"] += r.trades_count
        s["winning_trades"] += r.winning_trades
        s["losing_trades"] += r.losing_trades
        if s["first_value"] is None:
            s["first_value"] = r.portfolio_value

    # Resolve strategy names
    entries = []
    for strategy_id, data in sorted(by_strategy.items(), key=lambda x: x[1]["total_pnl"], reverse=True):
        strategy_name = "Unassigned"
        sid = strategy_id or "unassigned"

        if strategy_id:
            strategy = store.get_strategy(strategy_id)
            if strategy:
                strategy_name = strategy.name

        total_trades = data["trades_count"]
        win_rate = (data["winning_trades"] / total_trades * 100) if total_trades > 0 else 0.0
        return_pct = 0.0
        if data["first_value"] and data["first_value"] > 0:
            return_pct = round((data["total_pnl"] / data["first_value"]) * 100, 4)

        entries.append(StrategyPnLEntry(
            strategy_id=sid,
            strategy_name=strategy_name,
            total_pnl=data["total_pnl"],
            return_pct=return_pct,
            trades_count=total_trades,
            winning_trades=data["winning_trades"],
            losing_trades=data["losing_trades"],
            win_rate=round(win_rate, 2),
        ))

    return StrategyPnLResponse(strategies=entries, total=len(entries))


@router.get(
    "/by-symbol",
    response_model=SymbolPnLResponse,
    status_code=status.HTTP_200_OK,
    summary="P&L by symbol",
    description="Returns P&L breakdown by trading symbol.",
)
async def get_pnl_by_symbol(
    days: int = Query(default=30, ge=1, le=365, description="Number of days"),
    account_id: str | None = Query(default=None, description="Account ID (defaults to primary)"),
) -> SymbolPnLResponse:
    """Get P&L breakdown by trading symbol.

    Uses trade records to compute per-symbol P&L.

    Args:
        days: Number of days to look back.
        account_id: Optional account ID.

    Returns:
        SymbolPnLResponse with per-symbol breakdown.
    """
    store = get_store()
    acc_id = account_id or _get_primary_account_id(store)

    # Get trades for the period
    trades = store.get_trades_for_account(acc_id)

    # Filter by date range
    today = date.today()
    start_date = today - timedelta(days=days)

    by_symbol: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"total_pnl": 0.0, "trades_count": 0}
    )

    for t in trades:
        trade_date = t.executed_at.date() if hasattr(t.executed_at, "date") else t.executed_at
        if trade_date < start_date:
            continue

        sym = t.symbol
        by_symbol[sym]["trades_count"] += 1  # type: ignore[operator]
        # Approximate P&L from trade value minus commission
        side_val = t.side.value if hasattr(t.side, "value") else str(t.side)
        value = t.quantity * t.price
        if side_val == "sell":
            by_symbol[sym]["total_pnl"] += value - t.commission  # type: ignore[operator]
        else:
            by_symbol[sym]["total_pnl"] -= value + t.commission  # type: ignore[operator]

    entries = []
    for symbol, data in sorted(by_symbol.items(), key=lambda x: x[1]["total_pnl"], reverse=True):
        count = int(data["trades_count"])
        total = float(data["total_pnl"])
        avg = total / count if count > 0 else 0.0
        entries.append(SymbolPnLEntry(
            symbol=symbol,
            total_pnl=round(total, 4),
            trades_count=count,
            avg_pnl_per_trade=round(avg, 4),
        ))

    return SymbolPnLResponse(symbols=entries, total=len(entries))


@router.get(
    "/heatmap",
    response_model=MonthlyHeatmapResponse,
    status_code=status.HTTP_200_OK,
    summary="Monthly heatmap",
    description="Returns monthly return data formatted for heatmap chart rendering.",
)
async def get_monthly_heatmap(
    years: int = Query(default=2, ge=1, le=5, description="Number of years to include"),
    account_id: str | None = Query(default=None, description="Account ID (defaults to primary)"),
) -> MonthlyHeatmapResponse:
    """Get monthly return heatmap data.

    Groups PnL records by (year, month) and computes return percentage
    for each cell. Formatted for direct chart rendering.

    Args:
        years: Number of years to include.
        account_id: Optional account ID.

    Returns:
        MonthlyHeatmapResponse with heatmap cells.
    """
    store = get_store()
    acc_id = account_id or _get_primary_account_id(store)

    today = date.today()
    start_date = today - timedelta(days=years * 365)

    records = store.get_pnl_history(acc_id, start_date=start_date, end_date=today)

    # Group by (year, month)
    monthly: dict[tuple[int, int], dict[str, Any]] = defaultdict(
        lambda: {"total_pnl": 0.0, "trade_count": 0, "first_value": None}
    )

    for r in records:
        key = (r.record_date.year, r.record_date.month)
        m = monthly[key]
        m["total_pnl"] += r.total_pnl
        m["trade_count"] += r.trades_count
        if m["first_value"] is None:
            m["first_value"] = r.portfolio_value

    cells = []
    all_years = set()
    for (year, month), data in sorted(monthly.items()):
        all_years.add(year)
        return_pct = 0.0
        if data["first_value"] and data["first_value"] > 0:
            return_pct = round((data["total_pnl"] / data["first_value"]) * 100, 4)
        cells.append(HeatmapCell(
            year=year,
            month=month,
            return_pct=return_pct,
            trade_count=data["trade_count"],
        ))

    return MonthlyHeatmapResponse(
        cells=cells,
        years=sorted(all_years),
    )
