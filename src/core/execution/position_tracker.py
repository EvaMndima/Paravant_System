"""Position lifecycle tracker with P&L calculations and staleness monitoring.

Manages the full position lifecycle from opening to closing, with accurate
P&L calculations that always include commission (Critical Invariant #3).

Integration Point:
    OrderManager._handle_fill() calls PositionTracker.process_fill() after
    creating a Trade record, so the position is updated atomically with
    each fill event.

Decision: DEC-2026-02-08-002 - SQLAlchemy 2.0 with Mapped[T]
Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-08-007 - Input validation at boundaries
Decision: DEC-2026-02-08-008 - Structured logging

Phase 4B: Position Tracking & Execution Quality
"""
from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from src.core.exceptions import PositionStorageError
from src.core.execution.interface import ExecutionEngine
from src.data.models.base import generate_id
from src.data.models.order import OrderSide
from src.data.models.position import Position, PositionSide, PositionStatus
from src.data.models.strategy import StrategyType
from src.data.models.trade import Trade
from src.data.store import DataStore
from src.utils.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses for structured results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PositionSyncResult:
    """Result of position synchronization with exchange balances.

    Attributes:
        total_positions: Number of open positions checked.
        synced_positions: Positions where local matches exchange.
        corrected_positions: Positions where local was corrected.
        discrepancies: Details of each discrepancy found.
    """

    total_positions: int
    synced_positions: int
    corrected_positions: int
    discrepancies: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class StalenessResult:
    """Result of position staleness check.

    Attributes:
        position_id: The position that was checked.
        symbol: Trading pair symbol.
        hold_duration: How long the position has been held.
        should_warn: Whether warning threshold is exceeded.
        should_review: Whether force_review threshold is exceeded.
        should_close: Whether max_hold threshold is exceeded.
        days_remaining: Days until max_hold threshold.
        status: Human-readable status string.
    """

    position_id: str
    symbol: str
    hold_duration: timedelta
    should_warn: bool
    should_review: bool
    should_close: bool
    days_remaining: float
    status: str  # "OK", "WARNING", "REVIEW_REQUIRED", "MAX_HOLD_EXCEEDED"


# ---------------------------------------------------------------------------
# Staleness configuration
# ---------------------------------------------------------------------------

# Threshold values in hours for each holding period category
STALENESS_THRESHOLDS: dict[str, dict[str, float]] = {
    "day_trading": {
        "warning_hours": 24.0,
        "force_review_hours": 48.0,
        "max_hold_hours": 72.0,
    },
    "swing_trading": {
        "warning_hours": 168.0,       # 7 days
        "force_review_hours": 336.0,   # 14 days
        "max_hold_hours": 720.0,       # 30 days
    },
    "position_trading": {
        "warning_hours": 720.0,        # 30 days
        "force_review_hours": 1440.0,  # 60 days
        "max_hold_hours": 2160.0,      # 90 days
    },
}

# Maps StrategyType to holding period category
STRATEGY_HOLDING_PERIODS: dict[StrategyType, str] = {
    StrategyType.INTRADAY_PULLBACK: "day_trading",
    StrategyType.MEAN_REVERSION: "day_trading",
    StrategyType.VOLATILITY_BREAKOUT: "day_trading",
    StrategyType.TREND_FOLLOWING: "swing_trading",
    StrategyType.TREND_CONTINUATION: "swing_trading",
    StrategyType.TREND_BREAKOUT: "position_trading",
}

# Profitable positions get this multiplier on all thresholds
PROFITABLE_EXTENSION_MULTIPLIER: float = 1.5

# Floating point threshold for considering a position fully closed
_CLOSE_THRESHOLD: float = 1e-8


# ---------------------------------------------------------------------------
# PositionTracker
# ---------------------------------------------------------------------------


