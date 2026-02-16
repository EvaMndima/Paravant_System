# SESSION 5A VERIFICATION PROMPT
## Template System & Signal Generation Validation
**Duration:** ~8 hours | **Stages:** 4 | **Focus:** Quality & Production Readiness

**Goal:** Verify Session 5A implementation meets production grade standards.

---

## 📋 VERIFICATION STAGES

### STAGE 1: CODE QUALITY & STANDARDS (2 hours)

**Objective:** Ensure all code follows project standards.

#### 1.1 Type Hints Verification
```bash
# Verify 100% type hints
mypy src/core/strategy --strict

# Check coverage
grep -r "def\|async def" src/core/strategy | grep -v ":" | wc -l
# Should be 0 (all functions have type hints)
```

**Checklist:**
- [ ] All functions have type hints (parameters + return)
- [ ] All variables have explicit types in complex code
- [ ] No `Any` type except where justified
- [ ] Generic types used correctly (List[T], Dict[K, V], etc.)
- [ ] Optional types for nullable fields
- [ ] mypy --strict passes

#### 1.2 Code Formatting & Linting
```bash
# Format code
ruff format src/core/strategy

# Check for violations
ruff check src/core/strategy

# Check imports
isort --check-only src/core/strategy
```

**Checklist:**
- [ ] No ruff errors or warnings
- [ ] No isort violations
- [ ] Code follows project style
- [ ] Line length <= 100 chars (where reasonable)
- [ ] Docstrings follow Google style

#### 1.3 Datetime & Timezone Verification
```python
# Search for datetime usage
grep -r "datetime\." src/core/strategy | grep -v "timezone.utc"
# Should show none or justified exceptions

grep -r "utcnow" src/core/strategy
# Should show 0 results (deprecated)
```

**Checklist:**
- [ ] All datetime fields use `timezone.utc`
- [ ] No `datetime.utcnow()` anywhere
- [ ] TimestampMixin applied to all time-tracking models
- [ ] Timezone aware in all comparisons

#### 1.4 Input Validation Verification
```python
# Check for @validates decorators
grep -r "@validates" src/core/strategy
# Should see decorators on numeric/financial fields
```

**Checklist:**
- [ ] All numeric fields have validation
- [ ] NaN checks present: `math.isnan(value)`
- [ ] Infinity checks present: `math.isinf(value)`
- [ ] Range checks (min/max) enforced
- [ ] Type checks enforced
- [ ] Clear error messages for validation failures

#### 1.5 Structured Logging Verification
```python
# Check log format
grep -r "logger\." src/core/strategy
# Should see structured format with named parameters
```

**Checklist:**
- [ ] All logs use structured format (not f-strings)
- [ ] Critical operations logged with full context
- [ ] Log includes relevant IDs (strategy_id, symbol, etc.)
- [ ] Error logs include exception details (exc_info=True)
- [ ] Performance-critical operations tracked

---

### STAGE 2: TEMPLATE SYSTEM VALIDATION (2 hours)

**Objective:** Verify template system works correctly.

#### 2.1 Template Loading
```python
# Test each template loads
import yaml
from src.core.strategy.engine import TemplateManager

mgr = TemplateManager()
for template_id in [
    'ema_trend_rsi',
    'donchian_atr',
    'bb_squeeze_breakout',
    'rsi_bb_mean_reversion',
    'supertrend_volume_macd',
    'macd_pullback',
    'vwap_pullback_volume'
]:
    template = await mgr.load_template(template_id)
    assert template is not None
    assert template.id == template_id
    assert template.parameters is not None
```

**Checklist:**
- [ ] All 7 templates load without errors
- [ ] Template IDs match filenames
- [ ] Required fields present (id, name, parameters, entry_logic, exit_logic)
- [ ] Parameter specs complete (type, min, max, default, step)
- [ ] YAML syntax valid (no parse errors)
- [ ] No duplicate template IDs

#### 2.2 Strategy Creation
```python
# Test strategy creation from each template
async def test_create_from_each_template():
    for template_id in TEMPLATE_IDS:
        strategy = await engine.create_strategy(
            template_id=template_id,
            name=f"Test {template_id}",
            params=template.default_parameters,
            symbols=['BTCUSDT']
        )
        assert strategy is not None
        assert strategy.template_id == template_id
        assert strategy.status == StrategyStatus.DRAFT
```

