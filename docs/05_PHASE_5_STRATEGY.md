# PHASE 5: STRATEGY
## Weeks 9-10 | 40 Tasks | ~88 Hours

**Goal:** All 7 templates working with backtest and paper trading validation.

**Start Conditions:** Phase 4 complete (execution working)  
**Exit Conditions:** All templates generate signals, backtests deterministic, paper trading validates strategies

---

## 📊 PHASE 5 PROGRESS

```
Section 5.1 Template System   [░░░░░░░░░░] 0/10 tasks
Section 5.2 Signal Generation [░░░░░░░░░░] 0/10 tasks
Section 5.3 Backtest Engine   [░░░░░░░░░░] 0/10 tasks
Section 5.4 Paper Trading     [░░░░░░░░░░] 0/10 tasks
───────────────────────────────────────────────────
PHASE 5 TOTAL                 [░░░░░░░░░░] 0/40 tasks
```

---

## SECTION 5.1: TEMPLATE SYSTEM
*Estimated: 16 hours*

### Task 5.1.1: Create Strategy Engine Core
- [ ] **Status:** Not Started
- **Description:** Central strategy management component
- **Dependencies:** [1.3.3, 1.2.3]
- **Effort:** 2.5 hours

**File:** `src/core/strategy/engine.py`

**StrategyEngine class:**
```python
class StrategyEngine:
    def __init__(
        self,
        template_manager: TemplateManager,
        data_store: DataStore,
        market_data: MarketDataService
    ):
        self.templates = template_manager
        self.data_store = data_store
        self.market_data = market_data
    
    async def create_strategy(
        self,
        template_id: str,
        name: str,
        params: Dict,
        symbols: List[str]
    ) -> Strategy:
        """Create a new strategy from template."""
        pass
    
    async def get_strategy(self, strategy_id: str) -> Strategy:
        pass
    
    async def update_strategy_params(self, strategy_id: str, params: Dict) -> Strategy:
        pass
    
    async def set_strategy_status(self, strategy_id: str, status: StrategyStatus) -> Strategy:
        pass
```

**Acceptance Criteria:**
- [ ] Creates strategy from template
- [ ] Validates parameters against template
- [ ] Persists to database
- [ ] Unit test: strategy creation

---

### Task 5.1.2: Implement Parameter Validation
- [ ] **Status:** Not Started
- **Description:** Validate strategy parameters against template specs
- **Dependencies:** [5.1.1, 1.3.3]
- **Effort:** 2 hours

**Add to:** `src/core/strategy/engine.py`

**Method:** `validate_parameters(template: StrategyTemplate, params: Dict) -> List[str]`

**Validations:**
- Required parameters present
- Values within min/max bounds
- Values match step size (e.g., 0.5 step means 1.0, 1.5, 2.0 valid)
- Enum values in choices list
- Type checking (int vs float vs bool)

**Acceptance Criteria:**
- [ ] All validation rules enforced
- [ ] Clear error messages
- [ ] Returns all errors (not just first)
- [ ] Unit test: validation scenarios

---

### Task 5.1.2a: Implement Strategy Similarity Check
- [ ] **Status:** Not Started
- **Description:** Reject strategies too similar to existing ones per PRD Feature D
- **Dependencies:** [5.1.2]
- **Effort:** 2.5 hours

**Add to:** `src/core/strategy/engine.py`

**StrategySimilarityChecker class:**
```python
@dataclass
class SimilarityResult:
    is_too_similar: bool
    similarity_pct: float
    most_similar_strategy_id: Optional[str]
    breakdown: Dict[str, float]  # template, params, symbols, logic

class StrategySimilarityChecker:
    """
    Reject strategies too similar to existing ones per PRD Feature D.
    
    Similarity scoring:
    - Same template type: +40%
    - Parameter distance < 20% normalized: +30%
    - Symbol overlap > 50%: +20%
    - Same entry conditions: +10%
    
    Threshold: Reject if > 70% similar
    """
    
    SIMILARITY_THRESHOLD = 0.70
    
    WEIGHTS = {
        'template': 0.40,
        'parameters': 0.30,
        'symbols': 0.20,
        'entry_logic': 0.10
    }
    
    def __init__(self, data_store):
        self.data_store = data_store
    
    async def check_similarity(
        self, 
        new_strategy: Strategy,
        existing_strategies: List[Strategy] = None
    ) -> SimilarityResult:
        """Check if new strategy is too similar to existing active strategies."""
        
        if existing_strategies is None:
            existing_strategies = await self.data_store.get_active_strategies()
        
        max_similarity = 0.0
        most_similar_id = None
        best_breakdown = {}
        
        for existing in existing_strategies:
            similarity, breakdown = self._calculate_similarity(new_strategy, existing)
            
            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_id = existing.id
                best_breakdown = breakdown
        
        return SimilarityResult(
            is_too_similar=max_similarity > self.SIMILARITY_THRESHOLD,
            similarity_pct=max_similarity * 100,
            most_similar_strategy_id=most_similar_id,
            breakdown=best_breakdown
        )
    
    def _calculate_similarity(
        self, 
        new: Strategy, 
        existing: Strategy
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate similarity score between two strategies."""
        breakdown = {}
        
        # Template type similarity (40%)
        if new.template_id == existing.template_id:
            breakdown['template'] = self.WEIGHTS['template']
        else:
            breakdown['template'] = 0.0
        
        # Parameter distance (30%)
        param_similarity = self._calculate_parameter_similarity(
            new.parameters, existing.parameters
        )
        if param_similarity > 0.80:  # Parameters within 20%
            breakdown['parameters'] = self.WEIGHTS['parameters']
        else:
            breakdown['parameters'] = param_similarity * self.WEIGHTS['parameters']
        
        # Symbol overlap (20%)
        symbol_overlap = self._calculate_symbol_overlap(new.symbols, existing.symbols)
        if symbol_overlap > 0.50:  # More than 50% overlap
            breakdown['symbols'] = self.WEIGHTS['symbols']
        else:
            breakdown['symbols'] = symbol_overlap * self.WEIGHTS['symbols']
        
        # Entry logic similarity (10%)
        if self._same_entry_conditions(new, existing):
            breakdown['entry_logic'] = self.WEIGHTS['entry_logic']
        else:
            breakdown['entry_logic'] = 0.0
        
        total = sum(breakdown.values())
        return total, breakdown
    
    def _calculate_parameter_similarity(self, params1: Dict, params2: Dict) -> float:
        """Calculate normalized parameter distance."""
        # Returns 1.0 if identical, 0.0 if completely different
        pass
    
    def _calculate_symbol_overlap(self, symbols1: List[str], symbols2: List[str]) -> float:
        """Calculate percentage of symbol overlap."""
        set1 = set(symbols1)
        set2 = set(symbols2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    def _same_entry_conditions(self, s1: Strategy, s2: Strategy) -> bool:
        """Check if strategies have same entry conditions."""
        # Compare entry logic definitions
        pass
```

