# PHASE 6: BACKEND INTEGRATION
## Weeks 11-12 | 29 Tasks | ~98 Hours

**Goal:** Wire all backend components into a cohesive, production-ready system. The orchestrator coordinates everything, the API exposes all data, alerting keeps the operator informed, and comprehensive testing proves the system works end-to-end.

**Start Conditions:** Phase 5 complete (all strategies working)  
**Exit Conditions:** System runs 24 hours without crash, 100 paper trades executed successfully, all API endpoints returning correct data, alerts delivered within 30 seconds

---

## 📊 PHASE 6 PROGRESS

```
Section 6.1 Orchestrator     [░░░░░░░░░░] 0/9 tasks   (~30 hours)
Section 6.2 API Layer         [░░░░░░░░░░] 0/9 tasks   (~28 hours)
Section 6.3 Alerting          [░░░░░░░░░░] 0/6 tasks   (~16 hours)
Section 6.4 Final Testing     [░░░░░░░░░░] 0/5 tasks   (~24 hours)
───────────────────────────────────────────────────────────────────
PHASE 6 TOTAL                 [░░░░░░░░░░] 0/29 tasks  (~98 hours)
```

---

## SECTION 6.1: ORCHESTRATOR
*Estimated: 30 hours*

The orchestrator is the brain of the system — it coordinates all components, manages the main trading loop, handles startup/shutdown, and maintains system health. Every other component was built independently in Phases 1-5; now the orchestrator ties them together.

### Task 6.1.1: Create Orchestrator Core
- [ ] **Status:** Not Started
- **Description:** Main coordinator that initializes and manages all system components
- **Dependencies:** [3.1.1, 4.2.1, 5.2.9, 5.4.1]
- **Effort:** 3.5 hours

**File:** `src/core/orchestrator.py`

**Orchestrator class:**
```python
class Orchestrator:
    """
    Main trading system coordinator.
    Manages all components and runs the main trading loop.
    
    Responsibilities:
    - Initialize all components in correct order
    - Run pre-start checklist before trading
    - Execute main trading loop
    - Coordinate graceful shutdown
    - Report system health
    - Handle component failures via degradation
    """
    
    def __init__(
        self,
        config: ConfigLoader,
        data_store: DataStore,
        market_data: MarketDataService,
        risk_controller: RiskController,
        order_manager: OrderManager,
        position_tracker: PositionTracker,
        strategy_engine: StrategyEngine,
        alert_manager: AlertManager,
    ):
        self._running = False
        self._started_at: Optional[datetime] = None
        self._components = {
            'config': config,
            'data_store': data_store,
            'market_data': market_data,
            'risk_controller': risk_controller,
            'order_manager': order_manager,
            'position_tracker': position_tracker,
            'strategy_engine': strategy_engine,
            'alert_manager': alert_manager,
        }
        self._degradation_manager = DegradationManager(alert_manager)
        self._entry_coordinator = EntryCoordinator()
        self._health_checker = HealthChecker(self._components)
    
    async def start(self):
        """Start the trading system."""
        # 1. Run startup checklist
        checklist = StartupChecklist(self._components)
        result = await checklist.run()
        if not result.success:
            await self.alert_manager.send_critical(
                title="Startup Failed",
                message=f"Failed check: {result.failed_check}"
            )
            raise SystemStartupError(result.failed_check)
        
        # 2. Initialize components
        await self._initialize_components()
        
        # 3. Start main loop
        self._running = True
        self._started_at = datetime.utcnow()
        await self.alert_manager.send_info(
            title="System Started",
            message=f"Trading system started in {self.config.system.mode} mode"
        )
        await self._main_loop()
    
    async def stop(self, reason: str = "Manual shutdown"):
        """Stop the trading system gracefully."""
        pass
    
    async def get_status(self) -> SystemStatus:
        """Get overall system status."""
        pass
    
    async def _main_loop(self):
        """Main trading loop - runs continuously."""
        pass
```

**Acceptance Criteria:**
- [ ] Coordinates all components
- [ ] Graceful startup/shutdown
- [ ] Status reporting with uptime, mode, component health
- [ ] Component dependency injection (testable)
- [ ] Unit test: orchestrator lifecycle

---

### Task 6.1.1a: Implement Startup Checklist
- [ ] **Status:** Not Started
- **Description:** Full pre-start verification per PRD Safety E — system must NOT start trading if any check fails
- **Dependencies:** [6.1.1]
- **Effort:** 2.5 hours

**Add to:** `src/core/orchestrator.py`

**StartupChecklist class:**
```python
@dataclass
class StartupResult:
    success: bool
    failed_check: Optional[str] = None
    checks_passed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

class StartupChecklist:
    """
    Verify all systems before trading starts per PRD Safety E.
    
    Pre-start checks (in order):
    1. Database connection and integrity
    2. Exchange API auth and permissions
    3. Config file validity
    4. Disk space (> 1GB free)
    5. Memory available (> 500MB free)
    
    Position sync:
    - Fetch positions from exchange
    - Compare to local database
    - Alert on mismatch (don't auto-correct)
    
    Balance check:
    - Verify sufficient balance
    - Compare to last known (within 5% tolerance)
    
    Strategy validation:
    - All strategies load without error
    - Parameters within valid ranges
    - Symbols are tradeable on exchange
    
    CRITICAL: On ANY failure → DO NOT start trading, alert operator
    """
    
    REQUIRED_DISK_GB = 1.0
    REQUIRED_MEMORY_MB = 500
    BALANCE_TOLERANCE_PCT = 5.0
    
    def __init__(self, components: Dict):
        self.components = components
    
    async def run(self) -> StartupResult:
        """Run all startup checks in sequence."""
        start_time = time.monotonic()
        checks = [
            ('database_connection', self._check_database_connection),
            ('database_integrity', self._check_database_integrity),
            ('exchange_api_auth', self._check_api_auth),
            ('exchange_api_permissions', self._check_api_permissions),
            ('config_valid', self._check_config),
            ('disk_space', self._check_disk_space),
            ('memory_available', self._check_memory),
        ]
        
        passed = []
        for name, check_fn in checks:
            try:
                result = await check_fn()
                if not result.passed:
                    return StartupResult(
                        success=False, 
                        failed_check=name,
                        checks_passed=passed,
                        duration_ms=(time.monotonic() - start_time) * 1000
                    )
                passed.append(name)
            except Exception as e:
                return StartupResult(
                    success=False,
                    failed_check=f"{name}: {str(e)}",
                    checks_passed=passed,
                    duration_ms=(time.monotonic() - start_time) * 1000
                )
        
        # Position sync (compare but don't auto-correct)
        sync_result = await self._sync_positions()
        if sync_result.has_mismatch:
            await self._alert_position_mismatch(sync_result)
            return StartupResult(
                success=False,
                failed_check='position_sync',
                checks_passed=passed,
                warnings=[f"Position mismatch: {sync_result.details}"]
            )
        passed.append('position_sync')
        
        # Balance check
        balance_result = await self._check_balance()
        if not balance_result.sufficient:
            return StartupResult(
                success=False,
                failed_check='balance_insufficient',
                checks_passed=passed
            )
        passed.append('balance_check')
        
        # Strategy validation
        strategy_result = await self._validate_strategies()
        if strategy_result.has_errors:
            return StartupResult(
                success=False,
                failed_check='strategy_validation',
                checks_passed=passed,
                warnings=strategy_result.errors
            )
        passed.append('strategy_validation')
        
        return StartupResult(
            success=True, 
            checks_passed=passed,
            duration_ms=(time.monotonic() - start_time) * 1000
        )
    
    async def _check_disk_space(self) -> CheckResult:
        """Check > 1GB free disk space."""
        pass
    
    async def _check_memory(self) -> CheckResult:
        """Check > 500MB free memory."""
        pass
    
    async def _sync_positions(self) -> PositionSyncResult:
        """Sync positions without auto-correct."""
        pass
    
    async def _check_balance(self) -> BalanceCheckResult:
        """Verify balance is sufficient and within tolerance."""
        pass
    
    async def _validate_strategies(self) -> StrategyValidationResult:
        """Validate all strategies can load and are valid."""
        pass
```

**Integration:** Run before `_start_main_loop()` in Orchestrator.start()

**Acceptance Criteria:**
- [ ] Database connection check
- [ ] Database integrity check
- [ ] Exchange API auth check
- [ ] Exchange API permissions check
- [ ] Config validity check
- [ ] Disk space > 1GB check
- [ ] Memory > 500MB check
- [ ] Position sync (no auto-correct, alert on mismatch)
- [ ] Balance check with 5% tolerance
- [ ] Strategy validation (load, params, symbols)
- [ ] On any failure: do NOT start, alert operator immediately
- [ ] Startup result includes duration_ms for diagnostics
- [ ] Unit test: each check individually (mock dependencies)
- [ ] Integration test: full checklist with test database

---

### Task 6.1.2: Implement Main Trading Loop
- [ ] **Status:** Not Started
- **Description:** Core loop that continuously processes strategies, manages positions, and monitors health
- **Dependencies:** [6.1.1]
- **Effort:** 3 hours

**Add to:** `src/core/orchestrator.py`

