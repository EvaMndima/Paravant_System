# PHASE 2 SESSION 2: Computation Layer (Sections 2.2 + 2.4)

## Context
- **Session 1 Status**: COMPLETE (Market data fetching + symbol management fully implemented and tested)
- **Session 2 Goal**: Build technical indicators (2.2) and caching layer (2.4)
- **This Session**: 21 tasks across 2 sections (~42 hours)

## Essential Reading (MANDATORY - Read BEFORE Starting)
1. `.claude/DECISIONS.md` - All architectural decisions (focus on DEC-2026-02-08-XXX for Phase 2)
2. `.claude/rules/decision-consistency.md` - Decision enforcement
3. `.claude/rules/zero-technical-debt.md` - Code quality standards
4. `docs/02_PHASE_2_DATA_LAYER.md` - Tasks 2.2.1-2.2.16, 2.4.1-2.4.5
5. `docs/TRADING_SYSTEM_PRD.md` - Feature H (Data Quality), reference features for indicators

## Critical Quality Gates (Non-Negotiable)

### Type Hints (100% Coverage)
```python
# CORRECT - Every parameter and return typed
def calculate_ema(series: NDArray[np.float64], period: int) -> NDArray[np.float64]:
    """Calculate exponential moving average."""
    alpha: float = 2.0 / (period + 1)
    ema_values: NDArray[np.float64] = np.full_like(series, np.nan)
    return ema_values

# INCORRECT - Missing types
def calculate_ema(series, period):  # NEVER DO THIS
    alpha = 2.0 / (period + 1)
    return ema_values
```

### Import Organization (Strict)
```python
# CORRECT order:
import asyncio
import hashlib
import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Protocol

import numpy as np
from numpy.typing import NDArray
from sqlalchemy.orm import Mapped, mapped_column

from src.core.exceptions import ValidationError
from src.data.cache import CacheBackend

# INCORRECT - No grouping, wrong order
from src.core.exceptions import ValidationError
import numpy
import math
from src.data.cache import CacheBackend
from datetime import datetime
```

### Naming Consistency (Zero Synonyms)
```python
# CORRECT - Consistent names
indicator_result.values          # Use "values" everywhere
indicator_result.current         # Current value accessor
indicator_result.previous        # Previous value accessor

# INCORRECT - Inconsistent
indicator_result.data            # Don't use "data" and "values"
indicator_result.latest          # Don't use "latest" and "current"
indicator_result.prior           # Don't use "prior" and "previous"
```

## SECTION 2.2: TECHNICAL INDICATORS (16 Tasks)

### Execution Order (Strict Dependency Chain)

1. **2.2.1** → Indicator Base Class (foundation for all)
2. **2.2.2** → EMA (dependency for MACD, VWAP, others)
3. **2.2.3** → RSI (independent)
4. **2.2.4** → ATR (dependency for SuperTrend, VWAP, ADX, all volatility-based)
5. **2.2.10** → SMA (simple, dependency for Bollinger, ADX)
6. **2.2.5** → MACD (depends on EMA)
7. **2.2.6** → Bollinger Bands (uses SMA)
8. **2.2.7** → Donchian (independent)
9. **2.2.8** → SuperTrend (depends on ATR)
10. **2.2.9** → VWAP (depends on ATR)
11. **2.2.11** → ADX (depends on ATR and SMA)
12. **2.2.12** → Volume Average (depends on SMA)
13. **2.2.13** → Utility Functions (helpers for all)
14. **2.2.14** → Indicator Factory (registry)
15. **2.2.15** → Module Exports (__init__.py)
16. **2.2.16** → Comprehensive Tests

### Task 2.2.1: Indicator Base Class
**File:** `src/core/indicators/base.py`
**Effort:** 1 hour

**Classes Required:**
```python
class IndicatorResult(Generic[T]):
    """Generic indicator result container with current/previous access."""

    name: str                          # Indicator name (e.g., "EMA")
    values: NDArray[np.float64]        # Result array
    params: Dict[str, Any]             # Parameters used
    _current_index: int                # Track position

    @property
    def current(self) -> float:        # Latest value (safe NaN checking)

    @property
    def previous(self) -> float:       # Previous value

    def to_list(self) -> list[float]:  # Convert to Python list

class Indicator(ABC):
    """Base class for all indicators."""

    @abstractmethod
    def calculate(self, series: OHLCVSeries) -> IndicatorResult: ...

    @staticmethod
    def required_periods(period: int) -> int:
        """Return minimum bars needed before first valid value."""
        return period
```

**Acceptance Criteria:**
- [ ] IndicatorResult handles NaN values safely
- [ ] current/previous never return NaN (raise ValueError if insufficient data)
- [ ] Type hints 100% complete
- [ ] Unit tests: value access, NaN handling, edge cases
- [ ] Integration: Works with numpy arrays from Session 1