**Integration:** Call during strategy creation, reject with explanation if > 70% similar

**Acceptance Criteria:**
- [ ] Template type adds 40% if same
- [ ] Parameter distance adds up to 30% if within 20%
- [ ] Symbol overlap adds up to 20% if > 50%
- [ ] Entry logic adds 10% if same
- [ ] Rejects strategy if total similarity > 70%
- [ ] Rejection includes explanation of why too similar
- [ ] Compares against all active strategies
- [ ] Unit test: similarity calculation
- [ ] Unit test: rejection scenarios

---

### Task 5.1.3: Implement Strategy Status Transitions
- [ ] **Status:** Not Started
- **Description:** Manage strategy lifecycle states
- **Dependencies:** [5.1.1]
- **Effort:** 2 hours

**Add to:** `src/core/strategy/engine.py`

**Valid transitions (from PRD 3.3.4):**
```
DRAFT → BACKTEST
BACKTEST → SIMULATED_PAPER (if backtest passes)
BACKTEST → DRAFT (if backtest fails)
SIMULATED_PAPER → LIVE_PAPER (after min days)
LIVE_PAPER → PENDING_APPROVAL (after min days + validation)
PENDING_APPROVAL → LIVE (on approval)
PENDING_APPROVAL → LIVE_PAPER (if rejected)
LIVE → PAUSED (manual or circuit breaker)
LIVE → UNDERPERFORMING (auto-detected)
PAUSED → LIVE (manual resume)
UNDERPERFORMING → PAUSED (auto)
Any → RETIRED (manual)
```

**Method:** `async transition_status(strategy_id, new_status, reason) -> Strategy`

**Acceptance Criteria:**
- [ ] Only valid transitions allowed
- [ ] Lifecycle events recorded
- [ ] Reason required for transitions
- [ ] Unit test: all transitions

---

### Task 5.1.3a: Implement Market Regime Manager
- [ ] **Status:** Not Started
- **Description:** Manual regime tagging system per PRD Feature B
- **Dependencies:** [5.1.3]
- **Effort:** 2.5 hours

**File:** `src/core/strategy/regime.py`

**MarketRegimeManager class:**
```python
from enum import Enum
from datetime import datetime
from typing import List, Optional, Tuple
from dataclasses import dataclass

class MarketRegime(str, Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"

@dataclass
class RegimeChange:
    previous_regime: MarketRegime
    new_regime: MarketRegime
    changed_at: datetime
    changed_by: str  # operator name
    note: str

class MarketRegimeManager:
    """
    Manual regime tagging system per PRD Feature B.
    
    Features:
    - Operator sets current market regime via dashboard dropdown
    - Strategies define preferred_regimes and avoid_regimes
    - On mismatch: reduce position size by 50%
    
    Regimes:
    - trending_up: Strong upward trend
    - trending_down: Strong downward trend
    - ranging: Sideways, no clear direction
    - volatile: High volatility, unpredictable
    - unknown: Default, no regime set
    """
    
    MISMATCH_SIZE_REDUCTION = 0.5  # 50% size reduction
    
    def __init__(self, data_store):
        self.data_store = data_store
        self._current_regime = MarketRegime.UNKNOWN
        self._history: List[RegimeChange] = []
    
    def get_current_regime(self) -> MarketRegime:
        """Get the current market regime."""
        return self._current_regime
    
    async def set_regime(
        self, 
        regime: MarketRegime, 
        operator: str,
        note: str = ""
    ):
        """Set the current market regime (manual, via dashboard)."""
        change = RegimeChange(
            previous_regime=self._current_regime,
            new_regime=regime,
            changed_at=datetime.utcnow(),
            changed_by=operator,
            note=note
        )
        
        self._history.append(change)
        self._current_regime = regime
        
        # Persist to database
        await self.data_store.update_system_state('market_regime', regime.value)
        await self.data_store.add_regime_change(change)
    
    def get_regime_history(self, limit: int = 20) -> List[RegimeChange]:
        """Get recent regime changes."""
        return self._history[-limit:]
    
    def check_strategy_compatibility(
        self, 
        strategy: Strategy
    ) -> Tuple[bool, float]:
        """
        Check if current regime is compatible with strategy.
        
        Returns:
        - (True, 1.0) if compatible
        - (True, 0.5) if mismatch (reduce size 50%)
        - (False, 0.0) if in avoid_regimes
        """
        # Strategy defines which regimes it prefers
        preferred = getattr(strategy, 'preferred_regimes', [])
        avoid = getattr(strategy, 'avoid_regimes', [])
        
        current = self._current_regime
        
        # If in avoid list, don't trade
        if current in avoid:
            return False, 0.0
        
        # If current regime is unknown, trade with caution
        if current == MarketRegime.UNKNOWN:
            return True, 1.0
        
        # If in preferred list, full size
        if current in preferred or len(preferred) == 0:
            return True, 1.0
        
        # Mismatch: reduce size by 50%
        return True, self.MISMATCH_SIZE_REDUCTION
    
    async def load_from_database(self):
        """Load regime state from database on startup."""
        regime_str = await self.data_store.get_system_state('market_regime')
        if regime_str:
            self._current_regime = MarketRegime(regime_str)
        
        self._history = await self.data_store.get_regime_history()
```

