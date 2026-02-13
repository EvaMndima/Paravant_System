# SESSION 3B VERIFICATION PROMPT
## Circuit Breakers & Volatility Filter | Production Quality Verification & Sign-Off

**Role:** Production Quality Assurance Lead
**Task:** Verify Session 3B completion meets all production-grade quality standards
**Expected Duration:** 3-4 hours
**Result:** PASS or FAIL with detailed findings

---

## MANDATORY READING

1. `.claude/DECISIONS.md` (decision consistency)
2. `.claude/rules/zero-technical-debt.md` (quality standards)
3. `SESSION_3B_IMPLEMENTATION_PROMPT.md` (original requirements)
4. `docs/03_PHASE_3_RISK_CONTROLS.md` (Sections 3.3 + 3.4)
5. Session 3A code (RiskController, PortfolioState)
6. Phase 2 indicators (ATR for volatility)

---

## VERIFICATION WORKFLOW

### STAGE 1: Automated Quality Gates (30 minutes)

**Execute these commands in order. ALL must pass with 0 errors/violations.**

```bash
# 1. Type Safety
mypy src/core/risk/circuit_breakers.py src/core/risk/volatility.py src/core/risk/time_filter.py src/core/risk/event_filter.py --strict
# RESULT: Must show "Success: no issues found"

# 2. Code Linting
ruff check src/core/risk/
# RESULT: Must output nothing (0 violations)

# 3. Import Organization
isort src/core/risk/ --check --diff
# RESULT: Must show "All done! No files would be modified"

# 4. Test Execution
pytest tests/unit/test_circuit_breakers.py tests/unit/test_volatility_filter.py -v --tb=short
# RESULT: Must show "passed" for ALL tests, no failures or errors

# 5. Coverage Report
pytest tests/unit/test_circuit_breakers.py tests/unit/test_volatility_filter.py \
  --cov=src/core/risk --cov-report=term-missing | grep -E "^(src/|TOTAL)"
# RESULT: All files >90%, TOTAL >90%

# 6. Production Audit
@production-code-audit audit src/core/risk/circuit_breakers.py src/core/risk/volatility.py
# RESULT: Must show Grade A- or higher, no CRITICAL or HIGH issues
```

**GATE RESULT:**
- [ ] ✅ All 6 gates PASS → Continue to Stage 2
- [ ] ❌ Any gate FAILS → Document failure, DO NOT proceed

---

### STAGE 2: Circuit Breaker Threshold Validation (45 minutes)

**Verify each breaker triggers at EXACTLY the right threshold**

#### 2.1 Daily Loss Breaker (5% limit, resets UTC 00:00)

Test scenarios:

```python
# Scenario 1: Below threshold (4.9%)
portfolio.total_equity = 10000
portfolio.daily_pnl = -490  # 4.9% loss

result = await daily_loss_breaker.check(portfolio)
# Expected: result.triggered = False
# Expected: result.current_value = 4.9
# Expected: result.threshold = 5.0

# Scenario 2: Exactly at threshold (5.0%)
portfolio.daily_pnl = -500  # 5.0% loss

result = await daily_loss_breaker.check(portfolio)
# Expected: result.triggered = True (triggered at or above threshold)
# Expected: result.current_value = 5.0

# Scenario 3: Above threshold (5.1%)
portfolio.daily_pnl = -510  # 5.1% loss

result = await daily_loss_breaker.check(portfolio)
# Expected: result.triggered = True

# Scenario 4: No loss (positive P&L)
portfolio.daily_pnl = +500  # +5% profit

result = await daily_loss_breaker.check(portfolio)
# Expected: result.triggered = False (no loss = no trigger)
```

**Checklist:**
- [ ] Below threshold: NOT triggered
- [ ] At threshold: TRIGGERED
- [ ] Above threshold: TRIGGERED
- [ ] Positive P&L: NOT triggered
- [ ] Threshold = 5.0% (configurable)
- [ ] Resets daily at UTC 00:00
- [ ] Auto-reset doesn't require manual call

#### 2.2 Weekly Loss Breaker (10% limit, resets Monday UTC 00:00)

Test scenarios:

```python
# Scenario 1: Below threshold (9.9% loss on Thursday)
portfolio.weekly_pnl = -990  # 9.9% loss
current_day = "Thursday"

result = await weekly_loss_breaker.check(portfolio)
# Expected: result.triggered = False

# Scenario 2: At threshold (10.0% loss on Friday)
portfolio.weekly_pnl = -1000  # 10.0% loss

result = await weekly_loss_breaker.check(portfolio)
# Expected: result.triggered = True

# Scenario 3: Above threshold (11% loss on Saturday)
portfolio.weekly_pnl = -1100  # 11% loss

result = await weekly_loss_breaker.check(portfolio)
# Expected: result.triggered = True

# Scenario 4: Resets on Monday
# Set as Saturday with triggered=True
# Move to Monday UTC 00:00
# Check again with reset

# Expected: triggered = False (new week, new counter)
```

