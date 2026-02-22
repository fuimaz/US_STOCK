@echo off
chcp 65001 >nul
echo ========================================
echo Chan Theory Real-time Signal Scan
echo ========================================
echo.
echo Starting scan at %date% %time%
echo.

cd /d "%~dp0"
python scan_signals_realtime.py

echo.
echo Scan completed at %date% %time%
echo.
pause
