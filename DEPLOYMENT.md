# PARAVANT Trading System - Deployment Guide

## Prerequisites

- Python 3.11+
- pip (package manager)
- Git
- SQLite (development) / PostgreSQL 15+ (production)
- Telegram Bot Token (for alerts)
- Binance API keys (for live/paper trading)

---

## 1. Local Development

### First-Time Setup

```bash
# Clone repository
git clone <repo-url>
cd Paravant_System

# Run setup script (creates venv, installs deps, initializes DB)
# Windows:
setup_dev.bat

# Linux/macOS:
chmod +x setup_dev.sh
./setup_dev.sh
```

### Manual Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Verify
python scripts/verify_db.py
```

### Running the API

```bash
# Development mode with auto-reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# API documentation available at:
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

### Running Tests

```bash
# Full test suite with coverage
pytest tests/ -v --cov=src --cov-report=term-missing

# Specific test categories
pytest tests/integration/test_api.py -v          # API tests
pytest tests/integration/test_full_system.py -v   # E2E tests
pytest tests/load/test_performance.py -v          # Performance tests
pytest tests/unit/ -v                              # Unit tests
```

---

## 2. Environment Variables

### Required for Production

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/paravant` |
| `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) | `https://app.example.com` |
| `ENVIRONMENT` | Runtime environment | `production` |
| `PARAVANT_API_KEY` | Shared secret for state-mutating endpoints, 32 chars min. **Startup aborts without it whenever `ENVIRONMENT` is not `development`.** | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `TRADING_MODE` | Trading mode | `paper` or `live` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | `123456:ABC-DEF...` |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for alerts | `-1001234567890` |

> **Upgrading an existing deployment:** `PARAVANT_API_KEY` became mandatory on
> 2026-08-14 (DEC-2026-08-14-001). A deployment that sets `ENVIRONMENT` to
> anything other than `development` will crash-loop until the variable is set.
> That is the intended behaviour -- the alternative is silently serving
> unauthenticated order-placement endpoints. Any client calling a
> `POST`/`PUT`/`PATCH`/`DELETE` endpoint must send the same value in an
> `X-API-Key` header. See [SECURITY.md](SECURITY.md).

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level | `INFO` |
| `BINANCE_API_KEY` | Binance API key | (none) |
| `BINANCE_API_SECRET` | Binance API secret | (none) |
| `BINANCE_TESTNET` | Use Binance testnet | `true` |
| `API_RATE_LIMIT_PER_MINUTE` | Mutating requests per minute, per client. `0` disables | `30` |
| `API_RATE_LIMIT_GLOBAL_PER_MINUTE` | Mutating requests per minute, all clients. `0` disables | `120` |

> Rate-limit buckets live in process memory, so the effective limit is
> multiplied by the number of uvicorn workers and resets on restart. Run a
> single worker unless you raise the limits to match. See
> [SECURITY.md](SECURITY.md) and `docs/ARCHITECTURE.md` section 8.2.

---

## 3. Docker Deployment

### Build

```bash
docker build -t paravant-system:latest .
```

### Run

```bash
docker run -d \
  --name paravant \
  -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e TRADING_MODE=paper \
  -e DATABASE_URL=postgresql://user:pass@db:5432/paravant \
  -e ALLOWED_ORIGINS=https://your-domain.com \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -e TELEGRAM_CHAT_ID=your_chat_id \
  paravant-system:latest
```

### Health Checks

```bash
# Basic health (used by Docker HEALTHCHECK)
curl http://localhost:8000/health

# Detailed health (component breakdown)
curl http://localhost:8000/health/detailed

# Readiness (checks database connectivity)
curl http://localhost:8000/ready
```

---

## 4. Railway Deployment

### Setup

1. Connect your GitHub repository to Railway
2. Railway auto-detects Python and uses `requirements.txt`
3. Set the start command: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`

### Environment Variables

Set all required variables in Railway dashboard:

```
ENVIRONMENT=production
TRADING_MODE=paper
DATABASE_URL=<Railway PostgreSQL URL>
ALLOWED_ORIGINS=<your-frontend-url>
LOG_LEVEL=INFO
```

### Database

1. Add PostgreSQL plugin in Railway
2. Railway provides `DATABASE_URL` automatically
3. Tables are created on first startup

---

## 5. Post-Deployment Verification

### Health Check

```bash
# Should return {"status": "healthy", ...}
curl https://your-domain.com/health

# Should return {"ready": true, "checks": {"database": "ok", ...}}
curl https://your-domain.com/ready
```

### API Endpoints

```bash
# System status
curl https://your-domain.com/api/v1/system/status

# Dashboard summary
curl https://your-domain.com/api/v1/dashboard/summary

# SSE stream (should receive heartbeats)
curl -N https://your-domain.com/api/v1/events/stream
```

### Create Initial Account

```bash
curl -X POST https://your-domain.com/api/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{"name": "Main Account", "profile": "balanced", "initial_balance": 10000}'
```

---

## 6. Monitoring

### Structured Logs

In production, logs are output as JSON for parsing by log aggregators:

```json
{"event": "http_request", "method": "GET", "path": "/api/v1/dashboard/summary", "status_code": 200, "duration_ms": 12.5}
```

### Key Metrics to Monitor

- `/health` response time (should be < 50ms)
- `/health/detailed` component statuses
- HTTP request durations (p95 < 500ms target)
- Error rate (5xx responses)
- SSE subscriber count
- Database connection health

### Alert Conditions

- Health check failure (3 consecutive)
- Kill switch activation
- Circuit breaker trigger
- API error rate > 1%
- Response time p95 > 1000ms

---

## 7. Troubleshooting

### "Module Not Found" Errors

```bash
# Ensure venv is activated
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux

# Reinstall dependencies
pip install -r requirements.txt
```

### Database Connection Failures

```bash
# Verify DATABASE_URL is set correctly
echo $DATABASE_URL

# Test connection
python -c "from src.data.database import engine; print(engine.url)"
```

### CORS Errors

```bash
# Verify ALLOWED_ORIGINS is set
echo $ALLOWED_ORIGINS

# In development, localhost origins are allowed by default
# In production, ALLOWED_ORIGINS must be set explicitly
```

### SSE Connection Drops

- Verify `X-Accel-Buffering: no` header is passed through reverse proxy
- Check nginx/cloudflare proxy timeout settings (must be > 30s)
- Verify `Connection: keep-alive` is preserved

### High Memory Usage

- Check SSE subscriber count (`/health/detailed`)
- Verify EventBus queues are not filling up
- Check for leaked database sessions in logs
