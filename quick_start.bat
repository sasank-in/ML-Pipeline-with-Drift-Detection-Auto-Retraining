@echo off
REM Quick Start Script for ML Pipeline (Windows)

echo ==========================================
echo   ML Pipeline Quick Start
echo ==========================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo X Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo X Docker Compose is not installed. Please install Docker Compose first.
    pause
    exit /b 1
)

echo + Docker and Docker Compose are installed
echo.

REM Create necessary directories
echo Creating directories...
if not exist data mkdir data
if not exist logs mkdir logs
if not exist models mkdir models

REM Build and start services
echo.
echo Building and starting Docker containers...
docker-compose up --build -d

REM Wait for services to start
echo.
echo Waiting for services to start (30 seconds)...
timeout /t 30 /nobreak >nul

REM Check service health
echo.
echo Checking service health...

curl -s http://localhost:8001/health >nul 2>&1
if errorlevel 1 (
    echo X Ingestion API is not responding
) else (
    echo + Ingestion API is running
)

curl -s http://localhost:8002/health >nul 2>&1
if errorlevel 1 (
    echo X Prediction Service is not responding
) else (
    echo + Prediction Service is running
)

echo.
echo ==========================================
echo   Services Started Successfully!
echo ==========================================
echo.
echo Dashboard: http://localhost:8050
echo Ingestion API: http://localhost:8001
echo Prediction Service: http://localhost:8002
echo.
echo View logs: docker-compose logs -f
echo Stop services: docker-compose down
echo.
echo Run example: python example_pipeline.py
echo.
pause
