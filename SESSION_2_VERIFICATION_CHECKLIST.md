# SESSION 2 VERIFICATION CHECKLIST
## Post-Implementation Quality Assurance

**Date Started:** _______________
**Date Completed:** _______________
**Verified By:** _______________

---

## PHASE 1: CODE STRUCTURE & ORGANIZATION

### Directory Structure
- [ ] `src/core/indicators/` directory exists with all required files
- [ ] All 11 indicator files exist (ema.py, rsi.py, atr.py, macd.py, bollinger.py, donchian.py, supertrend.py, vwap.py, sma.py, adx.py, volume.py)
- [ ] Supporting files exist (base.py, utils.py, factory.py, __init__.py)
- [ ] `src/data/cache.py` exists with CacheBackend and InMemoryCache
- [ ] `tests/unit/indicators/` directory exists with all test files
- [ ] `tests/unit/test_cache.py` exists

### File Integrity
- [ ] No placeholder files (TODOs marked as incomplete)
- [ ] No duplicate files or backup files (.bak, .old, etc.)
- [ ] File sizes reasonable (no empty files or obviously incomplete)
- [ ] No syntax errors (can parse all files)

---

## PHASE 2: TYPE SAFETY (100% Required)

### Type Hints Validation
```bash
mypy src/core/indicators/ src/data/cache.py --strict
```

**Checklist:**
- [ ] Command executes with **ZERO errors**
- [ ] All function parameters typed
- [ ] All function returns typed
- [ ] All class attributes typed
- [ ] No `Any` used except where justified (with comments)
- [ ] No implicit `Optional` (use `Optional[T]` explicitly)
- [ ] Generic types used correctly (e.g., `NDArray[np.float64]`, `list[str]`)

**Manual Audit:**
- [ ] All `def` statements have full type hints
- [ ] All class `__init__` parameters typed
- [ ] All dataclass fields typed
- [ ] Protocol types used where appropriate
- [ ] Type imports at top of file (`from typing import ...`)

**Problem Indicators (Look For):**
- ❌ `def calculate(self, series):` (no type hint)
- ❌ `def get_value(self) -> ...` (return type but no params)
- ❌ `values: list` (should be `list[float]`)
- ❌ `Optional[Dict]` (should be `Optional[dict[str, Any]]`)

---

## PHASE 3: IMPORT ORGANIZATION (Strict)

### Import Check
```bash
isort src/core/indicators/ src/data/cache.py --check --diff
```

**Checklist:**
- [ ] Command passes (0 changes needed)
- [ ] Standard library imports grouped first
- [ ] Third-party imports (numpy, sqlalchemy) grouped second
- [ ] Local imports (src.*) grouped third
- [ ] Blank line between groups
- [ ] Imports alphabetized within groups
- [ ] No circular imports

**Manual Audit (Open each file):**
- [ ] Top of file: `import asyncio, math, os` (standard lib)
- [ ] Then: `import numpy as np` (third party)
- [ ] Then: `from src.core.exceptions import ...` (local)
- [ ] No `from X import *` (wildcard imports)
- [ ] No unused imports (`ruff check` catches these)

**Correct Pattern:**
```python
import asyncio
import hashlib
import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np
from numpy.typing import NDArray
from sqlalchemy.orm import Mapped

from src.core.exceptions import ValidationError
from src.data.validators import validate_ohlcv
```

---

## PHASE 4: CODE QUALITY & LINTING

### Ruff Check
```bash
ruff check src/core/indicators/ src/data/cache.py
```

**Checklist:**
- [ ] Command output: **0 violations**
- [ ] No unused variables
- [ ] No unused imports
- [ ] No redefined names
- [ ] No undefined names
- [ ] No bare `except:` clauses
- [ ] No mutable default arguments

### Naming Consistency Audit

**Indicator Result Properties:**
- [ ] All use `.values` (not `.data`, `.results`, `.output`)
- [ ] All use `.current` (not `.latest`, `.last`, `.current_value`)
- [ ] All use `.previous` (not `.prior`, `.prev`, `.last_value`)
- [ ] Consistent naming across all 11 indicators