**Template additions:** Each template can define:
```yaml
preferred_regimes: [trending_up, trending_down]
avoid_regimes: [volatile]
```

**Acceptance Criteria:**
- [ ] MarketRegime enum with 5 values
- [ ] Operator can set regime via API
- [ ] Regime changes logged with timestamp and operator
- [ ] Strategies can define preferred_regimes and avoid_regimes
- [ ] Size reduced by 50% on regime mismatch
- [ ] Trading blocked if in avoid_regimes
- [ ] Regime persists across restarts
- [ ] Unit test: regime setting
- [ ] Unit test: compatibility checking

---

### Task 5.1.4: Create All 7 Template YAML Files
- [ ] **Status:** Not Started
- **Description:** Create YAML config for all templates
- **Dependencies:** [1.3.3]
- **Effort:** 4 hours

**Files to create in `config/templates/`:**

1. **ema_trend_rsi.yaml** - Template 1: EMA Trend + RSI Filter
2. **donchian_atr.yaml** - Template 2: Donchian Breakout + ATR Sizing  
3. **bb_squeeze_breakout.yaml** - Template 3: Bollinger Band Squeeze
4. **rsi_bb_mean_reversion.yaml** - Template 4: RSI + BB Mean Reversion
5. **supertrend_volume_macd.yaml** - Template 5: SuperTrend + Volume/MACD
6. **macd_pullback.yaml** - Template 6: MACD Trend + Pullback Entry
7. **vwap_pullback_volume.yaml** - Template 7: VWAP Pullback + Volume

**Each file includes:**
- id, name, version, type, description
- entry_logic, exit_logic as structured definitions
- parameters with min/max/step/default/ui_group
- validation rules
- expected_performance benchmarks
- recommended_for / not_recommended_for

**Acceptance Criteria:**
- [ ] All 7 files created
- [ ] All parameters from PRD Section 3.3.2 included
- [ ] YAML syntax valid
- [ ] Templates load without errors
- [ ] Unit test: load each template

---

### Task 5.1.5: Implement Template Loading Verification
- [ ] **Status:** Not Started
- **Description:** Verify all templates load correctly on startup
- **Dependencies:** [5.1.4, 1.3.3]
- **Effort:** 1 hour

**Add to:** `src/core/strategy/engine.py`

**Method:** `async verify_templates() -> TemplateVerificationResult`

**Checks:**
- All 7 templates load
- No duplicate IDs
- All required fields present
- Parameter specs valid

**Acceptance Criteria:**
- [ ] Run on startup
- [ ] Fail fast if templates invalid
- [ ] Clear error messages
- [ ] Unit test: verification

---

### Task 5.1.6: Create Strategy API Endpoints
- [ ] **Status:** Not Started
- **Description:** API for strategy management
- **Dependencies:** [5.1.1]
- **Effort:** 2 hours

**File:** `src/api/routes/strategies.py`

**Endpoints:**
- `GET /api/templates` - List available templates
- `GET /api/templates/{id}` - Get template details
- `POST /api/strategies` - Create strategy from template
- `GET /api/strategies` - List strategies (with filters)
- `GET /api/strategies/{id}` - Get strategy details
- `PUT /api/strategies/{id}` - Update strategy params
- `PUT /api/strategies/{id}/status` - Change status
- `DELETE /api/strategies/{id}` - Retire strategy

**Acceptance Criteria:**
- [ ] All CRUD operations
- [ ] Template listing
- [ ] Status changes
- [ ] Proper validation errors
- [ ] Integration test: API calls

---

### Task 5.1.7: Implement Strategy Assignment to Account
- [ ] **Status:** Not Started
- **Description:** Assign strategies to trading accounts
- **Dependencies:** [5.1.1, 1.2.8]
- **Effort:** 1.5 hours

**Add to:** `src/core/strategy/engine.py`