**Checklist:**
- [ ] Below 10%: NOT triggered
- [ ] At 10%: TRIGGERED
- [ ] Above 10%: TRIGGERED
- [ ] Resets Monday at UTC 00:00 (not Sunday, not Tuesday)
- [ ] Uses UTC time (not local)
- [ ] New week = new counter

#### 2.3 Drawdown Breaker (15% limit, MANUAL RESET ONLY)

Test scenarios:

```python
# Scenario 1: Below threshold (14% drawdown)
portfolio.drawdown_pct = 14.0

result = await drawdown_breaker.check(portfolio)
# Expected: result.triggered = False

# Scenario 2: At threshold (15% drawdown)
portfolio.drawdown_pct = 15.0

result = await drawdown_breaker.check(portfolio)
# Expected: result.triggered = True

# Scenario 3: Above threshold (16% drawdown)
portfolio.drawdown_pct = 16.0

result = await drawdown_breaker.check(portfolio)
# Expected: result.triggered = True

# Scenario 4: DOES NOT auto-reset
# Set drawdown to 20% (triggered=True)
# Move to next day
# Check again without calling reset()

# Expected: result.triggered = True (STILL TRIGGERED)

# Scenario 5: Manual reset works
await drawdown_breaker.reset()
result = await drawdown_breaker.check(portfolio)
# Expected: triggered = False (after manual reset)
```

**Checklist:**
- [ ] Below 15%: NOT triggered
- [ ] At 15%: TRIGGERED
- [ ] Above 15%: TRIGGERED
- [ ] Does NOT auto-reset (critical)
- [ ] Manual reset() works
- [ ] Stays triggered across multiple checks until manually reset

#### 2.4 Consecutive Loss Breaker (5 limit, resets on winning trade)

Test scenarios:

```python
# Scenario 1: Below threshold (4 consecutive losses)
portfolio.consecutive_losses = 4

result = await consecutive_loss_breaker.check(portfolio)
# Expected: result.triggered = False

# Scenario 2: At threshold (5 consecutive losses)
portfolio.consecutive_losses = 5

result = await consecutive_loss_breaker.check(portfolio)
# Expected: result.triggered = True

# Scenario 3: Above threshold (7 consecutive losses)
portfolio.consecutive_losses = 7

result = await consecutive_loss_breaker.check(portfolio)
# Expected: result.triggered = True

# Scenario 4: Resets on winning trade
portfolio.consecutive_losses = 5  # Still triggered
portfolio.consecutive_losses = 0  # Win, reset to 0

result = await consecutive_loss_breaker.check(portfolio)
# Expected: result.triggered = False
```

**Checklist:**
- [ ] Below 5: NOT triggered
- [ ] At 5: TRIGGERED
- [ ] Above 5: TRIGGERED
- [ ] Resets automatically on winning trade
- [ ] Max consecutive losses = 5 (configurable)

#### 2.5 Correlation Breaker (40% BTC, 30% ETH, 60% group limit)

Test scenarios:

```python
# Scenario 1: BTC at 39% (below 40% limit)
btc_position_value = 39000
portfolio.total_equity = 100000
portfolio.open_positions = [Position(symbol="BTCUSDT", value=39000)]

result = await correlation_breaker.check(portfolio)
# Expected: result.triggered = False

# Scenario 2: BTC at 40% (exactly at limit)
btc_position_value = 40000

result = await correlation_breaker.check(portfolio)
# Expected: result.triggered = False (should allow exactly at limit)

# Scenario 3: BTC at 41% (exceeds limit)
btc_position_value = 41000

result = await correlation_breaker.check(portfolio)
# Expected: result.triggered = True
# Expected: "BTC" in reason

# Scenario 4: ETH at 30% (exactly at limit)
eth_position_value = 30000

result = await correlation_breaker.check(portfolio)
# Expected: result.triggered = False (at limit is OK)

# Scenario 5: ETH at 31% (exceeds limit)
eth_position_value = 31000

result = await correlation_breaker.check(portfolio)
# Expected: result.triggered = True

# Scenario 6: Layer1 group at 60% (SOL 20%, AVAX 20%, DOT 20%)
layer1_positions = {
    "SOLUSDT": 20000,
    "AVAXUSDT": 20000,
    "DOTUSDT": 20000
}
total_layer1 = 60000  # 60% of portfolio

result = await correlation_breaker.check(portfolio)
# Expected: result.triggered = False (exactly at group limit)

# Scenario 7: Layer1 group at 61%
total_layer1 = 61000  # 61% of portfolio

result = await correlation_breaker.check(portfolio)
# Expected: result.triggered = True
# Expected: "layer1" in reason
```

