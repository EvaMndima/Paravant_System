# SESSION 3A VERIFICATION PROMPT
## Risk Controller & Kill Switch | Production Quality Verification & Sign-Off

**Role:** Production Quality Assurance Lead
**Task:** Verify Session 3A completion meets all production-grade quality standards
**Expected Duration:** 3-4 hours
**Result:** PASS or FAIL with detailed findings

---

## MANDATORY READING

1. `.claude/DECISIONS.md` (decision consistency)
2. `.claude/rules/zero-technical-debt.md` (quality standards)
3. `SESSION_3A_IMPLEMENTATION_PROMPT.md` (original requirements)
4. `docs/03_PHASE_3_RISK_CONTROLS.md` (Sections 3.1 + 3.2)
5. Phase 1/2 models (Account, Position, SystemState)

---

## VERIFICATION WORKFLOW

### STAGE 1: Automated Quality Gates (30 minutes)

**Execute these commands in order. ALL must pass with 0 errors/violations.**

```bash
# 1. Type Safety
mypy src/core/risk/controller.py src/core/risk/kill_switch.py src/core/risk/types.py --strict
# RESULT: Must show "Success: no issues found"

# 2. Code Linting
ruff check src/core/risk/
# RESULT: Must output nothing (0 violations)

# 3. Import Organization
isort src/core/risk/ --check --diff
# RESULT: Must show "All done! No files would be modified"

# 4. Test Execution
pytest tests/unit/test_risk_controller.py tests/unit/test_kill_switch.py -v --tb=short
# RESULT: Must show "passed" for ALL tests, no failures or errors

# 5. Coverage Report
pytest tests/unit/test_risk_controller.py tests/unit/test_kill_switch.py \
  --cov=src/core/risk --cov-report=term-missing | grep -E "^(src/|TOTAL)"
# RESULT: All files >90%, TOTAL >90%

# 6. Production Audit
@production-code-audit audit src/core/risk/controller.py src/core/risk/kill_switch.py
# RESULT: Must show Grade A- or higher, no CRITICAL or HIGH issues
```

**GATE RESULT:**
- [ ] ✅ All 6 gates PASS → Continue to Stage 2
- [ ] ❌ Any gate FAILS → Document failure, DO NOT proceed

---

### STAGE 2: Financial Correctness Validation (45 minutes)

**Verify risk calculations are mathematically correct**

#### 2.1 Position Size Check Validation

Create test scenarios and verify calculations:

```python
# Scenario 1: Position size within limit
account_equity = 10000  # $10,000
risk_profile = "balanced"  # 5% max
order_quantity = 0.5  # BTC
order_price = 50000  # $50,000
position_value = 0.5 * 50000 = $25,000
position_pct = (25000 / 10000) * 100 = 250%  # EXCEEDS 5% LIMIT

# Expected result: REJECTED
# Verify: Error message states max 5% for balanced profile

# Scenario 2: Position within limit
account_equity = 100000
risk_profile = "balanced"  # 5% max
max_allowed = 100000 * 0.05 = $5,000
order_quantity = 0.1  # BTC
order_price = 50000
position_value = 0.1 * 50000 = $5,000

# Expected result: APPROVED (exactly at limit)
# Verify: No error, order proceeds
```

**Checklist:**
- [ ] Conservative (2%), Balanced (5%), Aggressive (10%) correctly enforced
- [ ] Position size = quantity × price
- [ ] Percentage calculation: (position_value / equity) × 100
- [ ] Boundary conditions: exactly at limit (should PASS)
- [ ] Edge case: zero equity (should REJECT with error)

#### 2.2 Concentration Check Validation

```python
# Scenario: Existing + new position exceeds 30%
account_equity = 100000
existing_btc_position = 0.4 BTC @ $50000 = $20,000 (20%)
new_btc_order = 0.2 BTC @ $50000 = $10,000 (10%)
combined = $30,000 (30%)

# Expected: APPROVED (exactly at 30% limit)

# Scenario 2: Combined exceeds 30%
existing_btc_position = 0.4 BTC @ $50000 = $20,000 (20%)
new_btc_order = 0.25 BTC @ $50000 = $12,500 (12.5%)
combined = $32,500 (32.5%)

# Expected: REJECTED
# Verify: Remaining capacity message shows how much more can be added
```

