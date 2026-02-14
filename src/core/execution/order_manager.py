"""Order lifecycle manager — central orchestrator for order execution.

Manages the full order lifecycle:
1. Risk validation
2. Order creation and persistence
3. Exchange submission
4. Background monitoring with adaptive polling
5. Fill handling (Trade creation, Position updates)
6. Order reconciliation (PRD Feature I)

Critical Invariant (IMMUTABLE):
    Risk Check -> Create Record -> Persist DB -> Submit Exchange
    -> Update Status -> Start Monitor

The order MUST be persisted to DB BEFORE submitting to the exchange.
This prevents order loss if the application crashes after submission.

Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-08-007 - Input validation at boundaries
Decision: DEC-2026-02-08-008 - Structured logging

Phase 4A: Execution Infrastructure
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from src.core.exceptions import (InvalidStateTransitionError,
                                 OrderNotFoundError, OrderSubmissionError,
                                 OrderTimeoutError)
from src.core.execution.interface import ExecutionEngine, OrderResult
from src.core.execution.position_tracker import PositionTracker
from src.core.risk.controller import RiskController
from src.core.risk.types import OrderRequest
from src.data.models.base import generate_id
from src.data.models.order import Order, OrderSide, OrderStatus, OrderType
from src.data.models.trade import Trade
from src.data.store import DataStore
from src.utils.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# State machine: valid one-way transitions
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"submitted", "rejected"},
    "submitted": {"partially_filled", "filled", "cancelled", "expired"},
    "partially_filled": {"filled", "cancelled"},
}


# ---------------------------------------------------------------------------
# Monitoring polling intervals (adaptive)
# ---------------------------------------------------------------------------

# Polling interval stages: (threshold_seconds, interval_seconds)
_POLLING_STAGES: list[tuple[float, float]] = [
    (30.0, 1.0),     # First 30s: poll every 1s
    (300.0, 5.0),    # Up to 5min: poll every 5s
    (float("inf"), 10.0),  # After 5min: poll every 10s
]

# Default timeout for order monitoring (30 minutes)
DEFAULT_MONITORING_TIMEOUT_SECONDS = 1800

# Reconciliation interval (60 seconds per PRD Feature I)
DEFAULT_RECONCILIATION_INTERVAL_SECONDS = 60


class OrderManager:
    """Central orchestrator for order lifecycle management.

    Coordinates between the ExecutionEngine (exchange adapter),
    DataStore (persistence), and RiskController (validation) to
    manage orders from creation through completion.

    Attributes:
        execution_engine: Exchange adapter for order operations.
        data_store: Database access layer.
        risk_controller: Optional risk validation pipeline.
        monitoring_timeout: Max seconds to monitor an order.
        reconciliation_interval: Seconds between reconciliation checks.
    """

    def __init__(
        self,
        execution_engine: ExecutionEngine,
        data_store: DataStore,
        risk_controller: RiskController | None = None,
        position_tracker: PositionTracker | None = None,
        monitoring_timeout: int = DEFAULT_MONITORING_TIMEOUT_SECONDS,
        reconciliation_interval: int = DEFAULT_RECONCILIATION_INTERVAL_SECONDS,
    ) -> None:
        """Initialize the OrderManager.

        Args:
            execution_engine: Exchange adapter implementing ExecutionEngine.
            data_store: DataStore instance for database operations.
            risk_controller: Optional RiskController for pre-trade validation.
            position_tracker: Optional PositionTracker for position updates on fill.
            monitoring_timeout: Max seconds to monitor an order before timeout.
            reconciliation_interval: Seconds between order reconciliation runs.
        """
        self.execution_engine = execution_engine
        self.data_store = data_store
        self.risk_controller = risk_controller
        self.position_tracker = position_tracker
        self.monitoring_timeout = monitoring_timeout
        self.reconciliation_interval = reconciliation_interval

        # Active monitoring tasks keyed by order ID
        self._monitoring_tasks: dict[str, asyncio.Task[None]] = {}

        # Reconciliation background task
        self._reconciliation_task: asyncio.Task[None] | None = None

        logger.info(
            "order_manager_initialized",
            has_risk_controller=risk_controller is not None,
            has_position_tracker=position_tracker is not None,
            monitoring_timeout=monitoring_timeout,
            reconciliation_interval=reconciliation_interval,
        )

    # =========================================================================
    # Public API
    # =========================================================================

    async def submit_order(self, request: OrderRequest) -> Order:
        """Submit a new order through the full lifecycle.

        CRITICAL INVARIANT (per PHASE_4_IMPLEMENTATION_GUIDE.md):
        Risk Check -> Create Record -> Persist DB -> Submit Exchange
        -> Update Status -> Start Monitor

        The order MUST be persisted before exchange submission.

        Args:
            request: Validated OrderRequest from the risk types module.

        Returns:
            The persisted Order model with current status.

        Raises:
            OrderSubmissionError: If exchange submission fails.
        """
        logger.info(
            "order_submission_started",
            account_id=request.account_id,
            strategy_id=request.strategy_id,
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            price=request.price,
        )

        # Step 1: Risk check (if controller available)
        if self.risk_controller:
            risk_results = await asyncio.to_thread(
                self.risk_controller.validate_order, request
            )
            # Last result determines pass/fail (fail-fast pipeline)
            last_result = risk_results[-1] if risk_results else None
            if last_result and not last_result.approved:
                logger.warning(
                    "order_rejected_by_risk",
                    symbol=request.symbol,
                    check_name=last_result.check_name,
                    reason=last_result.rejection_reason,
                )
                order = self._create_order_from_request(
                    request, OrderStatus.REJECTED
                )
                order.rejection_reason = last_result.rejection_reason
                saved = await asyncio.to_thread(
                    self.data_store.save_order, order
                )
                return saved

        # Step 2: Create order record in memory (PENDING status)
        order = self._create_order_from_request(request, OrderStatus.PENDING)

        # Step 3: Persist to DB - FIRST IRREVERSIBLE STEP
        # Order is safe in DB before going to exchange
        saved_order = await asyncio.to_thread(
            self.data_store.save_order, order
        )
        order_id = saved_order.id

        logger.info(
            "order_persisted",
            order_id=order_id,
            symbol=request.symbol,
            status="pending",
        )

        # Step 4: Submit to exchange
        try:
            result = await self.execution_engine.submit_order(request)
        except Exception as e:
            # Exchange submission failed — mark order as REJECTED
            logger.error(
                "order_exchange_submission_failed",
                order_id=order_id,
                symbol=request.symbol,
                error=str(e),
                exc_info=True,
            )
            await asyncio.to_thread(
                self.data_store.update_order,
                order_id,
                status=OrderStatus.REJECTED,
                rejection_reason=str(e),
            )
            raise OrderSubmissionError(
                order_id=order_id,
                symbol=request.symbol,
                reason=str(e),
            ) from e

        # Step 5: Update status to SUBMITTED with external ID
        now = datetime.now(timezone.utc)
        await asyncio.to_thread(
            self.data_store.update_order,
            order_id,
            status=OrderStatus.SUBMITTED,
            external_id=result.external_id,
            submitted_at=now,
        )

        logger.info(
            "order_submitted_to_exchange",
            order_id=order_id,
            external_id=result.external_id,
            symbol=request.symbol,
            exchange_status=result.status,
        )

        # If the order was immediately filled (market orders often are)
        if result.status == "filled":
            await self._handle_fill(order_id, result)
            # Re-fetch to get the filled state
            filled_order = await asyncio.to_thread(
                self.data_store.get_order, order_id
            )
            if filled_order:
                return filled_order

        # Step 6: Start background monitoring
        if result.status in ("submitted", "partially_filled"):
            await self._start_monitoring(order_id, request.symbol)

        # Return the latest order state
        final_order = await asyncio.to_thread(
            self.data_store.get_order, order_id
        )
        return final_order or saved_order

    async def cancel_order(self, order_id: str) -> Order:
        """Cancel an existing order.

        Args:
            order_id: Internal order ID.

        Returns:
            Updated Order with cancelled status.

        Raises:
            OrderNotFoundError: If order does not exist.
            InvalidStateTransitionError: If order cannot be cancelled.
        """
        order = await asyncio.to_thread(
            self.data_store.get_order, order_id
        )
        if order is None:
            raise OrderNotFoundError(order_id=order_id)

        # Validate state transition
        current_status = (
            order.status.value
            if isinstance(order.status, OrderStatus)
            else str(order.status)
        )
        self._validate_state_transition(current_status, "cancelled")

        logger.info(
            "cancelling_order",
            order_id=order_id,
            symbol=order.symbol,
            current_status=current_status,
        )

        # Cancel on exchange if it has an external ID
        if order.external_id:
            try:
                await self.execution_engine.cancel_order(
                    order_id=order.external_id,
                    symbol=order.symbol,
                )
            except Exception as e:
                logger.error(
                    "exchange_cancel_failed",
                    order_id=order_id,
                    external_id=order.external_id,
                    error=str(e),
                    exc_info=True,
                )
                # Still mark as cancelled locally
                # Exchange state will be reconciled later

        # Stop monitoring if active
        self._stop_monitoring(order_id)

        # Update DB
        updated = await asyncio.to_thread(
            self.data_store.update_order,
            order_id,
            status=OrderStatus.CANCELLED,
        )

        logger.info(
            "order_cancelled",
            order_id=order_id,
            symbol=order.symbol,
        )

        if updated:
            return updated
        raise OrderNotFoundError(order_id=order_id)

    async def get_order(self, order_id: str) -> Order | None:
        """Get an order by its internal ID.

        Args:
            order_id: Internal order ID.

        Returns:
            Order if found, None otherwise.
        """
        return await asyncio.to_thread(
            self.data_store.get_order, order_id
        )

    async def get_open_orders(self, account_id: str) -> list[Order]:
        """Get all open (non-terminal) orders for an account.

        Args:
            account_id: Account identifier.

        Returns:
            List of open orders.
        """
        return await asyncio.to_thread(
            self.data_store.get_orders_by_account_and_status,
            account_id,
            OrderStatus.SUBMITTED,
        )

    async def reconcile_orders(self) -> list[Order]:
        """Reconcile internal order state with exchange state.

        PRD Feature I: Order state reconciliation.

        Queries the exchange for all open orders and compares with
        our database records. Updates any mismatched statuses.

        Returns:
            List of orders that were updated during reconciliation.
        """
        logger.info("order_reconciliation_started")
        updated_orders: list[Order] = []

        # Get all orders we think are open
        pending_orders = await asyncio.to_thread(
            self.data_store.get_pending_orders
        )

        for order in pending_orders:
            if not order.external_id:
                continue

            try:
                result = await self.execution_engine.get_order_status(
                    order_id=order.external_id,
                    symbol=order.symbol,
                )

                current_status = (
                    order.status.value
                    if isinstance(order.status, OrderStatus)
                    else str(order.status)
                )

                # Check if exchange status differs from our record
                if result.status != current_status:
                    logger.warning(
                        "order_status_mismatch",
                        order_id=order.id,
                        external_id=order.external_id,
                        local_status=current_status,
                        exchange_status=result.status,
                    )

                    # Handle fills discovered during reconciliation
                    if result.status == "filled":
                        await self._handle_fill(order.id, result)

                    # Update status if transition is valid
                    try:
                        self._validate_state_transition(
                            current_status, result.status
                        )
                        updated = await asyncio.to_thread(
                            self.data_store.update_order,
                            order.id,
                            status=OrderStatus(result.status),
                        )
                        if updated:
                            updated_orders.append(updated)
                    except InvalidStateTransitionError:
                        logger.error(
                            "reconciliation_invalid_transition",
                            order_id=order.id,
                            current=current_status,
                            exchange=result.status,
                        )

            except Exception as e:
                logger.error(
                    "reconciliation_order_check_failed",
                    order_id=order.id,
                    external_id=order.external_id,
                    error=str(e),
                    exc_info=True,
                )

        logger.info(
            "order_reconciliation_completed",
            orders_checked=len(pending_orders),
            orders_updated=len(updated_orders),
        )

        return updated_orders

    async def start_reconciliation_loop(self) -> None:
        """Start the background reconciliation loop.

        Runs reconciliation at the configured interval until stopped.
        """
        logger.info(
            "reconciliation_loop_starting",
            interval=self.reconciliation_interval,
        )
        self._reconciliation_task = asyncio.create_task(
            self._reconciliation_loop()
        )

    async def shutdown(self) -> None:
        """Clean shutdown of all background tasks.

        Cancels all monitoring tasks and the reconciliation loop.
        """
        logger.info(
            "order_manager_shutting_down",
            active_monitors=len(self._monitoring_tasks),
        )

        # Cancel all monitoring tasks
        for order_id, task in self._monitoring_tasks.items():
            task.cancel()
            logger.debug(
                "monitoring_task_cancelled",
                order_id=order_id,
            )
        self._monitoring_tasks.clear()

        # Cancel reconciliation loop
        if self._reconciliation_task and not self._reconciliation_task.done():
            self._reconciliation_task.cancel()
            try:
                await self._reconciliation_task
            except asyncio.CancelledError:
                pass

        logger.info("order_manager_shutdown_complete")

    # =========================================================================
    # Internal: State machine
    # =========================================================================

    def _validate_state_transition(
        self, current: str, new: str
    ) -> None:
        """Validate that a state transition is allowed.

        The state machine is strictly one-way per
        PHASE_4_IMPLEMENTATION_GUIDE.md invariant #2.

        Args:
            current: Current order status (lowercase string).
            new: Requested new status (lowercase string).

        Raises:
            InvalidStateTransitionError: If transition is illegal.
        """
        valid_next = VALID_TRANSITIONS.get(current, set())
        if new not in valid_next:
            raise InvalidStateTransitionError(
                order_id="",
                current_status=current,
                requested_status=new,
            )

    # =========================================================================
    # Internal: Order creation
    # =========================================================================

    def _create_order_from_request(
        self,
        request: OrderRequest,
        status: OrderStatus,
    ) -> Order:
        """Create an Order model from an OrderRequest.

        Maps from the risk types OrderRequest to the database Order model,
        translating string-based sides/types to enum values.

        Args:
            request: Validated order request.
            status: Initial order status.

        Returns:
            Order model instance (not yet persisted).
        """
        side_enum = OrderSide(request.side)
        type_enum = OrderType(request.order_type)

        order = Order(
            id=generate_id("ord"),
            account_id=request.account_id,
            strategy_id=request.strategy_id,
            symbol=request.symbol,
            side=side_enum,
            type=type_enum,
            quantity=request.quantity,
            price=request.price if request.order_type != "market" else None,
            status=status,
            filled_quantity=0.0,
        )

        return order

    # =========================================================================
    # Internal: Monitoring
    # =========================================================================

    async def _start_monitoring(
        self, order_id: str, symbol: str
    ) -> None:
        """Start background monitoring for an order.

        Creates an asyncio task that polls the exchange for order
        status updates at adaptive intervals.

        Args:
            order_id: Internal order ID.
            symbol: Trading pair for exchange queries.
        """
        if order_id in self._monitoring_tasks:
            logger.warning(
                "monitoring_already_active",
                order_id=order_id,
            )
            return

        task = asyncio.create_task(
            self._monitor_order(order_id, symbol),
            name=f"monitor_{order_id}",
        )
        self._monitoring_tasks[order_id] = task

        logger.info(
            "order_monitoring_started",
            order_id=order_id,
            symbol=symbol,
            timeout=self.monitoring_timeout,
        )

    def _stop_monitoring(self, order_id: str) -> None:
        """Stop monitoring for an order.

        Args:
            order_id: Internal order ID.
        """
        task = self._monitoring_tasks.pop(order_id, None)
        if task and not task.done():
            task.cancel()
            logger.debug(
                "order_monitoring_stopped",
                order_id=order_id,
            )

    async def _monitor_order(
        self, order_id: str, symbol: str
    ) -> None:
        """Monitor an order until it reaches a terminal state.

        Uses adaptive polling intervals:
        - First 30s: every 1s
        - Up to 5min: every 5s
        - After 5min: every 10s

        Args:
            order_id: Internal order ID.
            symbol: Trading pair for exchange queries.
        """
        start_time = datetime.now(timezone.utc)

        # Get the external ID for exchange queries
        order = await asyncio.to_thread(
            self.data_store.get_order, order_id
        )
        if not order or not order.external_id:
            logger.error(
                "monitor_missing_external_id",
                order_id=order_id,
            )
            self._monitoring_tasks.pop(order_id, None)
            return

        external_id = order.external_id

        try:
            while True:
                # Check timeout
                elapsed = (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds()
                if elapsed > self.monitoring_timeout:
                    logger.warning(
                        "order_monitoring_timeout",
                        order_id=order_id,
                        external_id=external_id,
                        elapsed_seconds=elapsed,
                    )
                    raise OrderTimeoutError(
                        order_id=order_id,
                        timeout_seconds=self.monitoring_timeout,
                    )

                # Determine polling interval based on elapsed time
                interval = _POLLING_STAGES[-1][1]
                for threshold, stage_interval in _POLLING_STAGES:
                    if elapsed < threshold:
                        interval = stage_interval
                        break

                await asyncio.sleep(interval)

                # Poll exchange for status
                try:
                    result = await self.execution_engine.get_order_status(
                        order_id=external_id,
                        symbol=symbol,
                    )
                except Exception as e:
                    logger.warning(
                        "monitor_poll_failed",
                        order_id=order_id,
                        error=str(e),
                    )
                    continue  # Retry on next interval

                # Check for status change
                if result.status in ("filled", "cancelled", "expired", "rejected"):
                    logger.info(
                        "monitor_terminal_status",
                        order_id=order_id,
                        status=result.status,
                        filled_quantity=result.filled_quantity,
                    )

                    if result.status == "filled":
                        await self._handle_fill(order_id, result)
                    else:
                        # Update to terminal status
                        status_enum = OrderStatus(result.status)
                        await asyncio.to_thread(
                            self.data_store.update_order,
                            order_id,
                            status=status_enum,
                        )

                    break  # Exit monitoring loop

                elif result.status == "partially_filled":
                    # Update filled quantity but continue monitoring
                    await asyncio.to_thread(
                        self.data_store.update_order,
                        order_id,
                        status=OrderStatus.PARTIALLY_FILLED,
                        filled_quantity=result.filled_quantity,
                        filled_price=result.filled_price,
                    )

        except asyncio.CancelledError:
            logger.info(
                "order_monitoring_cancelled",
                order_id=order_id,
            )
        except OrderTimeoutError:
            # Mark order status — don't auto-cancel, just log
            logger.error(
                "order_monitoring_timed_out",
                order_id=order_id,
                timeout_seconds=self.monitoring_timeout,
            )
        except Exception as e:
            logger.error(
                "order_monitoring_error",
                order_id=order_id,
                error=str(e),
                exc_info=True,
            )
        finally:
            self._monitoring_tasks.pop(order_id, None)

    # =========================================================================
    # Internal: Fill handling
    # =========================================================================

    async def _handle_fill(
        self, order_id: str, result: OrderResult
    ) -> None:
        """Handle a filled order — create Trade record and update Order.

        Creates a Trade model from the fill data and updates the Order
        to FILLED status with fill details.

        Args:
            order_id: Internal order ID.
            result: OrderResult with fill details from the exchange.
        """
        logger.info(
            "handling_order_fill",
            order_id=order_id,
            symbol=result.symbol,
            filled_quantity=result.filled_quantity,
            filled_price=result.filled_price,
            commission=result.commission,
        )

        # Create Trade record
        now = datetime.now(timezone.utc)
        side_enum = OrderSide(result.side)

        trade = Trade(
            id=generate_id("trd"),
            order_id=order_id,
            account_id=result.order_id,  # account_id was stored in order_id field during submit
            symbol=result.symbol,
            side=side_enum,
            quantity=result.filled_quantity,
            price=result.filled_price or 0.0,
            commission=result.commission,
            executed_at=result.timestamp or now,
            external_trade_id=result.external_id,
        )

        # We need the account_id from the order record
        order = await asyncio.to_thread(
            self.data_store.get_order, order_id
        )
        if order:
            trade.account_id = order.account_id

        await asyncio.to_thread(self.data_store.save_trade, trade)

        # Update order to filled status
        await asyncio.to_thread(
            self.data_store.update_order,
            order_id,
            status=OrderStatus.FILLED,
            filled_quantity=result.filled_quantity,
            filled_price=result.filled_price,
            filled_at=now,
        )

        logger.info(
            "order_fill_processed",
            order_id=order_id,
            trade_id=trade.id,
            symbol=result.symbol,
            filled_quantity=result.filled_quantity,
            filled_price=result.filled_price,
            commission=result.commission,
        )

        # Phase 4B: Update positions from fill
        if self.position_tracker:
            try:
                strategy_id = order.strategy_id if order else None
                await self.position_tracker.process_fill(
                    trade, strategy_id=strategy_id
                )
            except Exception as pos_exc:
                # Position update failure must not block order processing
                # The trade is already saved, position can be reconciled later
                logger.error(
                    "position_update_from_fill_failed",
                    order_id=order_id,
                    trade_id=trade.id,
                    error=str(pos_exc),
                    exc_info=True,
                )

    # =========================================================================
    # Internal: Reconciliation loop
    # =========================================================================

    async def _reconciliation_loop(self) -> None:
        """Background loop that periodically reconciles orders.

        PRD Feature I: Order state reconciliation.
        """
        try:
            while True:
                await asyncio.sleep(self.reconciliation_interval)
                try:
                    await self.reconcile_orders()
                except Exception as e:
                    logger.error(
                        "reconciliation_loop_error",
                        error=str(e),
                        exc_info=True,
                    )
        except asyncio.CancelledError:
            logger.info("reconciliation_loop_stopped")
