# SESSION 4B VERIFICATION PROMPT
## Production Quality Verification & Sign-Off
**Position Tracking & Execution Quality (Sections 4.3 + 4.4)**

**Role:** Production Quality Assurance Lead
**Task:** Verify Session 4B completion meets all production-grade quality standards
**Expected Duration:** 2.5-3 hours
**Result:** PASS or FAIL with detailed findings

---

## MANDATORY READING

1. `.claude/DECISIONS.md` (decision consistency)
2. `.claude/rules/zero-technical-debt.md` (quality standards)
3. `SESSION_4B_IMPLEMENTATION_PROMPT.md` (original requirements)
4. `docs/04_PHASE_4_EXECUTION.md` (specification)
5. `SESSION_4A_VERIFICATION_PROMPT.md` (Session 4A baseline)

---

## VERIFICATION WORKFLOW

### STAGE 1: Automated Quality Gates (30 minutes)

**Execute these commands in order. ALL must pass with 0 errors/violations.**

```bash
# 1. Type Safety (MANDATORY)
mypy src/core/execution/ --strict
# RESULT: Must show "Success: no issues found"

# 2. Code Linting
ruff check src/core/execution/
# RESULT: Must output nothing (0 violations)

# 3. Import Organization
isort src/core/execution/ --check --diff
# RESULT: Must show "All done! No files would be modified"

# 4. Unit Tests
pytest tests/unit/test_position_tracker.py tests/unit/test_execution_quality.py -v --tb=short
# RESULT: Must show "passed" for ALL tests, no failures or errors

# 5. Integration Tests
pytest tests/integration/test_position_tracker_integration.py -v --tb=short
# RESULT: Must show "passed" for ALL tests

# 6. Coverage Report
pytest tests/unit/test_position_tracker.py tests/unit/test_execution_quality.py \
  --cov=src/core/execution \
  --cov-report=term-missing | grep -E "^(src/|TOTAL)"
# RESULT: All files >90%, TOTAL >90%

# 7. Production Audit
@production-code-audit audit src/core/execution/
# RESULT: Must show Grade A- or higher, no CRITICAL or HIGH issues
```

**GATE RESULT:**
- [ ] ✅ All 7 gates PASS → Continue to Stage 2
- [ ] ❌ Any gate FAILS → Document failure, DO NOT proceed

---

### STAGE 2: Position Tracker Validation (35 minutes)

**Verify PositionTracker implementation matches specification**

1. **Task 4.3.1 - Position Tracker Creation**
   - [ ] PositionTracker class created
   - [ ] Loads open positions from database on init
   - [ ] Tracks positions in `_positions` cache (symbol → Position)
   - [ ] All methods have full type hints
   - [ ] Correctly integrates DataStore and MarketDataService
   - Unit test: Basic position operations

2. **Task 4.3.2 - Position Opening**
   - [ ] Opens new position from trade fill
   - [ ] Sets: entry_price, quantity, side, opened_at
   - [ ] Optional: stop_loss_price, take_profit_price
   - [ ] Adds to cache and persists to database
   - [ ] Input validation: Rejects NaN/Infinity
   - [ ] Works for BUY and SELL sides
   - Unit test: BUY and SELL position opening

3. **Task 4.3.3 - Position Updates**
   - [ ] **Scenario 1: Adding to position (same direction)**
     - [ ] Calculates new average entry: (old_qty * old_avg + new_qty * new_price) / (old_qty + new_qty)
     - [ ] Updates quantity and entry_price
     - Test: BUY @ 45000, add BUY @ 46000 → avg = 45500
   - [ ] **Scenario 2: Partial close (opposite direction, partial quantity)**
     - [ ] Calculates realized P&L: (fill_price - entry_price) * fill_qty - commission
     - [ ] Reduces quantity, adds to total_realized_pnl
     - Test: Own 1 BTC @ 45000, sell 0.5 BTC @ 46000 → P&L = 500
   - [ ] **Scenario 3: Full close (opposite direction, full quantity)**
     - [ ] Calculates final realized P&L
     - [ ] Sets closed_at and status=CLOSED
     - [ ] Removes from cache
     - Test: Own 1 BTC @ 45000, sell 1 BTC @ 46000 → position closed
   - [ ] Commission included in P&L calculation
   - Unit test: All three scenarios

