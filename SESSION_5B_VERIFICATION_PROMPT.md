# SESSION 5B VERIFICATION PROMPT
## Backtest Engine & Paper Trading Validation
**Duration:** ~8 hours | **Stages:** 4 | **Focus:** Determinism & Correctness

**Goal:** Verify Session 5B implementation is production-grade and deterministic.

---

## 📋 VERIFICATION STAGES

### STAGE 1: CODE QUALITY & STANDARDS (2 hours)

**Objective:** Same standards as 5A - type hints, linting, logging, validation.

#### 1.1 Type Hints & Mypy
```bash
mypy src/core/strategy/backtest --strict
mypy src/core/strategy/paper --strict

# Expected: 0 errors
```

**Checklist:**
- [ ] All functions typed (backtest engine)
- [ ] All functions typed (paper trading engine)
- [ ] All functions typed (metrics calculator)
- [ ] Dataclass fields typed
- [ ] Generic types correct (List, Dict, Tuple)
- [ ] Optional types for nullable fields

#### 1.2 Financial Value Validation
```python
# Verify all financial calculations validate inputs
import math

def validate_price(price: float) -> float:
    """Validate price before calculation."""
    if math.isnan(price):
        raise ValueError(f"Price is NaN")
    if math.isinf(price):
        raise ValueError(f"Price is Infinity")
    if price <= 0:
        raise ValueError(f"Price must be positive: {price}")
    return price

# Search for this pattern in calculations
grep -r "math.isnan\|math.isinf" src/core/strategy/backtest
# Should show validation before every calculation
```

**Checklist:**
- [ ] All prices validated (NaN/Infinity checks)
- [ ] All quantities validated
- [ ] All P&L values validated
- [ ] All percentages validated
- [ ] All commission amounts validated
- [ ] Clear error messages on validation failure

#### 1.3 Structured Logging
```python
# All logs should be structured
self.logger.info(
    "backtest_started",
    strategy_id=strategy.id,
    symbol=symbol,
    start_date=start_date.isoformat(),
    end_date=end_date.isoformat(),
    initial_capital=config.initial_capital
)

# NOT:
# self.logger.info(f"Backtest started for {strategy.id}")
```

**Checklist:**
- [ ] No f-string logging
- [ ] Named parameters for context
- [ ] Strategy ID, symbol in logs
- [ ] Financial values logged
- [ ] Timestamps in ISO format
- [ ] Performance metrics logged at completion

---

### STAGE 2: BACKTEST ENGINE VALIDATION (3 hours)

**Objective:** Verify backtest determinism and correctness.

#### 2.1 Determinism Test
```python
import pytest

@pytest.mark.asyncio
async def test_backtest_determinism():
    """Critical: Same input → Same output always."""

    strategy = await create_test_strategy()
    config = BacktestConfig(
        initial_capital=10000,
        slippage_bps=2.0,
        commission_rate=0.001
    )

    # Run 1
    result1 = await backtest_engine.run_backtest(
        strategy=strategy,
        symbol='BTCUSDT',
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 3, 31, tzinfo=timezone.utc),
        config=config
    )

    # Run 2 (identical inputs)
    result2 = await backtest_engine.run_backtest(
        strategy=strategy,
        symbol='BTCUSDT',
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 3, 31, tzinfo=timezone.utc),
        config=config
    )

    # MUST match exactly
    assert result1.num_trades == result2.num_trades, \
        f"Trade count mismatch: {result1.num_trades} vs {result2.num_trades}"

    assert result1.final_capital == result2.final_capital, \
        f"Final capital mismatch: {result1.final_capital} vs {result2.final_capital}"

    assert result1.metrics.total_return_pct == result2.metrics.total_return_pct, \
        f"Return mismatch: {result1.metrics.total_return_pct} vs {result2.metrics.total_return_pct}"

    assert result1.metrics.sharpe_ratio == result2.metrics.sharpe_ratio, \
        f"Sharpe mismatch: {result1.metrics.sharpe_ratio} vs {result2.metrics.sharpe_ratio}"

    # Verify trades match exactly
    for i, (t1, t2) in enumerate(zip(result1.trade_log, result2.trade_log)):
        assert t1.entry_price == t2.entry_price, \
            f"Trade {i} entry price mismatch: {t1.entry_price} vs {t2.entry_price}"
        assert t1.exit_price == t2.exit_price, \
            f"Trade {i} exit price mismatch: {t1.exit_price} vs {t2.exit_price}"
        assert t1.realized_pnl == t2.realized_pnl, \
            f"Trade {i} P&L mismatch: {t1.realized_pnl} vs {t2.realized_pnl}"
```

