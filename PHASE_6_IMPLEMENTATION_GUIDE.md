# PHASE 6: BACKEND INTEGRATION MASTER GUIDE
## Complete Backend System Integration & Production Hardening
## 98 Hours | 29 Tasks | 2 Sessions | MVP Completion

---

## QUICK NAVIGATION

**Implementation Prompts:**
- [SESSION_6A_IMPLEMENTATION_PROMPT.md](SESSION_6A_IMPLEMENTATION_PROMPT.md) - Orchestrator & Alerting (46h, 15 tasks)
- [SESSION_6B_IMPLEMENTATION_PROMPT.md](SESSION_6B_IMPLEMENTATION_PROMPT.md) - API Layer & Testing (52h, 14 tasks)

**Verification Prompts:**
- [SESSION_6A_VERIFICATION_PROMPT.md](SESSION_6A_VERIFICATION_PROMPT.md) - Orchestrator/Alerting Validation (8h)
- [SESSION_6B_VERIFICATION_PROMPT.md](SESSION_6B_VERIFICATION_PROMPT.md) - API/System Validation (8h + 24h test)

**Phase Overview:**
- [docs/06_PHASE_6_BACKEND_INTEGRATION.md](docs/06_PHASE_6_BACKEND_INTEGRATION.md) - Source requirements
- [docs/00_MVP_TASK_INDEX.md](docs/00_MVP_TASK_INDEX.md) - Overall progress tracking
- [TRADING_SYSTEM_PRD.md](TRADING_SYSTEM_PRD.md) - Complete product specification

---

## PHASE 6 OVERVIEW

**Goal:** Wire all independently-built components (Phases 1-5) into a cohesive, production-ready trading system with orchestration, API exposure, multi-channel alerting, and comprehensive testing.

**Start Conditions:** Phase 5 complete (all strategies, backtesting, paper trading working)

**Exit Conditions:**
- System runs 24 hours without crash
- 100+ paper trades executed successfully
- All API endpoints return correct data
- Alerts delivered within 30 seconds
- 90%+ test coverage, Grade A+ quality
- All production audit findings resolved

**Timeline:** 2 weeks (Weeks 11-12)

---

## SESSION STRUCTURE

### SESSION 6A: ORCHESTRATOR & ALERTING (46 Hours)

**Purpose:** Build the core system brain and multi-channel notifications

**Sections:**
- **6.1 Orchestrator (30h, 9 tasks)**
  - Core coordinator
  - Startup checklist (pre-start validation)
  - Main trading loop (continuous execution)
  - Strategy processing (signals → orders)
  - Entry timing coordinator (stagger entries)
  - Graceful shutdown (clean state)
  - Health checker (system monitoring)
  - Graceful degradation (component failures)
  - Comprehensive tests

- **6.3 Alerting (16h, 6 tasks)**
  - Alert manager (multi-channel)
  - Telegram channel (immediate)
  - Escalation manager (Email 15min, SMS 30min, Critical 5min repeat)
  - Alert triggers (system events)
  - Rate limiting (prevent spam)
  - Comprehensive tests

**Critical Output:** System can start, run trading loop, handle failures, send alerts

### SESSION 6B: API LAYER & FINAL TESTING (52 Hours)

**Purpose:** Build interfaces and validate complete system

**Sections:**
- **6.2 API Layer (28h, 9 tasks)**
  - FastAPI application setup
  - System control endpoints (start/stop/status/regime)
  - Dashboard data endpoints (summary/equity/performance)
  - Account management (CRUD)
  - P&L tracking (daily/monthly/strategy/symbol)
  - API documentation (OpenAPI/Swagger)
  - API tests (comprehensive)
  - SSE event stream (real-time updates) ← KEY for efficiency

- **6.4 Final Testing (24h, 5 tasks)**
  - Integration test suite (12 end-to-end flows)
  - Load testing (100 concurrent, 50 req/s, memory leaks)
  - 24-hour stability test (zero crashes, stable memory)
  - UAT checklist (manual verification)
  - Deployment guide (step-by-step)