**Checklist:**
- [ ] Considers existing position quantity + current price
- [ ] Calculates combined value correctly
- [ ] Enforces 30% default limit
- [ ] Returns remaining capacity info
- [ ] Handles case where existing position doesn't exist

#### 2.3 Position Sizing Calculator Validation

```python
# Fixed Risk Sizing: size = (equity × risk_pct) / (entry - stop)
account_equity = 10000
risk_pct = 0.01  # 1% per trade
entry_price = 50000
stop_loss = 49000
risk_per_unit = 50000 - 49000 = 1000
risk_amount = 10000 * 0.01 = $100
quantity = 100 / 1000 = 0.1 BTC

# Expected: quantity = 0.1
# Verify: Calculation returns 0.1 with notional_value = $5000

# ATR-Based Sizing: size = (equity × risk_pct) / (atr × multiplier)
atr = 500
atr_multiplier = 2.0
quantity = (10000 * 0.01) / (500 * 2.0) = 100 / 1000 = 0.1 BTC

# Verify both methods produce same result when ATR available
```

**Checklist:**
- [ ] Fixed risk sizing: size = (equity × risk_pct) / (entry - stop)
- [ ] Stop loss validation: BUY must have stop BELOW entry
- [ ] Stop loss validation: SELL must have stop ABOVE entry
- [ ] ATR-based sizing available when ATR exists
- [ ] Result respects max position size limit
- [ ] Notional value calculated correctly
- [ ] Risk amount = equity × risk_pct

#### 2.4 Capital Allocation Rules Validation

```python
# Portfolio state
total_equity = 100000

# Minimum cash reserve
required_reserve = 100000 * 0.20 = $20000
emergency_buffer = 100000 * 0.10 = $10000
total_reserved = $30000

# Available for new positions
cash_balance = 50000
available_capital = 50000 - 30000 = $20000

# Expected: available_capital = 20000

# Strategy allocation
new_strategy_max = 5%  # $5000
proven_strategy_max = 15%  # $15000

# New strategy requesting 6% ($6000)
# Expected: REJECTED (exceeds 5% limit)

# Proven strategy requesting 15% ($15000)
# Expected: APPROVED (within 15% limit)
```

**Checklist:**
- [ ] 20% minimum cash reserve enforced
- [ ] 10% emergency buffer enforced
- [ ] Available capital = cash - reserves
- [ ] New strategy capped at 5%
- [ ] Proven strategy capped at 15%
- [ ] Graduation: 30+ days profitable + 20+ trades
- [ ] Graduation increases allocation by 5%

#### 2.5 Kill Switch State Validation

```python
# Scenario 1: Activation is immediate
start_time = now
await kill_switch.activate("test")
end_time = now
duration = end_time - start_time

# Expected: duration < 1ms (1 second max per spec)
# Verify: Activation timestamp recorded
# Verify: is_active() returns True immediately

# Scenario 2: State persistence
await kill_switch.activate("test_reason")
# (Simulate restart)
new_switch = KillSwitch(data_store)
await new_switch.load_state()

# Expected: new_switch.is_active() = True
# Expected: new_switch._reason = "test_reason"
# Expected: Timestamp preserved
```

**Checklist:**
- [ ] Activation completes in <1 second
- [ ] State persists to database
- [ ] Recovery on restart works
- [ ] Deactivation requires correct confirmation code
- [ ] Wrong code is rejected
- [ ] Status API returns correct state

---

### STAGE 3: Code Quality Audit (30 minutes)

**Manual inspection of code quality standards**

#### 3.1 Type Hints (100% Required)

```bash
# Search for missing type hints
grep -rn "def.*):$" src/core/risk/controller.py src/core/risk/kill_switch.py
# Result: Should show 0 matches (or only __init__, __post_init__)

# Verify parameter types
grep -rn "def.*\)" src/core/risk/ | grep -v " -> "
# Result: Should show 0 matches for public methods
```

**Checklist:**
- [ ] Every `def` has parameter types AND return type
- [ ] All class attributes typed (Mapped[T] or annotated)
- [ ] No bare `Any` without justification comment
- [ ] No implicit `Optional` (use `Optional[T]` explicitly)
- [ ] Financial fields typed as `float` (not `int`)
- [ ] Collections typed: `list[str]`, `dict[str, Any]`, not bare `list`

