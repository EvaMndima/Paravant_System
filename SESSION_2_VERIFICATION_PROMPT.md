# SESSION 2 VERIFICATION PROMPT
## Production Quality Verification & Sign-Off

**Role:** Production Quality Assurance Lead
**Task:** Verify Session 2 completion meets all production-grade quality standards
**Expected Duration:** 2-3 hours
**Result:** PASS or FAIL with detailed findings

---

## MANDATORY READING
1. `.claude/DECISIONS.md` (decision consistency)
2. `.claude/rules/zero-technical-debt.md` (quality standards)
3. `SESSION_2_IMPLEMENTATION_PROMPT.md` (original requirements)
4. `SESSION_2_VERIFICATION_CHECKLIST.md` (detailed phase checklist)

---

## VERIFICATION WORKFLOW

### STAGE 1: Automated Quality Gates (30 minutes)

**Execute these commands in order. ALL must pass with 0 errors/violations.**

```bash
# 1. Type Safety
mypy src/core/indicators/ src/data/cache.py --strict
# RESULT: Must show "Success: no issues found"

# 2. Code Linting
ruff check src/core/indicators/ src/data/cache.py
# RESULT: Must output nothing (0 violations)

# 3. Import Organization
isort src/core/indicators/ src/data/cache.py --check --diff
# RESULT: Must show "All done! No files would be modified"

# 4. Test Execution
pytest tests/unit/indicators/ tests/unit/test_cache.py -v --tb=short
# RESULT: Must show "passed" for ALL tests, no failures or errors

# 5. Coverage Report
pytest tests/unit/indicators/ tests/unit/test_cache.py \
  --cov=src/core/indicators --cov=src/data/cache \
  --cov-report=term-missing | grep -E "^(src/|TOTAL)"
# RESULT: All files >90%, TOTAL >90%

# 6. Production Audit
@production-code-audit audit src/core/indicators/ src/data/cache.py
# RESULT: Must show Grade A- or higher, no CRITICAL or HIGH issues
```

**GATE RESULT:**
- [ ] ✅ All 6 gates PASS → Continue to Stage 2
- [ ] ❌ Any gate FAILS → Document failure, DO NOT proceed

---

### STAGE 2: Reference Data Validation (45 minutes)

**Verify each of 11 indicators matches TradingView reference values within ±0.0001%**

For each indicator:
```python
# Pseudocode - implement actual comparison
indicator = IndicatorFactory.create("ema", period=12)
result = indicator.calculate(btc_1h_data)

# Compare with TradingView reference
tv_reference = load_tradingview_reference("ema_12_btc_1h")
accuracy = calculate_accuracy(result.values, tv_reference)
assert accuracy >= 99.99%  # ±0.0001%
```

**Indicator Validation Checklist:**
- [ ] EMA(12) - matches TradingView within ±0.0001%
- [ ] RSI(14) - uses Wilder's smoothing (verified), matches TV
- [ ] ATR(14) - uses Wilder's smoothing (verified), matches TV
- [ ] MACD(12,26,9) - all 3 components correct, matches TV
- [ ] Bollinger(20,2) - bands and %B correct, matches TV
- [ ] Donchian(20) - breakout logic verified
- [ ] SuperTrend(10,3) - direction flips verified
- [ ] VWAP - rolling window (24H) verified
- [ ] ADX(14) - DI+/DI-/ADX all components correct, matches TV
- [ ] SMA(20) - basic calculation verified
- [ ] Volume(20) - spike detection verified

**VALIDATION RESULT:**
- [ ] ✅ All 11 indicators PASS → Continue to Stage 3
- [ ] ❌ Any indicator FAILS → Document discrepancy, fix code, re-test

---

### STAGE 3: Code Quality Audit (30 minutes)

**Manual inspection of code quality standards**