**Critical Output:** API working, real-time updates, system validated 24h, production-ready

---

## CRITICAL INVARIANTS (DO NOT VIOLATE)

### 1. **Orchestrator Coordinates All Components**
- No direct connections between subcomponents bypassing orchestrator
- All component access through orchestrator or dependency injection
- Status/health queries through orchestrator

### 2. **Startup Checklist is Mandatory**
- System CANNOT start if ANY check fails
- Checks: DB connection, DB integrity, API auth, API permissions, config, disk (>1GB), memory (>500MB), position sync, balance, strategy validation
- On failure: Alert operator immediately, do NOT start trading

### 3. **Kill Switch Checked First**
- Kill switch check is FIRST step in main loop
- If active: skip all trading, only monitor positions
- SAFETY PRIORITY

### 4. **Entry Staggering Rules Locked** (PRD Feature E)
- Minimum 30 seconds between entries (cascade prevention)
- Max 3 entries per minute (overload prevention)
- Same symbol 5-minute cooldown (doubling-up prevention)
- Priority queue by Sharpe ratio (quality first)
- Bypass: stop losses, take profits, kill switch orders

### 5. **Graceful Degradation via DegradationManager**
- Exchange API down → read-only mode (no new trades, monitor positions)
- Database slow → cache mode (read cache, queue writes)
- Strategy error → skip failing strategy, continue others
- Memory pressure → clear caches, force GC
- Component failures NEVER crash the loop

### 6. **All Timestamps Timezone-Aware UTC**
- All datetime use `datetime.now(timezone.utc)`
- Never use `datetime.utcnow()` (deprecated)
- Database timestamps marked as UTC

---

## ARCHITECTURE DIAGRAMS

### Data Flow: Orchestrator Lifecycle

```
START
  ↓
Startup Checklist (BLOCKING)
  ├─ Database connection
  ├─ Exchange API auth/perms
  ├─ Config validity
  ├─ Disk space (>1GB)
  ├─ Memory (>500MB)
  ├─ Position sync (no auto-correct)
  ├─ Balance check (5% tolerance)
  └─ Strategy validation
  ↓
[FAIL] → Alert operator → DO NOT START
  ↓
[PASS] → Initialize Components
  ↓
MAIN LOOP (continuous while _running=True)
  ├─ Check Kill Switch (FIRST)
  ├─ Check Circuit Breakers
  ├─ Check Degradation Mode
  ├─ Process Strategies → Signals
  ├─ Entry Coordinator → Queue Entries (30s, 3/min, 5min/symbol)
  ├─ Sync Positions
  ├─ Record P&L
  ├─ Health Check
  ├─ Log Metrics
  └─ Sleep (cycle_interval)
  ↓
[SHUTDOWN] → Graceful Shutdown
  ├─ Cancel all pending orders
  ├─ Optionally close positions
  ├─ Record final P&L
  ├─ Save system state
  ├─ Close DB
  └─ Send shutdown alert
  ↓
STOP
```

### Data Flow: Alert Escalation

```
ALERT GENERATED
  ↓
INFO Level
  └─ Telegram only
     (No escalation)

WARNING Level
  ├─ Telegram (immediate)
  └─ → Email (if not acknowledged after 15 min)

ERROR Level
  ├─ Telegram (immediate)
  ├─ Email (immediate)
  └─ → SMS (if not acknowledged after 30 min)

CRITICAL Level
  ├─ Telegram (immediate)
  ├─ Email (immediate)
  ├─ SMS (immediate)
  └─ → Repeat all channels every 5 min until acknowledged

ACKNOWLEDGED
  └─ Stop escalation timer
     Remove from pending queue
```

---

## KEY FORMULAS & THRESHOLDS

### 1. **Entry Timing Rules (Locked)**

