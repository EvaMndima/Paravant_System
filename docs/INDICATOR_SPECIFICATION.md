# INDICATOR SPECIFICATION
## Technical Indicators for MVP - Paravant Trading System

**Document Version:** 1.0  
**Created:** 2026-02-07  
**Status:** LOCKED FOR MVP  
**Companion Documents:** `TRADING_SYSTEM_PRD.md`, `ARCHITECTURE.md`

---

## ⚠️ MVP SCOPE LOCK

**CRITICAL:** The following 12 indicators are the **ONLY** indicators allowed for MVP development.

**DO NOT:**
- Add new indicators not on this list
- Suggest alternative indicators
- Implement "better" indicators
- Add indicators from strategy templates not in MVP scope

**Any request to add indicators must be:**
1. Explicitly approved by user
2. Documented as scope change
3. Added to V1/V2 roadmap (NOT MVP)

---

## 📊 LOCKED INDICATORS (12 Total)

### 1. SMA (Simple Moving Average)

**Formula:**
```
SMA = Sum(Close, period) / period
```

**Parameters:**
- `period`: integer (5-200)
  - Default: varies by template
  - Simple_MA: 20/50
  - Donchian_BB: 20/55

**Usage:**
- Trend identification
- Support/resistance levels
- Crossover signals

**Test Data:**
- BTCUSDT 1h, 2024-01-01 to 2024-01-31
- Known values for SMA(20) validation
- Must match TradingView SMA calculations

---

### 2. EMA (Exponential Moving Average)

**Formula:**
```
multiplier = 2 / (period + 1)
EMA = (Close - EMA_prev) * multiplier + EMA_prev
```

**Parameters:**
- `period`: integer (5-200)
  - Default: varies by template
  - Simple_MA: 12/26

**Usage:**
- Trend-following
- More responsive than SMA
- Used in MACD calculation

**Test Data:**
- BTCUSDT 1h, 2024-01-01 to 2024-01-31
- First EMA value = SMA of same period
- Must match TradingView EMA calculations

---

### 3. RSI (Relative Strength Index)

**Formula:**
```
RS = Average Gain / Average Loss
RSI = 100 - (100 / (1 + RS))
```

**Parameters:**
- `period`: integer (2-50)
  - Default: 14

**Usage:**
- Overbought (>70) / Oversold (<30)
- Divergence detection
- Momentum measurement

**Test Data:**
- BTCUSDT 1h, 2024-01-01 to 2024-01-31
- Known RSI(14) values for validation
- Must match TradingView RSI calculations

---

### 4. MACD (Moving Average Convergence Divergence)

**Formula:**
```
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(MACD Line, 9)
Histogram = MACD Line - Signal Line
```

**Parameters:**
- `fast_period`: integer (default: 12)
- `slow_period`: integer (default: 26)
- `signal_period`: integer (default: 9)

**Usage:**
- Trend direction
- Momentum strength
- Signal line crossovers

**Test Data:**
- BTCUSDT 1h, 2024-01-01 to 2024-01-31
- Known MACD values for validation
- Must match TradingView MACD calculations

---

### 5. Bollinger Bands

**Formula:**
```
Middle Band = SMA(Close, period)
Upper Band = Middle Band + (stddev * multiplier)
Lower Band = Middle Band - (stddev * multiplier)
```

**Parameters:**
- `period`: integer (default: 20)
- `stddev_multiplier`: float (default: 2.0)

**Usage:**
- Volatility measurement
- Overbought/oversold zones
- Squeeze detection

**Test Data:**
- BTCUSDT 1h, 2024-01-01 to 2024-01-31
- Known BB(20, 2.0) values for validation
- Must match TradingView BB calculations

---

### 6. ATR (Average True Range)

**Formula:**
```
True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
ATR = SMA(True Range, period)
```

**Parameters:**
- `period`: integer (default: 14)

**Usage:**
- Volatility measurement
- Stop-loss calculation
- Position sizing

**Test Data:**
- BTCUSDT 1h, 2024-01-01 to 2024-01-31
- Known ATR(14) values for validation
- Must match TradingView ATR calculations

