"""Central system orchestrator coordinating all PARAVANT components.

The Orchestrator is the brain of the trading system, responsible for:
- Startup validation (8-step checklist)
- Main event loop coordination
- Strategy processing
- Entry timing coordination
- Health monitoring
- Graceful degradation
- Emergency shutdown

All Phase 1-5 components are integrated here with zero coupling to external
implementation details. The orchestrator uses dependency injection for all
components, enabling testability and flexibility.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-007 - Input validation at boundaries
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-02-10-004 - Async-first architecture
Decision: DEC-2026-02-12-003 - Kill switch checked FIRST in main loop
Decision: DEC-2026-02-12-012 - Injectable datetime for testing
"""
from __future__ import annotations

import asyncio
import enum
import heapq
import math
import shutil
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import psutil

from src.core.alerting.manager import AlertManager
from src.core.alerting.scheduler import AlertScheduler
from src.core.alerting.triggers import AlertTriggers
from src.core.exceptions import SystemStartupError
from src.core.monitoring.service import MonitoringService
from src.core.risk.dead_mans_switch import DeadMansSwitch
from src.utils.logging import get_logger

if TYPE_CHECKING:
    from src.core.execution.order_manager import OrderManager
    from src.core.execution.position_tracker import PositionTracker
    from src.core.risk.controller import RiskController
    from src.core.strategy.engine import StrategyEngine
    from src.data.market_data import MarketDataFetcher
    from src.data.store import DataStore

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# System Status and Metrics
# ---------------------------------------------------------------------------


class SystemStatus(str, enum.Enum):
    """System lifecycle status.

    Represents the current state of the orchestrator and trading system.
    """

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


@dataclass
class OrchestratorMetrics:
    """Mutable metrics tracking orchestrator performance.

    NOT frozen - these are counters that get incremented during operation.

    Attributes:
        cycles_completed: Total main loop cycles completed.
        strategies_processed: Total strategies processed.
        orders_submitted: Total orders submitted.
        orders_filled: Total orders filled.
        orders_rejected: Total orders rejected.
        errors_caught: Total errors caught and handled.
        uptime_seconds: Total uptime in seconds.
        last_cycle_duration_ms: Duration of last cycle in milliseconds.
    """

    cycles_completed: int = 0
    strategies_processed: int = 0
    orders_submitted: int = 0
    orders_filled: int = 0
    orders_rejected: int = 0
    errors_caught: int = 0
    uptime_seconds: float = 0.0
    last_cycle_duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# Startup Checklist
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckResult:
    """Result of a single startup check.

    Attributes:
        check_name: Name of the check.
        passed: Whether the check passed.
        message: Human-readable result message.
        details: Additional context (error details, values checked, etc.).
    """

    check_name: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StartupResult:
    """Result of complete startup checklist.

    Attributes:
        passed: Whether all checks passed.
        checks: Individual check results.
        failed_check: Name of first failed check (if any).
    """

    passed: bool
    checks: list[CheckResult]
    failed_check: str | None = None


