# PHASE 4 IMPLEMENTATION GUIDE
## Execution Infrastructure & Position Tracking
**Quick Reference | Best Practices | Common Patterns**

---

## 📋 Quick Navigation

- **Implementation Prompts:**
  - [SESSION_4A_IMPLEMENTATION_PROMPT.md](SESSION_4A_IMPLEMENTATION_PROMPT.md) - Binance Adapter + Order Manager
  - [SESSION_4B_IMPLEMENTATION_PROMPT.md](SESSION_4B_IMPLEMENTATION_PROMPT.md) - Position Tracker + Execution Quality

- **Verification Prompts:**
  - [SESSION_4A_VERIFICATION_PROMPT.md](SESSION_4A_VERIFICATION_PROMPT.md) - Execution validation
  - [SESSION_4B_VERIFICATION_PROMPT.md](SESSION_4B_VERIFICATION_PROMPT.md) - Position tracking validation

---

## 🎯 Phase 4 at a Glance

| Component | Duration | Tasks | Key Goal |
|-----------|----------|-------|----------|
| **Session 4A** | 45 hours | 18 | Reliable order execution on Binance |
| **Session 4B** | 43 hours | 16 | Accurate position tracking & P&L |
| **Total** | ~88 hours | 34 | End-to-end trading infrastructure |

---

## 🔑 Critical Invariants (Must Not Violate)

### **1. Order Submission Sequence is IMMUTABLE**
```
Risk Check → Create Record → Persist DB → Submit Exchange → Update Status → Start Monitor
                    ↓
            (can fail here without DB impact)
                    ↓
            Order safe in DB before going to exchange
```

**Violation**: Submitting to exchange before persisting to DB → Lost order if app crashes

### **2. Order State Machine is Strictly One-Way**
```
PENDING → SUBMITTED → PARTIALLY_FILLED → FILLED ✓
PENDING → SUBMITTED → CANCELLED ✓
PENDING → REJECTED (risk check failed) ✓

FILLED → CANCELLED ✗ (backward move - ILLEGAL)
SUBMITTED → PENDING ✗ (backward move - ILLEGAL)
```

**Violation**: Allowing state transitions backwards → Duplicate fills, state confusion

### **3. P&L Calculations Must Always Include Commission**
```
❌ Wrong: unrealized = (current - entry) * qty
✅ Right: unrealized = (current - entry) * qty - commission

❌ Wrong: return % = (pnl / qty) * 100
✅ Right: return % = (pnl / (entry * qty)) * 100
```

**Violation**: Commission-free P&L → Profit calculations wrong

### **4. All Timestamps Must Be Timezone-Aware (UTC)**
```
❌ Wrong: created_at = datetime.now()
✅ Right: created_at = datetime.now(timezone.utc)
```

**Violation**: Mixing UTC and local times → Time ordering breaks

### **5. No NaN or Infinity in Financial Values**
```
❌ If current_price is NaN: calculation silently produces NaN
✅ Validate all inputs: if math.isnan(price): raise ValueError
```

**Violation**: NaN silently propagates → Final P&L is NaN

---

## 📊 Data Flow Architecture

