# SESSION 6B VERIFICATION PROMPT
## API Layer & Final Testing Validation
## 8 Hours | 4 Validation Stages | Production Readiness

**Objective:** Verify complete system integration, API functionality, 24-hour stability, and production readiness before MVP launch.

**Duration:** 8 hours + 24-hour stability test

---

## STAGE 1: API CODE QUALITY (2 hours)

**Checklist:**
- [ ] All endpoints have type hints (Pydantic models)
- [ ] All responses documented with examples
- [ ] CORS properly configured (not wildcard)
- [ ] Error responses consistent JSON format
- [ ] Request logging captures: method, path, duration, status
- [ ] All sensitive data excluded from logs
- [ ] Response times logged for monitoring
- [ ] No hardcoded values (use config)

**Verification:**
```bash
mypy src/api/ --strict
ruff check src/api/
pytest tests/integration/test_api.py -v --tb=short
```

---

## STAGE 2: BACKTEST DETERMINISM VERIFICATION (3 hours)

**Critical: Backtest Must Be Deterministic**

```python
async def verify_determinism():
    """MANDATORY: Same input must produce identical output."""

    strategy = await load_strategy('simple_ma')
    data = await load_test_data('BTCUSDT', '2024-01-01', '2024-01-31')

    # Run 5 times
    results = []
    for i in range(5):
        result = await backtest_engine.run_backtest(
            strategy=strategy,
            data=data,
            start_date='2024-01-01',
            end_date='2024-01-31'
        )
        results.append(result)

    # All results must be IDENTICAL
    for i in range(1, 5):
        assert results[0].total_return == results[i].total_return
        assert results[0].sharpe_ratio == results[i].sharpe_ratio
        assert results[0].max_drawdown == results[i].max_drawdown
        assert results[0].win_rate == results[i].win_rate
        assert len(results[0].trades) == len(results[i].trades)

        # Verify each trade matches exactly
        for j, trade in enumerate(results[0].trades):
            assert trade.entry_time == results[i].trades[j].entry_time
            assert trade.entry_price == results[i].trades[j].entry_price
            assert trade.exit_price == results[i].trades[j].exit_price

    print("✓ Backtest is deterministic across 5 runs")
```

**Verification Items:**
- [ ] Same data always produces same metrics
- [ ] Trades executed in same order
- [ ] Entry/exit prices match exactly
- [ ] P&L calculations identical (within 1 cent tolerance)
- [ ] No random number usage in backtest
- [ ] No dict ordering issues (use sorted dicts)
- [ ] No timezone issues (all UTC)
- [ ] No floating point precision errors

### **P&L Verification (Manual Calculation)**

```python
# Test case: Manual backtest verification
# Strategy: Simple MA Crossover
# Data: 10 days of OHLCV
# Expected: 2 trades

async def verify_pnl_calculation():
    """Verify P&L calculated correctly."""

    # Trade 1:
    #   Entry: 45000 USDT, 0.5 BTC
    #   Exit: 46000 USDT, 0.5 BTC
    #   Commission: 5 USDT (both ways)
    #   Manual P&L: (46000-45000)*0.5 - 10 = 500 - 10 = 490 USDT

    backtest_result = await engine.run_backtest(...)
    trade1 = backtest_result.trades[0]

    manual_pnl = (trade1.exit_price - trade1.entry_price) * trade1.quantity - trade1.commission
    assert abs(trade1.pnl - manual_pnl) < 0.01  # Allow 1 cent tolerance

    print("✓ P&L calculation matches manual verification")
```

**Verification Items:**
- [ ] Entry P&L matches: (current - entry) * qty - commission
- [ ] Exit P&L accounts for commission both ways
- [ ] Return % uses correct denominator: (P&L / (entry * qty)) * 100
- [ ] Sharpe ratio uses √252 annualization factor
- [ ] Max drawdown calculated from equity curve
- [ ] All calculations match manual verification

---

## STAGE 3: PAPER TRADING & LIVE INTEGRATION (2 hours)

**Simulated Paper Trading (21 days):**
```python
async def verify_simulated_paper():
    """Verify simulated paper trading validates correctly."""

    strategy = await load_strategy('ema_trend')

    # Start simulated paper
    engine = PaperTradingEngine(
        strategy=strategy,
        mode='SIMULATED',  # Last 21 days of data
        data_store=data_store
    )

    await engine.start()

    # Wait for completion
    while engine.is_running():
        await asyncio.sleep(5)

    # Verify validation results
    result = engine.get_final_result()
    assert result.duration_days >= 21
    assert result.min_trades >= 10  # Minimum trades for validation
    assert result.validation_passed == True

    print("✓ Simulated paper trading validated")
```

