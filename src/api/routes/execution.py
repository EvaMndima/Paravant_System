"""Execution quality API endpoints.

Provides HTTP endpoints for monitoring execution quality including
slippage analysis, fill rate statistics, and comprehensive reports.

Decision: DEC-2026-02-08-004 - Explicit CORS origins
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-02-08-003 - Timezone-aware timestamps

Phase 4B: Position Tracking & Execution Quality
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.core.execution.quality import (ExecutionReportGenerator,
                                        FillRateTracker, SlippageEstimator,
                                        SlippageTracker)
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class SlippageStatsResponse(BaseModel):
    """Response model for slippage statistics."""

    total_orders: int = 0
    average_slippage_pct: float = 0.0
    average_slippage_bps: float = 0.0
    best_slippage: float = 0.0
    worst_slippage: float = 0.0
    slippage_by_symbol: dict[str, float] = Field(default_factory=dict)
    slippage_by_side: dict[str, float] = Field(default_factory=dict)


class FillRateStatsResponse(BaseModel):
    """Response model for fill rate statistics."""

    total_orders: int = 0
    filled_orders: int = 0
    cancelled_orders: int = 0
    rejected_orders: int = 0
    fill_rate_pct: float = 0.0
    cancellation_rate_pct: float = 0.0
    rejection_rate_pct: float = 0.0
    average_fill_time_seconds: float = 0.0
    min_fill_time_seconds: float = 0.0
    max_fill_time_seconds: float = 0.0
    stats_by_order_type: dict[str, Any] = Field(default_factory=dict)
    stats_by_symbol: dict[str, Any] = Field(default_factory=dict)


class ExecutionStatsResponse(BaseModel):
    """Combined execution statistics response."""

    slippage: SlippageStatsResponse
    fill_rate: FillRateStatsResponse
    timestamp: str


class SlippageAnalysisResponse(BaseModel):
    """Response model for slippage analysis."""

    average_slippage_pct: float
    total_records: int
    slippage_by_symbol: dict[str, float] = Field(default_factory=dict)
    slippage_by_side: dict[str, float] = Field(default_factory=dict)
    timestamp: str


class SlippageEstimateResponse(BaseModel):
    """Response model for pre-trade slippage estimate."""

    estimated_slippage_pct: float
    components: dict[str, float]
    should_warn: bool
    should_block: bool
    recommended_action: str
    recommendation: str


class ExecutionReportResponse(BaseModel):
    """Response model for execution quality report."""

    period_start: str
    period_end: str
    total_orders: int = 0
    filled_orders: int = 0
    cancelled_orders: int = 0
    rejected_orders: int = 0
    fill_rate_pct: float = 0.0
    average_slippage_pct: float = 0.0
    average_slippage_bps: float = 0.0
    best_slippage_pct: float = 0.0
    worst_slippage_pct: float = 0.0
    average_fill_time_seconds: float = 0.0
    min_fill_time_seconds: float = 0.0
    max_fill_time_seconds: float = 0.0
    orders_by_type: dict[str, int] = Field(default_factory=dict)
    slippage_by_symbol: dict[str, float] = Field(default_factory=dict)
    fill_rate_by_symbol: dict[str, float] = Field(default_factory=dict)
    symbols_with_high_slippage: list[str] = Field(default_factory=list)
    symbols_with_low_fill_rate: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Module-level dependency injection
# ---------------------------------------------------------------------------

_slippage_tracker: SlippageTracker | None = None
_slippage_estimator: SlippageEstimator | None = None
_fill_rate_tracker: FillRateTracker | None = None
_report_generator: ExecutionReportGenerator | None = None


def get_slippage_tracker() -> SlippageTracker:
    """Get the SlippageTracker singleton.

    Returns:
        SlippageTracker instance.

    Raises:
        HTTPException: If not initialized.
    """
    if _slippage_tracker is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Execution quality not initialized. Call init_execution_routes() first.",
        )
    return _slippage_tracker


def get_fill_rate_tracker() -> FillRateTracker:
    """Get the FillRateTracker singleton.

    Returns:
        FillRateTracker instance.

    Raises:
        HTTPException: If not initialized.
    """
    if _fill_rate_tracker is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Execution quality not initialized. Call init_execution_routes() first.",
        )
    return _fill_rate_tracker


def get_report_generator() -> ExecutionReportGenerator:
    """Get the ExecutionReportGenerator singleton.

    Returns:
        ExecutionReportGenerator instance.

    Raises:
        HTTPException: If not initialized.
    """
    if _report_generator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Execution quality not initialized. Call init_execution_routes() first.",
        )
    return _report_generator


def init_execution_routes(
    slippage_tracker: SlippageTracker,
    slippage_estimator: SlippageEstimator,
    fill_rate_tracker: FillRateTracker,
    report_generator: ExecutionReportGenerator,
) -> None:
    """Initialize the execution router with quality tracking instances.

    Must be called during application startup before handling requests.

    Args:
        slippage_tracker: Configured SlippageTracker instance.
        slippage_estimator: Configured SlippageEstimator instance.
        fill_rate_tracker: Configured FillRateTracker instance.
        report_generator: Configured ExecutionReportGenerator instance.
    """
    global _slippage_tracker, _slippage_estimator  # noqa: PLW0603
    global _fill_rate_tracker, _report_generator  # noqa: PLW0603
    _slippage_tracker = slippage_tracker
    _slippage_estimator = slippage_estimator
    _fill_rate_tracker = fill_rate_tracker
    _report_generator = report_generator
    logger.info("execution_routes_initialized")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/stats",
    response_model=ExecutionStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Current execution statistics",
    description="Returns combined slippage and fill rate statistics.",
)
async def get_execution_stats() -> ExecutionStatsResponse:
    """Get current execution quality statistics.

    Returns combined slippage and fill rate data for
    real-time monitoring dashboards.

    Returns:
        ExecutionStatsResponse with slippage and fill rate stats.
    """
    slippage_tracker = get_slippage_tracker()
    fill_rate_tracker = get_fill_rate_tracker()

    slippage_stats = slippage_tracker.get_slippage_stats()
    fill_stats = fill_rate_tracker.get_stats()

    return ExecutionStatsResponse(
        slippage=SlippageStatsResponse(
            total_orders=slippage_stats.total_orders,
            average_slippage_pct=slippage_stats.average_slippage_pct,
            average_slippage_bps=slippage_stats.average_slippage_bps,
            best_slippage=slippage_stats.best_slippage,
            worst_slippage=slippage_stats.worst_slippage,
            slippage_by_symbol=slippage_stats.slippage_by_symbol,
            slippage_by_side=slippage_stats.slippage_by_side,
        ),
        fill_rate=FillRateStatsResponse(
            total_orders=fill_stats.total_orders,
            filled_orders=fill_stats.filled_orders,
            cancelled_orders=fill_stats.cancelled_orders,
            rejected_orders=fill_stats.rejected_orders,
            fill_rate_pct=fill_stats.fill_rate_pct,
            cancellation_rate_pct=fill_stats.cancellation_rate_pct,
            rejection_rate_pct=fill_stats.rejection_rate_pct,
            average_fill_time_seconds=fill_stats.average_fill_time_seconds,
            min_fill_time_seconds=fill_stats.min_fill_time_seconds,
            max_fill_time_seconds=fill_stats.max_fill_time_seconds,
            stats_by_order_type=fill_stats.stats_by_order_type,
            stats_by_symbol=fill_stats.stats_by_symbol,
        ),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/slippage",
    response_model=SlippageAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Slippage analysis",
    description="Returns slippage analysis with optional symbol filter.",
)
async def get_slippage_analysis(
    symbol: str | None = Query(None, description="Filter by symbol"),
) -> SlippageAnalysisResponse:
    """Get slippage analysis with optional symbol filter.

    Args:
        symbol: Optional symbol to filter slippage data.

    Returns:
        SlippageAnalysisResponse with average and breakdowns.
    """
    slippage_tracker = get_slippage_tracker()
    stats = slippage_tracker.get_slippage_stats()

    avg_slippage = slippage_tracker.get_average_slippage(symbol=symbol)

    # If filtered by symbol, only show that symbol in breakdown
    by_symbol = stats.slippage_by_symbol
    if symbol and symbol in by_symbol:
        by_symbol = {symbol: by_symbol[symbol]}
    elif symbol:
        by_symbol = {}

    return SlippageAnalysisResponse(
        average_slippage_pct=avg_slippage,
        total_records=stats.total_orders,
        slippage_by_symbol=by_symbol,
        slippage_by_side=stats.slippage_by_side,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/slippage/estimate",
    response_model=SlippageEstimateResponse,
    status_code=status.HTTP_200_OK,
    summary="Pre-trade slippage estimate",
    description="Estimate slippage before placing an order (PRD Feature F).",
)
async def estimate_slippage(
    symbol: str = Query(..., description="Trading pair symbol"),
    order_size_usd: float = Query(..., gt=0, description="Order size in USD"),
    avg_daily_volume_usd: float | None = Query(
        None, gt=0, description="Average daily volume in USD"
    ),
) -> SlippageEstimateResponse:
    """Estimate slippage for a potential order.

    Uses historical data and market conditions to estimate
    expected slippage before order placement (PRD Feature F).

    Args:
        symbol: Trading pair symbol.
        order_size_usd: Order size in USD equivalent.
        avg_daily_volume_usd: Optional average daily volume.

    Returns:
        SlippageEstimateResponse with estimate and recommendation.
    """
    if _slippage_estimator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Slippage estimator not initialized.",
        )

    estimate = _slippage_estimator.estimate_slippage(
        symbol=symbol,
        order_size_usd=order_size_usd,
        avg_daily_volume_usd=avg_daily_volume_usd,
    )

    return SlippageEstimateResponse(
        estimated_slippage_pct=estimate.estimated_slippage_pct,
        components=estimate.components,
        should_warn=estimate.should_warn,
        should_block=estimate.should_block,
        recommended_action=estimate.recommended_action,
        recommendation=estimate.recommendation,
    )


@router.get(
    "/report",
    response_model=ExecutionReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Execution quality report",
    description="Generate a comprehensive execution quality report for a date range.",
)
async def get_execution_report(
    start_date: str = Query(
        ...,
        description="Report period start (ISO format, e.g. 2026-02-01T00:00:00Z)",
    ),
    end_date: str = Query(
        ...,
        description="Report period end (ISO format, e.g. 2026-02-13T23:59:59Z)",
    ),
) -> ExecutionReportResponse:
    """Generate a comprehensive execution quality report.

    Aggregates slippage and fill rate data for the specified
    period and provides actionable recommendations.

    Args:
        start_date: Period start in ISO format.
        end_date: Period end in ISO format.

    Returns:
        ExecutionReportResponse with full report.

    Raises:
        HTTPException: 400 if date format is invalid.
    """
    report_gen = get_report_generator()

    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {e}. Use ISO format (e.g. 2026-02-01T00:00:00Z).",
        ) from e

    # Ensure timezone-aware (Decision: DEC-2026-02-08-003)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)

    if end_dt <= start_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be after start_date.",
        )

    report = report_gen.generate_report(start_dt, end_dt)

    return ExecutionReportResponse(
        period_start=report.period_start.isoformat(),
        period_end=report.period_end.isoformat(),
        total_orders=report.total_orders,
        filled_orders=report.filled_orders,
        cancelled_orders=report.cancelled_orders,
        rejected_orders=report.rejected_orders,
        fill_rate_pct=report.fill_rate_pct,
        average_slippage_pct=report.average_slippage_pct,
        average_slippage_bps=report.average_slippage_bps,
        best_slippage_pct=report.best_slippage_pct,
        worst_slippage_pct=report.worst_slippage_pct,
        average_fill_time_seconds=report.average_fill_time_seconds,
        min_fill_time_seconds=report.min_fill_time_seconds,
        max_fill_time_seconds=report.max_fill_time_seconds,
        orders_by_type=report.orders_by_type,
        slippage_by_symbol=report.slippage_by_symbol,
        fill_rate_by_symbol=report.fill_rate_by_symbol,
        symbols_with_high_slippage=report.symbols_with_high_slippage,
        symbols_with_low_fill_rate=report.symbols_with_low_fill_rate,
        recommendations=report.recommendations,
    )