### **Session 4A: Order Execution Flow**
```
                    User Request
                         ↓
                  OrderRequest (symbol, side, qty)
                         ↓
                    ┌─────────────┐
                    │OrderManager │
                    └──────┬──────┘
                           ↓
                  ┌─────────────────────┐
                  │ 1. Risk Check ✓ / ✗ │ (memory only)
                  └──────────┬──────────┘
                             ↓
                  ┌──────────────────────┐
                  │ 2. Create Order      │ (memory)
                  │    (PENDING status)  │
                  └──────────┬───────────┘
                             ↓
                  ┌──────────────────────┐
                  │ 3. Persist to DB     │ ⚠️ FIRST IRREVERSIBLE STEP
                  │    (order saved)     │
                  └──────────┬───────────┘
                             ↓
                  ┌──────────────────────────────┐
                  │ 4. Submit to Exchange (Async)│
                  │    ┌──────────────────────┐  │
                  │    │ExecutionEngine       │  │
                  │    │BinanceAdapter        │  │
                  │    └──────────────────────┘  │
                  └──────────┬───────────────────┘
                             ↓
                  ┌──────────────────────┐
                  │ 5. Update Status     │
                  │    (SUBMITTED)       │
                  └──────────┬───────────┘
                             ↓
                  ┌──────────────────────┐
                  │ 6. Start Monitoring  │ (background task)
                  │    Polling interval: │
                  │    - 1s (first 30s)  │
                  │    - 5s (up to 5min) │
                  │    - 10s (after 5min)│
                  └──────────┬───────────┘
                             ↓
                  ┌──────────────────────┐
                  │ 7. Return Order      │
                  │    to caller         │
                  └──────────────────────┘
                             ↓
                        Monitor continues in background...
                             ↓
                  ┌──────────────────────┐
                  │ Poll Exchange Status │
                  └──────────┬───────────┘
                             ↓
                  ┌─────────────────────────────────┐
                  │ Status Change?                  │
                  └────┬────────────────────┬────┬──┘
                       ↓                    ↓    ↓
                   PARTIALLY_FILLED     FILLED CANCELLED
                       │                 │      │
                       └─ Log, update   └─┬────┘
                                           ↓
                                 ┌──────────────────┐
                                 │ _handle_fill()   │
                                 │ - Create Trade   │
                                 │ - Update Position│
                                 │ - Stop Monitor   │
                                 └──────────────────┘
```

### **Session 4B: Position Tracking Flow**
```
         Fill Event (from OrderManager)
                 ↓
         _handle_fill(order)
                 ↓
       ┌─────────────────────┐
       │ Open New Position?  │ (BUY after no position, or add to long)
       │ Update Existing?    │ (Add to existing position)
       │ Close Position?     │ (Sell to close, or reduce)
       └────────┬────────────┘
                ↓
       ┌──────────────────────────────────┐
       │ Calculate New Average Entry Price│
       │ (if adding to position)          │
       │ new_avg = (old_qty*old_avg +    │
       │            new_qty*new_price) / │
       │            (old_qty+new_qty)    │
       └────────┬─────────────────────────┘
                ↓
       ┌──────────────────────────────────┐
       │ Update Position in Database      │
       │ - quantity                       │
       │ - entry_price (if updated avg)   │
       │ - closed_at (if full close)      │
       │ - realized_pnl (if partial close)│
       └────────┬─────────────────────────┘
                ↓
    ┌───────────────────────────────────┐
    │ Position Monitoring               │
    │ (every 5 minutes)                │
    │                                  │
    │ 1. Check staleness (by strategy) │
    │ 2. Alert if exceeded thresholds  │
    │ 3. Auto-close if enabled         │
    └───────────────────────────────────┘
                ↓
      ┌──────────────────────┐
      │ Tracking Metrics     │
      │ - Slippage           │
      │ - Fill rate          │
      │ - P&L accuracy       │
      └──────────────────────┘
```

---

## 📐 Financial Formulas (Must Memorize)

### **1. Unrealized P&L (Open Position)**

```
LONG Position:
  unrealized = (current_price - entry_price) × quantity - commission

SHORT Position:
  unrealized = (entry_price - current_price) × quantity - commission

Example (LONG):
  Entry: 0.5 BTC @ $45,000 = $22,500 invested
  Commission: $5 (on entry)
  Current: $46,000
  unrealized = (46000 - 45000) × 0.5 - 5 = 500 - 5 = $495 ✓
```

### **2. Return Percentage**

```
return_pct = (unrealized_pnl / (entry_price × quantity)) × 100

Example:
  unrealized = $495
  investment = $45,000 × 0.5 = $22,500
  return = (495 / 22500) × 100 = 2.20% ✓
```

### **3. Average Entry Price (Adding to Position)**