```
Can Enter Now?
  = (entries_in_last_60s < 3)
    AND (seconds_since_last_entry >= 30)
    AND (symbol_not_on_5min_cooldown)

Wait Time = Max of:
  - Time until oldest entry falls outside 60s window
  - Time until 30s gap from last entry
```

### 2. **Regime Size Adjustment (Locked)**

```
Position Size Multiplier:
  IF strategy.avoid_regimes contains current_regime:
    size_multiplier = 0.0  (BLOCK entry completely)
  ELSE IF current_regime NOT IN strategy.preferred_regimes:
    size_multiplier = 0.5  (Reduce to 50%)
  ELSE:
    size_multiplier = 1.0  (Normal size)
```

### 3. **Health Check Thresholds**

```
Memory:
  Normal: < 70%
  Warning: 70-85%
  Critical: >= 85%

Database Latency:
  Normal: < 1000ms
  Warning: >= 1000ms
  Critical: > 2000ms

Market Data Staleness:
  Normal: < 5 minutes
  Critical: >= 5 minutes (no recent data)

Error Rate (rolling 1-hour):
  Normal: < 10 errors
  Warning: >= 10 errors

Disk Space:
  Normal: > 1GB free
  Critical: <= 1GB free
```

### 4. **API Response Time SLA**

```
Health Endpoints: < 100ms
Dashboard Endpoints: < 200ms
System Endpoints: < 200ms
All Others: < 500ms

Unacceptable: > 1000ms (slow operation)
```

---

## TEST DATA TEMPLATES

### Template 1: Simple Orchestrator Test

```python
@pytest.mark.asyncio
async def test_orchestrator_startup():
    """Verify orchestrator starts successfully."""
    # Create mocks for all components
    config = MockConfig(mode='paper', risk_limits=...)
    data_store = AsyncMock(spec=DataStore)
    market_data = AsyncMock(spec=MarketDataService)
    risk_controller = AsyncMock(spec=RiskController)
    order_manager = AsyncMock(spec=OrderManager)
    position_tracker = AsyncMock(spec=PositionTracker)
    strategy_engine = AsyncMock(spec=StrategyEngine)
    alert_manager = AsyncMock(spec=AlertManager)

    # Create orchestrator
    orch = Orchestrator(
        config, data_store, market_data, risk_controller,
        order_manager, position_tracker, strategy_engine, alert_manager
    )

    # Mock startup checklist to pass
    orch._components['data_store'].health_check.return_value = True

    # Start orchestrator (in test, run just initialization)
    await orch._initialize_components()

    # Verify components initialized
    assert orch._running == False  # Not running yet
    assert orch._status == SystemStatus.STOPPED
```

### Template 2: Entry Coordinator Test

```python
@pytest.mark.asyncio
async def test_entry_staggering():
    """Verify entries are staggered by 30 seconds."""
    coordinator = EntryCoordinator()

    # Create two mock signals
    signal1 = MockSignal(symbol='BTCUSDT', direction='BUY')
    strategy1 = MockStrategy(id='str_1', sharpe_ratio=1.5)

    signal2 = MockSignal(symbol='ETHUSDT', direction='BUY')
    strategy2 = MockStrategy(id='str_2', sharpe_ratio=1.2)

    # Queue first entry
    queued1 = await coordinator.queue_entry(signal1, strategy1)
    assert queued1 == True

    # Try to submit - should succeed (first entry)
    can_enter, wait = coordinator.can_enter_now()
    assert can_enter == True

    # Simulate submission
    submitted = await coordinator.process_queue(mock_order_manager)
    assert len(submitted) == 1

    # Try to submit second entry immediately - should fail
    can_enter, wait = coordinator.can_enter_now()
    assert can_enter == False
    assert wait > 25  # Less than 30s have passed

    # Simulate 30+ seconds passing
    with patch('datetime.now') as mock_now:
        future = datetime.now() + timedelta(seconds=31)
        mock_now.return_value = future

        can_enter, wait = coordinator.can_enter_now()
        assert can_enter == True
```

