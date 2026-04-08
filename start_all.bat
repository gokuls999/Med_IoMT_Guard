@echo off
title MedGuard IoMT - Launcher
echo ============================================
echo   MedGuard IoMT System - Starting All 3 Terminals
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ first.
    pause
    exit /b 1
)

:: Install dependencies if needed
echo [1/4] Installing dependencies...
pip install -r "%~dp0requirements.txt" --quiet
echo       Done.
echo.

:: Initialize hospital database
echo [2/4] Initializing hospital database...
cd /d "%~dp0hospital_workflow_system"
if not exist "outputs" mkdir outputs
python -c "from hospital_db import init_database; init_database()" 2>nul
cd /d "%~dp0"
echo       Done.
echo.

:: Start all 3 terminals
echo [3/4] Starting IDS Dashboard (port 8501)...
start "IDS Dashboard" cmd /c "cd /d "%~dp0Med-IoMT" && streamlit run demo_app.py --server.port 8501 --server.headless true"

echo [3/4] Starting Hospital Dashboard (port 8502)...
start "Hospital Dashboard" cmd /c "cd /d "%~dp0hospital_workflow_system" && streamlit run dashboard.py --server.port 8502 --server.headless true"

echo [3/4] Starting Attack Lab (port 8503)...
start "Attack Lab" cmd /c "cd /d "%~dp0iomt_attack_lab" && streamlit run app.py --server.port 8503 --server.headless true"

echo.
echo [4/4] All terminals launched!
echo ============================================
echo   IDS Dashboard:    http://localhost:8501
echo   Hospital System:  http://localhost:8502
echo   Attack Lab:       http://localhost:8503
echo ============================================
echo.
echo Press any key to open all 3 in browser...
pause >nul

start http://localhost:8501
start http://localhost:8502
start http://localhost:8503
