@echo off
REM Stop all services (Windows)

echo ==========================================
echo   Stopping ML Pipeline Services
echo ==========================================
echo.

REM Kill Python processes running our services
echo Stopping services...

taskkill /FI "WINDOWTITLE eq Ingestion API*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Prediction Service*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Drift Monitor*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Retraining Worker*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Dashboard*" /F >nul 2>&1

echo.
echo + All services stopped
echo.
pause