**Main loop flow:**
```python
async def _main_loop(self):
    while self._running:
        cycle_start = time.monotonic()
        try:
            # 1. Check kill switch
            if self.risk_controller.kill_switch.is_active():
                logger.info("Kill switch active, skipping trading cycle")
                await asyncio.sleep(5)
                continue
            
            # 2. Check circuit breakers
            portfolio = await self._get_portfolio_state()
            breaker_results = await self.risk_controller.check_circuit_breakers(portfolio)
            if any(r.triggered for r in breaker_results):
                await self._handle_circuit_breaker(breaker_results)
                continue
            
            # 3. Check degradation mode
            if self._degradation_manager.is_read_only:
                logger.info("Read-only mode, monitoring positions only")
                await self.position_tracker.sync_positions()
                await self._record_pnl()
                await asyncio.sleep(self.config.monitoring.market_data_interval_seconds)
                continue
            
            # 4. Process active strategies
            strategies = await self.strategy_engine.get_active_strategies()
            for strategy in strategies:
                try:
                    await self._process_strategy(strategy)
                    await self._degradation_manager.handle_strategy_success(strategy.id)
                except Exception as e:
                    await self._degradation_manager.handle_strategy_error(strategy.id, e)
                    logger.error(f"Strategy {strategy.id} error: {e}")
            
            # 5. Process entry queue (staggered entries)
            await self._entry_coordinator.process_queue(self.order_manager)
            
            # 6. Update positions and P&L
            await self.position_tracker.sync_positions()
            await self._record_pnl()
            
            # 7. Health check
            await self._health_check()
            
            # 8. Check escalations (alert acknowledgment timeouts)
            await self.alert_manager.check_escalations()
            
            # 9. Log cycle metrics
            cycle_duration = (time.monotonic() - cycle_start) * 1000
            logger.debug(f"Trading cycle completed in {cycle_duration:.1f}ms")
            
            # 10. Wait for next cycle
            await asyncio.sleep(self.config.monitoring.market_data_interval_seconds)
            
        except Exception as e:
            await self._handle_error(e)
```

**Acceptance Criteria:**
- [ ] All steps execute in correct order
- [ ] Kill switch check is first (safety priority)
- [ ] Circuit breaker check before any trading
- [ ] Degradation mode respected (read-only skips entries)
- [ ] Strategy errors don't crash the loop
- [ ] Entry queue processed with timing coordination
- [ ] Cycle duration logged for performance monitoring
- [ ] Error handling robust — loop continues on non-fatal errors
- [ ] Configurable interval via config
- [ ] Integration test: main loop with mock strategies

---

### Task 6.1.3: Implement Strategy Processing
- [ ] **Status:** Not Started
- **Description:** Process individual strategy within the main loop — evaluate signals, calculate sizing, submit orders
- **Dependencies:** [6.1.2]
- **Effort:** 2.5 hours

**Add to:** `src/core/orchestrator.py`

**Method:** `async _process_strategy(strategy: Strategy)`

