@echo off
REM Setup script for Windows

echo ==========================================
echo   ML Pipeline Setup
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
echo.

REM Remove old virtual environment if exists
if exist venv (
    echo Removing old virtual environment...
    rmdir /s /q venv
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Failed to create virtual environment!
    pause
    exit /b 1
)
echo + Virtual environment created
echo.

REM Activate and install dependencies
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment!
    pause
    exit /b 1
)

echo.
echo Installing dependencies (this may take a few minutes)...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies!
    echo Please check your internet connection and try again
    pause
    exit /b 1
)
echo + Dependencies installed
echo.

REM Create directories
echo Creating directories...
if not exist data mkdir data
if not exist logs mkdir logs
if not exist models mkdir models
echo + Directories created
echo.

echo ==========================================
echo   Setup Complete!
echo ==========================================
echo.
echo Next steps:
echo   1. Run: run_all_services.bat
echo   2. Wait 10-15 seconds
echo   3. Open new terminal and run: python demo.py
echo   4. Open browser: http://localhost:8050
echo.
echo For help, see: QUICKSTART.md
echo.
pause
