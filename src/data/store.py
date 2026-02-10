"""DataStore class for type-safe database operations.

This module provides a high-level interface for all database operations,
implementing the repository pattern with type-safe methods.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from typing import Generator, Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, joinedload

from .database import engine
from ..utils.logging import get_logger, LogContext
from .models import (
    Account,
    AccountStatus,
    Strategy,
    StrategyStatus,
    Order,
    OrderStatus,
    Position,
    PositionStatus,
    Trade,
    PnLRecord,
    EquitySnapshot,
    SystemState,
    AuditLog,
    StrategyAssignment,
    Signal,
)


class DataStore:
    """Central data access layer with type-safe operations.

    Implements the repository pattern, providing CRUD operations for all models.
    Uses context managers for safe session handling.

    Example:
        ```python
        store = DataStore()

        # Create an account
        account = Account(
            name="Main Trading Account",
            balance_usdt=10000.0,
            equity_usdt=10000.0
        )
        store.save_account(account)

        # Query accounts
        active_accounts = store.get_accounts_by_status(AccountStatus.ACTIVE)
        ```
    """

    def __init__(self) -> None:
        """Initialize the DataStore."""
        self.engine = engine
        self.logger = get_logger(__name__)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Create a new database session context.

        Yields:
            Session: SQLAlchemy session for database operations

        Example:
            ```python
            with store.session() as session:
                account = session.query(Account).first()
                account.balance_usdt = 15000.0
                session.commit()
            ```
        """
        session = Session(self.engine)
        try:
            yield session
            session.commit()
        except Exception as e:
            self.logger.error("database_transaction_error", error=str(e), exc_info=True)
            session.rollback()
            raise
        finally:
            session.close()

    # =========================================================================
    # ACCOUNT OPERATIONS
    # =========================================================================

    def save_account(self, account: Account) -> Account:
        """Save or update an account.

        Args:
            account: Account instance to save

        Returns:
            The saved account with updated fields
        """
        with self.session() as session:
            session.add(account)
            session.flush()
            session.refresh(account)
            session.expunge(account)  # Detach with loaded attributes
            return account

    def get_account(self, account_id: str) -> Account | None:
        """Get an account by ID.

        Args:
            account_id: The account ID

        Returns:
            Account if found, None otherwise
        """
        with self.session() as session:
            account = session.get(Account, account_id)
            if account:
                session.expunge(account)  # Detach with loaded attributes
            return account

    def get_all_accounts(self) -> list[Account]:
        """Get all accounts.

        Returns:
            List of all accounts
        """
        with self.session() as session:
            stmt = select(Account)
            accounts = list(session.scalars(stmt).all())
            for acc in accounts:
                session.expunge(acc)  # Detach with loaded attributes
            return accounts

    def get_accounts_by_status(self, status: AccountStatus) -> list[Account]:
        """Get accounts by status.

        Args:
            status: The account status to filter by

        Returns:
            List of accounts with the given status
        """
        with self.session() as session:
            stmt = select(Account).where(Account.status == status)
            accounts = list(session.scalars(stmt).all())
            for acc in accounts:
                session.expunge(acc)  # Detach with loaded attributes
            return accounts

    def get_active_accounts(self) -> list[Account]:
        """Get all active accounts.

        Returns:
            List of active accounts
        """
        return self.get_accounts_by_status(AccountStatus.ACTIVE)

    # =========================================================================
    # STRATEGY OPERATIONS
    # =========================================================================

    def save_strategy(self, strategy: Strategy) -> Strategy:
        """Save or update a strategy.

        Args:
            strategy: Strategy instance to save

        Returns:
            The saved strategy with updated fields
        """
        with self.session() as session:
            session.add(strategy)
            session.flush()
            session.refresh(strategy)
            self.logger.info(
                "strategy_saved",
                strategy_id=strategy.id,
                name=strategy.name,
                status=strategy.status
            )
            session.expunge(strategy)  # Detach with loaded attributes
            return strategy

    def get_strategy(self, strategy_id: str) -> Strategy | None:
        """Get a strategy by ID.

        Args:
            strategy_id: The strategy ID

        Returns:
            Strategy if found, None otherwise
        """
        with self.session() as session:
            strategy = session.get(Strategy, strategy_id)
            if strategy:
                session.expunge(strategy)  # Detach with loaded attributes
            return strategy

    def get_strategies_by_status(self, status: StrategyStatus) -> list[Strategy]:
        """Get strategies by status.

        Args:
            status: The strategy status to filter by

        Returns:
            List of strategies with the given status
        """
        with self.session() as session:
            stmt = select(Strategy).where(Strategy.status == status)
            strategies = list(session.scalars(stmt).all())
            for strat in strategies:
                session.expunge(strat)  # Detach with loaded attributes
            return strategies

    def get_active_strategies(self) -> list[Strategy]:
        """Get all strategies that are actively tradable (LIVE status).

        Returns:
            List of live strategies
        """
        return self.get_strategies_by_status(StrategyStatus.LIVE)

    def get_all_strategies(self) -> list[Strategy]:
        """Get all strategies.

        Returns:
            List of all strategies
        """
        with self.session() as session:
            stmt = select(Strategy)
            strategies = list(session.scalars(stmt).all())
            for strat in strategies:
                session.expunge(strat)  # Detach with loaded attributes
            return strategies

    # =========================================================================
    # ORDER OPERATIONS
    # =========================================================================

    def save_order(self, order: Order) -> Order:
        """Save or update an order.

        Args:
            order: Order instance to save

        Returns:
            The saved order with updated fields
        """
        with self.session() as session:
            session.add(order)
            session.flush()
            session.refresh(order)
            self.logger.info(
                "order_saved",
                order_id=order.id,
                symbol=order.symbol,
                side=order.side,
                status=order.status,
                quantity=order.quantity
            )
            session.expunge(order)  # Detach with loaded attributes
            return order

    def get_order(self, order_id: str) -> Order | None:
        """Get an order by ID.

        Args:
            order_id: The order ID

        Returns:
            Order if found, None otherwise
        """
        with self.session() as session:
            order = session.get(Order, order_id)
            if order:
                session.expunge(order)  # Detach with loaded attributes
            return order

    def get_orders_by_status(self, status: OrderStatus) -> list[Order]:
        """Get orders by status.

        Args:
            status: The order status to filter by

        Returns:
            List of orders with the given status
        """
        with self.session() as session:
            stmt = select(Order).where(Order.status == status)
            orders = list(session.scalars(stmt).all())
            for order in orders:
                session.expunge(order)  # Detach with loaded attributes
            return orders

    def get_pending_orders(self) -> list[Order]:
        """Get all pending orders (not yet filled or cancelled).

        Returns:
            List of pending orders with related data eagerly loaded
        """
        with self.session() as session:
            stmt = (
                select(Order)
                .where(Order.status.in_([OrderStatus.PENDING, OrderStatus.SUBMITTED]))
                .options(
                    selectinload(Order.account),
                    selectinload(Order.strategy),
                    selectinload(Order.trades)
                )
            )
            orders = list(session.scalars(stmt).all())
            for order in orders:
                session.expunge(order)  # Detach with loaded attributes
            return orders

    def get_orders_for_account(self, account_id: str) -> list[Order]:
        """Get all orders for a specific account.

        Args:
            account_id: The account ID

        Returns:
            List of orders for the account with related data eagerly loaded
        """
        with self.session() as session:
            stmt = (
                select(Order)
                .where(Order.account_id == account_id)
                .options(
                    selectinload(Order.strategy),
                    selectinload(Order.trades)
                )
            )
            orders = list(session.scalars(stmt).all())
            for order in orders:
                session.expunge(order)  # Detach with loaded attributes
            return orders

    # =========================================================================
    # POSITION OPERATIONS
    # =========================================================================

    def save_position(self, position: Position) -> Position:
        """Save or update a position.

        Args:
            position: Position instance to save

        Returns:
            The saved position with updated fields
        """
        with self.session() as session:
            session.add(position)
            session.flush()
            session.refresh(position)
            session.expunge(position)  # Detach with loaded attributes
            return position

    def get_position(self, position_id: str) -> Position | None:
        """Get a position by ID.

        Args:
            position_id: The position ID

        Returns:
            Position if found, None otherwise
        """
        with self.session() as session:
            position = session.get(Position, position_id)
            if position:
                session.expunge(position)  # Detach with loaded attributes
            return position

    def get_open_positions(self, account_id: str | None = None) -> list[Position]:
        """Get all open positions, optionally filtered by account.

        Args:
            account_id: Optional account ID to filter by

        Returns:
            List of open positions with related account and strategy eagerly loaded
        """
        with self.session() as session:
            stmt = (
                select(Position)
                .where(Position.status == PositionStatus.OPEN)
                .options(
                    selectinload(Position.account),
                    selectinload(Position.strategy)
                )
            )
            if account_id:
                stmt = stmt.where(Position.account_id == account_id)
            positions = list(session.scalars(stmt).all())
            for pos in positions:
                session.expunge(pos)  # Detach with loaded attributes
            return positions

    def get_position_by_symbol(
        self, account_id: str, symbol: str
    ) -> Position | None:
        """Get an open position for a specific account and symbol.

        Args:
            account_id: The account ID
            symbol: The trading symbol (e.g., "BTCUSDT")

        Returns:
            Position if found, None otherwise
        """
        with self.session() as session:
            stmt = (
                select(Position)
                .where(Position.account_id == account_id)
                .where(Position.symbol == symbol)
                .where(Position.status == PositionStatus.OPEN)
            )
            position = session.scalars(stmt).first()
            if position:
                session.expunge(position)  # Detach with loaded attributes
            return position

    def get_positions_for_account(self, account_id: str) -> list[Position]:
        """Get all positions for a specific account.

        Args:
            account_id: The account ID

        Returns:
            List of positions for the account with related data eagerly loaded
        """
        with self.session() as session:
            stmt = (
                select(Position)
                .where(Position.account_id == account_id)
                .options(
                    selectinload(Position.strategy),
                    selectinload(Position.account)
                )
            )
            positions = list(session.scalars(stmt).all())
            for pos in positions:
                session.expunge(pos)  # Detach with loaded attributes
            return positions

    # =========================================================================
    # TRADE OPERATIONS
    # =========================================================================

    def save_trade(self, trade: Trade) -> Trade:
        """Save a trade record.

        Args:
            trade: Trade instance to save

        Returns:
            The saved trade with updated fields
        """
        with self.session() as session:
            session.add(trade)
            session.flush()
            session.refresh(trade)
            self.logger.info(
                "trade_saved",
                trade_id=trade.id,
                order_id=trade.order_id,
                symbol=trade.symbol,
                side=trade.side,
                price=trade.price,
                quantity=trade.quantity
            )
            session.expunge(trade)  # Detach with loaded attributes
            return trade

    def get_trade(self, trade_id: str) -> Trade | None:
        """Get a trade by ID.

        Args:
            trade_id: The trade ID

        Returns:
            Trade if found, None otherwise
        """
        with self.session() as session:
            trade = session.get(Trade, trade_id)
            if trade:
                session.expunge(trade)  # Detach with loaded attributes
            return trade

    def get_trades_for_order(self, order_id: str) -> list[Trade]:
        """Get all trades (fills) for an order.

        Args:
            order_id: The order ID

        Returns:
            List of trades for the order
        """
        with self.session() as session:
            stmt = select(Trade).where(Trade.order_id == order_id)
            trades = list(session.scalars(stmt).all())
            for trade in trades:
                session.expunge(trade)  # Detach with loaded attributes
            return trades

    def get_trades_for_account(
        self, account_id: str, start_date: datetime | None = None
    ) -> list[Trade]:
        """Get all trades for an account, optionally from a start date.

        Args:
            account_id: The account ID
            start_date: Optional start date to filter from

        Returns:
            List of trades for the account
        """
        with self.session() as session:
            stmt = select(Trade).where(Trade.account_id == account_id)
            if start_date:
                stmt = stmt.where(Trade.executed_at >= start_date)
            trades = list(session.scalars(stmt).all())
            for trade in trades:
                session.expunge(trade)  # Detach with loaded attributes
            return trades

    # =========================================================================
    # P&L OPERATIONS
    # =========================================================================

    def save_pnl_record(self, pnl_record: PnLRecord) -> PnLRecord:
        """Save a P&L record.

        Args:
            pnl_record: PnLRecord instance to save

        Returns:
            The saved P&L record with updated fields
        """
        with self.session() as session:
            session.add(pnl_record)
            session.flush()
            session.refresh(pnl_record)
            session.expunge(pnl_record)  # Detach with loaded attributes
            return pnl_record

    def get_pnl_for_date(
        self, account_id: str, record_date: date
    ) -> PnLRecord | None:
        """Get P&L record for a specific date.

        Args:
            account_id: The account ID
            record_date: The date to query

        Returns:
            PnLRecord if found, None otherwise
        """
        with self.session() as session:
            stmt = (
                select(PnLRecord)
                .where(PnLRecord.account_id == account_id)
                .where(PnLRecord.record_date == record_date)
            )
            pnl = session.scalars(stmt).first()
            if pnl:
                session.expunge(pnl)  # Detach with loaded attributes
            return pnl

    def get_pnl_history(
        self,
        account_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[PnLRecord]:
        """Get P&L history for an account within a date range.

        Args:
            account_id: The account ID
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            List of P&L records ordered by date
        """
        with self.session() as session:
            stmt = select(PnLRecord).where(PnLRecord.account_id == account_id)
            if start_date:
                stmt = stmt.where(PnLRecord.record_date >= start_date)
            if end_date:
                stmt = stmt.where(PnLRecord.record_date <= end_date)
            stmt = stmt.order_by(PnLRecord.record_date)
            pnls = list(session.scalars(stmt).all())
            for pnl in pnls:
                session.expunge(pnl)  # Detach with loaded attributes
            return pnls

    def save_equity_snapshot(self, snapshot: EquitySnapshot) -> EquitySnapshot:
        """Save an equity snapshot.

        Args:
            snapshot: EquitySnapshot instance to save

        Returns:
            The saved equity snapshot with updated fields
        """
        with self.session() as session:
            session.add(snapshot)
            session.flush()
            session.refresh(snapshot)
            session.expunge(snapshot)  # Detach with loaded attributes
            return snapshot

    def get_equity_snapshots(
        self,
        account_id: str,
        start_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[EquitySnapshot]:
        """Get equity snapshots for an account.

        Args:
            account_id: The account ID
            start_time: Optional start timestamp
            limit: Maximum number of snapshots to return (default 1000)

        Returns:
            List of equity snapshots ordered by timestamp
        """
        with self.session() as session:
            stmt = select(EquitySnapshot).where(
                EquitySnapshot.account_id == account_id
            )
            if start_time:
                stmt = stmt.where(EquitySnapshot.timestamp >= start_time)
            stmt = stmt.order_by(EquitySnapshot.timestamp).limit(limit)
            snapshots = list(session.scalars(stmt).all())
            for snap in snapshots:
                session.expunge(snap)  # Detach with loaded attributes
            return snapshots

    # =========================================================================
    # SYSTEM STATE OPERATIONS
    # =========================================================================

    def get_system_state(self) -> SystemState:
        """Get the system state (singleton).

        Creates the system state record if it doesn't exist.

        Returns:
            The system state singleton
        """
        with self.session() as session:
            state = session.get(SystemState, "system_state_singleton")
            if state is None:
                # Create initial system state
                state = SystemState()
                session.add(state)
                session.flush()
                session.refresh(state)
            session.expunge(state)  # Detach with loaded attributes
            return state

    def update_system_state(
        self,
        kill_switch_active: bool | None = None,
        kill_switch_activated_at: datetime | None = None,
        kill_switch_reason: str | None = None,
        trading_enabled: bool | None = None,
        last_trade_at: datetime | None = None,
        last_health_check: datetime | None = None,
        health_status: str | None = None,
        circuit_breakers: dict[str, Any] | None = None,
    ) -> SystemState:
        """Update system state fields with type-safe parameters.

        Only non-None values will be updated, allowing partial updates.

        Args:
            kill_switch_active: Set kill switch state (True to halt all trading)
            kill_switch_activated_at: Timestamp when kill switch was activated
            kill_switch_reason: Reason for kill switch activation
            trading_enabled: Enable/disable trading system-wide
            last_trade_at: Timestamp of last executed trade
            last_health_check: Timestamp of last health check
            health_status: Current health status (healthy/degraded/unhealthy/unknown)
            circuit_breakers: Dictionary of circuit breaker states

        Returns:
            The updated system state

        Example:
            ```python
            store.update_system_state(
                kill_switch_active=True,
                kill_switch_reason="Daily loss limit exceeded"
            )
            ```

        Note:
            This method provides type safety and IDE autocomplete by using
            explicit parameters instead of **kwargs: Any.
        """
        with self.session() as session:
            state = self.get_system_state()
            # Reattach to current session
            state = session.merge(state)

            # Only update non-None values
            if kill_switch_active is not None:
                state.kill_switch_active = kill_switch_active
            if kill_switch_activated_at is not None:
                state.kill_switch_activated_at = kill_switch_activated_at
            if kill_switch_reason is not None:
                state.kill_switch_reason = kill_switch_reason
            if trading_enabled is not None:
                state.trading_enabled = trading_enabled
            if last_trade_at is not None:
                state.last_trade_at = last_trade_at
            if last_health_check is not None:
                state.last_health_check = last_health_check
            if health_status is not None:
                state.health_status = health_status
            if circuit_breakers is not None:
                state.circuit_breakers = circuit_breakers

            session.flush()
            session.refresh(state)
            self.logger.info(
                "system_state_updated",
                trading_enabled=state.trading_enabled,
                kill_switch_active=state.kill_switch_active,
                health_status=state.health_status
            )
            session.expunge(state)  # Detach with loaded attributes
            return state

    def add_audit_log(
        self,
        action: str,
        actor: str,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Add an entry to the audit log.

        Args:
            action: The action that was taken
            actor: Who/what initiated the action
            details: Optional additional context

        Returns:
            The created audit log entry

        Example:
            ```python
            store.add_audit_log(
                action="kill_switch_activated",
                actor="risk_controller",
                details={"reason": "Daily loss limit exceeded", "threshold": 3.0}
            )
            ```
        """
        from .models.base import generate_id

        with self.session() as session:
            log = AuditLog(
                id=generate_id("audit"),
                action=action,
                actor=actor,
                details=details,
            )
            session.add(log)
            session.flush()
            session.refresh(log)
            session.expunge(log)  # Detach with loaded attributes
            return log

    def get_audit_logs(
        self,
        action: str | None = None,
        actor: str | None = None,
        start_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get audit logs with optional filters.

        Args:
            action: Optional action type to filter by
            actor: Optional actor to filter by
            start_time: Optional start timestamp
            limit: Maximum number of logs to return (default 100)

        Returns:
            List of audit logs ordered by timestamp (newest first)
        """
        with self.session() as session:
            stmt = select(AuditLog)

            if action:
                stmt = stmt.where(AuditLog.action == action)
            if actor:
                stmt = stmt.where(AuditLog.actor == actor)
            if start_time:
                stmt = stmt.where(AuditLog.timestamp >= start_time)

            stmt = stmt.order_by(AuditLog.timestamp.desc()).limit(limit)
            logs = list(session.scalars(stmt).all())
            for log in logs:
                session.expunge(log)  # Detach with loaded attributes
            return logs

    # =========================================================================
    # STRATEGY ASSIGNMENT OPERATIONS
    # =========================================================================

    def save_assignment(self, assignment: StrategyAssignment) -> StrategyAssignment:
        """Save a strategy assignment.

        Args:
            assignment: StrategyAssignment instance to save

        Returns:
            The saved assignment with updated fields
        """
        with self.session() as session:
            session.add(assignment)
            session.flush()
            session.refresh(assignment)
            session.expunge(assignment)  # Detach with loaded attributes
            return assignment

    def get_assignments_for_account(self, account_id: str) -> list[StrategyAssignment]:
        """Get all strategy assignments for an account.

        Args:
            account_id: The account ID

        Returns:
            List of strategy assignments
        """
        with self.session() as session:
            stmt = select(StrategyAssignment).where(
                StrategyAssignment.account_id == account_id
            )
            assignments = list(session.scalars(stmt).all())
            for assignment in assignments:
                session.expunge(assignment)  # Detach with loaded attributes
            return assignments

    def get_active_assignments(self, account_id: str) -> list[StrategyAssignment]:
        """Get active strategy assignments for an account.

        Args:
            account_id: The account ID

        Returns:
            List of active strategy assignments
        """
        with self.session() as session:
            from .models import AssignmentStatus

            stmt = (
                select(StrategyAssignment)
                .where(StrategyAssignment.account_id == account_id)
                .where(StrategyAssignment.status == AssignmentStatus.ACTIVE)
            )
            assignments = list(session.scalars(stmt).all())
            for assignment in assignments:
                session.expunge(assignment)  # Detach with loaded attributes
            return assignments

    # =========================================================================
    # SIGNAL OPERATIONS
    # =========================================================================

    def save_signal(self, signal: Signal) -> Signal:
        """Save a trading signal.

        Args:
            signal: Signal instance to save

        Returns:
            The saved signal with updated fields
        """
        with self.session() as session:
            session.add(signal)
            session.flush()
            session.refresh(signal)
            session.expunge(signal)  # Detach with loaded attributes
            return signal

    def get_unexecuted_signals(self, strategy_id: str | None = None) -> list[Signal]:
        """Get unexecuted signals, optionally filtered by strategy.

        Args:
            strategy_id: Optional strategy ID to filter by

        Returns:
            List of unexecuted signals
        """
        with self.session() as session:
            stmt = select(Signal).where(Signal.executed.is_(False))
            if strategy_id:
                stmt = stmt.where(Signal.strategy_id == strategy_id)
            signals = list(session.scalars(stmt).all())
            for signal in signals:
                session.expunge(signal)  # Detach with loaded attributes
            return signals

    def get_signals_for_strategy(
        self, strategy_id: str, limit: int = 100
    ) -> list[Signal]:
        """Get recent signals for a strategy.

        Args:
            strategy_id: The strategy ID
            limit: Maximum number of signals to return (default 100)

        Returns:
            List of signals ordered by timestamp (newest first)
        """
        with self.session() as session:
            stmt = (
                select(Signal)
                .where(Signal.strategy_id == strategy_id)
                .order_by(Signal.timestamp.desc())
                .limit(limit)
            )
            signals = list(session.scalars(stmt).all())
            for signal in signals:
                session.expunge(signal)  # Detach with loaded attributes
            return signals