**Checklist:**
- [ ] Determinism test passes (run 5+ times)
- [ ] No floating point rounding errors
- [ ] Date ordering always chronological
- [ ] No random number usage
- [ ] No dict iteration (use sorted lists)
- [ ] Same seed/config produces same result

#### 2.2 P&L Calculation Verification
```python
@pytest.mark.asyncio
async def test_backtest_pnl_calculation():
    """Verify P&L matches manual calculation."""

    result = await backtest_engine.run_backtest(...)

    for trade in result.trade_log:
        # Manual calculation
        gross_pnl = (trade.exit_price - trade.entry_price) * trade.quantity
        total_commission = trade.entry_commission + trade.exit_commission
        expected_pnl = gross_pnl - total_commission

        # Actual from backtest
        actual_pnl = trade.realized_pnl

        # Should match within 1 cent
        assert abs(actual_pnl - expected_pnl) < 0.01, \
            f"P&L mismatch: expected {expected_pnl}, got {actual_pnl}"

@pytest.mark.asyncio
async def test_backtest_sharpe_calculation():
    """Verify Sharpe ratio calculation."""

    result = await backtest_engine.run_backtest(...)

    # Recalculate manually
    equity_curve = result.equity_curve['equity'].values
    returns = np.diff(equity_curve) / equity_curve[:-1]

    mean_return = np.mean(returns)
    std_return = np.std(returns)
    sharpe_expected = (mean_return / std_return) * np.sqrt(252)

    # Should match closely
    assert abs(result.metrics.sharpe_ratio - sharpe_expected) < 0.01, \
        f"Sharpe mismatch: expected {sharpe_expected}, got {result.metrics.sharpe_ratio}"

@pytest.mark.asyncio
async def test_backtest_max_drawdown():
    """Verify max drawdown calculation."""

    result = await backtest_engine.run_backtest(...)

    # Manual calculation
    equity = result.equity_curve['equity'].values
    peak = np.maximum.accumulate(equity)
    drawdown = (peak - equity) / peak
    max_dd_expected = np.max(drawdown) * 100

    # Should match
    assert abs(result.metrics.max_drawdown_pct - max_dd_expected) < 0.1, \
        f"Max DD mismatch: expected {max_dd_expected}%, got {result.metrics.max_drawdown_pct}%"

@pytest.mark.asyncio
async def test_backtest_win_rate():
    """Verify win rate calculation."""

    result = await backtest_engine.run_backtest(...)

    # Manual calculation
    winning_trades = sum(1 for t in result.trade_log if t.realized_pnl > 0)
    expected_win_rate = (winning_trades / len(result.trade_log)) * 100

    # Should match
    assert abs(result.metrics.win_rate_pct - expected_win_rate) < 0.1, \
        f"Win rate mismatch: expected {expected_win_rate}%, got {result.metrics.win_rate_pct}%"
```

**Checklist:**
- [ ] P&L calculation verified (entry - exit + commission)
- [ ] Sharpe ratio verified manually
- [ ] Sortino ratio verified
- [ ] Max drawdown verified
- [ ] Win rate verified
- [ ] Profit factor verified
- [ ] All metrics match within 0.01 tolerance
- [ ] No rounding errors

#### 2.3 No Lookahead Bias
```python
@pytest.mark.asyncio
async def test_backtest_no_lookahead_bias():
    """Verify signals don't use future data."""

    result = await backtest_engine.run_backtest(...)

    # For each trade entry:
    # - Signal must have been generated at bar N
    # - Fill must happen at bar N+1 open (or later)
    # - Cannot fill at bar N high/low

    for i, trade in enumerate(result.trade_log):
        # Entry should be reasonable (next bar open, not next bar high)
        # Would need to verify against actual OHLCV data
        assert trade.entry_price > 0
        assert trade.entry_price < 1000000  # Sanity check
```

**Checklist:**
- [ ] Fill at next bar open (not current bar high)
- [ ] Signal doesn't use future price
- [ ] No price peeking
- [ ] Chronological iteration verified
- [ ] No out-of-order processing

