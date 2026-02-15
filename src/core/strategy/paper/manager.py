"""Paper trading session manager.

Manages multiple concurrent paper trading sessions, providing
start/stop/status operations. Persists session state for recovery
via strategy model's paper_results JSON column.

Decision: DEC-2026-02-14-001 - Strategy lifecycle state machine
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

from typing import Any

from src.core.exceptions import PaperTradingError
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.factory import SignalGeneratorFactory
from src.core.strategy.paper.engine import PaperTradingEngine, SeriesProvider
from src.core.strategy.paper.types import PaperTradingMode, PaperTradingStatus
from src.core.strategy.paper.validator import PaperTradingValidator, PaperTradingThresholds
from src.data.models import Strategy
from src.data.store import DataStore
from src.utils.logging import get_logger

logger = get_logger(__name__)


class PaperTradingManager:
    """Manages multiple paper trading sessions.

    Provides a facade for starting, stopping, and monitoring paper
    trading sessions across multiple strategies. Each strategy can
    have at most one active session.

    Example:
        >>> manager = PaperTradingManager(factory, series_provider)
        >>> await manager.start_session(strategy, PaperTradingMode.SIMULATED)
        >>> status = manager.get_session_status(strategy.id)
        >>> await manager.stop_session(strategy.id)
    """

    def __init__(
        self,
        signal_generator_factory: SignalGeneratorFactory,
        series_provider: SeriesProvider,
        data_store: DataStore,
        config: BacktestConfig | None = None,
    ) -> None:
        """Initialize paper trading manager.

        Args:
            signal_generator_factory: Factory for signal generators.
            series_provider: Async callable for fetching market data.
            data_store: DataStore for persistence.
            config: Default trading configuration for new sessions.
        """
        self._factory = signal_generator_factory
        self._series_provider = series_provider
        self._data_store = data_store
        self._config = config or BacktestConfig()
        self._sessions: dict[str, PaperTradingEngine] = {}

        logger.info("paper_trading_manager_initialized")

    async def start_session(
        self,
        strategy: Strategy,
        mode: PaperTradingMode,
        config: BacktestConfig | None = None,
    ) -> PaperTradingStatus:
        """Start a new paper trading session for a strategy.

        Creates a new PaperTradingEngine and starts it. Only one
        session per strategy is allowed.

        Args:
            strategy: The strategy to paper trade.
            mode: Paper trading mode (SIMULATED or LIVE).
            config: Optional config override for this session.

        Returns:
            Initial PaperTradingStatus.

        Raises:
            PaperTradingError: If strategy already has an active session.
        """
        if strategy.id in self._sessions:
            existing = self._sessions[strategy.id]
            if existing.is_running:
                raise PaperTradingError(
                    strategy_id=strategy.id,
                    reason="Strategy already has an active paper trading session",
                )
            # Remove stale session
            del self._sessions[strategy.id]

        engine = PaperTradingEngine(
            strategy=strategy,
            signal_generator_factory=self._factory,
            series_provider=self._series_provider,
            mode=mode,
            config=config or self._config,
        )

        self._sessions[strategy.id] = engine

        logger.info(
            "paper_trading_session_starting",
            strategy_id=strategy.id,
            mode=mode.value,
        )

        await engine.start()

        return engine.get_status()

    async def stop_session(self, strategy_id: str) -> PaperTradingStatus:
        """Stop a running paper trading session.

        Args:
            strategy_id: ID of the strategy to stop.

        Returns:
            Final PaperTradingStatus.

        Raises:
            PaperTradingError: If no session exists for the strategy.
        """
        if strategy_id not in self._sessions:
            raise PaperTradingError(
                strategy_id=strategy_id,
                reason="No paper trading session found for strategy",
            )

        engine = self._sessions[strategy_id]
        await engine.stop()

        status = engine.get_status()

        # Persist results
        try:
            strategy = self._data_store.get_strategy(strategy_id)
            if strategy:
                strategy.paper_results = engine.get_state_snapshot()
                self._data_store.save_strategy(strategy)
                logger.info("paper_trading_results_persisted", strategy_id=strategy_id)
            else:
                logger.warning("strategy_not_found_for_persistence", strategy_id=strategy_id)
        except Exception as exc:
            logger.error(
                "paper_trading_persistence_failed",
                strategy_id=strategy_id,
                error=str(exc)
            )

        logger.info(
            "paper_trading_session_stopped",
            strategy_id=strategy_id,
            num_trades=status.num_trades,
        )

        return status

    def get_session_status(self, strategy_id: str) -> PaperTradingStatus | None:
        """Get the status of a paper trading session.

        Args:
            strategy_id: ID of the strategy to check.

        Returns:
            PaperTradingStatus if session exists, None otherwise.
        """
        engine = self._sessions.get(strategy_id)
        if engine is None:
            return None
        return engine.get_status()

    def get_all_sessions(self) -> list[PaperTradingStatus]:
        """Get status of all paper trading sessions.

        Returns:
            List of PaperTradingStatus for all known sessions.
        """
        return [engine.get_status() for engine in self._sessions.values()]

    def get_session_trades(self, strategy_id: str) -> list[dict[str, Any]]:
        """Get trade log for a specific session.

        Args:
            strategy_id: ID of the strategy.

        Returns:
            List of trade record dictionaries.

        Raises:
            PaperTradingError: If no session exists.
        """
        engine = self._sessions.get(strategy_id)
        if engine is None:
            raise PaperTradingError(
                strategy_id=strategy_id,
                reason="No paper trading session found",
            )
        return engine.get_trade_log()

    def get_session_equity_curve(self, strategy_id: str) -> list[dict[str, Any]]:
        """Get equity curve for a specific session.

        Args:
            strategy_id: ID of the strategy.

        Returns:
            List of equity point dictionaries.

        Raises:
            PaperTradingError: If no session exists.
        """
        engine = self._sessions.get(strategy_id)
        if engine is None:
            raise PaperTradingError(
                strategy_id=strategy_id,
                reason="No paper trading session found",
            )
        return engine.get_equity_curve()

    def validate_session(
        self,
        strategy_id: str,
        thresholds: PaperTradingThresholds | None = None,
    ) -> tuple[bool, list[str]]:
        """Validate a paper trading session against thresholds.

        Args:
            strategy_id: ID of the strategy to validate.
            thresholds: Validation thresholds. Uses defaults if None.

        Returns:
            Tuple of (passed: bool, errors: list[str]).

        Raises:
            PaperTradingError: If no session exists.
        """
        engine = self._sessions.get(strategy_id)
        if engine is None:
            raise PaperTradingError(
                strategy_id=strategy_id,
                reason="No paper trading session found for validation",
            )

        return PaperTradingValidator.validate(engine, thresholds)

    def get_session_snapshot(self, strategy_id: str) -> dict[str, Any] | None:
        """Get state snapshot for persistence.

        Args:
            strategy_id: ID of the strategy.

        Returns:
            State snapshot dictionary, or None if no session.
        """
        engine = self._sessions.get(strategy_id)
        if engine is None:
            return None
        return engine.get_state_snapshot()

    def remove_session(self, strategy_id: str) -> None:
        """Remove a completed session from tracking.

        Args:
            strategy_id: ID of the strategy session to remove.
        """
        if strategy_id in self._sessions:
            del self._sessions[strategy_id]
            logger.info(
                "paper_trading_session_removed",
                strategy_id=strategy_id,
            )
