"""Paper trading engine — simulated and live modes.

Validates strategies by running them through simulated or live paper
trading before deployment with real capital. Reuses PortfolioState
and SimulatedTrader from the backtest module to avoid code duplication.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-02-14-001 - Strategy lifecycle state machine
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Awaitable
from datetime import datetime, timezone
from typing import Any

from src.core.exceptions import PaperTradingError
from src.core.strategy.backtest.metrics import BacktestMetricsCalculator
from src.core.strategy.backtest.portfolio import OpenPosition, PortfolioState
from src.core.strategy.backtest.trader import SimulatedTrader
from src.core.strategy.backtest.types import BacktestConfig, EquityPoint, TradeRecord
from src.core.strategy.factory import SignalGeneratorFactory
from src.core.strategy.paper.types import PaperTradingMode, PaperTradingStatus
from src.data.market_data import OHLCVSeries
from src.data.models import Strategy
from src.data.models.paper_session import PaperTradingSession
from src.data.models.signal import SignalDirection
from src.data.store import DataStore
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Type alias for the async data provider function
# (symbol, lookback_bars) -> OHLCVSeries | None
SeriesProvider = Callable[[str, int], Awaitable[OHLCVSeries | None]]

# Default polling interval for live mode (seconds).
# 900s (15 min) is optimal for 1H-candle strategies: new data appears
# once per hour, so polling every minute wastes API calls and CPU.
LIVE_POLLING_INTERVAL = 900

# Default number of days for simulated mode
SIMULATED_DAYS = 21

# Minimum days required for live mode validation
LIVE_MIN_DAYS = 7


class PaperTradingEngine:
    """Paper trading engine for simulated and live strategy validation.

    Supports two modes:
    - SIMULATED: Runs on the last 21 days of historical data (synchronous)
    - LIVE: Polls for new data every 60 seconds (asynchronous loop)

    Reuses PortfolioState and SimulatedTrader from the backtest module
    for consistent simulation logic.

    Example:
        >>> engine = PaperTradingEngine(
        ...     strategy=strategy,
        ...     signal_generator_factory=factory,
        ...     series_provider=fetch_series,
        ...     mode=PaperTradingMode.SIMULATED,
        ... )
        >>> await engine.start()
        >>> status = engine.get_status()
    """

    def __init__(
        self,
        strategy: Strategy,
        signal_generator_factory: SignalGeneratorFactory,
        series_provider: SeriesProvider,
        mode: PaperTradingMode,
        config: BacktestConfig | None = None,
        store: DataStore | None = None,
    ) -> None:
        """Initialize paper trading engine.

        Args:
            strategy: The strategy to paper trade.
            signal_generator_factory: Factory for signal generators.
            series_provider: Async callable to fetch OHLCV data.
            mode: Paper trading mode (SIMULATED or LIVE).
            config: Trading configuration. Uses defaults if None.
            store: Optional DataStore for session state persistence.
                   When provided, state survives container restarts.
        """
        self._strategy = strategy
        self._factory = signal_generator_factory
        self._series_provider = series_provider
        self._mode = mode
        self._config = config or BacktestConfig()
        self._store = store

        self._portfolio = PortfolioState(self._config.initial_capital)
        self._trader = SimulatedTrader()
        self._generator = self._factory.get_generator(strategy.template_id)

        self._is_running = False
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None
        self._stop_event = asyncio.Event()
        self._last_bar_index = 0
        # Tracks the timestamp of the last bar processed by _process_live_bar.
        # Used to replay missed bars after Railway restarts so stop/TP checks
        # are applied to every bar, not just the latest one.
        self._last_bar_timestamp: datetime | None = None
        # Last observed market close, captured on every processed live bar.
        # Used to force-close an open position at a real price when the live
        # loop stops (PARA-02), mirroring BacktestEngine's force-close at
        # last_bar.close. None until the first live bar is processed.
        self._last_close_price: float | None = None

        logger.info(
            "paper_trading_engine_created",
            strategy_id=strategy.id,
            strategy_name=strategy.name,
            mode=mode.value,
        )

    @property
    def strategy_id(self) -> str:
        """Strategy ID being paper traded."""
        return self._strategy.id

    @property
    def is_running(self) -> bool:
        """Whether the engine is currently running."""
        return self._is_running

    @property
    def mode(self) -> PaperTradingMode:
        """Paper trading mode."""
        return self._mode

    @property
    def portfolio(self) -> PortfolioState:
        """Portfolio state (for validation and metrics)."""
        return self._portfolio

    @property
    def config(self) -> BacktestConfig:
        """Backtest configuration."""
        return self._config

    async def start(self) -> None:
        """Start the paper trading engine.

        For SIMULATED mode: runs the simulation synchronously on recent data.
        For LIVE mode: starts an async polling loop.

        Raises:
            PaperTradingError: If already running or if data provider fails.
        """
        if self._is_running:
            raise PaperTradingError(
                strategy_id=self._strategy.id,
                reason="Engine is already running",
            )

        self._is_running = True
        self._started_at = datetime.now(timezone.utc)
        self._stop_event.clear()

        logger.info(
            "paper_trading_started",
            strategy_id=self._strategy.id,
            mode=self._mode.value,
        )

        try:
            if self._mode == PaperTradingMode.SIMULATED:
                await self._run_simulated()
            else:
                await self._run_live()
        except PaperTradingError:
            raise
        except Exception as exc:
            raise PaperTradingError(
                strategy_id=self._strategy.id,
                reason=f"Paper trading failed: {exc}",
            ) from exc
        finally:
            self._is_running = False
            self._stopped_at = datetime.now(timezone.utc)

    async def stop(self) -> None:
        """Stop the paper trading engine gracefully.

        For LIVE mode: signals the polling loop to stop.
        For SIMULATED mode: no-op (runs synchronously).
        """
        if not self._is_running:
            return

        logger.info(
            "paper_trading_stopping",
            strategy_id=self._strategy.id,
        )

        self._stop_event.set()

    def get_status(self) -> PaperTradingStatus:
        """Get current paper trading status.

        Returns:
            PaperTradingStatus with current metrics and state.
        """
        current_pnl = 0.0
        current_equity = self._config.initial_capital
        current_pnl_pct = 0.0

        if self._portfolio.equity_curve:
            last_equity = self._portfolio.equity_curve[-1].equity
            current_equity = last_equity
            current_pnl = last_equity - self._config.initial_capital
            if self._config.initial_capital > 0:
                current_pnl_pct = (current_pnl / self._config.initial_capital) * 100.0

        # Realized PnL = sum of all closed trade records
        realized_pnl = sum(t.realized_pnl for t in self._portfolio.trade_log)
        # Unrealized PnL = mark-to-market equity minus realized gains
        unrealized_pnl = current_pnl - realized_pnl

        # Open position metadata for display
        has_open_position = self._portfolio.has_position()
        open_position_direction: str | None = None
        open_position_entry_price: float | None = None
        if has_open_position and self._portfolio.position is not None:
            open_position_direction = self._portfolio.position.direction.value
            open_position_entry_price = self._portfolio.position.entry_price

        days_elapsed = 0.0
        if self._started_at is not None:
            reference = self._stopped_at or datetime.now(timezone.utc)
            days_elapsed = (reference - self._started_at).total_seconds() / 86400.0

        return PaperTradingStatus(
            mode=self._mode,
            strategy_id=self._strategy.id,
            strategy_name=self._strategy.name,
            is_running=self._is_running,
            started_at=self._started_at,
            stopped_at=self._stopped_at,
            current_equity=current_equity,
            initial_capital=self._config.initial_capital,
            current_pnl=current_pnl,
            current_pnl_pct=current_pnl_pct,
            num_trades=len(self._portfolio.trade_log),
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            has_open_position=has_open_position,
            open_position_direction=open_position_direction,
            open_position_entry_price=open_position_entry_price,
            days_elapsed=days_elapsed,
        )

    def get_trade_log(self) -> list[dict[str, Any]]:
        """Get all completed trades as serialized dictionaries.

        Returns:
            List of trade record dictionaries.
        """
        return [t.to_dict() for t in self._portfolio.trade_log]

    def get_equity_curve(self) -> list[dict[str, Any]]:
        """Get equity curve as serialized dictionaries.

        Returns:
            List of equity point dictionaries.
        """
        return [p.to_dict() for p in self._portfolio.equity_curve]

    def get_metrics(self) -> dict[str, Any]:
        """Calculate and return current metrics.

        Returns:
            Metrics dictionary with current performance data.
        """
        metrics = BacktestMetricsCalculator.calculate(
            trades=self._portfolio.trade_log,
            equity_points=self._portfolio.equity_curve,
            initial_capital=self._config.initial_capital,
            config=self._config,
        )
        return metrics.to_dict()

    async def _run_simulated(self) -> None:
        """Run simulated paper trading on recent historical data.

        Fetches the last 21 days of data and runs the strategy
        through it bar-by-bar, identical to backtesting logic.
        """
        symbol = self._strategy.symbols[0] if self._strategy.symbols else "BTCUSDT"

        # Fetch recent data — 21 days * 24 hours * 60 minutes for 1m bars
        # or proportionally fewer for larger timeframes; use 2000 bars as safe default
        lookback_bars = 2000

        series = await self._series_provider(symbol, lookback_bars)
        if series is None or len(series) < self._generator.min_bars_required + 2:
            raise PaperTradingError(
                strategy_id=self._strategy.id,
                reason=(
                    f"Insufficient data for simulated paper trading: "
                    f"need {self._generator.min_bars_required + 2} bars"
                ),
            )

        logger.info(
            "simulated_paper_trading_running",
            strategy_id=self._strategy.id,
            num_bars=len(series),
        )

        min_bars = self._generator.min_bars_required

        for i in range(min_bars - 1, len(series) - 1):
            if self._stop_event.is_set():
                break

            # Check stop-loss / take-profit on current bar before signals
            self._trader.check_stop_take_profit(
                portfolio=self._portfolio,
                bar=series[i],
                config=self._config,
            )

            visible = series.slice(0, i + 1)
            signal = self._generator.generate(
                visible,
                self._strategy.parameters,
                series.symbol,
            )

            if signal is not None:
                next_bar = series[i + 1]
                self._trader.execute_signal(
                    signal=signal,
                    portfolio=self._portfolio,
                    next_bar=next_bar,
                    config=self._config,
                    allow_flip=False,
                )

            self._portfolio.record_equity(
                timestamp=series[i].timestamp,
                current_price=series[i].close,
            )

        # Record final equity and force-close
        last_bar = series[-1]
        self._portfolio.record_equity(
            timestamp=last_bar.timestamp,
            current_price=last_bar.close,
        )
        self._trader.force_close_at_price(
            portfolio=self._portfolio,
            price=last_bar.close,
            timestamp=last_bar.timestamp,
            config=self._config,
        )

        logger.info(
            "simulated_paper_trading_completed",
            strategy_id=self._strategy.id,
            num_trades=len(self._portfolio.trade_log),
        )

    def _load_state(self) -> None:
        """Restore portfolio state from a persisted DB snapshot.

        Called once at the start of _run_live(). If no snapshot exists
        (first run or store not configured), the portfolio starts fresh.
        Silently skips on any error so a corrupted snapshot never blocks startup.
        """
        if self._store is None:
            return

        try:
            saved = self._store.get_paper_session(self._strategy.id)
        except Exception as exc:
            logger.warning(
                "paper_state_load_failed",
                strategy_id=self._strategy.id,
                error=str(exc),
            )
            return

        if saved is None:
            return

        # Restore cash and started_at
        self._portfolio.cash = saved.cash
        self._started_at = saved.started_at

        # Restore open position if one was saved
        if saved.position_data:
            p = saved.position_data

            # Restore last-processed bar timestamp for gap-replay on restart
            last_ts_str = p.get("last_bar_timestamp")
            if last_ts_str:
                try:
                    self._last_bar_timestamp = datetime.fromisoformat(last_ts_str)
                except (ValueError, TypeError):
                    pass

            # Restore position when sentinel is present, or (backward-compat)
            # when old data has "symbol" key directly in the dict
            has_position = p.get("in_position_marker", bool(p.get("symbol")))
            if has_position:
                try:
                    self._portfolio._position = OpenPosition(
                        symbol=p["symbol"],
                        direction=SignalDirection(p["direction"]),
                        quantity=p["quantity"],
                        entry_price=p["entry_price"],
                        entry_commission=p["entry_commission"],
                        entry_slippage=p["entry_slippage"],
                        entry_time=datetime.fromisoformat(p["entry_time"]),
                        stop_loss=p.get("stop_loss"),
                        take_profit=p.get("take_profit"),
                        trail_distance=p.get("trail_distance"),
                    )
                except Exception as exc:
                    logger.warning(
                        "paper_state_position_restore_failed",
                        strategy_id=self._strategy.id,
                        error=str(exc),
                    )

        # Restore completed trade log
        restored_trades: list[TradeRecord] = []
        for t in saved.trade_log:
            try:
                restored_trades.append(TradeRecord(
                    entry_time=datetime.fromisoformat(t["entry_time"]),
                    exit_time=datetime.fromisoformat(t["exit_time"]),
                    symbol=t["symbol"],
                    direction=SignalDirection(t["direction"]),
                    entry_price=t["entry_price"],
                    exit_price=t["exit_price"],
                    quantity=t["quantity"],
                    entry_commission=t["entry_commission"],
                    exit_commission=t["exit_commission"],
                    slippage_cost=t["slippage_cost"],
                    realized_pnl=t["realized_pnl"],
                    return_pct=t["return_pct"],
                ))
            except Exception:
                pass  # Skip malformed records — don't lose the rest
        self._portfolio._trade_log = restored_trades

        # Restore equity curve (last 500 points)
        restored_curve: list[EquityPoint] = []
        for e in saved.equity_curve:
            try:
                restored_curve.append(EquityPoint(
                    timestamp=datetime.fromisoformat(e["timestamp"]),
                    equity=e["equity"],
                    cash=e["cash"],
                    position_value=e["position_value"],
                ))
            except Exception:
                pass
        self._portfolio.equity_curve = restored_curve

        logger.info(
            "paper_state_restored",
            strategy_id=self._strategy.id,
            cash=saved.cash,
            trades=len(restored_trades),
            equity_points=len(restored_curve),
            has_position=saved.position_data is not None,
        )

    def _save_state(self) -> None:
        """Persist current portfolio state to the DB.

        Called after every poll cycle. Silently skips on any error so a
        DB write failure never crashes the trading loop.
        Caps equity_curve at 500 points to keep the row bounded.
        """
        if self._store is None:
            return

        try:
            # Always persist last_bar_timestamp for gap-replay on restart.
            # When a position is open the sentinel "in_position_marker" is added
            # so _load_state() can distinguish "position present" from "timestamp only".
            last_ts_str = (
                self._last_bar_timestamp.isoformat()
                if self._last_bar_timestamp is not None
                else None
            )
            position_data: dict[str, Any] = {"last_bar_timestamp": last_ts_str}

            if self._portfolio.has_position() and self._portfolio.position is not None:
                pos = self._portfolio.position
                position_data.update({
                    "in_position_marker": True,
                    "symbol": pos.symbol,
                    "direction": pos.direction.value,
                    "quantity": pos.quantity,
                    "entry_price": pos.entry_price,
                    "entry_commission": pos.entry_commission,
                    "entry_slippage": pos.entry_slippage,
                    "entry_time": pos.entry_time.isoformat(),
                    "stop_loss": pos.stop_loss,
                    "take_profit": pos.take_profit,
                    "trail_distance": pos.trail_distance,
                })

            # Cap equity curve at 500 most recent points
            curve_slice = self._portfolio.equity_curve[-500:]

            symbol = self._strategy.symbols[0] if self._strategy.symbols else ""
            template_id = getattr(self._strategy, "template_id", "")

            session_record = PaperTradingSession(
                session_id=self._strategy.id,
                template_id=template_id,
                symbol=symbol,
                initial_capital=self._config.initial_capital,
                cash=self._portfolio.cash,
                position_data=position_data,
                trade_log=[t.to_dict() for t in self._portfolio.trade_log],
                equity_curve=[p.to_dict() for p in curve_slice],
                started_at=self._started_at or datetime.now(timezone.utc),
                total_trades=len(self._portfolio.trade_log),
            )
            self._store.upsert_paper_session(session_record)
        except Exception as exc:
            logger.warning(
                "paper_state_save_failed",
                strategy_id=self._strategy.id,
                error=str(exc),
            )

    async def _run_live(self) -> None:
        """Run live paper trading with polling loop.

        Polls for new data every LIVE_POLLING_INTERVAL seconds.
        Processes new bars as they arrive. Continues until stopped
        or stop_event is set.
        """
        symbol = self._strategy.symbols[0] if self._strategy.symbols else "BTCUSDT"
        min_bars = self._generator.min_bars_required

        # Restore state from last save point (survives container restarts)
        self._load_state()

        logger.info(
            "live_paper_trading_started",
            strategy_id=self._strategy.id,
            symbol=symbol,
            polling_interval=LIVE_POLLING_INTERVAL,
        )

        while not self._stop_event.is_set():
            try:
                # Fetch recent data
                lookback_bars = min_bars + 50  # Extra buffer for warmup
                series = await self._series_provider(symbol, lookback_bars)

                if series is None or len(series) < min_bars + 2:
                    logger.warning(
                        "live_paper_insufficient_data",
                        strategy_id=self._strategy.id,
                        available_bars=len(series) if series else 0,
                        required_bars=min_bars + 2,
                    )
                else:
                    # Process the latest bar
                    self._process_live_bar(series)
                    # Persist state so restarts don't lose progress
                    self._save_state()

            except PaperTradingError:
                raise
            except Exception as exc:
                logger.error(
                    "live_paper_trading_error",
                    strategy_id=self._strategy.id,
                    error=str(exc),
                )

            # Wait for next polling interval or stop signal
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=LIVE_POLLING_INTERVAL,
                )
                break  # Stop event was set
            except asyncio.TimeoutError:
                continue  # Timeout expired, poll again

        # Force-close on stop at the last observed market close, mirroring
        # BacktestEngine's end-of-run force-close (price=last_bar.close).
        #
        # PARA-02: the previous code passed `equity / position_value` — a
        # dimensionless ratio (~1.x), not a price — which booked the final
        # trade at ~$1-2 and corrupted the session trade_log that the live-
        # promotion validation report (DEC-2026-05-27-004/005) reads.
        if self._portfolio.has_position():
            close_price = self._last_close_price
            if close_price is None:
                # No live bar was processed this run (e.g. a position restored
                # from a prior session, then stopped before the first poll).
                # Fall back to the position's entry price: a real, positive
                # price (~break-even minus exit costs) rather than an invented
                # one. Logged so this rare path is observable in production.
                pos = self._portfolio.position
                close_price = pos.entry_price if pos is not None else None
                logger.warning(
                    "force_close_missing_live_close_price",
                    strategy_id=self._strategy.id,
                    fallback_entry_price=close_price,
                )
            if close_price is not None:
                self._trader.force_close_at_price(
                    portfolio=self._portfolio,
                    price=close_price,
                    timestamp=datetime.now(timezone.utc),
                    config=self._config,
                )

        logger.info(
            "live_paper_trading_stopped",
            strategy_id=self._strategy.id,
            num_trades=len(self._portfolio.trade_log),
        )

    def _process_live_bar(self, series: OHLCVSeries) -> None:
        """Process a single live data update.

        Replays every bar since the last poll before generating new signals.
        This closes the gap-replay bug: if Railway restarted and 6 hours of
        candles arrived while the service was down, stop/TP checks are applied
        to each missed bar in chronological order — not just the latest one.

        Uses the second-to-last bar for signal generation (no-lookahead)
        and the last bar as the fill bar for entry/exit orders.

        Args:
            series: Latest OHLCV series data.
        """
        current_bar = series[-1]
        # Retain the latest observed close so a force-close on stop can book
        # the position at a real market price (PARA-02). Set early — before
        # signal/stop processing that could raise — so it always reflects the
        # most recent bar the engine has seen.
        self._last_close_price = current_bar.close

        # --- Gap-replay: check stop/TP on every bar since last poll ---
        # Iterate over all bars newer than _last_bar_timestamp. On the very
        # first run (timestamp is None) fall back to only the current bar so
        # behaviour is identical to the old code for fresh sessions.
        if self._last_bar_timestamp is not None:
            for bar in series:
                if bar.timestamp <= self._last_bar_timestamp:
                    continue
                trade = self._trader.check_stop_take_profit(
                    portfolio=self._portfolio,
                    bar=bar,
                    config=self._config,
                )
                if trade is not None:
                    logger.info(
                        "gap_replay_stop_tp_triggered",
                        strategy_id=self._strategy.id,
                        symbol=series.symbol,
                        bar_timestamp=bar.timestamp.isoformat(),
                        realized_pnl=trade.realized_pnl,
                    )
                    # Position closed — stop replaying; remaining bars are
                    # irrelevant for the now-flat portfolio
                    break
        else:
            # First run — no timestamp reference; check current bar only
            self._trader.check_stop_take_profit(
                portfolio=self._portfolio,
                bar=current_bar,
                config=self._config,
            )

        # Advance timestamp cursor BEFORE signal generation so a crash here
        # does not replay the same bars again on the next restart
        self._last_bar_timestamp = current_bar.timestamp

        # --- Signal generation (no-lookahead: exclude latest bar) ---
        signal_series = series.slice(0, len(series) - 1)
        signal = self._generator.generate(
            signal_series,
            self._strategy.parameters,
            series.symbol,
        )

        if signal is not None:
            last_bar = series[-1]
            self._trader.execute_signal(
                signal=signal,
                portfolio=self._portfolio,
                next_bar=last_bar,
                config=self._config,
                allow_flip=False,
            )

        # Record equity
        self._portfolio.record_equity(
            timestamp=current_bar.timestamp,
            current_price=current_bar.close,
        )

    def get_state_snapshot(self) -> dict[str, Any]:
        """Create a state snapshot for persistence.

        Returns:
            Dictionary containing all state needed for recovery.
        """
        return {
            "strategy_id": self._strategy.id,
            "mode": self._mode.value,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "initial_capital": self._config.initial_capital,
            "cash": self._portfolio.cash,
            "has_position": self._portfolio.has_position(),
            "trade_log": self.get_trade_log(),
            "equity_curve": self.get_equity_curve(),
            "num_trades": len(self._portfolio.trade_log),
        }
