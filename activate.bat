@echo off
REM Quick activation script for Windows
REM Usage: activate.bat

if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found
    echo Please run setup_dev.bat first to create the environment
    exit /b 1
)

call .venv\Scripts\activate.bat
echo Virtual environment activated!
echo To deactivate, run: deactivate
cmd /k
