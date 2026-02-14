"""Fill rate tracking model for execution quality monitoring.

Records order fill times, cancellations, and rejections for
historical analysis of execution quality by symbol and order type.

Decision: DEC-2026-02-08-002 - SQLAlchemy 2.0 with Mapped[T]
Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
Decision: DEC-2026-02-08-007 - Input validation at model layer

Phase 4B: Position Tracking & Execution Quality
"""
from __future__ import annotations

import math
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, validates

from .base import Base, TimestampMixin, generate_id


class FillRateRecord(Base, TimestampMixin):
    """Fill rate record for execution quality tracking.

    Each record captures the outcome of an order submission
    (filled, cancelled, or rejected) and the associated timing.

    Attributes:
        id: Unique identifier (format: fillr_YYYYMMDDHHMMSS_uuid).
        order_id: Reference to the parent order.
        symbol: Trading pair symbol.
        order_type: Type of order (e.g., "market", "limit").
        submitted_at: When the order was submitted to the exchange.
        filled_at: When the order was filled (None if not filled).
        cancelled_at: When the order was cancelled (None if not cancelled).
        rejected_at: When the order was rejected (None if not rejected).
        time_to_fill_seconds: Seconds from submission to fill.
        status: Final status ("filled", "cancelled", "rejected").
    """

    __tablename__ = "fill_rate_records"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: generate_id("fillr"),
    )

    # Foreign key
    order_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("orders.id"),
        nullable=False,
        index=True,
    )

    # Order details
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Timing
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    time_to_fill_seconds: Mapped[float | None] = mapped_column(Float)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    @validates("time_to_fill_seconds")
    def validate_time_to_fill(
        self, key: str, value: float | None
    ) -> float | None:
        """Validate time to fill is non-negative and not NaN/Infinity.

        Args:
            key: Field name being validated.
            value: Value to validate.

        Returns:
            Validated value.

        Raises:
            ValueError: If value is NaN, Infinity, or negative.
        """
        if value is None:
            return value
        if math.isnan(value):
            raise ValueError(f"{key} cannot be NaN")
        if math.isinf(value):
            raise ValueError(f"{key} cannot be Infinity")
        if value < 0:
            raise ValueError(f"{key} must be non-negative, got {value}")
        return value

    def __repr__(self) -> str:
        """String representation of the fill rate record."""
        return (
            f"<FillRateRecord(id={self.id}, symbol={self.symbol}, "
            f"status={self.status})>"
        )