**Methods:**
- `assign_to_account(strategy_id, account_id, allocation_pct)`
- `unassign_from_account(strategy_id, account_id)`
- `get_account_strategies(account_id)`

**Acceptance Criteria:**
- [ ] Assignment creates StrategyAssignment record
- [ ] Allocation percentage tracked
- [ ] Can have multiple strategies per account
- [ ] Unit test: assignments

---

### Task 5.1.8: Write Template System Tests
- [ ] **Status:** Not Started
- **Description:** Tests for template system
- **Dependencies:** [5.1.1-5.1.7]
- **Effort:** 2 hours

**File:** `tests/unit/test_strategy_engine.py`

**Test scenarios:**
- Create strategy from each template
- Parameter validation
- Status transitions
- Template loading
- Account assignment

**Acceptance Criteria:**
- [ ] All templates tested
- [ ] Validation tested
- [ ] Transitions tested
- [ ] >85% coverage

---

## SECTION 5.2: SIGNAL GENERATION
*Estimated: 20 hours*

### Task 5.2.1: Create Signal Generator Interface
- [ ] **Status:** Not Started
- **Description:** Base class for signal generation
- **Dependencies:** [5.1.1, 2.2.15]
- **Effort:** 1.5 hours

**File:** `src/core/strategy/signals.py`

**Types:**
```python
class SignalType(Enum):
    LONG_ENTRY = "long_entry"
    LONG_EXIT = "long_exit"
    SHORT_ENTRY = "short_entry"  # For future
    SHORT_EXIT = "short_exit"    # For future
    NO_SIGNAL = "no_signal"

@dataclass
class Signal:
    type: SignalType
    symbol: str
    strategy_id: str
    timestamp: datetime
    price: float  # Current price when signal generated
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = 1.0
    metadata: Dict = field(default_factory=dict)

class SignalGenerator(ABC):
    @abstractmethod
    async def generate_signal(
        self,
        strategy: Strategy,
        symbol: str,
        data: OHLCVSeries
    ) -> Signal:
        pass
```

**Acceptance Criteria:**
- [ ] Signal types defined
- [ ] Signal dataclass complete
- [ ] Abstract generator interface
- [ ] Unit test: signal creation

---

### Task 5.2.2: Implement Template 1 Signal Generator (EMA Trend + RSI)
- [ ] **Status:** Not Started
- **Description:** Signal generator for EMA Trend + RSI template
- **Dependencies:** [5.2.1, 2.2.2, 2.2.3, 2.2.4]
- **Effort:** 2.5 hours

**File:** `src/core/strategy/generators/ema_trend_rsi.py`

**Entry Logic (from PRD):**
- Fast EMA > Slow EMA (uptrend)
- RSI between 40-60 (not overbought/oversold)
- Price pulls back to Fast EMA (within ATR distance)
- Entry: Market buy on confirmation

**Exit Logic:**
- Stop loss: ATR-based trailing stop
- Take profit: Risk multiple target (e.g., 2R)
- Exit if trend reverses (Fast EMA < Slow EMA)

**Acceptance Criteria:**
- [ ] Entry signal generated correctly
- [ ] Exit signal generated correctly
- [ ] Stop loss calculated with ATR
- [ ] Take profit calculated
- [ ] Unit test: with known data

---

### Task 5.2.3: Implement Template 2 Signal Generator (Donchian + ATR)
- [ ] **Status:** Not Started
- **Description:** Signal generator for Donchian Breakout template
- **Dependencies:** [5.2.1, 2.2.7, 2.2.4]
- **Effort:** 2 hours

**File:** `src/core/strategy/generators/donchian_atr.py`

**Entry Logic (Turtle-style):**
- Price breaks above N-day high (entry channel)
- ATR-based position sizing
- Optional: pyramiding on additional breakouts

**Exit Logic:**
- Price breaks below M-day low (exit channel, M < N)
- ATR trailing stop

**Acceptance Criteria:**
- [ ] Breakout detection works
- [ ] Entry/exit channels different
- [ ] ATR sizing integrated
- [ ] Unit test: breakout scenarios

---

### Task 5.2.4: Implement Template 3 Signal Generator (BB Squeeze)
- [ ] **Status:** Not Started
- **Description:** Signal generator for Bollinger Band Squeeze
- **Dependencies:** [5.2.1, 2.2.6, 2.2.4]
- **Effort:** 2 hours

**File:** `src/core/strategy/generators/bb_squeeze.py`

**Entry Logic:**
- BB width in squeeze (< 10th percentile of lookback)
- Breakout: close above upper band
- Volume confirmation (above average)

**Exit Logic:**
- Price returns inside bands
- ATR trailing stop
- Time-based exit (max bars in trade)

**Acceptance Criteria:**
- [ ] Squeeze detection works
- [ ] Breakout entry works
- [ ] Volume filter works
- [ ] Unit test: squeeze scenarios

---

### Task 5.2.5: Implement Template 4 Signal Generator (RSI + BB Mean Reversion)
- [ ] **Status:** Not Started
- **Description:** Signal generator for mean reversion template
- **Dependencies:** [5.2.1, 2.2.3, 2.2.6, 2.2.11]
- **Effort:** 2 hours

**File:** `src/core/strategy/generators/rsi_bb_mean_reversion.py`