**Checklist:**
- [ ] BTC: 40% limit enforced (not 39%, not 41%)
- [ ] ETH: 30% limit enforced (not 29%, not 31%)
- [ ] Group limits: 60% enforced (all symbols in group summed)
- [ ] Individual limits checked first
- [ ] Group limits checked second
- [ ] Violations reported in reason
- [ ] Multiple violations possible (return all)

---

### STAGE 3: Volatility Regime Validation (40 minutes)

**Verify volatility classification and size adjustments**

#### 3.1 Volatility Ratio Calculation

```python
# Formula: ATR(14) / Close Price * 100

# Scenario 1: Low volatility (1.5%)
atr = 75
close_price = 5000
vol_pct = (75 / 5000) * 100 = 1.5%

result = await volatility_analyzer.get_volatility_ratio("BTCUSDT")
# Expected: result ≈ 1.5

# Scenario 2: Moderate volatility (4.0%)
atr = 200
close_price = 5000
vol_pct = (200 / 5000) * 100 = 4.0%

result = await volatility_analyzer.get_volatility_ratio("BTCUSDT")
# Expected: result ≈ 4.0

# Scenario 3: High volatility (6.0%)
atr = 300
close_price = 5000
vol_pct = (300 / 5000) * 100 = 6.0%

result = await volatility_analyzer.get_volatility_ratio("BTCUSDT")
# Expected: result ≈ 6.0
```

**Checklist:**
- [ ] Formula: ATR / Price * 100
- [ ] Returns percentage (0-100 range)
- [ ] Handles edge cases: zero price, None ATR
- [ ] Returns 0 on error (not NaN or Infinity)

#### 3.2 Volatility Regime Classification

Test the thresholds:

```python
# NORMAL regime: < 3%
vol_pct = 2.9  # Below threshold

regime = await volatility_analyzer.get_regime("BTCUSDT")
# Expected: regime = VolatilityRegime.NORMAL

# ELEVATED regime: 3% to 5%
vol_pct = 4.0  # Between thresholds

regime = await volatility_analyzer.get_regime("BTCUSDT")
# Expected: regime = VolatilityRegime.ELEVATED

# EXTREME regime: > 5%
vol_pct = 5.1  # Above threshold

regime = await volatility_analyzer.get_regime("BTCUSDT")
# Expected: regime = VolatilityRegime.EXTREME

# Boundary: exactly 3.0%
vol_pct = 3.0

regime = await volatility_analyzer.get_regime("BTCUSDT")
# Expected: regime = VolatilityRegime.ELEVATED (3% is in ELEVATED range)

# Boundary: exactly 5.0%
vol_pct = 5.0

regime = await volatility_analyzer.get_regime("BTCUSDT")
# Expected: regime = VolatilityRegime.EXTREME (5% triggers EXTREME)
```

**Checklist:**
- [ ] NORMAL: vol < 3.0%
- [ ] ELEVATED: 3.0% <= vol < 5.0%
- [ ] EXTREME: vol >= 5.0%
- [ ] Boundaries correct (no off-by-one errors)
- [ ] Thresholds are 3.0 and 5.0 (configurable)

#### 3.3 Position Size Adjustment

```python
# NORMAL regime → 1.0x multiplier
should_reduce, multiplier = await volatility_analyzer.should_reduce_size("BTCUSDT")
# If vol < 3%:
# Expected: should_reduce = False, multiplier = 1.0

# ELEVATED regime → 0.5x multiplier
should_reduce, multiplier = await volatility_analyzer.should_reduce_size("BTCUSDT")
# If vol between 3-5%:
# Expected: should_reduce = True, multiplier = 0.5

# EXTREME regime → 0.0x multiplier (no entries)
should_reduce, multiplier = await volatility_analyzer.should_reduce_size("BTCUSDT")
# If vol > 5%:
# Expected: should_reduce = True, multiplier = 0.0

# Example usage:
base_size = 1.0  # 1 BTC
adjusted_size = base_size * multiplier
# NORMAL: 1.0 BTC
# ELEVATED: 0.5 BTC
# EXTREME: 0.0 BTC (no trade)
```

