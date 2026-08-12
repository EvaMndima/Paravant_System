# PHASE 6: INTEGRATION
## Weeks 11-12 | 28 Tasks | ~95 Hours

**Goal:** Everything works together with monitoring and alerts. Production ready.

**Start Conditions:** Phase 5 complete (all strategies working)  
**Exit Conditions:** System runs 24 hours without crash, 100 paper trades executed successfully

---

## 📊 PHASE 6 PROGRESS

```
Section 6.1 Orchestrator     [░░░░░░░░░░] 0/9 tasks
Section 6.2 API & Dashboard  [░░░░░░░░░░] 0/8 tasks
Section 6.3 Alerting         [░░░░░░░░░░] 0/6 tasks
Section 6.4 Final Testing    [░░░░░░░░░░] 0/5 tasks
───────────────────────────────────────────────────
PHASE 6 TOTAL                [░░░░░░░░░░] 0/28 tasks
```

---

## SECTION 6.1: ORCHESTRATOR
*Estimated: 14 hours*

### Task 6.1.1: Create Orchestrator Core
- [ ] **Status:** Not Started
- **Description:** Main coordinator that runs everything
- **Dependencies:** [3.1.1, 4.2.1, 5.2.9, 5.4.1]
- **Effort:** 3.5 hours

**File:** `src/core/orchestrator.py`

**Orchestrator class:**
```python
class Orchestrator:
    """
    Main trading system coordinator.
    Manages all components and runs the main trading loop.
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
        self._components = {}
    
    async def start(self):
        """Start the trading system."""
        await self._initialize_components()
        await self._start_main_loop()
    
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
- [ ] Status reporting
- [ ] Unit test: orchestrator lifecycle

---

### Task 6.1.1a: Implement Startup Checklist
- [ ] **Status:** Not Started
- **Description:** Full pre-start verification per PRD Safety E
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

class StartupChecklist:
    """
    Verify all systems before trading starts per PRD Safety E.
    
    Pre-start checks:
    - Database connection and integrity
    - Exchange API auth and permissions
    - Config file validity
    - Disk space (> 1GB free)
    - Memory available (> 500MB free)
    
    Position sync:
    - Fetch positions from exchange
    - Compare to local database
    - Alert on mismatch (don't auto-correct)
    
    Balance check:
    - Verify sufficient balance
    - Compare to last known
    
    Strategy validation:
    - All strategies load without error
    - Parameters within valid ranges
    - Symbols are tradeable
    
    On failure: DO NOT start trading, alert operator
    """
    
    REQUIRED_DISK_GB = 1.0
    REQUIRED_MEMORY_MB = 500
    BALANCE_TOLERANCE_PCT = 5.0
    
    def __init__(self, components: Dict):
        self.components = components
    
    async def run(self) -> StartupResult:
        """Run all startup checks."""
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
                        checks_passed=passed
                    )
                passed.append(name)
            except Exception as e:
                return StartupResult(
                    success=False,
                    failed_check=f"{name}: {str(e)}",
                    checks_passed=passed
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
        
        return StartupResult(success=True, checks_passed=passed)
    
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
- [ ] Position sync (no auto-correct)
- [ ] Balance check with 5% tolerance
- [ ] Strategy validation
- [ ] On any failure: do NOT start, alert operator
- [ ] Unit test: each check individually
- [ ] Integration test: full checklist

---

### Task 6.1.2: Implement Main Trading Loop
- [ ] **Status:** Not Started
- **Description:** Core loop that processes strategies
- **Dependencies:** [6.1.1]
- **Effort:** 3 hours

**Add to:** `src/core/orchestrator.py`

**Main loop flow:**
```python
async def _main_loop(self):
    while self._running:
        try:
            # 1. Check kill switch
            if self.risk_controller.kill_switch.is_active():
                await asyncio.sleep(5)
                continue
            
            # 2. Check circuit breakers
            portfolio = await self._get_portfolio_state()
            breaker_results = await self.risk_controller.check_circuit_breakers(portfolio)
            if any(r.triggered for r in breaker_results):
                await self._handle_circuit_breaker(breaker_results)
                continue
            
            # 3. Process active strategies
            strategies = await self.strategy_engine.get_active_strategies()
            for strategy in strategies:
                await self._process_strategy(strategy)
            
            # 4. Update positions and P&L
            await self.position_tracker.sync_positions()
            await self._record_pnl()
            
            # 5. Health check
            await self._health_check()
            
            # 6. Wait for next cycle
            await asyncio.sleep(self.config.monitoring.market_data_interval_seconds)
            
        except Exception as e:
            await self._handle_error(e)
```

**Acceptance Criteria:**
- [ ] All steps in correct order
- [ ] Error handling robust
- [ ] Configurable interval
- [ ] Logging at each step
- [ ] Integration test: main loop

---

### Task 6.1.3: Implement Strategy Processing
- [ ] **Status:** Not Started
- **Description:** Process individual strategy in main loop
- **Dependencies:** [6.1.2]
- **Effort:** 2.5 hours

**Add to:** `src/core/orchestrator.py`

**Method:** `async _process_strategy(strategy: Strategy)`

**Flow:**
1. Get market data for strategy symbols
2. Generate signals using signal generator
3. If entry signal:
   - Calculate position size
   - Create order request
   - Submit through order manager (which does risk checks)
4. If exit signal:
   - Get open position
   - Create close order
   - Submit through order manager
5. Update strategy metrics
6. Check for underperformance

**Acceptance Criteria:**
- [ ] Signals processed correctly
- [ ] Orders submitted correctly
- [ ] Positions managed
- [ ] Metrics updated
- [ ] Unit test: strategy processing

---

### Task 6.1.3a: Implement Entry Timing Coordinator
- [ ] **Status:** Not Started
- **Description:** Coordinate entry timing across strategies per PRD Feature E
- **Dependencies:** [6.1.3]
- **Effort:** 2.5 hours

**Add to:** `src/core/orchestrator.py`

**EntryCoordinator class:**
```python
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import heapq