class PositionTracker:
    """Position lifecycle manager with P&L tracking and staleness monitoring.

    Manages opening, updating, and closing positions based on trade fills.
    Calculates unrealized and realized P&L with commission included, and
    monitors position staleness based on strategy type.

    Attributes:
        data_store: Database access layer for persistence.
        _positions: In-memory cache of open positions (symbol -> Position).

    Example:
        >>> tracker = PositionTracker(data_store)
        >>> await tracker.initialize()
        >>> # Process a fill from OrderManager
        >>> position = await tracker.process_fill(trade, strategy_id="strat_123")
        >>> # Get unrealized P&L
        >>> pnl = PositionTracker.calculate_unrealized_pnl(position, 46000.0)
    """

    def __init__(self, data_store: DataStore) -> None:
        """Initialize position tracker.

        Args:
            data_store: DataStore instance for persistence.
        """
        self.data_store = data_store
        self._positions: dict[str, Position] = {}

        logger.info("position_tracker_created")

    async def initialize(self) -> None:
        """Load all open positions from database into memory cache.

        Must be called after construction before processing any fills.
        Loads all OPEN positions and indexes them by symbol for fast lookup.
        """
        open_positions = await asyncio.to_thread(
            self.data_store.get_open_positions
        )

        for position in open_positions:
            self._positions[position.symbol] = position

        logger.info(
            "position_tracker_initialized",
            open_positions=len(self._positions),
            symbols=list(self._positions.keys()),
        )

    # =========================================================================
    # Public API: Fill processing
    # =========================================================================

    async def process_fill(
        self,
        trade: Trade,
        strategy_id: str | None = None,
    ) -> Position:
        """Process a trade fill and update the corresponding position.

        Main entry point called by OrderManager after a trade fills.
        Determines whether to open a new position, add to an existing one,
        or partially/fully close a position.

        Args:
            trade: Trade record from a filled order.
            strategy_id: Optional strategy ID for the position.

        Returns:
            Updated or newly created Position.

        Raises:
            ValueError: If trade data contains NaN/Infinity values.
            PositionStorageError: If database operation fails.
        """
        self._validate_trade_data(trade)

        existing = self._positions.get(trade.symbol)

        if existing is None:
            return await self._open_position(trade, strategy_id)

        # Determine direction relative to existing position
        fill_side = self._trade_side_to_position_side(trade.side)

        if existing.side == fill_side:
            return await self._add_to_position(existing, trade)
        else:
            return await self._reduce_position(existing, trade)

    # =========================================================================
    # Public API: Position queries
    # =========================================================================

    async def get_position(self, symbol: str) -> Position | None:
        """Get an open position by symbol from the in-memory cache.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT").

        Returns:
            Position if found in cache, None otherwise.
        """
        return self._positions.get(symbol)

    async def get_all_positions(self) -> list[Position]:
        """Get all open positions from the in-memory cache.

        Returns:
            List of all open Position objects.
        """
        return list(self._positions.values())

    # =========================================================================
    # Public API: P&L calculations (static, pure functions)
    # =========================================================================

    @staticmethod
    def calculate_unrealized_pnl(
        position: Position,
        current_price: float,
    ) -> float:
        """Calculate unrealized P&L for an open position.

        Includes commission in the calculation per Critical Invariant #3.

        Formulas:
            LONG:  (current_price - entry_price) * size - commission_paid
            SHORT: (entry_price - current_price) * size - commission_paid

        Args:
            position: Position to calculate P&L for.
            current_price: Current market price of the asset.

        Returns:
            Unrealized P&L in quote currency (USDT). Returns NaN if
            current_price is NaN, 0.0 if position size is zero.

        Example:
            >>> # Long 0.5 BTC @ $45,000, commission $5, current $46,000
            >>> pnl = PositionTracker.calculate_unrealized_pnl(position, 46000.0)
            >>> # (46000 - 45000) * 0.5 - 5 = 495.0
        """
        if math.isnan(current_price) or math.isinf(current_price):
            logger.warning(
                "unrealized_pnl_invalid_price",
                position_id=position.id,
                current_price=current_price,
            )
            return float("nan")

        if position.size <= 0:
            return 0.0

        if position.side == PositionSide.LONG:
            price_diff = current_price - position.entry_price
        else:
            price_diff = position.entry_price - current_price

        unrealized = (price_diff * position.size) - position.commission_paid

        logger.debug(
            "unrealized_pnl_calculated",
            position_id=position.id,
            side=position.side.value,
            entry_price=position.entry_price,
            current_price=current_price,
            size=position.size,
            commission=position.commission_paid,
            unrealized=unrealized,
        )

        return unrealized

    @staticmethod
    def calculate_return_pct(
        position: Position,
        current_price: float,
    ) -> float:
        """Calculate return percentage for a position.

        Formula: (unrealized_pnl / (entry_price * size)) * 100

        Args:
            position: Position to calculate return for.
            current_price: Current market price.

        Returns:
            Return percentage. Returns NaN if current_price is NaN,
            0.0 if entry_price or size is zero.

        Example:
            >>> # Unrealized = $495, investment = $22,500
            >>> return_pct = PositionTracker.calculate_return_pct(position, 46000.0)
            >>> # (495 / 22500) * 100 = 2.20%
        """
        if position.entry_price <= 0 or position.size <= 0:
            return 0.0

        investment = position.entry_price * position.size
        unrealized = PositionTracker.calculate_unrealized_pnl(
            position, current_price
        )

        if math.isnan(unrealized):
            return float("nan")

        return_pct = (unrealized / investment) * 100

        logger.debug(
            "return_pct_calculated",
            position_id=position.id,
            unrealized=unrealized,
            investment=investment,
            return_pct=return_pct,
        )

        return return_pct

    @staticmethod
    def calculate_realized_pnl(position: Position) -> float:
        """Get accumulated realized P&L for a position.

        Realized P&L is accumulated in position.pnl_usdt during
        partial and full closes.

        Args:
            position: Position to get realized P&L for.

        Returns:
            Accumulated realized P&L in quote currency (USDT).
        """
        return position.pnl_usdt

    # =========================================================================
    # Public API: Position synchronization
    # =========================================================================

    async def sync_positions(
        self,
        execution_engine: ExecutionEngine,
    ) -> PositionSyncResult:
        """Reconcile local position state with exchange balance state.

        For Binance spot trading, positions are represented by asset
        balances. This method compares local position sizes with
        exchange-reported balances and corrects any discrepancies.

        Args:
            execution_engine: ExecutionEngine for balance queries.

        Returns:
            PositionSyncResult with sync statistics and discrepancy details.
        """
        logger.info("position_sync_starting")

        total = len(self._positions)
        synced = 0
        corrected = 0
        discrepancies: list[dict[str, Any]] = []

        try:
            balances = await execution_engine.get_account_balance()
        except Exception as exc:
            logger.error(
                "position_sync_balance_fetch_failed",
                error=str(exc),
                exc_info=True,
            )
            return PositionSyncResult(
                total_positions=total,
                synced_positions=0,
                corrected_positions=0,
                discrepancies=[],
            )

        # Build balance lookup: extract base asset from symbol (e.g., "BTC" from "BTCUSDT")
        balance_map: dict[str, float] = {}
        for bal in balances:
            balance_map[bal.asset] = bal.free + bal.locked

        for symbol, position in list(self._positions.items()):
            # Extract base asset from symbol (assumes *USDT pair)
            base_asset = symbol.replace("USDT", "").replace("BUSD", "")
            exchange_balance = balance_map.get(base_asset, 0.0)
            local_size = position.size

            # Compare with tolerance for floating point
            if abs(exchange_balance - local_size) < _CLOSE_THRESHOLD:
                synced += 1
                continue

            # Discrepancy found
            discrepancy = {
                "symbol": symbol,
                "position_id": position.id,
                "expected": local_size,
                "actual": exchange_balance,
                "difference": exchange_balance - local_size,
            }
            discrepancies.append(discrepancy)

            logger.warning(
                "position_discrepancy",
                symbol=symbol,
                position_id=position.id,
                expected=local_size,
                actual=exchange_balance,
            )

            # Update local position to match exchange
            try:
                updated = await asyncio.to_thread(
                    self.data_store.update_position,
                    position.id,
                    size=exchange_balance,
                    current_price=position.current_price,
                )
                if updated:
                    self._positions[symbol] = updated
                    corrected += 1
            except Exception as exc:
                logger.error(
                    "position_sync_update_failed",
                    position_id=position.id,
                    error=str(exc),
                    exc_info=True,
                )

        logger.info(
            "position_sync_completed",
            total_positions=total,
            synced_positions=synced,
            corrected_positions=corrected,
            discrepancies_found=len(discrepancies),
        )

        return PositionSyncResult(
            total_positions=total,
            synced_positions=synced,
            corrected_positions=corrected,
            discrepancies=discrepancies,
        )

    # =========================================================================
    # Public API: Staleness monitoring
    # =========================================================================

    def check_staleness(
        self,
        position: Position,
        strategy_type: StrategyType | None = None,
        unrealized_pnl: float = 0.0,
        now: datetime | None = None,
    ) -> StalenessResult:
        """Check if a position has exceeded staleness thresholds.

        Thresholds depend on strategy type (day_trading, swing_trading,
        position_trading). Profitable positions get a 1.5x extension
        on all thresholds (let winners run, be strict on losers).

        Args:
            position: Position to check staleness for.
            strategy_type: Strategy type for threshold lookup. If None,
                defaults to swing_trading thresholds.
            unrealized_pnl: Current unrealized P&L for profit extension.
            now: Current time (for testing). Defaults to UTC now.

        Returns:
            StalenessResult with threshold status and days remaining.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # Determine holding period category
        holding_period = "swing_trading"  # default
        if strategy_type is not None:
            holding_period = STRATEGY_HOLDING_PERIODS.get(
                strategy_type, "swing_trading"
            )

        thresholds = STALENESS_THRESHOLDS[holding_period]

        # Apply profitable extension
        multiplier = 1.0
        if unrealized_pnl > 0:
            multiplier = PROFITABLE_EXTENSION_MULTIPLIER

        warning_hours = thresholds["warning_hours"] * multiplier
        review_hours = thresholds["force_review_hours"] * multiplier
        max_hours = thresholds["max_hold_hours"] * multiplier

        # Calculate hold duration
        opened_at = position.opened_at
        # Handle naive datetimes from database
        if opened_at.tzinfo is None:
            opened_at = opened_at.replace(tzinfo=timezone.utc)

        hold_duration = now - opened_at
        hold_hours = hold_duration.total_seconds() / 3600.0

        # Determine status
        should_close = hold_hours >= max_hours
        should_review = hold_hours >= review_hours
        should_warn = hold_hours >= warning_hours

        if should_close:
            status = "MAX_HOLD_EXCEEDED"
        elif should_review:
            status = "REVIEW_REQUIRED"
        elif should_warn:
            status = "WARNING"
        else:
            status = "OK"

        # Days remaining until max hold
        remaining_hours = max(0.0, max_hours - hold_hours)
        days_remaining = remaining_hours / 24.0

        logger.debug(
            "staleness_checked",
            position_id=position.id,
            symbol=position.symbol,
            holding_period=holding_period,
            hold_hours=hold_hours,
            warning_hours=warning_hours,
            max_hours=max_hours,
            is_profitable=unrealized_pnl > 0,
            status=status,
        )

        return StalenessResult(
            position_id=position.id,
            symbol=position.symbol,
            hold_duration=hold_duration,
            should_warn=should_warn,
            should_review=should_review,
            should_close=should_close,
            days_remaining=days_remaining,
            status=status,
        )

    async def process_stale_positions(self) -> list[StalenessResult]:
        """Check all open positions for staleness.

        Retrieves strategy types from the database and checks each
        position against its strategy-specific thresholds.

        Returns:
            List of StalenessResult for all open positions.
        """
        results: list[StalenessResult] = []

        for symbol, position in self._positions.items():
            # Look up strategy type
            strategy_type: StrategyType | None = None
            if position.strategy_id:
                strategy = await asyncio.to_thread(
                    self.data_store.get_strategy, position.strategy_id
                )
                if strategy:
                    strategy_type = strategy.type

            # Calculate unrealized P&L for profitable extension
            unrealized_pnl = self.calculate_unrealized_pnl(
                position, position.current_price
            )

            result = self.check_staleness(
                position=position,
                strategy_type=strategy_type,
                unrealized_pnl=unrealized_pnl,
            )
            results.append(result)

            if result.status != "OK":
                logger.warning(
                    "stale_position_detected",
                    position_id=position.id,
                    symbol=symbol,
                    status=result.status,
                    hold_duration_hours=result.hold_duration.total_seconds() / 3600.0,
                    days_remaining=result.days_remaining,
                )

        logger.info(
            "staleness_check_completed",
            total_positions=len(results),
            warnings=sum(1 for r in results if r.status == "WARNING"),
            reviews=sum(1 for r in results if r.status == "REVIEW_REQUIRED"),
            exceeded=sum(1 for r in results if r.status == "MAX_HOLD_EXCEEDED"),
        )

        return results

    # =========================================================================
    # Internal: Position lifecycle operations
    # =========================================================================

    async def _open_position(
        self,
        trade: Trade,
        strategy_id: str | None = None,
    ) -> Position:
        """Open a new position from a trade fill.

        Creates a Position record, persists it to the database, and
        adds it to the in-memory cache.

        Args:
            trade: Trade that opens the position.
            strategy_id: Optional strategy ID to associate.

        Returns:
            Newly created Position.

        Raises:
            PositionStorageError: If database save fails.
        """
        position_side = self._trade_side_to_position_side(trade.side)

        position = Position(
            id=generate_id("pos"),
            account_id=trade.account_id,
            strategy_id=strategy_id,
            symbol=trade.symbol,
            side=position_side,
            size=trade.quantity,
            entry_price=trade.price,
            current_price=trade.price,
            commission_paid=trade.commission,
            pnl_usdt=0.0,
            pnl_pct=0.0,
            status=PositionStatus.OPEN,
            opened_at=trade.executed_at,
        )

        try:
            saved = await asyncio.to_thread(
                self.data_store.save_position, position
            )
        except Exception as exc:
            logger.error(
                "position_open_failed",
                symbol=trade.symbol,
                error=str(exc),
                exc_info=True,
            )
            raise PositionStorageError(
                position_id=position.id,
                reason=f"Failed to save new position: {exc}",
            ) from exc

        self._positions[saved.symbol] = saved

        logger.info(
            "position_opened",
            position_id=saved.id,
            symbol=saved.symbol,
            side=saved.side.value,
            size=saved.size,
            entry_price=saved.entry_price,
            commission=saved.commission_paid,
        )

        return saved

    async def _add_to_position(
        self,
        position: Position,
        trade: Trade,
    ) -> Position:
        """Add to an existing position (same direction fill).

        Calculates the new weighted average entry price and updates
        the position size and commission.

        Formula:
            new_avg = (old_size * old_entry + fill_qty * fill_price)
                    / (old_size + fill_qty)

        Args:
            position: Existing open position to add to.
            trade: Trade fill in the same direction.

        Returns:
            Updated Position with new average entry and size.

        Raises:
            PositionStorageError: If database update fails.
        """
        old_cost = position.size * position.entry_price
        new_cost = trade.quantity * trade.price
        total_size = position.size + trade.quantity

        # Weighted average entry price
        new_avg_entry = (old_cost + new_cost) / total_size
        new_commission = position.commission_paid + trade.commission

        try:
            updated = await asyncio.to_thread(
                self.data_store.update_position,
                position.id,
                size=total_size,
                entry_price=new_avg_entry,
                current_price=trade.price,
                commission_paid=new_commission,
            )
        except Exception as exc:
            logger.error(
                "position_add_failed",
                position_id=position.id,
                error=str(exc),
                exc_info=True,
            )
            raise PositionStorageError(
                position_id=position.id,
                reason=f"Failed to update position: {exc}",
            ) from exc

        if updated is None:
            raise PositionStorageError(
                position_id=position.id,
                reason="Position not found during add-to update",
            )

        self._positions[updated.symbol] = updated

        logger.info(
            "position_increased",
            position_id=updated.id,
            symbol=updated.symbol,
            new_size=updated.size,
            new_entry_price=updated.entry_price,
            total_commission=updated.commission_paid,
        )

        return updated

    async def _reduce_position(
        self,
        position: Position,
        trade: Trade,
    ) -> Position:
        """Reduce or close a position (opposite direction fill).

        Calculates realized P&L for the closed portion including
        the fill's commission. If the fill quantity equals or exceeds
        the position size, the position is fully closed.

        Realized P&L formula:
            LONG:  (fill_price - entry_price) * fill_qty - fill_commission
            SHORT: (entry_price - fill_price) * fill_qty - fill_commission

        Args:
            position: Existing open position to reduce.
            trade: Trade fill in the opposite direction.

        Returns:
            Updated Position (may be closed if fully reduced).

        Raises:
            PositionStorageError: If database update fails.
        """
        # Calculate realized P&L for this trade
        if position.side == PositionSide.LONG:
            price_diff = trade.price - position.entry_price
        else:
            price_diff = position.entry_price - trade.price

        # Use the lesser of fill qty and position size (prevent over-closing)
        close_qty = min(trade.quantity, position.size)
        realized_pnl = (price_diff * close_qty) - trade.commission

        new_size = position.size - close_qty
        new_total_pnl = position.pnl_usdt + realized_pnl
        new_commission = position.commission_paid + trade.commission

        # Check if fully closed
        is_fully_closed = new_size <= _CLOSE_THRESHOLD

        if is_fully_closed:
            # Full close
            now = datetime.now(timezone.utc)

            # Calculate final return percentage
            original_investment = position.entry_price * position.size
            pnl_pct = (new_total_pnl / original_investment * 100) if original_investment > 0 else 0.0

            try:
                updated = await asyncio.to_thread(
                    self.data_store.update_position,
                    position.id,
                    size=0.0,
                    current_price=trade.price,
                    exit_price=trade.price,
                    pnl_usdt=new_total_pnl,
                    pnl_pct=pnl_pct,
                    commission_paid=new_commission,
                    status=PositionStatus.CLOSED,
                    closed_at=now,
                )
            except Exception as exc:
                logger.error(
                    "position_close_failed",
                    position_id=position.id,
                    error=str(exc),
                    exc_info=True,
                )
                raise PositionStorageError(
                    position_id=position.id,
                    reason=f"Failed to close position: {exc}",
                ) from exc

            if updated is None:
                raise PositionStorageError(
                    position_id=position.id,
                    reason="Position not found during close update",
                )

            # Remove from cache
            self._positions.pop(position.symbol, None)

            logger.info(
                "position_closed",
                position_id=updated.id,
                symbol=updated.symbol,
                entry_price=position.entry_price,
                exit_price=trade.price,
                realized_pnl=new_total_pnl,
                return_pct=pnl_pct,
                total_commission=new_commission,
            )

            return updated
        else:
            # Partial close
            try:
                updated = await asyncio.to_thread(
                    self.data_store.update_position,
                    position.id,
                    size=new_size,
                    current_price=trade.price,
                    pnl_usdt=new_total_pnl,
                    commission_paid=new_commission,
                )
            except Exception as exc:
                logger.error(
                    "position_reduce_failed",
                    position_id=position.id,
                    error=str(exc),
                    exc_info=True,
                )
                raise PositionStorageError(
                    position_id=position.id,
                    reason=f"Failed to reduce position: {exc}",
                ) from exc

            if updated is None:
                raise PositionStorageError(
                    position_id=position.id,
                    reason="Position not found during reduce update",
                )

            self._positions[updated.symbol] = updated

            logger.info(
                "position_reduced",
                position_id=updated.id,
                symbol=updated.symbol,
                remaining_size=new_size,
                realized_pnl=realized_pnl,
                total_pnl=new_total_pnl,
                total_commission=new_commission,
            )

            return updated

    # =========================================================================
    # Internal: Utilities
    # =========================================================================

    @staticmethod
    def _trade_side_to_position_side(trade_side: OrderSide) -> PositionSide:
        """Convert trade side (BUY/SELL) to position side (LONG/SHORT).

        Args:
            trade_side: OrderSide enum value from the trade.

        Returns:
            Corresponding PositionSide enum value.
        """
        if trade_side == OrderSide.BUY:
            return PositionSide.LONG
        return PositionSide.SHORT

    @staticmethod
    def _validate_trade_data(trade: Trade) -> None:
        """Validate trade data before processing.

        Args:
            trade: Trade to validate.

        Raises:
            ValueError: If price or quantity is NaN/Infinity.
        """
        if math.isnan(trade.price) or math.isinf(trade.price):
            raise ValueError(
                f"Trade price cannot be NaN/Infinity: {trade.price}"
            )
        if math.isnan(trade.quantity) or math.isinf(trade.quantity):
            raise ValueError(
                f"Trade quantity cannot be NaN/Infinity: {trade.quantity}"
            )
        if trade.quantity <= 0:
            raise ValueError(
                f"Trade quantity must be positive: {trade.quantity}"
            )