```
new_avg = (old_qty × old_avg + new_qty × new_price) / (old_qty + new_qty)

Example:
  Own: 0.5 BTC @ $45,000
  Add: 0.5 BTC @ $44,000
  new_avg = (0.5×45000 + 0.5×44000) / 1.0
  new_avg = (22500 + 22000) / 1.0 = $44,500 ✓
```

### **4. Realized P&L (Closed Position)**

```
realized = (exit_price - entry_price) × quantity - total_commission

Example:
  Entry: 0.5 BTC @ $45,000, commission $5
  Exit: 0.5 BTC @ $46,000, commission $5
  realized = (46000 - 45000) × 0.5 - (5 + 5)
  realized = 500 - 10 = $490 ✓
```

### **5. Slippage**

```
BUY: slippage_pct = ((actual - expected) / expected) × 100
SELL: slippage_pct = ((expected - actual) / expected) × 100

Example (BUY):
  Expected: $45,000
  Actual: $45,050
  slippage = ((45050 - 45000) / 45000) × 100 = 0.111% ✓
```

---

## 🧪 Test Data Templates

### **Test Case: Simple Long Position**
```python
position = Position(
    id="test-long",
    symbol="BTCUSDT",
    side="BUY",
    entry_price=45000.0,
    quantity=0.5,
    commission_paid=5.0,
    opened_at=datetime.now(timezone.utc) - timedelta(hours=2)
)

current_price = 46000.0

# Expected:
# unrealized_pnl = (46000 - 45000) * 0.5 - 5 = 495
# return_pct = (495 / (45000 * 0.5)) * 100 = 2.20%

unrealized = position_tracker.calculate_unrealized_pnl(position, current_price)
assert abs(unrealized - 495.0) < 0.01

return_pct = position_tracker.calculate_return_pct(position, current_price)
assert abs(return_pct - 2.20) < 0.01
```

### **Test Case: Order Submission Flow**
```python
request = OrderRequest(
    account_id="acc-1",
    strategy_id="strategy-1",
    symbol="BTCUSDT",
    side="BUY",
    quantity=0.1,
    type="MARKET"
)

# Expected flow:
# 1. Risk check: approved
# 2. Create Order in memory (PENDING)
# 3. Persist to DB (PENDING)
# 4. Submit to exchange (gets order_id)
# 5. Update DB (SUBMITTED)
# 6. Start monitoring (background)

order = await order_manager.submit_order(request)
assert order.status == OrderStatus.SUBMITTED
assert order.id is not None

# Verify in database
db_order = await data_store.get_order(order.id)
assert db_order is not None
assert db_order.status == OrderStatus.SUBMITTED
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
- [ ] Coverage >90%
- [ ] mypy --strict passes
- [ ] ruff check passes
- [ ] isort check passes
- [ ] All logging includes relevant IDs (order_id, symbol, etc.)
- [ ] All financial calculations verified with manual tests
- [ ] All state transitions follow state machine
- [ ] All timestamps are timezone-aware
- [ ] No NaN/Infinity in financial values
- [ ] All errors logged and tracked

### **After Completing Session**
- [ ] Both implementation and verification prompts completed
- [ ] All tests passing
- [ ] Production audit Grade A- or higher
- [ ] Decision consistency verified
- [ ] Code ready for next session

---

## 🚀 Implementation Tips

### **Tip 1: Build in Stages**
Don't try to implement everything at once. Follow the strict sequence:
1. ExecutionEngine interface (enables all adapters)
2. BinanceExecutionAdapter (enables order submission)
3. OrderManager (enables order tracking)
4. PositionTracker (enables P&L)

### **Tip 2: Test as You Go**
Write unit tests immediately after each task, don't wait until the end:
```python
# Task 4.1.3 (Market order submission)
# Write test immediately:

async def test_market_order_quantity_rounding():
    adapter = BinanceExecutionAdapter(...)
    # Test quantity rounding
