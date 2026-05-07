"""Simulated portfolio state for backtesting.

Tracks cash, open positions, and equity curve during a backtest run.
This is the only mutable class in the backtest package — it maintains
running state that changes bar-by-bar during simulation.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-007 - Input validation at boundaries
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from src.core.strategy.backtest.types import EquityPoint, TradeRecord
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OpenPosition:
    """An open simulated position.

    Mutable only for tracking — once closed, the position is converted
    into an immutable TradeRecord.

    Attributes:
        symbol: Trading pair symbol.
        direction: Entry signal direction (LONG or SHORT).
        quantity: Position size in base asset.
        entry_price: Fill price at entry (after slippage).
        entry_commission: Commission paid at entry in USDT.
        entry_slippage: Slippage cost at entry in USDT.
        entry_time: Timezone-aware UTC entry timestamp.
        stop_loss: Stop loss price level (None if not set).
        take_profit: Take profit price level (None if not set).
        trail_distance: Fixed trailing distance in price units. When set,
            stop_loss ratchets in the favorable direction each bar.
            Computed automatically at open when stop_loss is set but
            take_profit is not (trend-following strategies).
    """

    symbol: str
    direction: SignalDirection
    quantity: float
    entry_price: float
    entry_commission: float
    entry_slippage: float
    entry_time: datetime
    stop_loss: float | None = None
    take_profit: float | None = None
    trail_distance: float | None = None


class PortfolioState:
    """Simulated portfolio tracking for bar-by-bar backtesting.

    Tracks cash balance, an optional open position, and records equity
    snapshots for building the equity curve. Enforces no-leverage
    (position cost cannot exceed available cash) and single-position
    (only one open position at a time).

    Attributes:
        initial_capital: Starting portfolio value.
        cash: Current cash balance.
        equity_curve: List of equity snapshots taken at each bar.
    """

    def __init__(self, initial_capital: float) -> None:
        """Initialize portfolio with starting capital.

        Args:
            initial_capital: Starting cash value in USDT.

        Raises:
            ValueError: If initial_capital is not positive or finite.
        """
        if math.isnan(initial_capital) or math.isinf(initial_capital):
            raise ValueError(
                f"initial_capital must be finite, got {initial_capital}"
            )
        if initial_capital <= 0:
            raise ValueError(
                f"initial_capital must be positive, got {initial_capital}"
            )

        self.initial_capital = initial_capital
        self.cash = initial_capital
        self._position: OpenPosition | None = None
        self.equity_curve: list[EquityPoint] = []
        self._trade_log: list[TradeRecord] = []

        logger.debug(
            "portfolio_initialized",
            initial_capital=initial_capital,
        )

    @property
    def position(self) -> OpenPosition | None:
        """Current open position, if any.

        Returns:
            The open position or None.
        """
        return self._position

    @property
    def trade_log(self) -> list[TradeRecord]:
        """All completed trades.

        Returns:
            List of completed trade records.
        """
        return list(self._trade_log)

    def has_position(self) -> bool:
        """Check if there is an open position.

        Returns:
            True if a position is currently open.
        """
        return self._position is not None

    def open_position(
        self,
        symbol: str,
        direction: SignalDirection,
        quantity: float,
        fill_price: float,
        commission: float,
        slippage_cost: float,
        timestamp: datetime,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> None:
        """Open a new simulated position.

        Deducts position cost and commission from cash. Enforces
        single-position and no-leverage constraints.

        Args:
            symbol: Trading pair symbol.
            direction: Entry direction (LONG or SHORT).
            quantity: Position size in base asset.
            fill_price: Fill price after slippage.
            commission: Commission in USDT.
            slippage_cost: Slippage cost in USDT.
            timestamp: Timezone-aware UTC entry timestamp.
            stop_loss: Stop loss price level (None if not set).
            take_profit: Take profit price level (None if not set).

        Raises:
            ValueError: If a position is already open, or if cost
                exceeds available cash.
        """
        if self._position is not None:
            raise ValueError(
                f"Cannot open position: already have position in "
                f"{self._position.symbol}"
            )

        total_cost = quantity * fill_price + commission
        if total_cost > self.cash:
            raise ValueError(
                f"Insufficient cash for position: need {total_cost:.2f}, "
                f"have {self.cash:.2f}"
            )

        self.cash -= total_cost

        # Auto-enable trailing stop for trend-following strategies:
        # if stop_loss is set but take_profit is not, the initial
        # stop distance becomes the trailing distance.
        trail_distance: float | None = None
        if stop_loss is not None and take_profit is None:
            trail_distance = abs(fill_price - stop_loss)

        self._position = OpenPosition(
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            entry_price=fill_price,
            entry_commission=commission,
            entry_slippage=slippage_cost,
            entry_time=timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trail_distance=trail_distance,
        )

        logger.debug(
            "position_opened",
            symbol=symbol,
            direction=direction.value,
            quantity=quantity,
            fill_price=fill_price,
            commission=commission,
            stop_loss=stop_loss,
            take_profit=take_profit,
            cash_remaining=self.cash,
        )

    def close_position(
        self,
        fill_price: float,
        commission: float,
        slippage_cost: float,
        timestamp: datetime,
    ) -> TradeRecord:
        """Close the current open position and record the trade.

        Calculates realized P&L, returns proceeds to cash, and creates
        an immutable TradeRecord.

        Args:
            fill_price: Exit fill price after slippage.
            commission: Exit commission in USDT.
            slippage_cost: Exit slippage cost in USDT.
            timestamp: Timezone-aware UTC exit timestamp.

        Returns:
            Completed TradeRecord with realized P&L.

        Raises:
            ValueError: If no position is currently open.
        """
        if self._position is None:
            raise ValueError("Cannot close position: no open position")

        pos = self._position

        # Calculate P&L based on direction
        if pos.direction == SignalDirection.LONG:
            gross_pnl = (fill_price - pos.entry_price) * pos.quantity
        else:
            # SHORT: profit when price goes down
            gross_pnl = (pos.entry_price - fill_price) * pos.quantity

        total_commission = pos.entry_commission + commission
        total_slippage = pos.entry_slippage + slippage_cost
        realized_pnl = gross_pnl - total_commission

        # Calculate return percentage based on entry value
        entry_value = pos.entry_price * pos.quantity
        return_pct = (realized_pnl / entry_value) * 100.0 if entry_value > 0 else 0.0

        # Return proceeds to cash (entry value + P&L - exit commission)
        proceeds = pos.quantity * fill_price - commission
        self.cash += proceeds

        trade = TradeRecord(
            entry_time=pos.entry_time,
            exit_time=timestamp,
            symbol=pos.symbol,
            direction=pos.direction,
            entry_price=pos.entry_price,
            exit_price=fill_price,
            quantity=pos.quantity,
            entry_commission=pos.entry_commission,
            exit_commission=commission,
            slippage_cost=total_slippage,
            realized_pnl=realized_pnl,
            return_pct=return_pct,
        )

        self._trade_log.append(trade)
        self._position = None

        logger.debug(
            "position_closed",
            symbol=pos.symbol,
            realized_pnl=realized_pnl,
            return_pct=return_pct,
            cash_after=self.cash,
        )

        return trade

    def get_total_value(self, current_price: float) -> float:
        """Calculate total portfolio value (cash + position mark-to-market).

        Args:
            current_price: Current market price for open position valuation.

        Returns:
            Total portfolio value in USDT.
        """
        position_value = 0.0
        if self._position is not None:
            if self._position.direction == SignalDirection.LONG:
                position_value = self._position.quantity * current_price
            else:
                # SHORT position: value = entry_value + (entry_price - current) * qty
                entry_value = self._position.quantity * self._position.entry_price
                unrealized = (self._position.entry_price - current_price) * self._position.quantity
                position_value = entry_value + unrealized

        return self.cash + position_value

    def get_position_value(self, current_price: float) -> float:
        """Get the mark-to-market value of the open position.

        Args:
            current_price: Current market price.

        Returns:
            Position value in USDT, or 0.0 if no position is open.
        """
        if self._position is None:
            return 0.0

        if self._position.direction == SignalDirection.LONG:
            return self._position.quantity * current_price
        else:
            entry_value = self._position.quantity * self._position.entry_price
            unrealized = (self._position.entry_price - current_price) * self._position.quantity
            return entry_value + unrealized

    def record_equity(self, timestamp: datetime, current_price: float) -> EquityPoint:
        """Record an equity curve snapshot at the current bar.

        Args:
            timestamp: Timezone-aware UTC timestamp of the bar.
            current_price: Current market price for position valuation.

        Returns:
            The recorded EquityPoint.
        """
        position_value = self.get_position_value(current_price)
        total_equity = self.cash + position_value

        point = EquityPoint(
            timestamp=timestamp,
            equity=total_equity,
            cash=self.cash,
            position_value=position_value,
        )
        self.equity_curve.append(point)
        return point