#### 3.2 Naming Consistency (Zero Synonyms)

Check consistent usage across all risk files:

```bash
# Check for naming consistency
grep -r "\.approved\b" src/core/risk/
grep -r "\.rejected\b" src/core/risk/
grep -r "\.triggered\b" src/core/risk/

# These terms should appear ONLY in their intended classes
# Do NOT use synonyms like: .approved_?, .failed, .breached, etc.
```

**Checklist:**
- [ ] All results use `.approved` (not `.success`, `.passed`, `.valid`)
- [ ] All rejections use `.rejection_reason` (not `.error`, `.message`)
- [ ] Circuit breakers use `.triggered` (not `.active`, `.fired`, `.breached`)
- [ ] All use `.reason` for explanations (not `.message`, `.description`)
- [ ] Consistent field naming across all data classes

#### 3.3 Input Validation

```bash
# Verify NaN/Infinity validation
grep -n "math.isnan\|math.isinf" src/core/risk/controller.py
# Should show validation for: price, quantity, equity values

# Example good validation
if order_request.price is None or math.isnan(order_request.price):
    raise ValueError("Order price cannot be NaN")
if math.isinf(order_request.price):
    raise ValueError("Order price cannot be Infinity")
```

**Checklist:**
- [ ] All numeric inputs checked for NaN
- [ ] All numeric inputs checked for Infinity
- [ ] All numeric inputs checked for negative values (where appropriate)
- [ ] All string inputs checked for empty strings
- [ ] All collection inputs checked for empty (where appropriate)
- [ ] ValueError raised with descriptive messages
- [ ] Validation happens BEFORE any calculations

#### 3.4 Imports (Strict Organization)

Open 3 random files and verify import order:

```python
# Correct pattern:
# 1. Standard library (asyncio, datetime, math, etc.)
# 2. Third-party (sqlalchemy, fastapi, etc.)
# 3. Local (src.*)
# 4. Blank lines between groups
# 5. Alphabetized within groups

# Example from src/core/risk/controller.py:
import asyncio
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

from src.core.risk.types import OrderRequest, PortfolioState
from src.core.risk.kill_switch import KillSwitch
from src.data.store import DataStore
```

**Checklist:**
- [ ] Import order correct in all files
- [ ] No wildcard imports (`from X import *`)
- [ ] No unused imports
- [ ] No circular imports
- [ ] Blank lines between import groups
- [ ] Alphabetized within groups

#### 3.5 Documentation

**Check random methods:**

```python
# Example from RiskController.check_order():
async def check_order(self, order_request: OrderRequest) -> RiskCheckResult:
    """
    Master entry point - run all risk checks on an order.

    Pipeline order (STRICT - DO NOT CHANGE):
    1. Kill switch check
    2. Position size check
    3. Concentration check
    4. Max positions check

    Args:
        order_request: Order to validate

    Returns:
        RiskCheckResult with approval status

    Raises:
        ValueError: If order contains NaN, Infinity, or invalid values
    """
```

**Checklist:**
- [ ] Every class has docstring (purpose, usage)
- [ ] Every public method has docstring (args, returns, raises)
- [ ] Pipeline order documented in check_order()
- [ ] Complex formulas commented with source
- [ ] Edge cases documented (e.g., "Drawdown does NOT auto-reset")
- [ ] Important notes prefaced with ⚠️ or CRITICAL

---

### STAGE 4: Kill Switch Critical Functionality (20 minutes)

**Test kill switch behavior in detail**

#### 4.1 Activation & Immediate Effect

```python
# Test: Kill switch activation blocks orders
await kill_switch.activate("test")

# Create order request
order = OrderRequest(...)

# Try to validate order
result = await risk_controller.check_order(order)

# Expected: result.approved = False
# Expected: result.check_name = "kill_switch"
# Expected: "Kill switch is active" in rejection_reason
```

**Checklist:**
- [ ] Activation sets is_active() = True
- [ ] All subsequent check_order() calls return REJECTED
- [ ] Rejection reason is clear
- [ ] Timestamp recorded with timezone awareness

#### 4.2 State Persistence & Recovery