**Parameter Names:**
- [ ] `period` used consistently (not `lookback`, `window_size`)
- [ ] `series` for OHLCVSeries input (not `data`, `candles`, `ohlcv`)
- [ ] `threshold` for comparison values (not `level`, `limit`)
- [ ] `multiplier` for ATR/Bollinger bands (not `factor`, `multiplier_pct`)

**Function Names:**
- [ ] Snake_case used consistently
- [ ] Verb-noun pattern for methods (`is_bullish()`, `calculate_slope()`)
- [ ] No abbreviations except standard ones (ATR, RSI, EMA, MACD)

**Search & Verify:**
```bash
# Check for inconsistent naming
grep -r "\.latest" src/core/indicators/     # Should be 0 results
grep -r "\.prior" src/core/indicators/      # Should be 0 results
grep -r "\.data\b" src/core/indicators/     # Should be 0 (except .data files)
```

---

## PHASE 5: TEST COVERAGE & EXECUTION

### Test Execution
```bash
pytest tests/unit/indicators/ tests/unit/test_cache.py -v
```

**Checklist:**
- [ ] All tests pass (0 failures, 0 errors)
- [ ] No skipped tests (`xfail` OK if documented)
- [ ] Test execution time < 60 seconds (or document if longer)
- [ ] No warnings during test run

### Coverage Report
```bash
pytest tests/unit/indicators/ tests/unit/test_cache.py \
  --cov=src/core/indicators --cov=src/data/cache \
  --cov-report=term-missing
```

**Checklist:**
- [ ] Overall coverage: **>90%**
- [ ] `src/core/indicators/base.py`: >90%
- [ ] `src/core/indicators/ema.py`: >90%
- [ ] `src/core/indicators/rsi.py`: >90%
- [ ] `src/core/indicators/atr.py`: >90%
- [ ] `src/core/indicators/macd.py`: >90%
- [ ] `src/core/indicators/bollinger.py`: >90%
- [ ] `src/core/indicators/donchian.py`: >90%
- [ ] `src/core/indicators/supertrend.py`: >90%
- [ ] `src/core/indicators/vwap.py`: >90%
- [ ] `src/core/indicators/sma.py`: >90%
- [ ] `src/core/indicators/adx.py`: >90%
- [ ] `src/core/indicators/volume.py`: >90%
- [ ] `src/core/indicators/utils.py`: >90%
- [ ] `src/core/indicators/factory.py`: >90%
- [ ] `src/data/cache.py`: >90%

**Coverage Gap Analysis:**
- [ ] Lines marked as uncovered: document why (unreachable, error handling, etc.)
- [ ] No "sorry, too hard to test" explanations
- [ ] All logic paths tested

### Test Quality Audit

**Test File Completeness:**
- [ ] Each indicator has dedicated test file
- [ ] Reference data present (conftest.py fixtures)
- [ ] TradingView validation implemented
- [ ] Edge cases tested
- [ ] Performance tests present

**Test Content Verification:**
- [ ] `test_ema.py`: ✓ matches TradingView ✓ slope works ✓ edge cases
- [ ] `test_rsi.py`: ✓ Wilder's smoothing ✓ 0-100 bounds ✓ oversold/overbought
- [ ] `test_atr.py`: ✓ TR calculation ✓ Wilder's smoothing ✓ volatility ratio
- [ ] `test_macd.py`: ✓ all 3 lines ✓ crossovers ✓ histogram
- [ ] `test_bollinger.py`: ✓ bands ✓ width/percentB ✓ squeeze
- [ ] `test_donchian.py`: ✓ highest/lowest ✓ breakouts
- [ ] `test_supertrend.py`: ✓ direction ✓ flips
- [ ] `test_vwap.py`: ✓ rolling window ✓ bands
- [ ] `test_adx.py`: ✓ DI+/DI- ✓ trending/ranging
- [ ] `test_factory.py`: ✓ create by name ✓ aliases ✓ list indicators
- [ ] `test_cache.py`: ✓ TTL ✓ concurrent ✓ get_or_set