@dataclass
class PendingEntry:
    signal: Signal
    strategy: Strategy
    priority: float  # Higher = better (e.g., Sharpe ratio)
    queued_at: datetime

class EntryCoordinator:
    """
    Coordinate entry timing across strategies per PRD Feature E.
    
    Rules:
    - Stagger entries: 30 seconds between strategy entries
    - Max 3 entries per minute
    - Same symbol cooldown: 5 minutes
    - Priority by Sharpe ratio (higher goes first)
    
    Exceptions:
    - Stop losses bypass coordination
    - Take profits bypass coordination
    - Kill switch orders bypass coordination
    """
    
    MIN_SECONDS_BETWEEN_ENTRIES = 30
    MAX_ENTRIES_PER_MINUTE = 3
    SAME_SYMBOL_COOLDOWN_MINUTES = 5
    
    def __init__(self):
        self._entry_times: List[datetime] = []
        self._symbol_cooldowns: Dict[str, datetime] = {}
        self._pending_entries: List[PendingEntry] = []  # Priority queue
        self._last_entry_time: Optional[datetime] = None
    
    async def queue_entry(
        self, 
        signal: Signal, 
        strategy: Strategy
    ) -> bool:
        """
        Add entry to queue with priority.
        Returns True if entry was queued, False if rejected.
        """
        # Check symbol cooldown
        if signal.symbol in self._symbol_cooldowns:
            cooldown_until = self._symbol_cooldowns[signal.symbol]
            if datetime.utcnow() < cooldown_until:
                return False  # Symbol on cooldown
        
        # Get strategy's Sharpe ratio for priority
        priority = strategy.live_results.get('sharpe_ratio', 0) if strategy.live_results else 0
        
        entry = PendingEntry(
            signal=signal,
            strategy=strategy,
            priority=priority,
            queued_at=datetime.utcnow()
        )
        
        # Add to priority queue (negated for max-heap behavior)
        heapq.heappush(
            self._pending_entries, 
            (-priority, entry.queued_at, entry)
        )
        
        return True
    
    async def process_queue(self, order_manager) -> List[Order]:
        """
        Process entries respecting timing rules.
        Returns list of submitted orders.
        """
        submitted = []
        
        while self._pending_entries:
            can_enter, wait_seconds = self.can_enter_now()
            
            if not can_enter:
                break  # Wait for next cycle
            
            # Get highest priority entry
            _, _, entry = heapq.heappop(self._pending_entries)
            
            # Submit order
            order = await order_manager.submit_order(
                self._create_order_request(entry)
            )
            
            if order:
                submitted.append(order)
                self._record_entry(entry.signal.symbol)
        
        return submitted
    
    def can_enter_now(self) -> Tuple[bool, int]:
        """
        Check if entry allowed now.
        Returns (allowed, wait_seconds).
        """
        now = datetime.utcnow()
        
        # Check entries per minute
        recent = [t for t in self._entry_times if now - t < timedelta(minutes=1)]
        if len(recent) >= self.MAX_ENTRIES_PER_MINUTE:
            oldest = min(recent)
            wait = 60 - (now - oldest).seconds
            return False, wait
        
        # Check time since last entry
        if self._last_entry_time:
            elapsed = (now - self._last_entry_time).seconds
            if elapsed < self.MIN_SECONDS_BETWEEN_ENTRIES:
                return False, self.MIN_SECONDS_BETWEEN_ENTRIES - elapsed
        
        return True, 0
    
    def _record_entry(self, symbol: str):
        """Record entry time and set cooldowns."""
        now = datetime.utcnow()
        
        self._entry_times.append(now)
        self._last_entry_time = now
        
        # Set symbol cooldown
        self._symbol_cooldowns[symbol] = now + timedelta(
            minutes=self.SAME_SYMBOL_COOLDOWN_MINUTES
        )
        
        # Clean old entry times
        self._entry_times = [
            t for t in self._entry_times 
            if now - t < timedelta(minutes=2)
        ]
    
    def should_bypass(self, order_type: str) -> bool:
        """Check if order type bypasses coordination."""
        bypass_types = ['stop_loss', 'take_profit', 'kill_switch']
        return order_type in bypass_types