**Entry Logic:**
- RSI oversold (< 30-35)
- Price at/below lower Bollinger Band
- ADX < 25 (ranging market, not trending)

**Exit Logic:**
- RSI overbought OR price at middle BB OR price at upper BB
- Fixed stop loss
- Time exit if no move

**Acceptance Criteria:**
- [ ] Oversold detection
- [ ] Ranging market filter (ADX)
- [ ] Mean reversion exit
- [ ] Unit test: ranging scenarios

---

### Task 5.2.6: Implement Template 5 Signal Generator (SuperTrend + Volume/MACD)
- [ ] **Status:** Not Started
- **Description:** Signal generator for SuperTrend template
- **Dependencies:** [5.2.1, 2.2.8, 2.2.5, 2.2.12]
- **Effort:** 2.5 hours

**File:** `src/core/strategy/generators/supertrend_volume_macd.py`

**Entry Logic:**
- SuperTrend flips bullish
- MACD histogram positive (confirmation)
- Volume above average (confirmation)

**Exit Logic:**
- SuperTrend flips bearish
- Or trailing stop triggered

**Acceptance Criteria:**
- [ ] SuperTrend flip detection
- [ ] MACD confirmation works
- [ ] Volume confirmation works
- [ ] Unit test: flip scenarios

---

### Task 5.2.7: Implement Template 6 Signal Generator (MACD Pullback)
- [ ] **Status:** Not Started
- **Description:** Signal generator for MACD pullback template
- **Dependencies:** [5.2.1, 2.2.5, 2.2.2]
- **Effort:** 2 hours

**File:** `src/core/strategy/generators/macd_pullback.py`

**Entry Logic:**
- MACD > Signal (bullish)
- Price in uptrend (above EMA)
- Pullback: histogram declining but still positive
- Entry on histogram turn (start rising again)

**Exit Logic:**
- MACD bearish crossover
- Or trailing stop

**Acceptance Criteria:**
- [ ] Trend confirmation
- [ ] Pullback detection
- [ ] Histogram turn detection
- [ ] Unit test: pullback scenarios

---

### Task 5.2.8: Implement Template 7 Signal Generator (VWAP Pullback)
- [ ] **Status:** Not Started
- **Description:** Signal generator for VWAP pullback template
- **Dependencies:** [5.2.1, 2.2.9, 2.2.3, 2.2.12]
- **Effort:** 2 hours

**File:** `src/core/strategy/generators/vwap_pullback.py`

**Entry Logic:**
- Price above VWAP (bullish bias)
- Pullback to VWAP ± tolerance
- RSI not overbought
- Volume confirmation

**Exit Logic:**
- Price reaches VWAP + band
- Partial take profit
- Time-based exit (intraday)

**Acceptance Criteria:**
- [ ] VWAP calculation correct
- [ ] Pullback to VWAP detection
- [ ] Partial TP logic
- [ ] Unit test: intraday scenarios

---

### Task 5.2.9: Create Signal Generator Factory
- [ ] **Status:** Not Started
- **Description:** Factory to create signal generators by template
- **Dependencies:** [5.2.2-5.2.8]
- **Effort:** 1 hour

**File:** `src/core/strategy/generators/__init__.py`

**SignalGeneratorFactory:**
```python
class SignalGeneratorFactory:
    _generators = {
        "ema_trend_rsi": EMATrendRSIGenerator,
        "donchian_atr": DonchianATRGenerator,
        "bb_squeeze_breakout": BBSqueezeGenerator,
        "rsi_bb_mean_reversion": RSIBBMeanReversionGenerator,
        "supertrend_volume_macd": SuperTrendGenerator,
        "macd_pullback": MACDPullbackGenerator,
        "vwap_pullback_volume": VWAPPullbackGenerator,
    }
    
    @classmethod
    def create(cls, template_id: str) -> SignalGenerator:
        pass
```

**Acceptance Criteria:**
- [ ] All 7 generators registered
- [ ] Create by template ID
- [ ] Unit test: factory creation

---

### Task 5.2.10: Write Signal Generator Tests
- [ ] **Status:** Not Started
- **Description:** Tests for all signal generators
- **Dependencies:** [5.2.1-5.2.9]
- **Effort:** 3 hours

**Files:**
- `tests/unit/strategy/test_signal_generators.py`
- `tests/fixtures/sample_ohlcv.py` (test data)

**Test approach:**
- Create known OHLCV data that should trigger signals
- Verify correct signal type generated
- Verify stop loss / take profit calculations
- Test no-signal conditions

**Acceptance Criteria:**
- [ ] Each generator has tests
- [ ] Entry and exit signals tested
- [ ] Edge cases covered
- [ ] >85% coverage

---

## SECTION 5.3: BACKTEST ENGINE
*Estimated: 20 hours*

### Task 5.3.1: Create Backtest Engine Core
- [ ] **Status:** Not Started
- **Description:** Core backtesting engine
- **Dependencies:** [5.2.9, 2.1.4]
- **Effort:** 3 hours

**File:** `src/core/strategy/backtest/engine.py`

**BacktestEngine class:**
```python
class BacktestEngine:
    def __init__(
        self,
        market_data: MarketDataService,
        generator_factory: SignalGeneratorFactory
    ):
        pass
    
    async def run_backtest(
        self,
        strategy: Strategy,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 10000
    ) -> BacktestResult:
        pass
```