**Flow:**
1. Get market data for strategy symbols
2. Check market regime compatibility (PRD Feature B)
3. Generate signals using signal generator
4. If entry signal:
   - Check portfolio correlation limits (PRD Feature A)
   - Calculate position size (with regime mismatch → 50% reduction)
   - Queue entry through EntryCoordinator (don't submit directly)
5. If exit signal:
   - Get open position
   - Create close order (exits bypass entry coordination)
   - Submit through order manager
6. Update strategy metrics (last evaluation time, signal count)
7. Check for underperformance (consecutive losses, drawdown)

**Regime mismatch handling (per PRD Feature B):**
```python
async def _check_regime_compatibility(self, strategy: Strategy) -> RegimeCheck:
    current_regime = await self.regime_manager.get_current_regime()
    
    if current_regime.value in strategy.avoid_regimes:
        return RegimeCheck(allowed=False, reason="Strategy avoids this regime")
    
    if current_regime.value not in strategy.preferred_regimes:
        return RegimeCheck(allowed=True, size_reduction=0.5, reason="Regime mismatch: 50% size")
    
    return RegimeCheck(allowed=True, size_reduction=1.0)
```

**Acceptance Criteria:**
- [ ] Signals processed correctly for each strategy
- [ ] Market regime compatibility checked before entry
- [ ] Position size reduced 50% on regime mismatch
- [ ] Entry blocked if strategy avoids current regime
- [ ] Entries queued through EntryCoordinator (not direct)
- [ ] Exits bypass entry coordination (immediate)
- [ ] Portfolio correlation checked before entry (PRD Feature A)
- [ ] Strategy metrics updated after each evaluation
- [ ] Underperformance detection triggers alerts
- [ ] Unit test: strategy processing with various scenarios

---

### Task 6.1.3a: Implement Entry Timing Coordinator
- [ ] **Status:** Not Started
- **Description:** Coordinate entry timing across strategies per PRD Feature E to prevent simultaneous entries
- **Dependencies:** [6.1.3]
- **Effort:** 2.5 hours

**Add to:** `src/core/orchestrator.py`

**EntryCoordinator class:**
```python
@dataclass
class PendingEntry:
    signal: Signal
    strategy: Strategy
    priority: float  # Higher = better (Sharpe ratio)
    queued_at: datetime
    size_multiplier: float = 1.0  # For regime adjustments

class EntryCoordinator:
    """
    Coordinate entry timing across strategies per PRD Feature E.
    
    Rules:
    - Stagger entries: 30 seconds minimum between strategy entries
    - Max 3 entries per minute (prevents cascade)
    - Same symbol cooldown: 5 minutes (prevents doubling up)
    - Priority by Sharpe ratio (higher goes first)
    
    Bypass exceptions (these go through immediately):
    - Stop losses
    - Take profits
    - Kill switch orders
    """
    
    MIN_SECONDS_BETWEEN_ENTRIES = 30
    MAX_ENTRIES_PER_MINUTE = 3
    SAME_SYMBOL_COOLDOWN_MINUTES = 5
    
    def __init__(self):
        self._entry_times: List[datetime] = []
        self._symbol_cooldowns: Dict[str, datetime] = {}
        self._pending_entries: List[PendingEntry] = []
        self._last_entry_time: Optional[datetime] = None
    
    async def queue_entry(self, signal: Signal, strategy: Strategy, 
                          size_multiplier: float = 1.0) -> bool:
        """Add entry to queue with priority. Returns True if queued."""
        # Check symbol cooldown
        if signal.symbol in self._symbol_cooldowns:
            cooldown_until = self._symbol_cooldowns[signal.symbol]
            if datetime.utcnow() < cooldown_until:
                return False
        
        priority = strategy.live_results.get('sharpe_ratio', 0) if strategy.live_results else 0
        entry = PendingEntry(
            signal=signal, strategy=strategy, priority=priority,
            queued_at=datetime.utcnow(), size_multiplier=size_multiplier
        )
        heapq.heappush(self._pending_entries, (-priority, entry.queued_at, entry))
        return True
    
    async def process_queue(self, order_manager) -> List[Order]:
        """Process entries respecting timing rules."""
        submitted = []
        while self._pending_entries:
            can_enter, wait_seconds = self.can_enter_now()
            if not can_enter:
                break
            _, _, entry = heapq.heappop(self._pending_entries)
            order = await order_manager.submit_order(
                self._create_order_request(entry)
            )
            if order:
                submitted.append(order)
                self._record_entry(entry.signal.symbol)
        return submitted
    
    def can_enter_now(self) -> Tuple[bool, int]:
        """Check if entry allowed now. Returns (allowed, wait_seconds)."""
        now = datetime.utcnow()
        recent = [t for t in self._entry_times if now - t < timedelta(minutes=1)]
        if len(recent) >= self.MAX_ENTRIES_PER_MINUTE:
            oldest = min(recent)
            return False, 60 - (now - oldest).seconds
        if self._last_entry_time:
            elapsed = (now - self._last_entry_time).seconds
            if elapsed < self.MIN_SECONDS_BETWEEN_ENTRIES:
                return False, self.MIN_SECONDS_BETWEEN_ENTRIES - elapsed
        return True, 0
    
    def should_bypass(self, order_type: str) -> bool:
        """Check if order type bypasses coordination."""
        return order_type in ['stop_loss', 'take_profit', 'kill_switch']
```

**Integration:** Called from `_process_strategy()` for entries; bypass for exits

**Acceptance Criteria:**
- [ ] Entries staggered by 30 seconds minimum
- [ ] Max 3 entries per minute enforced
- [ ] Same-symbol 5-minute cooldown enforced
- [ ] Priority queue by Sharpe ratio (higher first)
- [ ] Size multiplier passed through (for regime adjustments)
- [ ] Stop losses bypass coordination
- [ ] Take profits bypass coordination
- [ ] Kill switch orders bypass coordination
- [ ] Stale entries cleaned from queue (>5 min old)
- [ ] Unit test: timing enforcement
- [ ] Unit test: priority ordering
- [ ] Unit test: bypass rules

---

### Task 6.1.4: Implement Graceful Shutdown
- [ ] **Status:** Not Started
- **Description:** Clean shutdown procedure that preserves system state and prevents orphan orders
- **Dependencies:** [6.1.1]
- **Effort:** 1.5 hours

**Add to:** `src/core/orchestrator.py`

**Shutdown sequence (order matters):**
```python
async def stop(self, reason: str = "Manual shutdown"):
    """Graceful shutdown — preserves state, no orphan orders."""
    logger.info(f"Initiating shutdown: {reason}")
    
    # 1. Stop main loop (prevents new evaluations)
    self._running = False
    
    # 2. Cancel ALL pending orders (prevent unexpected fills during shutdown)
    cancelled = await self.order_manager.cancel_all_pending()
    logger.info(f"Cancelled {len(cancelled)} pending orders")
    
    # 3. Optionally close all positions (configurable per shutdown type)
    if self.config.shutdown.close_positions_on_stop:
        closed = await self.position_tracker.close_all_positions(reason="system_shutdown")
        logger.info(f"Closed {len(closed)} positions")
    
    # 4. Final P&L snapshot
    await self._record_pnl(final=True)
    
    # 5. Flush all logs
    await self._flush_logs()
    
    # 6. Save system state (for recovery on restart)
    await self._save_system_state(reason=reason)
    
    # 7. Close database connections
    await self.data_store.close()
    
    # 8. Send shutdown alert
    await self.alert_manager.send_info(
        title="System Stopped",
        message=f"Reason: {reason}. Uptime: {self._get_uptime_str()}"
    )
    
    logger.info("Shutdown complete")
```

**Signal handling:**
```python
# Register signal handlers for clean shutdown
import signal

def _setup_signal_handlers(self):
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(
            self.stop(reason=f"Received signal {s.name}")
        ))
```

**Acceptance Criteria:**
- [ ] Main loop stops accepting new work
- [ ] All pending orders cancelled
- [ ] Positions optionally closed (configurable)
- [ ] Final P&L recorded
- [ ] System state persisted for restart recovery
- [ ] Database connections closed cleanly
- [ ] Shutdown alert sent
- [ ] SIGTERM and SIGINT handled gracefully
- [ ] No orphan orders possible
- [ ] Unit test: shutdown sequence order

---

### Task 6.1.5: Implement Health Check System
- [ ] **Status:** Not Started
- **Description:** Continuous system health monitoring with automated response to failures
- **Dependencies:** [6.1.1, 1.4.4]
- **Effort:** 2 hours

**Add to:** `src/core/orchestrator.py`

**Health checks (run every cycle):**
```python
class HealthChecker:
    """Monitor system health and trigger responses."""
    
    STALE_DATA_THRESHOLD_MINUTES = 5
    STALE_TRADE_THRESHOLD_HOURS = 24
    ERROR_RATE_THRESHOLD = 10  # errors per hour
    MEMORY_WARNING_PCT = 70
    MEMORY_CRITICAL_PCT = 85
    
    async def check_all(self) -> SystemHealth:
        checks = {
            'database': await self._check_database(),
            'exchange_api': await self._check_exchange(),
            'market_data_freshness': await self._check_data_freshness(),
            'memory_usage': await self._check_memory(),
            'error_rate': await self._check_error_rate(),
            'last_trade': await self._check_last_trade(),
            'disk_space': await self._check_disk_space(),
        }
        
        overall = 'healthy'
        if any(c.status == 'critical' for c in checks.values()):
            overall = 'unhealthy'
        elif any(c.status == 'warning' for c in checks.values()):
            overall = 'degraded'
        
        return SystemHealth(overall=overall, checks=checks)
```

**Automated responses:**
- Warning (any metric 50-80% of limit) → Log warning, send alert
- Critical (any metric >80% of limit) → Activate kill switch, alert operator
- Exchange API down → Switch to read-only mode via DegradationManager
- Memory pressure → Clear caches via DegradationManager

**Acceptance Criteria:**
- [ ] Database connectivity checked
- [ ] Exchange API connectivity checked with latency
- [ ] Market data freshness verified (< 5 min stale)
- [ ] Memory usage tracked with thresholds
- [ ] Error rate monitored (rolling 1-hour window)
- [ ] Last trade time tracked
- [ ] Disk space monitored
- [ ] Warning → alert
- [ ] Critical → kill switch + alert
- [ ] Overall status: healthy | degraded | unhealthy
- [ ] Integration test: health check flow

---

### Task 6.1.5a: Implement Graceful Degradation
- [ ] **Status:** Not Started
- **Description:** Continue operating safely when individual components fail per PRD Reliability A
- **Dependencies:** [6.1.5]
- **Effort:** 2.5 hours

**Add to:** `src/core/orchestrator.py`

**DegradationManager class:**
```python
class DegradationMode(str, Enum):
    NORMAL = "normal"
    READ_ONLY = "read_only"        # Exchange API down
    CACHE_ONLY = "cache_only"      # Database slow
    DEGRADED = "degraded"          # Multiple issues

class DegradationManager:
    """
    Graceful degradation per PRD Reliability A.
    
    Scenarios and responses:
    
    1. Exchange API down (3 consecutive failed requests):
       → Switch to read-only mode (no new trades)
       → Continue monitoring existing positions
       → Auto-resume when API responds
       → Alert operator immediately
    
    2. Database slow (query time > 5 seconds):
       → Use cached data for reads
       → Queue writes for later
       → Process write queue when DB recovers
       → Alert if persists > 2 minutes
    
    3. Strategy error (exception during evaluation):
       → Skip failing strategy this cycle
       → Continue processing other strategies
       → Retry next cycle
       → Alert if error persists (3+ consecutive)
    
    4. Memory pressure (usage > 80%):
       → Clear market data cache
       → Clear indicator cache
       → Force garbage collection
       → Auto-recover as memory frees
    """
    
    CONSECUTIVE_FAILURES_THRESHOLD = 3
    DB_SLOW_THRESHOLD_SECONDS = 5
    MEMORY_PRESSURE_THRESHOLD_PCT = 80
    
    def __init__(self, alert_manager, cache_manager=None):
        self.alert_manager = alert_manager
        self.cache_manager = cache_manager
        self._mode = DegradationMode.NORMAL
        self._failure_counts: Dict[str, int] = {}
        self._write_queue: List = []
        self._mode_changed_at: Optional[datetime] = None
    
    async def handle_exchange_api_down(self):
        """Switch to read-only mode."""
        self._mode = DegradationMode.READ_ONLY
        self._mode_changed_at = datetime.utcnow()
        await self.alert_manager.send_warning(
            title="Exchange API Down",
            message="Switched to read-only mode. No new trades until API recovers."
        )
    
    async def handle_exchange_api_recovered(self):
        """Resume normal operation."""
        if self._mode == DegradationMode.READ_ONLY:
            self._mode = DegradationMode.NORMAL
            duration = (datetime.utcnow() - self._mode_changed_at).total_seconds()
            await self.alert_manager.send_info(
                title="Exchange API Recovered",
                message=f"Resuming normal operations. Downtime: {duration:.0f}s"
            )
    
    async def handle_database_slow(self):
        """Use cache and queue writes."""
        self._mode = DegradationMode.CACHE_ONLY
        await self.alert_manager.send_warning(
            title="Database Slow",
            message="Using cached data. Writes queued for later."
        )
    
    async def handle_strategy_error(self, strategy_id: str, error: Exception):
        """Skip failing strategy, continue others."""
        key = f"strategy_{strategy_id}"
        self._failure_counts[key] = self._failure_counts.get(key, 0) + 1
        if self._failure_counts[key] >= self.CONSECUTIVE_FAILURES_THRESHOLD:
            await self.alert_manager.send_error(
                title=f"Strategy Error Persists",
                message=f"Strategy {strategy_id} failed {self._failure_counts[key]} consecutive times: {error}"
            )
    
    async def handle_strategy_success(self, strategy_id: str):
        """Reset failure count on success."""
        self._failure_counts[f"strategy_{strategy_id}"] = 0
    
    async def handle_memory_pressure(self):
        """Clear caches to free memory."""
        if self.cache_manager:
            await self.cache_manager.clear_market_data()
            await self.cache_manager.clear_indicators()
        import gc
        gc.collect()
        await self.alert_manager.send_warning(
            title="Memory Pressure",
            message="Caches cleared to reduce memory usage."
        )
    
    async def queue_write(self, operation: Dict):
        """Queue a write operation for later."""
        self._write_queue.append({
            'operation': operation,
            'queued_at': datetime.utcnow()
        })
    
    async def process_write_queue(self):
        """Process queued writes when DB recovers."""
        processed = 0
        while self._write_queue:
            item = self._write_queue.pop(0)
            try:
                await self._execute_write(item['operation'])
                processed += 1
            except Exception:
                self._write_queue.insert(0, item)
                break
        if processed:
            logger.info(f"Processed {processed} queued writes, {len(self._write_queue)} remaining")
    
    @property
    def is_read_only(self) -> bool:
        return self._mode == DegradationMode.READ_ONLY
    
    @property
    def is_degraded(self) -> bool:
        return self._mode != DegradationMode.NORMAL
    
    @property
    def current_mode(self) -> DegradationMode:
        return self._mode
```

**Integration:** Used in main loop error handlers and health check responses

**Acceptance Criteria:**
- [ ] Exchange API down → read-only mode (no new trades, continue monitoring)
- [ ] Database slow → cache + queue writes
- [ ] Strategy error → skip failing strategy, continue others
- [ ] Memory pressure → clear caches, force GC
- [ ] Auto-recovery when issues resolve
- [ ] Alerts sent on every mode change (with duration on recovery)
- [ ] Write queue processed on DB recovery
- [ ] Strategy errors tracked with consecutive threshold
- [ ] Mode change timestamp tracked
- [ ] Unit test: each degradation scenario
- [ ] Unit test: recovery flows with timing

---

### Task 6.1.6: Write Orchestrator Tests
- [ ] **Status:** Not Started
- **Description:** Comprehensive orchestrator tests covering all lifecycle flows
- **Dependencies:** [6.1.1-6.1.5a]
- **Effort:** 2.5 hours

**File:** `tests/unit/test_orchestrator.py`

**Test scenarios:**
1. Startup sequence — checklist runs, components initialize in order
2. Startup failure — checklist fails, system does not start, alert sent
3. Main loop execution — all steps in correct order
4. Strategy processing — signal handling, entry queueing, exit bypass
5. Entry coordination — timing, priority, cooldowns, bypass rules
6. Graceful shutdown — order cancellation, state save, signal handling
7. Error handling — non-fatal errors don't crash loop
8. Health checks — warning/critical thresholds, automated responses
9. Kill switch integration — loop skips trading when active
10. Degradation modes — read-only, cache-only, recovery

**Test infrastructure:**
```python
@pytest.fixture
def mock_components():
    """Create mock versions of all orchestrator dependencies."""
    return {
        'config': MockConfig(),
        'data_store': AsyncMock(spec=DataStore),
        'market_data': AsyncMock(spec=MarketDataService),
        'risk_controller': AsyncMock(spec=RiskController),
        'order_manager': AsyncMock(spec=OrderManager),
        'position_tracker': AsyncMock(spec=PositionTracker),
        'strategy_engine': AsyncMock(spec=StrategyEngine),
        'alert_manager': AsyncMock(spec=AlertManager),
    }
```

**Acceptance Criteria:**
- [ ] All 10 scenarios tested
- [ ] Error scenarios covered (startup failure, component crash, signal edge cases)
- [ ] All dependencies mocked (no real database/exchange calls)
- [ ] Async tests using pytest-asyncio
- [ ] >80% code coverage on orchestrator module

---

## SECTION 6.2: API LAYER
*Estimated: 25 hours*

The API layer exposes all system data and controls to the frontend dashboard. FastAPI provides auto-generated OpenAPI docs, async request handling, and type-safe request/response models.

### Task 6.2.1: Create FastAPI Application
- [ ] **Status:** Not Started
- **Description:** Main FastAPI application with middleware, CORS, error handling, and health endpoints
- **Dependencies:** [1.1.3]
- **Effort:** 2 hours

**File:** `src/api/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes import (
    accounts, strategies, orders, positions, risk, system, dashboard
)
from src.api.middleware.error_handler import ErrorHandlerMiddleware
from src.api.middleware.request_logger import RequestLoggerMiddleware

app = FastAPI(
    title="PARAVANT Trading System",
    version="1.0.0",
    description="Autonomous crypto trading system — Investor Cockpit API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Middleware (order matters — last added = first executed)
app.add_middleware(RequestLoggerMiddleware)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes (all prefixed with /api/v1)
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["strategies"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(positions.router, prefix="/api/v1/positions", tags=["positions"])
app.include_router(risk.router, prefix="/api/v1/risk", tags=["risk"])

# Static files (serves built frontend in production)
# app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

**PRD Reliability C — Health Check Endpoints (3 levels of detail):**
```python
@app.get("/health")
async def health():
    """Quick health check — overall status only."""
    return {"overall_status": await get_overall_status()}  # healthy|degraded|unhealthy

@app.get("/health/detailed")
async def health_detailed():
    """Component-by-component breakdown for monitoring tools."""
    return {
        "status": await get_overall_status(),
        "uptime_seconds": orchestrator.get_uptime(),
        "components": {
            "database": {"status": "healthy", "latency_ms": 12},
            "exchange_api": {"status": "healthy", "latency_ms": 45},
            "strategy_engine": {"status": "healthy", "active_count": 5},
            "alert_manager": {"status": "healthy", "pending_escalations": 0},
        },
        "metrics": {
            "memory_usage_pct": 45,
            "error_count_last_hour": 0,
            "open_positions_count": 3,
            "last_trade_time": "2024-01-15T10:30:00Z",
        }
    }

@app.get("/health/strategies")
async def health_strategies():
    """Per-strategy health for debugging individual strategy issues."""
    return {
        "strategies": [
            {
                "id": "str_123",
                "name": "EMA Trend BTC",
                "status": "healthy",
                "last_evaluation_time": "2024-01-15T10:30:00Z",
                "consecutive_errors": 0,
                "current_drawdown_pct": 3.2,
                "signals_today": 2
            }
        ]
    }
```

**Acceptance Criteria:**
- [ ] App starts on configured port (default 8000)
- [ ] All route groups registered under `/api/v1/`
- [ ] CORS configured for frontend dev server
- [ ] Error handler returns consistent JSON error format
- [ ] Request logging captures method, path, duration, status
- [ ] `/health` returns overall_status: healthy|degraded|unhealthy
- [ ] `/health/detailed` returns component breakdown with latencies
- [ ] `/health/strategies` returns per-strategy health
- [ ] OpenAPI docs accessible at `/api/docs`
- [ ] Integration test: all health endpoints

---

### Task 6.2.2: Create System Control Endpoints
- [ ] **Status:** Not Started
- **Description:** API for controlling and monitoring the trading system
- **Dependencies:** [6.1.1, 6.2.1]
- **Effort:** 2 hours

**File:** `src/api/routes/system.py`

**Endpoints:**
```
GET  /api/v1/system/status           → Overall system status
POST /api/v1/system/start            → Start trading
POST /api/v1/system/stop             → Stop trading (body: {reason, close_positions})
GET  /api/v1/system/regime           → Get current market regime + options
PUT  /api/v1/system/regime           → Set market regime (body: {regime, operator, note})
GET  /api/v1/system/regime/history   → Get regime change history
```

**Status response model:**
```python
class SystemStatusResponse(BaseModel):
    status: str                    # running | stopped | starting | stopping
    mode: str                      # paper | live
    uptime_seconds: int
    active_strategies: int
    open_positions: int
    daily_pnl: float
    daily_pnl_pct: float
    kill_switch_active: bool
    degradation_mode: str          # normal | read_only | cache_only | degraded
    circuit_breakers_triggered: List[str]
    last_trade_at: Optional[str]
    started_at: Optional[str]
```

**Regime endpoint (PRD Feature B — Dashboard Dropdown):**
```python
@router.get("/regime")
async def get_current_regime():
    return {
        "current_regime": "ranging",
        "regime_options": ["trending_up", "trending_down", "ranging", "volatile", "unknown"],
        "changed_at": "2024-01-15T10:00:00Z",
        "changed_by": "operator1",
        "note": "Market consolidating after FOMC",
        "affected_strategies": {
            "active_in_regime": 3,
            "paused_by_regime": 1,
            "size_reduced": 1
        }
    }

@router.put("/regime")
async def set_market_regime(body: SetRegimeRequest):
    """Set current market regime. Affects all strategy sizing."""
    await regime_manager.set_regime(
        MarketRegime(body.regime),
        operator=body.operator,
        note=body.note
    )
    return {
        "status": "updated",
        "new_regime": body.regime,
        "affected_strategies": await get_affected_strategies()
    }
```

**Acceptance Criteria:**
- [ ] System status endpoint returns complete state
- [ ] Start/stop controls work with proper reason tracking
- [ ] Regime GET returns current regime + options
- [ ] Regime PUT updates regime and returns affected strategies count
- [ ] Regime changes logged with operator, timestamp, note
- [ ] Regime history endpoint returns last 20 changes
- [ ] Integration test: system control flow

---

### Task 6.2.3: Create Dashboard Data Endpoints
- [ ] **Status:** Not Started
- **Description:** Aggregated data endpoints optimized for dashboard rendering
- **Dependencies:** [6.2.1]
- **Effort:** 3 hours

**File:** `src/api/routes/dashboard.py`

**Endpoints:**
```
GET /api/v1/dashboard/summary        → Portfolio summary (hero metrics)
GET /api/v1/dashboard/equity         → Equity curve data (daily snapshots)
GET /api/v1/dashboard/performance    → Performance metrics (win rate, Sharpe, etc.)
GET /api/v1/dashboard/recent-trades  → Last N trades with P&L
GET /api/v1/dashboard/alerts         → Recent alert feed
GET /api/v1/dashboard/positions      → All open positions with live P&L
```

**Summary response (serves the Cockpit page hero cards):**
```python
class DashboardSummaryResponse(BaseModel):
    # Portfolio metrics
    portfolio_value: float
    daily_change: float
    daily_change_pct: float
    weekly_change: float
    weekly_change_pct: float
    monthly_change: float
    monthly_change_pct: float
    available_margin: float
    
    # Activity metrics
    open_positions_count: int
    active_strategies_count: int
    trades_today: int
    
    # Performance metrics
    win_rate_7d: float
    sharpe_ratio_30d: float
    max_drawdown_30d: float
    
    # Risk status
    risk_status: str             # NORMAL | WARNING | CRITICAL
    current_drawdown_pct: float
    daily_loss_used_pct: float
    
    # Market regime
    current_regime: str
    
    # Sparkline data (7 days of equity for mini chart)
    equity_sparkline: List[float]

class EquityCurveResponse(BaseModel):
    """Equity curve with benchmark overlay for portfolio page."""
    data: List[EquityPoint]      # {date, equity, benchmark, drawdown_pct}
    time_range: str              # 1W|1M|3M|6M|1Y|ALL
    total_return_pct: float
    benchmark_return_pct: float

class PositionResponse(BaseModel):
    """Open position with live P&L calculation."""
    id: str
    symbol: str
    side: str                    # LONG | SHORT
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    duration_hours: float
    strategy_name: str
    strategy_id: str
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
```

**Performance optimizations:**
- Cache summary data with 10-second TTL
- Equity curve cached per time range with 1-minute TTL
- Positions data refreshed on each request (real-time critical)
- Use database views/materialized queries for aggregate metrics

**Acceptance Criteria:**
- [ ] Summary endpoint returns all PRD §6.2.2 fields
- [ ] Equity curve supports time range filtering (1W/1M/3M/6M/1Y/ALL)
- [ ] Equity curve includes benchmark overlay data
- [ ] Positions include live unrealized P&L
- [ ] Recent trades sorted by time (newest first)
- [ ] Alerts feed matches alert severity levels
- [ ] Caching implemented for non-real-time data
- [ ] Response times < 200ms for summary
- [ ] Integration test: all dashboard endpoints

---

### Task 6.2.4: Create Account Management Endpoints
- [ ] **Status:** Not Started
- **Description:** Full CRUD for accounts with balance and P&L data
- **Dependencies:** [6.2.1, 1.2.2]
- **Effort:** 1.5 hours

**File:** `src/api/routes/accounts.py`

**Endpoints:**
```
POST /api/v1/accounts              → Create account
GET  /api/v1/accounts              → List all accounts
GET  /api/v1/accounts/{id}         → Get account details + risk profile
PUT  /api/v1/accounts/{id}         → Update account settings
GET  /api/v1/accounts/{id}/balance → Get live balance from exchange
GET  /api/v1/accounts/{id}/pnl     → Get P&L history (daily/weekly/monthly)
```

**Acceptance Criteria:**
- [ ] All CRUD operations functional
- [ ] Balance fetched from exchange (with caching)
- [ ] P&L history filterable by period
- [ ] Risk profile (Conservative/Balanced/Aggressive) included
- [ ] Integration test: account APIs

---

### Task 6.2.5: Create P&L Tracking Endpoints
- [ ] **Status:** Not Started
- **Description:** Detailed P&L data with multiple aggregation dimensions
- **Dependencies:** [6.2.1, 1.2.7]
- **Effort:** 2 hours

**File:** `src/api/routes/dashboard.py` (extend)

**Endpoints:**
```
GET /api/v1/pnl/daily              → Daily P&L records
GET /api/v1/pnl/monthly            → Monthly aggregated P&L
GET /api/v1/pnl/by-strategy        → P&L breakdown by strategy
GET /api/v1/pnl/by-symbol          → P&L breakdown by symbol
GET /api/v1/pnl/heatmap            → Monthly returns heatmap data (year × month grid)
```

**Heatmap response (for PRD §6.3.2 Monthly Returns Heatmap):**
```python
class MonthlyHeatmapResponse(BaseModel):
    years: List[int]
    months: List[str]
    data: List[HeatmapCell]  # {year, month, return_pct, trade_count}
```

**Acceptance Criteria:**
- [ ] Daily records with filtering by date range
- [ ] Monthly aggregation computed correctly
- [ ] Strategy breakdown shows per-strategy P&L
- [ ] Symbol breakdown shows per-symbol P&L
- [ ] Heatmap data formatted for direct chart rendering
- [ ] Integration test: P&L APIs with test data

---

### Task 6.2.6: Create API Documentation
- [ ] **Status:** Not Started
- **Description:** Complete OpenAPI/Swagger documentation with examples
- **Dependencies:** [6.2.1-6.2.5]
- **Effort:** 1.5 hours

**Tasks:**
- Add Pydantic models with `Field(description=..., example=...)` for all request/response types
- Add endpoint docstrings with usage examples
- Document error responses (400, 401, 404, 422, 500)
- Add API tags with descriptions
- Verify Swagger UI at `/api/docs` renders correctly
- Verify ReDoc at `/api/redoc` renders correctly

**Acceptance Criteria:**
- [ ] All endpoints documented with descriptions
- [ ] Request/response examples for every endpoint
- [ ] Error responses documented
- [ ] Swagger UI accessible and functional at `/api/docs`
- [ ] ReDoc accessible at `/api/redoc`

---

### Task 6.2.7: Write API Tests
- [ ] **Status:** Not Started
- **Description:** Comprehensive API endpoint tests using FastAPI TestClient
- **Dependencies:** [6.2.1-6.2.6]
- **Effort:** 3 hours

**File:** `tests/integration/test_api.py`

**Test coverage:**
```python
class TestSystemEndpoints:
    def test_system_status(self):
    def test_system_start(self):
    def test_system_stop(self):
    def test_regime_get(self):
    def test_regime_set(self):
    def test_regime_history(self):

class TestDashboardEndpoints:
    def test_dashboard_summary(self):
    def test_equity_curve_all_ranges(self):
    def test_performance_metrics(self):
    def test_recent_trades(self):
    def test_positions_with_live_pnl(self):

class TestAccountEndpoints:
    def test_account_crud(self):
    def test_account_balance(self):
    def test_account_pnl(self):

class TestPnLEndpoints:
    def test_daily_pnl(self):
    def test_monthly_pnl(self):
    def test_pnl_by_strategy(self):
    def test_heatmap_data(self):

class TestHealthEndpoints:
    def test_health_quick(self):
    def test_health_detailed(self):
    def test_health_strategies(self):

class TestErrorHandling:
    def test_404_not_found(self):
    def test_422_validation_error(self):
    def test_500_server_error(self):
```

**Acceptance Criteria:**
- [ ] All endpoints tested (happy path + error cases)
- [ ] Error responses match documented format
- [ ] Uses FastAPI TestClient (no real server needed)
- [ ] Mock database and exchange dependencies
- [ ] >80% coverage on API routes

---

### Task 6.2.8: Create SSE Event Stream Endpoint
- [ ] **Status:** Not Started
- **Description:** Server-Sent Events endpoint that streams real-time state changes to the frontend, replacing high-frequency REST polling for safety-critical and fast-changing data. Single persistent HTTP connection instead of ~63 requests/minute from polling.
- **Dependencies:** [6.2.1, 6.3.1]
- **Effort:** 3 hours

**File:** `src/api/routes/events.py`

**Why SSE over WebSocket:**
- SSE is one-directional (server → client) — exactly what the dashboard needs
- Works over standard HTTP — no special proxy config on Railway, no upgrade negotiation
- Browser `EventSource` API auto-reconnects on disconnect (built-in)
- FastAPI supports SSE natively via `StreamingResponse` — zero new dependencies
- The frontend only watches; all actions use existing REST POST endpoints

**Endpoint:**
```
GET /api/v1/events/stream  → SSE stream (text/event-stream)
```

**Event types to stream (Tier 1 — replaces all high-frequency polling):**
```python
import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/events", tags=["events"])

# Event types pushed to frontend
SSE_EVENT_TYPES = {
    "kill_switch_changed":   "Push immediately when kill switch activated/deactivated",
    "system_status_changed": "Push on mode change (running/stopped/degraded)",
    "position_updated":      "Push on fill, close, or P&L recalculation",
    "alert_created":         "Push immediately when new alert fires",
    "risk_status_changed":   "Push when risk threshold crossed or circuit breaker trips",
    "regime_changed":        "Push when operator changes market regime",
}

@router.get("/stream")
async def event_stream(request: Request, api_key: str = None):
    """
    SSE endpoint. Frontend connects once, receives real-time state changes.
    Replaces high-frequency polling for safety-critical data.
    
    Cost impact: Reduces ~91K HTTP requests/day to ~5K by replacing
    3s/5s/10s polling loops with a single persistent connection.
    """
    # Validate API key
    if not verify_api_key(api_key):
        return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
    
    async def generate():
        # Subscribe to the internal EventBus
        queue = asyncio.Queue()
        
        async def handler(event_type: str, data: dict):
            await queue.put({"type": event_type, "data": data, "timestamp": datetime.utcnow().isoformat()})
        
        # Subscribe to all Tier 1 event types
        subscriptions = []
        for event_type in SSE_EVENT_TYPES:
            event_bus.subscribe(event_type, lambda data, et=event_type: handler(et, data))
            subscriptions.append(event_type)
        
        try:
            # Send initial connection confirmation
            yield f"event: connected\ndata: {json.dumps({'subscriptions': subscriptions})}\n\n"
            
            # Send heartbeat every 30s to keep connection alive
            # (Railway and proxies may close idle connections)
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat — keeps connection alive through proxies
                    yield f"event: heartbeat\ndata: {json.dumps({'timestamp': datetime.utcnow().isoformat()})}\n\n"
                
                # Check if client disconnected
                if await request.is_disconnected():
                    break
        finally:
            # Unsubscribe from EventBus on disconnect
            for event_type in subscriptions:
                event_bus.unsubscribe(event_type, handler)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering if proxied
        }
    )
