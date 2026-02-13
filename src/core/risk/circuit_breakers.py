"""Stateful circuit breaker framework for risk management.

Circuit breakers differ from pure risk checks (checks.py) in that they
maintain persistent state. Once tripped, a breaker stays active until
its cooldown expires or it is manually reset. This prevents trading
resumption during brief recovery periods in losing streaks.

Classes:
    CircuitBreakerResult: Immutable result of a circuit breaker evaluation.
    CircuitBreaker: ABC for all circuit breaker implementations.
    DailyLossCircuitBreaker: Trips on excessive daily loss.
    WeeklyLossCircuitBreaker: Trips on excessive weekly loss.
    DrawdownCircuitBreaker: Trips on excessive drawdown.
    ConsecutiveLossCircuitBreaker: Trips on consecutive losing trades.
    CorrelationCircuitBreaker: Trips on correlated position concentration.
    CircuitBreakerManager: Coordinates all breakers with persistence.

Decision: DEC-2026-02-12-009 - Circuit breakers are stateful classes
Decision: DEC-2026-02-12-010 - Complement existing pure checks
Decision: DEC-2026-02-12-012 - Injectable datetime for testability
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from src.core.config.risk_profiles import RiskProfileConfig
from src.core.risk.types import PortfolioState
from src.data.store import DataStore
from src.utils.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CircuitBreakerResult:
    """Immutable result of a circuit breaker evaluation.

    Attributes:
        breaker_name: Identifier for the circuit breaker.
        is_triggered: Whether the breaker is currently tripped.
        current_value: The metric value that was evaluated.
        threshold: The threshold that triggers the breaker.
        triggered_at: When the breaker was first triggered.
        auto_reset_at: When the breaker will auto-reset (if applicable).
        message: Human-readable status message.
    """

    breaker_name: str
    is_triggered: bool
    current_value: float
    threshold: float
    triggered_at: datetime | None = None
    auto_reset_at: datetime | None = None
    message: str = ""

    def __post_init__(self) -> None:
        """Validate result fields.

        Raises:
            ValueError: If numeric fields are NaN or Infinity.
        """
        if math.isnan(self.current_value):
            raise ValueError("current_value cannot be NaN")
        if math.isinf(self.current_value):
            raise ValueError("current_value cannot be Infinity")
        if math.isnan(self.threshold):
            raise ValueError("threshold cannot be NaN")
        if math.isinf(self.threshold):
            raise ValueError("threshold cannot be Infinity")


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class CircuitBreaker(ABC):
    """Abstract base class for all circuit breakers.

    Subclasses must implement:
        - name (property): Unique identifier string.
        - _evaluate(): Core logic that determines if breaker should trip.

    The base class handles cooldown management, state serialization,
    and the check() orchestration pattern.

    Decision: DEC-2026-02-12-012 - Injectable datetime via `now` param.
    """

    def __init__(self, cooldown_minutes: int = 60) -> None:
        """Initialize the circuit breaker.

        Args:
            cooldown_minutes: Minutes before auto-reset after triggering.
        """
        self._is_triggered: bool = False
        self._triggered_at: datetime | None = None
        self._cooldown_minutes: int = cooldown_minutes

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this circuit breaker."""

    @abstractmethod
    def _evaluate(
        self,
        portfolio: PortfolioState,
        profile: RiskProfileConfig,
    ) -> tuple[bool, float, float, str]:
        """Core evaluation logic.

        Args:
            portfolio: Current portfolio state.
            profile: Risk profile configuration.

        Returns:
            Tuple of (should_trigger, current_value, threshold, message).
        """

    def check(
        self,
        portfolio: PortfolioState,
        profile: RiskProfileConfig,
        now: datetime | None = None,
    ) -> CircuitBreakerResult:
        """Evaluate the circuit breaker against current state.

        If already triggered, checks if cooldown has elapsed.
        If not triggered, evaluates whether conditions warrant tripping.

        Args:
            portfolio: Current portfolio state snapshot.
            profile: Risk profile configuration.
            now: Current time (injectable for testing).

        Returns:
            CircuitBreakerResult with current status.
        """
        now = now or datetime.now(timezone.utc)

        # Check if cooldown has elapsed for already-triggered breaker
        if self._is_triggered and self._triggered_at is not None:
            auto_reset_at = self._triggered_at + timedelta(
                minutes=self._cooldown_minutes
            )
            if now >= auto_reset_at:
                logger.info(
                    "circuit_breaker_auto_reset",
                    breaker=self.name,
                    triggered_at=self._triggered_at.isoformat(),
                    reset_at=now.isoformat(),
                )
                self._is_triggered = False
                self._triggered_at = None

        # Evaluate current conditions
        should_trigger, current_value, threshold, message = self._evaluate(
            portfolio, profile
        )

        if should_trigger and not self._is_triggered:
            # Trip the breaker
            self._is_triggered = True
            self._triggered_at = now
            logger.warning(
                "circuit_breaker_triggered",
                breaker=self.name,
                current_value=current_value,
                threshold=threshold,
                message=message,
            )

        auto_reset_at: datetime | None = None
        if self._is_triggered and self._triggered_at is not None:
            auto_reset_at = self._triggered_at + timedelta(
                minutes=self._cooldown_minutes
            )

        return CircuitBreakerResult(
            breaker_name=self.name,
            is_triggered=self._is_triggered,
            current_value=current_value,
            threshold=threshold,
            triggered_at=self._triggered_at,
            auto_reset_at=auto_reset_at,
            message=message if self._is_triggered else "",
        )

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        if self._is_triggered:
            logger.info(
                "circuit_breaker_manual_reset",
                breaker=self.name,
            )
        self._is_triggered = False
        self._triggered_at = None

    @property
    def is_triggered(self) -> bool:
        """Whether the breaker is currently tripped."""
        return self._is_triggered

    def to_dict(self) -> dict[str, Any]:
        """Serialize breaker state for persistence.

        Returns:
            Dictionary with breaker state suitable for JSON storage.
        """
        return {
            "name": self.name,
            "is_triggered": self._is_triggered,
            "triggered_at": (
                self._triggered_at.isoformat()
                if self._triggered_at
                else None
            ),
            "cooldown_minutes": self._cooldown_minutes,
        }

    def restore_from_dict(self, data: dict[str, Any]) -> None:
        """Restore breaker state from persisted data.

        Args:
            data: Dictionary previously returned by to_dict().
        """
        self._is_triggered = bool(data.get("is_triggered", False))
        triggered_at_str = data.get("triggered_at")
        if triggered_at_str and isinstance(triggered_at_str, str):
            self._triggered_at = datetime.fromisoformat(triggered_at_str)
            # Ensure timezone-aware (DEC-2026-02-08-003)
            if self._triggered_at.tzinfo is None:
                self._triggered_at = self._triggered_at.replace(
                    tzinfo=timezone.utc
                )
        else:
            self._triggered_at = None


