"""System control API endpoints.

Provides endpoints for system status, start/stop, and regime management.
Supports graceful degradation when orchestrator is not yet initialized.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-004 - Explicit CORS origins
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-01-15-005 - Monolithic architecture
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class SystemStatusResponse(BaseModel):
    """System status overview."""

    status: str
    mode: str
    uptime_seconds: float
    active_strategies: int = 0
    open_positions: int = 0
    daily_pnl: float = 0.0
    kill_switch_active: bool = False
    trading_enabled: bool = True
    health_status: str = "unknown"
    circuit_breakers: dict[str, Any] = Field(default_factory=dict)
    last_trade_at: str | None = None
    started_at: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class ActionResponse(BaseModel):
    """Response for start/stop actions."""

    status: str
    message: str
    timestamp: str


class RegimeResponse(BaseModel):
    """Current market regime."""

    regime: str
    account_id: str
    updated_at: str


class SetRegimeRequest(BaseModel):
    """Request to change the market regime."""

    regime: str = Field(
        ...,
        description="Market regime: trending_up, trending_down, ranging, volatile, unknown",
    )
    operator: str = Field(
        default="api_user",
        description="Who is making the change",
    )
    note: str | None = Field(
        default=None,
        description="Optional note explaining the regime change",
    )


class RegimeHistoryEntry(BaseModel):
    """A single regime change record."""

    timestamp: str
    action: str
    actor: str
    details: dict[str, Any] = Field(default_factory=dict)


class RegimeHistoryResponse(BaseModel):
    """Regime change history."""

    history: list[RegimeHistoryEntry]
    total: int


# ---------------------------------------------------------------------------
# Valid regimes (per MVP spec: manual regime tagging)
# ---------------------------------------------------------------------------

_VALID_REGIMES: frozenset[str] = frozenset({
    "trending_up",
    "trending_down",
    "ranging",
    "volatile",
    "unknown",
})


# ---------------------------------------------------------------------------
# Module-level dependency injection
# ---------------------------------------------------------------------------

_orchestrator: Any | None = None
_store: Any | None = None
_event_bus: Any | None = None


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
            detail="DataStore not initialized. Call init_system_routes() first.",
        )
    return _store


def init_system_routes(
    store: Any,
    orchestrator: Any | None = None,
    event_bus: Any | None = None,
) -> None:
    """Initialize the system routes with dependencies.

    Args:
        store: DataStore instance (required).
        orchestrator: Orchestrator instance (optional, may start later).
        event_bus: EventBus instance (optional, for real-time events).
    """
    global _orchestrator, _store, _event_bus  # noqa: PLW0603
    _store = store
    _orchestrator = orchestrator
    _event_bus = event_bus
    logger.info("system_routes_initialized")


def set_orchestrator(orchestrator: Any) -> None:
    """Set orchestrator after delayed initialization.

    Args:
        orchestrator: Orchestrator instance.
    """
    global _orchestrator  # noqa: PLW0603
    _orchestrator = orchestrator
    logger.info("system_routes_orchestrator_set")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/status",
    response_model=SystemStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get system status",
    description="Returns comprehensive system status including metrics and health.",
)
async def get_system_status() -> SystemStatusResponse:
    """Get current system status.

    Returns data from orchestrator if available, otherwise falls back
    to DataStore for basic state information.

    Returns:
        SystemStatusResponse with current system state.
    """
    store = get_store()
    now = datetime.now(timezone.utc)

    # Get system state from database (always available)
    system_state = store.get_system_state()

    # Get counts from database
    open_positions = store.get_open_positions()
    active_strategies = store.get_active_strategies()

    # Base response from DataStore
    response_data: dict[str, Any] = {
        "kill_switch_active": system_state.kill_switch_active,
        "trading_enabled": system_state.trading_enabled,
        "health_status": system_state.health_status,
        "circuit_breakers": system_state.circuit_breakers or {},
        "open_positions": len(open_positions),
        "active_strategies": len(active_strategies),
        "timestamp": now.isoformat(),
    }

    # Last trade timestamp
    if system_state.last_trade_at:
        response_data["last_trade_at"] = system_state.last_trade_at.isoformat()
    else:
        response_data["last_trade_at"] = None

    # Started at
    if system_state.started_at:
        response_data["started_at"] = system_state.started_at.isoformat()
    else:
        response_data["started_at"] = None

    # Enrich with orchestrator data if available
    if _orchestrator is not None:
        orch_status = _orchestrator.get_status()
        response_data["status"] = orch_status["status"]
        response_data["uptime_seconds"] = orch_status["uptime_seconds"]
        response_data["metrics"] = orch_status.get("metrics", {})
        response_data["mode"] = "live" if orch_status.get("running") else "stopped"
    else:
        response_data["status"] = "stopped"
        response_data["uptime_seconds"] = 0.0
        response_data["metrics"] = {}
        response_data["mode"] = "initializing"

    # Daily P&L from today's records
    from datetime import date as date_type
    accounts = store.get_active_accounts()
    daily_pnl = 0.0
    if accounts:
        today = date_type.today()
        pnl_records = store.get_pnl_history(
            account_id=accounts[0].id,
            start_date=today,
            end_date=today,
        )
        if pnl_records:
            daily_pnl = sum(r.total_pnl for r in pnl_records)
    response_data["daily_pnl"] = daily_pnl

    return SystemStatusResponse(**response_data)


@router.post(
    "/start",
    response_model=ActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Start the trading system",
    description="Starts the orchestrator and begins the main trading loop.",
)
async def start_system() -> ActionResponse:
    """Start the trading system.

    Requires orchestrator to be initialized.

    Returns:
        ActionResponse with result.

    Raises:
        HTTPException: 503 if orchestrator not initialized, 409 if already running.
    """
    if _orchestrator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator not initialized. System cannot be started via API yet.",
        )

    orch_status = _orchestrator.get_status()
    if orch_status["running"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="System is already running.",
        )

    try:
        # Start is async - fire and forget (runs in background)
        import asyncio
        asyncio.create_task(_orchestrator.start())

        store = get_store()
        store.add_audit_log(
            action="system_started",
            actor="api",
            details={"trigger": "manual_api_start"},
        )

        if _event_bus is not None:
            await _event_bus.publish("system_status_changed", {
                "status": "starting",
                "trigger": "api",
            })

        return ActionResponse(
            status="starting",
            message="System start initiated. Check /status for progress.",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error("system_start_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start system: {str(e)}",
        )


@router.post(
    "/stop",
    response_model=ActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Stop the trading system",
    description="Gracefully stops the orchestrator and cancels pending orders.",
)
async def stop_system() -> ActionResponse:
    """Stop the trading system gracefully.

    Returns:
        ActionResponse with result.

    Raises:
        HTTPException: 503 if orchestrator not initialized, 409 if not running.
    """
    if _orchestrator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator not initialized.",
        )

    orch_status = _orchestrator.get_status()
    if not orch_status["running"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="System is not running.",
        )

    try:
        await _orchestrator.stop()

        store = get_store()
        store.add_audit_log(
            action="system_stopped",
            actor="api",
            details={"trigger": "manual_api_stop"},
        )

        if _event_bus is not None:
            await _event_bus.publish("system_status_changed", {
                "status": "stopped",
                "trigger": "api",
            })

        return ActionResponse(
            status="stopped",
            message="System stopped gracefully.",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error("system_stop_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop system: {str(e)}",
        )


@router.get(
    "/regime",
    response_model=RegimeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current market regime",
    description="Returns the current manually-set market regime for the primary account.",
)
async def get_regime() -> RegimeResponse:
    """Get current market regime.

    Returns the regime for the primary (first active) account.

    Returns:
        RegimeResponse with current regime.
    """
    store = get_store()
    accounts = store.get_active_accounts()

    if not accounts:
        return RegimeResponse(
            regime="unknown",
            account_id="none",
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    account = accounts[0]
    updated_at = account.updated_at.isoformat() if hasattr(account, "updated_at") and account.updated_at else datetime.now(timezone.utc).isoformat()

    return RegimeResponse(
        regime=account.regime or "unknown",
        account_id=account.id,
        updated_at=updated_at,
    )


@router.put(
    "/regime",
    response_model=RegimeResponse,
    status_code=status.HTTP_200_OK,
    summary="Set market regime",
    description="Manually set the market regime for the primary account.",
)
async def set_regime(request: SetRegimeRequest) -> RegimeResponse:
    """Set the market regime.

    Validates the regime value, updates the primary account, and logs
    the change to the audit trail.

    Args:
        request: SetRegimeRequest with new regime and metadata.

    Returns:
        RegimeResponse with updated regime.

    Raises:
        HTTPException: 400 if invalid regime, 404 if no active account.
    """
    if request.regime not in _VALID_REGIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid regime: {request.regime}. "
                f"Valid regimes: {sorted(_VALID_REGIMES)}"
            ),
        )

    store = get_store()
    accounts = store.get_active_accounts()

    if not accounts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active account found. Create an account first.",
        )

    account = accounts[0]
    old_regime = account.regime

    # Update account regime via DataStore session
    with store.session() as session:
        from src.data.models import Account
        db_account = session.get(Account, account.id)
        if db_account is not None:
            db_account.regime = request.regime
            # session auto-commits via context manager

    # Audit log
    store.add_audit_log(
        action="regime_changed",
        actor=request.operator,
        details={
            "account_id": account.id,
            "old_regime": old_regime,
            "new_regime": request.regime,
            "note": request.note,
        },
    )

    logger.info(
        "regime_changed",
        account_id=account.id,
        old_regime=old_regime,
        new_regime=request.regime,
        operator=request.operator,
    )

    # Publish event for SSE
    if _event_bus is not None:
        await _event_bus.publish("regime_changed", {
            "account_id": account.id,
            "old_regime": old_regime,
            "new_regime": request.regime,
            "operator": request.operator,
        })

    return RegimeResponse(
        regime=request.regime,
        account_id=account.id,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/health/strategies",
    status_code=status.HTTP_200_OK,
    summary="Get per-strategy health",
    description="Returns health status for every active strategy (PRD §2.2.2).",
)
async def get_health_strategies() -> dict[str, Any]:
    """Return per-strategy health metrics.

    Reads active strategies from DataStore and enriches with
    monitoring state from the orchestrator when available.

    Returns:
        Dict with ``strategies`` list and ``total`` count.
        Each strategy entry contains:
        - strategy_id
        - status
        - last_evaluation_time
        - consecutive_errors
        - current_drawdown
    """
    store = get_store()
    active_strategies = store.get_active_strategies()

    # Pull monitoring state from orchestrator if available
    monitoring_state: dict[str, Any] = {}
    if _orchestrator is not None and hasattr(_orchestrator, "get_monitoring_state"):
        try:
            monitoring_state = _orchestrator.get_monitoring_state() or {}
        except Exception:
            pass  # Orchestrator may not have state yet; degrade gracefully

    strategy_health: list[dict[str, Any]] = []
    for strat in active_strategies:
        strat_id = strat.id
        mon = monitoring_state.get(strat_id, {})

        last_eval = mon.get("last_evaluation_time")
        if hasattr(last_eval, "isoformat"):
            last_eval = last_eval.isoformat()

        strategy_health.append({
            "strategy_id": strat_id,
            "status": strat.status.value if hasattr(strat.status, "value") else str(strat.status),
            "last_evaluation_time": last_eval,
            "consecutive_errors": mon.get("consecutive_errors", 0),
            "current_drawdown": mon.get("current_drawdown", 0.0),
        })

    logger.info(
        "health_strategies_queried",
        strategy_count=len(strategy_health),
    )

    return {
        "strategies": strategy_health,
        "total": len(strategy_health),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/regime/history",
    response_model=RegimeHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get regime change history",
    description="Returns the history of regime changes from the audit log.",
)
async def get_regime_history(
    limit: int = Query(default=50, ge=1, le=500, description="Maximum entries to return"),
) -> RegimeHistoryResponse:
    """Get regime change history from audit logs.

    Args:
        limit: Maximum number of entries to return.

    Returns:
        RegimeHistoryResponse with change history.
    """
    store = get_store()
    logs = store.get_audit_logs(action="regime_changed", limit=limit)

    entries = [
        RegimeHistoryEntry(
            timestamp=log.timestamp.isoformat() if hasattr(log.timestamp, "isoformat") else str(log.timestamp),
            action=log.action,
            actor=log.actor,
            details=log.details or {},
        )
        for log in logs
    ]

    return RegimeHistoryResponse(
        history=entries,
        total=len(entries),
    )