```

**EventBus integration:**
- The orchestrator's EventBus (from Task 6.1.1) already publishes events for kill switch, risk changes, order fills, alerts
- This endpoint subscribes a per-client queue to that EventBus
- Events are serialized to SSE format: `event: {type}\ndata: {json}\n\n`
- Heartbeat every 30s prevents Railway/proxy idle timeout disconnection

**Event payload examples:**
```json
// Kill switch activated
event: kill_switch_changed
data: {"active": true, "reason": "Manual activation", "activated_at": "2026-02-14T10:30:00Z", "transaction_id": "ks_20260214_103000"}

// New position opened
event: position_updated
data: {"action": "opened", "symbol": "BTCUSDT", "side": "long", "size": 0.01, "entry_price": 97500.00, "strategy_id": "str_001"}

// Alert created
event: alert_created
data: {"id": "alert_042", "level": "warning", "title": "Daily loss approaching limit", "message": "Daily loss at 1.8% (limit: 2.0%)", "timestamp": "2026-02-14T10:31:00Z"}

// Risk threshold crossed
event: risk_status_changed
data: {"field": "daily_loss_pct", "previous": 1.5, "current": 1.8, "threshold": 2.0, "circuit_breaker_tripped": false}

// Heartbeat (keeps connection alive)
event: heartbeat
data: {"timestamp": "2026-02-14T10:31:30Z"}
```

**Kill switch audit trail enhancement:**
- Kill switch activate/deactivate endpoints (Task 6.2.2) must now return a `transaction_id` and `server_timestamp` in the response
- Store `transaction_id`, `operator`, `reason`, `ip_address` in an immutable audit log
- Push `kill_switch_changed` event with `transaction_id` via SSE immediately on state change

**Acceptance Criteria:**
- [ ] SSE endpoint streams events in correct `text/event-stream` format
- [ ] Frontend `EventSource` connects and receives events
- [ ] Kill switch state changes push within 100ms of activation
- [ ] Alert events push immediately when alert manager fires
- [ ] Position updates push on fill, close, and periodic P&L recalc
- [ ] Heartbeat sent every 30s to prevent proxy timeout
- [ ] Auto-cleanup when client disconnects (no leaked subscriptions)
- [ ] API key validated on connection
- [ ] Works on Railway deployment (no buffering issues)
- [ ] Kill switch activate/deactivate returns `transaction_id` + `server_timestamp`
- [ ] Kill switch audit log persists `transaction_id`, operator, reason, IP

---

## SECTION 6.3: ALERTING
*Estimated: 16 hours*

The alerting system is the operator's eyes and ears when they're not watching the dashboard. Critical alerts must reach the operator immediately through multiple channels, with escalation if unacknowledged.

### Task 6.3.1: Create Alert Manager
- [ ] **Status:** Not Started
- **Description:** Central alert management with multi-channel support and deduplication
- **Dependencies:** [1.1.3]
- **Effort:** 2 hours

**File:** `src/core/alerting/manager.py`

**AlertManager class:**
```python
class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Alert:
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)
    alert_id: Optional[str] = None  # Auto-generated for tracking

