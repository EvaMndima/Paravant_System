# PHASE 5 IMPLEMENTATION GUIDE
## Strategy Templates & Backtesting
**Quick Reference | Best Practices | Common Patterns**

---

## 📋 Quick Navigation

- **Implementation Prompts:**
  - [SESSION_5A_IMPLEMENTATION_PROMPT.md](SESSION_5A_IMPLEMENTATION_PROMPT.md) - Template System + Signal Generation
  - [SESSION_5B_IMPLEMENTATION_PROMPT.md](SESSION_5B_IMPLEMENTATION_PROMPT.md) - Backtest Engine + Paper Trading

- **Verification Prompts:**
  - [SESSION_5A_VERIFICATION_PROMPT.md](SESSION_5A_VERIFICATION_PROMPT.md) - Template & signal validation
  - [SESSION_5B_VERIFICATION_PROMPT.md](SESSION_5B_VERIFICATION_PROMPT.md) - Backtest & paper trading validation

---

## 🎯 Phase 5 at a Glance

| Component | Duration | Tasks | Key Goal |
|-----------|----------|-------|----------|
| **Session 5A** | 44 hours | 20 | 7 working templates with signal generation |
| **Session 5B** | 44 hours | 20 | Deterministic backtest & paper trading |
| **Total** | ~88 hours | 40 | End-to-end strategy validation pipeline |

---

## 🔑 Critical Invariants (Must Not Violate)

### **1. Strategy Lifecycle is One-Way (Mostly)**

```
[DRAFT] → [BACKTEST] → [SIMULATED_PAPER] → [LIVE_PAPER] → [PENDING_APPROVAL] → [LIVE] ✓
                ↓
            Returns to DRAFT only on explicit fail ✓

BACKTEST → SIMULATED_PAPER (only if validation passes) ✓
SIMULATED_PAPER → LIVE_PAPER (after 21 days) ✓
LIVE_PAPER → PENDING_APPROVAL (after 7 days) ✓
LIVE_PAPER → LIVE_PAPER (repeat if fails) ✓

LIVE_PAPER → DRAFT ✗ (ILLEGAL - backward move)
SIMULATED_PAPER → BACKTEST ✗ (ILLEGAL - backward move)
```

**Violation**: Allowing backward transitions → Strategies trade without validation

### **2. Backtest Determinism is MANDATORY**

```
Same strategy + dates + config → EXACT same result (always)
✓ Chronological iteration (bar N, then N+1)
✓ Fill at next bar open (no lookahead)
✓ Consistent commission, slippage, rounding
✗ DO NOT: Use random(), sort dict.items(), float rounding
```

**Violation**: Non-deterministic results → Can't trust backtests

### **3. Strategy Similarity Threshold is 70% (LOCKED)**

```
Similarity Score =
  (template_match × 0.40) +
  (parameter_distance × 0.30) +
  (symbol_overlap × 0.20) +
  (entry_logic_match × 0.10)

Score > 70% → REJECT strategy
Score ≤ 70% → ALLOW strategy

❌ Wrong: Allowing 75% similar strategies (too lenient)
✅ Right: Rejecting all > 70% similar strategies
```

**Violation**: Allowing duplicate strategies → Portfolio concentration risk

### **4. All Timestamps Must Be Timezone-Aware (UTC)**

```
❌ Wrong: datetime.now()  # Naive datetime
✅ Right: datetime.now(timezone.utc)
```

**Violation**: Naive timestamps → Time ordering breaks, backtests fail

### **5. No NaN or Infinity in Financial Values**

```
❌ If entry_price is NaN: all calculations → NaN
✅ Validate all inputs: if math.isnan(price): raise ValueError
```

**Violation**: NaN propagates → Final P&L is NaN

### **6. Market Regime Size Reduction is 50% (LOCKED)**

```
Current Regime: TRENDING_UP
Strategy preferred_regimes: [TRENDING_UP]
Result: 100% position size (compatible)

Current Regime: VOLATILE
Strategy preferred_regimes: [TRENDING_UP]
Result: 50% position size (mismatch reduction)

Current Regime: VOLATILE
Strategy avoid_regimes: [VOLATILE]
Result: 0% position size (blocked - don't trade)
```