# ---------------------------------------------------------------------------
# Concrete implementations
# ---------------------------------------------------------------------------


class DailyLossCircuitBreaker(CircuitBreaker):
    """Trips when daily loss exceeds the profile's daily_loss_limit_pct.

    Auto-resets after cooldown period elapses. Complements the
    stateless check_daily_loss_limit() in checks.py by maintaining
    a persistent tripped state.

    Decision: DEC-2026-02-12-010 - Complements pure check.
    """

    @property
    def name(self) -> str:
        """Unique identifier for this breaker."""
        return "daily_loss"

    def _evaluate(
        self,
        portfolio: PortfolioState,
        profile: RiskProfileConfig,
    ) -> tuple[bool, float, float, str]:
        """Evaluate daily loss against threshold.

        Returns:
            Tuple of (should_trigger, daily_loss_pct, limit_pct, message).
        """
        threshold = profile.daily_loss_limit_pct

        if portfolio.total_equity <= 0:
            return (True, 0.0, threshold, "Zero or negative equity")

        if portfolio.daily_pnl >= 0:
            return (False, 0.0, threshold, "")

        daily_loss_pct = (
            abs(portfolio.daily_pnl) / portfolio.total_equity * 100
        )

        if daily_loss_pct >= threshold:
            message = (
                f"Daily loss {daily_loss_pct:.2f}% exceeds "
                f"limit {threshold:.1f}%"
            )
            return (True, daily_loss_pct, threshold, message)

        return (False, daily_loss_pct, threshold, "")


