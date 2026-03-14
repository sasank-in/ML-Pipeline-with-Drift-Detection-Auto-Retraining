@echo off
REM Setup script for Windows

echo ==========================================
echo   ML Pipeline Setup
echo ==========================================
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
echo For help, see: README.md
echo.
pause