class AlertManager:
    """
    Central alert management.
    
    Responsibilities:
    - Route alerts to appropriate channels based on severity
    - Rate limit to prevent spam
    - Track acknowledgments for escalation
    - Persist alert history for dashboard feed
    """
    
    def __init__(self, config: ConfigLoader, data_store: DataStore):
        self._channels: List[AlertChannel] = []
        self._rate_limiter = AlertRateLimiter()
        self._escalation_manager: Optional[EscalationManager] = None
        self._data_store = data_store
    
    def register_channel(self, channel: AlertChannel):
        self._channels.append(channel)
    
    def set_escalation_manager(self, manager: EscalationManager):
        self._escalation_manager = manager
    
    async def send_alert(self, alert: Alert):
        """Send alert to all registered channels, respecting rate limits."""
        # Generate alert ID for tracking
        alert.alert_id = f"{alert.title}_{alert.timestamp.isoformat()}"
        
        # Check rate limit
        if not self._rate_limiter.should_send(alert):
            logger.debug(f"Alert rate-limited: {alert.title}")
            return
        
        # Persist to database (for dashboard alert feed)
        await self._data_store.save_alert(alert)
        
        # Route through escalation if available
        if self._escalation_manager:
            await self._escalation_manager.send_with_escalation(alert)
        else:
            for channel in self._channels:
                try:
                    await channel.send(alert)
                except Exception as e:
                    logger.error(f"Failed to send alert via {channel.__class__.__name__}: {e}")
    
    async def send_info(self, title: str, message: str, **metadata):
        await self.send_alert(Alert(AlertLevel.INFO, title, message, metadata=metadata))
    
    async def send_warning(self, title: str, message: str, **metadata):
        await self.send_alert(Alert(AlertLevel.WARNING, title, message, metadata=metadata))
    
    async def send_error(self, title: str, message: str, **metadata):
        await self.send_alert(Alert(AlertLevel.ERROR, title, message, metadata=metadata))
    
    async def send_critical(self, title: str, message: str, **metadata):
        await self.send_alert(Alert(AlertLevel.CRITICAL, title, message, metadata=metadata))
    
    async def check_escalations(self):
        """Check pending alerts and escalate if unacknowledged. Called each main loop cycle."""
        if self._escalation_manager:
            await self._escalation_manager.check_escalations()
