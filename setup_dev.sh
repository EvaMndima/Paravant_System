#!/bin/bash
# Development Environment Setup Script for Linux/macOS
# This script creates and activates a virtual environment with all dependencies

set -e  # Exit on error

echo ""
echo "============================================"
echo "   PARAVANT Development Environment Setup"
echo "============================================"
echo ""

# Check if Python 3.11+ is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.11 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "Found Python $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "Virtual environment created successfully"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
python -m pip install --upgrade pip --quiet

# Install production dependencies
echo ""
echo "Installing production dependencies..."
pip install -r requirements.txt --quiet

# Install development dependencies
echo ""
echo "Installing development dependencies..."
pip install -r requirements-dev.txt --quiet || echo "WARNING: Failed to install dev dependencies"

# Initialize database
echo ""
echo "Initializing database..."
python scripts/init_db.py || echo "WARNING: Database initialization failed"

echo ""
echo "============================================"
echo "   Setup Complete!"
echo "============================================"
echo ""
echo "Virtual environment is activated."
echo ""
echo "Next steps:"
echo "  1. Copy .env.example to .env and configure your settings"
echo "  2. Run the API server: uvicorn src.api.main:app --reload"
echo "  3. Visit http://localhost:8000/docs for API documentation"
echo ""
echo "To activate this environment in the future, run:"
echo "  source .venv/bin/activate"
echo ""