---

### Task 2.2.2: EMA (Exponential Moving Average)
**File:** `src/core/indicators/ema.py`
**Effort:** 1.5 hours
**CRITICAL:** Used by MACD, VWAP, and other indicators

**Formula:**
```
α = 2 / (period + 1)
EMA[0] = first value (or SMA of first `period` bars)
EMA[t] = α * Price[t] + (1 - α) * EMA[t-1]
```

**Methods:**
```python
class EMA(Indicator):
    def __init__(self, period: int):
        self.period: int = period
        self.alpha: float = 2.0 / (period + 1)

    def calculate(self, series: OHLCVSeries) -> IndicatorResult:
        """Calculate EMA from OHLCV series (uses close prices)."""

    @staticmethod
    def slope(values: NDArray[np.float64], lookback: int) -> float:
        """Calculate slope over lookback period (% per bar)."""
```

**Reference Validation:**
```python
# Must match TradingView's EMA indicator
# Test data: BTC 1H 2024-01-01 to 2024-01-07
# Expected EMA(12) at specific timestamps should match ±0.0001%
```

**Acceptance Criteria:**
- [ ] EMA calculation matches TradingView reference (use test data)
- [ ] Handles startup period correctly (SMA fallback first N bars)
- [ ] Slope calculation works (% change per bar)
- [ ] Edge cases: insufficient data, all same prices, NaN handling
- [ ] Unit tests with known reference values from TradingView
- [ ] Performance: calculates 10k bars < 10ms

---

### Task 2.2.3: RSI (Relative Strength Index)
**File:** `src/core/indicators/rsi.py`
**Effort:** 1.5 hours