```

**Integration:** Call from `_process_strategy()` in main loop

**Acceptance Criteria:**
- [ ] Entries staggered by 30 seconds minimum
- [ ] Max 3 entries per minute enforced
- [ ] Same-symbol 5-minute cooldown enforced
- [ ] Priority queue by Sharpe ratio (higher first)
- [ ] Stop losses bypass coordination
- [ ] Take profits bypass coordination
- [ ] Kill switch orders bypass coordination
- [ ] Pending entries processed in priority order
- [ ] Unit test: timing enforcement
- [ ] Unit test: priority ordering
- [ ] Unit test: bypass rules

---

### Task 6.1.4: Implement Graceful Shutdown
- [ ] **Status:** Not Started
- **Description:** Clean shutdown procedure
- **Dependencies:** [6.1.1]
- **Effort:** 1.5 hours

**Add to:** `src/core/orchestrator.py`

**Shutdown sequence:**
1. Stop main loop (`_running = False`)
2. Cancel pending orders
3. Optionally close positions (configurable)
4. Flush logs
5. Save system state
6. Close database connections
7. Send shutdown alert

**Acceptance Criteria:**
- [ ] Clean shutdown
- [ ] No orphan orders
- [ ] State persisted
- [ ] Alert sent
- [ ] Unit test: shutdown

---

### Task 6.1.5: Implement Health Check System
- [ ] **Status:** Not Started
- **Description:** Monitor system health
- **Dependencies:** [6.1.1, 1.4.4]
- **Effort:** 2 hours

**Add to:** `src/core/orchestrator.py`

**Health checks:**
- Database connectivity
- Binance API connectivity
- Market data freshness
- Memory usage
- Last successful trade
- Error rate

**Method:** `async _health_check() -> SystemHealth`

**On unhealthy:**
- Log warning
- Send alert
- If critical, activate kill switch

**Acceptance Criteria:**
- [ ] All components checked
- [ ] Unhealthy triggers alert
- [ ] Critical triggers kill switch
- [ ] Integration test: health check

---

### Task 6.1.5a: Implement Graceful Degradation
- [ ] **Status:** Not Started
- **Description:** Continue operating when components fail per PRD Reliability A
- **Dependencies:** [6.1.5]
- **Effort:** 2.5 hours

**Add to:** `src/core/orchestrator.py`

**DegradationManager class:**
```python
from enum import Enum
from typing import Dict, Optional
from datetime import datetime

class DegradationMode(str, Enum):
    NORMAL = "normal"
    READ_ONLY = "read_only"
    CACHE_ONLY = "cache_only"
    DEGRADED = "degraded"

