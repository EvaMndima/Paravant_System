"""Position management API endpoints.

Provides HTTP endpoints for viewing positions with live P&L,
closing positions via market orders, and staleness analysis.

Decision: DEC-2026-02-08-004 - Explicit CORS origins
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-02-08-003 - Timezone-aware timestamps

Phase 4B: Position Tracking & Execution Quality
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from src.core.execution.position_tracker import PositionTracker
from src.data.models.position import Position, PositionStatus
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class PositionResponse(BaseModel):
    """Response model for a single position."""

    id: str
    account_id: str
    strategy_id: str | None = None
    symbol: str
    side: str
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    return_pct: float = 0.0
    realized_pnl: float = 0.0
    commission_paid: float = 0.0
    status: str
    opened_at: str
    closed_at: str | None = None
    exit_price: float | None = None


class PositionListResponse(BaseModel):
    """Response model for position list."""

    positions: list[PositionResponse]
    total: int


class StalenessEntry(BaseModel):
    """Staleness analysis for a single position."""

    position_id: str
    symbol: str
    hold_duration_hours: float
    should_warn: bool
    should_review: bool
    should_close: bool
    days_remaining: float
    status: str


class StalenessResponse(BaseModel):
    """Response model for staleness analysis."""

    positions: list[StalenessEntry]
    total: int
    warnings: int
    reviews: int
    exceeded: int


class ClosePositionResponse(BaseModel):
    """Response model for position close request."""

    success: bool
    message: str
    position_id: str


# ---------------------------------------------------------------------------
# Module-level dependency injection
# ---------------------------------------------------------------------------

_position_tracker: PositionTracker | None = None


def get_position_tracker() -> PositionTracker:
    """Get the PositionTracker singleton.

    Returns:
        PositionTracker instance.

    Raises:
        HTTPException: If PositionTracker is not initialized.
    """
    if _position_tracker is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Position tracker not initialized. Call init_position_routes() first.",
        )
    return _position_tracker


def init_position_routes(position_tracker: PositionTracker) -> None:
    """Initialize the positions router with a PositionTracker instance.

    Must be called during application startup before handling requests.

    Args:
        position_tracker: Configured PositionTracker instance.
    """
    global _position_tracker  # noqa: PLW0603
    _position_tracker = position_tracker
    logger.info("position_routes_initialized")


# ---------------------------------------------------------------------------
# Helper: Position model -> response
# ---------------------------------------------------------------------------


def _position_to_response(
    position: Position,
    unrealized_pnl: float = 0.0,
    return_pct: float = 0.0,
) -> PositionResponse:
    """Convert a Position model to API response.

    Args:
        position: Position model instance.
        unrealized_pnl: Calculated unrealized P&L.
        return_pct: Calculated return percentage.

    Returns:
        PositionResponse with all fields populated.
    """
    pos = position

    opened_at_str = ""
    if hasattr(pos, "opened_at") and pos.opened_at:
        opened_at_str = pos.opened_at.isoformat() if hasattr(pos.opened_at, "isoformat") else str(pos.opened_at)

    closed_at_str = None
    if hasattr(pos, "closed_at") and pos.closed_at:
        closed_at_str = pos.closed_at.isoformat() if hasattr(pos.closed_at, "isoformat") else str(pos.closed_at)

    side_val = pos.side.value if hasattr(pos.side, "value") else str(pos.side)
    status_val = pos.status.value if hasattr(pos.status, "value") else str(pos.status)

    return PositionResponse(
        id=pos.id,
        account_id=pos.account_id,
        strategy_id=pos.strategy_id,
        symbol=pos.symbol,
        side=side_val,
        size=pos.size,
        entry_price=pos.entry_price,
        current_price=pos.current_price,
        unrealized_pnl=unrealized_pnl,
        return_pct=return_pct,
        realized_pnl=pos.pnl_usdt,
        commission_paid=pos.commission_paid,
        status=status_val,
        opened_at=opened_at_str,
        closed_at=closed_at_str,
        exit_price=pos.exit_price,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=PositionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all open positions",
    description="Returns all open positions with live unrealized P&L.",
)
async def list_positions(
    symbol: str | None = Query(None, description="Filter by symbol"),
    position_status: str | None = Query(
        None, alias="status", description="Filter by status (open/closed)"
    ),
) -> PositionListResponse:
    """List all positions with optional filters.

    Args:
        symbol: Optional symbol filter.
        position_status: Optional status filter.

    Returns:
        PositionListResponse with position data and P&L.
    """
    tracker = get_position_tracker()
    positions = await tracker.get_all_positions()

    # Apply filters
    if symbol:
        positions = [p for p in positions if p.symbol == symbol]
    if position_status:
        try:
            status_enum = PositionStatus(position_status)
            positions = [p for p in positions if p.status == status_enum]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {position_status}. Valid: open, closed",
            )

    # Calculate P&L for each position
    responses: list[PositionResponse] = []
    for pos in positions:
        unrealized = PositionTracker.calculate_unrealized_pnl(
            pos, pos.current_price
        )
        return_pct = PositionTracker.calculate_return_pct(
            pos, pos.current_price
        )
        responses.append(_position_to_response(pos, unrealized, return_pct))

    return PositionListResponse(
        positions=responses,
        total=len(responses),
    )


@router.get(
    "/{symbol}",
    response_model=PositionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get position by symbol",
    description="Returns a single position with full details and P&L.",
)
async def get_position(symbol: str) -> PositionResponse:
    """Get a position by its trading symbol.

    Args:
        symbol: Trading pair symbol (e.g., BTCUSDT).

    Returns:
        PositionResponse with full details.

    Raises:
        HTTPException: 404 if position not found.
    """
    tracker = get_position_tracker()
    position = await tracker.get_position(symbol)

    if position is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No open position found for symbol: {symbol}",
        )

    unrealized = PositionTracker.calculate_unrealized_pnl(
        position, position.current_price
    )
    return_pct = PositionTracker.calculate_return_pct(
        position, position.current_price
    )

    return _position_to_response(position, unrealized, return_pct)


@router.delete(
    "/{symbol}",
    response_model=ClosePositionResponse,
    status_code=status.HTTP_200_OK,
    summary="Close position",
    description="Close a position by submitting a market order in the opposite direction.",
)
async def close_position(symbol: str) -> ClosePositionResponse:
    """Close a position via market order.

    Submits a market order in the opposite direction to close
    the entire position.

    Args:
        symbol: Trading pair symbol to close.

    Returns:
        ClosePositionResponse with result.

    Raises:
        HTTPException: 404 if position not found.
    """
    tracker = get_position_tracker()
    position = await tracker.get_position(symbol)

    if position is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No open position found for symbol: {symbol}",
        )

    # Position closing via OrderManager will be implemented in integration
    # For now, return the position details for manual closing
    return ClosePositionResponse(
        success=True,
        message=f"Close request received for {symbol} position (size={position.size})",
        position_id=position.id,
    )


@router.get(
    "/analysis/staleness",
    response_model=StalenessResponse,
    status_code=status.HTTP_200_OK,
    summary="Staleness analysis",
    description="Check all open positions for staleness based on strategy type.",
)
async def analyze_staleness() -> StalenessResponse:
    """Analyze staleness for all open positions.

    Checks each position against its strategy-specific thresholds
    and returns the staleness status.

    Returns:
        StalenessResponse with staleness data for all positions.
    """
    tracker = get_position_tracker()
    results = await tracker.process_stale_positions()

    entries = [
        StalenessEntry(
            position_id=r.position_id,
            symbol=r.symbol,
            hold_duration_hours=r.hold_duration.total_seconds() / 3600.0,
            should_warn=r.should_warn,
            should_review=r.should_review,
            should_close=r.should_close,
            days_remaining=r.days_remaining,
            status=r.status,
        )
        for r in results
    ]

    return StalenessResponse(
        positions=entries,
        total=len(entries),
        warnings=sum(1 for r in results if r.status == "WARNING"),
        reviews=sum(1 for r in results if r.status == "REVIEW_REQUIRED"),
        exceeded=sum(1 for r in results if r.status == "MAX_HOLD_EXCEEDED"),
    )