**Checklist:**
- [ ] NORMAL: multiplier = 1.0
- [ ] ELEVATED: multiplier = 0.5 (50% reduction)
- [ ] EXTREME: multiplier = 0.0 (no entries)
- [ ] Adjustment integrates with RiskController.calculate_position_size()

#### 3.4 Entry Blocking (EXTREME volatility)

```python
# EXTREME regime blocks new entries for 4 hours

# Scenario 1: NORMAL volatility
can_enter, reason = await volatility_analyzer.can_enter("BTCUSDT")
# If vol < 3%:
# Expected: can_enter = True, reason = "OK"

# Scenario 2: ELEVATED volatility
can_enter, reason = await volatility_analyzer.can_enter("BTCUSDT")
# If vol between 3-5%:
# Expected: can_enter = True (ELEVATED allows entries with reduced size)

# Scenario 3: EXTREME volatility
can_enter, reason = await volatility_analyzer.can_enter("BTCUSDT")
# If vol > 5%:
# Expected: can_enter = False
# Expected: "Extreme volatility" in reason
# Expected: "exits only" in reason

# Scenario 4: Cooldown after EXTREME
# Set vol to EXTREME, call can_enter()
# Vol drops to NORMAL (< 3%)
# Call can_enter() immediately
# Expected: can_enter = False (still in 4-hour cooldown)

# After 4 hours pass:
# Expected: can_enter = True (cooldown expired)
```

**Checklist:**
- [ ] NORMAL: allows entries
- [ ] ELEVATED: allows entries with size reduction
- [ ] EXTREME: blocks entries (exits only)
- [ ] 4-hour cooldown enforced after EXTREME
- [ ] Cooldown timestamp tracked correctly

---

### STAGE 4: Time-Based Filter Validation (25 minutes)

**Verify weekend/holiday detection and adjustments**

#### 4.1 Weekend Detection (UTC only)

```python
# Saturday: weekday() = 5
# Sunday: weekday() = 6
# All times in UTC

# Scenario 1: Friday (not weekend)
now = datetime(2026, 2, 13, 23, 59, tzinfo=timezone.utc)  # Friday 23:59 UTC
is_weekend = filter.is_weekend()
# Expected: is_weekend = False

# Scenario 2: Saturday 00:00 UTC
now = datetime(2026, 2, 14, 0, 0, tzinfo=timezone.utc)  # Saturday 00:00 UTC
is_weekend = filter.is_weekend()
# Expected: is_weekend = True

# Scenario 3: Saturday 23:59 UTC
now = datetime(2026, 2, 14, 23, 59, tzinfo=timezone.utc)  # Saturday 23:59 UTC
is_weekend = filter.is_weekend()
# Expected: is_weekend = True

# Scenario 4: Sunday 00:00 UTC
now = datetime(2026, 2, 15, 0, 0, tzinfo=timezone.utc)  # Sunday 00:00 UTC
is_weekend = filter.is_weekend()
# Expected: is_weekend = True

# Scenario 5: Sunday 23:59 UTC
now = datetime(2026, 2, 15, 23, 59, tzinfo=timezone.utc)  # Sunday 23:59 UTC
is_weekend = filter.is_weekend()
# Expected: is_weekend = True

# Scenario 6: Monday 00:00 UTC
now = datetime(2026, 2, 16, 0, 0, tzinfo=timezone.utc)  # Monday 00:00 UTC
is_weekend = filter.is_weekend()
# Expected: is_weekend = False
```

**Checklist:**
- [ ] Friday is NOT weekend
- [ ] Saturday 00:00 IS weekend
- [ ] Saturday 23:59 IS weekend
- [ ] Sunday 00:00 IS weekend
- [ ] Sunday 23:59 IS weekend
- [ ] Monday 00:00 is NOT weekend
- [ ] Uses UTC time (not local)

#### 4.2 Holiday Detection