**Verification Items:**
- [ ] Simulated paper runs on last 21 days
- [ ] Same validation thresholds as backtest
- [ ] Results generated correctly
- [ ] Metrics calculated in real-time
- [ ] State persisted for recovery
- [ ] Live paper runs continuously (7+ days)
- [ ] Both modes track equity curve
- [ ] Metrics updated correctly during paper trading

**Live Paper Integration:**
- [ ] Real-time execution with simulated fills
- [ ] Next bar open fill or next 1-minute fill
- [ ] 7+ day minimum before validation
- [ ] Continuous metrics tracking
- [ ] State recovery on restart

---

## STAGE 4: 24-HOUR STABILITY TEST (Setup 1h + Run 24h)

**Test Procedure:**
1. Start system with all components
2. Activate 3-5 strategies
3. Monitor continuously for 24 hours
4. Collect metrics every hour

**Verification Script:**

```python
async def run_24h_stability_test():
    """Run system for 24 hours, collect metrics hourly."""

    orchestrator = create_orchestrator()
    await orchestrator.start()

    metrics = {
        'start_time': datetime.now(timezone.utc),
        'memory_readings': [],
        'cycle_counts': [],
        'error_logs': [],
        'restarts': 0,
        'crashes': 0
    }

    try:
        for hour in range(24):
            await asyncio.sleep(3600)  # Wait 1 hour

            # Hourly checks
            memory = psutil.virtual_memory()
            metrics['memory_readings'].append(memory.percent)

            status = await orchestrator.get_status()
            metrics['cycle_counts'].append(status['metrics']['cycles_completed'])

            # Check for errors in logs
            error_count = await count_errors_in_logs()
            metrics['error_logs'].append(error_count)

            # Log hourly status
            print(f"Hour {hour+1}: Memory={memory.percent:.1f}%, "
                  f"Cycles={status['metrics']['cycles_completed']}, "
                  f"Errors={error_count}")
    finally:
        await orchestrator.stop(reason="24-hour test complete")

    # Generate report
    generate_stability_report(metrics)
```

**Stability Report Output:**

```
=== 24-Hour Stability Report ===
Duration: 24h 0m 12s
Start Time: 2026-02-14T10:00:00Z
End Time: 2026-02-15T10:00:12Z

System Reliability:
- Restarts: 0
- Crashes: 0
- Manual Stops: 0

Resource Usage:
- Peak Memory: 412MB (45%)
- Avg Memory: 380MB (42%)
- Memory Growth: 3.2% over 24h (acceptable)
- Min Memory: 350MB (38%)

Trading Activity:
- Total Cycles: 2,880 (1 per 30s)
- Strategies Evaluated: 14,400 (5 per cycle)
- Signals Generated: 47
- Paper Trades Executed: 23
- Orders Submitted: 23
- Fill Rate: 100%

System Health:
- ERROR logs: 0
- WARNING logs: 3
- INFO logs: 2,840
- Database Queries: 45,600
- Database Size Growth: 2.1MB

P&L Tracking:
- Starting Capital: $10,000
- Ending Capital: $10,235
- Daily Return: +2.35%
- Max Drawdown: 3.2%
- Sharpe Ratio: 1.8

Data Integrity:
- Positions Sync: ✓ Passed
- P&L Reconciliation: ✓ Passed
- Order History: ✓ Complete
- Alert Delivery: ✓ 100% success

Recommendations:
- All systems performing normally
- Ready for production deployment
```

**Pass Criteria:**
- [ ] Zero restarts or crashes during 24h
- [ ] Memory growth < 5% (starts 350MB, < 368MB at end)
- [ ] All strategy evaluations complete
- [ ] All signals processed correctly
- [ ] No ERROR entries in logs
- [ ] Database integrity maintained
- [ ] 100+ paper trades executed successfully
- [ ] All positions reconciled
- [ ] All P&L calculated correctly

---

## API ENDPOINT VALIDATION

**System Endpoints:**
```bash
# Test status endpoint
curl -X GET http://localhost:8000/api/v1/system/status
# Verify: status, mode, uptime_seconds, metrics

# Test regime endpoint
curl -X GET http://localhost:8000/api/v1/system/regime
# Verify: current_regime, options, affected_strategies

# Test health endpoints
curl -X GET http://localhost:8000/health
curl -X GET http://localhost:8000/health/detailed
curl -X GET http://localhost:8000/health/strategies
# Verify: all components reported correctly
```

