"""System state tracking and audit logging models.

This module provides models for:
- SystemState: Singleton tracking overall system state and kill switch
- AuditLog: Immutable record of all critical system actions
"""
from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy import String, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, generate_id


class SystemState(Base):
    """Track system state for recovery and audit (singleton pattern).

    This model uses a singleton pattern (single row with fixed ID) to track
    the global system state including kill switch status, trading enabled/disabled,
    circuit breakers, and health status.

    Attributes:
        id: Fixed ID for singleton ("system_state_singleton")
        kill_switch_active: Whether the kill switch is currently active
        kill_switch_activated_at: When the kill switch was activated
        kill_switch_reason: Why the kill switch was activated
        trading_enabled: Whether trading is currently enabled
        last_trade_at: When the last trade was executed
        last_health_check: When the last health check ran
        health_status: Current health status (healthy/degraded/unhealthy)
        circuit_breakers: State of all circuit breakers (JSON)
        started_at: When the system was started
        updated_at: When this record was last updated
    """

    __tablename__ = 'system_state'

    # Singleton ID - always the same value
    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default="system_state_singleton"
    )

    # Kill switch state
    kill_switch_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    kill_switch_activated_at: Mapped[datetime | None] = mapped_column(DateTime)
    kill_switch_reason: Mapped[str | None] = mapped_column(
        String(500)  # Why the kill switch was activated
    )

    # Trading state
    trading_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )
    last_trade_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Health monitoring
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime)
    health_status: Mapped[str] = mapped_column(
        String(50),
        default="unknown"  # healthy/degraded/unhealthy/unknown
    )

    # Circuit breakers state (avoid mutable default bug)
    # Structure: {"daily_loss": false, "drawdown": false, "correlation": false}
    circuit_breakers: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=lambda: cast(dict[str, Any], {})
    )

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    @property
    def is_safe_to_trade(self) -> bool:
        """Check if trading is safe (kill switch off and trading enabled).

        Returns:
            True if both kill switch is inactive and trading is enabled
        """
        return not self.kill_switch_active and self.trading_enabled

    @property
    def any_circuit_breaker_active(self) -> bool:
        """Check if any circuit breaker is currently active.

        Returns:
            True if any circuit breaker is tripped
        """
        if not self.circuit_breakers:
            return False
        return any(self.circuit_breakers.values())

    def __repr__(self) -> str:
        """String representation of system state."""
        return (
            f"<SystemState(kill_switch={self.kill_switch_active}, "
            f"trading={self.trading_enabled}, "
            f"health={self.health_status})>"
        )


class AuditLog(Base):
    """Audit log for critical actions with immutable record.

    This model provides an append-only audit trail of all critical system actions
    for compliance, debugging, and incident investigation.

    Attributes:
        id: Unique identifier (generated)
        timestamp: When the action occurred
        action: Type of action (e.g., "kill_switch_activated", "order_placed")
        actor: Who/what initiated the action (e.g., "system", "user", "api")
        details: Additional context about the action (JSON)

    Examples of logged actions:
        - Kill switch activation/deactivation
        - Circuit breaker triggers
        - Strategy approval/retirement
        - Manual trades
        - Configuration changes
        - System errors requiring intervention
    """

    __tablename__ = 'audit_logs'

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: generate_id("audit")
    )

    # When the action occurred
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,  # Index for time-based queries
        default=lambda: datetime.now(timezone.utc)
    )

    # What action was taken
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True  # Index for filtering by action type
    )

    # Who initiated the action
    actor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True  # Index for filtering by actor
        # Values: "system", "user", "api", "scheduler", "risk_controller", etc.
    )

    # Additional context (avoid mutable default bug)
    # Structure varies by action type, examples:
    # - kill_switch: {"reason": "...", "previous_state": false}
    # - order_placed: {"symbol": "BTCUSDT", "side": "buy", "quantity": 0.1}
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        default=lambda: cast(dict[str, Any] | None, None)
    )

    def __repr__(self) -> str:
        """String representation of the audit log entry."""
        return (
            f"<AuditLog({self.timestamp.isoformat()}: "
            f"{self.action} by {self.actor})>"
        )
