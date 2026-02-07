# Paravant Trading System

**Personal Autonomous Trading System - MVP**

A production-grade cryptocurrency trading system for personal use, focusing on capital preservation and operational clarity.

## Features (MVP)

- ✅ **Asset Class:** Crypto only (BTCUSDT, ETHUSDT, BNBUSDT)
- ✅ **Broker:** Binance Spot (testnet for development)
- ✅ **Strategy Library:** 6 pre-built templates
- ✅ **Risk Management:** Position sizing, daily loss limits, drawdown protection
- ✅ **Execution:** Market orders with instant fill confirmation
- ✅ **Backtesting:** Historical simulation with key metrics
- ✅ **Monitoring:** Read-only dashboard for positions, orders, PnL
- ✅ **Alerting:** Telegram notifications
- ✅ **Paper Trading:** Simulated execution with real-time data

## Quick Start

### Prerequisites

- Python 3.11+
- Docker Desktop (optional)
- Binance testnet account
- Telegram bot (for alerts)

### Installation

1. **Clone and setup environment:**
```bash
cd Paravant_System
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your Binance testnet API keys and Telegram credentials
```

4. **Initialize database:**
```bash
python scripts/init_db.py
```

5. **Run the system:**
```bash
uvicorn src.api.main:app --reload
```

Visit http://localhost:8000/docs for API documentation.

### Docker (Alternative)

```bash
# Production
docker-compose up

# Development (with hot reload)
docker-compose --profile dev up
```

## Documentation

- **[Environment Setup](docs/ENVIRONMENT_SETUP.md)** - Detailed setup guide
- **[PRD](docs/TRADING_SYSTEM_PRD.md)** - Product requirements
- **[Architecture](docs/ARCHITECTURE.md)** - System design
- **[Indicator Specification](docs/INDICATOR_SPECIFICATION.md)** - Technical indicators
- **[API Contract](docs/API_CONTRACT.md)** - API documentation

## Development

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest -m unit

# With coverage
pytest --cov=src --cov-report=html
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Project Structure

```
Paravant_System/
├── src/                 # Source code
│   ├── api/            # REST API
│   ├── core/           # Business logic
│   ├── data/           # Database models
│   └── brokers/        # Exchange integrations
├── tests/              # Test suite
├── config/             # Configuration files
├── docs/               # Documentation
├── scripts/            # Utility scripts
├── data/               # Runtime data
└── logs/               # Log files
```

## MVP Scope

This is an MVP release. The following features are explicitly **NOT** included:

- ❌ Multi-asset support (stocks, forex)
- ❌ Multiple brokers
- ❌ Limit orders
- ❌ Advanced backtesting (walk-forward, Monte Carlo)
- ❌ Live chart visualization
- ❌ Custom indicator builder
- ❌ Multi-account support

See `docs/TRADING_SYSTEM_PRD.md` for the complete roadmap.

## Safety & Risk

⚠️ **IMPORTANT:**
- Always use **testnet** for development
- Never commit `.env` files
- Start with **paper trading mode**
- Review all strategy configurations
- Monitor risk limits closely

## License

MIT

## Support

For setup issues, see [ENVIRONMENT_SETUP.md](docs/ENVIRONMENT_SETUP.md)

For scope questions, see [MVP Scope Control Rules](.agent/rules/mvp-scope-control.md)