```python
# Simulate system restart with active kill switch
await kill_switch.activate("critical_loss")
# ... system crashes ...
# ... restart ...

# Load state on startup
kill_switch_new = KillSwitch(data_store)
await kill_switch_new.load_state()

# Expected: kill_switch_new.is_active() = True
# Expected: Reason preserved: "critical_loss"
# Expected: Timestamp preserved
```

**Checklist:**
- [ ] State saved to database on activation
- [ ] load_state() correctly restores active state
- [ ] load_state() correctly restores inactive state
- [ ] Timestamp persisted as timezone-aware datetime
- [ ] Multiple restarts preserve state correctly

#### 4.3 Deactivation Security

```python
# Correct code deactivation
success = await kill_switch.deactivate("RESTART_TRADING_SYSTEM")
# Expected: success = True, is_active() = False

# Wrong code
success = await kill_switch.deactivate("wrong_code")
# Expected: success = False, is_active() = True (still active)

# Case-sensitive test
success = await kill_switch.deactivate("restart_trading_system")  # lowercase
# Expected: success = False (code is case-sensitive)
```

**Checklist:**
- [ ] Correct code deactivates immediately
- [ ] Wrong code is rejected
- [ ] Code is case-sensitive
- [ ] Deactivation logs audit event
- [ ] Cannot deactivate twice (idempotent)

#### 4.4 Kill Switch Triggers

Test auto-activation conditions:

```python
# Daily loss trigger test
portfolio.daily_pnl = -800  # 8% loss when 5% limit

reason = await kill_switch.check_triggers(portfolio)
# Expected: reason contains "Daily loss 8%"
# Expected: reason contains "exceeds limit 5%"

# Drawdown trigger test
portfolio.drawdown_pct = 20.0  # 20% when 15% limit

reason = await kill_switch.check_triggers(portfolio)
# Expected: reason contains "Drawdown 20%"

# Consecutive losses trigger test
portfolio.consecutive_losses = 12  # 12 when limit is 10

reason = await kill_switch.check_triggers(portfolio)
# Expected: reason contains "12 consecutive losses"
```

**Checklist:**
- [ ] Daily loss threshold (5%) triggers correctly
- [ ] Drawdown threshold (15%) triggers correctly
- [ ] Consecutive losses threshold (10) triggers correctly
- [ ] All thresholds are configurable
- [ ] check_triggers() returns reason string

---

### STAGE 5: Integration Testing (30 minutes)

**Verify Session 3A integrates correctly with Phase 1/2**

#### 5.1 Order Validation Pipeline Integration

```python
# Create sample order request
order = OrderRequest(
    account_id="ACC001",
    strategy_id="STRAT001",
    symbol="BTCUSDT",
    side="buy",
    quantity=0.5,
    price=50000,
    order_type="market",
    reason="trend_signal"
)

# Create realistic portfolio state
portfolio = PortfolioState(
    account_id="ACC001",
    total_equity=100000,
    cash_balance=50000,
    positions_value=50000,
    open_positions=[...],  # Real positions
    daily_pnl=-500,  # 0.5% daily loss
    weekly_pnl=-2000,  # 2% weekly loss
    drawdown_pct=3.0,  # 3% drawdown
    peak_equity=103000,
    consecutive_losses=1
)

# Run through full pipeline
result = await risk_controller.check_order(order)

# Expected: result.approved = True (all checks pass)
# Expected: result.checks_passed = ["kill_switch", "position_size", ...]
```

**Checklist:**
- [ ] Order passing all checks approved
- [ ] Order failing position size rejected (first)
- [ ] Order failing concentration rejected (at right point)
- [ ] Kill switch check runs first (fastest rejection)
- [ ] Pipeline order is correct (cannot reorder)
- [ ] No breaking changes to Phase 1 models

#### 5.2 Account & Portfolio Integration

```python
# Test with real Account model from Phase 1
account = await data_store.get_account("ACC001")

# Get portfolio state
portfolio = await risk_controller._get_portfolio_state("ACC001")

# Verify types match
assert isinstance(portfolio, PortfolioState)
assert portfolio.total_equity > 0
assert portfolio.cash_balance >= 0
assert portfolio.positions_value >= 0
```

**Checklist:**
- [ ] Works with Phase 1 Account model
- [ ] Works with Phase 1 Position model
- [ ] Works with Phase 1 Order model
- [ ] DataStore integration works
- [ ] No schema changes required