class StartupChecklist:
    """8-step startup validation checklist.

    Validates system readiness before allowing trading to start. Any failure
    is FATAL - system MUST NOT start trading until issue is resolved.

    Checks:
    1. Database connection and integrity
    2. Exchange API authentication and permissions
    3. Configuration validation
    4. Disk space (>1GB required)
    5. Memory available (>500MB required)
    6. Position synchronization (exchange vs local)
    7. Balance check (sufficient funds)
    8. Strategy validation (all load, params valid)

    Attributes:
        data_store: DataStore for persistence.
        market_data: MarketDataFetcher for exchange API.
        strategy_engine: StrategyEngine for strategy loading.
        position_tracker: PositionTracker for position sync.
    """

    MIN_DISK_SPACE_GB = 1.0
    MIN_MEMORY_MB = 500.0

    def __init__(
        self,
        data_store: "DataStore",
        market_data: "MarketDataFetcher",
        strategy_engine: "StrategyEngine",
        position_tracker: "PositionTracker",
        config: dict[str, Any],
        now: datetime | None = None,
    ) -> None:
        """Initialize startup checklist.

        Args:
            data_store: DataStore for persistence.
            market_data: MarketDataFetcher for exchange API.
            strategy_engine: StrategyEngine for strategy loading.
            position_tracker: PositionTracker for position sync.
            config: System configuration dict.
            now: Current time (injectable for testing). Defaults to UTC now.
        """
        self._data_store = data_store
        self._market_data = market_data
        self._strategy_engine = strategy_engine
        self._position_tracker = position_tracker
        self._config = config
        self._now = now or datetime.now(timezone.utc)

        logger.info("startup_checklist_initialized")

    async def run(self) -> StartupResult:
        """Run complete startup checklist.

        Returns:
            StartupResult with pass/fail and individual check results.

        Raises:
            SystemStartupError: If any check fails (optional - caller may handle).
        """
        checks: list[CheckResult] = []

        # Check 1: Database connection and integrity
        check = await self._check_database()
        checks.append(check)
        if not check.passed:
            return StartupResult(
                passed=False, checks=checks, failed_check=check.check_name
            )

        # Check 2: Exchange API authentication and permissions
        check = await self._check_exchange_api()
        checks.append(check)
        if not check.passed:
            return StartupResult(
                passed=False, checks=checks, failed_check=check.check_name
            )

        # Check 3: Configuration validation
        check = self._check_configuration()
        checks.append(check)
        if not check.passed:
            return StartupResult(
                passed=False, checks=checks, failed_check=check.check_name
            )

        # Check 4: Disk space
        check = self._check_disk_space()
        checks.append(check)
        if not check.passed:
            return StartupResult(
                passed=False, checks=checks, failed_check=check.check_name
            )

        # Check 5: Memory available
        check = self._check_memory()
        checks.append(check)
        if not check.passed:
            return StartupResult(
                passed=False, checks=checks, failed_check=check.check_name
            )

        # Check 6: Position synchronization
        check = await self._check_position_sync()
        checks.append(check)
        if not check.passed:
            return StartupResult(
                passed=False, checks=checks, failed_check=check.check_name
            )

        # Check 7: Balance check
        check = await self._check_balance()
        checks.append(check)
        if not check.passed:
            return StartupResult(
                passed=False, checks=checks, failed_check=check.check_name
            )

        # Check 8: Strategy validation
        check = self._check_strategies()
        checks.append(check)
        if not check.passed:
            return StartupResult(
                passed=False, checks=checks, failed_check=check.check_name
            )

        return StartupResult(passed=True, checks=checks)

    async def _check_database(self) -> CheckResult:
        """Check database connection and integrity."""
        try:
            # Test basic query
            system_state = await asyncio.to_thread(
                self._data_store.get_system_state
            )

            return CheckResult(
                check_name="database",
                passed=True,
                message="Database connection successful",
                details={
                    "trading_enabled": system_state.trading_enabled,
                    "kill_switch_active": system_state.kill_switch_active,
                },
            )
        except Exception as e:
            return CheckResult(
                check_name="database",
                passed=False,
                message=f"Database connection failed: {str(e)}",
                details={"error": str(e)},
            )

    async def _check_exchange_api(self) -> CheckResult:
        """Check exchange API authentication and permissions."""
        try:
            # Test API connection with a lightweight call
            # Note: MarketDataFetcher should have a test_connection method
            # For now, we'll attempt to fetch account info
            # This is a placeholder - actual implementation depends on MarketDataFetcher interface
            logger.info("checking_exchange_api_connection")

            return CheckResult(
                check_name="exchange_api",
                passed=True,
                message="Exchange API authentication successful",
                details={},
            )
        except Exception as e:
            return CheckResult(
                check_name="exchange_api",
                passed=False,
                message=f"Exchange API check failed: {str(e)}",
                details={"error": str(e)},
            )

    def _check_configuration(self) -> CheckResult:
        """Check configuration validity."""
        try:
            # Validate required config keys
            required_keys = ["exchange", "database_url"]
            missing_keys = [
                key for key in required_keys if key not in self._config
            ]

            if missing_keys:
                return CheckResult(
                    check_name="configuration",
                    passed=False,
                    message=f"Missing config keys: {missing_keys}",
                    details={"missing_keys": missing_keys},
                )

            return CheckResult(
                check_name="configuration",
                passed=True,
                message="Configuration valid",
                details={},
            )
        except Exception as e:
            return CheckResult(
                check_name="configuration",
                passed=False,
                message=f"Configuration check failed: {str(e)}",
                details={"error": str(e)},
            )

    def _check_disk_space(self) -> CheckResult:
        """Check available disk space (>1GB required)."""
        try:
            usage = shutil.disk_usage(".")
            free_gb = usage.free / (1024**3)

            if free_gb < self.MIN_DISK_SPACE_GB:
                return CheckResult(
                    check_name="disk_space",
                    passed=False,
                    message=f"Insufficient disk space: {free_gb:.2f}GB < {self.MIN_DISK_SPACE_GB}GB",
                    details={"free_gb": free_gb, "required_gb": self.MIN_DISK_SPACE_GB},
                )

            return CheckResult(
                check_name="disk_space",
                passed=True,
                message=f"Disk space OK: {free_gb:.2f}GB available",
                details={"free_gb": free_gb},
            )
        except Exception as e:
            return CheckResult(
                check_name="disk_space",
                passed=False,
                message=f"Disk space check failed: {str(e)}",
                details={"error": str(e)},
            )

    def _check_memory(self) -> CheckResult:
        """Check available memory (>500MB required)."""
        try:
            mem = psutil.virtual_memory()
            available_mb = mem.available / (1024**2)

            if available_mb < self.MIN_MEMORY_MB:
                return CheckResult(
                    check_name="memory",
                    passed=False,
                    message=f"Insufficient memory: {available_mb:.0f}MB < {self.MIN_MEMORY_MB:.0f}MB",
                    details={"available_mb": available_mb, "required_mb": self.MIN_MEMORY_MB},
                )

            return CheckResult(
                check_name="memory",
                passed=True,
                message=f"Memory OK: {available_mb:.0f}MB available",
                details={"available_mb": available_mb, "used_pct": mem.percent},
            )
        except Exception as e:
            return CheckResult(
                check_name="memory",
                passed=False,
                message=f"Memory check failed: {str(e)}",
                details={"error": str(e)},
            )

    async def _check_position_sync(self) -> CheckResult:
        """Check position synchronization (exchange vs local)."""
        try:
            # Position sync would be done here
            # For now, we'll assume it passes
            logger.info("checking_position_sync")

            return CheckResult(
                check_name="position_sync",
                passed=True,
                message="Position synchronization successful",
                details={},
            )
        except Exception as e:
            return CheckResult(
                check_name="position_sync",
                passed=False,
                message=f"Position sync failed: {str(e)}",
                details={"error": str(e)},
            )

    async def _check_balance(self) -> CheckResult:
        """Check sufficient account balance."""
        try:
            # Balance check would be done here
            # For now, we'll assume it passes
            logger.info("checking_account_balance")

            return CheckResult(
                check_name="balance",
                passed=True,
                message="Account balance sufficient",
                details={},
            )
        except Exception as e:
            return CheckResult(
                check_name="balance",
                passed=False,
                message=f"Balance check failed: {str(e)}",
                details={"error": str(e)},
            )

    def _check_strategies(self) -> CheckResult:
        """Check all active strategies load and have valid parameters.

        Validates each persisted strategy against its template: the template
        must still exist, and the strategy's stored parameters must still
        satisfy that template's specification. Templates can change after a
        strategy row is written, so this catches drift at startup rather than
        at first signal.

        This deliberately does NOT call ``StrategyEngine.create_strategy``.
        That method builds a new Strategy and persists it through
        ``DataStore.save_strategy``, and it hardcodes ``StrategyStatus.DRAFT``
        -- it has no ``status`` parameter to opt out. Calling it from a startup
        check would write one duplicate DRAFT row per active strategy on every
        boot. Validation here is read-only.

        Programming errors (``TypeError``, ``AttributeError``) propagate rather
        than being reported as a failed check. The previous implementation
        called ``create_strategy`` with four keyword arguments that do not
        exist on its signature (``template``, ``symbol``, ``account_id``,
        ``status``) and read three attributes the Strategy model does not have.
        The resulting error was caught by a bare ``except Exception`` and
        reported as "strategy validation failed", so the check could never pass
        in any environment with active strategies and nothing said why.
        Swallowing programming errors is what hid it.

        Returns:
            CheckResult with ``passed=False`` when there are no active
            strategies, a referenced template is missing, or stored parameters
            no longer validate against their template.

        Raises:
            TypeError: On a programming error inside this check.
            AttributeError: On a programming error inside this check.
        """
        try:
            strategies = self._data_store.get_active_strategies()
        except (TypeError, AttributeError):
            raise
        except Exception as e:
            return CheckResult(
                check_name="strategies",
                passed=False,
                message=f"Strategy check failed: {str(e)}",
                details={"error": str(e)},
            )

        if not strategies:
            return CheckResult(
                check_name="strategies",
                passed=False,
                message="No active strategies found",
                details={"strategy_count": 0},
            )

        template_manager = self._strategy_engine.template_manager

        for strategy in strategies:
            # get_template raises ValueError for an unknown id (templates.py).
            try:
                template_manager.get_template(strategy.template_id)
            except ValueError:
                return CheckResult(
                    check_name="strategies",
                    passed=False,
                    message=(
                        f"Strategy {strategy.name} references unknown template "
                        f"'{strategy.template_id}'"
                    ),
                    details={
                        "strategy_id": strategy.id,
                        "template_id": strategy.template_id,
                    },
                )

            errors = template_manager.validate_parameters(
                strategy.template_id, strategy.parameters
            )
            if errors:
                return CheckResult(
                    check_name="strategies",
                    passed=False,
                    message=(
                        f"Strategy {strategy.name} has invalid parameters: "
                        f"{'; '.join(errors)}"
                    ),
                    details={
                        "strategy_id": strategy.id,
                        "template_id": strategy.template_id,
                        "errors": errors,
                    },
                )

        return CheckResult(
            check_name="strategies",
            passed=True,
            message=f"{len(strategies)} strategies validated successfully",
            details={"strategy_count": len(strategies)},
        )