**Violation**: Wrong size reduction → Risk control fails

---

## 📊 Data Flow Architecture

### **Session 5A: Strategy Template & Signal Flow**

```
User Request: "Create EMA Trend Strategy"
         ↓
[StrategyEngine.create_strategy()]
    ↓
CRITICAL SEQUENCE:
1. Load template (ema_trend_rsi.yaml) ✓
   ├─ Validate template exists
   ├─ Load parameter specs
   └─ Load entry/exit logic
    ↓
2. Validate parameters ✓
   ├─ Type check (int/float)
   ├─ Min/max bounds
   └─ Step size validation
    ↓
3. Check similarity to existing ✓ (PRD Feature D)
   ├─ Compare template (40%)
   ├─ Compare parameters (30%)
   ├─ Compare symbols (20%)
   └─ If > 70% similar → REJECT
    ↓
4. Create Strategy record in memory
   └─ status = DRAFT
    ↓
5. Persist to database ⚠️ FIRST IRREVERSIBLE STEP
   └─ Order preserved
    ↓
6. Create associated objects
   ├─ StrategyAssignment (if assigned)
   └─ StrategyHistory (audit trail)
    ↓
7. Return Strategy to caller
         ↓
Strategy Ready (DRAFT state)

         ↓
         ↓
Signal Generation (Continuous)

User: "Start paper trading"
         ↓
[PaperTradingEngine.start()]
    ↓
For each bar (chronologically):
  1. Load OHLCV data (bar N)
  2. Create signal generator from factory
  3. Call generate_signal(strategy, symbol, data)
  4. Generator checks entry/exit conditions
  5. If signal triggered:
     - Fill at next bar open (bar N+1)
     - Track position & P&L
  6. Update metrics
         ↓
Paper Trading Results
(Feeds to backtester validation)
```

### **Session 5B: Backtest & Validation Flow**

```
User: "Run backtest"
         ↓
[BacktestEngine.run_backtest()]
    ↓
DETERMINISM GUARANTEED:
1. Load OHLCV data (fixed date range)
   ├─ start_date (inclusive)
   ├─ end_date (inclusive)
   └─ chronological order
    ↓
2. Create signal generator
   └─ Same factory as live trading
    ↓
3. Initialize portfolio
   ├─ cash = initial_capital
   ├─ position = None
   └─ trades = []
    ↓
4. Iterate bars chronologically (NO LOOKAHEAD)
   ├─ Bar N: Generate signal
   ├─ Bar N+1: Fill at open (never future data)
   ├─ Update position
   ├─ Track equity
   └─ Record trade if closed
    ↓
5. Calculate metrics from trades
   ├─ Total return %
   ├─ Sharpe ratio
   ├─ Max drawdown %
   ├─ Win rate %
   ├─ Profit factor
   └─ All verified against manual calculations
    ↓
6. Validate against thresholds
   ├─ Sharpe >= 0.5
   ├─ Max drawdown <= 15%
   ├─ Win rate >= 35%
   ├─ Profit factor >= 1.0
   └─ Min 30 trades
    ↓
7. Return BacktestResult
   ├─ metrics (all calculations)
   ├─ trade_log (entry/exit details)
   ├─ equity_curve (bar-by-bar tracking)
   └─ validation status
         ↓
Backtest Complete (Deterministic)

         ↓
         ↓
Paper Trading Validation

Simulated: Run on last 21 days
  → Must pass same validation
  → Quick feedback loop

Live: Run on real-time data
  → Must run 7+ days minimum
  → Auto-transition if passes
         ↓
Strategy Ready (LIVE or FAILED)
```

---

## 📐 Critical Formulas (Must Memorize)

### **1. Strategy Similarity Score (70% Threshold)**

