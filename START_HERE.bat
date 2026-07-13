@echo off
title IoMT Research Suite — Launcher
color 0A
cd /d "%~dp0"

echo.
echo  =====================================================
echo    IoMT Research Suite — All 5 Dashboards
echo  =====================================================
echo.
echo  Dashboards:
echo    8501  MedGuard-IDS (Classical AI Attack Detection)
echo    8502  MediCore Hospital HMS
echo    8503  IoMT Attack Lab
echo    8504  Quantum IDS Research
echo    8505  Quantum IDS Live Monitor
echo.
echo  =====================================================
echo.

:: ── Check Python ────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo  [ERROR] Python is not installed or not on PATH.
    echo.
    echo  Please install Python 3.10 or newer from:
    echo    https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: During installation, tick the box that says
    echo  "Add Python to PATH" before clicking Install Now.
    echo.
    echo  After installing Python, run this file again.
    echo.
    pause
    exit /b
)

echo  [OK] Python found.
echo.

:: ── Install packages (safe to run again — skips already installed) ──
echo  Installing required packages...
echo  (First run takes 3-5 minutes. Subsequent runs are instant.)
echo.
pip install streamlit pandas numpy scikit-learn xgboost torch joblib ^
    plotly openpyxl fpdf2 pennylane pennylane-lightning scipy ^
    --quiet --disable-pip-version-check

echo.
echo  [OK] Packages ready.
echo.

:: ── Stop any dashboards already running ─────────────────
echo  Stopping any existing dashboard processes...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: ── Launch all 5 dashboards ──────────────────────────────
echo  Starting dashboards (each opens in its own window)...
echo.

start "8501 MedGuard-IDS" cmd /k "cd /d "%~dp0Med-IoMT" && echo Starting MedGuard-IDS on port 8501... && python -m streamlit run demo_app.py --server.port 8501 --server.headless true"
echo  [1/5] MedGuard-IDS starting...
timeout /t 4 /nobreak >nul

start "8502 Hospital HMS" cmd /k "cd /d "%~dp0hospital_workflow_system" && echo Starting MediCore Hospital on port 8502... && python -m streamlit run dashboard.py --server.port 8502 --server.headless true"
echo  [2/5] Hospital HMS starting...
timeout /t 4 /nobreak >nul

start "8503 Attack Lab" cmd /k "cd /d "%~dp0iomt_attack_lab" && echo Starting Attack Lab on port 8503... && python -m streamlit run app.py --server.port 8503 --server.headless true"
echo  [3/5] Attack Lab starting...
timeout /t 4 /nobreak >nul

start "8504 Quantum IDS" cmd /k "cd /d "%~dp0quantum_diagnostic" && echo Starting Quantum IDS Research on port 8504... && python -m streamlit run app.py --server.port 8504 --server.headless true"
echo  [4/5] Quantum IDS Research starting...
timeout /t 4 /nobreak >nul

start "8505 Quantum Monitor" cmd /k "cd /d "%~dp0quantum_live_monitor" && echo Starting Quantum Live Monitor on port 8505... && python -m streamlit run app.py --server.port 8505 --server.headless true"
echo  [5/5] Quantum Live Monitor starting...
timeout /t 4 /nobreak >nul

:: ── Wait for apps to fully initialise before opening browser ──
echo.
echo  Waiting for dashboards to be ready (15 seconds)...
timeout /t 15 /nobreak >nul

:: ── Open browser tabs ────────────────────────────────────
echo.
echo  Opening dashboards in your browser...
start "" "http://localhost:8501"
timeout /t 1 /nobreak >nul
start "" "http://localhost:8502"
timeout /t 1 /nobreak >nul
start "" "http://localhost:8503"
timeout /t 1 /nobreak >nul
start "" "http://localhost:8504"
timeout /t 1 /nobreak >nul
start "" "http://localhost:8505"

echo.
echo  =====================================================
echo    All 5 dashboards are now open in your browser!
echo  =====================================================
echo.
echo  If any page shows "ERR_CONNECTION_REFUSED":
echo    Wait 30 seconds, then press F5 to refresh.
echo.
echo  The 5 black windows in the taskbar are the servers.
echo  DO NOT close them — the dashboards need them running.
echo.
echo  To stop everything: run STOP_ALL.bat
echo.
pause