```

### **Tip 3: Use Mocking for Fast Iteration**
Mock ExecutionEngine in OrderManager tests to avoid hitting testnet:
```python
# Mock that always returns SUBMITTED
mock_engine.submit_order = AsyncMock(
    return_value=OrderResult(..., status=OrderStatus.SUBMITTED)
)
```

### **Tip 4: Log Aggressively**
Every important operation should log with full context:
```python
logger.info(
    "order_submitted",
    order_id=order.id,
    symbol=order.symbol,
    side=order.side,
    quantity=order.quantity,
    status=order.status.value
)
```

### **Tip 5: Verify Calculations Manually**
For every P&L calculation, verify with a known example:
```python
# Test: Long position with profit
# Entry: 45000, Current: 46000, Qty: 0.5, Commission: 5
# Expected: (46000-45000)*0.5 - 5 = 495
# Your code should match EXACTLY (±0.01 tolerance for rounding)
```

---

## 🔍 Decision References

Key decisions that constrain Phase 4 implementation:

- **DEC-2026-02-08-002**: SQLAlchemy 2.0 with Mapped[T] syntax (all models)
- **DEC-2026-02-08-003**: Timezone-aware timestamps (all datetime fields)
- **DEC-2026-02-08-006**: 100% type hints (all functions)
- **DEC-2026-02-08-007**: Input validation at model layer (all numeric fields)
- **DEC-2026-02-08-008**: Structured logging (all events)

See `.claude/DECISIONS.md` for complete decision log.

---

## 📚 Reference Files

**Phase 4 Specification:**
- [docs/04_PHASE_4_EXECUTION.md](docs/04_PHASE_4_EXECUTION.md)

**PRD Features Implemented:**
- Feature F: Pre-trade slippage estimation (Session 4B)
- Feature I: Order state reconciliation (Session 4A)
- Feature K: Position staleness monitor (Session 4B)

**Phase 3 Integration Points:**
- RiskController: Used in OrderManager.submit_order()
- Kill Switch: Can stop order submission
- Circuit Breakers: Used in risk validation

**Phase 2 Integration Points:**
- MarketDataService: Used for current prices
- SymbolManager: Used for symbol validation
- DataStore: Used for database operations

---

## 🎓 Learning Resources

### **Order Execution Concepts**
- [Order Lifecycle](docs/04_PHASE_4_EXECUTION.md) - State transitions
- [Binance Order Types](https://binance-docs.github.io/apidocs/) - API reference

### **Financial Calculations**
- [P&L Calculation](SESSION_4B_IMPLEMENTATION_PROMPT.md#task-434---implement-pl-calculator) - Formulas with examples
- [Commission Handling](SESSION_4B_IMPLEMENTATION_PROMPT.md#formula-5-realized-pnl-on-close) - How commission affects P&L

### **Testing Patterns**
- [Mock Execution Engine](SESSION_4A_VERIFICATION_PROMPT.md#stage-3-order-manager-validation) - Testing without real orders
- [Test Data Templates](PHASE_4_IMPLEMENTATION_GUIDE.md#test-data-templates) - Reusable test cases

---

## 📞 Support

### **Common Issues**
See debugging sections in:
- [SESSION_4A_VERIFICATION_PROMPT.md - Debugging Guide](SESSION_4A_VERIFICATION_PROMPT.md#-debugging-guide-common-failures--solutions)
- [SESSION_4B_VERIFICATION_PROMPT.md - Debugging Guide](SESSION_4B_VERIFICATION_PROMPT.md#-debugging-guide-pal--position-issues)

### **Getting Help**
1. Check relevant debugging section for your error
2. Review code examples in implementation prompt
3. Run tests with verbose output: `pytest -vv`
4. Check production audit output: `@production-code-audit audit ...`

---

**Last Updated:** 2026-02-13
**Phase 4 Status:** Ready for implementation
**Next Steps:** Start with SESSION_4A_IMPLEMENTATION_PROMPT.md