**Checklist:**
- [ ] Strategy creates for all 7 templates
- [ ] Strategy status is DRAFT initially
- [ ] Parameters validated before creation
- [ ] Database persistence works
- [ ] Unique IDs generated

#### 2.3 Parameter Validation
```python
# Test validation framework
from src.core.strategy.validation import ParameterValidator

# Test valid parameters pass
valid_params = {'fast_ema': 12, 'slow_ema': 26, 'rsi_period': 14}
is_valid, errors = validator.validate(template, valid_params)
assert is_valid is True
assert len(errors) == 0

# Test invalid parameters fail
invalid_params = {'fast_ema': -5, 'slow_ema': 1000}
is_valid, errors = validator.validate(template, invalid_params)
assert is_valid is False
assert len(errors) > 0
```

**Checklist:**
- [ ] Type validation works (int vs float)
- [ ] Min/max bounds enforced
- [ ] Step size validation works
- [ ] Required parameters checked
- [ ] Enum values validated
- [ ] Clear error messages returned
- [ ] All errors collected (not just first)

#### 2.4 Strategy Similarity Check
```python
# Test 70% similarity threshold
from src.core.strategy.similarity import StrategySimilarityChecker

# Create similar strategies
strat1 = await engine.create_strategy(
    template_id='ema_trend_rsi',
    name='EMA 1',
    params={'fast_ema': 12, 'slow_ema': 26},
    symbols=['BTCUSDT']
)

# Identical parameters (should exceed 70%)
strat2_params = strat1.parameters.copy()
similarity_result = await checker.check_similarity(strat1, [strat2_params])
assert similarity_result.is_too_similar is True
assert similarity_result.similarity_pct > 70

# Very different parameters (should be < 70%)
strat3_params = {'fast_ema': 50, 'slow_ema': 200}
similarity_result = await checker.check_similarity(strat3_params, [strat1])
assert similarity_result.is_too_similar is False
assert similarity_result.similarity_pct < 70
```

**Checklist:**
- [ ] Template matching: 40% weight
- [ ] Parameter distance: 30% weight
- [ ] Symbol overlap: 20% weight
- [ ] Entry logic similarity: 10% weight
- [ ] Threshold at 70%
- [ ] Rejects too-similar strategies
- [ ] Explains why similar

#### 2.5 Status Transitions
```python
# Test state machine transitions
strategy = await engine.create_strategy(...)

# Valid: DRAFT → BACKTEST
updated = await engine.transition_status(
    strategy.id,
    StrategyStatus.BACKTEST,
    reason="User initiated backtest"
)
assert updated.status == StrategyStatus.BACKTEST

# Valid: BACKTEST → SIMULATED_PAPER
updated = await engine.transition_status(
    strategy.id,
    StrategyStatus.SIMULATED_PAPER,
    reason="Backtest passed"
)
assert updated.status == StrategyStatus.SIMULATED_PAPER

# Invalid: SIMULATED_PAPER → DRAFT (backward)
with pytest.raises(ValueError):
    await engine.transition_status(strategy.id, StrategyStatus.DRAFT, reason="")
```

**Checklist:**
- [ ] DRAFT → BACKTEST allowed
- [ ] BACKTEST → SIMULATED_PAPER allowed
- [ ] BACKTEST → DRAFT allowed (on fail)
- [ ] SIMULATED_PAPER → LIVE_PAPER allowed
- [ ] LIVE_PAPER → PENDING_APPROVAL allowed
- [ ] PENDING_APPROVAL → LIVE allowed
- [ ] Backward transitions blocked
- [ ] Transitions logged

