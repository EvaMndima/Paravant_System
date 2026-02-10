@echo off
REM Development Environment Setup Script for Windows
REM This script creates and activates a virtual environment with all dependencies

echo.
echo ============================================
echo   PARAVANT Development Environment Setup
echo ============================================
echo.

REM Check if Python 3.11+ is available
python --version 2>NUL
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or higher from python.org
    exit /b 1
)

REM Check Python version
for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

REM Create virtual environment if it doesn't exist
if not exist ".venv\" (
    echo.
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        exit /b 1
    )
    echo Virtual environment created successfully
) else (
    echo Virtual environment already exists
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    exit /b 1
)

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install production dependencies
echo.
echo Installing production dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install production dependencies
    exit /b 1
)

REM Install development dependencies
echo.
echo Installing development dependencies...
pip install -r requirements-dev.txt --quiet
if errorlevel 1 (
    echo WARNING: Failed to install development dependencies
    echo You can continue without dev dependencies
)

REM Initialize database
echo.
echo Initializing database...
python scripts\init_db.py
if errorlevel 1 (
    echo WARNING: Database initialization failed
    echo You may need to initialize manually with: python scripts\init_db.py
)

echo.
echo ============================================
echo   Setup Complete!
echo ============================================
echo.
echo Virtual environment is activated.
echo.
echo Next steps:
echo   1. Copy .env.example to .env and configure your settings
echo   2. Run the API server: uvicorn src.api.main:app --reload
echo   3. Visit http://localhost:8000/docs for API documentation
echo.
echo To activate this environment in the future, run:
echo   .venv\Scripts\activate
echo.

REM Keep the window open
cmd /k