4. **Task 4.3.4 - P&L Calculator**
   - [ ] **Unrealized P&L for LONG:**
     ```
     unrealized_pnl = (current_price - entry_price) * quantity - commission_paid
     ```
     - Test: Entry 45000, current 46000, qty 0.5, commission 5 = (46000-45000)*0.5-5 = 495
   - [ ] **Unrealized P&L for SHORT:**
     ```
     unrealized_pnl = (entry_price - current_price) * quantity - commission_paid
     ```
     - Test: Entry 46000 (short), current 45000, qty 0.5, commission 5 = (46000-45000)*0.5-5 = 495
   - [ ] **Return % calculation:**
     ```
     return_pct = (unrealized_pnl / (entry_price * quantity)) * 100
     ```
     - Test: unrealized 500 on 22500 investment = 2.22%
   - [ ] **Realized P&L:** Stored in position.total_realized_pnl (accumulated)
   - [ ] Edge cases: Zero quantity, NaN price, zero entry price
   - Unit test: P&L calculations with manual verification (must match exactly)

5. **Task 4.3.5 - Position Sync**
   - [ ] Gets all open positions from local cache
   - [ ] For each position: Gets exchange balance for symbol
   - [ ] Compares local quantity to exchange balance
   - [ ] On mismatch: Logs discrepancy, updates local quantity
   - [ ] Returns PositionSyncResult: total, synced, corrected, discrepancies
   - [ ] Runs on startup, every 5 minutes, and on-demand
   - [ ] Handles API errors gracefully (continue syncing others)
   - Unit test: Position sync with matching balances
   - Unit test: Position sync with discrepancies detected

6. **Task 4.3.5a - Position Staleness Monitor (PRD Feature K)**
   - [ ] **Thresholds by strategy type:**
     - [ ] Day trading: warn 24h, review 48h, max 72h
     - [ ] Swing trading: warn 7d, review 14d, max 30d
     - [ ] Position trading: warn 30d, review 60d, max 90d
   - [ ] **Profitable position extension:**
     - [ ] If position.unrealized_pnl > 0: All thresholds × 1.5
     - Test: Profitable position held 10 days (day trading) → warn threshold 36h (24h × 1.5)
   - [ ] **Staleness checks triggered:**
     - [ ] should_warn: Exceeded warning threshold
     - [ ] should_review: Exceeded force_review threshold
     - [ ] should_close: Exceeded max_hold threshold
   - [ ] **Actions on staleness:**
     - [ ] Warning: Send alert to operator
     - [ ] Review: Add to queue, send alert
     - [ ] Max hold: Auto-close (if enabled) or send alert
   - [ ] **Operator override:**
     - [ ] Can mark position as "intentionally long-term"
     - [ ] Exempted from staleness checks
   - [ ] **Scheduled task:** Runs every hour
   - Unit test: Staleness calculation for different strategy types
   - Unit test: Profitable position extension (1.5x)
   - Unit test: All three alert levels triggered

7. **Task 4.3.6 - Position API Endpoints**
   - [ ] `GET /api/positions` - Lists all open positions with P&L
   - [ ] `GET /api/positions/{symbol}` - Gets single position
   - [ ] `DELETE /api/positions/{symbol}` - Closes position (market order)
   - [ ] `GET /api/positions/analysis/staleness` - Staleness analysis
   - [ ] Response format includes: symbol, side, qty, entry_price, current_price, unrealized_pnl, return_pct
   - [ ] Error handling: 404 (not found), 400 (invalid), 500 (error)
   - Integration test: Full API lifecycle

8. **Task 4.3.7 - Position Tracker Tests**
   - [ ] All position lifecycle scenarios tested (open, add, partial close, full close)
   - [ ] P&L calculations verified with manual calculations
   - [ ] Staleness logic tested
   - [ ] API endpoints tested
   - [ ] >90% code coverage (unit)
   - [ ] >85% code coverage (integration)

**VALIDATION RESULT:**
- [ ] ✅ All position features PASS → Continue to Stage 3
- [ ] ❌ Any feature FAILS → Document, fix code, re-test

---

### STAGE 3: Execution Quality Validation (35 minutes)

**Verify execution quality monitoring implementation**

