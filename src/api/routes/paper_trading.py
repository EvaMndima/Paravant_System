"""Paper trading API endpoints.

Provides HTTP endpoints for starting, stopping, and monitoring
paper trading sessions, plus a dashboard summary endpoint.

Decision: DEC-2026-02-08-004 - Explicit CORS origins
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.core.exceptions import PaperTradingError
from src.core.strategy.backtest import BacktestConfig
from src.core.strategy.factory import SignalGeneratorFactory
from src.core.strategy.paper import (
    PaperTradingManager,
    PaperTradingMode,
    PaperTradingStatus,
)
from src.data.market_data import MarketDataFetcher, OHLCVSeries
from src.data.models import StrategyStatus
from src.data.store import DataStore
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class PaperStartRequest(BaseModel):
    """Request to start paper trading."""

    mode: str = Field(
        default="simulated",
        description="Paper trading mode: 'simulated' or 'live'",
    )
    initial_capital: float = Field(
        default=10_000.0, gt=0, description="Starting capital in USDT"
    )
    commission_rate: float = Field(
        default=0.001, ge=0, le=0.05, description="Commission rate per trade"
    )
    slippage_rate: float = Field(
        default=0.0005, ge=0, le=0.05, description="Slippage rate per trade"
    )


class PaperStatusResponse(BaseModel):
    """Response model for paper trading status."""

    strategy_id: str
    mode: str
    is_running: bool
    started_at: str | None = None
    stopped_at: str | None = None
    current_equity: float
    current_pnl_pct: float
    num_trades: int
    days_elapsed: float
    validation_passed: bool | None = None


class PaperTradeResponse(BaseModel):
    """Response model for a paper trade record."""

    entry_time: str
    exit_time: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    quantity: float
    realized_pnl: float
    return_pct: float


class PaperDashboardResponse(BaseModel):
    """Dashboard summary for a paper trading session."""

    status: PaperStatusResponse
    metrics: dict[str, Any] = Field(default_factory=dict)
    recent_trades: list[PaperTradeResponse] = Field(default_factory=list)
    equity_curve: list[dict[str, float | str]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_store: DataStore | None = None
_manager: PaperTradingManager | None = None


def _get_store() -> DataStore:
    """Get or create the DataStore singleton."""
    global _store
    if _store is None:
        _store = DataStore()
    return _store


def _get_manager() -> PaperTradingManager:
    """Get or create the PaperTradingManager singleton."""
    global _manager
    if _manager is None:
        _manager = PaperTradingManager(
            signal_generator_factory=SignalGeneratorFactory(),
            series_provider=_create_default_series_provider(),
            data_store=_get_store(),
        )
    return _manager


def _create_default_series_provider():
    """Create a default series provider using MarketDataFetcher."""
    fetcher = MarketDataFetcher()

    async def provider(symbol: str, lookback_bars: int) -> OHLCVSeries | None:
        try:
            return await fetcher.fetch_ohlcv(
                symbol=symbol,
                timeframe="1h",
                limit=lookback_bars,
            )
        except Exception as e:
            logger.error(
                "default_series_provider_failed",
                symbol=symbol,
                lookback_bars=lookback_bars,
                error=str(e),
            )
            return None

    return provider


def _status_to_response(s: PaperTradingStatus) -> PaperStatusResponse:
    """Convert internal PaperTradingStatus to API response model."""
    return PaperStatusResponse(
        strategy_id=s.strategy_id,
        mode=s.mode.value,
        is_running=s.is_running,
        started_at=s.started_at.isoformat() if s.started_at else None,
        stopped_at=s.stopped_at.isoformat() if s.stopped_at else None,
        current_equity=s.current_equity,
        current_pnl_pct=s.current_pnl_pct,
        num_trades=s.num_trades,
        days_elapsed=s.days_elapsed,
        validation_passed=s.validation_passed,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{strategy_id}/paper/start",
    response_model=PaperStatusResponse,
)
async def start_paper_trading(
    strategy_id: str,
    request: PaperStartRequest,
) -> PaperStatusResponse:
    """Start paper trading for a strategy.

    Validates the strategy exists and is in a valid status,
    then starts the paper trading engine in the requested mode.

    Args:
        strategy_id: ID of the strategy to paper trade.
        request: Paper trading configuration.

    Returns:
        PaperStatusResponse with current status.

    Raises:
        HTTPException: If strategy not found or paper trading fails.
    """
    store = _get_store()
    manager = _get_manager()

    # Load strategy
    strategy = store.get_strategy(strategy_id)
    if strategy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy not found: {strategy_id}",
        )

    # Parse mode
    try:
        mode = PaperTradingMode(request.mode)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode: {request.mode}. Use 'simulated' or 'live'",
        )

    # Validate strategy status allows paper trading
    allowed_statuses = {
        StrategyStatus.BACKTEST,
        StrategyStatus.SIMULATED_PAPER,
        StrategyStatus.LIVE_PAPER,
    }
    if strategy.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot paper trade strategy in {strategy.status.value} status. "
                f"Allowed: {[s.value for s in allowed_statuses]}"
            ),
        )

    # Build config
    config = BacktestConfig(
        initial_capital=request.initial_capital,
        commission_rate=request.commission_rate,
        slippage_rate=request.slippage_rate,
    )

    try:
        paper_status = await manager.start_session(
            strategy=strategy,
            mode=mode,
            config=config,
        )

        logger.info(
            "paper_trading_started",
            strategy_id=strategy_id,
            mode=mode.value,
        )

        return _status_to_response(paper_status)

    except PaperTradingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "paper_trading_start_failed",
            strategy_id=strategy_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Paper trading start failed: {e!s}",
        )


@router.post(
    "/{strategy_id}/paper/stop",
    response_model=PaperStatusResponse,
)
async def stop_paper_trading(strategy_id: str) -> PaperStatusResponse:
    """Stop paper trading for a strategy.

    Gracefully stops the paper trading engine and saves state.

    Args:
        strategy_id: ID of the strategy to stop.

    Returns:
        PaperStatusResponse with final status.

    Raises:
        HTTPException: If strategy not found or not paper trading.
    """
    manager = _get_manager()

    try:
        paper_status = await manager.stop_session(strategy_id)

        logger.info(
            "paper_trading_stopped",
            strategy_id=strategy_id,
        )

        return _status_to_response(paper_status)

    except PaperTradingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{strategy_id}/paper/status",
    response_model=PaperStatusResponse,
)
async def get_paper_status(strategy_id: str) -> PaperStatusResponse:
    """Get current paper trading status.

    Args:
        strategy_id: ID of the strategy.

    Returns:
        PaperStatusResponse with current metrics.

    Raises:
        HTTPException: If no active session found.
    """
    manager = _get_manager()

    paper_status = manager.get_session_status(strategy_id)
    if paper_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No paper trading session found for strategy: {strategy_id}",
        )
    return _status_to_response(paper_status)


@router.get(
    "/{strategy_id}/paper/trades",
    response_model=list[PaperTradeResponse],
)
async def get_paper_trades(strategy_id: str) -> list[PaperTradeResponse]:
    """Get trade log from the paper trading session.

    Args:
        strategy_id: ID of the strategy.

    Returns:
        List of paper trade records.

    Raises:
        HTTPException: If no active session found.
    """
    manager = _get_manager()

    try:
        trade_dicts = manager.get_session_trades(strategy_id)
    except PaperTradingError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    trades: list[PaperTradeResponse] = []
    for t in trade_dicts:
        trades.append(
            PaperTradeResponse(
                entry_time=t.get("entry_time", ""),
                exit_time=t.get("exit_time", ""),
                symbol=t.get("symbol", ""),
                direction=t.get("direction", ""),
                entry_price=t.get("entry_price", 0.0),
                exit_price=t.get("exit_price", 0.0),
                quantity=t.get("quantity", 0.0),
                realized_pnl=t.get("realized_pnl", 0.0),
                return_pct=t.get("return_pct", 0.0),
            )
        )

    return trades


@router.get(
    "/{strategy_id}/paper/dashboard",
    response_model=PaperDashboardResponse,
)
async def get_paper_dashboard(strategy_id: str) -> PaperDashboardResponse:
    """Get dashboard summary for a paper trading session.

    Provides status, metrics, recent trades, and equity curve
    for the monitoring dashboard.

    Args:
        strategy_id: ID of the strategy.

    Returns:
        PaperDashboardResponse with full session data.

    Raises:
        HTTPException: If no active session found.
    """
    manager = _get_manager()

    paper_status = manager.get_session_status(strategy_id)
    if paper_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No paper trading session found for strategy: {strategy_id}",
        )

    snapshot = manager.get_session_snapshot(strategy_id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No session snapshot for strategy: {strategy_id}",
        )

    # Recent trades (last 10)
    trade_log = snapshot.get("trade_log", [])
    recent_trades: list[PaperTradeResponse] = []
    for t in trade_log[-10:]:
        recent_trades.append(
            PaperTradeResponse(
                entry_time=t.get("entry_time", ""),
                exit_time=t.get("exit_time", ""),
                symbol=t.get("symbol", ""),
                direction=t.get("direction", ""),
                entry_price=t.get("entry_price", 0.0),
                exit_price=t.get("exit_price", 0.0),
                quantity=t.get("quantity", 0.0),
                realized_pnl=t.get("realized_pnl", 0.0),
                return_pct=t.get("return_pct", 0.0),
            )
        )

    return PaperDashboardResponse(
        status=_status_to_response(paper_status),
        metrics=snapshot.get("metrics", {}),
        recent_trades=recent_trades,
        equity_curve=snapshot.get("equity_curve", []),
    )