```python
# Fixed holidays: Dec 24, 25, 26 (Christmas) and Dec 31, Jan 1, 2 (New Year)

# Scenario 1: Dec 24 (Christmas Eve)
now = datetime(2026, 12, 24, 12, 0, tzinfo=timezone.utc)
is_holiday = filter.is_holiday()
# Expected: is_holiday = True

# Scenario 2: Dec 25 (Christmas)
now = datetime(2026, 12, 25, 12, 0, tzinfo=timezone.utc)
is_holiday = filter.is_holiday()
# Expected: is_holiday = True

# Scenario 3: Dec 26 (Day after Christmas)
now = datetime(2026, 12, 26, 12, 0, tzinfo=timezone.utc)
is_holiday = filter.is_holiday()
# Expected: is_holiday = True

# Scenario 4: Dec 31 (New Year's Eve)
now = datetime(2026, 12, 31, 12, 0, tzinfo=timezone.utc)
is_holiday = filter.is_holiday()
# Expected: is_holiday = True

# Scenario 5: Jan 1 (New Year's Day)
now = datetime(2027, 1, 1, 12, 0, tzinfo=timezone.utc)
is_holiday = filter.is_holiday()
# Expected: is_holiday = True

# Scenario 6: Jan 2 (Day after New Year)
now = datetime(2027, 1, 2, 12, 0, tzinfo=timezone.utc)
is_holiday = filter.is_holiday()
# Expected: is_holiday = True

# Scenario 7: Normal day (not holiday)
now = datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc)
is_holiday = filter.is_holiday()
# Expected: is_holiday = False
```

**Checklist:**
- [ ] Dec 24, 25, 26 detected as holiday
- [ ] Dec 31, Jan 1, 2 detected as holiday
- [ ] Other dates NOT holiday
- [ ] Holiday check works across year boundary

#### 4.3 Weekend/Holiday Adjustments

```python
# When filter.enabled = True and low_liquidity period:
adjustments = filter.get_adjustments()

# Expected adjustments:
# - size_multiplier: 0.5 (50% of normal)
# - volume_multiplier: 2.0 (require 2x volume)
# - spread_tolerance: 1.5 (accept 50% wider spreads)
# - max_position_pct: 3.0 (cap at 3% of portfolio)

# When NOT low_liquidity period:
adjustments = filter.get_adjustments()

# Expected adjustments:
# - size_multiplier: 1.0
# - volume_multiplier: 1.0
# - spread_tolerance: 1.0
# - max_position_pct: None (use normal limits)

# When filter.enabled = False:
filter = WeekendHolidayFilter(enabled=False)
adjustments = filter.get_adjustments()

# Expected: All adjustments = 1.0 (no adjustments applied)
```

**Checklist:**
- [ ] Weekend/holiday: 50% size (0.5 multiplier)
- [ ] Weekend/holiday: 2x volume requirement
- [ ] Weekend/holiday: 1.5x spread tolerance
- [ ] Weekend/holiday: 3% max position
- [ ] Normal days: 1.0x all multipliers
- [ ] Disabled filter: returns 1.0x for all

---

### STAGE 5: Integration Testing (30 minutes)

**Verify Session 3B integrates correctly with 3A and Phase 1/2**

#### 5.1 Circuit Breaker Manager Integration

```python
# Create manager with all breakers
manager = CircuitBreakerManager()
manager.register(DailyLossBreaker(data_store))
manager.register(WeeklyLossBreaker(data_store))
manager.register(DrawdownBreaker(data_store))
manager.register(ConsecutiveLossBreaker(data_store))
manager.register(CorrelationBreaker(data_store))

# Check all breakers in parallel
results = await manager.check_all(portfolio)

# Expected:
# - len(results) = 5 (one per breaker)
# - Each result has: triggered, breaker_name, reason, current_value, threshold
# - Manager state updated correctly

# Test get_triggered_breakers()
triggered = manager.get_triggered_breakers()
# Expected: List of breaker names that are triggered
```

**Checklist:**
- [ ] All breakers registered correctly
- [ ] check_all() runs all checks
- [ ] Results have correct structure
- [ ] Manager state tracking works
- [ ] is_any_triggered() works correctly
- [ ] Can reset individual breakers

#### 5.2 Volatility Filter Integration with RiskController

```python
# Add volatility filter to RiskController
risk_controller.volatility_analyzer = VolatilityAnalyzer(market_data_service)

# Create order during EXTREME volatility
order = OrderRequest(symbol="BTCUSDT", side="buy", ...)

# Call check_order()
result = await risk_controller.check_order(order)

# Expected:
# - Volatility check runs (early in pipeline)
# - If EXTREME: rejected with "Extreme volatility" reason
# - If ELEVATED: approved but position sized at 50%
# - If NORMAL: approved with full position size
```

**Checklist:**
- [ ] Volatility check integrated into pipeline
- [ ] Check runs in correct order (after kill switch, before position checks)
- [ ] EXTREME volatility blocks entries
- [ ] ELEVATED volatility reduces size (verified in position sizing)
- [ ] Size adjustment applied correctly

#### 5.3 Time Filter Integration