```
Similarity = (T × 0.40) + (P × 0.30) + (S × 0.20) + (L × 0.10)

Where:
  T = Template match (1.0 if same, 0.0 if different)
  P = Parameter similarity (0-1.0, based on distance)
  S = Symbol overlap (intersection / union)
  L = Entry logic match (1.0 if same, 0.0 if different)

Example:
  New:      EMA template, fast=12, slow=26, symbols=[BTC, ETH]
  Existing: EMA template, fast=14, slow=28, symbols=[BTC, SOL]

  T = 1.0 (same template)
  P = 0.8 (parameters close)
  S = 0.5 (1 overlap out of 2 unique)
  L = 1.0 (same entry logic)

  Score = (1.0 × 0.40) + (0.8 × 0.30) + (0.5 × 0.20) + (1.0 × 0.10)
        = 0.40 + 0.24 + 0.10 + 0.10
        = 0.84 = 84% → REJECT (> 70%)
```

### **2. Market Regime Size Adjustment**

```
Order Size = Base Size × Compatibility Multiplier

Where:
  Base Size = Account Position Size Limit

  Multiplier:
    = 1.0 if regime in preferred_regimes
    = 1.0 if regime is UNKNOWN (default)
    = 0.5 if regime not in preferred (mismatch)
    = 0.0 if regime in avoid_regimes (blocked)

Example:
  Base Size: 1.0 BTC
  Current Regime: VOLATILE
  Strategy preferred: [TRENDING_UP, TRENDING_DOWN]
  Strategy avoid: [VOLATILE]

  Mismatch (not in preferred):
    Order Size = 1.0 × 0.5 = 0.5 BTC (50% reduction)

  Or avoid_regimes (blocked):
    Order Size = 1.0 × 0.0 = 0.0 BTC (0% - DON'T TRADE)
```

### **3. Backtest P&L Calculation**

```
Realized PnL = (Exit Price - Entry Price) × Quantity - Total Commission

Example (LONG):
  Entry: BTC @ $45,000, quantity = 0.5, commission = $5
  Exit:  BTC @ $46,000, quantity = 0.5, commission = $5

  PnL = (46,000 - 45,000) × 0.5 - (5 + 5)
      = 1,000 × 0.5 - 10
      = 500 - 10
      = $490 ✓
```

### **4. Sharpe Ratio**

```
Sharpe = (R̄ - Rf) / σ(R) × √252

Where:
  R̄ = mean daily return
  Rf = risk-free rate (2% annual = 0.02/252 daily)
  σ(R) = daily return standard deviation
  √252 = annualization factor (252 trading days/year)

Example:
  Mean daily return: 0.1%
  Daily std dev: 0.5%
  Risk-free rate: 0.02/252 = 0.0000794

  Sharpe = (0.001 - 0.0000794) / 0.005 × √252
         = (0.0009206 / 0.005) × 15.87
         = 0.18412 × 15.87
         = 2.92 ✓

Interpretation:
  < 0.5 = Poor
  0.5-1.0 = Fair
  1.0-2.0 = Good
  > 2.0 = Excellent
```

### **5. Maximum Drawdown**

```
Drawdown at bar i = (Peak - Current) / Peak

Max Drawdown = max(all drawdowns) × 100%

Example:
  Equity: [10000, 11000, 10500, 10800, 9500, 10200, 11500]

  Peak tracking: [10000, 11000, 11000, 11000, 11000, 11000, 11500]
  Drawdown: [0, 0, 4.5%, 1.8%, 13.6%, 7.3%, 0]

  Max Drawdown = 13.6%
```

### **6. Win Rate**

```
Win Rate = (Winning Trades / Total Trades) × 100%

Winning Trade = realized_pnl > 0

Example:
  Total trades: 100
  Winning trades: 52
  Losing trades: 48

  Win Rate = (52 / 100) × 100% = 52%
```

### **7. Profit Factor**

```
Profit Factor = Gross Profit / Gross Loss

Where:
  Gross Profit = sum of all positive P&L
  Gross Loss = |sum of all negative P&L|

Example:
  Winning trades: [500, 300, 250] = 1050 total
  Losing trades: [-200, -150, -400] = -750 total

  Profit Factor = 1050 / 750 = 1.40

Interpretation:
  < 1.0 = More losses than profits
  1.0 = Break-even
  1.0-1.5 = Profitable but marginal
  > 1.5 = Good profitability
```

---

## 🧪 Test Data Templates