#### 2.6 Market Regime Manager
```python
# Test regime setting and compatibility
from src.core.strategy.regime import MarketRegimeManager, MarketRegime

regime_mgr = MarketRegimeManager(data_store)

# Set regime
await regime_mgr.set_regime(
    regime=MarketRegime.TRENDING_UP,
    operator="test_user",
    note="Strong uptrend detected"
)

# Check compatibility
strategy = await engine.create_strategy(
    template_id='ema_trend_rsi',
    name='Trend Strategy',
    params={...},
    symbols=['BTCUSDT'],
    preferred_regimes=[MarketRegime.TRENDING_UP]
)

is_compatible, size_multiplier = regime_mgr.check_strategy_compatibility(strategy)
assert is_compatible is True
assert size_multiplier == 1.0

# Test mismatch (50% reduction)
await regime_mgr.set_regime(MarketRegime.VOLATILE, "test", "")
is_compatible, size_multiplier = regime_mgr.check_strategy_compatibility(strategy)
assert is_compatible is True
assert size_multiplier == 0.5  # 50% reduction

# Test avoid regime (blocks trading)
strategy_avoid = await engine.create_strategy(
    template_id='ema_trend_rsi',
    name='Conservative',
    params={...},
    symbols=['BTCUSDT'],
    avoid_regimes=[MarketRegime.VOLATILE]
)

is_compatible, size_multiplier = regime_mgr.check_strategy_compatibility(strategy_avoid)
assert is_compatible is False
assert size_multiplier == 0.0
```

**Checklist:**
- [ ] 5 regimes defined (trending_up, trending_down, ranging, volatile, unknown)
- [ ] Operator can set regime
- [ ] Changes logged with timestamp
- [ ] Strategies can define preferred_regimes
- [ ] Strategies can define avoid_regimes
- [ ] 50% size reduction on mismatch
- [ ] Trading blocked on avoid regime
- [ ] Regime persists across restarts

---

### STAGE 3: SIGNAL GENERATION VALIDATION (2 hours)

**Objective:** Verify signal generators work correctly.

#### 3.1 Signal Interface
```python
# Test Signal dataclass
from src.core.strategy.signals import Signal, SignalType

signal = Signal(
    type=SignalType.LONG_ENTRY,
    symbol='BTCUSDT',
    strategy_id='test-strat-1',
    timestamp=datetime.now(timezone.utc),
    price=45000.0,
    stop_loss=44000.0,
    take_profit=46000.0,
    confidence=0.95,
    metadata={'reason': 'EMA crossover'}
)

# Verify required fields
assert signal.type == SignalType.LONG_ENTRY
assert signal.timestamp.tzinfo == timezone.utc
assert not math.isnan(signal.price)
assert not math.isinf(signal.price)
```

**Checklist:**
- [ ] Signal dataclass complete
- [ ] All required fields present
- [ ] Timestamp timezone-aware (UTC)
- [ ] Price validation (no NaN/Infinity)
- [ ] Metadata optional with default
- [ ] Confidence between 0-1 if set
- [ ] NO_SIGNAL type works correctly

#### 3.2 Signal Generator Factory
```python
# Test factory creates correct generators
from src.core.strategy.signals import SignalGeneratorFactory

factory = SignalGeneratorFactory()

generators = {
    'ema_trend_rsi': 'EMATrendRSIGenerator',
    'donchian_atr': 'DonchianATRGenerator',
    'bb_squeeze_breakout': 'BBSqueezeGenerator',
    'rsi_bb_mean_reversion': 'RSIBBMeanReversionGenerator',
    'supertrend_volume_macd': 'SuperTrendGenerator',
    'macd_pullback': 'MACDPullbackGenerator',
    'vwap_pullback_volume': 'VWAPPullbackGenerator',
}

for template_id, expected_class in generators.items():
    gen = factory.create(template_id)
    assert gen is not None
    assert expected_class in str(type(gen))
```

**Checklist:**
- [ ] All 7 generators registered
- [ ] Factory creates by template ID
- [ ] Each generator is SignalGenerator subclass
- [ ] Generator initialization works
- [ ] Factory raises on unknown ID

#### 3.3 Entry Signal Detection
```python
# Test entry signals generated correctly
# (Example: EMA Trend + RSI Generator)

generator = factory.create('ema_trend_rsi')

# Create test data: EMA uptrend, RSI in middle range
test_data = pd.DataFrame({
    'open': [45000, 45100, 45200, 45250, 45300],
    'high': [45100, 45150, 45250, 45300, 45350],
    'low': [44950, 45050, 45150, 45200, 45250],
    'close': [45050, 45120, 45220, 45270, 45320],
    'volume': [1000, 1100, 1200, 1100, 1000]
})

signal = await generator.generate_signal(
    strategy=strategy,
    symbol='BTCUSDT',
    data=test_data
)

# Entry should be generated
assert signal.type in [SignalType.LONG_ENTRY, SignalType.NO_SIGNAL]

# If entry, validate stop/profit
if signal.type == SignalType.LONG_ENTRY:
    assert signal.stop_loss < signal.price
    assert signal.take_profit > signal.price
    assert signal.confidence > 0
```