```python
# Add time filter to RiskController
risk_controller.time_filter = WeekendHolidayFilter(enabled=True)

# Try to trade on weekend
now = datetime(2026, 2, 14, 12, 0, tzinfo=timezone.utc)  # Saturday
order = OrderRequest(symbol="BTCUSDT", ...)

# Call check_order()
result = await risk_controller.check_order(order)

# Expected:
# - If filter enabled and weekend: adjustments applied
# - Size reduced to 50%
# - Volume requirements increased
# - Max position capped at 3%
```

**Checklist:**
- [ ] Time filter integrated into RiskController
- [ ] Weekend/holiday adjustments applied
- [ ] Size multiplier propagated to position sizing
- [ ] Can be disabled via config
- [ ] No impact when disabled

#### 5.4 Event Filter Integration

```python
# Add event to filter
event = TradingEvent(
    name="FOMC Meeting",
    datetime_utc=datetime(2026, 3, 18, 19, 0, tzinfo=timezone.utc),
    block_hours_before=2,
    block_hours_after=4
)
risk_controller.event_filter.add_event(event)

# Try to trade within blocking window
now = datetime(2026, 3, 18, 18, 30, tzinfo=timezone.utc)  # 30 min before event
order = OrderRequest(...)

result = await risk_controller.check_order(order)

# Expected: rejected with "Trading blocked: FOMC Meeting"

# Try outside blocking window
now = datetime(2026, 3, 18, 23, 30, tzinfo=timezone.utc)  # 4.5 hours after event
result = await risk_controller.check_order(order)

# Expected: approved (outside blocking window)
```

**Checklist:**
- [ ] Event blocking window correct
- [ ] Before event: blocked
- [ ] During event: blocked
- [ ] After event: blocked (within after_hours)
- [ ] Outside window: allowed
- [ ] Multiple events handled

#### 5.5 Pipeline Order Verification

```bash
# Verify pipeline order in check_order()
grep -n "def check_order" src/core/risk/controller.py
# Should show correct sequence:
# 1. Kill switch
# 2. Circuit breakers
# 3. Volatility filter
# 4. Time filter
# 5. Event filter
# 6. Position size check (with volatility adjustment)
# 7. Concentration check
# 8. Max positions check
```

**Checklist:**
- [ ] Pipeline order matches spec
- [ ] Kill switch check first (fastest rejection)
- [ ] All auto-triggers before manual checks
- [ ] Filters before sizing checks
- [ ] Position sizing before limits

---

### STAGE 6: Edge Case Validation (20 minutes)

**Verify all edge cases handled gracefully**

#### 6.1 Threshold Boundary Testing

```python
# Daily loss: exactly 5.0%
daily_pct = 5.0
# Expected: TRIGGERED (not just "at threshold" but triggered)

# Daily loss: 4.9999%
daily_pct = 4.9999
# Expected: NOT triggered

# Concentration: exactly 30%
concentration = 30.0
# Expected: NOT triggered (exactly at limit is OK)

# Concentration: 30.0001%
concentration = 30.0001
# Expected: TRIGGERED (just over limit is violation)

# Volatility: exactly 3.0%
vol_pct = 3.0
# Expected: ELEVATED regime (not NORMAL)

# Volatility: exactly 5.0%
vol_pct = 5.0
# Expected: EXTREME regime (not ELEVATED)
```

**Checklist:**
- [ ] Exactly at threshold triggers/blocks appropriately
- [ ] Just over threshold triggers
- [ ] Just under threshold passes
- [ ] No off-by-one errors
- [ ] Boundary conditions tested for all breakers

#### 6.2 Missing/Invalid Data Handling

```python
# Missing ATR for volatility
atr = None
close_price = 5000

vol_pct = await volatility_analyzer.get_volatility_ratio("BTCUSDT")
# Expected: returns 0.0 (safe fallback, not error)
# Expected: no NaN or Infinity propagated

# Zero ATR
atr = 0
close_price = 5000
vol_pct = (0 / 5000) * 100 = 0.0

# Expected: returns 0.0 (NORMAL regime)

# Zero closing price
atr = 100
close_price = 0
# Expected: ValueError or safe fallback (not divide by zero error)

# NaN in portfolio
portfolio.daily_pnl = float('nan')

result = await daily_loss_breaker.check(portfolio)
# Expected: ValueError raised
```

