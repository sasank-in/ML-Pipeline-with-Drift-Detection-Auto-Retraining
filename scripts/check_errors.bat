@echo off
REM Check for common errors

echo ==========================================
echo   Checking for Errors
echo ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.9+ from python.org
    pause
    exit /b 1
) else (
    echo [OK] Python found
    python --version
)

echo.

REM Check virtual environment
if exist venv (
    echo [OK] Virtual environment exists
) else (
    echo [ERROR] Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

echo.

REM Check if venv is activated
call venv\Scripts\activate.bat

echo.
echo Checking imports...
echo.

python -c "import sys; sys.path.insert(0, '.'); from shared.config import Config; print('[OK] shared.config')" 2>nul
if errorlevel 1 (
    echo [ERROR] Cannot import shared.config
) else (
    echo [OK] shared.config
)

python -c "import sys; sys.path.insert(0, '.'); from shared.database import DatabaseManager; print('[OK] shared.database')" 2>nul
if errorlevel 1 (
    echo [ERROR] Cannot import shared.database
) else (
    echo [OK] shared.database
)

python -c "import sys; sys.path.insert(0, '.'); from ml.training.trainer import ModelTrainer; print('[OK] ml.training.trainer')" 2>nul
if errorlevel 1 (
    echo [ERROR] Cannot import ml.training.trainer
) else (
    echo [OK] ml.training.trainer
)

echo.
echo Checking ports...
echo.

netstat -ano | findstr :8001 >nul
if errorlevel 1 (
    echo [OK] Port 8001 is free
) else (
    echo [WARNING] Port 8001 is in use
)

netstat -ano | findstr :8002 >nul
if errorlevel 1 (
    echo [OK] Port 8002 is free
) else (
    echo [WARNING] Port 8002 is in use
)

netstat -ano | findstr :8050 >nul
if errorlevel 1 (
    echo [OK] Port 8050 is free
) else (
    echo [WARNING] Port 8050 is in use
)

echo.
echo ==========================================
echo   Check Complete
echo ==========================================
echo.
echo If all checks passed, you can run:
echo   start_services_simple.bat
echo.
pause
