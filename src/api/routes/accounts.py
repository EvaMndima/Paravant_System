"""Account management API endpoints.

Provides CRUD operations for trading accounts, balance queries,
and per-account P&L history.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-004 - Explicit CORS origins
Decision: DEC-2026-02-08-007 - Input validation at boundaries
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.data.models.account import AccountStatus, RiskProfile
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class CreateAccountRequest(BaseModel):
    """Request to create a new trading account."""

    name: str = Field(..., min_length=1, max_length=100, description="Account name")
    broker: str = Field(default="binance", description="Broker name (binance only for MVP)")
    profile: str = Field(default="balanced", description="Risk profile: conservative, balanced, aggressive")
    initial_balance: float = Field(default=0.0, ge=0, description="Initial balance in USDT")


class UpdateAccountRequest(BaseModel):
    """Request to update an existing account."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    profile: str | None = Field(default=None, description="Risk profile")
    regime: str | None = Field(default=None, description="Market regime")
    risk_config: dict[str, Any] | None = Field(default=None, description="Risk configuration overrides")


class AccountResponse(BaseModel):
    """Account details response."""

    id: str
    name: str
    broker: str
    profile: str
    status: str
    balance_usdt: float
    equity_usdt: float
    regime: str
    risk_config: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class AccountListResponse(BaseModel):
    """List of accounts."""

    accounts: list[AccountResponse]
    total: int


class AccountDetailResponse(AccountResponse):
    """Account with additional detail (positions, strategies)."""

    open_positions_count: int = 0
    active_strategies_count: int = 0


class BalanceResponse(BaseModel):
    """Account balance breakdown."""

    account_id: str
    balance_usdt: float
    equity_usdt: float
    available_margin: float
    open_positions_value: float = 0.0
    timestamp: str


class PnLSummary(BaseModel):
    """P&L summary for a period."""

    total_pnl: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    best_day: float = 0.0
    worst_day: float = 0.0


class PnLEntry(BaseModel):
    """Single P&L record."""

    date: str
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    portfolio_value: float
    daily_return_pct: float | None = None
    trades_count: int = 0


class AccountPnLResponse(BaseModel):
    """Account P&L history with summary."""

    account_id: str
    records: list[PnLEntry]
    summary: PnLSummary
    period_start: str
    period_end: str


# ---------------------------------------------------------------------------
# Valid values
# ---------------------------------------------------------------------------

_VALID_PROFILES: frozenset[str] = frozenset({p.value for p in RiskProfile})
_VALID_REGIMES: frozenset[str] = frozenset({
    "trending_up", "trending_down", "ranging", "volatile", "unknown",
})


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
            detail="DataStore not initialized. Call init_account_routes() first.",
        )
    return _store


def init_account_routes(store: Any) -> None:
    """Initialize the account routes with a DataStore instance.

    Args:
        store: Configured DataStore instance.
    """
    global _store  # noqa: PLW0603
    _store = store
    logger.info("account_routes_initialized")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _account_to_response(account: Any) -> AccountResponse:
    """Convert Account model to API response.

    Args:
        account: Account model instance.

    Returns:
        AccountResponse with all fields populated.
    """
    profile_val = account.profile.value if hasattr(account.profile, "value") else str(account.profile)
    status_val = account.status.value if hasattr(account.status, "value") else str(account.status)
    created_at = account.created_at.isoformat() if hasattr(account, "created_at") and account.created_at else None
    updated_at = account.updated_at.isoformat() if hasattr(account, "updated_at") and account.updated_at else None

    return AccountResponse(
        id=account.id,
        name=account.name,
        broker=account.broker,
        profile=profile_val,
        status=status_val,
        balance_usdt=account.balance_usdt,
        equity_usdt=account.equity_usdt,
        regime=account.regime or "unknown",
        risk_config=account.risk_config or {},
        created_at=created_at,
        updated_at=updated_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create account",
    description="Create a new trading account.",
)
async def create_account(request: CreateAccountRequest) -> AccountResponse:
    """Create a new trading account.

    Args:
        request: CreateAccountRequest with account details.

    Returns:
        AccountResponse with created account.

    Raises:
        HTTPException: 400 if invalid profile.
    """
    if request.profile not in _VALID_PROFILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid profile: {request.profile}. Valid: {sorted(_VALID_PROFILES)}",
        )

    store = get_store()

    from src.data.models.account import Account

    account = Account(
        name=request.name,
        broker=request.broker,
        profile=RiskProfile(request.profile),
        balance_usdt=request.initial_balance,
        equity_usdt=request.initial_balance,
    )

    store.save_account(account)

    logger.info(
        "account_created",
        account_id=account.id,
        name=account.name,
        profile=request.profile,
        initial_balance=request.initial_balance,
    )

    store.add_audit_log(
        action="account_created",
        actor="api",
        details={
            "account_id": account.id,
            "name": account.name,
            "broker": request.broker,
            "profile": request.profile,
        },
    )

    return _account_to_response(account)


@router.get(
    "",
    response_model=AccountListResponse,
    status_code=status.HTTP_200_OK,
    summary="List accounts",
    description="Returns all trading accounts.",
)
async def list_accounts() -> AccountListResponse:
    """List all trading accounts.

    Returns:
        AccountListResponse with all accounts.
    """
    store = get_store()
    accounts = store.get_all_accounts()

    return AccountListResponse(
        accounts=[_account_to_response(a) for a in accounts],
        total=len(accounts),
    )


