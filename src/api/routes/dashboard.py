"""Dashboard data API endpoints.

Provides aggregated views of trading system performance for the frontend
dashboard. Uses TTL cache to reduce database load while maintaining
near-real-time data freshness.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-004 - Explicit CORS origins
Decision: DEC-2026-02-08-006 - N+1 prevention (selectinload)
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-01-15-005 - Monolithic architecture (no Redis)
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.cache import TTLCache
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Cache instances with different TTLs per endpoint
_cache = TTLCache()

# Cache TTL constants (seconds)
_SUMMARY_TTL: float = 10.0
_EQUITY_TTL: float = 60.0
_PERFORMANCE_TTL: float = 30.0


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class EquityPoint(BaseModel):
    """Single point on the equity curve."""

    timestamp: str
    equity: float


class DashboardSummaryResponse(BaseModel):
    """Dashboard overview with key metrics."""

    portfolio_value: float
    daily_change: float = 0.0
    daily_change_pct: float = 0.0
    weekly_change: float = 0.0
    weekly_change_pct: float = 0.0
    monthly_change: float = 0.0
    monthly_change_pct: float = 0.0
    open_positions_count: int = 0
    active_strategies_count: int = 0
    trades_today: int = 0
    win_rate_7d: float = 0.0
    max_drawdown_30d: float = 0.0
    risk_status: str = "normal"
    current_drawdown_pct: float = 0.0
    daily_loss_used_pct: float = 0.0
    current_regime: str = "unknown"
    equity_sparkline: list[float] = Field(default_factory=list)
    timestamp: str


class EquityCurveResponse(BaseModel):
    """Equity curve data for charting."""

    data: list[EquityPoint]
    time_range: str
    total_return_pct: float = 0.0
    data_points: int = 0


class PerformanceMetricsResponse(BaseModel):
    """Detailed performance metrics."""

    win_rate: float = 0.0
    total_return: float = 0.0
    total_return_pct: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    profit_factor: float = 0.0
    period_days: int = 30


class DashboardPositionEntry(BaseModel):
    """Position entry for dashboard display."""

    id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    duration_hours: float = 0.0
    strategy_name: str | None = None


class DashboardPositionListResponse(BaseModel):
    """List of dashboard positions."""

    positions: list[DashboardPositionEntry]
    total: int


class TradeEntry(BaseModel):
    """Recent trade entry."""

    id: str
    symbol: str
    side: str
    quantity: float
    price: float
    commission: float = 0.0
    executed_at: str
    order_id: str


class TradeListResponse(BaseModel):
    """List of recent trades."""

    trades: list[TradeEntry]
    total: int


class AlertEntry(BaseModel):
    """Alert entry from audit logs."""

    id: str
    timestamp: str
    action: str
    actor: str
    details: dict[str, Any] = Field(default_factory=dict)


class AlertListResponse(BaseModel):
    """List of recent alerts."""

    alerts: list[AlertEntry]
    total: int


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
            detail="DataStore not initialized. Call init_dashboard_routes() first.",
        )
    return _store


def init_dashboard_routes(store: Any) -> None:
    """Initialize the dashboard routes with a DataStore instance.

    Args:
        store: Configured DataStore instance.
    """
    global _store  # noqa: PLW0603
    _store = store
    logger.info("dashboard_routes_initialized")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _safe_pct(numerator: float, denominator: float) -> float:
    """Calculate percentage safely, returning 0 if denominator is zero.

    Args:
        numerator: Numerator value.
        denominator: Denominator value.

    Returns:
        Percentage value or 0.0 if denominator is zero/NaN/Inf.
    """
    if denominator == 0 or math.isnan(denominator) or math.isinf(denominator):
        return 0.0
    result = (numerator / denominator) * 100
    if math.isnan(result) or math.isinf(result):
        return 0.0
    return round(result, 4)


def _get_time_range_start(time_range: str) -> datetime:
    """Convert time range string to start datetime.

    Args:
        time_range: One of 1W, 1M, 3M, 6M, 1Y, ALL.

    Returns:
        Start datetime for the range.

    Raises:
        ValueError: If time_range is invalid.
    """
    now = datetime.now(timezone.utc)
    ranges = {
        "1W": timedelta(weeks=1),
        "1M": timedelta(days=30),
        "3M": timedelta(days=90),
        "6M": timedelta(days=180),
        "1Y": timedelta(days=365),
    }
    if time_range == "ALL":
        return datetime(2020, 1, 1, tzinfo=timezone.utc)
    delta = ranges.get(time_range)
    if delta is None:
        raise ValueError(f"Invalid time_range: {time_range}")
    return now - delta


# ---------------------------------------------------------------------------
# Risk metric helpers
# ---------------------------------------------------------------------------


def _compute_daily_loss_used_pct(
    daily_pnl: float,
    equity: float,
    account: Any,
) -> float:
    """Compute how much of the configured daily loss limit has been consumed.

    Per PRD §4.4, this is expressed as a fraction of the account's configured
    daily_loss_limit_pct, NOT as a fraction of total equity.

    Formula: abs(daily_loss) / (equity * daily_limit_pct / 100) * 100

    Args:
        daily_pnl: Today's realized P&L (negative when losing).
        equity: Current account equity in USDT.
        account: Account ORM object with risk_config dict.

    Returns:
        Percentage of configured daily loss limit consumed (0–100+).
        Returns 0.0 if no loss today or limit configuration is missing.
    """
    if daily_pnl >= 0:
        return 0.0

    risk_config: dict[str, Any] = {}
    if hasattr(account, "risk_config") and isinstance(account.risk_config, dict):
        risk_config = account.risk_config

    daily_limit_pct: float = float(risk_config.get("daily_loss_limit_pct", 0.0))
    if daily_limit_pct <= 0:
        return 0.0

    daily_loss_limit_usdt = equity * daily_limit_pct / 100.0
    return _safe_pct(abs(daily_pnl), daily_loss_limit_usdt)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Dashboard summary",
    description="Aggregated dashboard overview with key metrics. Cached for 10s.",
)
async def get_dashboard_summary() -> DashboardSummaryResponse:
    """Get dashboard summary with key metrics.

    Returns cached response if available (10s TTL).

    Returns:
        DashboardSummaryResponse with portfolio overview.
    """
    cached = _cache.get("dashboard_summary")
    if cached is not None:
        # TTLCache is intentionally heterogeneous, so get() is Any.
        # The key determines the type.
        return cast(DashboardSummaryResponse, cached)

    store = get_store()
    now = datetime.now(timezone.utc)

    # Get primary account
    accounts = store.get_active_accounts()
    if not accounts:
        empty = DashboardSummaryResponse(
            portfolio_value=0.0,
            timestamp=now.isoformat(),
        )
        _cache.set("dashboard_summary", empty, _SUMMARY_TTL)
        return empty

    account = accounts[0]
    portfolio_value = account.equity_usdt

    # Open positions
    open_positions = store.get_open_positions()

    # Active strategies
    active_strategies = store.get_active_strategies()

    # P&L data for different periods
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    daily_pnl = store.get_pnl_history(account.id, start_date=today, end_date=today)
    weekly_pnl = store.get_pnl_history(account.id, start_date=week_ago, end_date=today)
    monthly_pnl = store.get_pnl_history(account.id, start_date=month_ago, end_date=today)

    daily_change = sum(r.total_pnl for r in daily_pnl)
    weekly_change = sum(r.total_pnl for r in weekly_pnl)
    monthly_change = sum(r.total_pnl for r in monthly_pnl)

    # Win rate (7 days)
    weekly_trades = sum(r.trades_count for r in weekly_pnl)
    weekly_wins = sum(r.winning_trades for r in weekly_pnl)
    win_rate_7d = _safe_pct(weekly_wins, weekly_trades) if weekly_trades > 0 else 0.0

    # Trades today
    trades_today = sum(r.trades_count for r in daily_pnl)

    # Max drawdown (30 days)
    max_drawdown_30d = 0.0
    if monthly_pnl:
        drawdowns = [r.drawdown_pct for r in monthly_pnl if r.drawdown_pct is not None]
        if drawdowns:
            max_drawdown_30d = min(drawdowns)  # Most negative

    # Current drawdown
    current_drawdown_pct = 0.0
    if monthly_pnl:
        latest = monthly_pnl[-1]
        if latest.drawdown_pct is not None:
            current_drawdown_pct = latest.drawdown_pct

    # Risk status based on drawdown
    risk_status = "normal"
    if abs(current_drawdown_pct) > 5.0:
        risk_status = "warning"
    if abs(current_drawdown_pct) > 10.0:
        risk_status = "critical"

    # System state for kill switch info
    system_state = store.get_system_state()
    if system_state.kill_switch_active:
        risk_status = "halted"

    # Equity sparkline (last 7 daily values)
    sparkline_records = store.get_pnl_history(
        account.id, start_date=week_ago, end_date=today,
    )
    equity_sparkline = [r.portfolio_value for r in sparkline_records]

    # Previous portfolio value for percentage calculations
    prev_daily = portfolio_value - daily_change
    prev_weekly = portfolio_value - weekly_change
    prev_monthly = portfolio_value - monthly_change

    response = DashboardSummaryResponse(
        portfolio_value=portfolio_value,
        daily_change=daily_change,
        daily_change_pct=_safe_pct(daily_change, prev_daily),
        weekly_change=weekly_change,
        weekly_change_pct=_safe_pct(weekly_change, prev_weekly),
        monthly_change=monthly_change,
        monthly_change_pct=_safe_pct(monthly_change, prev_monthly),
        open_positions_count=len(open_positions),
        active_strategies_count=len(active_strategies),
        trades_today=trades_today,
        win_rate_7d=win_rate_7d,
        max_drawdown_30d=max_drawdown_30d,
        risk_status=risk_status,
        current_drawdown_pct=current_drawdown_pct,
        # PRD §4.4: fraction of configured daily loss limit consumed, not fraction of equity.
        # Formula: abs(daily_loss) / (equity * daily_limit_pct / 100) * 100
        daily_loss_used_pct=_compute_daily_loss_used_pct(daily_change, portfolio_value, account),
        current_regime=account.regime or "unknown",
        equity_sparkline=equity_sparkline,
        timestamp=now.isoformat(),
    )

    _cache.set("dashboard_summary", response, _SUMMARY_TTL)
    return response


@router.get(
    "/equity",
    response_model=EquityCurveResponse,
    status_code=status.HTTP_200_OK,
    summary="Equity curve data",
    description="Returns equity curve data points for charting. Cached for 60s per time range.",
)
async def get_equity_curve(
    time_range: str = Query(
        default="1M",
        description="Time range: 1W, 1M, 3M, 6M, 1Y, ALL",
    ),
) -> EquityCurveResponse:
    """Get equity curve data for charting.

    Args:
        time_range: Time range for the equity curve.

    Returns:
        EquityCurveResponse with data points.
    """
    valid_ranges = {"1W", "1M", "3M", "6M", "1Y", "ALL"}
    if time_range not in valid_ranges:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range: {time_range}. Valid: {sorted(valid_ranges)}",
        )

    cache_key = f"equity:{time_range}"
    cached = _cache.get(cache_key)
    if cached is not None:
        # TTLCache is intentionally heterogeneous, so get() is Any.
        # The key determines the type.
        return cast(EquityCurveResponse, cached)

    store = get_store()
    accounts = store.get_active_accounts()

    if not accounts:
        empty = EquityCurveResponse(data=[], time_range=time_range, data_points=0)
        _cache.set(cache_key, empty, _EQUITY_TTL)
        return empty

    start_time = _get_time_range_start(time_range)
    snapshots = store.get_equity_snapshots(accounts[0].id, start_time=start_time)

    data = [
        EquityPoint(
            timestamp=snap.timestamp.isoformat() if hasattr(snap.timestamp, "isoformat") else str(snap.timestamp),
            equity=snap.equity,
        )
        for snap in snapshots
    ]

    # Calculate total return
    total_return_pct = 0.0
    if len(data) >= 2:
        first_equity = data[0].equity
        last_equity = data[-1].equity
        total_return_pct = _safe_pct(last_equity - first_equity, first_equity)

    response = EquityCurveResponse(
        data=data,
        time_range=time_range,
        total_return_pct=total_return_pct,
        data_points=len(data),
    )

    _cache.set(cache_key, response, _EQUITY_TTL)
    return response


@router.get(
    "/performance",
    response_model=PerformanceMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Performance metrics",
    description="Detailed performance metrics for the last 30 days. Cached for 30s.",
)
async def get_performance_metrics() -> PerformanceMetricsResponse:
    """Get detailed performance metrics.

    Returns:
        PerformanceMetricsResponse with 30-day metrics.
    """
    cached = _cache.get("performance")
    if cached is not None:
        # TTLCache is intentionally heterogeneous, so get() is Any.
        # The key determines the type.
        return cast(PerformanceMetricsResponse, cached)

    store = get_store()
    accounts = store.get_active_accounts()

    if not accounts:
        empty = PerformanceMetricsResponse()
        _cache.set("performance", empty, _PERFORMANCE_TTL)
        return empty

    today = date.today()
    month_ago = today - timedelta(days=30)
    records = store.get_pnl_history(accounts[0].id, start_date=month_ago, end_date=today)

    if not records:
        empty = PerformanceMetricsResponse()
        _cache.set("performance", empty, _PERFORMANCE_TTL)
        return empty

    total_trades = sum(r.trades_count for r in records)
    winning_trades = sum(r.winning_trades for r in records)
    losing_trades = sum(r.losing_trades for r in records)
    total_return = sum(r.total_pnl for r in records)

    # Win rate
    win_rate = _safe_pct(winning_trades, total_trades) if total_trades > 0 else 0.0

    # Max drawdown
    drawdowns = [r.drawdown_pct for r in records if r.drawdown_pct is not None]
    max_drawdown_pct = min(drawdowns) if drawdowns else 0.0

    # Total return percentage
    first_value = records[0].portfolio_value if records else 0.0
    total_return_pct = _safe_pct(total_return, first_value)

    # Average win/loss percentages from daily returns
    positive_returns = [r.daily_return_pct for r in records if r.daily_return_pct and r.daily_return_pct > 0]
    negative_returns = [r.daily_return_pct for r in records if r.daily_return_pct and r.daily_return_pct < 0]
    avg_win_pct = sum(positive_returns) / len(positive_returns) if positive_returns else 0.0
    avg_loss_pct = sum(negative_returns) / len(negative_returns) if negative_returns else 0.0

    # Profit factor: sum of profits / abs(sum of losses)
    total_profit = sum(r.total_pnl for r in records if r.total_pnl > 0)
    total_loss = abs(sum(r.total_pnl for r in records if r.total_pnl < 0))
    profit_factor = round(total_profit / total_loss, 4) if total_loss > 0 else 0.0

    response = PerformanceMetricsResponse(
        win_rate=win_rate,
        total_return=total_return,
        total_return_pct=total_return_pct,
        max_drawdown=max_drawdown_pct * first_value / 100 if first_value else 0.0,
        max_drawdown_pct=max_drawdown_pct,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        avg_win_pct=round(avg_win_pct, 4),
        avg_loss_pct=round(avg_loss_pct, 4),
        profit_factor=profit_factor,
        period_days=30,
    )

    _cache.set("performance", response, _PERFORMANCE_TTL)
    return response


@router.get(
    "/recent-trades",
    response_model=TradeListResponse,
    status_code=status.HTTP_200_OK,
    summary="Recent trades",
    description="Returns recent trade executions. NOT cached (real-time critical).",
)
async def get_recent_trades(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum trades to return"),
) -> TradeListResponse:
    """Get recent trades for the primary account.

    Args:
        limit: Maximum number of trades to return.

    Returns:
        TradeListResponse with recent trades.
    """
    store = get_store()
    accounts = store.get_active_accounts()

    if not accounts:
        return TradeListResponse(trades=[], total=0)

    all_trades = store.get_trades_for_account(accounts[0].id)
    trades = all_trades[:limit]

    entries = [
        TradeEntry(
            id=t.id,
            symbol=t.symbol,
            side=t.side.value if hasattr(t.side, "value") else str(t.side),
            quantity=t.quantity,
            price=t.price,
            commission=t.commission,
            executed_at=t.executed_at.isoformat() if hasattr(t.executed_at, "isoformat") else str(t.executed_at),
            order_id=t.order_id,
        )
        for t in trades
    ]

    return TradeListResponse(trades=entries, total=len(entries))


@router.get(
    "/alerts",
    response_model=AlertListResponse,
    status_code=status.HTTP_200_OK,
    summary="Recent alerts",
    description="Returns recent system alerts from audit logs. NOT cached.",
)
async def get_recent_alerts(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum alerts to return"),
) -> AlertListResponse:
    """Get recent alerts from audit logs.

    Filters for alert-related actions: kill_switch, circuit_breaker,
    risk_breach, system_error, etc.

    Args:
        limit: Maximum number of alerts to return.

    Returns:
        AlertListResponse with recent alerts.
    """
    store = get_store()

    # Get all recent audit logs (alerts are stored as audit log entries)
    logs = store.get_audit_logs(limit=limit)

    # Filter for alert-relevant actions
    alert_actions = {
        "kill_switch_activated", "kill_switch_deactivated",
        "circuit_breaker_triggered", "circuit_breaker_reset",
        "risk_breach", "risk_warning",
        "system_error", "system_started", "system_stopped",
        "alert_sent", "alert_escalated",
    }

    entries = [
        AlertEntry(
            id=log.id,
            timestamp=log.timestamp.isoformat() if hasattr(log.timestamp, "isoformat") else str(log.timestamp),
            action=log.action,
            actor=log.actor,
            details=log.details or {},
        )
        for log in logs
        if log.action in alert_actions
    ]

    return AlertListResponse(alerts=entries, total=len(entries))


@router.get(
    "/positions",
    response_model=DashboardPositionListResponse,
    status_code=status.HTTP_200_OK,
    summary="Dashboard positions",
    description="Returns open positions with P&L for dashboard display. NOT cached.",
)
async def get_dashboard_positions() -> DashboardPositionListResponse:
    """Get open positions formatted for dashboard display.

    Returns:
        DashboardPositionListResponse with position data.
    """
    store = get_store()
    positions = store.get_open_positions()
    now = datetime.now(timezone.utc)

    entries: list[DashboardPositionEntry] = []
    for pos in positions:
        # Calculate unrealized P&L
        side_val = pos.side.value if hasattr(pos.side, "value") else str(pos.side)
        if side_val == "long":
            unrealized_pnl = (pos.current_price - pos.entry_price) * pos.size
        else:
            unrealized_pnl = (pos.entry_price - pos.current_price) * pos.size

        unrealized_pnl_pct = _safe_pct(
            unrealized_pnl, pos.entry_price * pos.size,
        )

        # Duration
        opened_at = pos.opened_at
        if hasattr(opened_at, "tzinfo") and opened_at.tzinfo is None:
            opened_at = opened_at.replace(tzinfo=timezone.utc)
        duration_hours = (now - opened_at).total_seconds() / 3600.0

        # Strategy name from relationship
        strategy_name = None
        if pos.strategy_id:
            strategy = store.get_strategy(pos.strategy_id)
            if strategy:
                strategy_name = strategy.name

        entries.append(DashboardPositionEntry(
            id=pos.id,
            symbol=pos.symbol,
            side=side_val,
            quantity=pos.size,
            entry_price=pos.entry_price,
            current_price=pos.current_price,
            unrealized_pnl=round(unrealized_pnl, 4),
            unrealized_pnl_pct=unrealized_pnl_pct,
            duration_hours=round(duration_hours, 2),
            strategy_name=strategy_name,
        ))

    return DashboardPositionListResponse(
        positions=entries,
        total=len(entries),
    )