### **Test Case: Simple EMA Trend Strategy**

```python
from src.core.strategy.engine import StrategyEngine
from datetime import datetime, timezone

# Create strategy from template
strategy = await engine.create_strategy(
    template_id='ema_trend_rsi',
    name='Test EMA Trend',
    params={
        'fast_ema': 12,
        'slow_ema': 26,
        'rsi_period': 14,
        'atr_period': 14
    },
    symbols=['BTCUSDT'],
    preferred_regimes=['trending_up'],
    avoid_regimes=['volatile']
)

# Expected:
# - status = DRAFT
# - template_id = 'ema_trend_rsi'
# - parameters stored exactly as provided
# - No validation errors

assert strategy.status == StrategyStatus.DRAFT
assert strategy.template_id == 'ema_trend_rsi'
assert strategy.parameters['fast_ema'] == 12
```

### **Test Case: Backtest with Known Trades**

```python
# Create OHLCV data that triggers known signals
test_data = pd.DataFrame({
    'timestamp': pd.date_range('2024-01-01', periods=100, freq='1h'),
    'open': np.linspace(45000, 46000, 100),
    'high': np.linspace(45100, 46100, 100),
    'low': np.linspace(44900, 45900, 100),
    'close': np.linspace(45050, 46050, 100),
    'volume': np.ones(100) * 1000
})

# Run backtest
result = await backtest_engine.run_backtest(
    strategy=strategy,
    symbol='BTCUSDT',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    end_date=datetime(2024, 1, 5, tzinfo=timezone.utc),
    config=BacktestConfig(initial_capital=10000, commission_rate=0.001)
)

# Expected:
# - deterministic results (same every run)
# - trades with entry/exit prices
# - correct P&L calculation
# - metrics in valid ranges

assert isinstance(result, BacktestResult)
assert result.initial_capital == 10000
assert len(result.trade_log) > 0
assert all(0 <= t.realized_pnl_pct <= 100 for t in result.trade_log)
```

### **Test Case: Similarity Check Threshold**

```python
# Create two strategies with 80% similarity (should reject)
strat1 = await engine.create_strategy(
    template_id='ema_trend_rsi',
    name='EMA Strategy 1',
    params={'fast_ema': 12, 'slow_ema': 26},
    symbols=['BTCUSDT', 'ETHUSDT']
)

# Almost identical
strat2_config = {
    'template_id': 'ema_trend_rsi',
    'name': 'EMA Strategy 2',
    'params': {'fast_ema': 12, 'slow_ema': 26},  # Identical
    'symbols': ['BTCUSDT']  # One symbol difference
}

# Check similarity
similarity = await similarity_checker.check_similarity(
    new_strategy_config=strat2_config,
    existing_strategies=[strat1]
)

# Expected:
# - is_too_similar = True (exceeds 70%)
# - similarity_pct > 70
# - breakdown shows: template 40%, parameters 30%, symbols 15%, logic 10%

assert similarity.is_too_similar is True
assert similarity.similarity_pct > 70
assert similarity.breakdown['template'] == 0.40
```

### **Test Case: Paper Trading 21-Day Simulation**

```python
# Run simulated paper trading on last 21 days
engine = PaperTradingEngine(
    strategy=strategy,
    market_data=market_data_service,
    signal_generator=signal_generator,
    mode=PaperTradingMode.SIMULATED,
    data_store=data_store
)

# Start (should complete in seconds)
await engine.start()

# Get final status
status = await engine.get_status()

# Expected:
# - is_running = False (completed)
# - days_elapsed ≈ 21
# - current_pnl >= 500 (5% of 10000) for passing validation
# - num_trades >= 5 for significance
# - validation_status = 'passed' or 'failed'

assert status.days_elapsed >= 20  # Roughly 21 days
assert status.num_trades >= 5
assert status.validation_status in ['passed', 'failed']
```

---

## ✅ Quality Checklist

### **Before Implementing Each Task**

- [ ] Read the implementation guide section
- [ ] Check code examples provided
- [ ] Understand the data flow
- [ ] Identify critical invariants that apply
- [ ] Review financial formulas if relevant
- [ ] Prepare test data templates
- [ ] Plan error scenarios

