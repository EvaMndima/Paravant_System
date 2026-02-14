"""Abstract execution engine interface and supporting data types.

Defines the contract that all execution adapters must implement,
along with immutable result types for order execution outcomes.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-007 - Input validation at boundaries

Phase 4A: Execution Infrastructure
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.core.risk.types import OrderRequest

# ---------------------------------------------------------------------------
# Validation helpers (same pattern as src/core/risk/types.py)
# ---------------------------------------------------------------------------


def _validate_finite_float(name: str, value: float) -> None:
    """Validate that a float is finite (not NaN or Infinity).

    Args:
        name: Field name for error message.
        value: Value to validate.

    Raises:
        ValueError: If value is NaN or Infinity.
    """
    if math.isnan(value):
        raise ValueError(f"{name} cannot be NaN")
    if math.isinf(value):
        raise ValueError(f"{name} cannot be Infinity")


def _validate_non_negative_float(name: str, value: float) -> None:
    """Validate that a float is non-negative and finite.

    Args:
        name: Field name for error message.
        value: Value to validate.

    Raises:
        ValueError: If value is NaN, Infinity, or negative.
    """
    _validate_finite_float(name, value)
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")


# ---------------------------------------------------------------------------
# Execution result types (frozen for thread safety and audit integrity)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OrderResult:
    """Immutable result of an order execution operation.

    Returned by ExecutionEngine methods to represent the current state
    of an order on the exchange. All values use internal lowercase
    conventions (e.g., side="buy", status="filled").

    Attributes:
        order_id: Internal order identifier.
        external_id: Exchange-assigned order identifier.
        symbol: Trading pair (e.g., "BTCUSDT").
        side: Order side ("buy" or "sell" - lowercase).
        order_type: Order type ("market" - lowercase).
        quantity: Requested quantity.
        filled_quantity: Quantity that has been filled.
        price: Requested price (None for market orders).
        filled_price: Average fill price (None if not filled).
        status: Order status (lowercase, matching OrderStatus enum values).
        commission: Total commission paid across all fills.
        timestamp: When this result was created (UTC).
        raw_response: Original exchange response for debugging.
    """

    order_id: str
    external_id: str | None
    symbol: str
    side: str
    order_type: str
    quantity: float
    filled_quantity: float
    price: float | None
    filled_price: float | None
    status: str
    commission: float
    timestamp: datetime
    raw_response: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate all fields at creation time.

        Raises:
            ValueError: If any field contains invalid data.
        """
        if not self.order_id:
            raise ValueError("order_id is required")
        if not self.symbol:
            raise ValueError("symbol is required")
        if self.side not in ("buy", "sell"):
            raise ValueError(
                f"side must be 'buy' or 'sell', got '{self.side}'"
            )

        # Validate numeric fields
        _validate_non_negative_float("quantity", self.quantity)
        _validate_non_negative_float("filled_quantity", self.filled_quantity)
        _validate_non_negative_float("commission", self.commission)

        if self.price is not None:
            _validate_finite_float("price", self.price)
            if self.price <= 0:
                raise ValueError(f"price must be positive, got {self.price}")

        if self.filled_price is not None:
            _validate_finite_float("filled_price", self.filled_price)
            if self.filled_price <= 0:
                raise ValueError(
                    f"filled_price must be positive, got {self.filled_price}"
                )

        # Validate timestamp is timezone-aware
        # Decision: DEC-2026-02-08-003
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (UTC)")


@dataclass(frozen=True)
class Balance:
    """Immutable account balance for a single asset.

    Returned by ExecutionEngine.get_account_balance() to represent
    the current balance state on the exchange.

    Attributes:
        asset: Asset symbol (e.g., "BTC", "USDT").
        free: Available balance for trading.
        locked: Balance locked in open orders.
        total: Total balance (free + locked).
    """

    asset: str
    free: float
    locked: float
    total: float

    def __post_init__(self) -> None:
        """Validate balance values.

        Raises:
            ValueError: If any value is invalid.
        """
        if not self.asset:
            raise ValueError("asset is required")

        _validate_non_negative_float("free", self.free)
        _validate_non_negative_float("locked", self.locked)
        _validate_non_negative_float("total", self.total)

        # Invariant: total = free + locked (allow 0.01 rounding tolerance)
        expected_total = self.free + self.locked
        if abs(self.total - expected_total) > 0.01:
            raise ValueError(
                f"Balance invariant violated: total={self.total}, "
                f"but free({self.free}) + locked({self.locked}) = "
                f"{expected_total}"
            )


# ---------------------------------------------------------------------------
# Abstract execution engine interface
# ---------------------------------------------------------------------------


class ExecutionEngine(ABC):
    """Abstract interface for order execution adapters.

    All execution adapters (Binance, paper trading, etc.) must implement
    this interface. The OrderManager depends only on this abstraction,
    enabling easy testing with mock implementations and future adapter
    additions.

    All methods are async to support non-blocking I/O with exchange APIs.
    All values use internal lowercase conventions — adapters are responsible
    for translating to/from exchange-specific formats.
    """

    @abstractmethod
    async def submit_order(self, request: OrderRequest) -> OrderResult:
        """Submit an order to the exchange.

        Args:
            request: Validated order request from risk pipeline.

        Returns:
            OrderResult with exchange response details.

        Raises:
            OrderSubmissionError: If submission fails.
            InsufficientBalanceError: If balance is insufficient.
            OrderRejectedError: If exchange rejects the order.
            BrokerConnectionError: If exchange is unreachable.
        """

    @abstractmethod
    async def cancel_order(
        self, order_id: str, symbol: str
    ) -> OrderResult:
        """Cancel an existing order on the exchange.

        Args:
            order_id: Exchange-assigned order ID.
            symbol: Trading pair (e.g., "BTCUSDT").

        Returns:
            OrderResult reflecting cancelled state.

        Raises:
            OrderNotFoundError: If order does not exist.
            BrokerConnectionError: If exchange is unreachable.
        """

    @abstractmethod
    async def get_order_status(
        self, order_id: str, symbol: str
    ) -> OrderResult:
        """Query current order status from the exchange.

        Args:
            order_id: Exchange-assigned order ID.
            symbol: Trading pair (e.g., "BTCUSDT").

        Returns:
            OrderResult with current status.

        Raises:
            OrderNotFoundError: If order does not exist.
            BrokerConnectionError: If exchange is unreachable.
        """

    @abstractmethod
    async def get_account_balance(self) -> list[Balance]:
        """Get account balance for all assets.

        Returns:
            List of Balance objects for each asset with non-zero balance.

        Raises:
            BrokerConnectionError: If exchange is unreachable.
        """

    @abstractmethod
    async def validate_symbol(self, symbol: str) -> bool:
        """Check if a trading symbol is valid and tradeable.

        Args:
            symbol: Trading pair to validate (e.g., "BTCUSDT").

        Returns:
            True if symbol is valid and tradeable, False otherwise.
        """
