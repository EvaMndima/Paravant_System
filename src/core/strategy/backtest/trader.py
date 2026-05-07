"""Simulated order execution for backtesting.

Handles fill price calculation with slippage and commission modeling.
Critical invariant: fills always use next bar open price (never current
bar close) to prevent lookahead bias.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-007 - Input validation at boundaries
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

from datetime import datetime

from src.core.strategy.backtest.portfolio import PortfolioState
from src.core.strategy.backtest.types import BacktestConfig, TradeRecord
from src.core.strategy.signals import TradingSignal
from src.data.market_data import OHLCV
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SimulatedTrader:
    """Simulates order execution with realistic fill modeling.

    Fills orders at the next bar's open price with configurable slippage
    and commission costs. Enforces no-lookahead by requiring the next bar
    (not the signal bar) for fill price computation.

    Example:
        >>> trader = SimulatedTrader()
        >>> trade = trader.execute_signal(
        ...     signal=signal,
        ...     portfolio=portfolio,
        ...     next_bar=next_bar,
        ...     config=config,
        ... )
    """

    def execute_signal(
        self,
        signal: TradingSignal,
        portfolio: PortfolioState,
        next_bar: OHLCV,
        config: BacktestConfig,
    ) -> TradeRecord | None:
        """Execute a trading signal against the simulated portfolio.

        For LONG signals: opens a buy position if none exists.
        For SHORT signals: opens a short position if none exists.
        For CLOSE signals: closes the current position if one exists.

        If a LONG/SHORT signal arrives while a position is open in the
        opposite direction, the existing position is first closed, then
        the new one opened. If the signal matches the current position
        direction, it is ignored (already positioned).

        Args:
            signal: The trading signal to execute.
            portfolio: Current portfolio state.
            next_bar: The next bar after the signal bar (for fill price).
            config: Backtest configuration with commission/slippage rates.

        Returns:
            A TradeRecord if a position was closed (completing a round-trip),
            or None if only a position was opened.
        """
        closed_trade: TradeRecord | None = None

        if signal.direction == SignalDirection.CLOSE:
            if portfolio.has_position():
                closed_trade = self._close_position(
                    portfolio, next_bar, config
                )
            else:
                logger.debug(
                    "close_signal_ignored",
                    reason="no_open_position",
                    symbol=signal.symbol,
                )
            return closed_trade

        # LONG or SHORT signal
        if portfolio.has_position():
            pos = portfolio.position
            if pos is not None and pos.direction == signal.direction:
                # Already positioned in same direction — skip
                logger.debug(
                    "signal_ignored",
                    reason="already_positioned",
                    direction=signal.direction.value,
                    symbol=signal.symbol,
                )
                return None

            # Close existing position before opening new one
            closed_trade = self._close_position(
                portfolio, next_bar, config
            )

        # Open new position
        self._open_position(signal, portfolio, next_bar, config)
        return closed_trade

    def _calculate_fill_price(
        self,
        base_price: float,
        direction: SignalDirection,
        slippage_rate: float,
    ) -> tuple[float, float]:
        """Calculate fill price and slippage cost.

        For buys: price slips UP (unfavorable).
        For sells/closes: price slips DOWN (unfavorable).

        Args:
            base_price: Next bar open price (or close for force-close).
            direction: Trade direction for slippage direction.
            slippage_rate: Slippage fraction from config.

        Returns:
            Tuple of (fill_price, slippage_cost_per_unit).
        """
        if direction == SignalDirection.LONG:
            # Buying: price slips up
            fill_price = base_price * (1.0 + slippage_rate)
        else:
            # Selling/shorting/closing: price slips down
            fill_price = base_price * (1.0 - slippage_rate)

        slippage_per_unit = abs(fill_price - base_price)
        return fill_price, slippage_per_unit

    def _open_position(
        self,
        signal: TradingSignal,
        portfolio: PortfolioState,
        next_bar: OHLCV,
        config: BacktestConfig,
    ) -> None:
        """Open a new position based on the signal.

        Calculates quantity from position size percentage of current equity,
        applies slippage and commission, and opens the position.

        Args:
            signal: The entry signal.
            portfolio: Current portfolio state.
            next_bar: Next bar for fill price.
            config: Backtest configuration.
        """
        fill_price, slippage_per_unit = self._calculate_fill_price(
            next_bar.open, signal.direction, config.slippage_rate
        )

        # Size position as percentage of available cash
        available = portfolio.cash * config.position_size_pct

        # Calculate max quantity we can afford (accounting for commission)
        # cost = qty * fill_price * (1 + commission_rate)
        # qty = available / (fill_price * (1 + commission_rate))
        max_quantity = available / (fill_price * (1.0 + config.commission_rate))

        if max_quantity <= 0:
            logger.debug(
                "position_skipped",
                reason="insufficient_funds",
                available=available,
                fill_price=fill_price,
            )
            return

        quantity = max_quantity
        commission = quantity * fill_price * config.commission_rate
        slippage_cost = slippage_per_unit * quantity

        portfolio.open_position(
            symbol=signal.symbol,
            direction=signal.direction,
            quantity=quantity,
            fill_price=fill_price,
            commission=commission,
            slippage_cost=slippage_cost,
            timestamp=next_bar.timestamp,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
        )

        logger.debug(
            "simulated_open",
            symbol=signal.symbol,
            direction=signal.direction.value,
            quantity=quantity,
            fill_price=fill_price,
            commission=commission,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
        )

    def _close_position(
        self,
        portfolio: PortfolioState,
        bar: OHLCV,
        config: BacktestConfig,
    ) -> TradeRecord:
        """Close the current open position.

        Args:
            portfolio: Portfolio with an open position.
            bar: The bar providing the close price (for exit fill).
            config: Backtest configuration for commission/slippage.

        Returns:
            Completed TradeRecord.

        Raises:
            ValueError: If no position is open (propagated from portfolio).
        """
        pos = portfolio.position
        if pos is None:
            raise ValueError("Cannot close: no open position")

        # For closing a long, we're selling (price slips down)
        # For closing a short, we're buying back (price slips up)
        close_direction = (
            SignalDirection.SHORT
            if pos.direction == SignalDirection.LONG
            else SignalDirection.LONG
        )

        fill_price, slippage_per_unit = self._calculate_fill_price(
            bar.open, close_direction, config.slippage_rate
        )

        commission = pos.quantity * fill_price * config.commission_rate
        slippage_cost = slippage_per_unit * pos.quantity

        trade = portfolio.close_position(
            fill_price=fill_price,
            commission=commission,
            slippage_cost=slippage_cost,
            timestamp=bar.timestamp,
        )

        logger.debug(
            "simulated_close",
            symbol=pos.symbol,
            fill_price=fill_price,
            realized_pnl=trade.realized_pnl,
            commission=commission,
        )

        return trade

    def force_close_at_price(
        self,
        portfolio: PortfolioState,
        price: float,
        timestamp: datetime,
        config: BacktestConfig,
    ) -> TradeRecord | None:
        """Force-close any open position at a specific price.

        Used at the end of a backtest to close remaining positions
        at the last bar's close price.

        Args:
            portfolio: Portfolio that may have an open position.
            price: The price to close at (typically last bar close).
            timestamp: Timezone-aware UTC timestamp.
            config: Backtest configuration for commission/slippage.

        Returns:
            TradeRecord if position was closed, None otherwise.
        """
        if not portfolio.has_position():
            return None

        pos = portfolio.position
        if pos is None:
            return None

        close_direction = (
            SignalDirection.SHORT
            if pos.direction == SignalDirection.LONG
            else SignalDirection.LONG
        )

        fill_price, slippage_per_unit = self._calculate_fill_price(
            price, close_direction, config.slippage_rate
        )

        commission = pos.quantity * fill_price * config.commission_rate
        slippage_cost = slippage_per_unit * pos.quantity

        trade = portfolio.close_position(
            fill_price=fill_price,
            commission=commission,
            slippage_cost=slippage_cost,
            timestamp=timestamp,
        )

        logger.debug(
            "force_close",
            symbol=pos.symbol,
            fill_price=fill_price,
            realized_pnl=trade.realized_pnl,
        )

        return trade

    def check_stop_take_profit(
        self,
        portfolio: PortfolioState,
        bar: OHLCV,
        config: BacktestConfig,
    ) -> TradeRecord | None:
        """Check if current bar triggers stop-loss or take-profit.

        Uses intrabar high/low to detect if price crossed stop or TP
        levels. When both are hit in the same bar (extreme volatility),
        stop-loss takes priority — conservative worst-case assumption.

        For LONG positions:
          - Stop hit when bar.low <= stop_loss
          - TP hit when bar.high >= take_profit

        For SHORT positions:
          - Stop hit when bar.high >= stop_loss
          - TP hit when bar.low <= take_profit

        Args:
            portfolio: Portfolio with potential open position.
            bar: Current OHLCV bar with high/low for intrabar check.
            config: Backtest configuration for commission/slippage.

        Returns:
            TradeRecord if stop or TP triggered, None otherwise.
        """
        if not portfolio.has_position():
            return None

        pos = portfolio.position
        if pos is None:
            return None

        # --- Trailing stop ratchet (before hit check) ---
        # When trail_distance is set, move stop in the favorable direction
        # based on the bar's extreme. The stop can only tighten, never widen.
        if pos.trail_distance is not None and pos.stop_loss is not None:
            if pos.direction == SignalDirection.LONG:
                new_stop = bar.high - pos.trail_distance
                if new_stop > pos.stop_loss:
                    logger.debug(
                        "trailing_stop_ratcheted",
                        symbol=pos.symbol,
                        direction="long",
                        old_stop=pos.stop_loss,
                        new_stop=new_stop,
                        bar_high=bar.high,
                    )
                    pos.stop_loss = new_stop
            else:
                new_stop = bar.low + pos.trail_distance
                if new_stop < pos.stop_loss:
                    logger.debug(
                        "trailing_stop_ratcheted",
                        symbol=pos.symbol,
                        direction="short",
                        old_stop=pos.stop_loss,
                        new_stop=new_stop,
                        bar_low=bar.low,
                    )
                    pos.stop_loss = new_stop

        # --- Check stop-loss and take-profit hits ---
        stop_hit = False
        tp_hit = False
        exit_price = 0.0

        if pos.direction == SignalDirection.LONG:
            if pos.stop_loss is not None and bar.low <= pos.stop_loss:
                stop_hit = True
                exit_price = pos.stop_loss
            if pos.take_profit is not None and bar.high >= pos.take_profit:
                tp_hit = True
                if not stop_hit:
                    exit_price = pos.take_profit
        else:
            # SHORT position
            if pos.stop_loss is not None and bar.high >= pos.stop_loss:
                stop_hit = True
                exit_price = pos.stop_loss
            if pos.take_profit is not None and bar.low <= pos.take_profit:
                tp_hit = True
                if not stop_hit:
                    exit_price = pos.take_profit

        if not stop_hit and not tp_hit:
            return None

        # Stop takes priority over TP (worst-case assumption)
        exit_reason = "stop_loss" if stop_hit else "take_profit"

        # Apply slippage to exit price
        close_direction = (
            SignalDirection.SHORT
            if pos.direction == SignalDirection.LONG
            else SignalDirection.LONG
        )
        fill_price, slippage_per_unit = self._calculate_fill_price(
            exit_price, close_direction, config.slippage_rate
        )

        commission = pos.quantity * fill_price * config.commission_rate
        slippage_cost = slippage_per_unit * pos.quantity

        trade = portfolio.close_position(
            fill_price=fill_price,
            commission=commission,
            slippage_cost=slippage_cost,
            timestamp=bar.timestamp,
        )

        logger.info(
            "stop_tp_triggered",
            reason=exit_reason,
            symbol=pos.symbol,
            direction=pos.direction.value,
            exit_price=fill_price,
            realized_pnl=trade.realized_pnl,
            stop_loss=pos.stop_loss,
            take_profit=pos.take_profit,
        )

        return trade