class WeeklyLossCircuitBreaker(CircuitBreaker):
    """Trips when weekly loss exceeds the profile's weekly_loss_limit_pct.

    Auto-resets after cooldown period elapses.
    """

    @property
    def name(self) -> str:
        """Unique identifier for this breaker."""
        return "weekly_loss"

    def _evaluate(
        self,
        portfolio: PortfolioState,
        profile: RiskProfileConfig,
    ) -> tuple[bool, float, float, str]:
        """Evaluate weekly loss against threshold.

        Returns:
            Tuple of (should_trigger, weekly_loss_pct, limit_pct, message).
        """
        threshold = profile.weekly_loss_limit_pct

        if portfolio.total_equity <= 0:
            return (True, 0.0, threshold, "Zero or negative equity")

        if portfolio.weekly_pnl >= 0:
            return (False, 0.0, threshold, "")

        weekly_loss_pct = (
            abs(portfolio.weekly_pnl) / portfolio.total_equity * 100
        )

        if weekly_loss_pct >= threshold:
            message = (
                f"Weekly loss {weekly_loss_pct:.2f}% exceeds "
                f"limit {threshold:.1f}%"
            )
            return (True, weekly_loss_pct, threshold, message)

        return (False, weekly_loss_pct, threshold, "")


class DrawdownCircuitBreaker(CircuitBreaker):
    """Trips when drawdown exceeds the profile's max_drawdown_pct.

    Auto-resets when drawdown recovers below 80% of the threshold
    OR when cooldown elapses. The 80% recovery requirement prevents
    premature reset during volatile drawdown oscillations.
    """

    RECOVERY_FACTOR: float = 0.8

    @property
    def name(self) -> str:
        """Unique identifier for this breaker."""
        return "drawdown"

    def check(
        self,
        portfolio: PortfolioState,
        profile: RiskProfileConfig,
        now: datetime | None = None,
    ) -> CircuitBreakerResult:
        """Override check to add recovery-based reset logic.

        In addition to cooldown-based reset, this breaker also resets
        when drawdown recovers below threshold * RECOVERY_FACTOR.

        Args:
            portfolio: Current portfolio state snapshot.
            profile: Risk profile configuration.
            now: Current time (injectable for testing).

        Returns:
            CircuitBreakerResult with current status.
        """
        now = now or datetime.now(timezone.utc)

        # Check recovery-based reset before standard evaluation
        if self._is_triggered:
            recovery_threshold = (
                profile.max_drawdown_pct * self.RECOVERY_FACTOR
            )
            if portfolio.drawdown_pct < recovery_threshold:
                logger.info(
                    "circuit_breaker_recovery_reset",
                    breaker=self.name,
                    drawdown_pct=portfolio.drawdown_pct,
                    recovery_threshold=recovery_threshold,
                )
                self._is_triggered = False
                self._triggered_at = None

        # Continue with standard check (handles cooldown reset too)
        return super().check(portfolio, profile, now)

    def _evaluate(
        self,
        portfolio: PortfolioState,
        profile: RiskProfileConfig,
    ) -> tuple[bool, float, float, str]:
        """Evaluate drawdown against threshold.

        Returns:
            Tuple of (should_trigger, drawdown_pct, limit_pct, message).
        """
        threshold = profile.max_drawdown_pct

        if portfolio.drawdown_pct >= threshold:
            message = (
                f"Drawdown {portfolio.drawdown_pct:.2f}% exceeds "
                f"limit {threshold:.1f}%"
            )
            return (True, portfolio.drawdown_pct, threshold, message)

        return (False, portfolio.drawdown_pct, threshold, "")