1. **Task 4.4.1 - Slippage Tracker**
   - [ ] Records slippage for all fills
   - [ ] Slippage formula correct (shows as % and basis points):
     - [ ] BUY: ((actual - expected) / expected) * 100
     - [ ] SELL: ((expected - actual) / expected) * 100
     - Test: BUY expected 45000, actual 45050 → slippage = +0.11% (50/45000)
   - [ ] Stores SlippageRecord: order_id, symbol, side, expected, actual, slippage_pct, slippage_bps
   - [ ] Methods available:
     - [ ] `record()` - Record slippage
     - [ ] `get_average_slippage()` - Overall or by-symbol
     - [ ] `get_slippage_stats()` - Comprehensive statistics
   - [ ] Statistics include: total, average, best, worst, by-symbol, by-side
   - Unit test: Slippage calculation (positive, negative, zero)

2. **Task 4.4.1a - Pre-Trade Slippage Estimation (PRD Feature F)**
   - [ ] **Estimation model components:**
     - [ ] Base slippage: 0.05% (minimum)
     - [ ] Size factor: (order_size / avg_daily_volume) * 0.5%
     - [ ] Volatility factor: (current_ATR / avg_ATR) * 0.1%
     - [ ] Spread factor: current_spread / 2
     - [ ] Total: sum of all components
   - [ ] **Thresholds:**
     - [ ] Warn: > 0.3% estimated slippage
     - [ ] Block: > 1.0% estimated slippage
   - [ ] **Integration into OrderManager:**
     - [ ] Called in submit_order() BEFORE risk check
     - [ ] If should_block: Blocks order, sends alert
     - [ ] If should_warn: Logs warning, allows order, alerts operator
     - [ ] If OK: Proceeds normally
   - [ ] **Post-trade comparison:**
     - [ ] Called after order fills
     - [ ] Compares estimated to actual slippage
     - [ ] Stores estimation error for model improvement
   - [ ] **Weekly recalibration:**
     - [ ] Analyzes recent estimation errors
     - [ ] Adjusts multipliers based on systematic over/under-estimation
     - [ ] Logs adjustment reasons
   - [ ] Edge cases: Missing market data (use fallbacks), NaN/Infinity handling
   - Test: Known inputs → verify all components calculated correctly
   - Test: Estimation > 1.0% → order blocked
   - Test: Estimation 0.3-1.0% → order allowed but warned
   - Unit test: Estimation calculations
   - Unit test: Warn and block thresholds

3. **Task 4.4.2 - Fill Rate Tracker**
   - [ ] Tracks fill rates per order type:
     - [ ] MARKET, LIMIT, STOP_LOSS, TAKE_PROFIT, BRACKET
   - [ ] Metrics calculated:
     - [ ] Fill rate %: filled / total * 100
     - [ ] Cancellation rate %: cancelled / total * 100
     - [ ] Rejection rate %: rejected / total * 100
     - [ ] Average fill time (seconds)
   - [ ] Breakdowns available:
     - [ ] By order type
     - [ ] By symbol
   - [ ] Methods: `track_order_fill()`, `track_order_cancellation()`, `track_order_rejection()`
   - Unit test: Fill rate calculation with known order counts

4. **Task 4.4.3 - Execution Report Generator**
   - [ ] Generates comprehensive ExecutionReport
   - [ ] Report includes:
     - [ ] Period (start_date, end_date)
     - [ ] Order metrics (total, filled, cancelled, rejected, fill_rate_pct)
     - [ ] Slippage metrics (average, best, worst, by-symbol)
     - [ ] Timing metrics (average/min/max fill time)
     - [ ] Breakdown by order type
     - [ ] Breakdown by symbol
     - [ ] Recommendations (symbols with high slippage, low fill rates)
   - [ ] Date range filtering works
   - [ ] Exportable format (JSON at minimum)
   - Unit test: Report generation with sample data

5. **Task 4.4.4 - Execution Quality API**
   - [ ] `GET /api/execution/stats` - Current execution statistics
     - Response: fill_rate_pct, average_slippage, etc.
   - [ ] `GET /api/execution/slippage` - Slippage analysis
     - Query params: symbol (optional), period_days (optional)
     - Response: SlippageStats with by-symbol breakdown
   - [ ] `GET /api/execution/report` - Full execution report
     - Query params: start_date, end_date (ISO format)
     - Response: ExecutionReport (detailed metrics and recommendations)
   - [ ] All endpoints return proper HTTP status codes
   - [ ] Error handling: 400 (bad request), 422 (invalid params), 500 (error)
   - Integration test: Full API workflow