### **Before Verification**

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Coverage >85% (>80% for paper trading)
- [ ] mypy --strict passes
- [ ] ruff check passes
- [ ] isort check passes
- [ ] All logging uses structured format
- [ ] All financial calculations verified manually
- [ ] All state transitions follow state machine
- [ ] All timestamps are timezone-aware (UTC)
- [ ] No NaN/Infinity in financial values
- [ ] All errors logged with context

### **After Completing Phase 5**

- [ ] Both sessions (5A & 5B) complete
- [ ] All 40 tasks implemented
- [ ] All 7 templates working
- [ ] All 7 signal generators working
- [ ] Backtest deterministic
- [ ] Paper trading validates strategies
- [ ] All tests passing
- [ ] Production audit Grade A+
- [ ] Decision consistency verified
- [ ] Code ready for Phase 6

---

## 🚀 Implementation Tips

### **Tip 1: Build Templates First, Then Generators**

Don't try to implement everything at once:

```
1. ✓ Create 7 template YAML files
2. ✓ Verify templates load
3. ✓ Implement StrategyEngine.create_strategy()
4. ✓ Test strategy creation from each template
5. THEN: Start signal generators
```

Why: Templates define what generators need to work with.

### **Tip 2: Test Determinism Early**

After backtest engine basics, verify determinism:

```python
# After Task 5.3.1:
async def test_determinism():
    result1 = await engine.run_backtest(...)
    result2 = await engine.run_backtest(...)
    assert result1.num_trades == result2.num_trades
    assert result1.final_capital == result2.final_capital
```

Why: Easier to fix determinism issues early than after 20 other tasks.

### **Tip 3: Use Actual OHLCV Data in Tests**

Don't create synthetic data:

```python
# BETTER: Use real historical data
data = await market_data_service.get_ohlcv(
    'BTCUSDT',
    start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
    end_date=datetime(2023, 3, 31, tzinfo=timezone.utc)
)

result = await backtest_engine.run_backtest(
    strategy=strategy,
    symbol='BTCUSDT',
    start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
    end_date=datetime(2023, 3, 31, tzinfo=timezone.utc)
)

assert result.num_trades > 0  # Real data produces real signals
```

### **Tip 4: Log Aggressively (But Structured)**

```python
# Every important operation should log with full context:
logger.info(
    "strategy_created",
    strategy_id=strategy.id,
    template_id=template_id,
    symbol=symbols[0],
    name=name,
    parameters=params  # Log what was set
)

logger.info(
    "backtest_completed",
    strategy_id=strategy.id,
    symbol=symbol,
    total_return_pct=result.metrics.total_return_pct,
    sharpe_ratio=result.metrics.sharpe_ratio,
    max_drawdown_pct=result.metrics.max_drawdown_pct,
    num_trades=result.num_trades,
    passed_validation=result.passed_validation
)
```

### **Tip 5: Verify Calculations Manually**

For every P&L and metric:

```python
# Manual verification template:

# Expected P&L for trade
entry = 45000
exit = 46000
qty = 0.5
commission = 5 + 5

expected_pnl = (exit - entry) * qty - commission
             = (46000 - 45000) * 0.5 - 10
             = 500 - 10
             = $490

# Get from backtest
actual_pnl = result.trade_log[0].realized_pnl

# Verify
assert abs(actual_pnl - expected_pnl) < 0.01
```

---

## 🔍 Decision References

Key decisions that constrain Phase 5 implementation:

- **DEC-2026-02-08-002**: SQLAlchemy 2.0 with Mapped[T] (all models)
- **DEC-2026-02-08-003**: Timezone-aware timestamps (all datetime fields)
- **DEC-2026-02-08-006**: 100% type hints (all functions)
- **DEC-2026-02-08-007**: Input validation at model layer (numeric fields)
- **DEC-2026-02-08-008**: Structured logging (all events)
- **DEC-2026-01-15-001**: LOCKED - Asset Class: Crypto ONLY
- **DEC-2026-01-15-002**: LOCKED - Broker: Binance ONLY
- **DEC-2026-01-15-004**: LOCKED - Order Types: Market ONLY