class ConsecutiveLossCircuitBreaker(CircuitBreaker):
    """Trips when consecutive losing trades reach the threshold.

    Default threshold is 5 consecutive losses. Auto-resets after
    cooldown period.
    """

    def __init__(
        self,
        threshold: int = 5,
        cooldown_minutes: int = 60,
    ) -> None:
        """Initialize with loss count threshold.

        Args:
            threshold: Number of consecutive losses to trigger.
            cooldown_minutes: Minutes before auto-reset.
        """
        super().__init__(cooldown_minutes=cooldown_minutes)
        self._threshold: int = threshold

    @property
    def name(self) -> str:
        """Unique identifier for this breaker."""
        return "consecutive_loss"

    def _evaluate(
        self,
        portfolio: PortfolioState,
        profile: RiskProfileConfig,
    ) -> tuple[bool, float, float, str]:
        """Evaluate consecutive loss count against threshold.

        Returns:
            Tuple of (should_trigger, losses, threshold, message).
        """
        losses = float(portfolio.consecutive_losses)
        threshold = float(self._threshold)

        if portfolio.consecutive_losses >= self._threshold:
            message = (
                f"{portfolio.consecutive_losses} consecutive losses "
                f"(limit: {self._threshold})"
            )
            return (True, losses, threshold, message)

        return (False, losses, threshold, "")