**Acceptance Criteria:**
- [ ] Runs on historical data
- [ ] Simulates trading
- [ ] Returns results
- [ ] Unit test: basic backtest

---

### Task 5.3.2: Implement Trade Simulation
- [ ] **Status:** Not Started
- **Description:** Simulate trade execution in backtest
- **Dependencies:** [5.3.1]
- **Effort:** 2.5 hours

**Add to:** `src/core/strategy/backtest/engine.py`

**SimulatedTrader:**
- Track virtual positions
- Track virtual cash
- Simulate fills at next bar open (conservative)
- Apply configurable slippage
- Apply commission

**Acceptance Criteria:**
- [ ] Position tracking correct
- [ ] Cash balance correct
- [ ] Slippage applied
- [ ] Commission applied
- [ ] Unit test: trade simulation

---

### Task 5.3.3: Implement Backtest Metrics Calculator
- [ ] **Status:** Not Started
- **Description:** Calculate performance metrics from backtest
- **Dependencies:** [5.3.1, 5.3.2]
- **Effort:** 2.5 hours

**File:** `src/core/strategy/backtest/metrics.py`

**Metrics to calculate (from PRD 3.5.2):**
- Total return %
- Sharpe ratio
- Sortino ratio
- Maximum drawdown %
- Win rate %
- Profit factor
- Average win / average loss
- Number of trades
- Average trade duration
- Expectancy

**Acceptance Criteria:**
- [ ] All metrics calculated correctly
- [ ] Verified against manual calculations
- [ ] Handle edge cases (no trades, all wins, all losses)
- [ ] Unit test: each metric

---

### Task 5.3.4: Implement Equity Curve Tracking
- [ ] **Status:** Not Started
- **Description:** Track equity over time during backtest
- **Dependencies:** [5.3.1]
- **Effort:** 1.5 hours

**Add to:** `src/core/strategy/backtest/engine.py`

**EquityCurve:**
- Record equity at each bar
- Calculate drawdown at each point
- Generate DataFrame for visualization

**Acceptance Criteria:**
- [ ] Equity tracked per bar
- [ ] Drawdown calculated
- [ ] Exportable to DataFrame
- [ ] Unit test: equity tracking

---

### Task 5.3.5: Implement Trade Log
- [ ] **Status:** Not Started
- **Description:** Log all trades during backtest
- **Dependencies:** [5.3.2]
- **Effort:** 1.5 hours

**Add to:** `src/core/strategy/backtest/engine.py`

**TradeLog:**
- Entry date, price
- Exit date, price
- P&L ($ and %)
- Holding period
- MAE (Max Adverse Excursion)
- MFE (Max Favorable Excursion)

**Acceptance Criteria:**
- [ ] All trades logged
- [ ] MAE/MFE tracked
- [ ] Exportable
- [ ] Unit test: trade logging

---

### Task 5.3.6: Implement Backtest Result
- [ ] **Status:** Not Started
- **Description:** Comprehensive backtest result object
- **Dependencies:** [5.3.3, 5.3.4, 5.3.5]
- **Effort:** 1.5 hours

**File:** `src/core/strategy/backtest/result.py`

**BacktestResult:**
```python
@dataclass
class BacktestResult:
    strategy_id: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    
    # Metrics
    metrics: BacktestMetrics
    
    # Details
    equity_curve: pd.DataFrame
    trade_log: List[TradeRecord]
    
    # Validation
    passed_validation: bool
    validation_errors: List[str]
    
    def to_dict(self) -> dict:
        pass
    
    def summary(self) -> str:
        pass
```

**Acceptance Criteria:**
- [ ] All data captured
- [ ] Serializable
- [ ] Human-readable summary
- [ ] Unit test: result creation

---

### Task 5.3.7: Implement Backtest Validation
- [ ] **Status:** Not Started
- **Description:** Validate backtest results against thresholds
- **Dependencies:** [5.3.6]
- **Effort:** 2 hours

**Add to:** `src/core/strategy/backtest/engine.py`

**Validation rules (from PRD 3.3.3):**
- Sharpe ratio >= 0.5 (configurable)
- Max drawdown <= 15% (from risk profile)
- Win rate >= 35%
- Minimum 30 trades for significance
- Profit factor >= 1.0

**Method:** `validate_result(result: BacktestResult, thresholds: ValidationThresholds) -> (bool, List[str])`

**Acceptance Criteria:**
- [ ] All rules checked
- [ ] Configurable thresholds
- [ ] Clear failure reasons
- [ ] Unit test: validation pass/fail

---

### Task 5.3.8: Implement Walk-Forward Analysis (Optional)
- [ ] **Status:** Not Started
- **Description:** Walk-forward optimization/validation
- **Dependencies:** [5.3.1]
- **Effort:** 3 hours

**File:** `src/core/strategy/backtest/walk_forward.py`

**Walk-Forward:**
- Split data into in-sample / out-of-sample periods
- Optimize on in-sample
- Test on out-of-sample
- Roll forward and repeat
- Aggregate OOS results

**Note:** Nice to have for MVP. Can be simplified.

**Acceptance Criteria:**
- [ ] Data splitting works
- [ ] Multiple windows tested
- [ ] OOS results aggregated
- [ ] Unit test: walk-forward

---

### Task 5.3.9: Create Backtest API Endpoints
- [ ] **Status:** Not Started
- **Description:** API for running backtests
- **Dependencies:** [5.3.1-5.3.7]
- **Effort:** 2 hours