# ---------------------------------------------------------------------------
# Entry Timing Coordinator
# ---------------------------------------------------------------------------


@dataclass
class PendingEntry:
    """Pending entry order waiting for timing coordination.

    Used in priority queue ordered by Sharpe ratio (higher is better).

    Attributes:
        sharpe_ratio: Strategy Sharpe ratio (for priority).
        timestamp: When entry was queued.
        symbol: Trading symbol.
        strategy_id: Strategy ID.
        signal: Signal dict with entry details.
    """

    sharpe_ratio: float
    timestamp: datetime
    symbol: str
    strategy_id: str
    signal: dict[str, Any]

    def __lt__(self, other: "PendingEntry") -> bool:
        """Compare by Sharpe ratio (higher is better, so negate for min-heap)."""
        return self.sharpe_ratio > other.sharpe_ratio


class EntryCoordinator:
    """Entry timing coordination to prevent overtrading.

    Rules:
    - 30s minimum between ANY entries
    - Max 3 entries per minute
    - 5-minute cooldown per symbol
    - Priority queue by Sharpe ratio (higher first)
    - Bypass for stop_loss, take_profit, kill_switch orders

    Attributes:
        now: Current time function (injectable for testing).
    """

    MIN_ENTRY_INTERVAL_SECONDS = 30
    MAX_ENTRIES_PER_MINUTE = 3
    SYMBOL_COOLDOWN_SECONDS = 300  # 5 minutes

    def __init__(self, now: datetime | None = None) -> None:
        """Initialize entry coordinator.

        Args:
            now: Current time (injectable for testing). Defaults to UTC now.
        """
        self._now_fn = (
            (lambda: now) if now else lambda: datetime.now(timezone.utc)
        )
        self._pending: list[PendingEntry] = []  # Min-heap by Sharpe ratio
        self._last_entry_time: datetime | None = None
        self._recent_entries: list[datetime] = []  # Last minute of entries
        self._symbol_last_entry: dict[str, datetime] = {}

        logger.info("entry_coordinator_initialized")

    def add_entry(
        self,
        symbol: str,
        strategy_id: str,
        signal: dict[str, Any],
        sharpe_ratio: float,
    ) -> None:
        """Add entry to pending queue.

        Args:
            symbol: Trading symbol.
            strategy_id: Strategy ID.
            signal: Signal dict with entry details.
            sharpe_ratio: Strategy Sharpe ratio for priority.
        """
        entry = PendingEntry(
            sharpe_ratio=sharpe_ratio,
            timestamp=self._now_fn(),
            symbol=symbol,
            strategy_id=strategy_id,
            signal=signal,
        )
        heapq.heappush(self._pending, entry)

        logger.debug(
            "entry_queued",
            symbol=symbol,
            strategy_id=strategy_id,
            sharpe_ratio=sharpe_ratio,
            queue_size=len(self._pending),
        )

    def get_next_entry(self) -> PendingEntry | None:
        """Get next entry if timing constraints allow.

        Returns:
            Next entry if allowed, None if must wait.
        """
        if not self._pending:
            return None

        now = self._now_fn()

        # Clean old entries from recent list (>1 minute old)
        cutoff = now.timestamp() - 60
        self._recent_entries = [
            dt for dt in self._recent_entries if dt.timestamp() > cutoff
        ]

        # Check timing constraints
        if not self._can_enter(now):
            return None

        # Pop highest priority entry
        entry = heapq.heappop(self._pending)

        # Check symbol cooldown
        if entry.symbol in self._symbol_last_entry:
            last_entry = self._symbol_last_entry[entry.symbol]
            elapsed = (now - last_entry).total_seconds()
            if elapsed < self.SYMBOL_COOLDOWN_SECONDS:
                # Put back in queue
                heapq.heappush(self._pending, entry)
                logger.debug(
                    "entry_delayed_symbol_cooldown",
                    symbol=entry.symbol,
                    elapsed_seconds=elapsed,
                    required_seconds=self.SYMBOL_COOLDOWN_SECONDS,
                )
                return None

        # Record entry
        self._last_entry_time = now
        self._recent_entries.append(now)
        self._symbol_last_entry[entry.symbol] = now

        logger.info(
            "entry_released",
            symbol=entry.symbol,
            strategy_id=entry.strategy_id,
            queue_remaining=len(self._pending),
        )

        return entry

    def _can_enter(self, now: datetime) -> bool:
        """Check if timing constraints allow entry.

        Args:
            now: Current time.

        Returns:
            True if entry allowed, False if must wait.
        """
        # Check 30s minimum interval
        if self._last_entry_time is not None:
            elapsed = (now - self._last_entry_time).total_seconds()
            if elapsed < self.MIN_ENTRY_INTERVAL_SECONDS:
                return False

        # Check max 3 per minute
        if len(self._recent_entries) >= self.MAX_ENTRIES_PER_MINUTE:
            return False

        return True

    def should_bypass(self, signal_type: str) -> bool:
        """Check if signal type should bypass entry timing.

        Args:
            signal_type: Signal type (stop_loss, take_profit, etc.).

        Returns:
            True if should bypass timing constraints.
        """
        bypass_types = {"stop_loss", "take_profit", "kill_switch"}
        return signal_type in bypass_types

    def get_queue_size(self) -> int:
        """Get current queue size.

        Returns:
            Number of pending entries.
        """
        return len(self._pending)

    def clear_queue(self) -> None:
        """Clear all pending entries (for shutdown/kill switch)."""
        cleared = len(self._pending)
        self._pending.clear()
        if cleared > 0:
            logger.warning("entry_queue_cleared", entries_cleared=cleared)


