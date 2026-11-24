@echo off
rem Runs Save Garage from source on Windows: creates a virtual environment on first run.
cd /d "%~dp0.."
if not exist .venv\Scripts\python.exe (
  python -m venv .venv || exit /b 1
  .venv\Scripts\pip install -r requirements.txt || exit /b 1
)
.venv\Scripts\python engine\main.py --open %*