See `.claude/DECISIONS.md` for complete decision log.

---

## 📚 Reference Files

**Phase 5 Specification:**
- [docs/05_PHASE_5_STRATEGY.md](docs/05_PHASE_5_STRATEGY.md)

**PRD Features Implemented:**
- Feature B: Market regime tagging (Session 5A)
- Feature D: Strategy similarity check (Session 5A)

**Phase 4 Integration Points:**
- OrderManager: Used by paper trading to verify integration
- ExecutionEngine: Used for live trading after paper validation

**Phase 2 Integration Points:**
- MarketDataService: Used for OHLCV data
- SymbolManager: Used for symbol validation

---

## 🎓 Learning Resources

### **Strategy Design**
- [Template System](SESSION_5A_IMPLEMENTATION_PROMPT.md) - How templates work
- [Signal Generation](SESSION_5A_IMPLEMENTATION_PROMPT.md) - Entry/exit logic

### **Backtesting**
- [Backtest Determinism](SESSION_5B_IMPLEMENTATION_PROMPT.md) - Why reproducibility matters
- [P&L Calculation](SESSION_5B_IMPLEMENTATION_PROMPT.md#task-533-implement-backtest-metrics-calculator) - Formulas with examples
- [Validation Thresholds](SESSION_5B_IMPLEMENTATION_PROMPT.md#task-537-implement-backtest-validation) - What passes/fails

### **Paper Trading**
- [Two Modes](SESSION_5B_IMPLEMENTATION_PROMPT.md#task-541-create-paper-trading-engine) - Simulated vs Live
- [State Persistence](SESSION_5B_IMPLEMENTATION_PROMPT.md#task-546-implement-paper-trading-state-persistence) - Recovery after crash

### **Testing Patterns**
- [Determinism Test](SESSION_5B_VERIFICATION_PROMPT.md#21-determinism-test) - Verify reproducibility
- [P&L Verification](SESSION_5B_VERIFICATION_PROMPT.md#22-pnl-calculation-verification) - Manual calculation checking

---

## 📞 Support

### **Common Issues**

See debugging sections in:
- [SESSION_5A_VERIFICATION_PROMPT.md - Debugging Guide](SESSION_5A_VERIFICATION_PROMPT.md#-debugging-guide-common-failures--solutions)
- [SESSION_5B_VERIFICATION_PROMPT.md - Debugging Guide](SESSION_5B_VERIFICATION_PROMPT.md#-debugging-guide-backtest--paper-trading-issues)

### **Getting Help**

1. Check relevant debugging section for your error
2. Review code examples in implementation prompt
3. Run tests with verbose output: `pytest -vv`
4. Check logs for structured information
5. Verify decision consistency: `.claude/DECISIONS.md`

---

## 📊 Critical Formulas Quick Reference

| Metric | Formula | Threshold |
|--------|---------|-----------|
| **Win Rate** | (Winners / Total) × 100% | >= 35% |
| **Sharpe Ratio** | (R̄ - Rf) / σ(R) × √252 | >= 0.5 |
| **Max Drawdown** | (Peak - Trough) / Peak × 100% | <= 15% |
| **Profit Factor** | Gross Profit / Gross Loss | >= 1.0 |
| **Similarity** | T×0.4 + P×0.3 + S×0.2 + L×0.1 | < 70% |

---

## 🔒 Invariants Quick Reference

| Invariant | Impact | What to Check |
|-----------|--------|---------------|
| Lifecycle One-Way | Can't undo bad transition | VALID_TRANSITIONS dict |
| Determinism | Results must be reproducible | Run backtest 5+ times |
| 70% Similarity | Reject duplicate strategies | SimilarityChecker logic |
| Timezone Aware | Time ordering must work | All datetime with UTC |
| No NaN/Infinity | P&L must be valid | math.isnan checks |
| 50% Size Reduction | Risk control on mismatch | check_strategy_compatibility |

---

**Last Updated:** 2026-02-14
**Phase 5 Status:** Ready for implementation
**Next Steps:** Start with SESSION_5A_IMPLEMENTATION_PROMPT.md using Plan Mode