---

## PHASE 6: INDICATOR CORRECTNESS

### Reference Data Validation

**For Each Indicator, Verify:**
- [ ] Matches TradingView (or reference library)
- [ ] Accuracy: within ±0.0001% of reference
- [ ] Test data: real OHLCV (not synthetic)
- [ ] Multiple assets tested (BTC, ETH)
- [ ] Multiple timeframes tested (1H, 4H)
- [ ] Edge cases validated

**Specific Indicator Checks:**

#### EMA
- [ ] Matches TradingView EMA exactly
- [ ] Startup period handled (SMA fallback)
- [ ] Slope calculation correct
- [ ] Test: BTC 1H for 7 days with 12/26 periods

#### RSI
- [ ] ⚠️ Uses Wilder's smoothing (CRITICAL)
- [ ] NOT using simple EMA (verify in code)
- [ ] Matches TradingView RSI exactly
- [ ] Bounds: strictly [0, 100]
- [ ] Oversold/overbought thresholds work
- [ ] Test: BTC 1H RSI(14) validation

#### ATR
- [ ] ⚠️ Uses Wilder's smoothing
- [ ] TR calculation covers all 3 cases
- [ ] Matches TradingView ATR exactly
- [ ] Volatility ratio calculation correct
- [ ] Test: BTC 1H ATR(14) validation

#### MACD
- [ ] All 3 lines (MACD, Signal, Histogram) correct
- [ ] MACD = EMA(12) - EMA(26)
- [ ] Signal = EMA(MACD, 9)
- [ ] Crossover detection works
- [ ] Matches TradingView MACD
- [ ] Test: BTC 1H MACD validation

#### Bollinger Bands
- [ ] Upper/Lower bands correct
- [ ] Width calculation: (Upper-Lower)/Middle*100
- [ ] %B calculation: (Close-Lower)/(Upper-Lower)*100
- [ ] Squeeze detection: width in bottom percentile
- [ ] Matches TradingView BB
- [ ] Test: BTC 1H BB(20,2) validation

#### ADX (Complex - High Risk)
- [ ] ⚠️ Complex calculation - verify each step
- [ ] +DM / -DM logic correct (all 4 cases)
- [ ] Uses Wilder's smoothing (same as RSI/ATR)
- [ ] +DI / -DI calculated correctly
- [ ] DX calculation correct
- [ ] ADX is smoothed DX
- [ ] Trending/ranging detection works
- [ ] Matches TradingView ADX exactly
- [ ] Test: BTC 1H ADX(14) validation with all components

#### SuperTrend
- [ ] Upper/Lower bands correct
- [ ] Trend direction tracking works (+1/-1)
- [ ] Flip detection accurate
- [ ] Matches reference (TradingView or TA-Lib)
- [ ] Test: BTC 1H SuperTrend validation

#### VWAP
- [ ] ✓ Rolling mode (24H for crypto)
- [ ] Typical Price calculation: (H+L+C)/3
- [ ] VWAP = Sum(TP*Vol)/Sum(Vol)
- [ ] Bands: VWAP ± ATR*multiplier
- [ ] Test: BTC 1H VWAP validation

### Edge Case Validation
- [ ] Insufficient data (fewer bars than period)
- [ ] Flat prices (all same value)
- [ ] NaN handling (graceful, no silent failures)
- [ ] Extreme values (gaps, flash crashes)
- [ ] Duplicate timestamps (handled correctly)
- [ ] Missing data (interpolated or paused)

---

## PHASE 7: CACHING LAYER CORRECTNESS

### Cache Backend
- [ ] AsyncIO safe (asyncio.Lock used)
- [ ] TTL expiration works
- [ ] cleanup_expired() removes old entries
- [ ] Concurrent access safe (no race conditions)
- [ ] set() and get() semantics correct

