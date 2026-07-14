@echo off
title IoMT Research Suite — Launcher
color 0A
cd /d "%~dp0"

echo.
echo  =====================================================
echo    IoMT Research Suite — All 5 Dashboards
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
    echo  IMPORTANT: During installation, tick the box
    echo  "Add Python to PATH" before clicking Install Now.
    echo.
    pause
    exit /b
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  [OK] %%v found.
echo.

:: ── Upgrade pip silently ────────────────────────────────
echo  Upgrading pip...
python -m pip install --upgrade pip --quiet --disable-pip-version-check
echo  [OK] pip ready.
echo.

:: ── Core packages ───────────────────────────────────────
echo  Installing core packages (streamlit, plotly, pandas, numpy)...
pip install streamlit plotly pandas numpy scikit-learn xgboost joblib ^
    openpyxl fpdf2 scipy torch --quiet --disable-pip-version-check
if errorlevel 1 (
    echo.
    echo  [WARN] Some core packages may have had issues.
    echo  Trying again without --quiet to show errors...
    pip install streamlit plotly pandas numpy scikit-learn xgboost joblib ^
        openpyxl fpdf2 scipy torch
)
echo  [OK] Core packages done.
echo.

:: ── PennyLane (quantum) — install separately so errors are visible ──
echo  Installing PennyLane quantum computing library...
pip install pennylane --disable-pip-version-check
if errorlevel 1 (
    color 0C
    echo.
    echo  [ERROR] PennyLane failed to install.
    echo  This is usually a Python version issue.
    echo.
    echo  Try running this command manually:
    echo    pip install pennylane --pre
    echo.
    echo  If that also fails, please contact the researcher.
    pause
    exit /b
)
echo  [OK] PennyLane installed.

echo  Installing PennyLane Lightning simulator...
pip install pennylane-lightning --disable-pip-version-check
if errorlevel 1 (
    echo  [WARN] pennylane-lightning not available — using default simulator instead.
    echo  The dashboards will still work, just slightly slower.
)
echo.

:: ── Verify PennyLane import works ───────────────────────
echo  Verifying quantum library import...
python -c "import pennylane; print('  [OK] PennyLane', pennylane.__version__, 'ready.')"
if errorlevel 1 (
    color 0C
    echo.
    echo  [ERROR] PennyLane installed but cannot be imported.
    echo  Please restart your computer and run START_HERE.bat again.
    pause
    exit /b
)
echo.

:: ── Stop any dashboards already running ─────────────────
echo  Stopping any existing dashboard processes...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: ── Launch all 5 dashboards ──────────────────────────────
echo  Starting dashboards...
echo.

start "8501 MedGuard-IDS" cmd /k "cd /d "%~dp0Med-IoMT" && echo [8501] MedGuard-IDS starting... && python -m streamlit run demo_app.py --server.port 8501 --server.headless true"
echo  [1/5] MedGuard-IDS (8501) starting...
timeout /t 4 /nobreak >nul

start "8502 Hospital HMS" cmd /k "cd /d "%~dp0hospital_workflow_system" && echo [8502] Hospital HMS starting... && python -m streamlit run dashboard.py --server.port 8502 --server.headless true"
echo  [2/5] Hospital HMS (8502) starting...
timeout /t 4 /nobreak >nul

start "8503 Attack Lab" cmd /k "cd /d "%~dp0iomt_attack_lab" && echo [8503] Attack Lab starting... && python -m streamlit run app.py --server.port 8503 --server.headless true"
echo  [3/5] Attack Lab (8503) starting...
timeout /t 4 /nobreak >nul

start "8504 Quantum IDS" cmd /k "cd /d "%~dp0quantum_diagnostic" && echo [8504] Quantum IDS Research starting... && python -m streamlit run app.py --server.port 8504 --server.headless true"
echo  [4/5] Quantum IDS Research (8504) starting...
timeout /t 4 /nobreak >nul

start "8505 Quantum Monitor" cmd /k "cd /d "%~dp0quantum_live_monitor" && echo [8505] Quantum Live Monitor starting... && python -m streamlit run app.py --server.port 8505 --server.headless true"
echo  [5/5] Quantum Live Monitor (8505) starting...
timeout /t 4 /nobreak >nul

:: ── Wait then open browser ───────────────────────────────
echo.
echo  Waiting 20 seconds for dashboards to be ready...
timeout /t 20 /nobreak >nul

echo  Opening in browser...
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
echo    All 5 dashboards launched!
echo  =====================================================
echo.
echo    8501 - MedGuard-IDS (Classical AI)
echo    8502 - MediCore Hospital HMS
echo    8503 - IoMT Attack Lab
echo    8504 - Quantum IDS Research
echo    8505 - Quantum IDS Live Monitor
echo.
echo  If any page shows "ERR_CONNECTION_REFUSED":
echo    Wait 30 seconds and press F5 to refresh.
echo.
echo  Keep the 5 black terminal windows open —
echo  closing them stops the dashboards.
echo.
echo  To stop everything: run STOP_ALL.bat
echo.
pause