6. **Task 4.4.5 - Execution Quality Tests**
   - [ ] All metrics tested (slippage, fill rate, estimation)
   - [ ] Edge cases covered (NaN, division by zero, zero volumes)
   - [ ] Report generation tested
   - [ ] API endpoints tested
   - [ ] >85% code coverage

**VALIDATION RESULT:**
- [ ] ✅ All execution quality features PASS → Continue to Stage 4
- [ ] ❌ Any feature FAILS → Document, fix code, re-test

---

### STAGE 4: Integration Testing (30 minutes)

**Test that Session 4B components integrate correctly with Session 4A**

**Critical Integration Points:**

1. **OrderManager → PositionTracker Integration**
   - [ ] OrderManager calls `position_tracker.open_position()` on fill
   - [ ] OrderManager calls `position_tracker.update_position()` for adds/closes
   - [ ] Position created with correct entry price and quantity
   - [ ] Position updated with correct average entry (on add)
   - [ ] Position closed with correct final P&L (on full close)
   - Test scenario: Submit BUY → fill → position opens → verify position in tracker

2. **OrderManager → SlippageEstimator Integration**
   - [ ] SlippageEstimator called before order submission
   - [ ] Blocks order if estimated slippage > 1.0%
   - [ ] Warns if estimated slippage 0.3-1.0%
   - [ ] Allows order if estimated slippage < 0.3%
   - Test scenario: Submit large order → slippage estimate calculated → action taken

3. **Fill Handler → P&L Calculator**
   - [ ] When position closes: P&L calculated and stored
   - [ ] Realized P&L formula correct (tested in Stage 2)
   - [ ] Commission included in calculation
   - Test scenario: Close position → verify realized P&L in database

4. **PositionTracker → SlippageTracker**
   - [ ] After fill: SlippageTracker records slippage
   - [ ] SlippageTracker uses actual_price from fill
   - [ ] Estimated slippage (from Stage 3) stored for comparison
   - Test scenario: Order fills → slippage recorded → verification in SlippageTracker

5. **Full Workflow: Order → Position → P&L → Reports**
   ```
   1. Submit order (with slippage estimate)
   2. Order fills (actual slippage recorded)
   3. Position opens/updates (tracked in PositionTracker)
   4. Position closes (realized P&L calculated)
   5. Reports generated (ExecutionReport includes all metrics)
   ```
   - Test on testnet: Market BUY → fill → position opens → market SELL → fill → position closes → verify P&L → generate report

6. **Staleness Monitor → Alert System (Phase 5 dependency)**
   - [ ] Staleness check runs every hour
   - [ ] Alerts triggered on warning/review/max_hold
   - [ ] Position override prevents alerts
   - Test scenario: Hold position for 25 hours (day trading) → warning alert triggered

**INTEGRATION RESULT:**
- [ ] ✅ All integration tests PASS → Continue to Stage 5
- [ ] ❌ Any integration test FAILS → Document, fix code, re-test

---

### STAGE 5: Financial Calculations Audit (20 minutes)

**Verify all financial calculations are precise and auditable**

**P&L Calculation Precision:**

Test with known values:
```python
# Test Case 1: Long position
entry_price = 45000.0
current_price = 46000.0
quantity = 1.0
commission = 10.0

unrealized_pnl = (46000 - 45000) * 1.0 - 10 = 990
return_pct = (990 / (45000 * 1.0)) * 100 = 2.20%

# VERIFY: Both values calculated correctly
```

- [ ] Manual test cases with known values match calculated values
- [ ] Calculations match to 0.01% precision (4 decimal places minimum)
- [ ] Commission correctly subtracted from P&L
- [ ] Return % calculation uses correct entry price (not average)
- [ ] Short positions calculated correctly (entry - current instead of current - entry)

**Average Entry Calculation:**

```python
# Test Case: Add to position
old_qty = 1.0, old_avg = 45000
new_qty = 0.5, new_price = 46000
new_avg = (1.0 * 45000 + 0.5 * 46000) / (1.0 + 0.5) = 45333.33

# VERIFY: Matches expected value
```

- [ ] Average entry calculated correctly
- [ ] Precision: 0.01% or better
- [ ] Works for both adding and averaging down

**Realized P&L Calculation:**

```python
# Test Case: Partial close
entry_price = 45000
exit_price = 46000
quantity = 0.5
commission = 5

realized_pnl = (46000 - 45000) * 0.5 - 5 = 495

# VERIFY: Matches expected value
```

- [ ] Realized P&L for partial close correct
- [ ] Realized P&L for full close correct
- [ ] Commission correctly included

