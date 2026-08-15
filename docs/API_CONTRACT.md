# API CONTRACT
## REST API Specification - Paravant Trading System MVP

**Document Version:** 1.0  
**Created:** 2026-02-07  
**Base URL:** `http://localhost:8000/api`  
**Authentication:** None (MVP single-user)  
**V1+:** JWT tokens required

---

## 📋 GENERAL CONVENTIONS

### Response Format

All responses follow this structure:

```json
{
  "status": "success" | "error",
  "data": { ... },          // Present on success
  "error": { ... },         // Present on error
  "timestamp": "2026-02-07T22:00:00Z"
}
```

### Error Response

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "symbol",
      "reason": "Symbol not supported in MVP"
    }
  },
  "timestamp": "2026-02-07T22:00:00Z"
}
```

### HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created
- `400 Bad Request` - Invalid request
- `401 Unauthorized` - Missing or invalid `X-API-Key` on a mutating request
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict (e.g., duplicate)
- `429 Too Many Requests` - Rate limit exceeded on a mutating request; carries a `Retry-After` header
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service unavailable (maintenance)

### Authentication

Every request whose method is `POST`, `PUT`, `PATCH` or `DELETE` must carry a
shared secret in an `X-API-Key` header. `GET` and `OPTIONS` requests are not
gated -- the dashboard is a read-only client, and `OPTIONS` must stay open or
CORS preflight fails before the real request is ever sent.

```
POST /api/v1/orders
X-API-Key: <the value of PARAVANT_API_KEY>
Content-Type: application/json
```

A missing or incorrect key returns `401` with the standard error body. The two
cases are deliberately indistinguishable in the response; the reason is
recorded in the server log only.

The gate is applied in middleware keyed on HTTP method, **not** as a per-route
dependency, so it does **not** appear in the generated OpenAPI schema at
`/docs`. That is a known and accepted trade-off: method-based gating is
fail-closed for endpoints added in future, where a per-route dependency is
fail-open if an author forgets it. See `docs/ARCHITECTURE.md` section 8.1 and
DEC-2026-08-14-001.

Configured via `PARAVANT_API_KEY` (32 characters minimum). Unset in
`ENVIRONMENT=development`, the gate is disabled and startup logs
`api_auth_disabled`; unset in any other environment, startup aborts.

### Rate Limiting

Mutating requests are also rate-capped. Read requests are not.

| Bucket | Env var | Default |
|---|---|---|
| Per client | `API_RATE_LIMIT_PER_MINUTE` | 30/min |
| Global | `API_RATE_LIMIT_GLOBAL_PER_MINUTE` | 120/min |

Exceeding either returns `429` with a `Retry-After` header giving whole seconds
to wait:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 12
Content-Type: application/json

{"detail": "Rate limit exceeded for state-mutating requests. Retry in 12s."}
```

Clients should honour `Retry-After` rather than retrying immediately. Set either
variable to `0` to disable that bucket.

Like the auth gate, this is applied in middleware keyed on HTTP method, so it
does not appear in the OpenAPI schema. See `docs/ARCHITECTURE.md` section 8.2
and DEC-2026-08-14-003.

---

## 🏥 HEALTH & STATUS

### GET `/health`

**Purpose:** Check system health

**Response:**
```json
{
  "status": "success",
  "data": {
    "status": "healthy" | "degraded" | "unhealthy",
    "timestamp": "2026-02-07T22:00:00Z",
    "components": {
      "database": "healthy",
      "exchange_api": "healthy",
      "strategies": "healthy"
    },
    "uptime_seconds": 3600
  }
}
```

---

### GET `/status`

**Purpose:** Get system status summary

**Response:**
```json
{
  "status": "success",
  "data": {
    "mode": "paper_trading" | "live_trading",
    "active_strategies": 3,
    "open_positions": 2,
    "open_orders": 1,
    "total_pnl_usd": 123.45,
    "last_update": "2026-02-07T21:59:50Z"
  }
}
```

---

## 💰 ACCOUNTS

### GET `/accounts`

**Purpose:** List all accounts

**Response:**
```json
{
  "status": "success",
  "data": {
    "accounts": [
      {
        "id": "acc_001",
        "name": "Main Account",
        "broker": "binance",
        "profile": "conservative",
        "status": "active",
        "balance_usdt": 10000.00,
        "equity_usdt": 10123.45,
        "regime": "trending_up",
        "created_at": "2026-01-01T00:00:00Z"
      }
    ],
    "total": 1
  }
}
```

---

### GET `/accounts/{account_id}`

