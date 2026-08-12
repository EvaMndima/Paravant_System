"""Strategy management API endpoints.

Provides HTTP endpoints for creating, listing, updating, and transitioning
strategies through their lifecycle. Also handles strategy assignment
and regime management.

Decision: DEC-2026-02-08-004 - Explicit CORS origins
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.core.exceptions import (
    InvalidParametersError,
    InvalidStatusTransitionError,
    StrategyError,
    TemplateNotFoundError,
)
from src.core.strategy.engine import StrategyEngine
from src.core.strategy.regime import MarketRegime, get_all_regimes, get_regime, set_regime
from src.data.models import StrategyStatus
from src.data.store import DataStore
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class CreateStrategyRequest(BaseModel):
    """Request to create a new strategy from a template."""

    name: str = Field(..., min_length=1, max_length=200, description="Strategy name")
    template_id: str = Field(..., min_length=1, description="Template identifier")
    parameters: dict[str, Any] | None = Field(
        default=None, description="Strategy parameters (uses template defaults if omitted)"
    )
    symbols: list[str] | None = Field(
        default=None, description="Trading symbols (uses template defaults if omitted)"
    )
    description: str = Field(default="", max_length=1000, description="Strategy description")


class UpdateParametersRequest(BaseModel):
    """Request to update strategy parameters."""

    parameters: dict[str, Any] = Field(..., description="New parameter values")


class TransitionRequest(BaseModel):
    """Request to transition strategy status."""

    new_status: str = Field(..., description="Target status value")
    reason: str = Field(default="", max_length=500, description="Reason for transition")


class AssignRequest(BaseModel):
    """Request to assign a strategy to an account."""

    account_id: str = Field(..., min_length=1, description="Account ID")
    symbol: str = Field(..., min_length=1, description="Trading symbol")
    timeframe: str = Field(..., min_length=1, description="Candle timeframe (e.g. 1h, 4h)")
    regime_filter: list[str] = Field(
        default_factory=list, description="Regime filter (empty = all regimes)"
    )


class SetRegimeRequest(BaseModel):
    """Request to set market regime for a symbol."""

    symbol: str = Field(..., min_length=1, description="Trading symbol")
    regime: str = Field(..., description="Market regime value")


class StrategyResponse(BaseModel):
    """Strategy response model."""

    id: str
    name: str
    status: str
    template_id: str
    template_version: str
    type: str
    symbols: list[str]
    description: str | None = None
    parameters: dict[str, Any] | None = None


class SimilarityWarning(BaseModel):
    """Warning about a similar existing strategy."""

    strategy_id: str
    strategy_name: str
    overall_score: float
    is_similar: bool


class CreateStrategyResponse(BaseModel):
    """Response after creating a strategy."""

    strategy: StrategyResponse
    similarity_warnings: list[SimilarityWarning]


# ---------------------------------------------------------------------------
# Module-level singletons (initialized on first use)
# ---------------------------------------------------------------------------

_store: DataStore | None = None
_engine: StrategyEngine | None = None


def _get_store() -> DataStore:
    """Get or create the DataStore singleton."""
    global _store
    if _store is None:
        _store = DataStore()
    return _store


def _get_engine() -> StrategyEngine:
    """Get or create the StrategyEngine singleton."""
    global _engine
    if _engine is None:
        _engine = StrategyEngine(store=_get_store())
    return _engine


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=CreateStrategyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_strategy(request: CreateStrategyRequest) -> CreateStrategyResponse:
    """Create a new strategy from a template.

    Creates a strategy in DRAFT status with validated parameters.
    Returns similarity warnings if similar strategies exist.
    """
    engine = _get_engine()

    try:
        strategy, similarities = engine.create_strategy(
            name=request.name,
            template_id=request.template_id,
            params=request.parameters,
            symbols=request.symbols,
            description=request.description,
        )
    except TemplateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.to_dict(),
        )
    except InvalidParametersError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.to_dict(),
        )
    except StrategyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict(),
        )

    return CreateStrategyResponse(
        strategy=StrategyResponse(
            id=strategy.id,
            name=strategy.name,
            status=strategy.status.value,
            template_id=strategy.template_id,
            template_version=strategy.template_version,
            type=strategy.type.value,
            symbols=strategy.symbols,
            description=strategy.description,
            parameters=strategy.parameters,
        ),
        similarity_warnings=[
            SimilarityWarning(
                strategy_id=s.strategy_id,
                strategy_name=s.strategy_name,
                overall_score=s.overall_score,
                is_similar=s.is_similar,
            )
            for s in similarities
            if s.is_similar
        ],
    )


@router.get("", response_model=list[StrategyResponse])
async def list_strategies(
    status_filter: str | None = None,
) -> list[StrategyResponse]:
    """List all strategies, optionally filtered by status."""
    store = _get_store()

    if status_filter:
        try:
            strategy_status = StrategyStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            )
        strategies = store.get_strategies_by_status(strategy_status)
    else:
        strategies = store.get_all_strategies()

    return [
        StrategyResponse(
            id=s.id,
            name=s.name,
            status=s.status.value,
            template_id=s.template_id,
            template_version=s.template_version,
            type=s.type.value,
            symbols=s.symbols,
            description=s.description,
            parameters=s.parameters,
        )
        for s in strategies
    ]


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str) -> dict[str, Any]:
    """Get strategy details including template info."""
    engine = _get_engine()

    try:
        return engine.get_strategy_summary(strategy_id)
    except StrategyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.to_dict(),
        )


@router.put("/{strategy_id}/parameters", response_model=StrategyResponse)
async def update_parameters(
    strategy_id: str,
    request: UpdateParametersRequest,
) -> StrategyResponse:
    """Update strategy parameters (only in DRAFT or PAUSED status)."""
    engine = _get_engine()

    try:
        strategy = engine.update_strategy_parameters(strategy_id, request.parameters)
    except InvalidParametersError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.to_dict(),
        )
    except StrategyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict(),
        )

    return StrategyResponse(
        id=strategy.id,
        name=strategy.name,
        status=strategy.status.value,
        template_id=strategy.template_id,
        template_version=strategy.template_version,
        type=strategy.type.value,
        symbols=strategy.symbols,
        description=strategy.description,
        parameters=strategy.parameters,
    )


@router.post("/{strategy_id}/transition", response_model=StrategyResponse)
async def transition_status(
    strategy_id: str,
    request: TransitionRequest,
) -> StrategyResponse:
    """Transition a strategy to a new lifecycle status."""
    engine = _get_engine()

    try:
        new_status = StrategyStatus(request.new_status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {request.new_status}",
        )

    try:
        strategy = engine.transition_status(
            strategy_id=strategy_id,
            new_status=new_status,
            reason=request.reason,
        )
    except InvalidStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.to_dict(),
        )
    except StrategyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict(),
        )

    return StrategyResponse(
        id=strategy.id,
        name=strategy.name,
        status=strategy.status.value,
        template_id=strategy.template_id,
        template_version=strategy.template_version,
        type=strategy.type.value,
        symbols=strategy.symbols,
        description=strategy.description,
        parameters=strategy.parameters,
    )


@router.get("/{strategy_id}/transitions")
async def get_valid_transitions(strategy_id: str) -> dict[str, list[str]]:
    """Get valid next statuses for a strategy."""
    engine = _get_engine()

    try:
        transitions = engine.get_valid_transitions(strategy_id)
    except StrategyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.to_dict(),
        )

    return {"valid_transitions": transitions}


@router.post("/{strategy_id}/assign")
async def assign_strategy(
    strategy_id: str,
    request: AssignRequest,
) -> dict[str, Any]:
    """Assign a strategy to an account for a symbol/timeframe."""
    engine = _get_engine()

    try:
        assignment = engine.assign_strategy(
            strategy_id=strategy_id,
            account_id=request.account_id,
            symbol=request.symbol,
            timeframe=request.timeframe,
            regime_filter=request.regime_filter,
        )
    except StrategyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict(),
        )

    return {
        "id": assignment.id,
        "strategy_id": assignment.strategy_id,
        "account_id": assignment.account_id,
        "symbol": assignment.symbol,
        "timeframe": assignment.timeframe,
        "status": assignment.status.value,
    }


@router.delete("/assignments/{assignment_id}")
async def unassign_strategy(assignment_id: str) -> dict[str, str]:
    """Unassign a strategy (set assignment to STOPPED)."""
    engine = _get_engine()

    try:
        engine.unassign_strategy(assignment_id)
    except StrategyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict(),
        )

    return {"status": "stopped", "assignment_id": assignment_id}


# ---------------------------------------------------------------------------
# Regime endpoints
# ---------------------------------------------------------------------------


@router.post("/regimes")
async def set_market_regime(request: SetRegimeRequest) -> dict[str, str]:
    """Set the market regime for a symbol."""
    try:
        regime = MarketRegime(request.regime)
    except ValueError:
        valid = [r.value for r in MarketRegime]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid regime '{request.regime}'. Valid: {valid}",
        )

    store = _get_store()
    set_regime(request.symbol, regime, store)

    return {
        "symbol": request.symbol,
        "regime": regime.value,
        "status": "set",
    }


@router.get("/regimes")
async def list_regimes() -> dict[str, str]:
    """Get all current market regimes."""
    store = _get_store()
    regimes = get_all_regimes(store)
    return {symbol: regime.value for symbol, regime in regimes.items()}


@router.get("/regimes/{symbol}")
async def get_symbol_regime(symbol: str) -> dict[str, str]:
    """Get the market regime for a specific symbol."""
    store = _get_store()
    regime = get_regime(symbol, store)
    return {"symbol": symbol, "regime": regime.value}