**Checklist:**
- [ ] Entry signals generated when conditions met
- [ ] Stop loss below entry (for long)
- [ ] Take profit above entry (for long)
- [ ] NO_SIGNAL when conditions not met
- [ ] Timestamp timezone-aware
- [ ] Price validation present
- [ ] All 7 generators generate signals

#### 3.4 Exit Signal Detection
```python
# Test exit signals after entry
# Signals should respect entry conditions

# Create trend reversal data (EMA downtrend)
test_data = pd.DataFrame({
    'close': [45300, 45250, 45200, 45150, 45100],  # Downtrend
    'volume': [1000, 1100, 1200, 1100, 1000]
})

signal = await generator.generate_signal(
    strategy=strategy,
    symbol='BTCUSDT',
    data=test_data
)

# Should generate exit signal
assert signal.type in [SignalType.LONG_EXIT, SignalType.NO_SIGNAL]
```

**Checklist:**
- [ ] Exit signals generated when reversals occur
- [ ] Exit signals generated at take profit
- [ ] Exit signals generated at stop loss
- [ ] Exit signals generated on time exit
- [ ] NO_SIGNAL when trend continues
- [ ] All generators implement exit logic

#### 3.5 Edge Cases
```python
# Test NO_SIGNAL conditions
signal = await generator.generate_signal(
    strategy=strategy,
    symbol='BTCUSDT',
    data=minimal_data  # Only 1-2 bars
)
assert signal.type == SignalType.NO_SIGNAL

# Test extreme prices
test_data.loc[0, 'close'] = 1000000  # Extreme
signal = await generator.generate_signal(
    strategy=strategy,
    symbol='BTCUSDT',
    data=test_data
)
# Should handle without error
assert signal is not None
```

**Checklist:**
- [ ] Handles insufficient data (NO_SIGNAL)
- [ ] Handles extreme prices
- [ ] Handles missing data
- [ ] Handles zero volume
- [ ] Handles NaN gracefully
- [ ] No exceptions during normal operation

---

### STAGE 4: INTEGRATION & COMPLETENESS (2 hours)

**Objective:** Verify all components work together.

#### 4.1 API Endpoints
```bash
# Test template endpoints
curl -X GET http://localhost:8000/api/templates
curl -X GET http://localhost:8000/api/templates/ema_trend_rsi

# Test strategy endpoints
curl -X POST http://localhost:8000/api/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "ema_trend_rsi",
    "name": "My Strategy",
    "parameters": {"fast_ema": 12, "slow_ema": 26},
    "symbols": ["BTCUSDT"]
  }'

# Get strategy
curl -X GET http://localhost:8000/api/strategies/{id}

# Update strategy
curl -X PUT http://localhost:8000/api/strategies/{id} \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"fast_ema": 14}}'

# Change status
curl -X PUT http://localhost:8000/api/strategies/{id}/status \
  -H "Content-Type: application/json" \
  -d '{"status": "BACKTEST", "reason": "User initiated"}'
```

**Checklist:**
- [ ] GET /api/templates returns all 7
- [ ] GET /api/templates/{id} returns template
- [ ] POST /api/strategies creates strategy
- [ ] GET /api/strategies lists strategies
- [ ] GET /api/strategies/{id} retrieves
- [ ] PUT /api/strategies/{id} updates
- [ ] PUT /api/strategies/{id}/status transitions
- [ ] DELETE /api/strategies/{id} retires

#### 4.2 Database Persistence
```python
# Verify database operations
from src.data.database import get_session

async with get_session() as session:
    # Create strategy via API
    strategy = await engine.create_strategy(...)

    # Retrieve from database
    retrieved = await session.query(Strategy).filter_by(id=strategy.id).first()
    assert retrieved is not None
    assert retrieved.template_id == strategy.template_id

    # Update
    retrieved.parameters = {'fast_ema': 14}
    await session.commit()

    # Verify update persisted
    refreshed = await session.query(Strategy).filter_by(id=strategy.id).first()
    assert refreshed.parameters['fast_ema'] == 14
```

