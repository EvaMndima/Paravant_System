# Development Environment Setup Guide

This guide explains how to set up your local development environment for the PARAVANT Trading System.

## Quick Start (Recommended)

### Windows

Run the automated setup script:

```bash
setup_dev.bat
```

This will:
- Create a virtual environment in `.venv/`
- Install all dependencies (production + development)
- Initialize the database
- Activate the environment

### Linux/macOS

Make the script executable and run it:

```bash
chmod +x setup_dev.sh
./setup_dev.sh
```

---

## Manual Setup (If Scripts Don't Work)

### Prerequisites

- **Python 3.11 or higher** - Check with `python --version`
- **pip** - Should be included with Python
- **Git** - For version control

### Step-by-Step

1. **Create Virtual Environment**

   ```bash
   # Windows
   python -m venv .venv

   # Linux/macOS
   python3 -m venv .venv
   ```

2. **Activate Virtual Environment**

   ```bash
   # Windows
   .venv\Scripts\activate

   # Linux/macOS
   source .venv/bin/activate
   ```

   You should see `(.venv)` in your terminal prompt.

3. **Upgrade pip**

   ```bash
   python -m pip install --upgrade pip
   ```

4. **Install Dependencies**

   ```bash
   # Production dependencies
   pip install -r requirements.txt

   # Development dependencies (optional but recommended)
   pip install -r requirements-dev.txt
   ```

5. **Configure Environment Variables**

   ```bash
   # Copy the example file
   cp .env.example .env

   # Edit .env with your settings (API keys, etc.)
   ```

6. **Initialize Database**

   ```bash
   python scripts/init_db.py
   ```

7. **Verify Setup**

   ```bash
   python scripts/verify_db.py
   python scripts/health_check.py
   ```

---

## Running the System

### Start API Server

```bash
uvicorn src.api.main:app --reload
```

Visit http://localhost:8000/docs for interactive API documentation.

### Run Tests

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

---

## Quick Activation (After Initial Setup)

### Windows

```bash
activate.bat
```

Or manually:

```bash
.venv\Scripts\activate
```

### Linux/macOS

```bash
source .venv/bin/activate
```

---

## Deactivating

When you're done working, deactivate the virtual environment:

```bash
deactivate
```

---

## Docker Alternative

If you prefer not to set up a local Python environment, you can use Docker.
No `.env` and no other setup is required — the compose file declares working
defaults for everything.

```bash
# Start the API (creates the database schema first, then serves on :8000)
docker compose up --build

# Check it
curl http://localhost:8000/health

# Development mode, with hot reload, on :8001
docker compose --profile dev up
```

Note `docker compose` (a subcommand of Docker) rather than the older
standalone `docker-compose` binary, which is end-of-life.

Two things the compose file does deliberately:

- **It runs `scripts/init_db.py` before starting the API.** `init_db()` is a
  function nothing calls at import, so without this the API would boot and
  then fail every query with "no such table". It is idempotent, so restarts
  are safe.
- **`LIVE_TRADING_ENABLED` and `BINANCE_TESTNET` are hardcoded, not
  interpolated.** Compose reads a local `.env` for `${VAR}` substitution, so
  inheriting them would point a local demo container at whatever a developer's
  `.env` selects — including mainnet. No Binance credentials are passed into
  the container at all.

Set `PARAVANT_API_KEY` in your environment or `.env` to exercise the API key
gate; leave it unset and the gate stays off in development. See
[SECURITY.md](SECURITY.md).

---

## Troubleshooting

### "Python not found"

**Windows:** Install Python from [python.org](https://www.python.org/downloads/) and make sure to check "Add Python to PATH" during installation.

**Linux:** Install Python 3.11+ using your package manager:
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3.11 python3.11-venv

# macOS (using Homebrew)
brew install python@3.11
```

### "Module not found" errors

Make sure your virtual environment is activated (you should see `(.venv)` in your prompt). If not:

```bash
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

Then reinstall dependencies:

```bash
pip install -r requirements.txt
```

### Database initialization fails

Check that the `data/` directory exists and you have write permissions:

```bash
# Windows
mkdir data

# Linux/macOS
mkdir -p data
chmod 755 data
```

### Port 8000 already in use

Either kill the process using port 8000, or run on a different port:

```bash
uvicorn src.api.main:app --reload --port 8001
```

---

## Why Virtual Environments?

Virtual environments isolate your project dependencies from system Python and other projects. Benefits:

- **No conflicts** - Each project has its own dependencies
- **Reproducible** - `requirements.txt` ensures everyone has the same versions
- **Clean** - Easily delete and recreate if something breaks
- **No sudo** - Install packages without administrator privileges

---

## Why venv (not conda)?

This project uses `venv` (Python's built-in virtual environment) instead of Conda because:

1. **Lightweight** - venv is part of Python, no extra software needed
2. **Standard** - Uses pip and PyPI, the standard Python ecosystem
3. **Fast** - Faster activation and package installation
4. **Project match** - We use `pyproject.toml` and `requirements.txt` (pip standard)
5. **Docker-first** - Production uses Docker, local environment is just for development

Conda is excellent for data science projects with C/C++ dependencies (NumPy, SciPy, etc.), but this project is pure Python with standard web/trading libraries.

---

## Editor/IDE Setup

### VS Code

Install the Python extension and select the virtual environment:

1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS)
2. Type "Python: Select Interpreter"
3. Choose `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (Linux/macOS)

### PyCharm

1. Go to **Settings** → **Project** → **Python Interpreter**
2. Click the gear icon → **Add**
3. Select **Existing environment**
4. Choose `.venv/Scripts/python.exe` or `.venv/bin/python`

---

## Getting Help

- **Documentation issues:** Check [README.md](README.md)
- **Setup problems:** See this file's Troubleshooting section
- **Code questions:** Check [ARCHITECTURE.md](docs/ARCHITECTURE.md) and [API_CONTRACT.md](docs/API_CONTRACT.md)
- **Bugs:** Create an issue (if using GitHub)

---

**Happy coding!** 🚀
