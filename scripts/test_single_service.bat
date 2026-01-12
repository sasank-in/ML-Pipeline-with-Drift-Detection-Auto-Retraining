@echo off
REM Test a single service to check for errors

echo ==========================================
echo   Testing Single Service
echo ==========================================
echo.

if not exist venv (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Testing Ingestion API...
echo.
python services/ingestion_api/app.py

pause