```

**Acceptance Criteria:**
- [ ] Multiple channels supported (register/unregister)
- [ ] Alert levels (INFO/WARNING/ERROR/CRITICAL)
- [ ] Alerts persisted to database for dashboard feed
- [ ] Alert IDs generated for tracking/acknowledgment
- [ ] Channel failures don't crash the alert system
- [ ] Async sending (non-blocking)
- [ ] Unit test: alert manager with mock channels

---

### Task 6.3.2: Implement Telegram Channel
- [ ] **Status:** Not Started
- **Description:** Primary alert delivery via Telegram bot
- **Dependencies:** [6.3.1]
- **Effort:** 2 hours

**File:** `src/core/alerting/channels/telegram.py`

**TelegramChannel:**
```python
class TelegramChannel(AlertChannel):
    """
    Send alerts via Telegram Bot API.
    
    Message format:
    🚨 CRITICAL: Kill Switch Activated
    
    All trading halted. Manual positions check required.
    
    2024-01-15 10:30:00 UTC
    """
    
    EMOJI_MAP = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌",
        "critical": "🚨"
    }
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def send(self, alert: Alert):
        """Format and send alert via Telegram Bot API."""
        message = self._format_message(alert)
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        async with self._get_session() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    raise AlertDeliveryError(f"Telegram API returned {resp.status}")
    
    def _format_message(self, alert: Alert) -> str:
        emoji = self.EMOJI_MAP.get(alert.level.value, "📢")
        lines = [
            f"{emoji} <b>{alert.level.value.upper()}: {alert.title}</b>",
            "",
            alert.message,
            "",
            f"<i>{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC</i>"
        ]
        # Add metadata if present
        if alert.metadata:
            lines.append("")
            for key, value in alert.metadata.items():
                lines.append(f"<code>{key}</code>: {value}")
        return "\n".join(lines)
```

**Acceptance Criteria:**
- [ ] Messages sent to Telegram successfully
- [ ] HTML formatting renders correctly
- [ ] Emoji indicates severity level
- [ ] Metadata included when present
- [ ] Connection errors handled gracefully (logged, not crashed)
- [ ] Integration test: send test message to bot

---

### Task 6.3.2a: Implement Emergency Contact Escalation
- [ ] **Status:** Not Started
- **Description:** Multi-channel alerts with timed escalation per PRD Safety C
- **Dependencies:** [6.3.2]
- **Effort:** 2.5 hours

**File:** `src/core/alerting/channels/escalation.py`

**Escalation rules by severity:**
```
INFO:
  → Telegram only
  → No acknowledgment required

WARNING:
  → Telegram immediately
  → Email after 15 min if unacknowledged

ERROR:
  → Telegram + Email immediately
  → SMS after 15 min if unacknowledged

CRITICAL:
  → Telegram + Email + SMS immediately
  → Repeat every 5 min until acknowledged
```

**EscalationManager class:**
```python
class EscalationLevel(str, Enum):
    L1_TELEGRAM = "telegram"
    L2_EMAIL = "email"
    L3_SMS = "sms"

@dataclass
class EscalationContact:
    name: str
    telegram_id: str
    email: str
    phone: str

@dataclass
class EscalationPolicy:
    alert_level: str
    channels: List[EscalationLevel]
    escalation_delay_minutes: int
    require_acknowledgment: bool

class EscalationManager:
    """Multi-channel alert escalation per PRD Safety C."""
    
    POLICIES = {
        'info': EscalationPolicy('info', [EscalationLevel.L1_TELEGRAM], 0, False),
        'warning': EscalationPolicy('warning', [EscalationLevel.L1_TELEGRAM], 15, True),
        'error': EscalationPolicy('error', [EscalationLevel.L1_TELEGRAM, EscalationLevel.L2_EMAIL], 15, True),
        'critical': EscalationPolicy('critical', [EscalationLevel.L1_TELEGRAM, EscalationLevel.L2_EMAIL, EscalationLevel.L3_SMS], 5, True),
    }
    
    async def send_with_escalation(self, alert: Alert) -> str:
        """Send alert and start escalation timer if needed."""
        policy = self.POLICIES[alert.level.value]
        for channel in policy.channels:
            await self._send_to_channel(alert, channel)
        if policy.require_acknowledgment:
            self._pending_acknowledgments[alert.alert_id] = datetime.utcnow()
        return alert.alert_id
    
    async def acknowledge(self, alert_id: str, by: str):
        """Mark alert as acknowledged, stop escalation."""
        if alert_id in self._pending_acknowledgments:
            del self._pending_acknowledgments[alert_id]
    
    async def check_escalations(self):
        """Check pending alerts and escalate. Called each main loop cycle."""
        now = datetime.utcnow()
        for alert_id, sent_at in list(self._pending_acknowledgments.items()):
            elapsed_min = (now - sent_at).total_seconds() / 60
            current_level = self._escalation_state.get(alert_id, 0)
            if elapsed_min > 30 and current_level < 2:
                await self._escalate_to_sms(alert_id)
                self._escalation_state[alert_id] = 2
            elif elapsed_min > 15 and current_level < 1:
                await self._escalate_to_email(alert_id)
                self._escalation_state[alert_id] = 1
