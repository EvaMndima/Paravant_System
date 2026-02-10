"""Health check system for monitoring component status.

Provides a registry-based health checker that runs component checks
in parallel and computes an overall system health status.

Health Status Logic:
- HEALTHY: All components report healthy status.
- DEGRADED: Some non-critical components are unhealthy.
- UNHEALTHY: One or more critical components (database, exchange) are down.
- UNKNOWN: Health status could not be determined.

Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
"""
from __future__ import annotations

import asyncio
import enum
import inspect
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Type alias for async health check functions
HealthCheckFunc = Callable[[], Awaitable["ComponentHealth"]]


class HealthStatus(str, enum.Enum):
    """Health check status values.

    Attributes:
        HEALTHY: Component is functioning normally.
        DEGRADED: Component is operational but below optimal.
        UNHEALTHY: Component is down or non-functional.
        UNKNOWN: Component status could not be determined.
    """

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


# Critical components whose failure makes the entire system unhealthy
CRITICAL_COMPONENTS: frozenset[str] = frozenset({
    "database",
    "exchange",
})


@dataclass
class ComponentHealth:
    """Health status of a single system component.

    Attributes:
        name: Component identifier (e.g., 'database', 'exchange').
        status: Current health status of the component.
        latency_ms: Time taken to perform the health check (ms).
        message: Human-readable status message.
        details: Additional diagnostic information.
    """

    name: str
    status: HealthStatus
    latency_ms: float = 0.0
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize component health to a dictionary.

        Returns:
            Dictionary representation of the component health.
        """
        return {
            "name": self.name,
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 2),
            "message": self.message,
            "details": self.details,
        }


@dataclass
class SystemHealth:
    """Overall system health aggregated from component checks.

    Attributes:
        overall_status: Computed overall health status.
        components: Individual component health results.
        timestamp: When the health check was performed (UTC).
        check_duration_ms: Total time to run all checks (ms).
    """

    overall_status: HealthStatus
    components: list[ComponentHealth]
    timestamp: datetime
    check_duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize system health to a dictionary.

        Returns:
            Dictionary representation suitable for API responses.
        """
        return {
            "overall_status": self.overall_status.value,
            "components": [c.to_dict() for c in self.components],
            "timestamp": self.timestamp.isoformat(),
            "check_duration_ms": round(self.check_duration_ms, 2),
        }


