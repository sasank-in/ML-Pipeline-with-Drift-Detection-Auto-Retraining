@echo off
REM First-time setup for the ML pipeline (Windows).
REM Creates the runtime directories. Dependencies are installed manually
REM via `conda activate main && pip install -r requirements.txt`.

echo ==========================================
echo   ML Pipeline - First-Time Setup
echo ==========================================
echo.

if not exist data mkdir data
if not exist logs mkdir logs
if not exist models mkdir models
echo [+] Runtime directories ready (data, logs, models)
echo.

echo Next steps:
echo   1. conda activate main
echo   2. pip install -r requirements.txt
echo   3. run_all_services.bat
echo   4. Open http://localhost:8050
echo.
echo For details, see README.md.
echo.
pause
