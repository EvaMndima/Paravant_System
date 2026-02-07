# DATABASE SEED DATA
## Test Data for Development & Testing - Paravant Trading System

**Document Version:** 1.0  
**Created:** 2026-02-07  
**Purpose:** Standardized seed data for unit testing, integration testing, and development

---

## 📋 PURPOSE

This document defines standardized seed data for:
- Unit testing
- Integration testing
- Development environment
- Demo scenarios
- UAT (User Acceptance Testing)

---

## 🗄️ SEED DATA CATEGORIES

### 1. ACCOUNTS

```sql
-- Conservative Account (Default Test Account)
INSERT INTO accounts (id, name, broker, profile, status, balance_usdt, equity_usdt, regime, risk_config, created_at)
VALUES
  ('acc_test_001', 'Test Conservative Account', 'binance', 'conservative', 'active', 10000.00, 10000.00, 'unknown',
   '{"max_position_pct": 5.0, "max_daily_loss_pct": 2.0, "max_drawdown_pct": 10.0}',
   '2026-01-01 00:00:00');

-- Aggressive Account
INSERT INTO accounts (id, name, broker, profile, status, balance_usdt, equity_usdt, regime, risk_config, created_at)
VALUES
  ('acc_test_002', 'Test Aggressive Account', 'binance', 'aggressive', 'active', 25000.00, 25000.00, 'trending_up',
   '{"max_position_pct": 10.0, "max_daily_loss_pct": 5.0, "max_drawdown_pct": 20.0}',
   '2026-01-01 00:00:00');

-- Paused Account (For Testing Account Status)
INSERT INTO accounts (id, name, broker, profile, status, balance_usdt, equity_usdt, regime, risk_config, created_at)
VALUES
  ('acc_test_003', 'Test Paused Account', 'binance', 'conservative', 'paused', 5000.00, 5000.00, 'ranging',
   '{"max_position_pct": 3.0, "max_daily_loss_pct": 1.0, "max_drawdown_pct": 5.0}',
   '2026-01-01 00:00:00');
```

---

### 2. STRATEGIES

```sql
-- Simple MA Strategy (Active)
INSERT INTO strategies (id, account_id, template, symbol, timeframe, status, regime_filter, params, created_at)
VALUES
  ('strat_test_001', 'acc_test_001', 'Simple_MA', 'BTCUSDT', '1h', 'active', 
   '["trending_up", "trending_down"]',
   '{"fast_ma": 20, "slow_ma": 50, "position_size_pct": 5.0}',
   '2026-01-01 00:00:00');

-- Donchian BB Strategy (Active)
INSERT INTO strategies (id, account_id, template, symbol, timeframe, status, regime_filter, params, created_at)
VALUES
  ('strat_test_002', 'acc_test_002', 'Donchian_BB', 'ETHUSDT', '4h', 'active',
   '["trending_up"]',
   '{"donchian_period": 20, "bb_period": 55, "bb_stddev": 2.0, "position_size_pct": 10.0}',
   '2026-01-01 00:00:00');

-- Scalper RSI Strategy (Paused)
INSERT INTO strategies (id, account_id, template, symbol, timeframe, status, regime_filter, params, created_at)
VALUES
  ('strat_test_003', 'acc_test_001', 'Scalper_RSI', 'BNBUSDT', '15m', 'paused',
   '["ranging", "volatile"]',
   '{"rsi_period": 14, "rsi_overbought": 70, "rsi_oversold": 30, "position_size_pct": 3.0}',
   '2026-01-01 00:00:00');
```

---

### 3. POSITIONS

```sql
-- Long Position (Winning)
INSERT INTO positions (id, account_id, strategy_id, symbol, side, size, entry_price, current_price, pnl_usdt, pnl_pct, status, opened_at)
VALUES
  ('pos_test_001', 'acc_test_001', 'strat_test_001', 'BTCUSDT', 'long', 0.1, 42000.00, 42500.00, 50.00, 1.19, 'open', '2026-02-07 20:00:00');

-- Short Position (Losing)
INSERT INTO positions (id, account_id, strategy_id, symbol, side, size, entry_price, current_price, pnl_usdt, pnl_pct, status, opened_at)
VALUES
  ('pos_test_002', 'acc_test_002', 'strat_test_002', 'ETHUSDT', 'short', 1.0, 2500.00, 2520.00, -20.00, -0.80, 'open', '2026-02-07 19:00:00');

-- Closed Position (Winning)
INSERT INTO positions (id, account_id, strategy_id, symbol, side, size, entry_price, current_price, pnl_usdt, pnl_pct, status, opened_at, closed_at)
VALUES
  ('pos_test_003', 'acc_test_001', 'strat_test_001', 'BTCUSDT', 'long', 0.05, 41000.00, 41500.00, 25.00, 1.22, 'closed', '2026-02-06 10:00:00', '2026-02-07 14:00:00');
```