### Cache Manager
- [ ] Key generation deterministic (same input = same key)
- [ ] Key generation handles complex objects
- [ ] get_or_set() pattern works with sync factory
- [ ] get_or_set() pattern works with async factory
- [ ] Factory not called on cache hit
- [ ] TTL properly respected

### OHLCV Caching
- [ ] Different TTLs by timeframe (1m=30s, 1h=300s, etc.)
- [ ] Cache key format: `ohlcv:{symbol}:{timeframe}:{limit}`
- [ ] Cache hit reduces API calls
- [ ] Integration with Session 1 MarketDataService
- [ ] Manual cache invalidation works

### Indicator Caching
- [ ] Cached results identical to uncached
- [ ] Cache key includes params hash
- [ ] TTL matches OHLCV timeframe TTL
- [ ] Performance: cache hit < 1ms
- [ ] Integration with indicator factory

---

## PHASE 8: INTEGRATION WITH SESSION 1

### Backward Compatibility
- [ ] No breaking changes to Session 1 APIs
- [ ] OHLCVSeries still works with indicators
- [ ] DataStore methods still work
- [ ] No new required dependencies added

### Cross-Module Integration
- [ ] Indicators accept OHLCVSeries from Session 1
- [ ] Cache works with MarketDataService
- [ ] Validators still work (Feature H)
- [ ] Rate limiter still works (Feature J)
- [ ] Symbol manager still works

### Dependency Chain
```
Session 1 Outputs: OHLCVSeries, MarketDataService, DataStore
        ↓
Session 2 Inputs: Used by indicators and caching
        ↓
Session 2 Outputs: Indicators, IndicatorFactory, Cache
        ↓
Session 3 Inputs: Will be used by risk controls
```

- [ ] All dependencies correctly wired
- [ ] No missing imports
- [ ] No circular dependencies

---

## PHASE 9: PERFORMANCE VALIDATION

### Calculation Performance

**Run with 10,000 bars:**
```python
# Each should complete < target time
```

- [ ] EMA(12): < 10ms
- [ ] RSI(14): < 15ms
- [ ] ATR(14): < 15ms
- [ ] MACD(12,26,9): < 20ms
- [ ] Bollinger(20,2): < 20ms
- [ ] Donchian(20): < 15ms
- [ ] SuperTrend(10,3): < 20ms
- [ ] VWAP: < 25ms
- [ ] ADX(14): < 30ms (complex calculation)
- [ ] SMA(20): < 5ms
- [ ] Volume(20): < 10ms

### Memory Performance
- [ ] No memory leaks (run 1000 iterations, check memory)
- [ ] Numpy arrays used (not Python lists)
- [ ] Array operations optimized
- [ ] No unnecessary copies

### Cache Performance
- [ ] Cache hit: < 1ms
- [ ] Cache miss (requires calculation): < target time
- [ ] TTL expiration: < 100ms to check all expired

---

## PHASE 10: DOCUMENTATION & COMMENTS

### Docstrings (Google Style)
- [ ] Every class has docstring
- [ ] Every public method has docstring
- [ ] Every function has docstring
- [ ] Docstrings include: Purpose, Args, Returns, Raises

**Correct Format:**
```python
def calculate_ema(series: OHLCVSeries, period: int) -> IndicatorResult:
    """Calculate exponential moving average.

    Uses EMA formula with 2/(period+1) smoothing factor.
    First value is SMA of first `period` bars.

    Args:
        series: OHLCV data (uses close prices)
        period: EMA period (typically 12, 26)

    Returns:
        IndicatorResult with EMA values

    Raises:
        ValueError: If period < 1 or insufficient data
    """
```

### Inline Comments (WHY, not WHAT)
- [ ] Complex formulas commented (formula notation)
- [ ] Non-obvious logic explained (why this choice)
- [ ] Edge cases documented (what could go wrong)
- [ ] Decision references included (DEC-YYYY-MM-DD-XXX)

