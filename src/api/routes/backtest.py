"""Backtest API endpoints.

Provides HTTP endpoints for running backtests on strategies and
retrieving trade log results.

Decision: DEC-2026-02-08-004 - Explicit CORS origins
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations


from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.core.exceptions import BacktestError, StrategyError
from src.core.strategy.backtest import (
    BacktestConfig,
    BacktestEngine,
)
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import MarketDataFetcher
from src.data.models import StrategyStatus
from src.data.store import DataStore
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class BacktestRequest(BaseModel):
    """Request to run a backtest."""

    initial_capital: float = Field(
        default=10_000.0, gt=0, description="Starting capital in USDT"
    )
    commission_rate: float = Field(
        default=0.001, ge=0, le=0.05, description="Commission rate per trade"
    )
    slippage_rate: float = Field(
        default=0.0005, ge=0, le=0.05, description="Slippage rate per trade"
    )
    symbol: str = Field(
        default="BTCUSDT", min_length=1, description="Trading pair"
    )
    timeframe: str = Field(
        default="1h", min_length=1, description="Candle timeframe"
    )
    lookback_days: int = Field(
        default=90, ge=7, le=365, description="Days of historical data"
    )


class BacktestMetricsResponse(BaseModel):
    """Response model for backtest metrics summary."""

    total_return_pct: float
    annualized_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    total_trades: int
    win_rate_pct: float
    profit_factor: float
    expectancy: float
    passed_validation: bool
    validation_errors: list[str] = Field(default_factory=list)


class BacktestResponse(BaseModel):
    """Response after running a backtest."""

    strategy_id: str
    strategy_name: str
    status: str
    metrics: BacktestMetricsResponse
    initial_capital: float
    final_capital: float
    start_date: str
    end_date: str


class TradeRecordResponse(BaseModel):
    """Response model for a single trade record."""

    entry_time: str
    exit_time: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    quantity: float
    realized_pnl: float
    return_pct: float


class TradeLogResponse(BaseModel):
    """Paginated trade log response."""

    trades: list[TradeRecordResponse]
    total: int
    page: int
    per_page: int


class EquityPointResponse(BaseModel):
    """Single equity curve snapshot."""

    timestamp: str
    value: float


class FullTradeResponse(BaseModel):
    """Complete trade record for modal consumption."""

    id: str
    entry_time: str
    exit_time: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    quantity: float
    realized_pnl: float
    return_pct: float
    duration_hours: float
    commission_total: float


class FullBacktestMetricsResponse(BaseModel):
    """All metrics fields the modal Overview and P&L tabs consume."""

    total_return_pct: float
    annualized_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown_pct: float
    max_drawdown_duration_days: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    expectancy: float
    avg_win_pct: float
    avg_loss_pct: float
    largest_win: float
    largest_loss: float
    passed_validation: bool
    validation_errors: list[str] = Field(default_factory=list)


class FullBacktestResponse(BaseModel):
    """Complete backtest results for modal consumption.

    Returns all equity curve points and all trades without pagination,
    so the frontend modal can render charts and the full trade log.
    """

    strategy_id: str
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    metrics: FullBacktestMetricsResponse
    equity_curve: list[EquityPointResponse]
    trades: list[FullTradeResponse]
    passed_validation: bool
    validation_errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_store: DataStore | None = None


def _get_store() -> DataStore:
    """Get or create the DataStore singleton."""
    global _store
    if _store is None:
        _store = DataStore()
    return _store


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{strategy_id}/backtest",
    response_model=BacktestResponse,
    status_code=status.HTTP_200_OK,
)
async def run_backtest(
    strategy_id: str,
    request: BacktestRequest,
) -> BacktestResponse:
    """Run a backtest for a strategy.

    Validates the strategy exists and is in a valid status,
    then runs the backtest engine and stores results.

    Args:
        strategy_id: ID of the strategy to backtest.
        request: Backtest configuration parameters.

    Returns:
        BacktestResponse with metrics summary.

    Raises:
        HTTPException: If strategy not found or backtest fails.
    """
    store = _get_store()

    # Load strategy
    strategy = store.get_strategy(strategy_id)
    if strategy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy not found: {strategy_id}",
        )

    # Validate strategy status allows backtesting
    allowed_statuses = {
        StrategyStatus.DRAFT,
        StrategyStatus.BACKTEST,
    }
    if strategy.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot backtest strategy in {strategy.status.value} status. "
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
        # Fetch historical data
        fetcher = MarketDataFetcher()
        from datetime import datetime, timedelta, timezone

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=request.lookback_days)

        series = await fetcher.fetch_historical_ohlcv(
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_date=start_date,
            end_date=end_date,
        )

        # Run backtest
        factory = SignalGeneratorFactory()
        engine = BacktestEngine(signal_generator_factory=factory)
        result = engine.run_backtest(
            strategy=strategy,
            series=series,
            config=config,
        )

        # Store results in strategy
        strategy.backtest_results = result.to_dict()
        store.save_strategy(strategy)

        logger.info(
            "backtest_completed",
            strategy_id=strategy_id,
            total_return_pct=result.metrics.total_return_pct,
            sharpe=result.metrics.sharpe_ratio,
            passed=result.passed_validation,
        )

        return BacktestResponse(
            strategy_id=strategy.id,
            strategy_name=strategy.name,
            status=strategy.status.value,
            initial_capital=result.initial_capital,
            final_capital=result.final_capital,
            start_date=result.start_date.isoformat(),
            end_date=result.end_date.isoformat(),
            metrics=BacktestMetricsResponse(
                total_return_pct=result.metrics.total_return_pct,
                annualized_return_pct=result.metrics.annualized_return_pct,
                sharpe_ratio=result.metrics.sharpe_ratio,
                sortino_ratio=result.metrics.sortino_ratio,
                max_drawdown_pct=result.metrics.max_drawdown_pct,
                total_trades=result.metrics.total_trades,
                win_rate_pct=result.metrics.win_rate_pct,
                profit_factor=result.metrics.profit_factor,
                expectancy=result.metrics.expectancy,
                passed_validation=result.passed_validation,
                validation_errors=list(result.validation_errors),
            ),
        )

    except BacktestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except StrategyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "backtest_failed",
            strategy_id=strategy_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backtest failed: {e!s}",
        )


@router.get(
    "/{strategy_id}/backtest/trades",
    response_model=TradeLogResponse,
)
async def get_backtest_trades(
    strategy_id: str,
    page: int = 1,
    per_page: int = 50,
) -> TradeLogResponse:
    """Get trade log from the last backtest run.

    Returns paginated list of trade records stored in
    Strategy.backtest_results.

    Args:
        strategy_id: ID of the strategy.
        page: Page number (1-indexed).
        per_page: Results per page (max 100).

    Returns:
        TradeLogResponse with paginated trades.

    Raises:
        HTTPException: If strategy or backtest results not found.
    """
    store = _get_store()

    strategy = store.get_strategy(strategy_id)
    if strategy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy not found: {strategy_id}",
        )

    backtest_data = strategy.backtest_results
    if not backtest_data or not isinstance(backtest_data, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No backtest results found for this strategy",
        )

    trade_log = backtest_data.get("trade_log", [])
    total = len(trade_log)

    # Clamp per_page
    per_page = min(max(per_page, 1), 100)
    page = max(page, 1)

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_trades = trade_log[start_idx:end_idx]

    trades = []
    for t in page_trades:
        trades.append(
            TradeRecordResponse(
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

    return TradeLogResponse(
        trades=trades,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/{strategy_id}/backtest/results",
    response_model=FullBacktestResponse,
)
async def get_backtest_results(
    strategy_id: str,
) -> FullBacktestResponse:
    """Get complete backtest results for modal consumption.

    Returns all equity curve points and all trade records without
    pagination, along with the full metrics set. Intended for the
    BacktestResultsModal which renders charts and a complete trade log.

    Args:
        strategy_id: ID of the strategy.

    Returns:
        FullBacktestResponse with equity curve, all trades, and metrics.

    Raises:
        HTTPException: If strategy or backtest results not found.
    """
    store = _get_store()

    strategy = store.get_strategy(strategy_id)
    if strategy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy not found: {strategy_id}",
        )

    data = strategy.backtest_results
    if not data or not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No backtest results found for this strategy",
        )

    metrics_raw = data.get("metrics", {})
    passed = data.get("passed_validation", False)
    validation_errors: list[str] = data.get("validation_errors", [])

    # Build equity curve list
    equity_curve: list[EquityPointResponse] = [
        EquityPointResponse(
            timestamp=ep.get("timestamp", ""),
            value=float(ep.get("equity", 0.0)),
        )
        for ep in data.get("equity_curve", [])
    ]

    # Build full trade list — compute duration_hours and commission_total
    raw_trades: list[dict] = data.get("trade_log", [])
    trades: list[FullTradeResponse] = []
    for idx, t in enumerate(raw_trades):
        entry_iso = t.get("entry_time", "")
        exit_iso = t.get("exit_time", "")
        try:
            entry_dt = datetime.fromisoformat(entry_iso)
            exit_dt = datetime.fromisoformat(exit_iso)
            duration_hours = (exit_dt - entry_dt).total_seconds() / 3600.0
        except (ValueError, TypeError):
            duration_hours = 0.0

        symbol = t.get("symbol", "")
        commission_total = float(
            t.get("entry_commission", 0.0) + t.get("exit_commission", 0.0)
        )

        trades.append(
            FullTradeResponse(
                id=f"{symbol}-{idx}",
                entry_time=entry_iso,
                exit_time=exit_iso,
                symbol=symbol,
                direction=t.get("direction", ""),
                entry_price=float(t.get("entry_price", 0.0)),
                exit_price=float(t.get("exit_price", 0.0)),
                quantity=float(t.get("quantity", 0.0)),
                realized_pnl=float(t.get("realized_pnl", 0.0)),
                return_pct=float(t.get("return_pct", 0.0)),
                duration_hours=round(duration_hours, 2),
                commission_total=round(commission_total, 6),
            )
        )

    metrics = FullBacktestMetricsResponse(
        total_return_pct=float(metrics_raw.get("total_return_pct", 0.0)),
        annualized_return_pct=float(metrics_raw.get("annualized_return_pct", 0.0)),
        sharpe_ratio=float(metrics_raw.get("sharpe_ratio", 0.0)),
        sortino_ratio=float(metrics_raw.get("sortino_ratio", 0.0)),
        calmar_ratio=float(metrics_raw.get("calmar_ratio", 0.0)),
        max_drawdown_pct=float(metrics_raw.get("max_drawdown_pct", 0.0)),
        max_drawdown_duration_days=float(metrics_raw.get("max_drawdown_duration_days", 0.0)),
        total_trades=int(metrics_raw.get("total_trades", 0)),
        winning_trades=int(metrics_raw.get("winning_trades", 0)),
        losing_trades=int(metrics_raw.get("losing_trades", 0)),
        win_rate_pct=float(metrics_raw.get("win_rate_pct", 0.0)),
        profit_factor=float(metrics_raw.get("profit_factor", 0.0)),
        expectancy=float(metrics_raw.get("expectancy", 0.0)),
        avg_win_pct=float(metrics_raw.get("avg_win_pct", 0.0)),
        avg_loss_pct=float(metrics_raw.get("avg_loss_pct", 0.0)),
        largest_win=float(metrics_raw.get("largest_win", 0.0)),
        largest_loss=float(metrics_raw.get("largest_loss", 0.0)),
        passed_validation=passed,
        validation_errors=list(validation_errors),
    )

    logger.info(
        "backtest_results_fetched",
        strategy_id=strategy_id,
        equity_points=len(equity_curve),
        trades=len(trades),
    )

    return FullBacktestResponse(
        strategy_id=strategy_id,
        strategy_name=data.get("strategy_name", ""),
        symbol=data.get("symbol", ""),
        timeframe=data.get("timeframe", ""),
        start_date=data.get("start_date", ""),
        end_date=data.get("end_date", ""),
        initial_capital=float(data.get("initial_capital", 0.0)),
        final_capital=float(data.get("final_capital", 0.0)),
        metrics=metrics,
        equity_curve=equity_curve,
        trades=trades,
        passed_validation=passed,
        validation_errors=list(validation_errors),
    )
