# Real-Time ML Pipeline with Auto-Retraining & Drift Detection

A production-ready machine learning pipeline with automatic drift detection and model retraining, built using microservices architecture.

## Features

- **5 Microservices Architecture**: Ingestion API, Prediction Service, Drift Monitor, Retraining Worker, Dashboard
- **Automatic Drift Detection**: Monitors data distribution changes in real-time
- **Auto-Retraining**: Automatically retrains models when drift is detected
- **Real-Time Monitoring**: Live dashboard with metrics and visualizations
- **Production-Ready**: Complete logging, error handling, and database management

## Quick Start

### 1. Setup (First Time Only)

```bash
# Windows
setup.bat

# Linux/Mac
chmod +x setup.sh
./setup.sh
```

### 2. Start Services

```bash
# Windows
run_all_services.bat

# Linux/Mac
./run_all_services.sh
```

Wait 10-15 seconds for services to initialize.

### 3. Run Demo

Open a new terminal:

```bash
# Windows
venv\Scripts\activate
python demo.py

# Linux/Mac
source venv/bin/activate
python demo.py
```

### 4. Access Dashboard

Open browser: http://localhost:8050

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Ingestion API  │────▶│  Feature Store   │────▶│ Prediction Svc  │
│   (Port 8001)   │     │   (Database)     │     │  (Port 8002)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │                          │
                                ▼                          ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  Drift Monitor   │────▶│ Retraining Wkr  │
                        │  (Background)    │     │  (Background)   │
                        └──────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │    Dashboard     │
                        │   (Port 8050)    │
                        └──────────────────┘
```

## Services

### 1. Ingestion API (Port 8001)
- Receives and validates incoming data
- Supports batch and streaming ingestion
- Stores data in feature store

### 2. Prediction Service (Port 8002)
- Serves ML model predictions
- Loads active model from registry
- Logs predictions for monitoring

### 3. Drift Monitor (Background)
- Continuously monitors for data drift
- Uses KS-test, PSI, and distribution analysis
- Triggers retraining when drift detected

### 4. Retraining Worker (Background)
- Automatically retrains models
- Evaluates and registers new models
- Updates active model in registry

### 5. Dashboard (Port 8050)
- Real-time metrics visualization
- Drift detection status
- Model performance tracking
- System health monitoring

## Dataset

Uses real lung disease dataset with:
- 40 patient samples
- 15 medical features (age, smoking, symptoms, etc.)
- Binary classification (disease present/absent)

## Requirements

- Python 3.9+
- 2GB RAM
- 500MB disk space

## Project Structure

```
auto-trigger/
├── services/           # Microservices
│   ├── ingestion_api/
│   ├── prediction_service/
│   ├── drift_monitor/
│   └── retraining_worker/
├── ml/                 # ML components
│   ├── training/
│   ├── evaluation/
│   └── feature_store/
├── dashboards/         # Monitoring dashboard
├── shared/             # Shared utilities
├── data/               # Data files
├── logs/               # Service logs
├── models/             # Trained models
├── scripts/            # Helper scripts
├── docs/               # Documentation
└── tests/              # Test files
```

## API Endpoints

### Ingestion API (8001)
- `GET /health` - Health check
- `POST /ingest/batch` - Ingest batch data
- `POST /ingest/stream` - Ingest streaming data
- `GET /stats` - Get ingestion statistics

### Prediction Service (8002)
- `GET /health` - Health check
- `POST /predict` - Make predictions
- `POST /predict/batch` - Batch predictions
- `POST /reload_model` - Reload model

## Troubleshooting

### Python not found
Install Python 3.9+ from python.org

### Virtual environment not found
Run `setup.bat` (Windows) or `./setup.sh` (Linux/Mac)

### Port already in use
```bash
# Windows
netstat -ano | findstr :8001
taskkill /PID <pid> /F

# Linux/Mac
lsof -i :8001
kill -9 <pid>
```

### Services won't start
1. Run `scripts\verify_setup.bat` to diagnose
2. Check logs in `logs/` directory
3. Ensure all dependencies installed

### Demo connection error
1. Verify services are running
2. Wait 15 seconds after starting services
3. Check health endpoints in browser

## Stopping Services

```bash
# Windows
stop_all_services.bat

# Linux/Mac
./stop_all_services.sh
```

Or close all service windows manually.

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Checking Single Service
```bash
scripts\test_single_service.bat
```

### Viewing Logs
```bash
# Windows
type logs\ingestion_api_20260112.log

# Linux/Mac
cat logs/ingestion_api_20260112.log
```

## Documentation

- `docs/ARCHITECTURE.md` - Detailed system design
- `docs/GETTING_STARTED.md` - Setup guide
- `docs/TROUBLESHOOTING.md` - Common issues and solutions
- `docs/TESTING_RESULTS.md` - Test results

## License

This project is for educational purposes (Final Year Project).

## Author

Created as a final year project demonstrating production-ready ML pipeline with drift detection and auto-retraining capabilities.