**Slippage Calculation:**

```python
# Test Case: Market BUY
expected = 45000
actual = 45050
slippage_pct = ((45050 - 45000) / 45000) * 100 = 0.1111%
slippage_bps = 11.11

# VERIFY: Both values match
```

- [ ] Slippage % calculated correctly
- [ ] Basis points (slippage_pct * 100) correct
- [ ] BUY vs SELL formulas correct

**AUDIT RESULT:**
- [ ] ✅ All calculations precise and correct → Continue to Stage 6
- [ ] ❌ Any calculation incorrect → Fix code, re-verify

---

### STAGE 6: Code Quality Audit (15 minutes)

**Manual inspection of code quality standards**

**Type Hints (100% Required):**
```bash
grep -rn "def.*):$" src/core/execution/position_tracker.py src/core/execution/quality.py
# Result: MUST show 0 matches

grep -rn "def.*:$" src/core/execution/ | grep -v " -> "
# Result: MUST show 0 matches
```

- [ ] Every function has parameter types and return type
- [ ] All dataclasses use `@dataclass` decorator
- [ ] Optional fields use `Optional[T]`
- [ ] Collection fields use `List[T]`, `Dict[K, V]`
- [ ] No bare `Any` without justification

**Naming Consistency:**
- [ ] Position fields: entry_price, current_price, unrealized_pnl (consistent)
- [ ] Slippage fields: slippage_pct, slippage_bps (consistent)
- [ ] No synonyms: "position" vs "pos", "pnl" vs "profit", etc.

**Financial Value Validation:**
```bash
grep -n "validate\|isnan\|isinf" src/core/execution/position_tracker.py src/core/execution/quality.py
# Should find validation decorators for all numeric fields
```

- [ ] All numeric fields validated for NaN/Infinity
- [ ] All prices validated for negative values
- [ ] All quantities validated for negative values
- [ ] All percentages clamped to valid ranges (0-100 for return %)

**Error Handling:**
- [ ] Try-except around all market data calls
- [ ] Try-except around all database operations
- [ ] Specific exceptions caught (not bare `except:`)
- [ ] All errors logged with context

**Structured Logging:**
```bash
grep -n "logger\." src/core/execution/ | head -20
# Should see: logger.info("event_name", field=value, ...)
```

- [ ] All logging uses structured format
- [ ] Event names descriptive (e.g., "position_opened", "pnl_calculated")
- [ ] All relevant fields included in log context
- [ ] No f-strings in log messages

**AUDIT RESULT:**
- [ ] ✅ All standards MET → Continue to Stage 7
- [ ] ❌ Issues found → List them, fix code, re-verify

---

### STAGE 7: Decision Consistency Check (10 minutes)

**Verify implementation follows all architectural decisions**

**Decision Verification:**
- [ ] Type hints 100% complete (DEC-2026-02-08-006)
- [ ] Timezone-aware timestamps used throughout (DEC-2026-02-08-003)
- [ ] Input validation comprehensive on all financials (DEC-2026-02-08-007)
- [ ] Structured logging with event names (DEC-2026-02-08-008)
- [ ] SQLAlchemy 2.0 patterns used (DEC-2026-02-08-002)
- [ ] No locked decisions violated

**DECISION RESULT:**
- [ ] ✅ All decisions followed → Continue to Stage 8
- [ ] ❌ Violations found → Fix code

---

### STAGE 8: Performance Validation (15 minutes)

**Verify Session 4B meets performance targets**

Test with realistic data (100 positions, 1000 historical trades):

```python
import time

# Scenario 1: Calculate unrealized P&L for 100 positions
start = time.time()
for position in positions:
    pnl = position_tracker.calculate_unrealized_pnl(position.symbol, current_prices[position.symbol])
elapsed = time.time() - start
assert elapsed < 2, f"P&L calc for 100 positions took {elapsed}s, target <2s"

# Scenario 2: Generate execution report (1000 orders)
start = time.time()
report = execution_report.generate_report(start_date, end_date)
elapsed = time.time() - start
assert elapsed < 5, f"Report generation took {elapsed}s, target <5s"

# Scenario 3: Position staleness check (100 positions)
start = time.time()
for position in positions:
    result = staleness_monitor.check_staleness(position)
elapsed = time.time() - start
assert elapsed < 3, f"Staleness check for 100 positions took {elapsed}s, target <3s"

# Scenario 4: API response (list 100 positions)
start = time.time()
response = await api.get_positions()
elapsed = time.time() - start
assert elapsed < 1, f"API response took {elapsed}s, target <1s"
```