**Checklist:**
- [ ] Strategies persist to database
- [ ] Parameters stored correctly
- [ ] Status changes persisted
- [ ] Timestamps recorded
- [ ] No N+1 queries
- [ ] Foreign key constraints enforced
- [ ] Data integrity maintained

#### 4.3 Test Coverage
```bash
# Run tests with coverage
pytest tests/unit/strategy/ --cov=src/core/strategy --cov-report=term-missing

# Expected output:
# src/core/strategy/engine.py: 92%
# src/core/strategy/signals.py: 88%
# src/core/strategy/generators/*: >85%
# src/core/strategy/regime.py: 90%
```

**Checklist:**
- [ ] >85% coverage for all modules
- [ ] Critical paths 100% coverage
- [ ] Edge cases tested
- [ ] Error paths tested
- [ ] Integration paths tested
- [ ] Test count reasonable (not over-tested)

#### 4.4 Documentation & Comments
```python
# Verify docstrings
# Each class/function should have Google-style docstring

class StrategyEngine:
    """Central strategy management component.

    Responsibilities:
    - Create strategies from templates
    - Manage strategy lifecycle
    - Validate parameters
    - Check strategy similarity

    Example:
        engine = StrategyEngine(...)
        strategy = await engine.create_strategy(...)
    """

    async def create_strategy(
        self,
        template_id: str,
        name: str,
        params: Dict[str, Any],
        symbols: List[str],
        preferred_regimes: List[str] = None,
        avoid_regimes: List[str] = None
    ) -> Strategy:
        """Create new strategy from template.

        Args:
            template_id: Template to use
            name: Human-readable strategy name
            params: Parameter values
            symbols: Trading symbols
            preferred_regimes: Optional regime preferences
            avoid_regimes: Optional regime avoidances

        Returns:
            Created Strategy object

        Raises:
            ValueError: If parameters invalid or template not found
            StrategyLimitError: If too many similar strategies exist
        """
```

**Checklist:**
- [ ] All classes have docstrings
- [ ] All public methods have docstrings
- [ ] Docstrings describe purpose and behavior
- [ ] Args and Returns documented
- [ ] Raises documented
- [ ] Examples provided where helpful
- [ ] Comments explain why, not what
- [ ] No commented-out code

---

## 🔍 DEBUGGING GUIDE: COMMON FAILURES & SOLUTIONS

### Issue: Template Not Loading

**Symptom:**
```
FileNotFoundError: config/templates/ema_trend_rsi.yaml not found
```

**Root Causes:**
1. YAML files not created in correct location
2. File permissions issue
3. Relative path incorrect

**Solution:**
```bash
# Verify files exist
ls -la config/templates/
# Should show all 7 templates

# Check file permissions
chmod 644 config/templates/*.yaml

# Verify from correct directory
cd /path/to/paravant_system
python -c "from src.core.strategy.engine import TemplateManager; \
           mgr = TemplateManager(); \
           print(mgr.list_templates())"
```

---

### Issue: Parameter Validation Always Fails

**Symptom:**
```
ValueError: fast_ema must be in range [5, 50] but got 12
```

**Root Cause:**
- Template min/max values incorrectly defined
- Validator checking against wrong bounds

**Solution:**
```python
# Check template definition
template = await template_manager.load_template('ema_trend_rsi')
print(template.parameters['fast_ema'])
# Should show: {'type': 'int', 'min': 5, 'max': 50, 'default': 12, 'step': 1}

# Check validator logic
from src.core.strategy.validation import ParameterValidator
validator = ParameterValidator()
is_valid, errors = validator.validate(template, {'fast_ema': 12})
print(errors)  # Should be empty
```

---

### Issue: Similarity Check Always Rejects

**Symptom:**
```
Strategy too similar to existing_id (87% similar)
```

**Root Cause:**
- Threshold too low (should be 70%)
- Weight calculations incorrect
- Comparing against wrong strategies

**Solution:**
```python
# Check threshold
from src.core.strategy.similarity import StrategySimilarityChecker
checker = StrategySimilarityChecker(data_store)
print(checker.SIMILARITY_THRESHOLD)  # Should be 0.70

# Check weights
print(checker.WEIGHTS)
# Should be: {'template': 0.40, 'parameters': 0.30, 'symbols': 0.20, 'entry_logic': 0.10}

# Manual calculation
new_strat = await engine.create_strategy(...)
result = await checker.check_similarity(new_strat, [existing])
print(result.breakdown)  # Verify component scores
print(f"Total: {sum(result.breakdown.values())}")  # Should show calculation
```