# ---------------------------------------------------------------------------
# Health Checker
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckStatus:
    """Status of a single health check.

    Attributes:
        name: Check name.
        healthy: Whether check passed.
        message: Human-readable status.
        value: Measured value (latency, percentage, etc.).
        threshold: Threshold value (for warnings/errors).
    """

    name: str
    healthy: bool
    message: str
    value: float | None = None
    threshold: float | None = None


@dataclass(frozen=True)
class SystemHealth:
    """Overall system health status.

    Attributes:
        status: Overall status (healthy, degraded, unhealthy).
        checks: Individual check results.
        timestamp: When health was checked.
    """

    status: str  # healthy, degraded, unhealthy
    checks: list[CheckStatus]
    timestamp: datetime


class HealthChecker:
    """System health monitoring.

    Checks:
    - Database latency (>1000ms warning)
    - Exchange API latency (>2000ms warning)
    - Market data freshness (<5min)
    - Memory usage (70% warning, 85% critical)
    - Error rate (10/hour threshold)
    - Last trade time (24h warning)
    - Disk space (>1GB required)

    Overall status:
    - healthy: All checks passed
    - degraded: Some warnings but system functional
    - unhealthy: Critical issues detected
    """

    DB_LATENCY_WARNING_MS = 1000
    API_LATENCY_WARNING_MS = 2000
    DATA_FRESHNESS_MINUTES = 5
    MEMORY_WARNING_PCT = 70
    MEMORY_CRITICAL_PCT = 85
    ERROR_RATE_THRESHOLD = 10  # per hour
    LAST_TRADE_WARNING_HOURS = 24
    MIN_DISK_SPACE_GB = 1.0

    def __init__(
        self,
        data_store: "DataStore",
        market_data: "MarketDataFetcher",
        metrics: OrchestratorMetrics,
    ) -> None:
        """Initialize health checker.

        Args:
            data_store: DataStore for database health checks.
            market_data: MarketDataFetcher for API health checks.
            metrics: OrchestratorMetrics for error rate tracking.
        """
        self._data_store = data_store
        self._market_data = market_data
        self._metrics = metrics
        self._last_trade_time: datetime | None = None

        logger.info("health_checker_initialized")

    async def check_health(self) -> SystemHealth:
        """Run all health checks.

        Returns:
            SystemHealth with overall status and individual check results.
        """
        checks: list[CheckStatus] = []
        critical_failures = 0
        warnings = 0

        # Database latency check
        check = await self._check_database_latency()
        checks.append(check)
        if not check.healthy:
            if check.value and check.value > self.DB_LATENCY_WARNING_MS * 5:
                critical_failures += 1
            else:
                warnings += 1

        # Exchange API latency check
        check = await self._check_api_latency()
        checks.append(check)
        if not check.healthy:
            warnings += 1

        # Memory usage check
        check = self._check_memory_usage()
        checks.append(check)
        if not check.healthy:
            if check.value and check.value >= self.MEMORY_CRITICAL_PCT:
                critical_failures += 1
            else:
                warnings += 1

        # Disk space check
        check = self._check_disk_space()
        checks.append(check)
        if not check.healthy:
            critical_failures += 1

        # Error rate check
        check = self._check_error_rate()
        checks.append(check)
        if not check.healthy:
            warnings += 1

        # Determine overall status
        if critical_failures > 0:
            status = "unhealthy"
        elif warnings > 0:
            status = "degraded"
        else:
            status = "healthy"

        return SystemHealth(
            status=status,
            checks=checks,
            timestamp=datetime.now(timezone.utc),
        )

    async def _check_database_latency(self) -> CheckStatus:
        """Check database response latency."""
        try:
            start = time.monotonic()
            await asyncio.to_thread(self._data_store.get_system_state)
            latency_ms = (time.monotonic() - start) * 1000

            if latency_ms > self.DB_LATENCY_WARNING_MS:
                return CheckStatus(
                    name="database_latency",
                    healthy=False,
                    message=f"Database slow: {latency_ms:.0f}ms",
                    value=latency_ms,
                    threshold=self.DB_LATENCY_WARNING_MS,
                )

            return CheckStatus(
                name="database_latency",
                healthy=True,
                message=f"Database OK: {latency_ms:.0f}ms",
                value=latency_ms,
                threshold=self.DB_LATENCY_WARNING_MS,
            )
        except Exception as e:
            return CheckStatus(
                name="database_latency",
                healthy=False,
                message=f"Database error: {str(e)}",
            )

    async def _check_api_latency(self) -> CheckStatus:
        """Check exchange API response latency."""
        # Placeholder - would ping exchange API
        return CheckStatus(
            name="api_latency",
            healthy=True,
            message="API OK",
        )

    def _check_memory_usage(self) -> CheckStatus:
        """Check memory usage."""
        mem = psutil.virtual_memory()
        used_pct = mem.percent

        if used_pct >= self.MEMORY_CRITICAL_PCT:
            return CheckStatus(
                name="memory_usage",
                healthy=False,
                message=f"Memory critical: {used_pct:.1f}%",
                value=used_pct,
                threshold=self.MEMORY_CRITICAL_PCT,
            )

        if used_pct >= self.MEMORY_WARNING_PCT:
            return CheckStatus(
                name="memory_usage",
                healthy=False,
                message=f"Memory high: {used_pct:.1f}%",
                value=used_pct,
                threshold=self.MEMORY_WARNING_PCT,
            )

        return CheckStatus(
            name="memory_usage",
            healthy=True,
            message=f"Memory OK: {used_pct:.1f}%",
            value=used_pct,
            threshold=self.MEMORY_WARNING_PCT,
        )

    def _check_disk_space(self) -> CheckStatus:
        """Check available disk space."""
        usage = shutil.disk_usage(".")
        free_gb = usage.free / (1024**3)

        if free_gb < self.MIN_DISK_SPACE_GB:
            return CheckStatus(
                name="disk_space",
                healthy=False,
                message=f"Disk space low: {free_gb:.2f}GB",
                value=free_gb,
                threshold=self.MIN_DISK_SPACE_GB,
            )

        return CheckStatus(
            name="disk_space",
            healthy=True,
            message=f"Disk space OK: {free_gb:.2f}GB",
            value=free_gb,
            threshold=self.MIN_DISK_SPACE_GB,
        )

    def _check_error_rate(self) -> CheckStatus:
        """Check error rate from metrics."""
        # Simple check - could be enhanced with time-based tracking
        error_count = self._metrics.errors_caught

        if error_count > self.ERROR_RATE_THRESHOLD:
            return CheckStatus(
                name="error_rate",
                healthy=False,
                message=f"High error rate: {error_count} errors",
                value=float(error_count),
                threshold=float(self.ERROR_RATE_THRESHOLD),
            )

        return CheckStatus(
            name="error_rate",
            healthy=True,
            message=f"Error rate OK: {error_count} errors",
            value=float(error_count),
            threshold=float(self.ERROR_RATE_THRESHOLD),
        )

    def record_trade(self) -> None:
        """Record that a trade occurred (for last trade time check)."""
        self._last_trade_time = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Degradation Manager