**Formula (Wilder's Smoothing - CRITICAL):**
```
UpMove = max(close[t] - close[t-1], 0)
DnMove = max(close[t-1] - close[t], 0)
AvgUp[0] = SMA(UpMove, period)
AvgDn[0] = SMA(DnMove, period)
AvgUp[t] = (AvgUp[t-1] * (period - 1) + UpMove[t]) / period  # WILDER'S, NOT EMA!
AvgDn[t] = (AvgDn[t-1] * (period - 1) + DnMove[t]) / period
RS = AvgUp / AvgDn
RSI = 100 - (100 / (1 + RS))
```

**Methods:**
```python
class RSI(Indicator):
    def calculate(self, series: OHLCVSeries) -> IndicatorResult:
        """Calculate RSI (0-100 bounded)."""

    @staticmethod
    def is_oversold(values: NDArray[np.float64], threshold: float = 30.0) -> bool:
        """Check if current RSI < threshold."""

    @staticmethod
    def is_overbought(values: NDArray[np.float64], threshold: float = 70.0) -> bool:
        """Check if current RSI > threshold."""
```

**⚠️ CRITICAL ERROR PREVENTION:**
- MUST use Wilder's smoothing (not simple EMA)
- WRONG: `AvgUp = ema(upMoves)` → Will produce incorrect values
- RIGHT: `AvgUp[t] = (AvgUp[t-1] * (period-1) + UpMove[t]) / period`

**Acceptance Criteria:**
- [ ] Uses Wilder's smoothing (verified against TradingView)
- [ ] Values strictly bounded [0, 100]
- [ ] Oversold/overbought detection works
- [ ] Edge cases: flat prices (AvgDn=0), insufficient data
- [ ] Unit tests with TradingView reference values
- [ ] Performance: calculates 10k bars < 15ms

---

### Task 2.2.4: ATR (Average True Range)
**File:** `src/core/indicators/atr.py`
**Effort:** 1.5 hours
**CRITICAL:** Dependency for SuperTrend, VWAP, ADX

**Formula:**
```
TR[t] = max(
    High[t] - Low[t],
    |High[t] - Close[t-1]|,
    |Low[t] - Close[t-1]|
)
ATR[0] = SMA(TR, period)
ATR[t] = (ATR[t-1] * (period - 1) + TR[t]) / period  # Wilder's smoothing
```

**Methods:**
```python
class ATR(Indicator):
    def calculate(self, series: OHLCVSeries) -> IndicatorResult:
        """Calculate ATR, store TR in metadata."""
        # Must include TR values in result for dependent indicators

    @staticmethod
    def volatility_ratio(values: NDArray[np.float64],
                         closes: NDArray[np.float64]) -> float:
        """Return current ATR as % of current close."""
```

**Acceptance Criteria:**
- [ ] True Range calculated correctly for all scenarios
- [ ] Uses Wilder's smoothing (same as RSI)
- [ ] TR values accessible in result.metadata["tr"]
- [ ] Volatility ratio = ATR / Close * 100 (%)
- [ ] Unit tests with known TR values
- [ ] Edge cases: gaps, limit up/down moves
- [ ] Performance: calculates 10k bars < 15ms

---

### Task 2.2.5: MACD (Moving Average Convergence Divergence)
**File:** `src/core/indicators/macd.py`
**Effort:** 2 hours
**Dependencies:** EMA (2.2.2)

**Formula:**
```
MACD = EMA(12) - EMA(26)
Signal = EMA(MACD, 9)
Histogram = MACD - Signal
```

**Result Class:**
```python
class MACDResult(IndicatorResult):
    macd_line: NDArray[np.float64]      # MACD values
    signal_line: NDArray[np.float64]    # Signal line (EMA of MACD)
    histogram: NDArray[np.float64]      # MACD - Signal

    def is_bullish_crossover(self) -> bool:
        """MACD crosses above signal line."""

    def is_bearish_crossover(self) -> bool:
        """MACD crosses below signal line."""

    def histogram_rising(self) -> bool:
        """Histogram increasing (MACD accelerating)."""
```

**Acceptance Criteria:**
- [ ] All three components calculated correctly
- [ ] Bullish/bearish crossover detection works
- [ ] Histogram rising/falling detection works
- [ ] Unit tests with TradingView reference values
- [ ] Crossover edge cases tested
- [ ] Performance: calculates 10k bars < 20ms

---

### Task 2.2.6: Bollinger Bands
**File:** `src/core/indicators/bollinger.py`
**Effort:** 2 hours

**Formula:**
```
Basis = SMA(close, 20)
StdDev = StdDev(close, 20)
Upper = Basis + (StdDev * 2)
Lower = Basis - (StdDev * 2)
Width = (Upper - Lower) / Basis * 100  # Band width as % of basis
%B = (Close - Lower) / (Upper - Lower) * 100  # Position in band (0-100)
```

**Result Class:**
```python
class BollingerResult(IndicatorResult):
    upper: NDArray[np.float64]
    middle: NDArray[np.float64]       # SMA
    lower: NDArray[np.float64]
    width: NDArray[np.float64]        # %
    percent_b: NDArray[np.float64]    # 0-100

    def is_squeezed(self, percentile: int = 10) -> bool:
        """Check if band width in bottom N percentile."""

    def is_at_upper(self) -> bool:
        """Price at or above upper band."""

    def is_at_lower(self) -> bool:
        """Price at or below lower band."""
```

**Acceptance Criteria:**
- [ ] All bands calculated correctly
- [ ] Width and %B calculations correct
- [ ] Squeeze detection (width percentile logic)
- [ ] Unit tests with TradingView reference
- [ ] Edge cases: gaps, extreme volatility
- [ ] Performance: calculates 10k bars < 20ms

---

### Task 2.2.7: Donchian Channels
**File:** `src/core/indicators/donchian.py`
**Effort:** 1.5 hours

**Formula:**
```
Upper = Highest High over last N periods
Lower = Lowest Low over last N periods
Middle = (Upper + Lower) / 2
```

**Result Class:**
```python
class DonchianResult(IndicatorResult):
    upper: NDArray[np.float64]
    middle: NDArray[np.float64]
    lower: NDArray[np.float64]

    def is_breakout_up(self) -> bool:
        """Price closed above upper band."""

    def is_breakout_down(self) -> bool:
        """Price closed below lower band."""
```

**Acceptance Criteria:**
- [ ] Highest/lowest logic correct (no off-by-one errors)
- [ ] Breakout detection works
- [ ] Unit tests with known values
- [ ] Edge cases: all same prices, gaps
- [ ] Performance: calculates 10k bars < 15ms

---

### Task 2.2.8: SuperTrend
**File:** `src/core/indicators/supertrend.py`
**Effort:** 2.5 hours
**Dependencies:** ATR (2.2.4)

**Formula:**
```
HL2 = (High + Low) / 2
UpperBand = HL2 + (Multiplier * ATR)
LowerBand = HL2 - (Multiplier * ATR)

if Close > UpperBand[prev]: Trend = 1 (bullish)
if Close < LowerBand[prev]: Trend = -1 (bearish)
ST = UpperBand if Trend==1 else LowerBand
```

**Result Class:**
```python
class SuperTrendResult(IndicatorResult):
    supertrend: NDArray[np.float64]    # ST values
    trend: NDArray[np.int8]            # +1 bullish, -1 bearish
    upper_band: NDArray[np.float64]
    lower_band: NDArray[np.float64]

    def just_flipped_bullish(self) -> bool:
        """Trend flipped from -1 to +1."""

    def just_flipped_bearish(self) -> bool:
        """Trend flipped from +1 to -1."""
```

**Acceptance Criteria:**
- [ ] SuperTrend value correct
- [ ] Trend direction tracked correctly
- [ ] Flip detection works
- [ ] Unit tests with reference data
- [ ] Edge cases: rapid trend changes
- [ ] Performance: calculates 10k bars < 20ms

---

### Task 2.2.9: VWAP (Volume Weighted Average Price)
**File:** `src/core/indicators/vwap.py`
**Effort:** 2 hours
**Dependencies:** ATR (2.2.4)

**Formula:**
```
TypicalPrice = (High + Low + Close) / 3
VWAP = Σ(TypicalPrice * Volume) / Σ(Volume)

For crypto (24/7):
- Rolling mode: 24-hour window
- Session mode: Daily reset at 00:00 UTC
```

**Result Class:**
```python
class VWAPResult(IndicatorResult):
    vwap: NDArray[np.float64]
    upper_band: NDArray[np.float64]    # VWAP + ATR*multiplier
    lower_band: NDArray[np.float64]    # VWAP - ATR*multiplier

    def is_at_vwap(self, tolerance: float = 0.05) -> bool:
        """Price within tolerance of VWAP."""
```

**Acceptance Criteria:**
- [ ] Rolling VWAP correct (24H window)
- [ ] Bands calculated correctly
- [ ] Price-at-VWAP detection works
- [ ] Unit tests with known values
- [ ] Edge cases: volume spikes, gaps
- [ ] Performance: calculates 10k bars < 25ms

---

### Task 2.2.10: SMA (Simple Moving Average)
**File:** `src/core/indicators/sma.py`
**Effort:** 45 minutes

**Formula:**
```
SMA = Sum(Close[t:t-period+1]) / period
```

**Acceptance Criteria:**
- [ ] SMA calculation correct
- [ ] Works for price and volume
- [ ] Edge cases: insufficient data
- [ ] Unit tests with known values
- [ ] Performance: calculates 10k bars < 5ms

---

### Task 2.2.11: ADX (Average Directional Index)
**File:** `src/core/indicators/adx.py`
**Effort:** 2 hours
**Dependencies:** ATR (2.2.4), SMA (2.2.10)

**Formula (Complex - be careful):**
```
+DM = max(High[t] - High[t-1], 0) if positive
-DM = max(Low[t-1] - Low[t], 0) if positive
(else both 0 if high-low is greater)

+DI = 100 * Wilder's Smoothed(+DM) / ATR
-DI = 100 * Wilder's Smoothed(-DM) / ATR
DX = 100 * |+DI - -DI| / (+DI + -DI)
ADX = Wilder's Smoothed(DX)
```

**Result Class:**
```python
class ADXResult(IndicatorResult):
    adx: NDArray[np.float64]
    plus_di: NDArray[np.float64]       # +DI
    minus_di: NDArray[np.float64]      # -DI

    def is_trending(self, threshold: float = 25.0) -> bool:
        """ADX > threshold indicates trend."""

    def is_ranging(self, threshold: float = 20.0) -> bool:
        """ADX < threshold indicates range."""

    @property
    def trend_direction(self) -> int:
        """Return +1 (bullish), -1 (bearish), 0 (equal)."""
```

**Acceptance Criteria:**
- [ ] ADX and DI values correct (complex calculation)
- [ ] Trending/ranging detection works
- [ ] Trend direction logic correct
- [ ] Unit tests with TradingView reference values
- [ ] Edge cases: calculation startup, flat prices
- [ ] Performance: calculates 10k bars < 30ms

---

### Task 2.2.12: Volume Average
**File:** `src/core/indicators/volume.py`
**Effort:** 1 hour

**Methods:**
```python
class VolumeAverage(Indicator):
    def calculate(self, series: OHLCVSeries) -> IndicatorResult:
        """Calculate volume moving average."""

    @staticmethod
    def is_volume_spike(values: NDArray[np.float64],
                       avg: NDArray[np.float64],
                       multiplier: float = 1.5) -> bool:
        """Check if current volume > average * multiplier."""

    @staticmethod
    def volume_ratio(current: float, avg: float) -> float:
        """Return current / avg ratio."""
```

**Acceptance Criteria:**
- [ ] Volume average calculated correctly (SMA of volume)
- [ ] Spike detection works
- [ ] Ratio calculation works
- [ ] Edge cases: zero volume, gaps
- [ ] Unit tests with known values

---

### Task 2.2.13: Utility Functions
**File:** `src/core/indicators/utils.py`
**Effort:** 45 minutes

**Functions Required:**
```python
def calculate_slope(values: NDArray[np.float64], lookback: int) -> float:
    """Linear regression slope (change per bar)."""

def calculate_normalized_slope(values: NDArray[np.float64],
                               lookback: int) -> float:
    """Slope as % of current value."""

def is_rising(values: NDArray[np.float64], periods: int) -> bool:
    """Check if all last N values rising."""

def is_falling(values: NDArray[np.float64], periods: int) -> bool:
    """Check if all last N values falling."""

def crossover(fast: NDArray[np.float64],
              slow: NDArray[np.float64]) -> bool:
    """Check if fast just crossed above slow."""

def crossunder(fast: NDArray[np.float64],
               slow: NDArray[np.float64]) -> bool:
    """Check if fast just crossed below slow."""

def highest(values: NDArray[np.float64], period: int) -> float:
    """Highest value in last N periods."""

def lowest(values: NDArray[np.float64], period: int) -> float:
    """Lowest value in last N periods."""
```

**Acceptance Criteria:**
- [ ] All utilities work correctly
- [ ] Cross detection (current vs previous)
- [ ] Edge cases handled
- [ ] Unit tests for each function

---

### Task 2.2.14: Indicator Factory
**File:** `src/core/indicators/factory.py`
**Effort:** 1 hour

**Registry Pattern:**
```python
class IndicatorFactory:
    _registry: Dict[str, Type[Indicator]] = {
        "ema": EMA,
        "sma": SMA,
        "rsi": RSI,
        "atr": ATR,
        "macd": MACD,
        "bollinger": BollingerBands,
        "bb": BollingerBands,  # Alias
        "donchian": DonchianChannel,
        "supertrend": SuperTrend,
        "vwap": VWAP,
        "adx": ADX,
        "volume": VolumeAverage,
    }

    @staticmethod
    def create(name: str, **params) -> Indicator:
        """Create indicator by name with params."""

    @staticmethod
    def register(name: str, indicator_class: Type[Indicator]) -> None:
        """Register custom indicator."""

    @staticmethod
    def list_indicators() -> list[str]:
        """List all registered indicators."""
```

**Acceptance Criteria:**
- [ ] Create by name works
- [ ] Aliases work (bb → BollingerBands)
- [ ] Invalid names raise ValueError
- [ ] List available indicators
- [ ] Unit tests for factory

---

### Task 2.2.15: Indicators Module Exports
**File:** `src/core/indicators/__init__.py`
**Effort:** 15 minutes

**Exports Required:**
```python
# All indicator classes
from .ema import EMA
from .rsi import RSI
from .atr import ATR
from .macd import MACD, MACDResult
from .bollinger import BollingerBands, BollingerResult
from .donchian import DonchianChannel, DonchianResult
from .supertrend import SuperTrend, SuperTrendResult
from .vwap import VWAP, VWAPResult
from .sma import SMA
from .adx import ADX, ADXResult
from .volume import VolumeAverage

# Base classes
from .base import Indicator, IndicatorResult

# Utilities
from .factory import IndicatorFactory
from . import utils

__all__ = [
    "EMA", "RSI", "ATR", "MACD", "MACDResult",
    "BollingerBands", "BollingerResult",
    "DonchianChannel", "DonchianResult",
    "SuperTrend", "SuperTrendResult",
    "VWAP", "VWAPResult",
    "SMA", "ADX", "ADXResult",
    "VolumeAverage",
    "Indicator", "IndicatorResult",
    "IndicatorFactory", "utils",
]
```

**Acceptance Criteria:**
- [ ] All classes importable from `src.core.indicators`
- [ ] No circular imports
- [ ] `__all__` complete

---

### Task 2.2.16: Comprehensive Indicator Tests
**File:** `tests/unit/indicators/`
**Effort:** 4 hours

**Test Files Required:**
```
tests/unit/indicators/
├── conftest.py           # Fixtures: test data, reference values
├── test_ema.py           # EMA with TradingView ref data
├── test_rsi.py           # RSI with Wilder's validation
├── test_atr.py           # ATR with TR values
├── test_macd.py          # MACD with crossover tests
├── test_bollinger.py     # Bollinger with squeeze tests
├── test_donchian.py      # Donchian with breakout tests
├── test_supertrend.py    # SuperTrend with flip tests
├── test_vwap.py          # VWAP with band tests
├── test_adx.py           # ADX with trending/ranging
├── test_sma.py           # SMA basic tests
├── test_volume.py        # Volume with spike tests
├── test_utils.py         # Utility functions
├── test_factory.py       # Factory pattern
└── test_integration.py   # Cross-indicator tests
```

**Reference Data Requirements:**
```python
# conftest.py should provide:
@pytest.fixture
def btc_hourly_data():
    """Real BTC 1H data 2024-01-01 to 2024-02-01."""
    # Load from CSV or hardcoded values
    return OHLCVSeries(...)

@pytest.fixture
def reference_values():
    """TradingView reference values for validation."""
    return {
        "EMA_12": [39210.45, 39215.30, ...],
        "RSI_14": [65.23, 62.18, ...],
        "ATR_14": [425.12, 432.56, ...],
        ...
    }
```

**Test Coverage Requirements:**
- [ ] Each indicator has dedicated test file
- [ ] Tests use real reference data (TradingView, pandas-ta)
- [ ] Edge cases: insufficient data, flat prices, gaps, NaN
- [ ] Performance tests: 10k bars < timeout
- [ ] Integration tests: multiple indicators on same data
- [ ] **Coverage: >90% for all indicator files**

**Key Test Scenarios:**
```python
def test_ema_matches_tradingview():
    """Validate EMA against TradingView reference."""
    # Compare calculated vs reference within 0.0001%

def test_rsi_wilder_smoothing():
    """Verify Wilder's smoothing is used (not simple EMA)."""

def test_atr_true_range_logic():
    """Test all three TR cases."""

def test_macd_crossover_detection():
    """Test bullish and bearish crossovers."""

def test_bollinger_squeeze_percentile():
    """Test squeeze detection at different percentiles."""

def test_adx_trending_vs_ranging():
    """Test trend strength detection."""
```

**Acceptance Criteria:**
- [ ] All 11 indicators have dedicated test files
- [ ] Reference data integrated (conftest.py)
- [ ] >90% code coverage for indicators module
- [ ] All tests pass
- [ ] No performance regressions
- [ ] Edge cases documented and tested

---

## SECTION 2.4: CACHING LAYER (5 Tasks)

### Task 2.4.1: Cache Backend Interface
**File:** `src/data/cache.py`
**Effort:** 1.5 hours

**Classes Required:**
```python
class CacheBackend(ABC):
    """Abstract cache interface."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]: ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool: ...

    @abstractmethod
    async def delete(self, key: str) -> bool: ...

    @abstractmethod
    async def clear(self) -> bool: ...

class InMemoryCache(CacheBackend):
    """In-memory cache with TTL support."""

    def __init__(self):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value, check TTL expiration."""

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value with optional TTL (seconds)."""

    async def cleanup_expired(self) -> None:
        """Remove expired entries (call periodically)."""

    async def size(self) -> int:
        """Return number of entries."""
```

**Acceptance Criteria:**
- [ ] Abstract interface defined correctly
- [ ] In-memory cache with TTL works
- [ ] Async-safe (uses asyncio.Lock)
- [ ] cleanup_expired() works (remove expired)
- [ ] Edge cases: TTL=None (no expiration), TTL=0 (immediate), negative TTL
- [ ] Unit tests: get/set/delete/clear operations
- [ ] Concurrent access tests

---

### Task 2.4.2: Cache Manager
**Add to:** `src/data/cache.py`
**Effort:** 1 hour

**Class Required:**
```python
class CacheManager:
    """High-level cache manager with key generation."""

    def __init__(self, backend: CacheBackend):
        self.backend: CacheBackend = backend

    @staticmethod
    def generate_key(*args: Any, **kwargs: Any) -> str:
        """Generate deterministic cache key (MD5 hash of args/kwargs)."""
        # Key: "cached:{hash}"
        # Must be deterministic (same input = same key)

    async def get(self, key: str) -> Optional[Any]:
        """Get from backend."""

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set in backend."""

    async def delete(self, key: str) -> bool:
        """Delete from backend."""

    async def get_or_set(self, key: str,
                        factory: Callable[[], Awaitable[Any]] | Callable[[], Any],
                        ttl: Optional[int] = None) -> Any:
        """Get or compute if missing (factory can be async or sync)."""
```

**Acceptance Criteria:**
- [ ] Key generation is deterministic
- [ ] Key generation handles complex objects (dict, list)
- [ ] get_or_set works with async factory
- [ ] get_or_set works with sync factory
- [ ] Cache hit/miss behavior correct
- [ ] Unit tests for all methods

---

### Task 2.4.3: OHLCV Caching
**Update:** `src/data/service.py`
**Effort:** 1.5 hours
**Dependency:** Session 1 MarketDataService + CacheManager

**Cache Strategy:**
```python
# TTL by timeframe (seconds)
OHLCV_CACHE_TTLS = {
    "1m": 30,      # 1m data: 30 sec TTL (fresh)
    "5m": 60,      # 5m data: 60 sec TTL
    "15m": 60,
    "30m": 120,
    "1h": 300,     # 1h data: 5 min TTL
    "4h": 900,     # 4h data: 15 min TTL
    "1d": 1800,    # 1d data: 30 min TTL
    "1w": 3600,    # 1w data: 1 hour TTL
}

# Cache key: ohlcv:{symbol}:{timeframe}:{limit}
```

**Updates Required:**
```python
class MarketDataService:
    def __init__(self, fetcher: MarketDataFetcher, cache_mgr: CacheManager):
        self.fetcher = fetcher
        self.cache = cache_mgr

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500,
                       use_cache: bool = True, validate: bool = True) -> OHLCVSeries:
        """Fetch OHLCV with caching."""
        if use_cache:
            key = f"ohlcv:{symbol}:{timeframe}:{limit}"
            cached = await self.cache.get(key)
            if cached is not None:
                return cached

        # Fetch from API
        data = await self.fetcher.get_ohlcv(symbol, timeframe, limit)

        # Validate
        if validate:
            validate_ohlcv(data)

        # Cache with TTL
        if use_cache:
            ttl = OHLCV_CACHE_TTLS.get(timeframe, 300)
            await self.cache.set(key, data, ttl=ttl)

        return data
```

**Acceptance Criteria:**
- [ ] Different TTLs by timeframe
- [ ] Cache key includes all relevant params
- [ ] Cache hit reduces API calls
- [ ] Cache invalidation works (manual delete)
- [ ] Unit tests: caching behavior, TTL expiration
- [ ] Integration tests: concurrent requests (cache collision)
- [ ] Performance: cache hit < 1ms latency

---

### Task 2.4.4: Indicator Caching
**File:** `src/core/indicators/cached.py`
**Effort:** 1.5 hours

**Class Required:**
```python
class CachedIndicatorCalculator:
    """Wraps indicator with caching."""

    def __init__(self, indicator: Indicator, cache_mgr: CacheManager):
        self.indicator: Indicator = indicator
        self.cache: CacheManager = cache_mgr

    async def calculate(self, series: OHLCVSeries) -> IndicatorResult:
        """Calculate indicator with caching."""
        # Key: indicator:{name}:{symbol}:{timeframe}:{params_hash}
        # TTL: matches OHLCV TTL for that timeframe

        key = self._generate_key(series, self.indicator.params)

        # Try cache
        cached = await self.cache.get(key)
        if cached is not None:
            return cached

        # Calculate
        result = await self.indicator.calculate(series)

        # Cache
        ttl = self._get_ttl_for_timeframe(series.timeframe)
        await self.cache.set(key, result, ttl=ttl)

        return result

    def _generate_key(self, series: OHLCVSeries, params: Dict[str, Any]) -> str:
        """Generate cache key from series and params."""

    def _get_ttl_for_timeframe(self, timeframe: str) -> int:
        """Return TTL based on OHLCV timeframe."""
```

**Acceptance Criteria:**
- [ ] Indicator results cached
- [ ] Cache key includes: indicator name, symbol, timeframe, params
- [ ] TTL matches OHLCV TTL
- [ ] Cache invalidation when data updates
- [ ] Unit tests: cache hits, misses
- [ ] Performance: repeated calculation much faster

---

### Task 2.4.5: Cache Tests
**File:** `tests/unit/test_cache.py`
**Effort:** 1.5 hours

**Test Cases Required:**
```python
# Async operations
async def test_cache_get_set():
    """Test basic get/set."""

async def test_cache_ttl_expiration():
    """Test that entries expire after TTL."""

async def test_cache_delete():
    """Test deletion."""

async def test_cache_clear():
    """Test clearing entire cache."""

# Key generation
def test_key_generation_deterministic():
    """Same input always produces same key."""

def test_key_generation_different_params():
    """Different params produce different keys."""

# get_or_set pattern
async def test_get_or_set_sync_factory():
    """Test get_or_set with sync factory."""

async def test_get_or_set_async_factory():
    """Test get_or_set with async factory."""

async def test_get_or_set_factory_not_called_on_hit():
    """Factory not called if value in cache."""

# Concurrent access
async def test_concurrent_access():
    """Multiple tasks accessing same cache."""

async def test_concurrent_get_or_set():
    """Multiple tasks calling get_or_set simultaneously."""

# Integration
async def test_ohlcv_caching():
    """Test caching with real MarketDataService."""

async def test_indicator_caching():
    """Test caching with real indicators."""
```

**Acceptance Criteria:**
- [ ] TTL expiration tested
- [ ] Key generation deterministic
- [ ] Concurrent access safe
- [ ] get_or_set with sync/async factories
- [ ] OHLCV caching integration
- [ ] Indicator caching integration
- [ ] **Coverage: >90% for cache module**

---

## Production Quality Checkpoints

### Before Any Code Submission

**Type Checking:**
```bash
mypy src/core/indicators/ src/data/cache.py --strict
# Must pass with 0 errors
```

**Code Quality:**
```bash
ruff check src/core/indicators/ src/data/cache.py
# Must have 0 violations
```

**Import Organization:**
```bash
isort src/core/indicators/ src/data/cache.py --check
# Must be properly organized
```

**Test Coverage:**
```bash
pytest tests/unit/indicators/ tests/unit/test_cache.py \
  --cov=src/core/indicators --cov=src/data/cache \
  --cov-report=term-missing
# Must be >90%
```

**Production Audit:**
```bash
# Run before final submission
@production-code-audit audit src/core/indicators/ src/data/cache.py
# Must show Grade A- or higher
```

### Decision Consistency Verification

**Before implementing each task:**
```
1. Read .claude/DECISIONS.md
2. Identify relevant decisions:
   - DEC-2026-02-08-002: SQLAlchemy 2.0 (not applicable for indicators)
   - DEC-2026-02-08-003: Timezone-aware datetimes (if any timestamp logic)
   - DEC-2026-02-08-006: Type hints (100% coverage)
   - DEC-2026-02-08-008: Structured logging (for cache operations)
3. Verify implementation matches decision rationale
4. Add decision references in code comments
```

### Reference Data Sources

**For Indicator Validation:**
1. **TradingView** - Use TV charts to capture reference values
2. **pandas-ta** - Python library with reference implementations
3. **TA-Lib** - Industry standard
4. **Manual calculation** - For critical indicators

**Test Data Requirements:**
- Real OHLCV data (not synthetic)
- Multiple assets (BTC, ETH)
- Multiple timeframes (1H, 4H)
- Multiple conditions (trending, ranging, volatile)
- Edge cases (gaps, flash crashes, limit moves)

---

## Session Deliverables

### Code Artifacts
- [ ] `src/core/indicators/base.py` - Base classes
- [ ] `src/core/indicators/ema.py` - EMA indicator
- [ ] `src/core/indicators/rsi.py` - RSI indicator
- [ ] `src/core/indicators/atr.py` - ATR indicator
- [ ] `src/core/indicators/macd.py` - MACD indicator
- [ ] `src/core/indicators/bollinger.py` - Bollinger Bands
- [ ] `src/core/indicators/donchian.py` - Donchian Channels
- [ ] `src/core/indicators/supertrend.py` - SuperTrend
- [ ] `src/core/indicators/vwap.py` - VWAP
- [ ] `src/core/indicators/sma.py` - SMA
- [ ] `src/core/indicators/adx.py` - ADX
- [ ] `src/core/indicators/volume.py` - Volume Average
- [ ] `src/core/indicators/utils.py` - Utilities
- [ ] `src/core/indicators/factory.py` - Factory pattern
- [ ] `src/core/indicators/__init__.py` - Exports
- [ ] `src/data/cache.py` - Cache backend & manager
- [ ] `tests/unit/indicators/` - All test files
- [ ] `tests/unit/test_cache.py` - Cache tests

### Test Coverage
- [ ] >90% coverage for `src/core/indicators/`
- [ ] >90% coverage for `src/data/cache.py`
- [ ] All edge cases tested
- [ ] Reference data validation for each indicator

### Quality Metrics
- [ ] `mypy --strict` passes (0 errors)
- [ ] `ruff check` passes (0 violations)
- [ ] `isort --check` passes (proper imports)
- [ ] `pytest` passes (all tests)
- [ ] `@production-code-audit` shows Grade A-
- [ ] Zero type issues
- [ ] Zero naming inconsistencies

---

## Command Reference

```bash
# Activate venv (ALWAYS FIRST)
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Run all tests
pytest tests/unit/indicators/ tests/unit/test_cache.py -v

# Run with coverage
pytest tests/unit/indicators/ tests/unit/test_cache.py \
  --cov=src/core/indicators --cov=src/data/cache \
  --cov-report=html

# Type checking
mypy src/core/indicators/ src/data/cache.py --strict

# Code quality
ruff check src/core/indicators/ src/data/cache.py

# Import organization
isort src/core/indicators/ src/data/cache.py

# Production audit
@production-code-audit audit src/core/indicators/ src/data/cache.py
```

---

## Session Completion Criteria

✓ All 21 tasks completed (16 indicators + 5 cache)
✓ >90% test coverage
✓ All tests passing
✓ mypy --strict passes
✓ ruff check passes
✓ Reference data validation complete
✓ Production audit: Grade A- or higher
✓ Decision consistency verified
✓ Zero type issues
✓ Zero naming inconsistencies
✓ Import organization perfect
✓ Ready for Session 3 (Risk Controls)