**Example:**
```python
# Wilder's smoothing: (prev * (period-1) + current) / period
# NOT simple EMA - see DEC-2026-02-08-XXX for rationale
avg_up = (prev_avg_up * (period - 1) + up_move) / period
```

### README for Indicators
- [ ] File: `src/core/indicators/README.md` exists
- [ ] Lists all 11 indicators
- [ ] Explains usage (factory pattern)
- [ ] Provides examples
- [ ] References (formulas, sources)

---

## PHASE 11: DECISION CONSISTENCY

### Pre-Implementation Review
- [ ] Verified `.claude/DECISIONS.md` exists
- [ ] Identified relevant decisions:
  - DEC-2026-02-08-002: SQLAlchemy 2.0 (not applicable)
  - DEC-2026-02-08-003: Timezone-aware datetimes (if used)
  - DEC-2026-02-08-006: Type hints (100% coverage) ✓ VERIFIED
  - DEC-2026-02-08-008: Structured logging ✓ VERIFIED

### Decision Implementation
- [ ] All relevant decisions followed in code
- [ ] Decision references in comments where applicable
- [ ] No violations of locked decisions
- [ ] New decisions documented (if any)

### Consistency Audit
- [ ] Type hints: 100% (DEC-2026-02-08-006) ✓
- [ ] Imports organized (DEC standard) ✓
- [ ] Naming consistent (no synonyms) ✓
- [ ] Error handling proper (DEC standard) ✓

---

## PHASE 12: PRODUCTION AUDIT

### Run Production Code Audit
```bash
@production-code-audit audit src/core/indicators/ src/data/cache.py
```

**Checklist:**
- [ ] Command completes successfully
- [ ] Result: **Grade A- or higher**
- [ ] No CRITICAL issues
- [ ] No HIGH issues
- [ ] All LOW issues documented (if any)

**Expected Results:**
- ✓ Type safety: PASS
- ✓ Test coverage: PASS (>90%)
- ✓ Code quality: PASS (0 violations)
- ✓ Security: PASS (no injection, no hardcoded secrets)
- ✓ Performance: PASS (meets targets)
- ✓ Documentation: PASS (complete)

---

## PHASE 13: FINAL INTEGRATION TEST

### End-to-End Test
```python
# This test verifies everything works together
async def test_session2_complete_integration():
    """Test complete Session 2 workflow."""

    # 1. Create cache
    cache = InMemoryCache()
    cache_mgr = CacheManager(cache)

    # 2. Get OHLCV from Session 1 (mock or real)
    service = MarketDataService(fetcher, cache_mgr)
    ohlcv = await service.get_ohlcv("BTCUSDT", "1h", 500)

    # 3. Calculate all indicators
    factory = IndicatorFactory()
    ema = factory.create("ema", period=12)
    rsi = factory.create("rsi", period=14)
    atr = factory.create("atr", period=14)

    # ... calculate all 11 indicators

    # 4. Verify results
    assert ema.current > 0
    assert 0 <= rsi.current <= 100
    assert atr.current > 0

    # 5. Verify caching
    ohlcv_cached = await service.get_ohlcv("BTCUSDT", "1h", 500)
    assert ohlcv_cached is ohlcv  # Same object from cache
```

**Checklist:**
- [ ] Test executes without errors
- [ ] All 11 indicators calculate successfully
- [ ] Caching works correctly
- [ ] Performance acceptable (< 100ms total)
- [ ] Integration with Session 1 seamless

---

## PHASE 14: REGRESSION TESTING

### Session 1 Verification
```bash
pytest tests/unit/ --co -q | grep -E "test_data|test_market"
pytest tests/unit/test_market_data.py -v
pytest tests/unit/test_symbol_manager.py -v
```

**Checklist:**
- [ ] All Session 1 tests still pass
- [ ] No import errors
- [ ] No breaking changes
- [ ] MarketDataService works with new cache
- [ ] DataStore still functional

