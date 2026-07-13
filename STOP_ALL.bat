@echo off
title IoMT Research Suite — Stop All
color 0C
cd /d "%~dp0"

echo.
echo  =====================================================
echo    Stopping All IoMT Dashboards
echo  =====================================================
echo.
echo  Closing all running dashboard processes...

taskkill /f /im python.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1

timeout /t 2 /nobreak >nul

echo.
echo  [OK] All dashboards stopped.
echo.
echo  Run START_HERE.bat to start them again.
echo.
pause
