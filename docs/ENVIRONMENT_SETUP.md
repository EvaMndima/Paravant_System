# ENVIRONMENT SETUP GUIDE
## Paravant Trading System - Development Environment

**Document Version:** 1.0  
**Created:** 2026-02-07  
**Last Updated:** 2026-02-07  
**Status:** ACTIVE

---

## 📋 PREREQUISITES

### Required Software

**Mandatory:**
- Python 3.11+ (3.11.7 recommended)
- Git 2.40+
- Docker Desktop 4.20+ (for deployment testing)
- Code Editor (VS Code recommended)

**Accounts:**
- Binance Account (testnet for MVP)
- Telegram Account (for alert notifications)

**Operating Systems:**
- Windows 10/11
- macOS 12+
- Linux (Ubuntu 20.04+, Debian 11+)

---

## 🚀 INSTALLATION STEPS

### 1. Clone Repository

```bash
git clone <repository-url>
cd Paravant_System
```

---

### 2. Python Environment Setup

#### Option A: venv (Recommended for MVP)

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip
```

#### Option B: conda (Alternative)

```bash
# Create conda environment
conda create -n paravant python=3.11.7 -y

# Activate
conda activate paravant

# Upgrade pip
python -m pip install --upgrade pip
```

---

### 3. Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

**Expected Installation Time:** 2-5 minutes

**Verify Installation:**
```bash
python -c "import fastapi, pandas, ccxt; print('✅ Core dependencies installed')"
```

---

### 4. Environment Variables

#### Create `.env` File

```bash
# Copy template
cp .env.example .env

# Edit with your editor
code .env  # VS Code
# or
nano .env  # Terminal
```

#### Required Variables

```env
# ============================================
# DATABASE
# ============================================
DATABASE_URL=sqlite:///./trading_system.db

# ============================================
# BINANCE API (TESTNET FOR MVP)
# ============================================
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_SECRET_KEY=your_testnet_secret_key_here
BINANCE_TESTNET=true
BINANCE_BASE_URL=https://testnet.binance.vision

# How to get testnet keys:
# 1. Visit https://testnet.binance.vision/
# 2. Sign in with GitHub
# 3. Generate API Key
# 4. Copy API Key and Secret Key

# ============================================
# TELEGRAM ALERTS
# ============================================
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# How to get Telegram credentials:
# 1. Create bot: Talk to @BotFather on Telegram
# 2. Send /newbot and follow instructions
# 3. Copy bot token
# 4. Get chat ID: Talk to @userinfobot, copy your ID

# ============================================
# LOGGING
# ============================================
LOG_LEVEL=INFO
LOG_FILE=logs/trading_system.log

# ============================================
# OPTIONAL (MVP Defaults)
# ============================================
# ENVIRONMENT=development
# DEBUG=false
# API_PORT=8000
```

---

### 5. Database Initialization

```bash
# Create database directory
mkdir -p data

# Run database migrations
python scripts/init_db.py

# Verify database
python scripts/verify_db.py
```

**Expected Output:**
```
✅ Database initialized
✅ Tables created: 8
✅ Seed data loaded
✅ Database ready
```

---

### 6. Verify Installation

```bash
# Run system health check
python scripts/health_check.py
```

**Expected Output:**
```
✅ Python version: 3.11.7
✅ Dependencies installed: 47/47
✅ Database connected
✅ Binance API connected (testnet)
✅ Telegram bot connected
✅ Environment variables valid
✅ All checks passed
```

---

## 🧪 RUNNING TESTS

### Run All Tests

```bash
# Run full test suite
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test category
pytest tests/unit/
pytest tests/integration/
```

**Expected Test Results:**
```
==================== 187 tests passed ====================
Coverage: 85%
```

---

## 🏃 RUNNING THE SYSTEM

### Development Mode

```bash
# Start API server
uvicorn src.main:app --reload --port 8000

# In another terminal, start strategy engine
python -m src.core.strategy_engine
```

### Access API

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health

---

## 🐳 DOCKER SETUP (Optional for MVP)

### Build Image

```bash
docker build -t paravant-trading-system .
```

### Run Container

```bash
docker run -p 8000:8000 --env-file .env paravant-trading-system
```

---

## 🛠️ IDE CONFIGURATION

### VS Code (Recommended)

**Extensions:**
- Python (Microsoft)
- Pylance (Microsoft)
- Python Test Explorer
- GitLens
- Docker

**Workspace Settings** (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "editor.formatOnSave": true,
  "editor.rulers": [88],
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    ".pytest_cache": true,
    ".mypy_cache": true
  }
}
```

---

## 🔧 TROUBLESHOOTING

### Issue: Python Version Mismatch

**Symptoms:**
```
ERROR: This project requires Python 3.11+
```

**Solution:**
```bash
# Check Python version
python --version

# Install Python 3.11 from python.org
# Create new environment with correct version
```

---

### Issue: Binance API Connection Failed

**Symptoms:**
```
ERROR: Binance API connection failed: Invalid API-key
```