**Add to:** `src/api/routes/strategies.py`

**Endpoints:**
- `POST /api/strategies/{id}/backtest` - Run backtest
- `GET /api/strategies/{id}/backtest` - Get backtest results
- `GET /api/strategies/{id}/backtest/trades` - Get trade log
- `GET /api/strategies/{id}/backtest/equity` - Get equity curve

**Acceptance Criteria:**
- [ ] Can trigger backtest
- [ ] Results returned
- [ ] Trade log available
- [ ] Equity curve available

---

### Task 5.3.10: Write Backtest Engine Tests
- [ ] **Status:** Not Started
- **Description:** Comprehensive backtest tests
- **Dependencies:** [5.3.1-5.3.9]
- **Effort:** 3 hours

**File:** `tests/unit/strategy/test_backtest_engine.py`

**Test scenarios:**
- Backtest with known signals
- Verify P&L calculation
- Verify metrics calculation
- Determinism (same input = same output)
- Edge cases (no trades, all wins, all losses)

**Acceptance Criteria:**
- [ ] Deterministic results verified
- [ ] Metrics verified manually
- [ ] Edge cases handled
- [ ] >85% coverage

---

## SECTION 5.4: PAPER TRADING
*Estimated: 20 hours*

### Task 5.4.1: Create Paper Trading Engine
- [ ] **Status:** Not Started
- **Description:** Paper trading for strategy validation
- **Dependencies:** [5.2.9, 4.3.1]
- **Effort:** 3 hours

**File:** `src/core/strategy/paper/engine.py`

**PaperTradingEngine class:**
```python
class PaperTradingEngine:
    """
    Two modes:
    1. Simulated Paper: Backtest-style but on recent data
    2. Live Paper: Real-time with simulated execution
    """
    
    def __init__(
        self,
        strategy: Strategy,
        market_data: MarketDataService,
        signal_generator: SignalGenerator,
        mode: PaperTradingMode  # SIMULATED or LIVE
    ):
        pass
    
    async def start(self):
        """Start paper trading loop."""
        pass
    
    async def stop(self):
        """Stop paper trading."""
        pass
    
    async def get_status(self) -> PaperTradingStatus:
        pass
```

**Acceptance Criteria:**
- [ ] Both modes implemented
- [ ] Tracks virtual P&L
- [ ] Can start/stop
- [ ] Unit test: basic paper trading

---

### Task 5.4.2: Implement Simulated Paper Trading
- [ ] **Status:** Not Started
- **Description:** Paper trading on recent historical data
- **Dependencies:** [5.4.1]
- **Effort:** 2 hours

**Add to:** `src/core/strategy/paper/engine.py`

**Simulated Paper (Phase 1 from PRD 3.3.4):**
- Run on last 21 days of data
- Same as backtest but recent data
- Faster validation before live paper
- Must pass same validation thresholds

**Acceptance Criteria:**
- [ ] Uses last 21 days
- [ ] Same metrics as backtest
- [ ] Validation applied
- [ ] Unit test: simulated paper

---

### Task 5.4.3: Implement Live Paper Trading
- [ ] **Status:** Not Started
- **Description:** Real-time paper trading with live prices
- **Dependencies:** [5.4.1, 2.1.7]
- **Effort:** 3 hours

**Add to:** `src/core/strategy/paper/engine.py`

**Live Paper (Phase 2 from PRD 3.3.4):**
- Real-time price feeds
- Simulated order fills
- Track performance over 7+ days
- Log all signals and fills

**Main loop:**
```python
async def _paper_trading_loop(self):
    while self._running:
        for symbol in self.strategy.symbols:
            data = await self.market_data.get_ohlcv(symbol, timeframe)
            signal = await self.signal_generator.generate_signal(...)
            if signal.type != SignalType.NO_SIGNAL:
                await self._execute_paper_signal(signal)
        await asyncio.sleep(interval)
```

**Acceptance Criteria:**
- [ ] Real-time data used
- [ ] Signals generated live
- [ ] Paper fills simulated
- [ ] Runs for configured duration
- [ ] Integration test: live paper

---

### Task 5.4.4: Implement Paper Trading Metrics Tracker
- [ ] **Status:** Not Started
- **Description:** Track metrics during paper trading
- **Dependencies:** [5.4.1, 5.3.3]
- **Effort:** 2 hours

**Add to:** `src/core/strategy/paper/engine.py`

**Track:**
- Running P&L
- Running Sharpe (approximation)
- Win rate so far
- Drawdown from peak
- Number of trades
- Signal accuracy (did signal direction match outcome)

**Acceptance Criteria:**
- [ ] Metrics update in real-time
- [ ] Comparable to backtest metrics
- [ ] Queryable via API
- [ ] Unit test: metric tracking

---

### Task 5.4.5: Implement Paper Trading Validation
- [ ] **Status:** Not Started
- **Description:** Validate paper trading meets thresholds
- **Dependencies:** [5.4.1, 5.4.4]
- **Effort:** 2 hours

**Add to:** `src/core/strategy/paper/engine.py`

**Validation triggers (from PRD 3.3.4):**
- Simulated paper: After 21 days (or equivalent trades)
- Live paper: After 7 days minimum

**Auto-transition:**
- If validation passes → move to next status
- If validation fails → stay in current status, notify user