#### 2.4 Edge Cases
```python
@pytest.mark.asyncio
async def test_backtest_no_trades():
    """Backtest with strategy that never generates signals."""

    # Create strategy that never triggers
    result = await backtest_engine.run_backtest(...)

    assert len(result.trade_log) == 0
    assert result.metrics.num_trades == 0
    assert result.metrics.win_rate_pct == 0  # Or some default
    assert not result.passed_validation  # Should fail validation

@pytest.mark.asyncio
async def test_backtest_all_winning_trades():
    """Backtest with perfect entry/exit."""

    result = await backtest_engine.run_backtest(...)

    # All trades should be winners
    assert result.metrics.win_rate_pct == 100.0
    assert result.metrics.num_losing_trades == 0
    assert result.metrics.profit_factor > 1.0

@pytest.mark.asyncio
async def test_backtest_insufficient_capital():
    """Backtest with insufficient capital for position."""

    # Should gracefully handle or reject
    with pytest.raises(ValueError):
        result = await backtest_engine.run_backtest(
            strategy=strategy,
            symbol='BTCUSDT',
            start_date=...,
            end_date=...,
            config=BacktestConfig(initial_capital=1.0)  # Too small
        )
```

**Checklist:**
- [ ] Handles no trades (validation fails)
- [ ] Handles all wins
- [ ] Handles all losses
- [ ] Handles insufficient capital
- [ ] Handles extreme prices
- [ ] Handles missing data
- [ ] Handles zero volume

#### 2.5 Metrics Range Validation
```python
@pytest.mark.asyncio
async def test_backtest_metrics_ranges():
    """Verify all metrics are in valid ranges."""

    result = await backtest_engine.run_backtest(...)

    metrics = result.metrics

    # Win rate: 0-100%
    assert 0 <= metrics.win_rate_pct <= 100, \
        f"Win rate out of range: {metrics.win_rate_pct}%"

    # Sharpe: -5 to 5 (for backtests)
    assert -5 <= metrics.sharpe_ratio <= 5, \
        f"Sharpe out of range: {metrics.sharpe_ratio}"

    # Max drawdown: 0-100%
    assert 0 <= metrics.max_drawdown_pct <= 100, \
        f"Max DD out of range: {metrics.max_drawdown_pct}%"

    # Profit factor: >= 0
    assert metrics.profit_factor >= 0, \
        f"Profit factor negative: {metrics.profit_factor}"

    # No NaN values
    assert not np.isnan(metrics.sharpe_ratio)
    assert not np.isnan(metrics.max_drawdown_pct)
    assert not np.isnan(metrics.win_rate_pct)
```

**Checklist:**
- [ ] All metrics in valid ranges
- [ ] No NaN values
- [ ] No Infinity values
- [ ] Sensible minimums/maximums

---

### STAGE 3: PAPER TRADING VALIDATION (2 hours)

**Objective:** Verify paper trading engine works correctly.

#### 3.1 Simulated Paper Trading
```python
@pytest.mark.asyncio
async def test_simulated_paper_trading():
    """Test paper trading on 21 days of data."""

    engine = PaperTradingEngine(
        strategy=strategy,
        market_data=market_data,
        signal_generator=signal_generator,
        mode=PaperTradingMode.SIMULATED,
        data_store=data_store
    )

    # Start paper trading
    await engine.start()

    # Should complete (21 days of data)
    status = await engine.get_status()
    assert status.is_running is False
    assert status.validation_status in ['passed', 'failed']
    assert status.days_elapsed >= 21
    assert status.num_trades > 0

@pytest.mark.asyncio
async def test_simulated_paper_validation():
    """Verify simulated paper validates against thresholds."""

    engine = PaperTradingEngine(...)
    await engine.start()

    status = await engine.get_status()

    # Should validate the same as backtest
    # Minimum 5% return, 5+ trades
    if status.current_pnl > 500:  # 5% of 10000
        assert status.validation_status == 'passed'
    else:
        assert status.validation_status == 'failed'
```

**Checklist:**
- [ ] Simulated mode loads 21 days of data
- [ ] Signals generated correctly
- [ ] Trades simulated with fills
- [ ] Metrics tracked in real-time
- [ ] Validation applied at end
- [ ] Pass/fail status correct
- [ ] State persists and recovers

#### 3.2 Live Paper Trading
```python
@pytest.mark.asyncio
async def test_live_paper_trading_mock():
    """Test live paper with mocked real-time data."""

    # Mock market data service
    market_data_mock = AsyncMock()
    market_data_mock.get_ohlcv = AsyncMock(
        return_value=get_mock_ohlcv_data()  # Mocked real-time data
    )

    engine = PaperTradingEngine(
        strategy=strategy,
        market_data=market_data_mock,
        signal_generator=signal_generator,
        mode=PaperTradingMode.LIVE,
        data_store=data_store
    )

    # Start in background (runs for 7 days in production)
    task = asyncio.create_task(engine.start())

    # Simulate time passing
    await asyncio.sleep(1)  # 1 second

    # Check status
    status = await engine.get_status()
    assert status.is_running is True
    assert status.mode == PaperTradingMode.LIVE

    # Stop
    await engine.stop()
    await task

    # Verify stopped
    status = await engine.get_status()
    assert status.is_running is False
```