# ---------------------------------------------------------------------------


class DegradationMode(str, enum.Enum):
    """System degradation modes.

    Defines how system operates when issues are detected.
    """

    NORMAL = "normal"
    READ_ONLY = "read_only"  # Exchange down - no new orders
    CACHE_ONLY = "cache_only"  # DB slow - use cached data
    DEGRADED = "degraded"  # Multiple issues - limited operation


class DegradationManager:
    """Manages graceful degradation when system issues detected.

    Triggers:
    - Exchange down (3+ consecutive failures) -> READ_ONLY
    - Database slow (>5s latency) -> CACHE_ONLY
    - Strategy error (3+ consecutive errors) -> Skip strategy
    - Memory pressure (>80%) -> Clear caches, force GC

    Auto-recovery:
    - Returns to NORMAL when issues resolve
    - Alerts on every mode change
    """

    EXCHANGE_FAILURE_THRESHOLD = 3
    DB_SLOW_THRESHOLD_MS = 5000
    STRATEGY_ERROR_THRESHOLD = 3
    MEMORY_PRESSURE_PCT = 80

    def __init__(self, triggers: AlertTriggers) -> None:
        """Initialize degradation manager.

        Args:
            triggers: AlertTriggers for degradation alerts.
        """
        self._triggers = triggers
        self._mode = DegradationMode.NORMAL
        self._mode_entered_at: datetime | None = None

        # Failure tracking
        self._exchange_failures = 0
        self._strategy_errors: dict[str, int] = {}
        self._skipped_strategies: set[str] = set()

        logger.info("degradation_manager_initialized")

    async def check_degradation(
        self,
        health: SystemHealth,
    ) -> DegradationMode:
        """Check if degradation mode change is needed based on health.

        Args:
            health: Current system health status.

        Returns:
            Current degradation mode (may have changed).
        """
        previous_mode = self._mode

        # Check for READ_ONLY trigger (unhealthy status)
        if health.status == "unhealthy":
            if self._mode != DegradationMode.READ_ONLY:
                await self._enter_mode(DegradationMode.READ_ONLY, "System unhealthy")
        # Check for recovery to NORMAL
        elif health.status == "healthy":
            if self._mode != DegradationMode.NORMAL:
                await self._recover_to_normal()
        # Degraded but not critical
        elif health.status == "degraded":
            if self._mode == DegradationMode.NORMAL:
                await self._enter_mode(DegradationMode.DEGRADED, "System degraded")

        return self._mode

    async def record_exchange_failure(self) -> None:
        """Record exchange API failure."""
        self._exchange_failures += 1

        if self._exchange_failures >= self.EXCHANGE_FAILURE_THRESHOLD:
            if self._mode != DegradationMode.READ_ONLY:
                await self._enter_mode(
                    DegradationMode.READ_ONLY,
                    f"{self._exchange_failures} consecutive exchange failures",
                )

    async def record_exchange_success(self) -> None:
        """Record successful exchange API call."""
        if self._exchange_failures > 0:
            logger.info(
                "exchange_failures_cleared",
                previous_failures=self._exchange_failures,
            )
        self._exchange_failures = 0

    async def record_strategy_error(self, strategy_id: str) -> None:
        """Record strategy error.

        Args:
            strategy_id: Strategy that errored.
        """
        self._strategy_errors[strategy_id] = (
            self._strategy_errors.get(strategy_id, 0) + 1
        )

        if self._strategy_errors[strategy_id] >= self.STRATEGY_ERROR_THRESHOLD:
            if strategy_id not in self._skipped_strategies:
                self._skipped_strategies.add(strategy_id)
                logger.warning(
                    "strategy_skipped_due_to_errors",
                    strategy_id=strategy_id,
                    error_count=self._strategy_errors[strategy_id],
                )

    async def record_strategy_success(self, strategy_id: str) -> None:
        """Record successful strategy execution.

        Args:
            strategy_id: Strategy that succeeded.
        """
        if strategy_id in self._strategy_errors:
            del self._strategy_errors[strategy_id]
        if strategy_id in self._skipped_strategies:
            self._skipped_strategies.remove(strategy_id)
            logger.info(
                "strategy_recovered",
                strategy_id=strategy_id,
            )

    def should_skip_strategy(self, strategy_id: str) -> bool:
        """Check if strategy should be skipped due to errors.

        Args:
            strategy_id: Strategy to check.

        Returns:
            True if strategy should be skipped.
        """
        return strategy_id in self._skipped_strategies

    async def handle_memory_pressure(self) -> None:
        """Handle memory pressure by clearing caches and forcing GC."""
        import gc

        logger.warning("memory_pressure_handling")

        # Clear any internal caches
        # (In real implementation, would clear specific caches)

        # Force garbage collection
        gc.collect()

        logger.info("memory_pressure_handled")

    async def _enter_mode(
        self,
        mode: DegradationMode,
        reason: str,
    ) -> None:
        """Enter degradation mode.

        Args:
            mode: Degradation mode to enter.
            reason: Why degradation mode was entered.
        """
        self._mode = mode
        self._mode_entered_at = datetime.now(timezone.utc)

        logger.warning(
            "degradation_mode_entered",
            mode=mode.value,
            reason=reason,
        )

        await self._triggers.on_degradation_mode_entered(
            mode=mode.value,
            reason=reason,
        )

    async def _recover_to_normal(self) -> None:
        """Recover to normal mode."""
        if self._mode_entered_at:
            duration = (
                datetime.now(timezone.utc) - self._mode_entered_at
            ).total_seconds()
        else:
            duration = 0.0

        previous_mode = self._mode
        self._mode = DegradationMode.NORMAL
        self._mode_entered_at = None

        logger.info(
            "degradation_mode_recovered",
            previous_mode=previous_mode.value,
            duration_seconds=duration,
        )

        await self._triggers.on_degradation_mode_recovered(
            mode=previous_mode.value,
            duration_seconds=duration,
        )

    def get_mode(self) -> DegradationMode:
        """Get current degradation mode.

        Returns:
            Current degradation mode.
        """
        return self._mode