**Dashboard Endpoints:**
```bash
# Test summary
curl -X GET http://localhost:8000/api/v1/dashboard/summary
# Verify: portfolio_value, daily_change, open_positions, win_rate_7d, sharpe_ratio_30d

# Test positions
curl -X GET http://localhost:8000/api/v1/dashboard/positions
# Verify: all open positions with live unrealized_pnl

# Test recent trades
curl -X GET http://localhost:8000/api/v1/dashboard/recent-trades
# Verify: last 20 trades with entry/exit prices, P&L

# Test equity curve
curl -X GET "http://localhost:8000/api/v1/dashboard/equity?range=1W"
# Verify: equity points for 1 week with drawdown calculations
```

**SSE Event Stream:**
```javascript
// Test from browser console
const source = new EventSource('http://localhost:8000/api/v1/events/stream?api_key=test');

source.addEventListener('connected', (event) => {
  console.log('Connected:', event.data);
});

source.addEventListener('kill_switch_changed', (event) => {
  console.log('Kill switch event:', event.data);
});

source.addEventListener('position_updated', (event) => {
  console.log('Position updated:', event.data);
});

source.addEventListener('heartbeat', (event) => {
  console.log('Heartbeat:', event.data);
});
```

**Verification Items:**
- [ ] All endpoints return 200 status
- [ ] Response times < 200ms (dashboard) / < 100ms (health)
- [ ] All required fields present
- [ ] Data values realistic (not stale, not garbage)
- [ ] SSE connects and receives heartbeats
- [ ] SSE receives kill switch events
- [ ] SSE receives position updates
- [ ] No HTTP errors or timeouts

---

## LOAD TEST RESULTS

**Expected Results:**
```
Concurrent API Requests (100 simultaneous):
✓ All completed within 500ms
✓ No timeouts or errors
✓ Average response time: 125ms

Dashboard Summary (50 req/s for 60s):
✓ p50: 80ms
✓ p95: 180ms
✓ p99: 250ms
✓ All requests successful

Market Data Processing (1000 candles/batch):
✓ Processing time: 450ms
✓ No skipped candles
✓ Accurate OHLCV parsing

Signal Generation (100 signals/minute):
✓ All signals evaluated
✓ Average evaluation: 5ms per signal
✓ No timeouts

Memory Stability (1000 cycles):
✓ Initial: 350MB
✓ Final: 365MB
✓ Growth: 4.3% (< 5% acceptable)
```

---

## DEBUGGING GUIDE

### **Issue: Tests Hang on Startup Checklist**

**Solutions:**
1. Verify all mocks have no infinite loops
2. Add explicit timeouts to all async operations
3. Check that health_check() methods have timeouts
4. Verify database mock completes quickly

### **Issue: P&L Mismatch in Backtest**

**Solutions:**
1. Verify commission calculated both ways (entry + exit)
2. Check slippage isn't being applied twice
3. Verify correct fill price (next bar open, not current)
4. Check for floating point precision issues
5. Manually calculate expected P&L and compare

### **Issue: 24-Hour Test Crashes After N Hours**

**Solutions:**
1. Check memory usage growth (add gc.collect() if needed)
2. Look for resource leaks (unclosed connections, etc.)
3. Verify database connections are properly closed
4. Check for circular references in objects
5. Look for timeout issues (set explicit timeouts)

### **Issue: SSE Events Not Flowing**

**Solutions:**
1. Verify EventBus is properly initialized
2. Check subscribers are registered for correct events
3. Verify client disconnect handling works
4. Check heartbeat is being sent every 30s
5. Look for buffering issues (X-Accel-Buffering header)

---

## SIGN-OFF CHECKLIST

**API & Integration:**
- [ ] All endpoints return correct data
- [ ] Response times within SLA (< 200ms)
- [ ] CORS configured securely (not wildcard)
- [ ] Error responses consistent
- [ ] SSE event stream working
- [ ] Heartbeat sent every 30s
- [ ] All integrations tested

**System Stability:**
- [ ] 24-hour test passes (zero crashes)
- [ ] Memory growth < 5%
- [ ] All strategy evaluations complete
- [ ] 100+ paper trades executed
- [ ] No ERROR logs
- [ ] All positions reconciled
- [ ] All P&L correct

**Production Readiness:**
- [ ] >90% test coverage
- [ ] All acceptance criteria met
- [ ] Grade A+ quality verified
- [ ] UAT checklist passed
- [ ] Deployment guide ready
- [ ] Rollback procedure documented

**Sign-Off:** _________________ Date: _________________

---

**System Ready for Production Deployment:** YES / NO

**Next Step:** PHASE_6_COMPLETE - Ready for MVP Launch
**Related Files:** SESSION_6B_IMPLEMENTATION_PROMPT.md | PHASE_6_IMPLEMENTATION_GUIDE.md
