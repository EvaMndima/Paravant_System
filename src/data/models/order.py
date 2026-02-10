"""Order model for tracking all orders."""
from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime
import enum

from sqlalchemy import String, Float, ForeignKey, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
import math

from .base import Base, TimestampMixin, generate_id

if TYPE_CHECKING:
    from .account import Account
    from .strategy import Strategy
    from .trade import Trade


class OrderSide(str, enum.Enum):
    """Order side enum."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, enum.Enum):
    """Order type enum."""

    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, enum.Enum):
    """Order status enum."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Order(Base, TimestampMixin):
    """Order model with execution tracking."""

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: generate_id("ord"))
    external_id: Mapped[str | None] = mapped_column(String(100))  # Exchange order ID

    # References
    account_id: Mapped[str] = mapped_column(String, ForeignKey("accounts.id"), nullable=False)
    strategy_id: Mapped[str | None] = mapped_column(String, ForeignKey("strategies.id"))

    # Order details
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)
    type: Mapped[OrderType] = mapped_column(Enum(OrderType), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float | None] = mapped_column(Float)  # For limit orders
    stop_price: Mapped[float | None] = mapped_column(Float)  # For stop orders

    # Execution
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    filled_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    filled_price: Mapped[float | None] = mapped_column(Float)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Rejection
    rejection_reason: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="orders")
    strategy: Mapped["Strategy | None"] = relationship("Strategy", back_populates="orders")
    trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="order")

    @validates("quantity", "price", "stop_price", "filled_quantity", "filled_price")
    def validate_numeric_values(self, key: str, value: float | None) -> float | None:
        """Validate numeric values are positive and not NaN/Infinity.

        Args:
            key: Field name being validated
            value: Value to validate

        Returns:
            Validated value

        Raises:
            ValueError: If value is invalid
        """
        if value is None:
            # Allow None for optional fields (price, stop_price, filled_price)
            if key in ["price", "stop_price", "filled_price"]:
                return value
            raise ValueError(f"{key} cannot be None")

        if math.isnan(value):
            raise ValueError(f"{key} cannot be NaN")
        if math.isinf(value):
            raise ValueError(f"{key} cannot be Infinity")

        # filled_quantity can be 0 (order not yet filled), but not negative
        if key == "filled_quantity":
            if value < 0:
                raise ValueError(f"{key} must be non-negative, got {value}")
        else:
            # All other fields must be positive (> 0)
            if value <= 0:
                raise ValueError(f"{key} must be positive, got {value}")

        return value

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, symbol={self.symbol}, side={self.side}, status={self.status})>"