---

### Issue: Signal Generator Returns Wrong Type

**Symptom:**
```
AssertionError: Expected SignalType.LONG_ENTRY but got SignalType.NO_SIGNAL
```

**Root Causes:**
1. OHLCV data insufficient (< lookback bars)
2. Indicator calculation missing
3. Entry conditions too strict

**Solution:**
```python
# Verify data length
data = test_ohlcv_data
print(f"Data length: {len(data)} bars")
# Should be > lookback_period (usually 20-200)

# Manually check indicator
fast_ema = data['close'].ewm(span=12).mean()
slow_ema = data['close'].ewm(span=26).mean()
latest_fast = fast_ema.iloc[-1]
latest_slow = slow_ema.iloc[-1]
print(f"Fast EMA: {latest_fast}, Slow EMA: {latest_slow}")
# Should show trend (one > other)

# Generate with debug info
signal = await generator.generate_signal(strategy, 'BTCUSDT', data)
print(f"Signal type: {signal.type}")
print(f"Signal metadata: {signal.metadata}")
# Metadata should show why signal was/wasn't generated
```

---

### Issue: Status Transition Blocked Incorrectly

**Symptom:**
```
ValueError: Invalid transition from DRAFT to BACKTEST
```

**Root Cause:**
- Valid transition not in VALID_TRANSITIONS dict
- Strategy status not updated in database

**Solution:**
```python
# Check valid transitions
from src.core.strategy.lifecycle import VALID_TRANSITIONS
print(VALID_TRANSITIONS)
# Should show: DRAFT → [BACKTEST]

# Verify current status
strategy = await engine.get_strategy(strategy_id)
print(f"Current status: {strategy.status}")

# Check if transition in valid list
from_state = StrategyStatus.DRAFT
to_state = StrategyStatus.BACKTEST
if to_state not in VALID_TRANSITIONS.get(from_state, []):
    print("Transition not valid")
```

---

### Issue: Regime Manager Not Persisting

**Symptom:**
```
AssertantionError: Current regime is UNKNOWN (expected TRENDING_UP)
```

**Root Cause:**
- set_regime() not persisting to database
- load_from_database() not called on startup

**Solution:**
```python
# Verify database persistence
regime_mgr = MarketRegimeManager(data_store)

# Set regime
await regime_mgr.set_regime(
    regime=MarketRegime.TRENDING_UP,
    operator="test",
    note="test"
)

# Check database
regime_state = await data_store.get_system_state('market_regime')
print(f"Stored regime: {regime_state}")
# Should show: trending_up

# Load and verify
regime_mgr2 = MarketRegimeManager(data_store)
await regime_mgr2.load_from_database()
print(f"Loaded regime: {regime_mgr2.get_current_regime()}")
# Should show: MarketRegime.TRENDING_UP
```

---

## ✅ SIGN-OFF CHECKLIST

**Code Quality:**
- [ ] mypy --strict passes
- [ ] ruff check passes
- [ ] isort check passes
- [ ] No commented-out code
- [ ] All docstrings present
- [ ] Type hints 100%

**Functionality:**
- [ ] All 7 templates load
- [ ] Strategies create from templates
- [ ] Parameters validated correctly
- [ ] Similarity check works (70% threshold)
- [ ] Status transitions enforced
- [ ] Regime manager works
- [ ] All signals generate correctly
- [ ] Factory creates all 7 generators

**Database:**
- [ ] Data persists correctly
- [ ] Foreign keys enforced
- [ ] No N+1 queries
- [ ] Migrations run successfully

**Testing:**
- [ ] >85% coverage
- [ ] All critical paths tested
- [ ] Edge cases tested
- [ ] Error paths tested
- [ ] Integration tests pass

**Documentation:**
- [ ] All classes documented
- [ ] All methods documented
- [ ] Comments explain decisions
- [ ] README updated with examples

**API:**
- [ ] All endpoints functional
- [ ] Request validation works
- [ ] Response format correct
- [ ] Error responses clear

---

**Sign-off:** _________________ **Date:** _________________ **Grade:** _________

---

**Last Updated:** 2026-02-14
**Status:** Ready for validation
**Next Step:** Run validation against Session 5A implementation