---

### 7. Donchian Channel

**Formula:**
```
Upper Band = Highest(High, period)
Lower Band = Lowest(Low, period)
Middle Band = (Upper Band + Lower Band) / 2
```

**Parameters:**
- `period`: integer (default: 20)

**Usage:**
- Breakout detection
- Support/resistance
- Trend identification

**Test Data:**
- BTCUSDT 1h, 2024-01-01 to 2024-01-31
- Known Donchian(20) values for validation
- Must match TradingView Donchian calculations

---

### 8. ADX (Average Directional Index)

**Formula:**
```
+DM = High - Prev High (if positive, else 0)
-DM = Prev Low - Low (if positive, else 0)
+DI = 100 * SMA(+DM, period) / ATR
-DI = 100 * SMA(-DM, period) / ATR
DX = 100 * abs(+DI - -DI) / (+DI + -DI)
ADX = SMA(DX, period)
```

**Parameters:**
- `period`: integer (default: 14)

**Usage:**
- Trend strength (not direction)
- Filter weak trends (<20)
- Strong trends (>25)

**Test Data:**
- BTCUSDT 1h, 2024-01-01 to 2024-01-31
- Known ADX(14) values for validation
- Must match TradingView ADX calculations

---

### 9. Volume SMA

**Formula:**
```
Volume SMA = Sum(Volume, period) / period
```

**Parameters:**
- `period`: integer (default: 20)

**Usage:**
- Volume confirmation
- Breakout validation
- Divergence detection

**Test Data:**
- BTCUSDT 1h, 2024-01-01 to 2024-01-31
- Known Volume SMA(20) values for validation
- Must match TradingView Volume SMA calculations

---

### 10. Stochastic RSI

**Formula:**
```
StochRSI = (RSI - Lowest(RSI, period)) / (Highest(RSI, period) - Lowest(RSI, period))
%K = SMA(StochRSI, k_period)
%D = SMA(%K, d_period)
```

**Parameters:**
- `rsi_period`: integer (default: 14)
- `stoch_period`: integer (default: 14)
- `k_period`: integer (default: 3)
- `d_period`: integer (default: 3)

**Usage:**
- Overbought/oversold
- More sensitive than RSI
- Crossover signals

**Test Data:**
- BTCUSDT 1h, 2024-01-01 to 2024-01-31
- Known StochRSI values for validation
- Must match TradingView StochRSI calculations

---

### 11. VWAP (Volume-Weighted Average Price)

**Formula:**
```
Typical Price = (High + Low + Close) / 3
VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)
```

**Parameters:**
- `anchor`: string (default: "session")
  - Options: "session", "week", "month"

**Usage:**
- Institutional price levels
- Fair value reference
- Trend bias

**Test Data:**
- BTCUSDT 1h, 2024-01-01 to 2024-01-31
- Known VWAP values for validation
- Must match TradingView VWAP calculations

---

### 12. Linear Regression

**Formula:**
```
slope = covariance(Close, index) / variance(index)
intercept = mean(Close) - slope * mean(index)
value = slope * current_index + intercept
```

**Parameters:**
- `period`: integer (default: 100)

**Usage:**
- Trend line calculation
- Price deviation
- Mean reversion

**Test Data:**
- BTCUSDT 1h, 2024-01-01 to 2024-01-31
- Known Linear Regression values for validation
- Must match TradingView Linear Regression calculations

---

## 🏗️ IMPLEMENTATION REQUIREMENTS

### Code Structure

```python
# /src/indicators/base.py
class IndicatorBase:
    """Base class for all indicators"""
    
    def __init__(self, params: dict):
        self.params = params
        self.validate_params()
    
    def validate_params(self):
        """Validate parameters against spec"""
        raise NotImplementedError
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """Calculate indicator values"""
        raise NotImplementedError
    
    def get_metadata(self) -> dict:
        """Return indicator metadata"""
        return {
            "name": self.__class__.__name__,
            "params": self.params,
            "version": "1.0"
        }
```

### Naming Convention