**Checklist:**
- [ ] Missing ATR handled safely
- [ ] Zero prices handled
- [ ] NaN/Infinity rejected with errors
- [ ] No silent failures
- [ ] No cascade failures (one bad value doesn't break everything)

#### 6.3 State Management Edge Cases

```python
# Daily loss: triggered on Tuesday, check on Wednesday
breaker._triggered = True
breaker._last_reset_date = date(2026, 2, 10)  # Tuesday

# Simulate check on Wednesday
now = date(2026, 2, 11)  # Wednesday (new day)

result = await breaker.check(portfolio)
# Expected: triggered = False (reset on new day)
# Expected: _last_reset_date = date(2026, 2, 11)

# Drawdown: triggered, check multiple times
breaker._triggered = True
result1 = await breaker.check(portfolio)
result2 = await breaker.check(portfolio)
result3 = await breaker.check(portfolio)

# Expected: all return triggered = True (no auto-reset)

# Reset manually
await breaker.reset()
result4 = await breaker.check(portfolio)

# Expected: triggered = False (after manual reset)
```

**Checklist:**
- [ ] Daily/weekly auto-reset works on time boundary
- [ ] Drawdown stays triggered until manual reset
- [ ] State consistent across multiple checks
- [ ] Reset() clears state completely
- [ ] No lingering state from previous checks

---

### STAGE 7: Decision Consistency Check (15 minutes)

**Verify implementation follows all architectural decisions**

#### 7.1 Type Hints 100%

```bash
# All functions must have return types
grep -rn "async def " src/core/risk/circuit_breakers.py | grep -v " -> "
# Expected: 0 matches (all async functions have return types)

grep -rn "def " src/core/risk/volatility.py | grep -v " -> "
# Expected: 0 matches (all functions have return types)
```

**Checklist:**
- [ ] Every `async def` has `-> ReturnType`
- [ ] Every `def` has `-> ReturnType`
- [ ] All parameters typed
- [ ] Return types specific (not just `None`, actual types)

#### 7.2 Input Validation

```bash
# Verify NaN/Infinity checks
grep -n "math.isnan\|math.isinf" src/core/risk/
# Should show validation in: volatility.py, circuit_breakers.py
```

**Checklist:**
- [ ] Volatility calculations check for NaN/Infinity
- [ ] Portfolio values checked in circuit breakers
- [ ] Threshold comparisons safe
- [ ] No silent NaN propagation

#### 7.3 Timezone-Aware Datetimes

```bash
# All datetimes must use timezone.utc
grep -n "datetime.now()" src/core/risk/
# Result: Should show 0 matches (deprecated utcnow)

grep -n "datetime.now(timezone.utc)" src/core/risk/
# Result: Should show multiple (correct usage)
```

**Checklist:**
- [ ] No `datetime.utcnow()` (deprecated)
- [ ] All datetimes use `timezone.utc`
- [ ] Time comparisons work correctly across resets

#### 7.4 Structured Logging

```bash
# Verify structured format
grep -n "logger\." src/core/risk/circuit_breakers.py
# Should show structured logging format:
# logger.info("breaker_triggered", extra={"name": ..., "value": ...})
```

**Checklist:**
- [ ] All logs use structured format
- [ ] No string concatenation in logs
- [ ] Extra dict contains relevant fields
- [ ] Log levels appropriate (info, warning, error)

#### 7.5 Decision References

```bash
# Verify decisions referenced in code comments
grep -r "DEC-2026-02-08" src/core/risk/
# Should show decision references in comments
```

**Checklist:**
- [ ] Type hints decision referenced (DEC-2026-02-08-006)
- [ ] Timezone decision referenced (DEC-2026-02-08-003)
- [ ] Input validation decision referenced (DEC-2026-02-08-007)
- [ ] Logging decision referenced (DEC-2026-02-08-008)

---

### STAGE 8: Final Sign-Off (10 minutes)

**Complete final verification and sign-off**

#### 8.1 Final Checklist

```
CODE QUALITY:
- [ ] Stage 1: Automated gates - ALL PASS
- [ ] Stage 2: Threshold validation - ALL CORRECT
- [ ] Stage 3: Volatility regimes - ALL WORKING
- [ ] Stage 4: Time-based filters - ALL CORRECT
- [ ] Stage 5: Integration - ALL TESTS PASS
- [ ] Stage 6: Edge cases - ALL HANDLED
- [ ] Stage 7: Decisions - ALL CONSISTENT

COVERAGE SUMMARY:
- [ ] src/core/risk/circuit_breakers.py   >90%  ✅
- [ ] src/core/risk/volatility.py         >90%  ✅
- [ ] src/core/risk/time_filter.py        >90%  ✅
- [ ] src/core/risk/event_filter.py       >90%  ✅
- [ ] tests/unit/test_circuit_breakers.py >90%  ✅
- [ ] tests/unit/test_volatility_filter.py >90%  ✅
- [ ] TOTAL COVERAGE                  >90%  ✅

CIRCUIT BREAKER VALIDATION:
- [ ] Daily loss: 5% threshold correct
- [ ] Weekly loss: 10% threshold correct
- [ ] Drawdown: 15% threshold, no auto-reset
- [ ] Consecutive losses: 5 threshold, resets on win
- [ ] Correlation: 40% BTC, 30% ETH, 60% group

VOLATILITY FILTER VALIDATION:
- [ ] NORMAL: < 3% ATR/Price
- [ ] ELEVATED: 3-5% ATR/Price (50% size reduction)
- [ ] EXTREME: > 5% (exits only, 4-hour cooldown)
- [ ] Size adjustment integrates with controller

TIME FILTER VALIDATION:
- [ ] Weekend: Saturday 00:00 - Sunday 23:59 UTC
- [ ] Holidays: Dec 24-26, Dec 31-Jan 2
- [ ] Adjustments: 50% size, 2x volume, 1.5x spreads, 3% max
- [ ] Can be disabled via config

INTEGRATION VALIDATION:
- [ ] All breakers in manager work
- [ ] Volatility adjusts position sizing
- [ ] Time filter applies adjustments
- [ ] Event filter blocks correctly
- [ ] Pipeline order correct
- [ ] No breaking changes to Phase 3A
```

#### 8.2 Threshold Summary

```
THRESHOLDS (VERIFIED):
Daily Loss:          5.0% (UTC resets 00:00)
Weekly Loss:        10.0% (UTC resets Mon 00:00)
Drawdown:           15.0% (manual reset only)
Consecutive Losses:   5    (resets on win)
BTC Correlation:    40.0%
ETH Correlation:    30.0%
Group Correlation:  60.0%
Volatility Normal:   <3.0% ATR/Price
Volatility Elevated: 3-5% ATR/Price
Volatility Extreme:  >5.0% ATR/Price
Weekend Size:       50.0% (0.5x multiplier)
Weekend Cooldown:    4 hours (EXTREME vol)
```

#### 8.3 Final Status

```
[✅] Type Safety: mypy --strict PASS (0 errors)
[✅] Code Quality: ruff check PASS (0 violations)
[✅] Imports: isort PASS (0 changes)
[✅] Tests: pytest PASS (all pass, 0 failures)
[✅] Coverage: PASS (>90% per file, >90% total)
[✅] Thresholds: VERIFIED (all correct)
[✅] Regimes: VERIFIED (all correct)
[✅] Time Filters: VERIFIED (UTC-only, correct dates)
[✅] Integration: PASS (Pipeline correct, no breaking changes)
[✅] Decisions: PASS (all consistent, all decisions followed)
[✅] Production Audit: PASS (Grade A-)

OVERALL: ✅ PRODUCTION READY FOR PHASE 4
```

#### 8.4 Sign-Off Statement

If ALL checkpoints are ✅, sign off with:

```
SESSION 3B: ✅ COMPLETE & PRODUCTION READY

Verified: [DATE]
Verified By: [ROLE/NAME]
Signature: ___________________________

Tests Passed: ALL
Coverage: >90% per file
Production Audit: Grade A-
Thresholds: All verified and correct
Ready for: Phase 4 (Execution Engine)

PHASE 3 COMPLETE: Risk Controls Fully Implemented
- Session 3A: Risk Controller + Kill Switch ✅
- Session 3B: Circuit Breakers + Volatility ✅
- Total: 30 tasks, ~60 hours, production quality
```

---

## FAILURE PROTOCOL

If ANY stage fails:

1. **Document the failure:**
   - Stage number
   - Specific failure
   - Error message
   - Root cause

2. **Fix the issue:**
   - Update code
   - Re-run relevant stage
   - Verify no regressions

3. **Re-test:**
   - Run failed stage again
   - Verify fix passes
   - Run integration test

**Only mark as PASS when ALL stages pass.**

---

## ESTIMATED TIME

- Stage 1 (Automated): 30 min
- Stage 2 (Thresholds): 45 min
- Stage 3 (Volatility): 40 min
- Stage 4 (Time Filters): 25 min
- Stage 5 (Integration): 30 min
- Stage 6 (Edge Cases): 20 min
- Stage 7 (Decisions): 15 min
- Stage 8 (Sign-Off): 10 min

**Total: ~3.5 hours (can be 2.5 hours if everything passes first try)**

---

**Prompt Version:** 1.0
**Last Updated:** 2026-02-12
**Applies To:** Session 3B Verification (Sections 3.3 + 3.4)
**Next:** Phase 4 (Execution Engine)