**Type Hints (100% Required):**
```bash
# Search for type hint issues
grep -rn "def.*):$" src/core/indicators/     # Missing return type
grep -rn "def.*:$" src/core/indicators/ | grep -v " -> " # No return type
# Result: MUST show 0 matches (or only for __init__, which can be implicit)
```

- [ ] Every `def` has parameter types and return type
- [ ] All class attributes typed in `__init__` or at class level
- [ ] No bare `Any` without justification comment
- [ ] No implicit `Optional` (use `Optional[T]` explicitly)

**Naming Consistency (Zero Synonyms):**
```bash
# All indicator results use these names:
grep -r "\.data\b" src/core/indicators/       # Should be ".values"
grep -r "\.latest" src/core/indicators/       # Should be ".current"
grep -r "\.prior" src/core/indicators/        # Should be ".previous"
# Result: MUST show 0 matches (except in comments)
```

- [ ] All use `.values` (consistent across 11 indicators)
- [ ] All use `.current` (no `.latest`, `.last`, `.latest_value`)
- [ ] All use `.previous` (no `.prior`, `.prev`)
- [ ] All use `.period` for lookback (no `.window`, `.lookback_period`)
- [ ] All use `.series` for input (no `.data`, `.candles`, `.ohlcv`)

**Imports (Strict Organization):**
```python
# Open 3 random indicator files
# Verify import order:
# 1. Standard library (asyncio, math, etc.)
# 2. Third-party (numpy, sqlalchemy)
# 3. Local (src.*)
# 4. Blank lines between groups
# 5. Alphabetized within groups
```

- [ ] Import order correct in all files
- [ ] No wildcard imports (`from X import *`)
- [ ] No unused imports (ruff already caught)
- [ ] No circular imports

**Documentation:**
- [ ] Every class has docstring (purpose, usage)
- [ ] Every public method has docstring (args, returns, raises)
- [ ] Complex formulas commented with source/reference
- [ ] Edge cases documented in code

**AUDIT RESULT:**
- [ ] ✅ All standards MET → Continue to Stage 4
- [ ] ❌ Issues found → List them, fix code, re-verify

---

### STAGE 4: Integration Testing (30 minutes)

**Test that Session 2 integrates correctly with Session 1**

```python
# This integration test must work:
async def test_full_workflow():
    """Test Session 2 works with Session 1."""

    # 1. Get OHLCV from Session 1 (real or mock)
    service = MarketDataService(fetcher, cache_manager)
    btc_data = await service.get_ohlcv("BTCUSDT", "1h", 500)

    # 2. Create all 11 indicators
    factory = IndicatorFactory()
    indicators = [
        factory.create("ema", period=12),
        factory.create("rsi", period=14),
        factory.create("atr", period=14),
        factory.create("macd"),
        factory.create("bollinger", period=20),
        factory.create("donchian", period=20),
        factory.create("supertrend", period=10, multiplier=3),
        factory.create("vwap"),
        factory.create("adx", period=14),
        factory.create("sma", period=20),
        factory.create("volume", period=20),
    ]

    # 3. Calculate all indicators
    for indicator in indicators:
        result = indicator.calculate(btc_data)
        assert result.current is not None
        assert not math.isnan(result.current)

    # 4. Test caching
    btc_cached = await service.get_ohlcv("BTCUSDT", "1h", 500)
    assert btc_cached is btc_data  # Same object from cache
```

**Integration Checks:**
- [ ] All 11 indicators calculate without errors
- [ ] All return valid results (not NaN, not None)
- [ ] Cache integration works (cache hits reduce API calls)
- [ ] No breaking changes to Session 1 APIs
- [ ] No circular dependencies

**INTEGRATION RESULT:**
- [ ] ✅ All tests PASS → Continue to Stage 5
- [ ] ❌ Tests FAIL → Fix integration issues, re-test

---

### STAGE 5: Performance Validation (15 minutes)

**Verify each indicator meets performance targets with 10,000 bars**