**Solution:**
1. Verify you're using **testnet** credentials
2. Check `.env` has correct `BINANCE_TESTNET=true`
3. Regenerate API keys at https://testnet.binance.vision/

---

### Issue: Database Locked

**Symptoms:**
```
ERROR: database is locked
```

**Solution:**
```bash
# Stop all running processes
# Delete database
rm trading_system.db

# Reinitialize
python scripts/init_db.py
```

---

### Issue: Module Not Found

**Symptoms:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

---

### Issue: Telegram Bot Not Working

**Symptoms:**
```
ERROR: Telegram bot connection failed
```

**Solution:**
1. Verify `TELEGRAM_BOT_TOKEN` is correct
2. Ensure bot is not blocked
3. Test token manually:
   ```bash
   curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe
   ```

---

## 📂 PROJECT STRUCTURE

```
Paravant_System/
├── .env                    # Environment variables (DO NOT COMMIT)
├── .env.example            # Environment template
├── .gitignore
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── pytest.ini              # Pytest configuration
├── pyproject.toml          # Project metadata
├── README.md
├── docs/                   # Documentation
│   ├── TRADING_SYSTEM_PRD.md
│   ├── ARCHITECTURE.md
│   ├── INDICATOR_SPECIFICATION.md
│   └── ENVIRONMENT_SETUP.md
├── src/                    # Source code
│   ├── core/               # Core business logic
│   ├── indicators/         # Technical indicators
│   ├── strategies/         # Trading strategies
│   ├── risk/               # Risk management
│   ├── execution/          # Order execution
│   ├── data/               # Data layer
│   ├── api/                # REST API
│   └── utils/              # Utilities
├── tests/                  # Tests
│   ├── unit/
│   ├── integration/
│   └── data/               # Test data
├── scripts/                # Utility scripts
│   ├── init_db.py
│   ├── verify_db.py
│   └── health_check.py
├── logs/                   # Log files (auto-created)
└── data/                   # Runtime data (auto-created)
```

---

## 🔐 SECURITY BEST PRACTICES

### Environment Variables

- ❌ **NEVER** commit `.env` to git
- ✅ Use `.env.example` as template
- ✅ Use testnet for development
- ✅ Rotate API keys regularly

### API Keys

- ❌ Never share API keys
- ❌ Never use production keys in development
- ✅ Use testnet keys for MVP
- ✅ Restrict API key permissions (read-only for testing)

---

## 📊 PERFORMANCE EXPECTATIONS

### Development Environment

- **API Response Time:** < 100ms
- **Indicator Calculation (10k candles):** < 100ms
- **Strategy Backtest (1 month):** < 5 seconds
- **Database Query:** < 10ms

### Hardware Recommendations

**Minimum:**
- 4 GB RAM
- 10 GB disk space
- 2 CPU cores

**Recommended:**
- 8 GB RAM
- 20 GB disk space
- 4 CPU cores

---

## 🔄 UPDATING DEPENDENCIES

### Check for Updates

```bash
pip list --outdated
```

### Update Specific Package

```bash
pip install --upgrade <package-name>

# Update requirements.txt
pip freeze > requirements.txt
```

### Update All Packages (⚠️ Use with Caution)

```bash
pip install --upgrade -r requirements.txt
```

**⚠️ Warning:** Always test after updating dependencies.

---

## 🧹 CLEANUP

### Reset Environment

```bash
# Deactivate virtual environment
deactivate

# Remove virtual environment
rm -rf .venv

# Remove database
rm trading_system.db

# Remove logs
rm -rf logs/

# Remove cache
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type d -name ".pytest_cache" -exec rm -rf {} +
```

---

## 📞 GETTING HELP

### Common Issues

1. Check `TROUBLESHOOTING` section above
2. Check `docs/` for relevant documentation
3. Run `python scripts/health_check.py`

### System Information

```bash
# Python version
python --version

# Installed packages
pip list

# Environment variables (DO NOT share full output)
python -c "import os; print([k for k in os.environ if k.startswith('BINANCE') or k.startswith('TELEGRAM')])"
```

---

## ✅ CONFIGURATION CHECKLIST

Before starting development, verify:

- [ ] Python 3.11+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created with all required variables
- [ ] Binance testnet API keys configured
- [ ] Telegram bot configured
- [ ] Database initialized (`python scripts/init_db.py`)
- [ ] Health check passed (`python scripts/health_check.py`)
- [ ] Tests pass (`pytest`)
- [ ] IDE configured with linting and formatting

---

## 🚦 NEXT STEPS

After setup is complete:

1. Read `docs/TRADING_SYSTEM_PRD.md` for system overview
2. Read `docs/ARCHITECTURE.md` for technical architecture
3. Review `docs/INDICATOR_SPECIFICATION.md` for indicator details
4. Read `docs/README.md` for the documentation index. The original phase
   plans are complete and archived under `docs/archive/build-plans/`.

---

**End of Document**