#### 5.3 Decision Consistency

```bash
# Verify all decisions are documented
grep -r "Decision:" src/core/risk/ | head -10
# Should show decision references (DEC-2026-02-08-XXX)

# Verify no decisions violated
# Check: Type hints 100%? Yes
# Check: Input validation comprehensive? Yes
# Check: Timezone-aware datetimes? Yes (for kill switch)
# Check: Structured logging? Check logs
```

**Checklist:**
- [ ] Type hints 100% complete (DEC-2026-02-08-006)
- [ ] Timezone-aware timestamps (DEC-2026-02-08-003)
- [ ] Input validation comprehensive (DEC-2026-02-08-007)
- [ ] Structured logging used (DEC-2026-02-08-008)
- [ ] All decisions referenced in `.claude/DECISIONS.md`

---

### STAGE 6: Edge Case Validation (20 minutes)

**Verify all indicators handle edge cases gracefully**

#### 6.1 Insufficient/Invalid Portfolio Data

```python
# Edge case: Zero equity
portfolio = PortfolioState(total_equity=0, ...)
# Expected: ValueError raised with clear message

# Edge case: Negative equity (liquidation)
portfolio = PortfolioState(total_equity=-1000, ...)
# Expected: ValueError raised

# Edge case: NaN in calculations
portfolio = PortfolioState(total_equity=float('nan'), ...)
# Expected: ValueError raised in __post_init__
```

**Checklist:**
- [ ] Zero equity rejected
- [ ] Negative equity rejected
- [ ] NaN in equity rejected
- [ ] Infinity in equity rejected
- [ ] Mismatched equity (cash + positions != total) rejected

#### 6.2 Boundary Condition Testing

```python
# Position size exactly at limit
position_pct = 5.0  # Exactly 5% limit
# Expected: APPROVED (not rejected)

# Position size 0.0001% over limit
position_pct = 5.0001  # Just over 5%
# Expected: REJECTED

# Concentration exactly at 30%
concentration_pct = 30.0
# Expected: APPROVED

# Drawdown exactly at 15% threshold
drawdown_pct = 15.0
# Expected: TRIGGERED
```

**Checklist:**
- [ ] Exactly at threshold: PASS (not fail)
- [ ] Just over threshold: FAIL
- [ ] Just under threshold: PASS
- [ ] Zero values handled correctly
- [ ] Very large values rejected appropriately

#### 6.3 Kill Switch Edge Cases

```python
# Multiple activations (should be idempotent)
await kill_switch.activate("reason1")
await kill_switch.activate("reason2")
# Expected: Only first activation recorded, second ignored

# Deactivate when not active
success = await kill_switch.deactivate("code")
# Expected: success = True (idempotent, no error)

# Deactivate twice
await kill_switch.deactivate("code")
await kill_switch.deactivate("code")
# Expected: Second call returns success=True (or False, but consistent)
```

**Checklist:**
- [ ] Activation is idempotent
- [ ] Deactivation on inactive switch handled
- [ ] No errors from edge cases
- [ ] Behavior is predictable and consistent

---

### STAGE 7: Decision Consistency Check (15 minutes)

**Verify implementation follows all architectural decisions**

#### 7.1 Read Relevant Decisions

Check `.claude/DECISIONS.md` for:

```
DEC-2026-02-08-002: SQLAlchemy 2.0 with Mapped[T]
DEC-2026-02-08-003: Timezone-aware timestamps (utc)
DEC-2026-02-08-006: Type hints 100%
DEC-2026-02-08-007: Input validation at model layer
DEC-2026-02-08-008: Structured logging
DEC-2026-02-08-010: Lambda for mutable defaults
DEC-2026-02-08-015: Bidirectional relationships
```

#### 7.2 Verify Each Decision

**DEC-2026-02-08-006: Type Hints 100%**
- [ ] grep -r "def " src/core/risk/ | grep -v " -> " shows 0 matches
- [ ] All parameters have types
- [ ] All return types specified
- [ ] No bare `Any` without comment

**DEC-2026-02-08-003: Timezone-Aware Timestamps**
- [ ] All timestamps use `datetime.now(timezone.utc)`
- [ ] No `datetime.utcnow()` anywhere
- [ ] Kill switch timestamps timezone-aware
- [ ] No naive datetimes in database