### Cross-Session Compatibility
- [ ] Can import indicators without breaking data module
- [ ] Cache doesn't break MarketDataFetcher
- [ ] OHLCVSeries works with indicators
- [ ] No circular dependencies introduced

---

## PHASE 15: DOCUMENTATION COMPLETENESS

### Code Documentation
- [ ] Every file has module docstring
- [ ] Every class documented (purpose, usage)
- [ ] Every method documented (args, returns, raises)
- [ ] Complex formulas include source/reference

### User Documentation
- [ ] `src/core/indicators/README.md` complete
- [ ] Usage examples for each indicator
- [ ] Factory pattern explained
- [ ] Reference data sources documented
- [ ] Caching strategy documented

### Inline Documentation
- [ ] Edge cases documented
- [ ] Performance assumptions noted
- [ ] Design decisions explained
- [ ] Decision IDs referenced

---

## PHASE 16: SECURITY & SAFETY

### Security Audit
- [ ] No hardcoded secrets
- [ ] No SQL injection risks (not applicable here)
- [ ] No unserialization vulnerabilities
- [ ] Input validation for all public methods

### Safety Audit
- [ ] No bare `except:` clauses
- [ ] Proper exception handling
- [ ] No `eval()` or `exec()` usage
- [ ] Type safety prevents runtime errors

---

## PHASE 17: CLEANUP & POLISH

### Code Cleanup
- [ ] No debug print statements
- [ ] No commented-out code (except documented reasons)
- [ ] No TODO/FIXME without dates (or remove if done)
- [ ] No test code in production files

### File Cleanup
- [ ] No .pyc files
- [ ] No __pycache__ directories (git-ignored anyway)
- [ ] No .tmp or backup files
- [ ] No IDE-specific files (.vscode, .idea)

### Version Control
- [ ] All new files committed
- [ ] Commit messages descriptive
- [ ] No merge conflicts
- [ ] Branch status clean (ready to merge)

---

## PHASE 18: FINAL SIGN-OFF

### Verification Summary

**Type Safety:**
- [ ] mypy --strict: ✓ PASS (0 errors)

**Code Quality:**
- [ ] ruff check: ✓ PASS (0 violations)
- [ ] isort check: ✓ PASS (0 changes)

**Testing:**
- [ ] pytest: ✓ PASS (all tests pass)
- [ ] Coverage: ✓ PASS (>90%)

**Reference Validation:**
- [ ] All indicators vs TradingView: ✓ PASS
- [ ] All calculations correct: ✓ PASS

**Performance:**
- [ ] All targets met: ✓ PASS
- [ ] No regressions: ✓ PASS

**Integration:**
- [ ] Session 1 compatibility: ✓ PASS
- [ ] No breaking changes: ✓ PASS

**Production Audit:**
- [ ] Grade: ✓ A- or higher
- [ ] No CRITICAL issues: ✓ PASS
- [ ] No HIGH issues: ✓ PASS

### Final Checklist
- [ ] All 21 tasks completed (16 indicators + 5 cache)
- [ ] All 18 verification phases passed
- [ ] Ready for Session 3 (Risk Controls)
- [ ] Code review completed
- [ ] No known issues

---

## SIGN-OFF

**All Verification Phases Completed:** ☐

**Code Status:** PRODUCTION READY ☐

**Ready for Session 3:** ☐

**Signed Off By:** _________________
**Date:** _________________
**Time Spent (Session 2):** _________________

---

## Notes & Issues Found

*Document any issues found during verification and how they were resolved:*

```
Issue 1: _________________________
Status: RESOLVED / DEFERRED / OPEN
Resolution: _________________________

Issue 2: _________________________
Status: RESOLVED / DEFERRED / OPEN
Resolution: _________________________
```

---

## Recommendations for Session 3

*Document lessons learned and recommendations for next session:*

1. _________________________
2. _________________________
3. _________________________

---

**Checklist Version:** 1.0
**Last Updated:** 2026-02-11
**Applies To:** Session 2 (Sections 2.2 + 2.4)