class DegradationManager:
    """
    Graceful degradation per PRD Reliability A.
    
    Scenarios:
    
    1. Exchange API down (3 consecutive failed requests):
       → Switch to read-only mode (no new trades)
       → Continue monitoring positions
       → Auto-resume when API responds
    
    2. Database slow (query time > 5 seconds):
       → Use cached data
       → Queue writes for later
       → Process queue when DB recovers
    
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
    
    def __init__(self, alert_manager, cache_manager):
        self.alert_manager = alert_manager
        self.cache_manager = cache_manager
        self._mode = DegradationMode.NORMAL
        self._failure_counts: Dict[str, int] = {}
        self._write_queue: List = []
    
    async def handle_exchange_api_down(self):
        """Switch to read-only mode."""
        self._mode = DegradationMode.READ_ONLY
        
        await self.alert_manager.send_warning(
            title="Exchange API Down",
            message="Switched to read-only mode. No new trades until API recovers."
        )
        
        # Continue monitoring but no new orders
    
    async def handle_exchange_api_recovered(self):
        """Resume normal operation."""
        if self._mode == DegradationMode.READ_ONLY:
            self._mode = DegradationMode.NORMAL
            
            await self.alert_manager.send_info(
                title="Exchange API Recovered",
                message="Resuming normal trading operations."
            )
    
    async def handle_database_slow(self):
        """Use cache and queue writes."""
        self._mode = DegradationMode.CACHE_ONLY
        
        await self.alert_manager.send_warning(
            title="Database Slow",
            message="Using cached data. Writes queued for later."
        )
    
    async def queue_write(self, operation: Dict):
        """Queue a write operation for later."""
        self._write_queue.append({
            'operation': operation,
            'queued_at': datetime.utcnow()
        })
    
    async def process_write_queue(self):
        """Process queued writes when DB recovers."""
        while self._write_queue:
            item = self._write_queue.pop(0)
            try:
                await self._execute_write(item['operation'])
            except Exception as e:
                # Re-queue on failure
                self._write_queue.insert(0, item)
                break
    
    async def handle_strategy_error(
        self, 
        strategy_id: str, 
        error: Exception
    ):
        """Skip failing strategy, continue others."""
        key = f"strategy_{strategy_id}"
        self._failure_counts[key] = self._failure_counts.get(key, 0) + 1
        
        if self._failure_counts[key] >= self.CONSECUTIVE_FAILURES_THRESHOLD:
            await self.alert_manager.send_error(
                title=f"Strategy Error Persists",
                message=f"Strategy {strategy_id} has failed {self._failure_counts[key]} times: {error}"
            )
    
    async def handle_strategy_success(self, strategy_id: str):
        """Reset failure count on success."""
        key = f"strategy_{strategy_id}"
        self._failure_counts[key] = 0
    
    async def handle_memory_pressure(self):
        """Clear caches to free memory."""
        await self.cache_manager.clear_market_data()
        await self.cache_manager.clear_indicators()
        
        import gc
        gc.collect()
        
        await self.alert_manager.send_warning(
            title="Memory Pressure",
            message="Caches cleared to reduce memory usage."
        )
    
    @property
    def is_read_only(self) -> bool:
        return self._mode == DegradationMode.READ_ONLY
    
    @property
    def is_degraded(self) -> bool:
        return self._mode != DegradationMode.NORMAL
```

**Integration:** Use in main loop and error handlers

**Acceptance Criteria:**
- [ ] Exchange API down → read-only mode
- [ ] Database slow → cache + queue writes
- [ ] Strategy error → skip, continue others
- [ ] Memory pressure → clear caches
- [ ] Auto-recovery when issues resolve
- [ ] Alerts sent on mode changes
- [ ] Write queue processed on DB recovery
- [ ] Strategy errors tracked with threshold
- [ ] Unit test: each degradation scenario
- [ ] Unit test: recovery flows

---

### Task 6.1.6: Write Orchestrator Tests
- [ ] **Status:** Not Started
- **Description:** Comprehensive orchestrator tests
- **Dependencies:** [6.1.1-6.1.5]
- **Effort:** 2.5 hours

**File:** `tests/unit/test_orchestrator.py`

**Test scenarios:**
- Startup sequence
- Main loop execution
- Strategy processing
- Graceful shutdown
- Error handling
- Health checks
- Kill switch integration

**Acceptance Criteria:**
- [ ] All flows tested
- [ ] Error scenarios covered
- [ ] Mock dependencies
- [ ] >80% coverage

---

## SECTION 6.2: API & DASHBOARD
*Estimated: 14 hours*

### Task 6.2.1: Create FastAPI Application
- [ ] **Status:** Not Started
- **Description:** Main FastAPI application setup
- **Dependencies:** [1.1.3]
- **Effort:** 1.5 hours

**File:** `src/api/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import (
    accounts, strategies, orders, positions, risk, system
)
from src.api.middleware.error_handler import ErrorHandlerMiddleware

app = FastAPI(
    title="PARAVANT Trading System",
    version="1.0.0",
    description="Autonomous crypto trading system"
)

# Middleware
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(positions.router, prefix="/api/positions", tags=["positions"])
app.include_router(risk.router, prefix="/api/risk", tags=["risk"])
app.include_router(system.router, prefix="/api/system", tags=["system"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

**PRD Reliability C - Health Check Endpoints:**
```python
@app.get("/health")
async def health():
    """Overall status: healthy|degraded|unhealthy"""
    return {"overall_status": await get_overall_status()}

@app.get("/health/detailed")
async def health_detailed():
    """Component-by-component breakdown"""
    return {
        "status": await get_overall_status(),
        "components": {
            "database": {
                "status": "healthy",
                "latency_ms": 12
            },
            "exchange_api": {
                "status": "healthy",
                "latency_ms": 45
            }
        },
        "metrics": {
            "database_latency_ms": 12,
            "exchange_api_status": "connected",
            "active_strategies_count": 5,
            "open_positions_count": 3,
            "last_trade_time": "2024-01-15T10:30:00Z",
            "memory_usage_pct": 45,
            "error_count_last_hour": 0
        }
    }

@app.get("/health/strategies")
async def health_strategies():
    """Per-strategy health status"""
    return {
        "strategies": [
            {
                "id": "str_123",
                "name": "EMA Trend BTC",
                "status": "healthy",
                "last_evaluation_time": "2024-01-15T10:30:00Z",
                "consecutive_errors": 0,
                "current_drawdown_pct": 3.2
            }
        ]
    }
```

**Acceptance Criteria:**
- [ ] App starts correctly
- [ ] All routes registered
- [ ] CORS configured
- [ ] Error handling works
- [ ] `/health` returns overall_status: healthy|degraded|unhealthy
- [ ] `/health/detailed` returns component breakdown:
  - database_latency_ms
  - exchange_api_status
  - active_strategies_count
  - open_positions_count
  - last_trade_time
  - memory_usage_pct
  - error_count_last_hour
- [ ] `/health/strategies` returns per-strategy:
  - last_evaluation_time
  - consecutive_errors
  - current_drawdown
- [ ] Integration test: all health endpoints

---

### Task 6.2.2: Create System Status Endpoint
- [ ] **Status:** Not Started
- **Description:** Overall system status API
- **Dependencies:** [6.1.1, 6.2.1]
- **Effort:** 1.5 hours

**File:** `src/api/routes/system.py`

**Endpoints:**
- `GET /api/system/status` - Overall system status
- `GET /api/system/health` - Detailed health check
- `POST /api/system/start` - Start trading
- `POST /api/system/stop` - Stop trading

**Status response:**
```json
{
  "status": "running",
  "mode": "paper",
  "uptime_seconds": 3600,
  "active_strategies": 3,
  "open_positions": 2,
  "daily_pnl": 150.25,
  "kill_switch_active": false,
  "circuit_breakers_triggered": [],
  "last_trade_at": "2024-03-20T10:30:00Z"
}
```

**Acceptance Criteria:**
- [ ] Status endpoint works
- [ ] Health details returned
- [ ] Can start/stop system
- [ ] Integration test: status API

---

### Task 6.2.3: Create Dashboard Data Endpoints
- [ ] **Status:** Not Started
- **Description:** Aggregated data for dashboard
- **Dependencies:** [6.2.1]
- **Effort:** 2.5 hours

**File:** `src/api/routes/dashboard.py`

**Endpoints:**
- `GET /api/dashboard/summary` - Portfolio summary
- `GET /api/dashboard/equity` - Equity curve data
- `GET /api/dashboard/performance` - Performance metrics
- `GET /api/dashboard/recent-trades` - Recent trade list
- `GET /api/dashboard/alerts` - Recent alerts

**Summary response:**
```json
{
  "portfolio_value": 10500.00,
  "daily_change": 150.25,
  "daily_change_pct": 1.45,
  "open_positions_count": 2,
  "active_strategies_count": 3,
  "win_rate_7d": 65.5,
  "sharpe_ratio_30d": 1.2,
  "max_drawdown_30d": 8.5
}
```

**Acceptance Criteria:**
- [ ] All dashboard data available
- [ ] Performance optimized
- [ ] Caching where appropriate
- [ ] Integration test: dashboard APIs

---

### Task 6.2.3a: Add Regime Dashboard Dropdown
- [ ] **Status:** Not Started
- **Description:** Dashboard dropdown for manual regime selection per PRD Feature B
- **Dependencies:** [6.2.3, 5.1.3a]
- **Effort:** 1.5 hours

**Add to:** `src/api/routes/system.py`

**Endpoints:**

```python
@router.get("/regime")
async def get_current_regime():
    """Get current market regime and options."""
    return {
        "current_regime": "ranging",
        "regime_options": [
            "trending_up",
            "trending_down",
            "ranging",
            "volatile",
            "unknown"
        ],
        "changed_at": "2024-01-15T10:00:00Z",
        "changed_by": "operator1",
        "note": "Market consolidating after FOMC"
    }

@router.put("/regime")
async def set_market_regime(
    regime: str,
    operator: str,
    note: str = ""
):
    """
    Set current market regime (manual, via dashboard dropdown).
    
    This affects all strategies:
    - If strategy in preferred_regimes: normal trading
    - If strategy in avoid_regimes: no trading
    - If mismatch: 50% position size reduction
    """
    await regime_manager.set_regime(
        MarketRegime(regime),
        operator=operator,
        note=note
    )
    
    return {
        "status": "updated",
        "new_regime": regime,
        "affected_strategies": await get_affected_strategies()
    }

@router.get("/regime/history")
async def get_regime_history(limit: int = 20):
    """Get recent regime changes."""
    return {
        "changes": [
            {
                "from": "unknown",
                "to": "ranging",
                "changed_at": "2024-01-15T10:00:00Z",
                "changed_by": "operator1",
                "note": "Market consolidating"
            }
        ]
    }
```

**Dashboard integration:**
- Regime dropdown in dashboard header
- Current regime displayed prominently
- Regime affects strategy status indicators
- Warning shown when strategies have regime mismatch

**Acceptance Criteria:**
- [ ] GET /api/system/regime returns current regime and options
- [ ] PUT /api/system/regime updates regime
- [ ] Regime change logged with operator and timestamp
- [ ] GET /api/system/regime/history returns recent changes
- [ ] Dashboard summary includes current_regime field
- [ ] Affected strategies count returned on regime change
- [ ] Integration test: regime endpoints

---

### Task 6.2.4: Create Account Management Endpoints
- [ ] **Status:** Not Started
- **Description:** API for account management
- **Dependencies:** [6.2.1, 1.2.2]
- **Effort:** 1.5 hours

**File:** `src/api/routes/accounts.py`

**Endpoints:**
- `POST /api/accounts` - Create account
- `GET /api/accounts` - List accounts
- `GET /api/accounts/{id}` - Get account details
- `PUT /api/accounts/{id}` - Update account
- `GET /api/accounts/{id}/balance` - Get balance
- `GET /api/accounts/{id}/pnl` - Get P&L history

**Acceptance Criteria:**
- [ ] All CRUD operations
- [ ] Balance from exchange
- [ ] P&L history available
- [ ] Integration test: account APIs

---

### Task 6.2.5: Create P&L Tracking Endpoints
- [ ] **Status:** Not Started
- **Description:** API for P&L data
- **Dependencies:** [6.2.1, 1.2.7]
- **Effort:** 2 hours

**Add to:** `src/api/routes/dashboard.py`

**Endpoints:**
- `GET /api/pnl/daily` - Daily P&L records
- `GET /api/pnl/monthly` - Monthly aggregated P&L
- `GET /api/pnl/by-strategy` - P&L breakdown by strategy
- `GET /api/pnl/by-symbol` - P&L breakdown by symbol

**Acceptance Criteria:**
- [ ] Daily records available
- [ ] Aggregations work
- [ ] Breakdowns by dimension
- [ ] Integration test: P&L APIs

---

### Task 6.2.6: Create API Documentation
- [ ] **Status:** Not Started
- **Description:** OpenAPI/Swagger documentation
- **Dependencies:** [6.2.1-6.2.5]
- **Effort:** 1.5 hours

**Setup:**
- FastAPI auto-generates OpenAPI spec
- Add descriptions to all endpoints
- Add request/response examples
- Document error responses

**Access:** `/docs` (Swagger UI) and `/redoc` (ReDoc)

**Acceptance Criteria:**
- [ ] All endpoints documented
- [ ] Examples provided
- [ ] Error responses documented
- [ ] Accessible at /docs

---

### Task 6.2.7: Write API Tests
- [ ] **Status:** Not Started
- **Description:** API endpoint tests
- **Dependencies:** [6.2.1-6.2.6]
- **Effort:** 3 hours

**File:** `tests/integration/test_api.py`

**Test all endpoints:**
- System status/health
- Account CRUD
- Strategy CRUD
- Order submission/cancellation
- Position queries
- Risk endpoints
- Dashboard data

**Use TestClient from FastAPI.**

**Acceptance Criteria:**
- [ ] All endpoints tested
- [ ] Error responses tested
- [ ] Auth tested (if applicable)
- [ ] >80% coverage

---

## SECTION 6.3: ALERTING
*Estimated: 10 hours*

### Task 6.3.1: Create Alert Manager
- [ ] **Status:** Not Started
- **Description:** Central alert management
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

class AlertManager:
    def __init__(self, config: ConfigLoader):
        self._channels: List[AlertChannel] = []
    
    def register_channel(self, channel: AlertChannel):
        pass
    
    async def send_alert(self, alert: Alert):
        """Send alert to all registered channels."""
        pass
    
    async def send_info(self, title: str, message: str):
        pass
    
    async def send_warning(self, title: str, message: str):
        pass
    
    async def send_error(self, title: str, message: str):
        pass
    
    async def send_critical(self, title: str, message: str):
        pass
```

**Acceptance Criteria:**
- [ ] Multiple channels supported
- [ ] Alert levels work
- [ ] Async sending
- [ ] Unit test: alert manager

---

### Task 6.3.2: Implement Telegram Channel
- [ ] **Status:** Not Started
- **Description:** Send alerts via Telegram
- **Dependencies:** [6.3.1]
- **Effort:** 2 hours

**File:** `src/core/alerting/channels/telegram.py`

**TelegramChannel implements AlertChannel:**
```python
class TelegramChannel(AlertChannel):
    def __init__(self, bot_token: str, chat_id: str):
        self.bot = telegram.Bot(token=bot_token)
        self.chat_id = chat_id
    
    async def send(self, alert: Alert):
        """Format and send alert via Telegram."""
        message = self._format_message(alert)
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            parse_mode="HTML"
        )
    
    def _format_message(self, alert: Alert) -> str:
        emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}
        return f"""
{emoji[alert.level.value]} <b>{alert.title}</b>

