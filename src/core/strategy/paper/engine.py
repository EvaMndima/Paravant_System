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
from src.core.strategy.backtest.portfolio import PortfolioState
from src.core.strategy.backtest.trader import SimulatedTrader
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.factory import SignalGeneratorFactory
from src.core.strategy.paper.types import PaperTradingMode, PaperTradingStatus
from src.data.market_data import OHLCVSeries
from src.data.models import Strategy
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Type alias for the async data provider function
# (symbol, lookback_bars) -> OHLCVSeries | None
SeriesProvider = Callable[[str, int], Awaitable[OHLCVSeries | None]]

# Default polling interval for live mode (seconds)
LIVE_POLLING_INTERVAL = 60

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
    ) -> None:
        """Initialize paper trading engine.

        Args:
            strategy: The strategy to paper trade.
            signal_generator_factory: Factory for signal generators.
            series_provider: Async callable to fetch OHLCV data.
            mode: Paper trading mode (SIMULATED or LIVE).
            config: Trading configuration. Uses defaults if None.
        """
        self._strategy = strategy
        self._factory = signal_generator_factory
        self._series_provider = series_provider
        self._mode = mode
        self._config = config or BacktestConfig()

        self._portfolio = PortfolioState(self._config.initial_capital)
        self._trader = SimulatedTrader()
        self._generator = self._factory.get_generator(strategy.template_id)

        self._is_running = False
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None
        self._stop_event = asyncio.Event()
        self._last_bar_index = 0

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

    async def _run_live(self) -> None:
        """Run live paper trading with polling loop.

        Polls for new data every LIVE_POLLING_INTERVAL seconds.
        Processes new bars as they arrive. Continues until stopped
        or stop_event is set.
        """
        symbol = self._strategy.symbols[0] if self._strategy.symbols else "BTCUSDT"
        min_bars = self._generator.min_bars_required

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

        # Force-close on stop
        if self._portfolio.has_position() and self._portfolio.equity_curve:
            last_point = self._portfolio.equity_curve[-1]
            self._trader.force_close_at_price(
                portfolio=self._portfolio,
                price=last_point.equity / max(1.0, last_point.position_value) if last_point.position_value > 0 else last_point.equity,
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

        Uses the second-to-last bar for signal generation and
        the last bar for fill price.

        Args:
            series: Latest OHLCV series data.
        """
        # Use all but last bar for signal generation
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
            )

        # Record equity
        current_bar = series[-1]
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