**Purpose:** Get account details

**Response:**
```json
{
  "status": "success",
  "data": {
    "id": "acc_001",
    "name": "Main Account",
    "broker": "binance",
    "profile": "conservative",
    "status": "active",
    "balance_usdt": 10000.00,
    "equity_usdt": 10123.45,
    "regime": "trending_up",
    "risk_config": {
      "max_position_pct": 5.0,
      "max_daily_loss_pct": 2.0,
      "max_drawdown_pct": 10.0
    },
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-02-07T22:00:00Z"
  }
}
```

---

### PUT `/accounts/{account_id}/regime`

**Purpose:** Update account regime (manual tagging)

**Request:**
```json
{
  "regime": "trending_up" | "trending_down" | "ranging" | "volatile" | "unknown"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "id": "acc_001",
    "regime": "trending_up",
    "updated_at": "2026-02-07T22:00:00Z"
  }
}
```

---

## 📊 STRATEGIES

### GET `/strategies`

**Purpose:** List all strategies

**Query Parameters:**
- `account_id` (optional): Filter by account
- `status` (optional): Filter by status (`active`, `paused`, `stopped`)

**Response:**
```json
{
  "status": "success",
  "data": {
    "strategies": [
      {
        "id": "strat_001",
        "account_id": "acc_001",
        "template": "Simple_MA",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "status": "active",
        "regime_filter": ["trending_up", "trending_down"],
        "params": {
          "fast_ma": 20,
          "slow_ma": 50
        },
        "created_at": "2026-01-01T00:00:00Z"
      }
    ],
    "total": 1
  }
}
```

---

### GET `/strategies/{strategy_id}`

**Purpose:** Get strategy details

**Response:**
```json
{
  "status": "success",
  "data": {
    "id": "strat_001",
    "account_id": "acc_001",
    "template": "Simple_MA",
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "status": "active",
    "regime_filter": ["trending_up", "trending_down"],
    "params": {
      "fast_ma": 20,
      "slow_ma": 50,
      "position_size_pct": 5.0
    },
    "performance": {
      "total_trades": 15,
      "win_rate": 0.60,
      "total_pnl_usdt": 234.56,
      "max_drawdown_pct": 3.2
    },
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-02-07T22:00:00Z"
  }
}
```

---

### GET `/strategies/{strategy_id}/signals`

**Purpose:** Get recent signals from strategy

**Query Parameters:**
- `limit` (optional, default: 10): Number of signals to return

**Response:**
```json
{
  "status": "success",
  "data": {
    "signals": [
      {
        "id": "sig_001",
        "strategy_id": "strat_001",
        "timestamp": "2026-02-07T21:00:00Z",
        "direction": "long" | "short" | "close",
        "price": 42500.00,
        "indicators": {
          "fast_ma": 42450.00,
          "slow_ma": 42300.00
        },
        "executed": true
      }
    ],
    "total": 1
  }
}
```

---

## 📈 POSITIONS

### GET `/positions`

**Purpose:** List all open positions

**Query Parameters:**
- `account_id` (optional): Filter by account

**Response:**
```json
{
  "status": "success",
  "data": {
    "positions": [
      {
        "id": "pos_001",
        "account_id": "acc_001",
        "strategy_id": "strat_001",
        "symbol": "BTCUSDT",
        "side": "long" | "short",
        "size": 0.1,
        "entry_price": 42000.00,
        "current_price": 42500.00,
        "pnl_usdt": 50.00,
        "pnl_pct": 1.19,
        "opened_at": "2026-02-07T20:00:00Z"
      }
    ],
    "total": 1,
    "total_pnl_usdt": 50.00
  }
}
```

---

### GET `/positions/{position_id}`

**Purpose:** Get position details

**Response:**
```json
{
  "status": "success",
  "data": {
    "id": "pos_001",
    "account_id": "acc_001",
    "strategy_id": "strat_001",
    "symbol": "BTCUSDT",
    "side": "long",
    "size": 0.1,
    "entry_price": 42000.00,
    "current_price": 42500.00,
    "pnl_usdt": 50.00,
    "pnl_pct": 1.19,
    "opened_at": "2026-02-07T20:00:00Z",
    "updated_at": "2026-02-07T22:00:00Z"
  }
}
```

---

## 📝 ORDERS

### GET `/orders`

**Purpose:** List orders

**Query Parameters:**
- `account_id` (optional): Filter by account
- `status` (optional): Filter by status (`open`, `filled`, `rejected`)
- `limit` (optional, default: 50): Number of orders to return