**Performance Checklist:**
- [ ] P&L calculation (100 positions): < 2 seconds
- [ ] Report generation (1000 orders): < 5 seconds
- [ ] Staleness check (100 positions): < 3 seconds
- [ ] Slippage estimation: < 500ms per order
- [ ] API response (list positions): < 1 second
- [ ] Position sync (100 positions): < 2 seconds

**PERFORMANCE RESULT:**
- [ ] ✅ All targets MET → Continue to Stage 9
- [ ] ❌ Any target MISSED → Optimize code, re-test

---

### STAGE 9: Final Sign-Off (10 minutes)

**Complete final verification and sign-off**

**Final Checklist:**
- [ ] Stage 1: Automated gates - ALL PASS
- [ ] Stage 2: Position tracker - ALL FEATURES PASS
- [ ] Stage 3: Execution quality - ALL FEATURES PASS
- [ ] Stage 4: Integration - ALL TESTS PASS
- [ ] Stage 5: Financial audit - ALL CALCULATIONS CORRECT
- [ ] Stage 6: Code quality - ALL STANDARDS MET
- [ ] Stage 7: Decisions - ALL CONSISTENT
- [ ] Stage 8: Performance - ALL TARGETS MET

**Coverage Summary:**
```
src/core/execution/position_tracker.py        >90%  ✅
src/core/execution/quality.py                 >90%  ✅
src/api/routes/positions.py                   >90%  ✅
src/api/routes/execution.py                   >90%  ✅
TOTAL                                         >90%  ✅
```

**Production Audit Grade:** A- or higher ✅

**Complete Workflow Test (Executed on Testnet):**
- [ ] Submit market BUY → fills → position opens
- [ ] Market price updates → unrealized P&L calculated
- [ ] Position held 25 hours → staleness warning sent
- [ ] Submit market SELL → fills → position closes
- [ ] Realized P&L calculated and stored
- [ ] Slippage tracked for both fills
- [ ] Execution report generated and verified
- [ ] All API endpoints responding correctly

**PRD Compliance (Phase 4):**
- [ ] Feature F: Pre-trade slippage estimation (all components working)
- [ ] Feature K: Position staleness monitor (all thresholds working)

**Integration with Phase 3 (Risk Controls):**
- [ ] Risk controller checks run before order submission
- [ ] Kill switch can stop order submission (tested)
- [ ] Circuit breakers work with execution metrics

**Final Status:**
```
[✅] Type Safety: PASS (mypy --strict)
[✅] Code Quality: PASS (ruff, isort)
[✅] Tests: PASS (all pass, >90% coverage)
[✅] Position Tracker: PASS (all features working)
[✅] Execution Quality: PASS (all metrics accurate)
[✅] Financial Calculations: PASS (precision verified)
[✅] Integration: PASS (Session 4A compatible)
[✅] Performance: PASS (all targets met)
[✅] Decisions: PASS (all consistent)
[✅] Production Audit: PASS (Grade A-)

OVERALL: ✅ PRODUCTION READY - Phase 4 Complete
```

---

## 🔧 DEBUGGING GUIDE: P&L & Position Issues

### **Issue: P&L Calculations Don't Match Manual Calculations**

**Symptoms:**
```
Expected unrealized P&L: $495, got $500
Return % calculation off by 0.1%
Commission not being subtracted
```

**Root Causes & Solutions:**

| Issue | Cause | Solution |
|-------|-------|----------|
| Wrong by commission | Commission not subtracted | Ensure: `pnl = price_diff * qty - commission` |
| Off by rounding | Floating point precision | Use ±0.01 tolerance in assertions, not exact equality |
| Wrong for SHORT | Using LONG formula | Check: `if side == "SHORT": pnl = (entry - current) * qty` |
| Return % wrong | Using wrong denominator | Denominator must be `entry_price * quantity`, not just quantity |

**Debugging P&L Calculations:**