- Class name: `{IndicatorName}Indicator` (e.g., `SMAIndicator`)
- File name: `{indicator_name}.py` (e.g., `sma.py`)
- Test file: `test_{indicator_name}.py` (e.g., `test_sma.py`)

---

## 🧪 TESTING REQUIREMENTS

### Unit Tests

Each indicator MUST have:

1. **Parameter Validation Test**
   - Valid parameters accepted
   - Invalid parameters rejected
   - Edge cases handled

2. **Known Values Test**
   - Compare with TradingView calculations
   - Use test data from `/tests/data/indicators/`
   - Tolerance: 0.01% for floating point

3. **Edge Case Tests**
   - Not enough data
   - NaN values in data
   - Zero values
   - Negative values (where applicable)

### Integration Tests

1. **Strategy Integration**
   - Used in at least one MVP template
   - Correctly integrated with signal generation

2. **Performance Test**
   - 10,000 candles < 100ms calculation time
   - Memory usage reasonable

---

## 📝 DOCUMENTATION REQUIREMENTS

Each indicator file MUST include:

```python
"""
{Indicator Name}

Formula:
    {mathematical formula}

Parameters:
    - param1: type (range, default: value)
    - param2: type (range, default: value)

Usage:
    - Primary use case
    - Secondary use case

Example:
    >>> indicator = {IndicatorName}Indicator(period=20)
    >>> result = indicator.calculate(data)

Test Data:
    - Location: /tests/data/indicators/{indicator_name}/
    - Source: TradingView, BTCUSDT 1h, 2024-01-01 to 2024-01-31
"""
```

---

## 🚫 ANTI-SCOPE-CREEP RULES

### ❌ FORBIDDEN During MVP

1. **Adding New Indicators**
   - "I found a better RSI variant"
   - "Let's add Ichimoku Cloud"
   - "What about adding Fibonacci?"

2. **Customizing Formulas**
   - "Let's use EMA instead of SMA in Bollinger Bands"
   - "What if we modify RSI formula?"
   - "Let's add a smoothing factor"

3. **Adding Features**
   - "Let's add divergence detection to RSI"
   - "What about adding squeeze detection to BB?"
   - "Let's add color coding"

### ✅ ALLOWED During MVP

1. **Bug Fixes**
   - Calculation errors
   - Parameter validation issues
   - Performance problems

2. **Documentation**
   - Clarifying formulas
   - Adding examples
   - Improving comments

3. **Testing**
   - More test cases
   - Better edge case coverage
   - Performance benchmarks

---

## 📦 DEPENDENCIES

**Required Libraries:**
- `pandas >= 2.0.0`
- `numpy >= 1.24.0`
- `ta-lib >= 0.4.28` (optional, for validation only)

**DO NOT:**
- Introduce new indicator libraries
- Use third-party indicator implementations
- Add plotting dependencies

---

## 🔄 V1/V2 INDICATOR ROADMAP

**V1 Additions (Post-MVP):**
- Ichimoku Cloud
- Parabolic SAR
- Keltner Channels
- SuperTrend

**V2 Additions:**
- Custom indicators
- User-defined formulas
- Indicator combinations

**IMPORTANT:** These are NOT in MVP scope. Do not implement.

---

## ✅ ACCEPTANCE CRITERIA

An indicator is COMPLETE when:

1. ✅ Implementation matches formula exactly
2. ✅ All unit tests pass
3. ✅ Integration tests pass
4. ✅ Performance tests pass
5. ✅ Documentation complete
6. ✅ Test data validated against TradingView
7. ✅ Code review approved
8. ✅ Used in at least one strategy template

---

## 📞 SCOPE CHANGE PROCESS

If a new indicator is absolutely necessary:

1. **Document Justification**
   - Why is it needed?
   - What problem does it solve?
   - Can existing indicators solve this?

2. **User Approval Required**
   - User must explicitly approve
   - Document as scope change
   - Update MVP timeline

3. **Add to Roadmap**
   - V1 or V2 (NOT MVP)
   - Document dependencies
   - Estimate effort

---

**End of Document**
