# SESSION 4A VERIFICATION PROMPT
## Production Quality Verification & Sign-Off
**Execution Infrastructure Testing (Sections 4.1 + 4.2)**

**Role:** Production Quality Assurance Lead
**Task:** Verify Session 4A completion meets all production-grade quality standards
**Expected Duration:** 2.5-3 hours
**Result:** PASS or FAIL with detailed findings

---

## MANDATORY READING

1. `.claude/DECISIONS.md` (decision consistency)
2. `.claude/rules/zero-technical-debt.md` (quality standards)
3. `SESSION_4A_IMPLEMENTATION_PROMPT.md` (original requirements)
4. `docs/04_PHASE_4_EXECUTION.md` (specification)

---

## VERIFICATION WORKFLOW

### STAGE 1: Automated Quality Gates (30 minutes)

**Execute these commands in order. ALL must pass with 0 errors/violations.**

```bash
# 1. Type Safety (MANDATORY)
mypy src/core/execution/ src/brokers/binance/ --strict
# RESULT: Must show "Success: no issues found"

# 2. Code Linting
ruff check src/core/execution/ src/brokers/binance/
# RESULT: Must output nothing (0 violations)

# 3. Import Organization
isort src/core/execution/ src/brokers/binance/ --check --diff
# RESULT: Must show "All done! No files would be modified"

# 4. Unit Tests
pytest tests/unit/test_binance_execution.py tests/unit/test_order_manager.py -v --tb=short
# RESULT: Must show "passed" for ALL tests, no failures or errors

# 5. Integration Tests (requires testnet API keys)
pytest tests/integration/test_binance_orders.py tests/integration/test_order_manager_integration.py -v --tb=short
# RESULT: Must show "passed" for ALL tests

# 6. Coverage Report
pytest tests/unit/test_binance_execution.py tests/unit/test_order_manager.py \
  --cov=src/core/execution --cov=src/brokers/binance \
  --cov-report=term-missing | grep -E "^(src/|TOTAL)"
# RESULT: All files >90%, TOTAL >90%

# 7. Production Audit
@production-code-audit audit src/core/execution/ src/brokers/binance/
# RESULT: Must show Grade A- or higher, no CRITICAL or HIGH issues
```

**GATE RESULT:**
- [ ] ✅ All 7 gates PASS → Continue to Stage 2
- [ ] ❌ Any gate FAILS → Document failure, DO NOT proceed

---

### STAGE 2: Execution Engine Validation (30 minutes)

**Verify Binance Adapter implementation matches specification**

For each method in BinanceExecutionAdapter:

1. **Task 4.1.2 - Binance Adapter Initialization**
   - [ ] Adapter correctly implements ExecutionEngine ABC
   - [ ] Testnet/mainnet switching via config working
   - [ ] BinanceClient properly initialized
   - [ ] SymbolManager integration working
   - Unit test coverage: >85%

2. **Task 4.1.3 - Market Order Submission**
   - [ ] Submits market orders to Binance successfully
   - [ ] Quantity correctly rounded to step size
   - [ ] Returns OrderResult with filled details
   - [ ] Integration test: Market buy fills on testnet
   - Integration test: Market sell fills on testnet
   - Input validation: Rejects NaN/Infinity
   - Binance testnet order: Submit and verify fill

3. **Task 4.1.4 - Limit Order Submission**
   - [ ] Submits limit orders to Binance
   - [ ] All three TIF options work: GTC, IOC, FOK
   - [ ] Price correctly rounded to tick size
   - [ ] Integration test: Limit order on testnet
   - Integration test: Cancel limit order
   - Input validation: Rejects NaN/Infinity

4. **Task 4.1.5 - Stop Loss Order**
   - [ ] Creates STOP_LOSS_LIMIT order correctly
   - [ ] Stop price and limit price set correctly
   - [ ] Integration test: Stop loss on testnet
   - Input validation: Validates stop price vs entry

5. **Task 4.1.6 - Take Profit Order**
   - [ ] Creates TAKE_PROFIT_LIMIT order correctly
   - [ ] Price rounded to tick size
   - [ ] Integration test: Take profit on testnet