**DEC-2026-02-08-007: Input Validation**
- [ ] All numeric fields validated for NaN
- [ ] All numeric fields validated for Infinity
- [ ] All inputs validated before use
- [ ] Validation errors raised with descriptive messages

**DEC-2026-02-08-008: Structured Logging**
- [ ] All logs use structured format
- [ ] Example: `logger.info("kill_switch_activated", extra={"reason": reason})`
- [ ] No string concatenation in log messages

**Checklist:**
- [ ] Type hints 100% complete
- [ ] Timezone-aware datetimes only
- [ ] Input validation comprehensive
- [ ] Structured logging used
- [ ] No decisions violated
- [ ] All decisions documented in code comments

---

### STAGE 8: Final Sign-Off (10 minutes)

**Complete final verification and sign-off**

#### 8.1 Final Checklist

```
CODE QUALITY:
- [ ] Stage 1: Automated gates - ALL PASS
- [ ] Stage 2: Financial correctness - VERIFIED
- [ ] Stage 3: Code quality - ALL STANDARDS MET
- [ ] Stage 4: Kill switch functionality - WORKING
- [ ] Stage 5: Integration - ALL TESTS PASS
- [ ] Stage 6: Edge cases - ALL HANDLED
- [ ] Stage 7: Decisions - ALL CONSISTENT

COVERAGE SUMMARY:
- [ ] src/core/risk/controller.py      >90%  ✅
- [ ] src/core/risk/types.py           >90%  ✅
- [ ] src/core/risk/kill_switch.py     >90%  ✅
- [ ] tests/unit/test_risk_controller.py >90%  ✅
- [ ] tests/unit/test_kill_switch.py   >90%  ✅
- [ ] TOTAL COVERAGE              >90%  ✅

CRITICAL FUNCTIONALITY:
- [ ] Kill switch activates <1 second
- [ ] Kill switch state persists across restarts
- [ ] Position sizing calculations correct
- [ ] Concentration limits enforced
- [ ] Capital allocation rules enforced
- [ ] No breaking changes to Phase 1/2
- [ ] All input validation working

PRODUCTION AUDIT:
- [ ] Grade A- or higher ✅
- [ ] No CRITICAL issues ✅
- [ ] No HIGH issues ✅
```

#### 8.2 Final Status

```
[✅] Type Safety: mypy --strict PASS (0 errors)
[✅] Code Quality: ruff check PASS (0 violations)
[✅] Imports: isort PASS (0 changes)
[✅] Tests: pytest PASS (all pass, 0 failures)
[✅] Coverage: PASS (>90% per file, >90% total)
[✅] Financial Correctness: VERIFIED (all calculations correct)
[✅] Kill Switch: VERIFIED (<1s activation, state persistence)
[✅] Integration: PASS (Phase 1/2 compatible)
[✅] Decisions: PASS (all consistent)
[✅] Production Audit: PASS (Grade A-)

OVERALL: ✅ PRODUCTION READY FOR SESSION 3B
```

#### 8.3 Sign-Off Statement

If ALL checkpoints are ✅, sign off with:

```
SESSION 3A: ✅ COMPLETE & PRODUCTION READY

Verified: [DATE]
Verified By: [ROLE/NAME]
Signature: ___________________________

Tests Passed: ALL
Coverage: >90% per file
Production Audit: Grade A-
Ready for: Session 3B (Circuit Breakers & Volatility)
```

---

## FAILURE PROTOCOL

If ANY stage fails:

1. **Document the failure:**
   - Stage number
   - Specific failure (test name, metric, etc.)
   - Error message
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

## ESTIMATED TIME

- Stage 1 (Automated): 30 min
- Stage 2 (Financial): 45 min
- Stage 3 (Code Quality): 30 min
- Stage 4 (Kill Switch): 20 min
- Stage 5 (Integration): 30 min
- Stage 6 (Edge Cases): 20 min
- Stage 7 (Decisions): 15 min
- Stage 8 (Sign-Off): 10 min

**Total: ~3.5 hours (can be 2.5 hours if everything passes first try)**

---

**Prompt Version:** 1.0
**Last Updated:** 2026-02-12
**Applies To:** Session 3A Verification (Sections 3.1 + 3.2)
**Next:** SESSION_3B_VERIFICATION_PROMPT.md