class CorrelationCircuitBreaker(CircuitBreaker):
    """Trips when too many positions exist in the same symbol.

    For MVP, this performs a simple duplicate-symbol check rather
    than computing a full correlation matrix. The threshold is
    the maximum allowed positions per symbol (default 1).

    A full correlation matrix implementation is planned for V1.
    """

    def __init__(
        self,
        max_per_symbol: int = 1,
        cooldown_minutes: int = 60,
    ) -> None:
        """Initialize with max positions per symbol.

        Args:
            max_per_symbol: Max concurrent positions in one symbol.
            cooldown_minutes: Minutes before auto-reset.
        """
        super().__init__(cooldown_minutes=cooldown_minutes)
        self._max_per_symbol: int = max_per_symbol

    @property
    def name(self) -> str:
        """Unique identifier for this breaker."""
        return "correlation"

    def _evaluate(
        self,
        portfolio: PortfolioState,
        profile: RiskProfileConfig,
    ) -> tuple[bool, float, float, str]:
        """Evaluate position concentration per symbol.

        Returns:
            Tuple of (should_trigger, max_count, threshold, message).
        """
        threshold = float(self._max_per_symbol)

        # Count positions per symbol
        symbol_counts: dict[str, int] = {}
        for position in portfolio.open_positions:
            symbol = position.symbol
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1

        if not symbol_counts:
            return (False, 0.0, threshold, "")

        max_count = max(symbol_counts.values())
        max_symbol = max(symbol_counts, key=symbol_counts.get)  # type: ignore[arg-type]

        if max_count > self._max_per_symbol:
            message = (
                f"{max_symbol} has {max_count} positions "
                f"(max: {self._max_per_symbol})"
            )
            return (True, float(max_count), threshold, message)

        return (False, float(max_count), threshold, "")


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class CircuitBreakerManager:
    """Coordinates all circuit breakers with state persistence.

    Evaluates all registered breakers, tracks triggered state,
    and persists/restores state via SystemState.circuit_breakers
    JSON field in the database.

    Attributes:
        breakers: List of registered CircuitBreaker instances.
    """

    def __init__(
        self,
        breakers: list[CircuitBreaker],
        store: DataStore,
    ) -> None:
        """Initialize the manager with breakers and store.

        Args:
            breakers: List of circuit breaker instances to manage.
            store: DataStore for state persistence.
        """
        self._breakers: list[CircuitBreaker] = list(breakers)
        self._store: DataStore = store

    @property
    def breakers(self) -> list[CircuitBreaker]:
        """Get all registered breakers."""
        return list(self._breakers)

    def check_all(
        self,
        portfolio: PortfolioState,
        profile: RiskProfileConfig,
        now: datetime | None = None,
    ) -> list[CircuitBreakerResult]:
        """Evaluate all circuit breakers.

        Args:
            portfolio: Current portfolio state snapshot.
            profile: Risk profile configuration.
            now: Current time (injectable for testing).

        Returns:
            List of results, one per breaker.
        """
        results: list[CircuitBreakerResult] = []
        for breaker in self._breakers:
            result = breaker.check(portfolio, profile, now)
            results.append(result)
        return results

    def any_triggered(self) -> bool:
        """Check if any breaker is currently tripped.

        Returns:
            True if at least one breaker is triggered.
        """
        return any(b.is_triggered for b in self._breakers)

    def get_triggered(self) -> list[str]:
        """Get names of all currently triggered breakers.

        Returns:
            List of breaker name strings.
        """
        return [b.name for b in self._breakers if b.is_triggered]

    def reset(self, breaker_name: str) -> None:
        """Reset a specific breaker by name.

        Args:
            breaker_name: Name of the breaker to reset.

        Raises:
            ValueError: If breaker_name not found.
        """
        for breaker in self._breakers:
            if breaker.name == breaker_name:
                breaker.reset()
                logger.info(
                    "circuit_breaker_reset_by_manager",
                    breaker=breaker_name,
                )
                return
        raise ValueError(
            f"Circuit breaker '{breaker_name}' not found. "
            f"Available: {[b.name for b in self._breakers]}"
        )

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers:
            breaker.reset()
        logger.info(
            "circuit_breakers_all_reset",
            count=len(self._breakers),
        )

    def persist_state(self) -> None:
        """Save all breaker states to the database.

        Serializes each breaker's state to a dict and stores
        in SystemState.circuit_breakers JSON field. The dict
        uses breaker names as keys with boolean triggered values
        at the top level (compatible with SystemState.any_circuit_breaker_active)
        and detailed state in a nested "_state" key.
        """
        # Top-level: {name: bool} for SystemState.any_circuit_breaker_active
        state_dict: dict[str, Any] = {}
        for breaker in self._breakers:
            state_dict[breaker.name] = breaker.is_triggered

        # Nested detail for restore
        state_dict["_state"] = {
            b.name: b.to_dict() for b in self._breakers
        }

        try:
            self._store.update_system_state(circuit_breakers=state_dict)
            logger.info(
                "circuit_breakers_state_persisted",
                triggered=self.get_triggered(),
            )
        except Exception as e:
            logger.error(
                "circuit_breakers_persist_failed",
                error=str(e),
                exc_info=True,
            )

    def restore_state(self) -> None:
        """Load breaker states from the database.

        Reads from SystemState.circuit_breakers JSON field and
        restores each breaker's internal state.
        """
        try:
            system_state = self._store.get_system_state()
            stored = system_state.circuit_breakers

            if not stored or "_state" not in stored:
                logger.info("circuit_breakers_no_state_to_restore")
                return

            detail = stored["_state"]
            for breaker in self._breakers:
                if breaker.name in detail:
                    breaker.restore_from_dict(detail[breaker.name])

            logger.info(
                "circuit_breakers_state_restored",
                triggered=self.get_triggered(),
            )
        except Exception as e:
            logger.error(
                "circuit_breakers_restore_failed",
                error=str(e),
                exc_info=True,
            )