### Template 3: 24-Hour Stability Baseline

```
Starting Conditions:
- Paper trading mode
- 3 active strategies
- 1 minute cycle interval
- 1440 total cycles expected (24h * 60 min)

Expected Metrics:
- Memory start: ~350MB
- Memory peak: < 380MB (8.6% growth acceptable)
- Cycles completed: 1440 ± 5%
- Errors logged: 0
- Warnings logged: < 10
- Paper trades: 20-100 (strategy-dependent)
- Position sync checks: 24 (one per hour)
```

---

## IMPLEMENTATION CHECKLIST

### Before Implementation

- [ ] Read SESSION_6A_IMPLEMENTATION_PROMPT.md completely
- [ ] Review TRADING_SYSTEM_PRD.md sections 5, 6
- [ ] Check existing Phase 1-5 implementations for patterns
- [ ] Verify all decision files in `.claude/DECISIONS.md`
- [ ] Set up virtual environment and install dependencies
- [ ] Understand dependency injection pattern used

### During Implementation (Session 6A)

- [ ] Task 6.1.1-6.1.6: Complete all orchestrator tasks
- [ ] Task 6.3.1-6.3.5: Complete all alerting tasks
- [ ] After each task: Run unit tests and verify coverage >85%
- [ ] After section: Run integration tests
- [ ] Document any deviations from spec

### After Session 6A

- [ ] Run SESSION_6A_VERIFICATION_PROMPT.md (4 stages, 8 hours)
- [ ] All stages must pass before proceeding to Session 6B
- [ ] Address any issues found in verification
- [ ] Get sign-off on Orchestrator + Alerting

### Before Session 6B

- [ ] Session 6A components fully working and tested
- [ ] All critical invariants verified
- [ ] Orchestrator can start, run loop, degrade gracefully
- [ ] Alerts working in all channels with escalation

### During Implementation (Session 6B)

- [ ] Task 6.2.1-6.2.8: Complete all API tasks
- [ ] Task 6.4.1-6.4.5: Complete all testing tasks
- [ ] After API: Run API tests and verify coverage >80%
- [ ] After testing: Run 24-hour stability test
- [ ] Document any issues found

### After Session 6B

- [ ] Run SESSION_6B_VERIFICATION_PROMPT.md (4 stages, 8h + 24h test)
- [ ] 24-hour stability test must pass (zero crashes)
- [ ] UAT checklist all items pass
- [ ] API endpoints tested and responding correctly
- [ ] Get sign-off on complete system

### Before MVP Launch

- [ ] All 29 tasks completed
- [ ] >90% test coverage
- [ ] Grade A+ quality verified
- [ ] Zero critical or high-priority issues
- [ ] Deployment guide tested
- [ ] Team sign-off obtained

---

## DECISION REFERENCES

All decisions tracked in `.claude/DECISIONS.md` and `.agent/DECISIONS.md`:

- **DEC-2026-02-08-002:** SQLAlchemy 2.0 with Mapped[T] syntax
- **DEC-2026-02-08-003:** Timezone-aware timestamps (UTC only)
- **DEC-2026-02-08-004:** CORS security (not wildcard)
- **DEC-2026-02-08-005:** Real database health checks (not fake)
- **DEC-2026-02-08-006:** 100% type hints (mypy --strict)
- **DEC-2026-02-08-007:** Input validation at model layer (NaN/Infinity)
- **DEC-2026-02-08-008:** Structured logging (named parameters)
- **DEC-2026-02-08-010:** Lambda functions for mutable defaults
- **DEC-2026-02-08-011:** Boolean comparison with .is_()

**Locked MVP Scope Decisions:**
- **DEC-2026-01-15-001:** Crypto ONLY (no stocks/forex)
- **DEC-2026-01-15-002:** Binance ONLY (no other exchanges)
- **DEC-2026-01-15-003:** SQLite/PostgreSQL ONLY
- **DEC-2026-01-15-004:** Market orders ONLY
- **DEC-2026-01-15-005:** Monolithic ONLY (no microservices)