```

**EmailChannel and SMSChannel:**
```python
class EmailChannel(AlertChannel):
    """Send alerts via email using aiosmtplib."""
    def __init__(self, smtp_host, smtp_port, username, password, from_addr):
        ...
    async def send(self, alert: Alert, to_addrs: List[str]):
        subject = f"[{alert.level.value.upper()}] PARAVANT: {alert.title}"
        # Use aiosmtplib for async email sending

class SMSChannel(AlertChannel):
    """Send SMS alerts via Twilio."""
    def __init__(self, account_sid, auth_token, from_number):
        ...
    async def send(self, alert: Alert, to_numbers: List[str]):
        message = f"{alert.level.value.upper()}: {alert.title} - {alert.message[:100]}"
        # Use Twilio REST API
```

**Acceptance Criteria:**
- [ ] Telegram: immediate delivery for all levels
- [ ] Email: added for WARNING+ immediately, or after 15 min unacknowledged
- [ ] SMS: added for ERROR+ immediately, or after 30 min unacknowledged
- [ ] Critical: all channels immediately, repeat every 5 min until acknowledged
- [ ] Acknowledgment stops escalation timer
- [ ] Escalation state tracked in memory (persisted on shutdown)
- [ ] Unit test: escalation timing
- [ ] Integration test: multi-channel delivery (mocked)

---

### Task 6.3.3: Implement Alert Triggers
- [ ] **Status:** Not Started
- **Description:** Connect alert triggers to all system events
- **Dependencies:** [6.3.1]
- **Effort:** 2.5 hours

**File:** `src/core/alerting/triggers.py`

**Alert trigger categories:**
```python
class AlertTriggers:
    """
    Connect system events to alerts.
    Each method is called by the relevant component.
    """
    
    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
    
    # Trade alerts (called by OrderManager)
    async def on_order_filled(self, order: Order):
        await self.alert_manager.send_info(
            title=f"Order Filled: {order.symbol}",
            message=f"{order.side} {order.quantity} @ {order.fill_price}",
            strategy=order.strategy_id, symbol=order.symbol
        )
    
    # Risk alerts (called by RiskController)
    async def on_daily_loss_warning(self, used_pct: float, limit_pct: float):
        await self.alert_manager.send_warning(
            title="Daily Loss Warning",
            message=f"Used {used_pct:.1f}% of {limit_pct:.1f}% daily limit"
        )
    
    async def on_drawdown_warning(self, current_pct: float, max_pct: float):
        await self.alert_manager.send_warning(
            title="Drawdown Warning",
            message=f"Current drawdown: {current_pct:.1f}% (max: {max_pct:.1f}%)"
        )
    
    # System alerts (called by Orchestrator)
    async def on_kill_switch_activated(self, reason: str, by: str):
        await self.alert_manager.send_critical(
            title="Kill Switch Activated",
            message=f"All trading halted. Reason: {reason}. By: {by}"
        )
    
    async def on_circuit_breaker_triggered(self, breaker: str, details: str):
        await self.alert_manager.send_error(
            title=f"Circuit Breaker: {breaker}",
            message=details
        )
    
    # Strategy alerts
    async def on_strategy_underperforming(self, strategy_id: str, metric: str, value: float):
        await self.alert_manager.send_warning(
            title=f"Strategy Underperforming",
            message=f"Strategy {strategy_id}: {metric} = {value}"
        )
    
    # Error alerts
    async def on_exchange_api_error(self, error: str, consecutive: int):
        level = "error" if consecutive >= 3 else "warning"
        await getattr(self.alert_manager, f"send_{level}")(
            title="Exchange API Error",
            message=f"Error: {error}. Consecutive failures: {consecutive}"
        )
```

**Integration points:**
- OrderManager → `on_order_filled`, `on_order_rejected`
- RiskController → `on_daily_loss_warning`, `on_drawdown_warning`
- Orchestrator → `on_kill_switch_activated`, `on_circuit_breaker_triggered`
- StrategyEngine → `on_strategy_underperforming`
- BinanceAdapter → `on_exchange_api_error`

**Acceptance Criteria:**
- [ ] All trigger points integrated with their source components
- [ ] Alert levels appropriate to severity
- [ ] Metadata attached for dashboard rendering
- [ ] Configurable thresholds (warning at 50%, critical at 80%)
- [ ] Unit test: each trigger type

---

### Task 6.3.4: Implement Alert Rate Limiting
- [ ] **Status:** Not Started
- **Description:** Prevent alert spam without missing critical events
- **Dependencies:** [6.3.1]
- **Effort:** 1.5 hours

**Add to:** `src/core/alerting/manager.py`

**Rate limiting rules:**
```python
class AlertRateLimiter:
    """
    Prevent alert spam while ensuring critical alerts always arrive.
    
    Rules:
    - Same alert title: max 1 per 5 minutes
    - Same level: max 10 per hour
    - CRITICAL alerts: ALWAYS send (no rate limit)
    - Suppressed alerts: logged with count
    """
    
    TITLE_COOLDOWN_SECONDS = 300    # 5 minutes
    LEVEL_MAX_PER_HOUR = 10
    
    def __init__(self):
        self._recent_by_title: Dict[str, datetime] = {}
        self._level_counts: Dict[AlertLevel, deque] = defaultdict(deque)
        self._suppressed_count: int = 0
    
    def should_send(self, alert: Alert) -> bool:
        # Critical always sends
        if alert.level == AlertLevel.CRITICAL:
            return True
        
        now = datetime.utcnow()
        
        # Check title cooldown
        if alert.title in self._recent_by_title:
            last_sent = self._recent_by_title[alert.title]
            if (now - last_sent).total_seconds() < self.TITLE_COOLDOWN_SECONDS:
                self._suppressed_count += 1
                return False
        
        # Check level rate limit
        level_times = self._level_counts[alert.level]
        # Clean old entries
        while level_times and (now - level_times[0]).total_seconds() > 3600:
            level_times.popleft()
        if len(level_times) >= self.LEVEL_MAX_PER_HOUR:
            self._suppressed_count += 1
            return False
        
        # Record and allow
        self._recent_by_title[alert.title] = now
        self._level_counts[alert.level].append(now)
        return True
```

**Acceptance Criteria:**
- [ ] Duplicate titles suppressed for 5 minutes
- [ ] Max 10 alerts per level per hour
- [ ] CRITICAL alerts always sent (zero suppression)
- [ ] Suppressed count tracked for monitoring
- [ ] Unit test: rate limiting scenarios

---

### Task 6.3.5: Write Alerting Tests
- [ ] **Status:** Not Started
- **Description:** Comprehensive tests for the alerting system
- **Dependencies:** [6.3.1-6.3.4]
- **Effort:** 2 hours

**File:** `tests/unit/test_alerting.py`

**Test scenarios:**
1. Alert formatting — correct emoji, HTML structure, metadata
2. Multi-channel delivery — alert routes to all registered channels
3. Rate limiting — duplicate suppression, level limits, critical bypass
4. Escalation timing — 15 min email, 30 min SMS, critical repeat
5. Acknowledgment — stops escalation, removes from pending
6. Trigger integration — each trigger type sends correct alert
7. Channel failure — one channel failing doesn't block others
8. Telegram API — mocked HTTP calls, error handling

**Acceptance Criteria:**
- [ ] All alert components tested
- [ ] Rate limiting verified with time manipulation
- [ ] Escalation timing verified
- [ ] Telegram API mocked (no real API calls in tests)
- [ ] >80% coverage on alerting module

---

## SECTION 6.4: FINAL TESTING
*Estimated: 24 hours*

This section proves the entire system works end-to-end. Every component built in Phases 1-5, wired together in Phase 6, must work as an integrated whole.

### Task 6.4.1: Create Integration Test Suite
- [ ] **Status:** Not Started
- **Description:** End-to-end integration tests covering all major system flows
- **Dependencies:** [6.1.1-6.3.5]
- **Effort:** 4 hours

**File:** `tests/integration/test_full_system.py`

**Test scenarios (each is a complete flow):**

1. **System Startup Flow**
   - Initialize all components → startup checklist runs → all checks pass → main loop starts
   - Verify: alert sent, status = running, uptime counting

2. **Startup Failure Flow**
   - Inject database connection failure → startup checklist fails
   - Verify: system does NOT start, critical alert sent, error logged

3. **Strategy Creation Flow**
   - Create strategy from template → similarity check runs → strategy saved
   - Verify: strategy in database, appears in API response

4. **Backtest Flow**
   - Run backtest on strategy → results generated → metrics computed
   - Verify: deterministic results, Sharpe/drawdown calculated

5. **Paper Trading Flow**
   - Start paper trading → signal generated → paper order created → fill simulated
   - Verify: position tracked, P&L updated

6. **Order Flow**
   - Submit order → risk checks pass → order sent → fill received
   - Verify: position created, alert sent, P&L recorded

7. **Risk Rejection Flow**
   - Submit order that exceeds daily loss limit → risk check blocks
   - Verify: order rejected, reason logged, alert sent

8. **Kill Switch Flow**
   - Activate kill switch → trading stops → deactivate → trading resumes
   - Verify: no trades during active, resume works, alerts sent both ways

9. **Circuit Breaker Flow**
   - Trigger drawdown circuit breaker → trading paused → manual reset
   - Verify: breaker state saved, alert sent, strategies paused

10. **Alert Escalation Flow**
    - Send warning → wait 15 min (simulated) → email escalation
    - Verify: Telegram immediate, email after delay

11. **Degradation Flow**
    - Simulate exchange API failure → read-only mode → API recovery → normal mode
    - Verify: no new trades during read-only, monitoring continues, recovery alert sent

12. **Shutdown Flow**
    - Trigger graceful shutdown → orders cancelled → state saved → alert sent
    - Verify: no orphan orders, state recoverable

**Acceptance Criteria:**
- [ ] All 12 flows tested end-to-end
- [ ] Uses testnet for exchange calls (or mocked)
- [ ] Tests are repeatable (deterministic)
- [ ] Clear pass/fail with descriptive assertions
- [ ] Each test independent (no test order dependencies)

---

### Task 6.4.2: Create Load Test Suite
- [ ] **Status:** Not Started
- **Description:** Verify system performance under realistic and stress loads
- **Dependencies:** [6.1.1, 6.2.1]
- **Effort:** 2 hours

**File:** `tests/load/test_performance.py`

**Load tests:**

| Test | Target | Pass Criteria |
|------|--------|--------------|
| API concurrent requests | 100 simultaneous | All return < 500ms |
| Dashboard summary endpoint | 50 req/s for 60s | p95 < 200ms |
| Market data processing | 1000 candles/batch | Processing < 1s |
| Signal generation | 100 signals/minute | All evaluated correctly |
| Order throughput | 10 orders/second | All acknowledged |
| Main loop cycle | Single cycle | < 2 seconds total |

**Memory leak detection:**
```python
async def test_no_memory_leak():
    """Run 1000 main loop cycles, verify memory doesn't grow."""
    initial_mem = get_memory_usage()
    for _ in range(1000):
        await orchestrator._main_loop_single_cycle()
    final_mem = get_memory_usage()
    growth_pct = (final_mem - initial_mem) / initial_mem * 100
    assert growth_pct < 5, f"Memory grew {growth_pct:.1f}% over 1000 cycles"
