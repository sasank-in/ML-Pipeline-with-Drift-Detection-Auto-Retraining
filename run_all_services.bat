@echo off
REM Run all services locally without Docker (Windows)

echo ==========================================
echo   Starting ML Pipeline Services
echo ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python is not installed!
    echo Please install Python 3.9+ from python.org
    pause
    exit /b 1
)

echo + Python is installed
python --version
echo.

REM Create directories
echo Creating directories...
if not exist data mkdir data
if not exist logs mkdir logs
if not exist models mkdir models
echo + Directories created
echo.

REM Check if virtual environment exists
if not exist venv (
    echo Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment!
    pause
    exit /b 1
)

REM Install/upgrade dependencies
echo.
echo Installing dependencies (this may take a minute)...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies!
    echo Please check your internet connection and try again
    pause
    exit /b 1
)
echo + Dependencies installed
echo.

REM Start services in separate windows
echo Starting services...
echo This will open 5 windows, one for each service.
echo.

start "Ingestion API - Port 8001" cmd /k "cd /d %CD% && venv\Scripts\activate.bat && python services/ingestion_api/app.py"
timeout /t 2 /nobreak >nul

start "Prediction Service - Port 8002" cmd /k "cd /d %CD% && venv\Scripts\activate.bat && python services/prediction_service/app.py"
timeout /t 2 /nobreak >nul

start "Drift Monitor" cmd /k "cd /d %CD% && venv\Scripts\activate.bat && python services/drift_monitor/monitor.py"
timeout /t 2 /nobreak >nul

start "Retraining Worker" cmd /k "cd /d %CD% && venv\Scripts\activate.bat && python services/retraining_worker/worker.py"
timeout /t 2 /nobreak >nul

start "Dashboard - Port 8050" cmd /k "cd /d %CD% && venv\Scripts\activate.bat && python dashboards/monitoring_app.py"

echo.
echo ==========================================
echo   All Services Started!
echo ==========================================
echo.
echo Services running:
echo   1. Ingestion API - http://localhost:8001
echo   2. Prediction Service - http://localhost:8002
echo   3. Drift Monitor (Background)
echo   4. Retraining Worker (Background)
echo   5. Dashboard - http://localhost:8050
echo.
echo Wait 10-15 seconds for initialization...
echo.
echo Then run in NEW terminal:
echo   venv\Scripts\activate
echo   python demo.py
echo.
echo Dashboard: http://localhost:8050
echo.
echo To stop: run stop_all_services.bat
echo For help: see QUICKSTART.md
echo.
pause