```python
# Test case: Calculate unrealized P&L step-by-step

entry_price = 45000.0
current_price = 46000.0
quantity = 0.5
commission_paid = 5.0

# Manual calculation
price_diff = current_price - entry_price
print(f"Price difference: {price_diff}")  # Should be 1000
print(f"Quantity: {quantity}")            # Should be 0.5

raw_pnl = price_diff * quantity
print(f"Raw P&L (before commission): {raw_pnl}")  # Should be 500

unrealized_pnl = raw_pnl - commission_paid
print(f"Unrealized P&L (after commission): {unrealized_pnl}")  # Should be 495

# Expected: 495
# If you get 500: commission not being subtracted
# If you get 490: commission subtracted twice

# Return % calculation
investment = entry_price * quantity
print(f"Investment: {investment}")  # Should be 22500

return_pct = (unrealized_pnl / investment) * 100
print(f"Return %: {return_pct}")  # Should be 2.20

# If off: verify investment calculation
# Wrong: return_pct = (unrealized_pnl / quantity) * 100  (wrong denominator)
# Wrong: return_pct = (unrealized_pnl / entry_price) * 100  (missing quantity)
# Right: return_pct = (unrealized_pnl / (entry_price * quantity)) * 100
```

---

### **Issue: Average Entry Price Calculation Wrong**

**Symptoms:**
```
Expected average: $44,500, got $44,750
Position average price drifts after adding to position
```

**Root Cause:** Average entry formula error

```python
# WRONG formula (common mistake)
new_avg = (old_avg + new_price) / 2  # WRONG - treats quantities equally

# CORRECT formula (must weight by quantity)
new_avg = (old_qty * old_avg + new_qty * new_price) / (old_qty + new_qty)

# Example - shows why weighting matters:
old_qty = 0.5, old_avg = 45000
new_qty = 0.5, new_price = 44000

# Wrong: (45000 + 44000) / 2 = 44500  (WRONG - happens to work here)
# Right: (0.5*45000 + 0.5*44000) / 1.0 = 44500  (coincidentally same)

# But with different quantities:
old_qty = 1.0, old_avg = 45000
new_qty = 0.5, new_price = 44000

# Wrong: (45000 + 44000) / 2 = 44500  (WRONG - treats them equally)
# Right: (1.0*45000 + 0.5*44000) / 1.5 = (45000+22000)/1.5 = 44666.67  (correct weighting)
```

**Fix:**
```python
def calculate_average_entry(
    old_qty: float,
    old_avg: float,
    new_qty: float,
    new_price: float
) -> float:
    """MUST weight by quantity."""
    total_cost = (old_qty * old_avg) + (new_qty * new_price)
    total_qty = old_qty + new_qty
    return total_cost / total_qty  # Weighted average
```

---

### **Issue: Position Staleness Monitor Not Triggering**

**Symptoms:**
```
Position held 25 hours, no warning alert sent
Strategy type not recognized
Profitable position extension not working
```

**Root Causes & Solutions:**

| Issue | Cause | Solution |
|-------|-------|----------|
| No alert | Threshold comparison wrong | Check: `if hold_duration > warning_hours` (not >=) |
| Wrong strategy type | Strategy lookup failing | Verify PositionStalenessMonitor gets correct strategy_id |
| Extension not applied | Profitable check wrong | Check: `if position.unrealized_pnl > 0: extend thresholds by 1.5x` |

**Debugging Staleness:**

```python
async def test_position_staleness():
    # Setup position held for 25 hours
    now = datetime.now(timezone.utc)
    position = Position(
        id="pos-1",
        symbol="BTCUSDT",
        side="BUY",
        opened_at=now - timedelta(hours=25),  # 25 hours ago
        entry_price=45000,
        quantity=0.5,
        unrealized_pnl=100,  # Profitable
        strategy_id="day_trading"
    )

    staleness_monitor = PositionStalenessMonitor(...)
    result = await staleness_monitor.check_staleness(position)

    # Expected thresholds for day trading:
    # - warning: 24 hours
    # - force_review: 48 hours
    # - max_hold: 72 hours
    # Since profitable, multiply by 1.5:
    # - warning: 36 hours
    # - force_review: 72 hours
    # - max_hold: 108 hours

    print(f"Hold duration: {result.hold_duration}")  # 25 hours
    print(f"Should warn: {result.should_warn}")  # False (25h < 36h threshold)

    # Change to 37 hours
    position.opened_at = now - timedelta(hours=37)
    result = await staleness_monitor.check_staleness(position)
    print(f"Should warn: {result.should_warn}")  # True (37h > 36h threshold)
```

---

### **Issue: Position Sync Detects Wrong Discrepancies**