```

**Acceptance Criteria:**
- [ ] API handles 100 concurrent requests
- [ ] No memory leaks over 1000 cycles
- [ ] Dashboard response times < 200ms
- [ ] System stable under sustained load
- [ ] Results logged for baseline comparison

---

### Task 6.4.3: Create 24-Hour Stability Test
- [ ] **Status:** Not Started
- **Description:** Prove the system runs continuously for 24 hours without failure
- **Dependencies:** [6.1.1-6.3.5]
- **Effort:** 1 hour setup + 24 hours run

**Test procedure:**
1. Start system in paper trading mode
2. Activate all 5 strategy templates concurrently
3. Monitor for 24 hours with automated checks
4. Every hour, verify:
   - No crashes or restarts
   - Memory usage stable (< 5% growth)
   - All signals processed (no dropped evaluations)
   - Alerts sent correctly (test alerts at known intervals)
   - Logs clean (no ERROR level entries)
   - Database not growing unbounded
5. At end: generate stability report

**Stability report format:**
```
=== 24-Hour Stability Report ===
Duration: 24h 0m 12s
Restarts: 0
Peak Memory: 412MB (45% of available)
Total Cycles: 2,880
Strategy Evaluations: 14,400
Signals Generated: 47
Paper Trades Executed: 23
Errors Logged: 0
Warnings Logged: 3
Database Size Growth: 2.1MB
```

**Acceptance Criteria:**
- [ ] System runs full 24 hours without crash
- [ ] Zero restarts required
- [ ] Memory usage stable (< 5% growth over 24h)
- [ ] All strategy evaluations completed
- [ ] Logs contain no ERROR entries
- [ ] Stability report generated automatically

---

### Task 6.4.4: Create User Acceptance Test Checklist
- [ ] **Status:** Not Started
- **Description:** Manual UAT checklist for operator verification
- **Dependencies:** [6.1.1-6.3.5]
- **Effort:** 2 hours

**File:** `tests/UAT_CHECKLIST.md`

**Operator verification checklist:**

| # | Test | Steps | Expected Result | Pass? |
|---|------|-------|-----------------|-------|
| 1 | System Start | Run start command | Startup checklist passes, alert received |  |
| 2 | Create Strategy | POST to strategy API with template | Strategy created, visible in list |  |
| 3 | Run Backtest | POST backtest request | Results returned with metrics |  |
| 4 | Start Paper Trading | Activate strategy for paper mode | Signals generated within 1 cycle |  |
| 5 | View Dashboard Data | GET dashboard/summary | All fields populated, values reasonable |  |
| 6 | View Positions | GET positions | Open positions with live P&L |  |
| 7 | Kill Switch On | POST kill-switch/activate | Trading stops, alert received |  |
| 8 | Kill Switch Off | POST kill-switch/deactivate | Trading resumes, alert received |  |
| 9 | Set Market Regime | PUT system/regime | Regime updated, strategy adjustments shown |  |
| 10 | Receive Alert | Trigger a warning condition | Telegram message within 30 seconds |  |
| 11 | System Recovery | Stop and restart system | State recovered, positions intact |  |
| 12 | View Logs | Check log files | Clear, structured, useful entries |  |

**Acceptance Criteria:**
- [ ] Comprehensive checklist covering all MVP capabilities
- [ ] All items pass during verification
- [ ] Issues documented with severity

---

### Task 6.4.5: Create Deployment Guide
- [ ] **Status:** Not Started
- **Description:** Step-by-step deployment documentation for Railway
- **Dependencies:** [6.1.1-6.4.4]
- **Effort:** 2 hours

**File:** `DEPLOYMENT.md`

**Contents:**

1. **Prerequisites**
   - Railway account setup
   - Binance testnet API keys (how to create)
   - Telegram bot token (how to create via BotFather)
   - Required environment variables (full list with descriptions)

2. **Local Development**
   - Clone, install dependencies
   - Configure `.env` file
   - Run database migrations
   - Start backend (`uvicorn src.api.main:app`)
   - Start frontend dev server (`cd frontend && npm run dev`)
   - Verify health endpoint

3. **Railway Deployment**
   - Connect GitHub repo
   - Configure environment variables
   - Deploy backend service
   - Deploy frontend (or serve from backend)
   - Configure custom domain (optional)
   - Verify deployment health

4. **Post-Deployment**
   - Verify health check
   - Create first account
   - Create first strategy from template
   - Run first backtest
   - Start paper trading
   - Verify Telegram alerts

5. **Monitoring & Maintenance**
   - Log access on Railway
   - Database backups
   - Updating the system
   - Rollback procedure

6. **Troubleshooting**
   - Common startup failures
   - Exchange API issues
   - Database connection problems
   - Alert delivery failures
   - Performance issues

**Acceptance Criteria:**
- [ ] Step-by-step guide (no assumed knowledge)
- [ ] All prerequisites listed with setup instructions
- [ ] Environment variables documented with example values
- [ ] Troubleshooting section covers common issues
- [ ] Tested on fresh deployment (someone else can follow it)

---

## 📋 PHASE 6 COMPLETION CHECKLIST

Before moving to Phase 7 (Frontend), verify:

### Core Integration
- [ ] All 29 tasks completed
- [ ] Orchestrator coordinates all components correctly
- [ ] Startup checklist runs before trading begins
- [ ] Entry timing coordinator staggers entries (30s, max 3/min)
- [ ] Graceful degradation handles component failures
- [ ] Main trading loop runs continuously without errors

### API Layer
- [ ] All API endpoints functional and returning correct data
- [ ] Dashboard summary returns all PRD §6.2.2 fields
- [ ] Market regime GET/PUT endpoints working
- [ ] Health check endpoints return detailed component status
- [ ] OpenAPI documentation complete and accessible
- [ ] SSE event stream endpoint connects and pushes real-time events
- [ ] Kill switch activate/deactivate returns transaction_id + server_timestamp
- [ ] Kill switch audit log persists all activations/deactivations with operator, reason, IP

### Alerting
- [ ] Telegram alerts delivered within 30 seconds
- [ ] Email escalation triggers after 15 min unacknowledged
- [ ] SMS escalation triggers after 30 min unacknowledged
- [ ] Critical alerts repeat every 5 min until acknowledged
- [ ] Rate limiting prevents spam (no more than 10/hour per level)

### System Stability
- [ ] System runs 24 hours without crash
- [ ] 100 paper trades executed successfully
- [ ] All integration tests pass
- [ ] Load tests pass (100 concurrent API requests)
- [ ] No memory leaks detected
- [ ] UAT checklist complete
- [ ] Deployment guide tested

### PRD Compliance
- [ ] Safety C: Multi-channel escalation (Telegram + Email + SMS)
- [ ] Safety E: Startup checklist runs before trading
- [ ] Reliability A: Graceful degradation on component failure
- [ ] Reliability C: Detailed health check endpoints (3 levels)
- [ ] Feature A: Portfolio correlation limits checked before entry
- [ ] Feature B: Market regime dropdown via API
- [ ] Feature E: Entry timing coordination

**Sign-off:** _________________ Date: _________________

---

**Previous Phase:** [05_PHASE_5_STRATEGY.md](./05_PHASE_5_STRATEGY.md)  
**Next Phase:** [07_PHASE_7_FRONTEND.md](./07_PHASE_7_FRONTEND.md)  
**Return to:** [00_MVP_TASK_INDEX.md](./00_MVP_TASK_INDEX.md)