6. **Task 4.1.7 - Order Cancellation**
   - [ ] Cancels single order successfully
   - [ ] Cancels all orders for symbol
   - [ ] Handles already-filled orders gracefully (no error)
   - [ ] Returns cancelled order IDs
   - Integration test: Cancel on testnet

7. **Task 4.1.8 - Order Status Polling**
   - [ ] Status mapping correct (NEW→SUBMITTED, FILLED→FILLED, etc.)
   - [ ] Partial fills tracked
   - [ ] Commission captured
   - All statuses tested: NEW, PARTIALLY_FILLED, FILLED, CANCELED, REJECTED, EXPIRED

8. **Task 4.1.9 - Balance Fetching**
   - [ ] Get single asset balance
   - [ ] Get all balances
   - [ ] Tracks free vs locked balance
   - Integration test: Get balances on testnet

**VALIDATION RESULT:**
- [ ] ✅ All methods PASS → Continue to Stage 3
- [ ] ❌ Any method FAILS → Document, fix code, re-test

---

### STAGE 3: Order Manager Validation (30 minutes)

**Verify OrderManager implementation matches specification**

1. **Task 4.2.1 - Order Manager Creation**
   - [ ] OrderManager class created
   - [ ] Correctly integrates ExecutionEngine (from 4.1)
   - [ ] Correctly integrates RiskController (from Phase 3)
   - [ ] Tracks pending orders in-memory and database
   - [ ] Loads pending orders on startup
   - Unit test: Basic operations

2. **Task 4.2.2 - Order Submission Flow**
   - [ ] **CRITICAL: Sequence verification (in strict order):**
     - [ ] Risk controller check runs FIRST (approves/rejects)
     - [ ] Order saved to database BEFORE submission to exchange
     - [ ] Execution engine called AFTER database persist
     - [ ] Status updated to SUBMITTED
     - [ ] Monitoring task started
   - [ ] Risk rejection logged with reason
   - [ ] Database failure handled gracefully (with rollback attempt)
   - [ ] Execution engine failure logged and order marked REJECTED
   - Unit test: Success path (all steps)
   - Unit test: Risk rejection path
   - Unit test: Database failure path

3. **Task 4.2.3 - Order Status Tracking**
   - [ ] Monitoring starts immediately after submission
   - [ ] Initial polling interval: 1 second
   - [ ] Backoff after 30 seconds: 5-second intervals
   - [ ] Backoff after 5 minutes: 10-second intervals
   - [ ] Max polling: 1000 polls (~30 minutes)
   - [ ] Status transitions logged
   - [ ] Partial fills tracked
   - [ ] Terminal states detected (FILLED, CANCELLED, REJECTED)
   - Unit test: Status transitions
   - Unit test: Polling backoff

4. **Task 4.2.4 - Order Fill Handling**
   - [ ] Creates Trade record for fills
   - [ ] Updates Order with filled quantity and average price
   - [ ] Updates Position via position_tracker
   - [ ] Commission tracked correctly
   - [ ] Fill logged with details
   - Unit test: Trade creation
   - Unit test: Commission capture

5. **Task 4.2.5 - Bracket Orders**
   - [ ] Bracket order structure created
   - [ ] Entry order submitted first
   - [ ] SL and TP orders submitted on entry fill
   - [ ] OCO linking: When one leg fills, other cancelled
   - [ ] Race condition handled (if both fill simultaneously)
   - Unit test: Bracket order creation
   - Unit test: OCO cancellation

6. **Task 4.2.6 - Order Timeout Handling**
   - [ ] Market orders timeout after 30 seconds
   - [ ] Limit orders timeout after 1 hour
   - [ ] Stop/take profit orders NEVER timeout
   - [ ] Auto-cancellation on timeout
   - [ ] Timeout logged
   - Unit test: Timeout calculation
   - Unit test: Auto-cancellation trigger