**Response:**
```json
{
  "status": "success",
  "data": {
    "orders": [
      {
        "id": "ord_001",
        "account_id": "acc_001",
        "strategy_id": "strat_001",
        "symbol": "BTCUSDT",
        "side": "buy" | "sell",
        "type": "market",
        "size": 0.1,
        "status": "open" | "filled" | "rejected",
        "filled_price": 42000.00,
        "created_at": "2026-02-07T20:00:00Z",
        "filled_at": "2026-02-07T20:00:01Z"
      }
    ],
    "total": 1
  }
}
```

---

### GET `/orders/{order_id}`

**Purpose:** Get order details

**Response:**
```json
{
  "status": "success",
  "data": {
    "id": "ord_001",
    "account_id": "acc_001",
    "strategy_id": "strat_001",
    "symbol": "BTCUSDT",
    "side": "buy",
    "type": "market",
    "size": 0.1,
    "status": "filled",
    "filled_price": 42000.00,
    "filled_size": 0.1,
    "exchange_order_id": "binance_123456",
    "created_at": "2026-02-07T20:00:00Z",
    "filled_at": "2026-02-07T20:00:01Z"
  }
}
```

---

## 📉 BACKTESTING

### POST `/backtest`

**Purpose:** Run backtest

**Request:**
```json
{
  "template": "Simple_MA",
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "initial_balance": 10000.00,
  "params": {
    "fast_ma": 20,
    "slow_ma": 50,
    "position_size_pct": 5.0
  }
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "id": "backtest_001",
    "status": "completed",
    "results": {
      "total_trades": 15,
      "win_rate": 0.60,
      "total_return_pct": 12.5,
      "max_drawdown_pct": 4.2,
      "sharpe_ratio": 1.8,
      "final_balance": 11250.00
    },
    "completed_at": "2026-02-07T22:00:05Z"
  }
}
```

---

### GET `/backtest/{backtest_id}`

**Purpose:** Get backtest results

**Response:**
```json
{
  "status": "success",
  "data": {
    "id": "backtest_001",
    "template": "Simple_MA",
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "status": "completed",
    "results": {
      "total_trades": 15,
      "win_rate": 0.60,
      "total_return_pct": 12.5,
      "max_drawdown_pct": 4.2,
      "sharpe_ratio": 1.8,
      "initial_balance": 10000.00,
      "final_balance": 11250.00
    },
    "trades": [
      {
        "entry_date": "2024-01-05T10:00:00Z",
        "exit_date": "2024-01-06T14:00:00Z",
        "side": "long",
        "entry_price": 42000.00,
        "exit_price": 42500.00,
        "pnl_usdt": 25.00
      }
    ],
    "created_at": "2026-02-07T22:00:00Z",
    "completed_at": "2026-02-07T22:00:05Z"
  }
}
```

---

## 📊 ANALYTICS

### GET `/analytics/pnl`

**Purpose:** Get PnL summary

**Query Parameters:**
- `account_id` (required): Account ID
- `period` (optional): `day` | `week` | `month` | `all` (default: `day`)

**Response:**
```json
{
  "status": "success",
  "data": {
    "account_id": "acc_001",
    "period": "day",
    "total_pnl_usdt": 123.45,
    "total_pnl_pct": 1.23,
    "total_trades": 5,
    "winning_trades": 3,
    "losing_trades": 2,
    "win_rate": 0.60,
    "start_balance": 10000.00,
    "end_balance": 10123.45
  }
}
```

---

## 📜 ERROR CODES

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Invalid request parameters |
| `NOT_FOUND` | Resource not found |
| `DUPLICATE` | Resource already exists |
| `RISK_BREACH` | Risk limit breached |
| `API_ERROR` | External API error (Binance) |
| `DATABASE_ERROR` | Database error |
| `INTERNAL_ERROR` | Internal server error |

---

## 📝 NOTES

### MVP Limitations

1. **Single shared API key:** one secret, no user identities, no rotation or
   expiry, and read endpoints are ungated. See the Authentication section above
2. **Rate limiting is a burst cap only:** per-client identity is spoofable,
   buckets are per process and reset on restart, and a leaked key can still be
   used indefinitely within the global cap
3. **No Pagination:** Limited to 50-100 results
4. **No Filtering:** Basic filtering only
5. **No Sorting:** Results in chronological order
6. **No Webhooks:** Polling only

### V1 Features

- Per-user authentication with rotation and revocation
- Shared rate-limit state across processes (currently per worker)
- Full pagination
- Advanced filtering
- WebSocket notifications
- Webhook support

---

**End of Document**