```python
import time

data = load_10k_bars()  # Real OHLCV data

# Each indicator must complete in target time:
targets = {
    "ema": 10,          # ms
    "sma": 5,           # ms
    "rsi": 15,          # ms
    "atr": 15,          # ms
    "macd": 20,         # ms
    "bollinger": 20,    # ms
    "donchian": 15,     # ms
    "supertrend": 20,   # ms
    "vwap": 25,         # ms
    "adx": 30,          # ms (complex)
    "volume": 10,       # ms
}

for name, target_ms in targets.items():
    indicator = IndicatorFactory.create(name)
    start = time.time()
    result = indicator.calculate(data)
    elapsed_ms = (time.time() - start) * 1000

    assert elapsed_ms < target_ms, \
        f"{name} took {elapsed_ms:.1f}ms, target {target_ms}ms"
    print(f"✅ {name}: {elapsed_ms:.1f}ms")
```

**Performance Checklist:**
- [ ] EMA < 10ms
- [ ] RSI < 15ms
- [ ] ATR < 15ms
- [ ] MACD < 20ms
- [ ] Bollinger < 20ms
- [ ] Donchian < 15ms
- [ ] SuperTrend < 20ms
- [ ] VWAP < 25ms
- [ ] ADX < 30ms (complex calculation)
- [ ] SMA < 5ms
- [ ] Volume < 10ms
- [ ] Cache hit < 1ms

**PERFORMANCE RESULT:**
- [ ] ✅ All targets MET → Continue to Stage 6
- [ ] ❌ Any target MISSED → Optimize code, re-test

---

### STAGE 6: Edge Case Validation (20 minutes)

**Verify all indicators handle edge cases gracefully**

```python
# Edge case scenarios
test_cases = [
    ("insufficient_data", OHLCVSeries with 5 bars, period=14),
    ("flat_prices", OHLCVSeries with all same price),
    ("large_gap", OHLCVSeries with 50% gap),
    ("zero_volume", OHLCVSeries with volume=0),
    ("extreme_volatility", OHLCVSeries with 30% daily moves),
]

for case_name, data, period in test_cases:
    try:
        indicator = IndicatorFactory.create("ema", period=period)
        result = indicator.calculate(data)
        # Should either calculate correctly or raise ValueError
        # NOT crash or return NaN silently
        assert result is not None
        print(f"✅ {case_name}: handled gracefully")
    except ValueError as e:
        print(f"✅ {case_name}: raised ValueError as expected")
```

**Edge Case Checklist:**
- [ ] Insufficient data: raises ValueError or returns partial results
- [ ] Flat prices (all same): calculations don't break, RSI=50 (neutral), ATR=0
- [ ] Large gaps: doesn't produce NaN, handles correctly
- [ ] Zero volume: doesn't divide by zero
- [ ] Extreme volatility: doesn't overflow, stays bounded

**EDGE CASE RESULT:**
- [ ] ✅ All cases handled → Continue to Stage 7
- [ ] ❌ Any case fails → Add error handling, re-test

---

### STAGE 7: Decision Consistency Check (15 minutes)

**Verify implementation follows all architectural decisions**

**Check DEC-2026-02-08-XXX decisions:**

```bash
# 1. DEC-2026-02-08-006: Type Hints (100%)
grep -r ": " src/core/indicators/ | grep "def " | grep -v " -> "
# Result: Should show 0 (all functions have return types)

# 2. DEC-2026-02-08-008: Structured Logging
grep -r "logger\." src/core/indicators/
# Result: Should use structured format (if logging present)

# 3. All decision references present in code
grep -r "DEC-2026-02-08" src/core/indicators/
# Result: Should have at least some decision references
```

**Decision Verification:**
- [ ] Type hints 100% complete (DEC-2026-02-08-006)
- [ ] Structured logging used (DEC-2026-02-08-008)
- [ ] No locked decisions violated (asset class, broker, order types)
- [ ] Decision consistency verified in `.claude/DECISIONS.md`