7. **Task 4.2.7 - Order Reconciliation**
   - [ ] Reconciliation compares local to exchange
   - [ ] Detects orders on exchange not in local database
   - [ ] Detects orders in local not on exchange
   - [ ] Auto-corrects minor discrepancies
   - [ ] Minor mismatch: 1-2 orders
   - [ ] Major mismatch: 3+ orders (alerts, doesn't auto-correct)
   - [ ] Runs on startup
   - [ ] Runs periodically (every 5 minutes)
   - Unit test: Reconciliation scenarios

8. **Task 4.2.8a - Order State Reconciliation (PRD Feature I)**
   - [ ] **CRITICAL: Runs every 60 seconds**
   - [ ] Reconciles open orders (local vs exchange)
   - [ ] Reconciles positions (delegates to PositionTracker)
   - [ ] Reconciles balances (local vs exchange)
   - [ ] Minor difference (<1%): Auto-corrects
   - [ ] Major difference (>=1%): Alerts operator and pauses trading
   - [ ] Mismatches logged for audit
   - Unit test: Minor mismatch (<1%) auto-corrected
   - Unit test: Major mismatch (>=1%) alerts and pauses
   - Verify: Run for 2 minutes and confirm reconciliation completes every 60 seconds

9. **Task 4.2.8 - Order Manager API**
   - [ ] POST /api/orders submits order
   - [ ] GET /api/orders lists orders (with filters)
   - [ ] GET /api/orders/{id} gets single order
   - [ ] DELETE /api/orders/{id} cancels order
   - [ ] All endpoints return proper HTTP status codes
   - [ ] Error handling: 400, 404, 422, 500
   - Integration test: Full API workflow

10. **Task 4.2.9 - Order Manager Tests**
    - [ ] All order flows tested
    - [ ] Unit tests use mock execution engine
    - [ ] Integration tests use testnet
    - [ ] >90% code coverage (unit)
    - [ ] >85% code coverage (integration)

**VALIDATION RESULT:**
- [ ] ✅ All order flows PASS → Continue to Stage 4
- [ ] ❌ Any flow FAILS → Document, fix code, re-test

---

### STAGE 4: Integration Testing (30 minutes)

**Test that Session 4A components integrate correctly with Phase 3 and database**

**Critical Integration Points:**

1. **OrderManager + RiskController Integration**
   - [ ] RiskController successfully approves/rejects orders
   - [ ] Approved orders proceed to execution
   - [ ] Rejected orders don't submit to exchange
   - [ ] Rejection reasons logged
   - Test scenario: Submit order that violates position limit → Should be rejected

2. **OrderManager + ExecutionEngine Integration**
   - [ ] OrderManager calls ExecutionEngine methods
   - [ ] Order data flows correctly
   - [ ] Status updates flow back from ExecutionEngine
   - [ ] Error handling works end-to-end
   - Test scenario: Submit order → Verify it reaches Binance testnet

3. **OrderManager + Database Integration**
   - [ ] Orders persisted before submission
   - [ ] Status updates persist immediately
   - [ ] Trades created on fill
   - [ ] Orders retrieved on startup (for monitoring)
   - Test scenario: Submit order → Restart app → Order still being monitored

4. **Full Order Lifecycle**
   - [ ] Submit market order
   - [ ] Order fills on testnet
   - [ ] Trade record created
   - [ ] Status transitions: PENDING → SUBMITTED → FILLED
   - [ ] Monitoring stops on terminal state
   - Test on testnet: BUY BTCUSDT market → verify complete flow

5. **Bracket Order Lifecycle**
   - [ ] Entry order submitted
   - [ ] On entry fill: SL and TP submitted
   - [ ] OCO linking works: one leg fills, other cancelled
   - [ ] Database reflects final state correctly
   - Test on testnet: Bracket order → entry fills → verify SL/TP creation

**INTEGRATION RESULT:**
- [ ] ✅ All integration tests PASS → Continue to Stage 5
- [ ] ❌ Any integration test FAILS → Document, fix code, re-test

---

### STAGE 5: Code Quality Audit (20 minutes)

**Manual inspection of code quality standards**

**Type Hints (100% Required):**
```bash
# Search for missing type hints
grep -rn "def.*):$" src/core/execution/ src/brokers/binance/
# Result: MUST show 0 matches (all functions have return types)

grep -rn "def.*:$" src/core/execution/ src/brokers/binance/ | grep -v " -> "
# Result: MUST show 0 matches
```

- [ ] Every `def` has parameter types and return type
- [ ] All class attributes typed via `Mapped[T]`
- [ ] No bare `Any` without justification comment
- [ ] No implicit `Optional` (use `Optional[T]` explicitly)

**Naming Consistency:**
- [ ] OrderManager uses consistent naming throughout
- [ ] No synonyms for same concept (e.g., "order" vs "order_obj")
- [ ] Symbol parameter always named `symbol` (not `sym`, `ticker`, etc.)
- [ ] Consistent use of `order_id`, not mixed with `id`

**Input Validation:**
- [ ] All numeric inputs (price, quantity) validated for NaN/Infinity
- [ ] All API inputs validated for type and range
- [ ] Error messages descriptive ("quantity must be positive" not just "error")

**Structured Logging:**
```bash
# Check logging format
grep -n "logger\." src/core/execution/ src/brokers/binance/ | head -20
# Should see: logger.info("event_name", field1=value1, field2=value2)
# NOT: logger.info(f"Event: {value1}, {value2}")
```

- [ ] All logging uses structured format (event name + fields)
- [ ] No f-strings in log messages
- [ ] Log levels appropriate (info, warning, error, critical)

**Error Handling:**
- [ ] Try-except blocks around all API calls
- [ ] Specific exceptions caught (not bare `except:`)
- [ ] Logging on all error paths
- [ ] Errors propagated correctly (raised, not silently caught)

**Database Operations:**
- [ ] All database calls via DataStore (not raw SQL)
- [ ] No N+1 query patterns
- [ ] Transactions used where needed (order persist + status update)

**AUDIT RESULT:**
- [ ] ✅ All standards MET → Continue to Stage 6
- [ ] ❌ Issues found → List them, fix code, re-verify

---

### STAGE 6: Decision Consistency Check (10 minutes)

**Verify implementation follows all architectural decisions**

**Check DEC-2026-02-08-XXX decisions:**

```bash
# Type hints 100%
grep -r "def.*):$" src/core/execution/
# Result: Should show 0

# Timezone-aware timestamps
grep -r "datetime.utcnow\|datetime.now()" src/core/execution/
# Result: Should show 0 (use timezone.utc)

# Input validation at model layer
grep -r "@validates\|ValueError" src/core/execution/
# Result: Should find validation decorators
```

**Decision Verification:**
- [ ] Type hints 100% complete (DEC-2026-02-08-006)
- [ ] Timezone-aware timestamps used (DEC-2026-02-08-003)
- [ ] Input validation comprehensive (DEC-2026-02-08-007)
- [ ] Structured logging used (DEC-2026-02-08-008)
- [ ] SQLAlchemy 2.0 patterns (DEC-2026-02-08-002)
- [ ] No locked decisions violated

**DECISION RESULT:**
- [ ] ✅ All decisions followed → Continue to Stage 7
- [ ] ❌ Violations found → Fix code, update decisions if needed

---

### STAGE 7: Performance Validation (15 minutes)

**Verify Session 4A meets performance targets**

Test with 1000 historical orders from testnet (if available):

```python
import time

# Scenario 1: Order status polling (simulate 100 concurrent orders)
start = time.time()
for i in range(100):
    await order_manager.monitor_order(order)  # Start monitoring
elapsed = time.time() - start
assert elapsed < 5, f"Monitoring 100 orders took {elapsed}s, target <5s"

# Scenario 2: Order reconciliation (1000 orders)
orders = [create_test_order() for _ in range(1000)]
start = time.time()
result = await order_manager.reconcile_orders()
elapsed = time.time() - start
assert elapsed < 10, f"Reconciling 1000 orders took {elapsed}s, target <10s"

# Scenario 3: State reconciliation (every 60 seconds)
start = time.time()
result = await order_state_reconciler.reconcile()
elapsed = time.time() - start
assert elapsed < 5, f"State reconciliation took {elapsed}s, target <5s"
```

**Performance Checklist:**
- [ ] Monitoring 100 orders: < 5 seconds
- [ ] Reconciling 1000 orders: < 10 seconds
- [ ] State reconciliation (every 60s): < 5 seconds
- [ ] API response time (submit order): < 1 second
- [ ] API response time (list orders): < 2 seconds
- [ ] Polling interval accurate (±10%)

**PERFORMANCE RESULT:**
- [ ] ✅ All targets MET → Continue to Stage 8
- [ ] ❌ Any target MISSED → Optimize code, re-test

---

### STAGE 8: Final Sign-Off (10 minutes)

**Complete final verification and sign-off**

**Final Checklist:**
- [ ] Stage 1: Automated gates - ALL PASS
- [ ] Stage 2: Execution engine - ALL METHODS PASS
- [ ] Stage 3: Order manager - ALL FLOWS PASS
- [ ] Stage 4: Integration - ALL TESTS PASS
- [ ] Stage 5: Code quality - ALL STANDARDS MET
- [ ] Stage 6: Decisions - ALL CONSISTENT
- [ ] Stage 7: Performance - ALL TARGETS MET

**Coverage Summary:**
```
src/core/execution/interface.py         >90%  ✅
src/core/execution/order_manager.py    >90%  ✅
src/brokers/binance/execution.py       >90%  ✅
src/api/routes/orders.py               >90%  ✅
TOTAL                                  >90%  ✅
```

**Production Audit Grade:** A- or higher ✅

**Integration Test Checklist:**
- [ ] Submit market buy → fills → persists to database
- [ ] Submit market sell → fills → updates database
- [ ] Submit limit buy → wait → cancel
- [ ] Submit bracket order → entry fills → SL/TP created
- [ ] Order reconciliation detects discrepancies
- [ ] Order state reconciliation runs every 60 seconds
- [ ] Status updates flow through monitoring
- [ ] Commission tracked correctly

**Final Status:**
```
[✅] Type Safety: PASS (mypy --strict)
[✅] Code Quality: PASS (ruff, isort)
[✅] Tests: PASS (all pass, >90% coverage)
[✅] Execution Engine: PASS (all methods tested)
[✅] Order Manager: PASS (all flows tested)
[✅] Integration: PASS (Phase 3 compatible)
[✅] Performance: PASS (all targets met)
[✅] Decisions: PASS (all consistent)
[✅] Production Audit: PASS (Grade A-)

OVERALL: ✅ PRODUCTION READY - Ready for Session 4B
```

---

## 🔧 DEBUGGING GUIDE: Common Failures & Solutions

If tests fail, use this guide to diagnose the issue:

### **Issue: mypy Type Safety Fails**

**Symptoms:**
```
error: Function is missing a return type annotation
error: Argument "quantity" to "submit_order" has incompatible type "None"
```

**Root Causes & Solutions:**

| Error Message | Root Cause | Solution |
|---------------|-----------|----------|
| `missing a return type` | Function defined without `->` | Add `-> ReturnType:` to every `async def` |
| `incompatible type` | Parameter type mismatch | Check OrderRequest fields match submit_order params |
| `Optional` issues | Using `T` instead of `Optional[T]` | Import Optional, use `Optional[Type]` for nullable fields |

**Fix Process:**
1. Run: `mypy src/core/execution/interface.py --strict --show-error-codes`
2. Copy first error line
3. Open that file and line number
4. Add type hint: `def method(param: str) -> bool:`
5. Rerun mypy, fix next error
6. Repeat until "Success: no issues found"

---

### **Issue: Binance Adapter Integration Test Fails**

**Symptoms:**
```
BinanceExecutionError: BinanceClient not connected
ConnectionError: Failed to reach testnet
OrderSubmissionError: API call failed (OrderRejectCount threshold exceeded)
```

**Root Causes & Solutions:**

| Error | Cause | Solution |
|-------|-------|----------|
| `not connected` | Missing/invalid API keys | Check `.env` has `BINANCE_TESTNET_API_KEY`, `BINANCE_TESTNET_API_SECRET` |
| `Failed to reach` | Network issue or endpoint wrong | Verify testnet URL is `https://testnet.binance.vision` |
| `OrderRejectCount` | Too many rejected orders | Slow down test, wait between orders, check symbol validity |

**Debugging Steps:**
```bash
# Step 1: Verify API keys are set
python -c "import os; print(os.getenv('BINANCE_TESTNET_API_KEY'))"
# Should print your API key, not None

# Step 2: Test connectivity directly
python -c "
from src.brokers.binance.client import BinanceClient
client = BinanceClient(use_testnet=True)
print(f'Connected: {client.is_connected}')
"

# Step 3: Verify symbol is valid
python -c "
from src.data.symbol_manager import SymbolManager
sm = SymbolManager()
print(sm.is_valid_symbol('BTCUSDT'))  # Should be True
print(sm.get_step_size('BTCUSDT'))     # Should be > 0
"

# Step 4: Test order submission with logging
python -c "
import asyncio
import logging
logging.basicConfig(level=logging.DEBUG)

from src.brokers.binance.execution import BinanceExecutionAdapter
from src.brokers.binance.client import BinanceClient
from src.data.symbol_manager import SymbolManager

async def test():
    client = BinanceClient(use_testnet=True)
    sm = SymbolManager()
    adapter = BinanceExecutionAdapter(client, sm, use_testnet=True)

    # Try submitting a small market order
    result = await adapter.submit_order(
        symbol='BTCUSDT',
        side='BUY',
        quantity=0.001,
        order_type='MARKET'
    )
    print(f'Order result: {result}')

asyncio.run(test())
"
```

---

### **Issue: Order Submission Flow Tests Fail**

**Symptoms:**
```
AssertionError: order.status = PENDING, expected SUBMITTED
AssertionError: order not found in database
OrderRejectedError: Position size exceeds limit
```

**Root Causes & Solutions:**

| Failure | Cause | Solution |
|---------|-------|----------|
| Status wrong | Monitoring didn't run | Mock needs to update status immediately, or wait longer |
| Order not in DB | DB transaction not committed | Verify DataStore.create_order() commits before returning |
| Risk rejection | RiskController rejecting valid orders | Check mock returns approved=True for test orders |

**Fix Process:**

```python
# In test file, verify flow step-by-step:

async def test_order_submission_flow():
    # 1. Setup
    order_manager = OrderManager(mock_engine, mock_controller, mock_store)
    request = OrderRequest(symbol="BTCUSDT", side="BUY", quantity=0.1)

    # 2. Step-by-step verification
    print("Before submit:")
    initial_orders = await mock_store.get_pending_orders()
    print(f"  Orders in DB: {len(initial_orders)}")  # Should be 0

    # 3. Submit
    print("Submitting order...")
    order = await order_manager.submit_order(request)

    # 4. Verify each step
    print(f"After submit, order.status = {order.status.value}")
    assert order.status == OrderStatus.SUBMITTED, f"Expected SUBMITTED, got {order.status.value}"

    print(f"Order in memory ID: {order.id}")
    # Verify in database
    db_order = await mock_store.get_order(order.id)
    print(f"Order in DB: {db_order is not None}")
    assert db_order is not None, "Order not persisted to database"
    assert db_order.status == OrderStatus.SUBMITTED, f"DB order status wrong: {db_order.status}"

    print("✓ All steps passed")
```

---

### **Issue: Order Monitoring Not Detecting Fills**

**Symptoms:**
```
Order status stays SUBMITTED forever
Monitoring task runs but doesn't update status
Fill notification never sent
```

**Root Causes & Solutions:**

| Cause | Symptom | Solution |
|-------|---------|----------|
| Status not changing in mock | Mock always returns same status | Mock must return updated status on subsequent calls |
| Not awaiting monitoring | Test checks immediately before monitor runs | Add `await asyncio.sleep(1.5)` to give monitor time |
| DB not persisting updates | Status not saved | Verify mock_store.update_order() is called |
| Terminal state not detected | Monitor keeps polling after fill | Check status mapping: FILLED → OrderStatus.FILLED |

**Debugging Monitoring:**

```python
async def test_order_monitoring():
    # Setup mock to return SUBMITTED first, then FILLED
    call_count = 0

    async def mock_get_status(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return OrderResult(status=OrderStatus.SUBMITTED, ...)
        else:
            return OrderResult(status=OrderStatus.FILLED, filled_quantity=0.1, ...)

    mock_engine.get_order_status = mock_get_status

    # Start monitoring
    order = Order(id="test-1", status=OrderStatus.SUBMITTED, ...)
    monitor_task = asyncio.create_task(order_manager._monitor_order(order))

    # Wait for monitoring to run (at least 2 polls)
    await asyncio.sleep(2.5)  # First poll at 1s, second at 2s

    # Check results
    print(f"Mock was called {call_count} times")
    print(f"Order status: {order.status.value}")
    assert order.status == OrderStatus.FILLED, "Monitoring didn't detect fill"
    assert call_count >= 2, "Monitoring didn't poll enough times"

    # Wait for monitor to exit gracefully
    try:
        await asyncio.wait_for(monitor_task, timeout=1)
    except asyncio.TimeoutError:
        print("Monitor still running (expected if FILLED stops it)")
```

---

### **Issue: Production Audit Fails**

**Symptoms:**
```
Grade D (75%): Multiple CRITICAL issues
ERROR: Unhandled exceptions possible
ERROR: Missing error handling in execute path
```

**Root Causes:**

| Issue | Impact | Fix |
|-------|--------|-----|
| No try-except around API calls | App crashes on network error | Wrap all `execution_engine.` calls in try-except |
| Missing validation | Invalid data crashes calculation | Add `if math.isnan(x)` checks |
| Unlogged errors | No visibility to failures | Log all exceptions with context |

**Fix Process:**
1. Run: `@production-code-audit audit src/core/execution/ --verbose`
2. Find first CRITICAL issue
3. Go to file and line number
4. Add error handling: wrap in try-except, add logging
5. Rerun audit, fix next issue

---

## FAILURE PROTOCOL

If ANY stage fails:

1. **Document the failure:**
   - Stage number
   - Specific failure (test name, metric, code location, etc.)
   - Error message (full stack trace if applicable)
   - Root cause analysis

2. **Fix the issue:**
   - Update code
   - Re-run relevant stage
   - Verify fix doesn't break other stages

3. **Re-test:**
   - Run failed stage again
   - Verify it now passes
   - Run integration test to ensure no regressions

4. **Document resolution:**
   - What was fixed and why
   - Root cause analysis
   - Prevention for future

**Only mark as PASS when ALL stages pass without issue.**

---

## DELIVERABLES

After successful verification:

1. **Verification Report** (this document completed with all checkboxes)
2. **Code ready for Session 4B**
3. **Test coverage report** (>90%)
4. **Performance report** (all targets met)
5. **Decision consistency audit** (all verified)

---

## ESTIMATED TIME

- Stage 1 (Automated): 30 min
- Stage 2 (Execution Engine): 30 min
- Stage 3 (Order Manager): 30 min
- Stage 4 (Integration): 30 min
- Stage 5 (Code Quality): 20 min
- Stage 6 (Decisions): 10 min
- Stage 7 (Performance): 15 min
- Stage 8 (Sign-Off): 10 min

**Total: ~2.5-3 hours**

---

## SUCCESS CRITERIA

**Session 4A is PRODUCTION READY when:**
- ✅ All 8 stages PASS
- ✅ mypy --strict: 0 errors
- ✅ ruff check: 0 violations
- ✅ pytest: 100% pass (all tests)
- ✅ Coverage: >90% per file, >90% total
- ✅ All execution methods work on testnet
- ✅ Order lifecycle complete: submit → track → fill → persist
- ✅ Production audit: Grade A- or higher
- ✅ Ready for Session 4B (Position Tracking)

**If ALL checkpoints are ✅, sign off with:**
```
SESSION 4A: ✅ COMPLETE & PRODUCTION READY
Verified: [DATE]
Ready for: Session 4B (Position Tracking & Execution Quality)
```

---

**Prompt Version:** 1.0
**Last Updated:** 2026-02-13
**Applies To:** Session 4A Verification (Sections 4.1 + 4.2)