---

### 4. ORDERS

```sql
-- Filled Buy Order
INSERT INTO orders (id, account_id, strategy_id, symbol, side, type, size, status, filled_price, filled_size, exchange_order_id, created_at, filled_at)
VALUES
  ('ord_test_001', 'acc_test_001', 'strat_test_001', 'BTCUSDT', 'buy', 'market', 0.1, 'filled', 42000.00, 0.1, 'binance_123456', '2026-02-07 20:00:00', '2026-02-07 20:00:01');

-- Filled Sell Order
INSERT INTO orders (id, account_id, strategy_id, symbol, side, type, size, status, filled_price, filled_size, exchange_order_id, created_at, filled_at)
VALUES
  ('ord_test_002', 'acc_test_002', 'strat_test_002', 'ETHUSDT', 'sell', 'market', 1.0, 'filled', 2500.00, 1.0, 'binance_789012', '2026-02-07 19:00:00', '2026-02-07 19:00:01');

-- Rejected Order (Insufficient Balance)
INSERT INTO orders (id, account_id, strategy_id, symbol, side, type, size, status, rejection_reason, created_at)
VALUES
  ('ord_test_003', 'acc_test_003', 'strat_test_003', 'BNBUSDT', 'buy', 'market', 10.0, 'rejected', 'Insufficient balance', '2026-02-07 18:00:00');
```

---

### 5. SIGNALS

```sql
-- Long Signal (Executed)
INSERT INTO signals (id, strategy_id, timestamp, direction, price, indicators, executed)
VALUES
  ('sig_test_001', 'strat_test_001', '2026-02-07 20:00:00', 'long', 42000.00, 
   '{"fast_ma": 41950.00, "slow_ma": 41800.00}', 1);

-- Short Signal (Executed)
INSERT INTO signals (id, strategy_id, timestamp, direction, price, indicators, executed)
VALUES
  ('sig_test_002', 'strat_test_002', '2026-02-07 19:00:00', 'short', 2500.00,
   '{"donchian_upper": 2520.00, "donchian_lower": 2400.00, "bb_middle": 2460.00}', 1);

-- Close Signal (Not Executed - Account Paused)
INSERT INTO signals (id, strategy_id, timestamp, direction, price, indicators, executed)
VALUES
  ('sig_test_003', 'strat_test_003', '2026-02-07 18:00:00', 'close', 350.00,
   '{"rsi": 75}', 0);
```

---

## 🧪 EDGE CASES & SPECIAL SCENARIOS

### Risk Breach Scenarios

```sql
-- Account Near Max Daily Loss
INSERT INTO accounts (id, name, broker, profile, status, balance_usdt, equity_usdt, regime, risk_config, created_at)
VALUES
  ('acc_edge_001', 'Near Max Daily Loss', 'binance', 'conservative', 'active', 10000.00, 9810.00, 'volatile',
   '{"max_position_pct": 5.0, "max_daily_loss_pct": 2.0, "max_drawdown_pct": 10.0}',
   '2026-01-01 00:00:00');
-- Current loss: 1.9% (near 2.0% limit)

-- Account Exceeding Max Drawdown
INSERT INTO accounts (id, name, broker, profile, status, balance_usdt, equity_usdt, regime, risk_config, created_at)
VALUES
  ('acc_edge_002', 'Exceeded Max Drawdown', 'binance', 'aggressive', 'active', 10000.00, 8950.00, 'ranging',
   '{"max_position_pct": 10.0, "max_daily_loss_pct": 5.0, "max_drawdown_pct": 10.0}',
   '2026-01-01 00:00:00');
-- Current drawdown: 10.5% (exceeded 10.0% limit)
```

---

### Regime Filtering Scenarios

```sql
-- Strategy Filtered Out by Regime
INSERT INTO strategies (id, account_id, template, symbol, timeframe, status, regime_filter, params, created_at)
VALUES
  ('strat_edge_001', 'acc_test_001', 'Simple_MA', 'BTCUSDT', '1h', 'active',
   '["trending_up"]',  -- Only active in trending_up
   '{"fast_ma": 20, "slow_ma": 50, "position_size_pct": 5.0}',
   '2026-01-01 00:00:00');
-- Account regime is 'unknown', so this strategy should not trade
```

---

### Multiple Positions Scenario

```sql
-- Multiple Positions for Same Strategy
INSERT INTO positions (id, account_id, strategy_id, symbol, side, size, entry_price, current_price, pnl_usdt, pnl_pct, status, opened_at)
VALUES
  ('pos_edge_001', 'acc_test_002', 'strat_test_002', 'ETHUSDT', 'long', 0.5, 2400.00, 2500.00, 50.00, 4.17, 'open', '2026-02-06 10:00:00'),
  ('pos_edge_002', 'acc_test_002', 'strat_test_002', 'ETHUSDT', 'long', 0.5, 2450.00, 2500.00, 25.00, 2.04, 'open', '2026-02-07 12:00:00');
-- Testing: Should aggregate position size and PnL correctly
```