**Acceptance Criteria:**
- [ ] Validation at end of period
- [ ] Auto-transition on pass
- [ ] Notification on fail
- [ ] Unit test: validation

---

### Task 5.4.6: Implement Paper Trading State Persistence
- [ ] **Status:** Not Started
- **Description:** Persist paper trading state for recovery
- **Dependencies:** [5.4.1]
- **Effort:** 1.5 hours

**Add to:** `src/core/strategy/paper/engine.py`

**Persist:**
- Current positions
- Cash balance
- Trade history
- Running metrics
- Start time

**Recovery on restart:**
- Load state
- Resume from where left off
- Continue tracking

**Acceptance Criteria:**
- [ ] State persists to database
- [ ] Recovery works
- [ ] No P&L gaps
- [ ] Unit test: persistence

---

### Task 5.4.7: Create Paper Trading API
- [ ] **Status:** Not Started
- **Description:** API for paper trading control
- **Dependencies:** [5.4.1]
- **Effort:** 1.5 hours

**Add to:** `src/api/routes/strategies.py`

**Endpoints:**
- `POST /api/strategies/{id}/paper/start` - Start paper trading
- `POST /api/strategies/{id}/paper/stop` - Stop paper trading
- `GET /api/strategies/{id}/paper/status` - Get status and metrics
- `GET /api/strategies/{id}/paper/trades` - Get paper trades

**Acceptance Criteria:**
- [ ] Can start/stop paper trading
- [ ] Status includes metrics
- [ ] Trade history available
- [ ] Integration test: API

---

### Task 5.4.8: Implement Multi-Strategy Paper Trading
- [ ] **Status:** Not Started
- **Description:** Run multiple strategies in paper trading
- **Dependencies:** [5.4.1-5.4.7]
- **Effort:** 2 hours

**File:** `src/core/strategy/paper/manager.py`

**PaperTradingManager:**
- Manage multiple PaperTradingEngine instances
- Coordinate shared market data
- Aggregate metrics

**Acceptance Criteria:**
- [ ] Multiple strategies run concurrently
- [ ] Shared data feed
- [ ] Individual metrics per strategy
- [ ] Unit test: multi-strategy

---

### Task 5.4.9: Create Paper Trading Dashboard Data
- [ ] **Status:** Not Started
- **Description:** Data for paper trading dashboard
- **Dependencies:** [5.4.4]
- **Effort:** 1.5 hours

**Add to:** `src/api/routes/strategies.py`

**Endpoint:** `GET /api/strategies/{id}/paper/dashboard`

**Returns:**
- Current status (running/stopped/complete)
- Days remaining
- Current metrics summary
- Recent trades
- Equity curve data points
- Validation progress

**Acceptance Criteria:**
- [ ] All dashboard data
- [ ] Refresh-friendly
- [ ] Performance optimized
- [ ] Integration test: dashboard data

---

### Task 5.4.10: Write Paper Trading Tests
- [ ] **Status:** Not Started
- **Description:** Tests for paper trading
- **Dependencies:** [5.4.1-5.4.9]
- **Effort:** 2.5 hours

**File:** `tests/unit/strategy/test_paper_trading.py`

**Test scenarios:**
- Simulated paper trading
- Live paper trading (mocked prices)
- Metric tracking
- Validation pass/fail
- State persistence
- Multi-strategy

**Acceptance Criteria:**
- [ ] Both modes tested
- [ ] Metrics verified
- [ ] Persistence tested
- [ ] >80% coverage

---

## 📋 PHASE 5 COMPLETION CHECKLIST

Before moving to Phase 6, verify:

- [ ] All 40 tasks completed
- [ ] All 7 template YAML files created and load correctly
- [ ] All 7 signal generators implemented and tested
- [ ] Strategy similarity check rejects > 70% similar strategies
- [ ] Market regime manager working with dashboard dropdown
- [ ] Regime mismatch reduces position size by 50%
- [ ] Backtest engine produces deterministic results
- [ ] Backtest metrics verified against manual calculations
- [ ] Paper trading (simulated) works for all templates
- [ ] Paper trading (live) runs with real-time data
- [ ] Validation thresholds enforced correctly
- [ ] Status transitions follow PRD lifecycle
- [ ] `pytest tests/unit/strategy/` passes with >85% coverage
- [ ] API endpoints work correctly
- [ ] No linting errors

**Template Verification:**
- [ ] Template 1 (EMA Trend + RSI) generates correct signals
- [ ] Template 2 (Donchian + ATR) generates correct signals
- [ ] Template 3 (BB Squeeze) generates correct signals
- [ ] Template 4 (RSI + BB Mean Reversion) generates correct signals
- [ ] Template 5 (SuperTrend + Volume/MACD) generates correct signals
- [ ] Template 6 (MACD Pullback) generates correct signals
- [ ] Template 7 (VWAP Pullback) generates correct signals

**PRD Compliance Checklist:**
- [ ] Feature B: Market regime tagging with dropdown
- [ ] Feature D: Strategy similarity check (70% threshold)

**Sign-off:** _________________ Date: _________________

---

**Previous Phase:** [04_PHASE_4_EXECUTION.md](./04_PHASE_4_EXECUTION.md)  
**Next Phase:** [06_PHASE_6_INTEGRATION.md](./06_PHASE_6_INTEGRATION.md)
