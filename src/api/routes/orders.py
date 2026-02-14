"""Order management API endpoints.

Provides HTTP endpoints for order submission, cancellation,
status queries, and reconciliation.

Decision: DEC-2026-02-08-004 - Explicit CORS origins
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-02-08-003 - Timezone-aware timestamps

Phase 4A: Execution Infrastructure
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.core.exceptions import (InvalidStateTransitionError,
                                 OrderNotFoundError, OrderSubmissionError,
                                 TradingSystemError)
from src.core.execution.order_manager import OrderManager
from src.core.risk.types import OrderRequest
from src.data.models.order import Order, OrderStatus
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class OrderSubmitRequest(BaseModel):
    """Request to submit a new order."""

    account_id: str = Field(
        ...,
        min_length=1,
        description="Account placing the order",
    )
    strategy_id: str = Field(
        ...,
        min_length=1,
        description="Strategy that generated the signal",
    )
    symbol: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Trading pair (e.g., BTCUSDT)",
    )
    side: str = Field(
        ...,
        pattern="^(buy|sell)$",
        description="Order side: 'buy' or 'sell'",
    )
    quantity: float = Field(
        ...,
        gt=0,
        description="Order quantity in base asset",
    )
    price: float = Field(
        ...,
        gt=0,
        description="Expected execution price",
    )
    order_type: str = Field(
        default="market",
        pattern="^(market|limit)$",
        description="Order type (MVP: market only)",
    )
    reason: str = Field(
        default="",
        max_length=500,
        description="Why this order was generated",
    )


class OrderResponse(BaseModel):
    """Serialized order response."""

    id: str
    external_id: str | None = None
    account_id: str
    strategy_id: str | None = None
    symbol: str
    side: str
    type: str
    quantity: float
    price: float | None = None
    status: str
    filled_quantity: float = 0.0
    filled_price: float | None = None
    filled_at: str | None = None
    submitted_at: str | None = None
    rejection_reason: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class OrderListResponse(BaseModel):
    """Paginated list of orders."""

    orders: list[OrderResponse]
    total: int


class ReconciliationResponse(BaseModel):
    """Result of order reconciliation."""

    orders_updated: int
    updated_order_ids: list[str]
    timestamp: str


class ActionResponse(BaseModel):
    """Generic action response."""

    status: str
    message: str
    timestamp: str


# ---------------------------------------------------------------------------
# Module-level singleton (initialized on first use)
# ---------------------------------------------------------------------------

_order_manager: OrderManager | None = None


def get_order_manager() -> OrderManager:
    """Get or create the OrderManager singleton.

    Returns:
        OrderManager instance.

    Raises:
        HTTPException: If OrderManager is not initialized.
    """
    if _order_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Order manager not initialized. Call init_order_routes() first.",
        )
    return _order_manager


def init_order_routes(order_manager: OrderManager) -> None:
    """Initialize the orders router with an OrderManager instance.

    Must be called during application startup before handling requests.

    Args:
        order_manager: Configured OrderManager instance.
    """
    global _order_manager  # noqa: PLW0603
    _order_manager = order_manager
    logger.info("order_routes_initialized")


# ---------------------------------------------------------------------------
# Helper: Order model -> response
# ---------------------------------------------------------------------------


def _order_to_response(order: Order) -> OrderResponse:
    """Convert an Order model to an API response.

    Args:
        order: Order model instance.

    Returns:
        Serialized OrderResponse.
    """
    side_value = (
        order.side.value
        if hasattr(order.side, "value")
        else str(order.side)
    )
    type_value = (
        order.type.value
        if hasattr(order.type, "value")
        else str(order.type)
    )
    status_value = (
        order.status.value
        if hasattr(order.status, "value")
        else str(order.status)
    )

    return OrderResponse(
        id=order.id,
        external_id=order.external_id,
        account_id=order.account_id,
        strategy_id=order.strategy_id,
        symbol=order.symbol,
        side=side_value,
        type=type_value,
        quantity=order.quantity,
        price=order.price,
        status=status_value,
        filled_quantity=order.filled_quantity,
        filled_price=order.filled_price,
        filled_at=order.filled_at.isoformat() if order.filled_at else None,
        submitted_at=(
            order.submitted_at.isoformat() if order.submitted_at else None
        ),
        rejection_reason=order.rejection_reason,
        created_at=(
            order.created_at.isoformat()
            if hasattr(order, "created_at") and order.created_at
            else None
        ),
        updated_at=(
            order.updated_at.isoformat()
            if hasattr(order, "updated_at") and order.updated_at
            else None
        ),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new order",
)
async def submit_order(request: OrderSubmitRequest) -> OrderResponse:
    """Submit a new order for execution.

    The order goes through the full lifecycle:
    1. Risk validation (if controller configured)
    2. Persistence to database
    3. Submission to exchange
    4. Background monitoring

    Returns the order with its current status.
    """
    manager = get_order_manager()

    try:
        # Convert API request to domain OrderRequest
        order_request = OrderRequest(
            account_id=request.account_id,
            strategy_id=request.strategy_id,
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            price=request.price,
            order_type=request.order_type,
            reason=request.reason,
        )

        logger.info(
            "api_order_submission",
            account_id=request.account_id,
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
        )

        order = await manager.submit_order(order_request)
        return _order_to_response(order)

    except OrderSubmissionError as e:
        logger.error(
            "api_order_submission_failed",
            error=str(e),
            symbol=request.symbol,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.to_dict(),
        ) from e

    except TradingSystemError as e:
        logger.error(
            "api_order_error",
            error=str(e),
            code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict(),
        ) from e

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "VALIDATION_ERROR", "message": str(e)}},
        ) from e


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get order by ID",
)
async def get_order(order_id: str) -> OrderResponse:
    """Get a specific order by its internal ID."""
    manager = get_order_manager()

    order = await manager.get_order(order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order not found: {order_id}",
        )

    return _order_to_response(order)


@router.get(
    "",
    response_model=OrderListResponse,
    summary="List orders",
)
async def list_orders(
    account_id: str = Query(..., description="Account ID to filter by"),
    order_status: str | None = Query(
        None,
        alias="status",
        description="Filter by status (pending, submitted, filled, etc.)",
    ),
) -> OrderListResponse:
    """List orders for an account with optional status filter."""
    manager = get_order_manager()

    status_enum: OrderStatus | None = None
    if order_status:
        try:
            status_enum = OrderStatus(order_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {order_status}",
            )

    import asyncio

    orders = await asyncio.to_thread(
        manager.data_store.get_orders_by_account_and_status,
        account_id,
        status_enum,
    )

    return OrderListResponse(
        orders=[_order_to_response(o) for o in orders],
        total=len(orders),
    )


@router.delete(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Cancel an order",
)
async def cancel_order(order_id: str) -> OrderResponse:
    """Cancel an existing order.

    Only orders in PENDING, SUBMITTED, or PARTIALLY_FILLED status
    can be cancelled.
    """
    manager = get_order_manager()

    try:
        order = await manager.cancel_order(order_id)
        return _order_to_response(order)

    except OrderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.to_dict(),
        ) from e

    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.to_dict(),
        ) from e


@router.post(
    "/reconcile",
    response_model=ReconciliationResponse,
    summary="Trigger order reconciliation",
)
async def reconcile_orders() -> ReconciliationResponse:
    """Manually trigger order reconciliation with the exchange.

    PRD Feature I: Order state reconciliation.
    Compares internal order state with exchange state and updates
    any mismatches.
    """
    manager = get_order_manager()

    updated = await manager.reconcile_orders()

    return ReconciliationResponse(
        orders_updated=len(updated),
        updated_order_ids=[o.id for o in updated],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