**DECISION RESULT:**
- [ ] ✅ All decisions followed → Continue to Stage 8
- [ ] ❌ Violations found → Fix code, update DECISIONS.md if needed

---

### STAGE 8: Final Sign-Off (10 minutes)

**Complete final verification and sign-off**

**Final Checklist:**
- [ ] Stage 1: Automated gates - ALL PASS
- [ ] Stage 2: Reference validation - ALL PASS
- [ ] Stage 3: Code quality - ALL STANDARDS MET
- [ ] Stage 4: Integration - ALL TESTS PASS
- [ ] Stage 5: Performance - ALL TARGETS MET
- [ ] Stage 6: Edge cases - ALL HANDLED
- [ ] Stage 7: Decisions - ALL CONSISTENT

**Coverage Summary:**
```
src/core/indicators/base.py       >90%  ✅
src/core/indicators/ema.py        >90%  ✅
src/core/indicators/rsi.py        >90%  ✅
src/core/indicators/atr.py        >90%  ✅
src/core/indicators/macd.py       >90%  ✅
src/core/indicators/bollinger.py  >90%  ✅
src/core/indicators/donchian.py   >90%  ✅
src/core/indicators/supertrend.py >90%  ✅
src/core/indicators/vwap.py       >90%  ✅
src/core/indicators/sma.py        >90%  ✅
src/core/indicators/adx.py        >90%  ✅
src/core/indicators/volume.py     >90%  ✅
src/core/indicators/utils.py      >90%  ✅
src/core/indicators/factory.py    >90%  ✅
src/data/cache.py                 >90%  ✅
TOTAL                             >90%  ✅
```

**Production Audit Grade:** A- or higher ✅

**Final Status:**
```
[✅] Type Safety: PASS (mypy --strict)
[✅] Code Quality: PASS (ruff, isort)
[✅] Tests: PASS (all pass, >90% coverage)
[✅] Reference Data: PASS (TradingView validation)
[✅] Performance: PASS (all targets met)
[✅] Integration: PASS (Session 1 compatible)
[✅] Decisions: PASS (all consistent)
[✅] Production Audit: PASS (Grade A-)

OVERALL: ✅ PRODUCTION READY
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

## DELIVERABLES

After successful verification:

1. **Verification Report** (this document completed)
2. **Code ready for Session 3**
3. **Test coverage report** (>90%)
4. **Performance report** (all targets met)
5. **Decision consistency audit** (all verified)

---

## ESTIMATED TIME

- Stage 1 (Automated): 30 min
- Stage 2 (Reference): 45 min
- Stage 3 (Code Quality): 30 min
- Stage 4 (Integration): 30 min
- Stage 5 (Performance): 15 min
- Stage 6 (Edge Cases): 20 min
- Stage 7 (Decisions): 15 min
- Stage 8 (Sign-Off): 10 min

**Total: ~3 hours (can be 2 hours if everything passes first try)**

---

## SUCCESS CRITERIA

**Session 2 is PRODUCTION READY when:**
- ✅ All 8 stages PASS
- ✅ mypy --strict: 0 errors
- ✅ ruff check: 0 violations
- ✅ pytest: 100% pass (all tests)
- ✅ Coverage: >90% per file, >90% total
- ✅ Reference data: All indicators match within ±0.0001%
- ✅ Performance: All targets met
- ✅ Production audit: Grade A- or higher
- ✅ Ready for Session 3 (Risk Controls)

**If ALL checkpoints are ✅, sign off with:**
```
SESSION 2: ✅ COMPLETE & PRODUCTION READY
Verified: [DATE]
Ready for: Session 3 (Risk Controls)
```

---

**Prompt Version:** 1.0
**Last Updated:** 2026-02-11
**Applies To:** Session 2 Verification (Sections 2.2 + 2.4)
