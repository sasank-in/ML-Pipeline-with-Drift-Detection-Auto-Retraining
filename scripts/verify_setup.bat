@echo off
REM Verify that setup is complete and everything is ready

echo ==========================================
echo   Verifying Setup
echo ==========================================
echo.

REM Check Python
echo [1/7] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Python not found
    echo Please install Python 3.9+ from python.org
    goto :failed
) else (
    python --version
    echo [PASS] Python found
)
echo.

REM Check virtual environment
echo [2/7] Checking virtual environment...
if exist venv (
    echo [PASS] Virtual environment exists
) else (
    echo [FAIL] Virtual environment not found
    echo Please run: setup.bat
    goto :failed
)
echo.

REM Activate venv
echo [3/7] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [FAIL] Cannot activate virtual environment
    goto :failed
) else (
    echo [PASS] Virtual environment activated
)
echo.

REM Check dependencies
echo [4/7] Checking dependencies...
python -c "import sklearn; import pandas; import numpy; import flask; import dash" 2>nul
if errorlevel 1 (
    echo [FAIL] Some dependencies missing
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [FAIL] Failed to install dependencies
        goto :failed
    )
    echo [PASS] Dependencies installed
) else (
    echo [PASS] All dependencies installed
)
echo.

REM Check directories
echo [5/7] Checking directories...
if not exist data mkdir data
if not exist logs mkdir logs
if not exist models mkdir models
echo [PASS] Directories ready
echo.

REM Check data file
echo [6/7] Checking data file...
if exist data\lung_disease.csv (
    echo [PASS] lung_disease.csv found
) else (
    if exist lung_disease.csv (
        echo [INFO] Moving lung_disease.csv to data folder...
        move lung_disease.csv data\
        echo [PASS] lung_disease.csv moved
    ) else (
        echo [WARN] lung_disease.csv not found
        echo Demo will create sample data
    )
)
echo.

REM Check ports
echo [7/7] Checking ports...
netstat -ano | findstr :8001 >nul
if errorlevel 1 (
    echo [PASS] Port 8001 is free
) else (
    echo [WARN] Port 8001 is in use
)

netstat -ano | findstr :8002 >nul
if errorlevel 1 (
    echo [PASS] Port 8002 is free
) else (
    echo [WARN] Port 8002 is in use
)

netstat -ano | findstr :8050 >nul
if errorlevel 1 (
    echo [PASS] Port 8050 is free
) else (
    echo [WARN] Port 8050 is in use
)
echo.

echo ==========================================
echo   Verification Complete - ALL CHECKS PASSED!
echo ==========================================
echo.
echo Your setup is ready!
echo.
echo Next steps:
echo   1. Run: run_all_services.bat
echo   2. Wait 10 seconds
echo   3. Run: python demo.py
echo   4. Open: http://localhost:8050
echo.
pause
exit /b 0

:failed
echo.
echo ==========================================
echo   Verification Failed
echo ==========================================
echo.
echo Please fix the issues above and try again.
echo.
echo If you need help:
echo   - Check START_HERE.txt
echo   - Check TROUBLESHOOTING.md
echo   - Run setup.bat again
echo.
pause
exit /b 1