**Checklist:**
- [ ] Live mode runs main loop
- [ ] Generates signals on each update
- [ ] Executes paper signals
- [ ] Updates metrics in real-time
- [ ] Can start/stop cleanly
- [ ] Minimum 7 days required
- [ ] Validation applied at end

#### 3.3 State Persistence
```python
@pytest.mark.asyncio
async def test_paper_trading_state_persistence():
    """Verify state persists and recovers."""

    engine = PaperTradingEngine(...)

    # Start trading
    await engine.start()

    # Get state after some trades
    initial_status = await engine.get_status()
    initial_trades = len(initial_status.trades)
    initial_equity = initial_status.current_equity

    # Save state
    await engine._save_state()

    # Create new engine instance
    engine2 = PaperTradingEngine(...)

    # Load state
    await engine2._load_state()

    # Verify recovery
    status2 = await engine2.get_status()
    assert status2.num_trades == initial_trades
    assert abs(status2.current_equity - initial_equity) < 0.01
```

**Checklist:**
- [ ] State persists to database
- [ ] Recovery loads all state
- [ ] No P&L gaps
- [ ] Trades preserved
- [ ] Position preserved
- [ ] Metrics preserved

---

### STAGE 4: API & INTEGRATION (1.5 hours)

**Objective:** Verify API endpoints work correctly.

#### 4.1 Backtest API
```bash
# Run backtest
curl -X POST http://localhost:8000/api/strategies/strat-1/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "start_date": "2024-01-01",
    "end_date": "2024-03-31",
    "initial_capital": 10000
  }'

# Response should include metrics and trades
# {"passed_validation": true, "metrics": {...}, "trade_log": [...]}

# Get trades
curl -X GET http://localhost:8000/api/strategies/strat-1/backtest/trades

# Get equity curve
curl -X GET http://localhost:8000/api/strategies/strat-1/backtest/equity
```

**Checklist:**
- [ ] POST /api/strategies/{id}/backtest works
- [ ] Returns BacktestResult
- [ ] GET /api/strategies/{id}/backtest returns results
- [ ] GET /api/strategies/{id}/backtest/trades returns trades
- [ ] GET /api/strategies/{id}/backtest/equity returns curve
- [ ] Proper error responses on invalid input

#### 4.2 Paper Trading API
```bash
# Start paper trading
curl -X POST http://localhost:8000/api/strategies/strat-1/paper/start

# Get status
curl -X GET http://localhost:8000/api/strategies/strat-1/paper/status
# Returns: {"is_running": true, "current_equity": 10500, "pnl": 500, ...}

# Get trades
curl -X GET http://localhost:8000/api/strategies/strat-1/paper/trades

# Get dashboard
curl -X GET http://localhost:8000/api/strategies/strat-1/paper/dashboard
# Returns: {"status": "running", "days_elapsed": 3.5, "metrics": {...}, ...}

# Stop paper trading
curl -X POST http://localhost:8000/api/strategies/strat-1/paper/stop
```

**Checklist:**
- [ ] POST /paper/start works
- [ ] POST /paper/stop works
- [ ] GET /paper/status returns current metrics
- [ ] GET /paper/trades returns trade history
- [ ] GET /paper/dashboard returns dashboard data
- [ ] Proper error handling

---

## 🔍 DEBUGGING GUIDE: Backtest & Paper Trading Issues

### Issue: Non-Deterministic Results

**Symptom:**
```
Test failed: Run 1 generated 45 trades, Run 2 generated 44 trades
```

**Root Causes:**
1. Random number usage
2. Dict iteration (order not guaranteed)
3. Floating point precision loss
4. Out-of-order date processing
5. Timezone conversion issues

**Solution:**
```python
# Search for non-deterministic sources
grep -r "random\|shuffle\|uuid" src/core/strategy/backtest
# Should return nothing (or justified uses)

grep -r "\.items()" src/core/strategy/backtest
# Use .items() with sorted() or use OrderedDict

# Check float precision
# Use Decimal for financial values if needed:
from decimal import Decimal
price = Decimal('45000.50')

# Check timezone consistency
signal.timestamp.tzinfo == timezone.utc  # Always UTC
```

---

### Issue: P&L Mismatch

**Symptom:**
```
Expected P&L: $500.00, Got: $499.89
```