**Symptoms:**
```
Says position discrepancy of 0.001 BTC when there's none
Discrepancy detection too sensitive
Wrong balance comparison
```

**Root Cause:** Floating point precision or rounding

```python
# WRONG - exact equality (floating point precision issue)
if local_qty == exchange_balance:
    # May fail due to rounding: 0.123456 != 0.12345600000000001

# RIGHT - use tolerance
TOLERANCE = 1e-8  # 0.00000001 BTC
if abs(local_qty - exchange_balance) < TOLERANCE:
    # This allows for floating point rounding errors
```

**Fix:**
```python
def positions_match(local_qty: float, exchange_qty: float, tolerance: float = 1e-8) -> bool:
    """Check if quantities match within tolerance."""
    return abs(local_qty - exchange_qty) < tolerance
```

---

### **Issue: Slippage Estimation Always Blocks Orders**

**Symptoms:**
```
All orders blocked: "Estimated slippage > 1.0%"
Estimation too conservative
Orders never reach exchange
```

**Root Cause:** Estimation formula too aggressive

```python
# Estimation components:
base = 0.05%
size_factor = (order_size / avg_daily_volume) * 0.5%
volatility_factor = (current_ATR / avg_ATR) * 0.1%
spread_factor = spread / 2

# Example - large order:
# If order is 50% of daily volume:
#   size_factor = 0.5 * 0.5% = 0.25%
# Plus base 0.05% = 0.30%
# Plus volatility ~0.1% = 0.40%
# Plus spread ~0.1% = 0.50%
# Total = 0.90% (just under 1.0% block threshold)

# If volatility spikes:
# Volatility factor could add another 0.3%
# Total = 1.20% → BLOCKED

# Check which component is too large:
print(f"Base: {base}")
print(f"Size factor: {size_factor}")  # Likely culprit for large orders
print(f"Volatility: {volatility}")     # Check if ATR multiplier too high
print(f"Spread: {spread}")
print(f"Total: {total}")

# If size_factor is problem: order is too large for current volume
# If volatility is problem: market too volatile, wait for calmer conditions
# If spread is problem: bad venue or bad symbol choice
```

---

## FAILURE PROTOCOL

If ANY stage fails:

1. **Document the failure:**
   - Stage number
   - Specific failure (test name, calculation error, missing feature)
   - Error message or calculation discrepancy
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
   - What was fixed
   - Why it failed
   - Prevention for future

**Only mark as PASS when ALL stages pass without issue.**

---

## DELIVERABLES

After successful verification:

1. **Verification Report** (this document completed with all checkboxes)
2. **Code ready for Phase 5**
3. **Test coverage report** (>90%)
4. **Performance report** (all targets met)
5. **Financial calculations audit** (all verified precise)
6. **Phase 4 completion summary**

---

## ESTIMATED TIME

- Stage 1 (Automated): 30 min
- Stage 2 (Position Tracker): 35 min
- Stage 3 (Execution Quality): 35 min
- Stage 4 (Integration): 30 min
- Stage 5 (Financial Audit): 20 min
- Stage 6 (Code Quality): 15 min
- Stage 7 (Decisions): 10 min
- Stage 8 (Performance): 15 min
- Stage 9 (Sign-Off): 10 min

**Total: ~2.5-3 hours**

---

## SUCCESS CRITERIA

**Session 4B is PRODUCTION READY when:**
- ✅ All 9 stages PASS
- ✅ mypy --strict: 0 errors
- ✅ ruff check: 0 violations
- ✅ pytest: 100% pass (all tests)
- ✅ Coverage: >90% per file, >90% total
- ✅ Positions open/close correctly
- ✅ P&L calculations accurate (verified with manual calculations)
- ✅ Slippage tracking and estimation working
- ✅ Position staleness monitoring working (PRD Feature K)
- ✅ All financial calculations verified to 4 decimal places
- ✅ Production audit: Grade A- or higher
- ✅ Ready for Phase 5 (Strategy Execution)

**If ALL checkpoints are ✅, sign off with:**
```
SESSION 4B: ✅ COMPLETE & PRODUCTION READY
PHASE 4: ✅ EXECUTION COMPLETE & PRODUCTION READY
Verified: [DATE]
Ready for: Phase 5 (Strategy Execution & Backtesting)
```

---

**Prompt Version:** 1.0
**Last Updated:** 2026-02-13
**Applies To:** Session 4B Verification (Sections 4.3 + 4.4)
