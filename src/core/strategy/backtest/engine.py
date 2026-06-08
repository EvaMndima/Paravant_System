"""Backtest engine — core orchestrator for historical strategy simulation.

Runs a strategy's signal generator over historical OHLCV data, simulates
trades with realistic fills, and computes comprehensive performance metrics.

Critical Invariants:
    1. Determinism: same inputs MUST produce identical outputs.
    2. No lookahead: signal at bar[i] uses data up to bar[i], fills at bar[i+1] open.
    3. No floating-point randomness: consistent rounding, no dict ordering issues.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-007 - Input validation at boundaries
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-02-14-001 - Strategy status transitions follow strict state machine
"""
from __future__ import annotations

from src.core.exceptions import BacktestError
from src.core.strategy.backtest.metrics import BacktestMetricsCalculator
from src.core.strategy.backtest.portfolio import PortfolioState
from src.core.strategy.backtest.result import BacktestResult
from src.core.strategy.backtest.trader import SimulatedTrader
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.backtest.validator import BacktestValidator, ValidationThresholds
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import OHLCVSeries
from src.data.models import Strategy
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BacktestEngine:
    """Core backtest engine for historical strategy simulation.

    Orchestrates the full backtest lifecycle:
    1. Validate inputs (strategy, data, config)
    2. Create signal generator from factory
    3. Initialize portfolio
    4. Iterate bars chronologically, generating signals and executing trades
    5. Force-close any open position at end
    6. Calculate metrics
    7. Validate against thresholds
    8. Return complete BacktestResult

    Example:
        >>> engine = BacktestEngine(factory)
        >>> result = engine.run_backtest(strategy, series)
        >>> print(result.summary())
    """

    def __init__(
        self,
        signal_generator_factory: SignalGeneratorFactory,
    ) -> None:
        """Initialize backtest engine with dependencies.

        Args:
            signal_generator_factory: Factory for creating signal generators.
        """
        self._factory = signal_generator_factory
        self._trader = SimulatedTrader()

    def run_backtest(
        self,
        strategy: Strategy,
        series: OHLCVSeries,
        config: BacktestConfig | None = None,
        thresholds: ValidationThresholds | None = None,
        lookback_window: int | None = None,
    ) -> BacktestResult:
        """Run a full backtest simulation.

        This is the main entry point. Synchronous — no async needed
        since backtesting is purely computational.

        Args:
            strategy: The strategy to backtest (must have template_id).
            series: Historical OHLCV data for the target symbol/timeframe.
            config: Backtest configuration. Uses defaults if None.
            thresholds: Validation thresholds. Uses defaults if None.
            lookback_window: PERFORMANCE option. If None (default), each bar's
                signal is generated from the FULL history up to that bar — the
                original behavior, unchanged. If set, only the trailing
                ``max(lookback_window, min_bars)`` bars are passed to the
                generator, collapsing the per-bar indicator recomputation from
                O(i) to O(window) and the whole loop from O(n^2) to O(n).
                SAFE ONLY for strategies whose indicators are bounded-lookback or
                exponentially-converging (EMA/MACD/RSI/ADX/BB/Ichimoku); strategies
                with inception-cumulative indicators (VPT running sum, Heikin-Ashi
                recursion) MUST use None. Equivalence with the full-history result
                is verified per strategy by
                ``tests/unit/backtest/test_window_equivalence.py``.
                Decision: DEC-2026-06-04-015.

        Returns:
            Complete BacktestResult with metrics and validation status.

        Raises:
            BacktestError: If strategy lacks template_id, series has
                insufficient data, or simulation fails unexpectedly.
        """
        if config is None:
            config = BacktestConfig()

        # --- 1. Validate inputs ---
        self._validate_inputs(strategy, series)

        # --- 2. Create signal generator ---
        try:
            generator = self._factory.get_generator(strategy.template_id)
        except Exception as exc:
            raise BacktestError(
                strategy_id=strategy.id,
                reason=f"Failed to create signal generator: {exc}",
            ) from exc

        min_bars = generator.min_bars_required

        if len(series) < min_bars + 2:
            # Need at least min_bars for warmup + 1 signal bar + 1 fill bar
            raise BacktestError(
                strategy_id=strategy.id,
                reason=(
                    f"Insufficient data: need {min_bars + 2} bars, "
                    f"have {len(series)}"
                ),
            )

        logger.info(
            "backtest_started",
            strategy_id=strategy.id,
            strategy_name=strategy.name,
            template_id=strategy.template_id,
            symbol=series.symbol,
            timeframe=series.timeframe,
            num_bars=len(series),
            initial_capital=config.initial_capital,
        )

        # --- 3. Initialize portfolio ---
        portfolio = PortfolioState(config.initial_capital)

        # --- 4. Main simulation loop ---
        # Iterate from warmup bar to second-to-last bar
        # Signal at bar[i] -> fill at bar[i+1]
        #
        # Performance: when lookback_window is set, pass only a bounded TRAILING
        # window to the generator instead of the full 0..i history, so each step
        # recomputes indicators over O(window) bars rather than O(i) -- collapsing
        # the loop from O(n^2) to O(n). lookback_window=None preserves the exact
        # original full-history behavior. The window is clamped to at least
        # min_bars so the generator always has its required warmup. Equivalence is
        # verified per strategy in tests/unit/backtest/test_window_equivalence.py
        # (Decision: DEC-2026-06-04-015).
        effective_window = (
            None if lookback_window is None else max(lookback_window, min_bars)
        )
        try:
            for i in range(min_bars - 1, len(series) - 1):
                # Check stop-loss / take-profit on current bar before signals
                self._trader.check_stop_take_profit(
                    portfolio=portfolio,
                    bar=series[i],
                    config=config,
                )

                # Slice series up to and including bar[i] — no lookahead. With a
                # window, start from i+1-window (still no lookahead; only older
                # bars beyond the converged indicator horizon are dropped).
                start = 0 if effective_window is None else max(0, i + 1 - effective_window)
                visible_series = series.slice(start, i + 1)

                # Generate signal using only visible data
                signal = generator.generate(
                    visible_series,
                    strategy.parameters,
                    series.symbol,
                )

                # Execute signal at next bar's open
                if signal is not None:
                    next_bar = series[i + 1]
                    self._trader.execute_signal(
                        signal=signal,
                        portfolio=portfolio,
                        next_bar=next_bar,
                        config=config,
                    )

                # Record equity at current bar's close
                current_close = series[i].close
                portfolio.record_equity(
                    timestamp=series[i].timestamp,
                    current_price=current_close,
                )
        except BacktestError:
            raise
        except Exception as exc:
            raise BacktestError(
                strategy_id=strategy.id,
                reason=f"Simulation failed at bar {i}: {exc}",
            ) from exc

        # Record equity for the last bar
        last_bar = series[-1]
        portfolio.record_equity(
            timestamp=last_bar.timestamp,
            current_price=last_bar.close,
        )

        # --- 5. Force-close any remaining position ---
        self._trader.force_close_at_price(
            portfolio=portfolio,
            price=last_bar.close,
            timestamp=last_bar.timestamp,
            config=config,
        )

        # --- 6. Calculate metrics ---
        metrics = BacktestMetricsCalculator.calculate(
            trades=portfolio.trade_log,
            equity_points=portfolio.equity_curve,
            initial_capital=config.initial_capital,
            config=config,
        )

        # --- 7. Validate ---
        passed, errors = BacktestValidator.validate(
            BacktestResult(
                strategy_id=strategy.id,
                strategy_name=strategy.name,
                template_id=strategy.template_id,
                symbol=series.symbol,
                timeframe=series.timeframe,
                start_date=series[0].timestamp,
                end_date=last_bar.timestamp,
                initial_capital=config.initial_capital,
                final_capital=portfolio.cash,
                metrics=metrics,
            ),
            thresholds,
        )

        # --- 8. Build final result ---
        result = BacktestResult(
            strategy_id=strategy.id,
            strategy_name=strategy.name,
            template_id=strategy.template_id,
            symbol=series.symbol,
            timeframe=series.timeframe,
            start_date=series[0].timestamp,
            end_date=last_bar.timestamp,
            initial_capital=config.initial_capital,
            final_capital=portfolio.cash,
            metrics=metrics,
            equity_curve=portfolio.equity_curve,
            trade_log=portfolio.trade_log,
            config=config,
            passed_validation=passed,
            validation_errors=errors,
        )

        logger.info(
            "backtest_completed",
            strategy_id=strategy.id,
            total_trades=metrics.total_trades,
            total_return_pct=metrics.total_return_pct,
            sharpe_ratio=metrics.sharpe_ratio,
            max_drawdown_pct=metrics.max_drawdown_pct,
            passed=passed,
        )

        return result

    def _validate_inputs(
        self,
        strategy: Strategy,
        series: OHLCVSeries,
    ) -> None:
        """Validate backtest inputs.

        Args:
            strategy: Strategy to validate.
            series: OHLCV series to validate.

        Raises:
            BacktestError: If inputs are invalid.
        """
        if not strategy.template_id:
            raise BacktestError(
                strategy_id=strategy.id if strategy.id else "",
                reason="Strategy must have a template_id for backtesting",
            )

        if len(series) < 2:
            raise BacktestError(
                strategy_id=strategy.id if strategy.id else "",
                reason=f"Need at least 2 bars, have {len(series)}",
            )