---

## 📊 HISTORICAL OHLCV DATA

### Sample OHLCV Data (BTCUSDT, 1h)

```sql
-- Create table for OHLCV data
CREATE TABLE IF NOT EXISTS ohlcv_test (
  symbol TEXT,
  timeframe TEXT,
  timestamp TIMESTAMP,
  open REAL,
  high REAL,
  low REAL,
  close REAL,
  volume REAL,
  PRIMARY KEY (symbol, timeframe, timestamp)
);

-- Insert sample data (2024-01-01 00:00 to 2024-01-01 10:00)
INSERT INTO ohlcv_test (symbol, timeframe, timestamp, open, high, low, close, volume) VALUES
  ('BTCUSDT', '1h', '2024-01-01 00:00:00', 42000.00, 42100.00, 41900.00, 42050.00, 1000.0),
  ('BTCUSDT', '1h', '2024-01-01 01:00:00', 42050.00, 42200.00, 42000.00, 42150.00, 1200.0),
  ('BTCUSDT', '1h', '2024-01-01 02:00:00', 42150.00, 42300.00, 42100.00, 42250.00, 1100.0),
  ('BTCUSDT', '1h', '2024-01-01 03:00:00', 42250.00, 42250.00, 42050.00, 42100.00, 900.0),
  ('BTCUSDT', '1h', '2024-01-01 04:00:00', 42100.00, 42150.00, 41950.00, 42000.00, 950.0),
  ('BTCUSDT', '1h', '2024-01-01 05:00:00', 42000.00, 42100.00, 41900.00, 42050.00, 1050.0),
  ('BTCUSDT', '1h', '2024-01-01 06:00:00', 42050.00, 42300.00, 42000.00, 42200.00, 1300.0),
  ('BTCUSDT', '1h', '2024-01-01 07:00:00', 42200.00, 42400.00, 42150.00, 42350.00, 1400.0),
  ('BTCUSDT', '1h', '2024-01-01 08:00:00', 42350.00, 42500.00, 42300.00, 42450.00, 1500.0),
  ('BTCUSDT', '1h', '2024-01-01 09:00:00', 42450.00, 42550.00, 42400.00, 42500.00, 1350.0),
  ('BTCUSDT', '1h', '2024-01-01 10:00:00', 42500.00, 42500.00, 42300.00, 42400.00, 1100.0);
```

---

## 🔄 LOADING SEED DATA

### Development Environment

```bash
# Load all seed data
python scripts/load_seed_data.py

# Load specific category
python scripts/load_seed_data.py --category accounts
python scripts/load_seed_data.py --category strategies
```

### Testing Environment

```python
# In test setup
import pytest
from scripts.load_seed_data import load_accounts, load_strategies

@pytest.fixture(scope="function")
def db_with_seed_data(db):
    """Load seed data for tests"""
    load_accounts(db)
    load_strategies(db)
    yield db
    # Cleanup happens via transaction rollback
```

---

## 🧹 CLEANUP

### Reset Database

```sql
-- Delete all data (in order to maintain FK constraints)
DELETE FROM signals;
DELETE FROM orders;
DELETE FROM positions;
DELETE FROM strategies;
DELETE FROM accounts;
DELETE FROM ohlcv_test;
```

### Reset to Seed Data

```bash
# Full reset
python scripts/reset_database.py --load-seed

# Verify
python scripts/verify_seed_data.py
```

---

## 📝 GUIDELINES

### Adding New Seed Data

1. **Consistency:** Use `test_` prefix for test IDs
2. **Clarity:** Use descriptive names
3. **Completeness:** Include all required fields
4. **Validity:** Ensure data passes validation
5. **Documentation:** Add comments explaining purpose

### Test Data Principles

- **Isolation:** Each test should be independent
- **Reproducibility:** Same input → same output
- **Coverage:** Cover happy path and edge cases
- **Realism:** Use realistic values
- **Simplicity:** Keep data minimal and focused

---

## ✅ VERIFICATION

### Verify Seed Data

```sql
-- Count records
SELECT 'accounts' as table_name, COUNT(*) as count FROM accounts
UNION ALL
SELECT 'strategies', COUNT(*) FROM strategies
UNION ALL
SELECT 'positions', COUNT(*) FROM positions
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'signals', COUNT(*) FROM signals;

-- Expected Output:
-- accounts: 5
-- strategies: 4
-- positions: 4
-- orders: 3
-- signals: 3
```

---

**End of Document**