{alert.message}

<i>{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC</i>
"""
```

**Acceptance Criteria:**
- [ ] Messages sent to Telegram
- [ ] Formatting looks good
- [ ] Emoji by level
- [ ] Integration test: send message

---

### Task 6.3.2a: Implement Emergency Contact Escalation
- [ ] **Status:** Not Started
- **Description:** Multi-channel alerts with escalation per PRD Safety C
- **Dependencies:** [6.3.2]
- **Effort:** 2.5 hours

**File:** `src/core/alerting/channels/escalation.py`

**EscalationManager class:**
```python
from enum import Enum
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

class EscalationLevel(str, Enum):
    L1_TELEGRAM = "telegram"      # Default
    L2_EMAIL = "email"            # 15 min unacknowledged
    L3_SMS = "sms"                # 30 min unacknowledged
    L4_PHONE = "phone"            # Critical only

@dataclass
class EscalationContact:
    name: str
    telegram_id: str
    email: str
    phone: str  # For SMS

@dataclass
class EscalationPolicy:
    alert_level: str
    channels: List[EscalationLevel]
    escalation_delay_minutes: int
    require_acknowledgment: bool

class EscalationManager:
    """
    Multi-channel alert escalation per PRD Safety C.
    
    Channels:
    - Telegram: Immediate (default)
    - Email: Added for WARNING and above
    - SMS: Added for ERROR and above, or after 30 min unacknowledged
    
    Escalation rules by severity:
    
    INFO:
    - Telegram only
    - No acknowledgment required
    
    WARNING:
    - Telegram immediately
    - Email after 15 min if unacknowledged
    
    ERROR:
    - Telegram + Email immediately
    - SMS after 15 min if unacknowledged
    
    CRITICAL:
    - Telegram + Email + SMS immediately
    - Repeat every 5 min until acknowledged
    """
    
    POLICIES = {
        'info': EscalationPolicy(
            alert_level='info',
            channels=[EscalationLevel.L1_TELEGRAM],
            escalation_delay_minutes=0,
            require_acknowledgment=False
        ),
        'warning': EscalationPolicy(
            alert_level='warning',
            channels=[EscalationLevel.L1_TELEGRAM],
            escalation_delay_minutes=15,
            require_acknowledgment=True
        ),
        'error': EscalationPolicy(
            alert_level='error',
            channels=[EscalationLevel.L1_TELEGRAM, EscalationLevel.L2_EMAIL],
            escalation_delay_minutes=15,
            require_acknowledgment=True
        ),
        'critical': EscalationPolicy(
            alert_level='critical',
            channels=[
                EscalationLevel.L1_TELEGRAM,
                EscalationLevel.L2_EMAIL,
                EscalationLevel.L3_SMS
            ],
            escalation_delay_minutes=5,
            require_acknowledgment=True
        )
    }
    
    def __init__(self, channels: Dict[str, 'AlertChannel'], contacts: List[EscalationContact]):
        self.channels = channels  # telegram, email, sms
        self.contacts = contacts
        self._pending_acknowledgments: Dict[str, datetime] = {}
        self._escalation_state: Dict[str, int] = {}  # alert_id -> current level
    
    async def send_with_escalation(self, alert: 'Alert') -> str:
        """Send alert and start escalation if needed."""
        alert_id = f"{alert.title}_{alert.timestamp.isoformat()}"
        policy = self.POLICIES[alert.level.value]
        
        # Send to initial channels
        for channel in policy.channels:
            await self._send_to_channel(alert, channel)
        
        # Track for escalation if acknowledgment required
        if policy.require_acknowledgment:
            self._pending_acknowledgments[alert_id] = datetime.utcnow()
            self._escalation_state[alert_id] = 0
        
        return alert_id
    
    async def acknowledge(self, alert_id: str, by: str):
        """Mark alert as acknowledged, stop escalation."""
        if alert_id in self._pending_acknowledgments:
            del self._pending_acknowledgments[alert_id]
            del self._escalation_state[alert_id]
    
    async def check_escalations(self):
        """Check pending alerts and escalate as needed."""
        now = datetime.utcnow()
        
        for alert_id, sent_at in list(self._pending_acknowledgments.items()):
            elapsed = (now - sent_at).total_seconds() / 60
            current_level = self._escalation_state[alert_id]
            
            # Escalate based on time
            if elapsed > 30 and current_level < 2:
                await self._escalate_to_sms(alert_id)
                self._escalation_state[alert_id] = 2
            elif elapsed > 15 and current_level < 1:
                await self._escalate_to_email(alert_id)
                self._escalation_state[alert_id] = 1
    
    async def _send_to_channel(self, alert: 'Alert', channel: EscalationLevel):
        """Send alert to specific channel."""
        if channel == EscalationLevel.L1_TELEGRAM:
            await self.channels['telegram'].send(alert)
        elif channel == EscalationLevel.L2_EMAIL:
            await self.channels['email'].send(alert)
        elif channel == EscalationLevel.L3_SMS:
            await self.channels['sms'].send(alert)
```

**EmailChannel and SMSChannel:**
```python
class EmailChannel(AlertChannel):
    """Send alerts via email using SMTP."""
    
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str, from_addr: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
    
    async def send(self, alert: Alert, to_addrs: List[str]):
        """Send email alert."""
        subject = f"[{alert.level.value.upper()}] {alert.title}"
        body = self._format_email(alert)
        # Use aiosmtplib for async
        pass

class SMSChannel(AlertChannel):
    """Send SMS alerts via Twilio or similar."""
    
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
    
    async def send(self, alert: Alert, to_numbers: List[str]):
        """Send SMS alert."""
        message = f"{alert.level.value.upper()}: {alert.title} - {alert.message[:100]}"
        # Use Twilio API
        pass
```

**Acceptance Criteria:**
- [ ] Telegram channel: immediate delivery
- [ ] Email channel: for WARNING and above
- [ ] SMS channel: for ERROR and above
- [ ] Escalation: email after 15 min unacknowledged
- [ ] Escalation: SMS after 30 min unacknowledged
- [ ] Critical alerts: all channels immediately
- [ ] Critical alerts: repeat every 5 min until acknowledged
- [ ] Acknowledgment stops escalation
- [ ] Escalation state persisted
- [ ] Unit test: escalation timing
- [ ] Integration test: multi-channel delivery

---

### Task 6.3.3: Implement Alert Triggers
- [ ] **Status:** Not Started
- **Description:** Automatic alert triggers
- **Dependencies:** [6.3.1]
- **Effort:** 2.5 hours

**File:** `src/core/alerting/triggers.py`

**Alert triggers:**
- **Trade alerts:** Order filled, position opened/closed
- **Risk alerts:** Daily loss warning, drawdown warning
- **System alerts:** Kill switch activated, circuit breaker triggered
- **Strategy alerts:** Signal generated, validation failed
- **Error alerts:** API error, connection lost

**Integration points:**
- Order manager → trade alerts
- Risk controller → risk alerts
- Orchestrator → system alerts
- Paper trading → strategy alerts

**Acceptance Criteria:**
- [ ] All trigger points integrated
- [ ] Configurable alert levels
- [ ] Rate limiting (no spam)
- [ ] Unit test: trigger integration

---

### Task 6.3.4: Implement Alert Rate Limiting
- [ ] **Status:** Not Started
- **Description:** Prevent alert spam
- **Dependencies:** [6.3.1]
- **Effort:** 1.5 hours

**Add to:** `src/core/alerting/manager.py`

**Rate limiting:**
- Same alert title: max 1 per 5 minutes
- Same level: max 10 per hour
- Critical alerts: always send (no limit)

**Implementation:**
```python
class AlertRateLimiter:
    def __init__(self):
        self._recent_alerts: Dict[str, datetime] = {}
        self._level_counts: Dict[AlertLevel, deque] = {}
    
    def should_send(self, alert: Alert) -> bool:
        # Critical always sends
        if alert.level == AlertLevel.CRITICAL:
            return True
        
        # Check title rate limit
        # Check level rate limit
        # ...
```

**Acceptance Criteria:**
- [ ] Duplicate suppression
- [ ] Level rate limiting
- [ ] Critical always sends
- [ ] Unit test: rate limiting

---

### Task 6.3.5: Write Alerting Tests
- [ ] **Status:** Not Started
- **Description:** Tests for alerting system
- **Dependencies:** [6.3.1-6.3.4]
- **Effort:** 2 hours

**File:** `tests/unit/test_alerting.py`

**Test scenarios:**
- Alert formatting
- Multi-channel delivery
- Rate limiting
- Trigger integration
- Telegram message (mocked)

**Acceptance Criteria:**
- [ ] All components tested
- [ ] Rate limiting verified
- [ ] Mock Telegram API
- [ ] >80% coverage

---

## SECTION 6.4: FINAL TESTING
*Estimated: 10 hours*

### Task 6.4.1: Create Integration Test Suite
- [ ] **Status:** Not Started
- **Description:** End-to-end integration tests
- **Dependencies:** [6.1.1-6.3.5]
- **Effort:** 3 hours

**File:** `tests/integration/test_full_system.py`

**Test scenarios:**
1. **System startup** - All components initialize
2. **Strategy creation** - Create strategy from template
3. **Backtest flow** - Run backtest, verify results
4. **Paper trading flow** - Start paper trading, generate signal
5. **Order flow** - Submit order, track to fill
6. **Risk flow** - Trigger risk limit, verify rejection
7. **Kill switch flow** - Activate kill switch, verify halt
8. **Alert flow** - Trigger alert, verify delivery
9. **Shutdown flow** - Clean shutdown

**Acceptance Criteria:**
- [ ] All flows tested end-to-end
- [ ] Uses testnet for exchange calls
- [ ] Tests are repeatable
- [ ] Clear pass/fail results

---

### Task 6.4.2: Create Load Test Suite
- [ ] **Status:** Not Started
- **Description:** Test system under load
- **Dependencies:** [6.1.1]
- **Effort:** 2 hours

**File:** `tests/load/test_performance.py`

**Load tests:**
- **API load** - 100 concurrent requests
- **Data processing** - 1000 candles per second
- **Signal generation** - 100 signals per minute
- **Order throughput** - 10 orders per second

**Tools:** pytest with async, or locust

**Acceptance Criteria:**
- [ ] API handles 100 req/s
- [ ] No memory leaks
- [ ] Response times < 500ms
- [ ] System stable under load

---

### Task 6.4.3: Create 24-Hour Stability Test
- [ ] **Status:** Not Started
- **Description:** Run system for 24 hours
- **Dependencies:** [6.1.1]
- **Effort:** 1 hour (setup) + 24 hours (run)

**Test procedure:**
1. Start system in paper trading mode
2. Run all 7 templates concurrently
3. Monitor for 24 hours
4. Check:
   - No crashes
   - Memory stable
   - All signals processed
   - Alerts sent correctly
   - Logs clean (no errors)

**Acceptance Criteria:**
- [ ] System runs 24 hours
- [ ] No crashes or restarts
- [ ] Memory usage stable
- [ ] Logs show no errors

---

### Task 6.4.4: Create User Acceptance Test Checklist
- [ ] **Status:** Not Started
- **Description:** Manual UAT checklist
- **Dependencies:** [6.1.1-6.3.5]
- **Effort:** 2 hours

**File:** `tests/UAT_CHECKLIST.md`

**Checklist items:**
- [ ] Can create account via API
- [ ] Can create strategy from each template
- [ ] Can run backtest and see results
- [ ] Can start paper trading
- [ ] Can see dashboard data
- [ ] Can view positions and orders
- [ ] Can activate/deactivate kill switch
- [ ] Receive Telegram alerts
- [ ] System recovers from restart
- [ ] Logs are clear and useful

**Acceptance Criteria:**
- [ ] Comprehensive checklist
- [ ] All items pass
- [ ] Issues documented

---

### Task 6.4.5: Create Deployment Guide
- [ ] **Status:** Not Started
- **Description:** Document deployment process
- **Dependencies:** [6.1.1-6.4.4]
- **Effort:** 2 hours

**File:** `DEPLOYMENT.md`

**Contents:**
1. **Prerequisites**
   - Railway account
   - Binance testnet credentials
   - Telegram bot token
   - Environment variables

2. **Deployment steps**
   - Clone repository
   - Configure environment
   - Deploy to Railway
   - Verify deployment

3. **Post-deployment**
   - Health check
   - First strategy setup
   - Monitoring setup

4. **Troubleshooting**
   - Common issues
   - Log locations
   - Support contacts

**Acceptance Criteria:**
- [ ] Step-by-step guide
- [ ] All prerequisites listed
- [ ] Troubleshooting section
- [ ] Tested on fresh deployment

---

## 📋 PHASE 6 COMPLETION CHECKLIST

Before declaring MVP complete, verify:

- [ ] All 28 tasks completed
- [ ] Orchestrator coordinates all components
- [ ] Startup checklist runs before trading begins
- [ ] Entry timing coordinator staggers entries (30s, max 3/min)
- [ ] Graceful degradation handles component failures
- [ ] Main trading loop runs correctly
- [ ] API endpoints all functional
- [ ] Dashboard data available
- [ ] Market regime dropdown working
- [ ] Telegram alerts working
- [ ] Email escalation working (after 15 min unacknowledged)
- [ ] SMS escalation working (after 30 min unacknowledged)
- [ ] Health check endpoints return detailed status
- [ ] System runs 24 hours without crash
- [ ] 100 paper trades executed successfully
- [ ] All integration tests pass
- [ ] UAT checklist complete
- [ ] Deployment guide complete
- [ ] No critical or high-priority bugs

**Final Integration Verification:**
- [ ] Start system → startup checklist runs → main loop starts
- [ ] Create strategy → similarity check runs → appears in dashboard
- [ ] Set market regime → strategies adjust accordingly
- [ ] Run backtest → results displayed
- [ ] Start paper trading → signals generated
- [ ] Paper trade fills → position updates
- [ ] Multiple entries → staggered by 30 seconds
- [ ] Daily loss limit → circuit breaker triggers
- [ ] Activate kill switch → trading stops
- [ ] Dead man's switch test → heartbeat monitored
- [ ] Deactivate kill switch → trading resumes
- [ ] Exchange API down → read-only mode activates
- [ ] Critical alert → all channels notified
- [ ] Alert unacknowledged → escalation occurs
- [ ] Stop system → graceful shutdown
- [ ] Restart system → state recovered

**PRD Compliance Checklist:**
- [ ] Safety C: Multi-channel escalation (Telegram + Email + SMS)
- [ ] Safety E: Startup checklist runs before trading
- [ ] Reliability A: Graceful degradation on component failure
- [ ] Reliability C: Detailed health check endpoints
- [ ] Feature B: Market regime dropdown in dashboard
- [ ] Feature E: Entry timing coordination

**Sign-off:** _________________ Date: _________________

---

## 🎉 MVP COMPLETE

Congratulations! If all phases are complete and all checklists pass, the MVP is ready for production paper trading.

**Next steps after MVP:**
1. Run in paper trading for 30 days
2. Review performance metrics
3. Address any issues found
4. Plan V2 features (REST API, custom strategies, etc.)

---

**Previous Phase:** [05_PHASE_5_STRATEGY.md](./05_PHASE_5_STRATEGY.md)  
**Return to:** [00_MVP_TASK_INDEX.md](./00_MVP_TASK_INDEX.md)