---

## PRODUCTION QUALITY REQUIREMENTS

### Code Quality

- ✅ **Type Hints:** 100% coverage, mypy --strict passes
- ✅ **Timezone Handling:** All UTC, never naive datetime
- ✅ **Input Validation:** NaN/Infinity checks on all financial values
- ✅ **Error Handling:** Comprehensive try/except, no silent failures
- ✅ **Logging:** Structured format (no f-strings), appropriate levels
- ✅ **Comments:** Explain WHY, not WHAT
- ✅ **Docstrings:** All classes and public methods documented

### Testing

- ✅ **Unit Test Coverage:** >85% for orchestrator and alerting
- ✅ **API Test Coverage:** >80% for endpoints
- ✅ **Integration Tests:** All 12 major flows tested end-to-end
- ✅ **Load Testing:** 100 concurrent, 50 req/s, memory leak detection
- ✅ **Stability Testing:** 24-hour run with zero crashes
- ✅ **Determinism:** Backtest results identical across 5 runs

### Production Readiness

- ✅ **No Critical Issues:** All issues resolved
- ✅ **No High-Priority Issues:** All issues resolved
- ✅ **Grade A+ Quality:** 100% production readiness
- ✅ **Performance:** Response times within SLA
- ✅ **Reliability:** 24-hour stability verified
- ✅ **Security:** No hardcoded values, CORS configured, input validated
- ✅ **Maintainability:** Clean code, documented, testable
- ✅ **Deployability:** Deployment guide complete and tested

---

## SUPPORT & DEBUGGING

**If You Get Stuck:**

1. **Check the implementation prompt** for your current task
2. **Review the critical invariants** (may be violating one)
3. **Run the verification prompt** for your session
4. **Check `.claude/DECISIONS.md`** for related decisions
5. **Review existing phase implementations** for patterns
6. **Ask for clarification** if specification is ambiguous

**Common Issues & Solutions:**

| Issue | Cause | Solution |
|-------|-------|----------|
| Startup always fails | Mock not configured | Verify mock has all required methods |
| Main loop hangs | Infinite sleep | Add timeout to all async operations |
| Alerts not sent | Rate limiting | Check that critical alerts bypass limit |
| SSE not flowing | EventBus not connected | Verify subscribers registered |
| P&L wrong | Commission calculation | Check applied both entry and exit |
| 24h test crashes | Memory leak | Add gc.collect(), check connections closed |
| API slow | N+1 queries | Use eager loading with selectinload |
| Tests flaky | Timing issues | Use mock.patch for datetime |

---

## TIMELINE ESTIMATE

**Realistic breakdown (98 hours total):**

- **Session 6A Setup:** 2 hours (environment, understanding)
- **Session 6A Implementation:** 42 hours (coding)
- **Session 6A Verification:** 8 hours (validation + fixes)
- **Session 6B Setup:** 1 hour (understanding)
- **Session 6B Implementation:** 40 hours (coding)
- **Session 6B Verification:** 8 hours (validation)
- **24-Hour Stability Test:** 24 hours (parallel)
- **Fixes & Sign-Off:** 5 hours

**Total with parallel stability test:** ~12 calendar days (intensive work)

---

**Status:** Phase 6 Ready for Implementation
**Quality Target:** Grade A+ (100% production ready)
**Next Milestone:** Phase 7 Frontend (begins after Phase 6 complete and signed off)

---

**Phase Index:** [00_MVP_TASK_INDEX.md](docs/00_MVP_TASK_INDEX.md)
**Previous Phase:** [docs/05_PHASE_5_STRATEGY.md](docs/05_PHASE_5_STRATEGY.md)
**Architecture Reference:** [ARCHITECTURE.md](ARCHITECTURE.md)
