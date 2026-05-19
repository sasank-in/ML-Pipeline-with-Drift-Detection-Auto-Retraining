@echo off
REM Run all services locally (Windows).
REM Each service runs in its own window with the `main` conda env activated.

echo ==========================================
echo   Starting ML Pipeline Services
echo ==========================================
echo.

REM Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python is not installed!
    echo Please install Python 3.9+ from python.org
    pause
    exit /b 1
)

echo [+] Python found
python --version
echo.

REM Ensure runtime directories exist
if not exist data mkdir data
if not exist logs mkdir logs
if not exist models mkdir models

REM Start each service in a separate window
echo Starting 5 services (5 new windows)...
echo.

start "Ingestion API - Port 8001" cmd /k "cd /d %CD% && conda activate main && python services/ingestion_api/app.py"
timeout /t 2 /nobreak >nul

start "Prediction Service - Port 8002" cmd /k "cd /d %CD% && conda activate main && python services/prediction_service/app.py"
timeout /t 2 /nobreak >nul

start "Drift Monitor" cmd /k "cd /d %CD% && conda activate main && python services/drift_monitor/monitor.py"
timeout /t 2 /nobreak >nul

start "Retraining Worker" cmd /k "cd /d %CD% && conda activate main && python services/retraining_worker/worker.py"
timeout /t 2 /nobreak >nul

start "Dashboard - Port 8050" cmd /k "cd /d %CD% && conda activate main && python dashboards/monitoring_app.py"

echo.
echo ==========================================
echo   All Services Started
echo ==========================================
echo.
echo Endpoints:
echo   - Ingestion API:      http://localhost:8001
echo   - Prediction Service: http://localhost:8002
echo   - Dashboard:          http://localhost:8050
echo.
echo Wait ~10 seconds for services to initialise, then visit the dashboard.
echo.
echo To stop everything: stop_all_services.bat
echo.
pause