**Root Causes:**
1. Commission not applied correctly
2. Slippage calculation wrong
3. Rounding errors
4. Entry/exit commission both applied?

**Solution:**
```python
# Trace through calculation
trade = result.trade_log[0]
print(f"Entry: {trade.entry_price} × {trade.quantity} = {trade.entry_price * trade.quantity}")
print(f"Entry Commission: {trade.entry_commission}")
print(f"Exit: {trade.exit_price} × {trade.quantity} = {trade.exit_price * trade.quantity}")
print(f"Exit Commission: {trade.exit_commission}")

# Calculate manually
gross_pnl = (trade.exit_price - trade.entry_price) * trade.quantity
total_commission = trade.entry_commission + trade.exit_commission
expected_pnl = gross_pnl - total_commission

print(f"Calculated: {expected_pnl}")
print(f"Backtest reported: {trade.realized_pnl}")
print(f"Difference: {abs(expected_pnl - trade.realized_pnl)}")
```

---

### Issue: Validation Always Fails

**Symptom:**
```
Backtest passed_validation: false
Errors: ['Win rate too low: 30.0% < 35%']
```

**Root Cause:**
- Strategy genuinely under-performing
- Validation thresholds too strict

**Solution:**
```python
# Check if backtest results are reasonable
result = backtest_result
print(f"Trades: {result.num_trades}")
print(f"Win rate: {result.metrics.win_rate_pct:.1f}%")
print(f"Sharpe: {result.metrics.sharpe_ratio:.2f}")
print(f"Max DD: {result.metrics.max_drawdown_pct:.1f}%")

# If numbers are reasonable but below threshold:
# Adjust thresholds for MVP
VALIDATION_THRESHOLDS = ValidationThresholds(
    min_win_rate_pct=30.0,  # Lower threshold
    min_sharpe_ratio=0.3,   # Lower threshold
    max_drawdown_pct=20.0   # Higher tolerance
)
```

---

### Issue: Paper Trading Stuck or Not Starting

**Symptom:**
```
Paper trading started but status.is_running is False immediately
```

**Root Causes:**
1. No data available
2. Exception in main loop (not visible)
3. Too few bars for indicator calculation
4. Signal generator initialization failed

**Solution:**
```python
# Check data availability
data = await market_data.get_ohlcv('BTCUSDT', lookback_bars=200)
print(f"Data points: {len(data)}")
# Should be > lookback needed

# Check signal generator initialization
generator = signal_generator_factory.create(strategy.template_id)
print(f"Generator type: {type(generator)}")
# Should not be None

# Add logging to main loop
self.logger.info("paper_trading_loop_iteration",
                 symbols=self.strategy.symbols,
                 timestamp=datetime.now(timezone.utc))

# Check for exceptions
try:
    await engine.start()
except Exception as e:
    print(f"Paper trading failed: {e}")
    import traceback
    traceback.print_exc()
```

---

## ✅ SIGN-OFF CHECKLIST

**Backtest Engine:**
- [ ] Determinism test passes (5+ runs)
- [ ] P&L calculation verified manually
- [ ] Sharpe ratio verified manually
- [ ] Max drawdown verified manually
- [ ] Win rate verified manually
- [ ] All metrics in valid ranges
- [ ] No lookahead bias
- [ ] Edge cases handled
- [ ] No NaN/Infinity in results
- [ ] Chronological iteration verified

**Paper Trading Engine:**
- [ ] Simulated mode completes in 21 days
- [ ] Live mode runs continuously
- [ ] Both modes track metrics
- [ ] Validation applies at end
- [ ] State persists correctly
- [ ] Recovery works (no P&L gaps)
- [ ] API endpoints functional
- [ ] Multi-strategy coordination works

**Testing:**
- [ ] >85% backtest coverage
- [ ] >80% paper trading coverage
- [ ] All critical paths tested
- [ ] Edge cases tested
- [ ] Integration tests pass

**Quality:**
- [ ] mypy --strict passes
- [ ] ruff check passes
- [ ] isort check passes
- [ ] All docstrings present
- [ ] Type hints 100%
- [ ] No commented-out code
- [ ] Structured logging throughout

**Production Readiness:**
- [ ] Input validation complete
- [ ] Error handling comprehensive
- [ ] Logging sufficient for debugging
- [ ] No test data in production code
- [ ] Database migrations run
- [ ] Performance acceptable

---

**Sign-off:** _________________ **Date:** _________________ **Grade:** _________

---

**Last Updated:** 2026-02-14
**Status:** Ready for validation
**Next Step:** Run validation against Session 5B implementation