@router.get(
    "/{account_id}",
    response_model=AccountDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get account details",
    description="Returns detailed account information including position and strategy counts.",
)
async def get_account(account_id: str) -> AccountDetailResponse:
    """Get account by ID with additional details.

    Args:
        account_id: Account ID.

    Returns:
        AccountDetailResponse with full details.

    Raises:
        HTTPException: 404 if account not found.
    """
    store = get_store()
    account = store.get_account(account_id)

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account not found: {account_id}",
        )

    # Count positions and strategies
    positions = store.get_positions_for_account(account_id)
    from src.data.models.position import PositionStatus
    open_positions = [p for p in positions if p.status == PositionStatus.OPEN]

    assignments = store.get_assignments_for_account(account_id)
    active_assignments = [a for a in assignments if a.is_active]

    base = _account_to_response(account)
    return AccountDetailResponse(
        **base.model_dump(),
        open_positions_count=len(open_positions),
        active_strategies_count=len(active_assignments),
    )


@router.put(
    "/{account_id}",
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Update account",
    description="Update account name, profile, regime, or risk configuration.",
)
async def update_account(
    account_id: str,
    request: UpdateAccountRequest,
) -> AccountResponse:
    """Update an existing account.

    Only non-None fields in the request are updated.

    Args:
        account_id: Account ID to update.
        request: UpdateAccountRequest with fields to change.

    Returns:
        AccountResponse with updated account.

    Raises:
        HTTPException: 404 if not found, 400 if invalid values.
    """
    store = get_store()
    account = store.get_account(account_id)

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account not found: {account_id}",
        )

    # Validate profile if provided
    if request.profile is not None and request.profile not in _VALID_PROFILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid profile: {request.profile}. Valid: {sorted(_VALID_PROFILES)}",
        )

    # Validate regime if provided
    if request.regime is not None and request.regime not in _VALID_REGIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid regime: {request.regime}. Valid: {sorted(_VALID_REGIMES)}",
        )

    # Update via session
    with store.session() as session:
        from src.data.models.account import Account
        db_account = session.get(Account, account_id)
        if db_account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {account_id}",
            )
        if request.name is not None:
            db_account.name = request.name
        if request.profile is not None:
            db_account.profile = RiskProfile(request.profile)
        if request.regime is not None:
            db_account.regime = request.regime
        if request.risk_config is not None:
            db_account.risk_config = request.risk_config

    # Fetch updated account
    updated = store.get_account(account_id)

    logger.info(
        "account_updated",
        account_id=account_id,
        fields_changed=[k for k, v in request.model_dump().items() if v is not None],
    )

    return _account_to_response(updated)


@router.get(
    "/{account_id}/balance",
    response_model=BalanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get account balance",
    description="Returns account balance breakdown.",
)
async def get_account_balance(account_id: str) -> BalanceResponse:
    """Get account balance details.

    Args:
        account_id: Account ID.

    Returns:
        BalanceResponse with balance breakdown.

    Raises:
        HTTPException: 404 if account not found.
    """
    store = get_store()
    account = store.get_account(account_id)

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account not found: {account_id}",
        )

    # Calculate open positions value
    positions = store.get_positions_for_account(account_id)
    from src.data.models.position import PositionStatus
    open_positions = [p for p in positions if p.status == PositionStatus.OPEN]
    positions_value = sum(p.current_price * p.size for p in open_positions)

    available_margin = account.equity_usdt - positions_value

    return BalanceResponse(
        account_id=account.id,
        balance_usdt=account.balance_usdt,
        equity_usdt=account.equity_usdt,
        available_margin=max(0.0, available_margin),
        open_positions_value=round(positions_value, 4),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/{account_id}/pnl",
    response_model=AccountPnLResponse,
    status_code=status.HTTP_200_OK,
    summary="Get account P&L",
    description="Returns P&L history for an account with summary statistics.",
)
async def get_account_pnl(
    account_id: str,
    days: int = Query(default=30, ge=1, le=365, description="Number of days of history"),
) -> AccountPnLResponse:
    """Get P&L history for an account.

    Args:
        account_id: Account ID.
        days: Number of days of history to return.

    Returns:
        AccountPnLResponse with records and summary.

    Raises:
        HTTPException: 404 if account not found.
    """
    store = get_store()
    account = store.get_account(account_id)

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account not found: {account_id}",
        )

    today = date.today()
    start_date = today - timedelta(days=days)

    records = store.get_pnl_history(account_id, start_date=start_date, end_date=today)

    entries = [
        PnLEntry(
            date=str(r.record_date),
            realized_pnl=r.realized_pnl,
            unrealized_pnl=r.unrealized_pnl,
            total_pnl=r.total_pnl,
            portfolio_value=r.portfolio_value,
            daily_return_pct=r.daily_return_pct,
            trades_count=r.trades_count,
        )
        for r in records
    ]

    # Summary statistics
    total_pnl = sum(r.total_pnl for r in records)
    realized_pnl = sum(r.realized_pnl for r in records)
    unrealized_pnl = sum(r.unrealized_pnl for r in records)
    total_trades = sum(r.trades_count for r in records)
    winning_trades = sum(r.winning_trades for r in records)
    losing_trades = sum(r.losing_trades for r in records)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

    daily_pnls = [r.total_pnl for r in records]
    best_day = max(daily_pnls) if daily_pnls else 0.0
    worst_day = min(daily_pnls) if daily_pnls else 0.0

    summary = PnLSummary(
        total_pnl=total_pnl,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=round(win_rate, 2),
        best_day=best_day,
        worst_day=worst_day,
    )

    return AccountPnLResponse(
        account_id=account_id,
        records=entries,
        summary=summary,
        period_start=str(start_date),
        period_end=str(today),
    )