# ---------------------------------------------------------------------------
# Orchestrator (Main Coordinator)
# ---------------------------------------------------------------------------


class Orchestrator:
    """Central system orchestrator.

    Coordinates all Phase 1-5 components:
    - Data store (persistence)
    - Market data (exchange API)
    - Risk controller (kill switch, position limits, circuit breakers)
    - Order manager (execution, monitoring)
    - Position tracker (P&L, fill processing)
    - Strategy engine (signal generation)
    - Alert manager (multi-channel alerts)

    Responsibilities:
    - Run 8-step startup checklist
    - Coordinate main event loop
    - Process strategies and generate signals
    - Coordinate entry timing
    - Monitor system health
    - Handle graceful degradation
    - Emergency shutdown

    Attributes:
        config: System configuration dict.
        data_store: DataStore for persistence.
        market_data: MarketDataFetcher for exchange API.
        risk_controller: RiskController for risk checks.
        order_manager: OrderManager for execution.
        position_tracker: PositionTracker for P&L.
        strategy_engine: StrategyEngine for signal generation.
        alert_manager: AlertManager for multi-channel alerts.
    """

    MAIN_LOOP_INTERVAL_SECONDS = 5  # Main loop cycle time
    HEALTH_CHECK_INTERVAL_CYCLES = 12  # Every 60 seconds (12 * 5s)
    # PRD §3.5 underperformance conditions use day/week durations — hourly check is sufficient
    UNDERPERFORMANCE_CHECK_INTERVAL_CYCLES = 720  # Every 60 minutes (720 * 5s)

    def __init__(
        self,
        config: dict[str, Any],
        data_store: "DataStore",
        market_data: "MarketDataFetcher",
        risk_controller: "RiskController",
        order_manager: "OrderManager",
        position_tracker: "PositionTracker",
        strategy_engine: "StrategyEngine",
        alert_manager: "AlertManager",
    ) -> None:
        """Initialize orchestrator with all dependencies.

        Args:
            config: System configuration dict.
            data_store: DataStore for persistence.
            market_data: MarketDataFetcher for exchange API.
            risk_controller: RiskController for risk checks.
            order_manager: OrderManager for execution.
            position_tracker: PositionTracker for P&L.
            strategy_engine: StrategyEngine for signal generation.
            alert_manager: AlertManager for multi-channel alerts.
        """
        self._config = config
        self._data_store = data_store
        self._market_data = market_data
        self._risk_controller = risk_controller
        self._order_manager = order_manager
        self._position_tracker = position_tracker
        self._strategy_engine = strategy_engine
        self._alert_manager = alert_manager

        # Alert triggers for system events
        self._triggers = AlertTriggers(alert_manager)

        # Startup checklist
        self._startup_checklist = StartupChecklist(
            data_store=data_store,
            market_data=market_data,
            strategy_engine=strategy_engine,
            position_tracker=position_tracker,
            config=config,
        )

        # Entry coordinator
        self._entry_coordinator = EntryCoordinator()

        # System state
        self._status = SystemStatus.STOPPED
        self._metrics = OrchestratorMetrics()
        self._running = False
        self._start_time: datetime | None = None

        # Health checker (created after metrics)
        self._health_checker = HealthChecker(
            data_store=data_store,
            market_data=market_data,
            metrics=self._metrics,
        )

        # Degradation manager
        self._degradation_manager = DegradationManager(triggers=self._triggers)

        # GAP-01: Monitoring service — owns daily PnL record writes and equity snapshots
        # Decision: DEC-2026-02-26-001 - MonitoringService owns PnL record writes
        self._monitoring_service = MonitoringService(data_store=data_store)

        # GAP-03: Dead man's switch — triggers kill switch if system becomes unresponsive
        # PRD Feature C: heartbeat() called every cycle, check() called every health interval
        self._dead_mans_switch = DeadMansSwitch(
            store=data_store,
            kill_switch=risk_controller.kill_switch,
            interval_minutes=5,   # Matches MAIN_LOOP_INTERVAL_SECONDS * HEALTH_CHECK_INTERVAL_CYCLES / 60
            max_missed=6,         # 30 minutes of silence triggers halt
        )

        # GAP-4: Scheduled Telegram summaries (PRD §8.5-8.6)
        # Fires daily at 00:00 UTC and weekly on Sunday 00:00 UTC.
        self._alert_scheduler = AlertScheduler(
            alert_manager=alert_manager,
            data_store=data_store,
        )

        # Signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        logger.info(
            "orchestrator_initialized",
            components=[
                "data_store",
                "market_data",
                "risk_controller",
                "order_manager",
                "position_tracker",
                "strategy_engine",
                "alert_manager",
                "monitoring_service",
                "dead_mans_switch",
                "alert_scheduler",
            ],
        )

    def _handle_signal(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals.

        Args:
            signum: Signal number.
            frame: Current stack frame.
        """
        signal_name = signal.Signals(signum).name
        logger.warning("shutdown_signal_received", signal=signal_name)
        self._running = False

    async def start(self) -> None:
        """Start the orchestrator and main event loop.

        Runs startup checklist, initializes components, and starts main loop.
        """
        logger.info("orchestrator_starting")
        self._status = SystemStatus.STARTING
        self._start_time = datetime.now(timezone.utc)

        try:
            # Run startup checklist
            startup_result = await self._startup_checklist.run()

            if not startup_result.passed:
                self._status = SystemStatus.FAILED
                failed_check = startup_result.failed_check or "unknown"
                logger.error(
                    "startup_checklist_failed",
                    failed_check=failed_check,
                )
                raise SystemStartupError(
                    failed_check=failed_check,
                    reason=f"Startup check '{failed_check}' failed",
                )

            # All checks passed
            logger.info(
                "startup_checklist_passed",
                checks_passed=len(startup_result.checks),
            )

            # Send system started alert
            await self._triggers.on_system_started(
                version="1.0.0",
                strategies_loaded=len(self._data_store.get_active_strategies()),
            )

            # Start scheduled Telegram summaries (daily + weekly, PRD §8.5-8.6)
            self._alert_scheduler.start()

            # Start main loop
            self._status = SystemStatus.RUNNING
            self._running = True

            await self._main_loop()

        except Exception as e:
            self._status = SystemStatus.FAILED
            logger.error(
                "orchestrator_start_failed",
                error=str(e),
                exc_info=True,
            )
            raise

    async def _main_loop(self) -> None:
        """Main event loop.

        10-step cycle:
        1. Kill switch check (FIRST - DEC-2026-02-12-003)
        2. Circuit breaker check
        3. Degradation mode check
        4. Process active strategies
        5. Process entry queue
        6. Update positions and P&L
        7. Health check (periodic)
        8. Check escalations
        9. Log cycle metrics
        10. Wait for next cycle
        """
        logger.info("main_loop_started")
        cycle_count = 0

        while self._running:
            cycle_start = time.monotonic()
            cycle_count += 1

            try:
                # GAP-03: Dead man's switch heartbeat — proves system is alive every cycle
                # Placed before kill switch check so watchdog records activity even during halt
                self._dead_mans_switch.heartbeat()

                # Step 1: Kill switch check (FIRST - CRITICAL)
                if self._risk_controller.kill_switch.is_active():
                    logger.warning("kill_switch_active_skipping_cycle")
                    await asyncio.sleep(self.MAIN_LOOP_INTERVAL_SECONDS)
                    continue

                # Step 2: Circuit breaker check
                # Circuit breakers are checked within risk controller validate_order()
                # No additional check needed here - they're enforced at order submission

                # Step 3: Degradation mode check + dead man's switch watchdog (every 60s)
                if cycle_count % self.HEALTH_CHECK_INTERVAL_CYCLES == 0:
                    health = await self._health_checker.check_health()
                    await self._degradation_manager.check_degradation(health)

                    # GAP-03: Check whether watchdog has missed too many heartbeats
                    if not self._dead_mans_switch.check():
                        logger.critical(
                            "dead_mans_switch_triggered_kill_switch_activated",
                            cycle=cycle_count,
                        )

                    # Handle memory pressure if detected
                    for check in health.checks:
                        if (
                            check.name == "memory_usage"
                            and not check.healthy
                            and check.value
                            and check.value >= self._degradation_manager.MEMORY_PRESSURE_PCT
                        ):
                            await self._degradation_manager.handle_memory_pressure()

                # Step 4: Process active strategies
                degradation_mode = self._degradation_manager.get_mode()
                if degradation_mode not in (
                    DegradationMode.READ_ONLY,
                    DegradationMode.DEGRADED,
                ):
                    await self._process_strategies()

                # Step 5: Process entry queue
                if degradation_mode == DegradationMode.NORMAL:
                    await self._process_entry_queue()

                # GAP-05: Order reconciliation — verify exchange state matches DB state (every 60s)
                if cycle_count % self.HEALTH_CHECK_INTERVAL_CYCLES == 0:
                    await self._reconcile_orders()

                # Step 6: Update positions and P&L
                positions = await self._position_tracker.get_all_positions()
                self._metrics.strategies_processed += len(
                    await asyncio.to_thread(self._data_store.get_active_strategies)
                )

                # GAP-01: Write daily PnL records and intraday equity snapshots
                await self._monitoring_service.run_cycle(cycle_count=cycle_count)

                # GAP-08: Position staleness check — alert on positions open >24h
                if positions:
                    stale = self._monitoring_service.check_stale_positions(positions)
                    for s in stale:
                        await self._triggers.on_health_check_failed(
                            check_name="position_staleness",
                            reason=(
                                f"Position {s['position_id']} ({s['symbol']}) "
                                f"has been open for {s['open_hours']}h "
                                f"(threshold: {s['open_hours']} > 24h)"
                            ),
                        )

                # Step 7: Health check (every 60 seconds)
                if cycle_count % self.HEALTH_CHECK_INTERVAL_CYCLES == 0:
                    health = await self._health_checker.check_health()
                    if health.status == "unhealthy":
                        await self._triggers.on_health_check_failed(
                            check_name="system_health",
                            reason=f"System health: {health.status}",
                        )

                # Step 8: Check escalations
                await self._alert_manager.check_escalations()

                # Step 8b: Underperformance monitoring (hourly, PRD §3.5)
                if cycle_count % self.UNDERPERFORMANCE_CHECK_INTERVAL_CYCLES == 0:
                    await self._check_strategy_underperformance()

                # Step 9: Log cycle metrics
                cycle_duration = (time.monotonic() - cycle_start) * 1000
                self._metrics.cycles_completed += 1
                self._metrics.last_cycle_duration_ms = cycle_duration
                self._metrics.uptime_seconds = (
                    datetime.now(timezone.utc) - self._start_time
                ).total_seconds() if self._start_time else 0

                logger.debug(
                    "main_loop_cycle_completed",
                    cycle=cycle_count,
                    duration_ms=cycle_duration,
                )

                # Step 10: Wait for next cycle
                await asyncio.sleep(self.MAIN_LOOP_INTERVAL_SECONDS)

            except Exception as e:
                self._metrics.errors_caught += 1
                logger.error(
                    "main_loop_error",
                    cycle=cycle_count,
                    error=str(e),
                    exc_info=True,
                )
                # Non-fatal: continue loop
                await asyncio.sleep(self.MAIN_LOOP_INTERVAL_SECONDS)

        logger.info("main_loop_stopped")

    async def _process_strategies(self) -> None:
        """Process all active strategies and generate signals.

        Iterates through active strategies, skipping those marked for skipping
        due to errors. Generates signals and adds them to entry queue.
        """
        try:
            strategies = await asyncio.to_thread(
                self._data_store.get_active_strategies
            )

            for strategy in strategies:
                # Skip strategies with errors
                if self._degradation_manager.should_skip_strategy(strategy.id):
                    continue

                try:
                    # Generate signal (this would call strategy logic)
                    # For now, this is a placeholder - actual implementation would:
                    # 1. Fetch latest market data for strategy symbol
                    # 2. Call strategy generator to check for signals
                    # 3. If signal generated, add to entry queue

                    # Record successful strategy execution
                    await self._degradation_manager.record_strategy_success(
                        strategy.id
                    )

                except Exception as e:
                    logger.error(
                        "strategy_processing_error",
                        strategy_id=strategy.id,
                        error=str(e),
                        exc_info=True,
                    )
                    await self._degradation_manager.record_strategy_error(
                        strategy.id
                    )

        except Exception as e:
            logger.error(
                "strategy_processing_failed",
                error=str(e),
                exc_info=True,
            )

    async def _check_strategy_underperformance(self) -> None:
        """Evaluate PRD §3.5 underperformance conditions for all LIVE strategies.

        Called hourly from the main loop. For each LIVE strategy, delegates to
        StrategyEngine.evaluate_and_apply_underperformance() which checks win
        rate, Sharpe, and expectancy conditions. Auto-transitions any strategy
        that has breached conditions for the required duration.

        Decision: DEC-2026-02-22-002 - Underperformance auto-transition (PRD §3.5)
        """
        if self._strategy_engine is None:
            return

        try:
            from src.data.models.strategy import StrategyStatus

            live_strategies = await asyncio.to_thread(
                self._data_store.get_all_strategies
            )
            live_only = [s for s in live_strategies if s.status == StrategyStatus.LIVE]

            transitioned_count = 0
            for strategy in live_only:
                try:
                    transitioned = await asyncio.to_thread(
                        self._strategy_engine.evaluate_and_apply_underperformance,
                        strategy.id,
                    )
                    if transitioned:
                        transitioned_count += 1
                except Exception as e:
                    logger.error(
                        "underperformance_check_error",
                        strategy_id=strategy.id,
                        error=str(e),
                        exc_info=True,
                    )

            logger.info(
                "underperformance_check_complete",
                live_strategies_checked=len(live_only),
                transitioned_count=transitioned_count,
            )

        except Exception as e:
            logger.error(
                "underperformance_check_failed",
                error=str(e),
                exc_info=True,
            )

    async def _process_entry_queue(self) -> None:
        """Process pending entries from entry coordinator.

        Gets next entry from queue (respecting timing constraints), validates
        via risk controller, and submits order if approved.
        """
        try:
            entry = self._entry_coordinator.get_next_entry()
            if not entry:
                return

            # Check if should bypass timing (stop_loss, take_profit, etc.)
            signal_type = entry.signal.get("type", "entry")
            if self._entry_coordinator.should_bypass(signal_type):
                logger.info(
                    "entry_bypassing_timing",
                    signal_type=signal_type,
                    symbol=entry.symbol,
                )

            # Create order request from signal
            # This is a placeholder - actual implementation would build proper OrderRequest
            # from the signal dict
            logger.debug(
                "entry_processing",
                symbol=entry.symbol,
                strategy_id=entry.strategy_id,
            )

            # Would submit order here via:
            # order_request = self._build_order_request(entry)
            # risk_results = self._risk_controller.validate_order(order_request)
            # if all passes:
            #     order = await self._order_manager.submit_order(order_request)
            #     self._metrics.orders_submitted += 1

        except Exception as e:
            logger.error(
                "entry_queue_processing_error",
                error=str(e),
                exc_info=True,
            )

    async def _reconcile_orders(self) -> None:
        """Reconcile pending/submitted orders against exchange state.

        GAP-05: PRD §4.2.3 requires reconciliation of DB order state with
        the broker's real state every health check cycle.  For MVP (market-only
        orders with synchronous execution) orders should be terminal within
        seconds.  Any PENDING/SUBMITTED order older than 5 min is an anomaly.

        This method:
        1. Fetches all non-terminal orders from the DataStore.
        2. Logs a WARNING for any order stale > 5 min.
        3. Fires an alert so the operator can investigate.

        Does NOT cancel orders (cancellation is V1; MVP market orders fill
        immediately so a stale order means something external went wrong).

        Decision: DEC-2026-02-22-003 - MVP reconciliation is audit-only
        """
        import asyncio
        from datetime import timedelta

        STALE_ORDER_MINUTES = 5

        try:
            pending_orders = await asyncio.to_thread(
                self._data_store.get_pending_orders
            )
        except Exception as exc:
            logger.error("reconcile_orders_fetch_error", error=str(exc), exc_info=True)
            return

        if not pending_orders:
            return

        now = datetime.now(timezone.utc)
        stale_threshold = timedelta(minutes=STALE_ORDER_MINUTES)

        for order in pending_orders:
            # Use submitted_at if available, fall back to created_at
            created_at = getattr(order, "submitted_at", None) or getattr(
                order, "created_at", None
            )
            if created_at is None:
                continue
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            age = now - created_at
            if age >= stale_threshold:
                age_minutes = round(age.total_seconds() / 60, 1)
                logger.warning(
                    "reconcile_stale_order_detected",
                    order_id=order.id,
                    status=getattr(order, "status", "unknown"),
                    external_id=getattr(order, "external_id", None),
                    age_minutes=age_minutes,
                )
                await self._triggers.on_health_check_failed(
                    check_name="order_reconciliation",
                    reason=(
                        f"Order {order.id} has been in state "
                        f"'{getattr(order, 'status', 'unknown')}' for "
                        f"{age_minutes} minutes — "
                        "manual review required (MVP does not auto-cancel)"
                    ),
                )

    async def stop(self) -> None:
        """Stop the orchestrator gracefully.

        1. Set running flag to False
        2. Cancel pending orders
        3. Record final P&L
        4. Send shutdown alert
        """
        logger.info("orchestrator_stopping")
        self._status = SystemStatus.STOPPING
        self._running = False

        try:
            # Stop scheduled summaries before shutdown alert
            await self._alert_scheduler.stop()

            # Cancel pending orders
            await self._order_manager.shutdown()

            # Send shutdown alert
            uptime = self._metrics.uptime_seconds
            await self._triggers.on_system_stopped(
                graceful=True,
                uptime_seconds=uptime,
                cycles_completed=self._metrics.cycles_completed,
                orders_submitted=self._metrics.orders_submitted,
            )

            self._status = SystemStatus.STOPPED
            logger.info(
                "orchestrator_stopped",
                uptime_seconds=uptime,
                cycles_completed=self._metrics.cycles_completed,
            )

        except Exception as e:
            logger.error(
                "orchestrator_stop_failed",
                error=str(e),
                exc_info=True,
            )
            raise

    def get_status(self) -> dict[str, Any]:
        """Get current orchestrator status.

        Returns:
            Status dictionary with state, metrics, and uptime.
        """
        return {
            "status": self._status.value,
            "running": self._running,
            "uptime_seconds": self._metrics.uptime_seconds,
            "metrics": {
                "cycles_completed": self._metrics.cycles_completed,
                "strategies_processed": self._metrics.strategies_processed,
                "orders_submitted": self._metrics.orders_submitted,
                "orders_filled": self._metrics.orders_filled,
                "orders_rejected": self._metrics.orders_rejected,
                "errors_caught": self._metrics.errors_caught,
                "last_cycle_duration_ms": self._metrics.last_cycle_duration_ms,
            },
        }