class HealthChecker:
    """Registry-based health checker with parallel execution.

    Manages a collection of named health check functions and provides
    methods to run them concurrently and compute the overall system
    health status.

    Example::

        checker = HealthChecker()
        checker.register("database", check_database_health)
        checker.register("exchange", check_exchange_health)

        health = await checker.run_checks()
        print(health.overall_status)  # HealthStatus.HEALTHY
    """

    def __init__(self) -> None:
        """Initialize the health checker with an empty registry.

        HIGH-012 fix: Uses RLock to prevent race conditions when
        register/unregister are called while run_checks() is iterating.
        """
        self._checks: dict[str, HealthCheckFunc] = {}
        self._lock = threading.RLock()  # Reentrant lock allows nested acquire

    def register(self, name: str, check_func: HealthCheckFunc) -> None:
        """Register a health check function (thread-safe).

        Args:
            name: Unique component name for this check.
            check_func: Async function that returns ComponentHealth.

        Raises:
            TypeError: If check_func is not an async function.
        """
        # MEDIUM-013: Validate check_func is actually async
        if not inspect.iscoroutinefunction(check_func):
            raise TypeError(
                f"check_func must be async function, got {type(check_func).__name__}. "
                f"Did you forget 'async def'?"
            )

        with self._lock:
            self._checks[name] = check_func
        logger.debug(
            "health_check_registered",
            component=name,
        )

    def unregister(self, name: str) -> None:
        """Remove a health check function from the registry (thread-safe).

        Args:
            name: The component name to remove.
        """
        with self._lock:
            self._checks.pop(name, None)

    @property
    def registered_checks(self) -> list[str]:
        """Get list of registered check names.

        Returns:
            Sorted list of registered component names.
        """
        return sorted(self._checks.keys())

    async def run_checks(self) -> SystemHealth:
        """Run all registered health checks in parallel (thread-safe).

        Each check is executed concurrently using ``asyncio.gather``.
        If a check raises an exception, it is caught and recorded as
        an UNKNOWN status for that component.

        HIGH-012 fix: Creates snapshot of checks dict inside lock to
        prevent "dictionary changed size during iteration" errors if
        register/unregister are called concurrently.

        Returns:
            SystemHealth with overall status and per-component results.
        """
        start_time = time.monotonic()
        check_timestamp = datetime.now(timezone.utc)

        # HIGH-012: Snapshot checks dict inside lock to prevent concurrent modification
        with self._lock:
            if not self._checks:
                return SystemHealth(
                    overall_status=HealthStatus.HEALTHY,
                    components=[],
                    timestamp=check_timestamp,
                    check_duration_ms=0.0,
                )
            # Create snapshot of checks to iterate safely
            checks_snapshot = list(self._checks.items())

        # Run all checks concurrently (outside lock - checks are async and independent)
        tasks = [
            self._run_single_check(name, check_func)
            for name, check_func in checks_snapshot
        ]
        components = await asyncio.gather(*tasks)

        # Compute overall status
        overall_status = self._compute_overall_status(list(components))
        check_duration_ms = (time.monotonic() - start_time) * 1000

        logger.info(
            "health_check_completed",
            overall_status=overall_status.value,
            component_count=len(components),
            duration_ms=round(check_duration_ms, 2),
        )

        return SystemHealth(
            overall_status=overall_status,
            components=list(components),
            timestamp=check_timestamp,
            check_duration_ms=check_duration_ms,
        )

    async def _run_single_check(
        self, name: str, check_func: HealthCheckFunc
    ) -> ComponentHealth:
        """Run a single health check with error handling and timeout.

        MEDIUM-012: 10-second timeout prevents hung health checks from
        blocking the API. Timeout failures return UNKNOWN status.

        Args:
            name: Component name.
            check_func: The async health check function.

        Returns:
            ComponentHealth result (UNKNOWN status on exception or timeout).
        """
        start_time = time.monotonic()
        try:
            # MEDIUM-012: 10s timeout for individual health checks
            result = await asyncio.wait_for(check_func(), timeout=10.0)
            # Ensure the returned component has the correct name
            result.name = name
            result.latency_ms = (time.monotonic() - start_time) * 1000
            return result
        except asyncio.TimeoutError:
            # Health check exceeded timeout
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "health_check_timeout",
                component=name,
                timeout_seconds=10.0,
                latency_ms=round(latency_ms, 2),
            )
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNKNOWN,
                latency_ms=latency_ms,
                message=f"Health check exceeded 10s timeout",
            )
        except Exception as exc:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "health_check_failed",
                component=name,
                error=str(exc),
                latency_ms=round(latency_ms, 2),
            )
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNKNOWN,
                latency_ms=latency_ms,
                message=f"Check failed: {exc}",
                details={"error": str(exc)},
            )

    @staticmethod
    def _compute_overall_status(
        components: list[ComponentHealth],
    ) -> HealthStatus:
        """Compute overall system health from component results.

        Logic:
        - If no components, return HEALTHY.
        - If all components are HEALTHY, return HEALTHY.
        - If any critical component is UNHEALTHY or UNKNOWN, return UNHEALTHY.
        - Otherwise, return DEGRADED.

        Args:
            components: List of individual component health results.

        Returns:
            The computed overall HealthStatus.
        """
        if not components:
            return HealthStatus.HEALTHY

        # Check if all components are healthy
        if all(c.status == HealthStatus.HEALTHY for c in components):
            return HealthStatus.HEALTHY

        # Check if any critical component is down
        critical_down = any(
            c.name in CRITICAL_COMPONENTS
            and c.status in (HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN)
            for c in components
        )

        if critical_down:
            return HealthStatus.UNHEALTHY

        return HealthStatus.DEGRADED
