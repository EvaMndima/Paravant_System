"""Trade model for recording executed fills.

This model tracks individual trade executions (fills) from orders.
Each order can have multiple trades if it's partially filled.
"""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Float, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column, validates
import math

from .base import Base, TimestampMixin, generate_id
from .order import OrderSide

if TYPE_CHECKING:
    from .order import Order


class Trade(Base, TimestampMixin):
    """Individual trade/fill record with full audit trail.

    A trade represents a single execution (fill) on the exchange. An order
    may result in multiple trades if it's filled in multiple chunks.

    Attributes:
        id: Unique trade identifier (format: trd_YYYYMMDDHHMMSS_uuid)
        order_id: Reference to the parent order
        account_id: Reference to the trading account
        symbol: Trading pair (e.g., BTCUSDT)
        side: Trade side (BUY or SELL)
        quantity: Amount traded
        price: Execution price
        commission: Trading commission/fee paid
        executed_at: When the trade was executed on exchange
        external_trade_id: Exchange's trade ID for reconciliation
        created_at: When this record was created (from TimestampMixin)
        updated_at: When this record was last updated (from TimestampMixin)
    """

    __tablename__ = 'trades'

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: generate_id("trd")
    )

    # Foreign key references
    order_id: Mapped[str] = mapped_column(
        String,
        ForeignKey('orders.id'),
        nullable=False,
        index=True  # Index for fast lookups by order
    )
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey('accounts.id'),
        nullable=False,
        index=True  # Index for fast lookups by account
    )

    # Trade details
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    commission: Mapped[float] = mapped_column(Float, default=0.0)

    # Execution information
    executed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True  # Index for time-based queries
    )
    external_trade_id: Mapped[str | None] = mapped_column(
        String(100)  # Exchange's trade ID for reconciliation
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="trades"
    )

    @validates("quantity", "price", "commission")
    def validate_numeric_values(self, key: str, value: float | None) -> float:
        """Validate numeric values are non-negative and not NaN/Infinity.

        SQLAlchemy validators can receive None during object construction,
        so the type signature must reflect this reality.

        Args:
            key: Field name being validated
            value: Value to validate (can be None during construction)

        Returns:
            Validated value

        Raises:
            ValueError: If value is invalid (None, NaN, Infinity, negative, zero)
        """
        if value is None:
            raise ValueError(f"{key} cannot be None")
        if math.isnan(value):
            raise ValueError(f"{key} cannot be NaN")
        if math.isinf(value):
            raise ValueError(f"{key} cannot be Infinity")
        if value < 0:
            raise ValueError(f"{key} must be non-negative, got {value}")
        if key in ["quantity", "price"] and value <= 0:
            raise ValueError(f"{key} must be positive, got {value}")
        return value

    @property
    def notional_value(self) -> float:
        """Calculate trade notional value.

        Returns:
            The total value of the trade (quantity * price)
        """
        return self.quantity * self.price

    @property
    def total_cost(self) -> float:
        """Calculate total cost including commission.

        Returns:
            The total cost of the trade including fees
        """
        return self.notional_value + self.commission

    def __repr__(self) -> str:
        """String representation of the trade."""
        return (
            f"<Trade(id={self.id}, "
            f"{self.side.value} {self.quantity} {self.symbol} @ {self.price})>"
        )
