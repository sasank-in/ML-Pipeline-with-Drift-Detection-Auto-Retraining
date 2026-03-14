# Real-Time ML Pipeline with Auto-Retraining & Drift Detection

A production-ready machine learning pipeline with automatic drift detection and model retraining.

## What This Application Can Do

- Ingest batch or stream data through an API
- Serve real-time predictions from the latest deployed model
- Log predictions and system events to a database
- Detect data drift with statistical tests
- Trigger automated model retraining when drift is detected
- Deploy the new model and auto-reload it in the prediction service
- Visualize system health and metrics in a live dashboard
- Inject synthetic data to simulate drift scenarios

## Quick Start (Windows + Conda)

```bash
# 1. Create a conda environment
conda create -n ml-pipeline python=3.9 -y

# 2. Activate it
conda activate ml-pipeline

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start all services (opens 5 windows)
run_all_services.bat

# 5. View dashboard
# http://localhost:8050
```

## Quick Start (Single Terminal)

If you prefer one terminal for services:

```bash
# 1. Create conda env + install deps
conda create -n ml-pipeline python=3.9 -y
conda activate ml-pipeline
pip install -r requirements.txt

# 2. Start services in the same terminal
python start_services.py
```

Open:
- Ingestion API: http://localhost:8001  
- Prediction Service: http://localhost:8002  
- Dashboard: http://localhost:8050  

## Run the Pipeline With Your Data

```bash
# Basic usage
python run_pipeline.py --data your_data.csv --target target_column

# Custom test size
python run_pipeline.py --data sales.csv --target revenue --test-size 0.25

# Skip drift detection
python run_pipeline.py --data customers.csv --target churn --no-drift

# See all options
python run_pipeline.py --help
```

## Inject Drift Samples (Synthetic)

Use this to simulate drift with synthetic data and trigger drift detection:

```bash
python inject_drift.py --feature-dim 8 --baseline 200 --drift 200 --drift-amount 2.5
```

Retail-like realistic scenario (matches `demo.py` feature set):

```bash
python inject_drift.py --scenario retail --baseline 300 --drift 300 --drift-amount 1.5
```

The pipeline automatically:
- Handles missing values
- Encodes categorical columns
- Scales numeric features
- Splits train/test data

## Demo (Retail Dataset)

```bash
python demo.py
```

This uses `data/retail_data.csv` and runs the pipeline locally without the services.

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

## Services and Ports

| Service | Port | Purpose |
|---------|------|-------------|
| Ingestion API | 8001 | Receives batch/stream data and queues it |
| Prediction Service | 8002 | Serves predictions and logs results |
| Drift Monitor | Background | Checks recent data for drift |
| Retraining Worker | Background | Retrains and deploys new models |
| Dashboard | 8050 | Visualizes metrics and system health |

## API Endpoints

### Ingestion API (Port 8001)
- `GET /` - Service home UI
- `GET /health` - Health check
- `POST /ingest/batch` - Ingest batch data
- `POST /ingest/stream` - Ingest streaming data
- `GET /stats` - Get statistics

### Prediction Service (Port 8002)
- `GET /` - Service home UI
- `GET /health` - Health check
- `GET/POST /predict` - Make predictions
- `GET/POST /reload_model` - Reload latest model from disk

## Dataset

**File:** `data/retail_data.csv`
- Used by `demo.py` for the retail customer value example
- For `run_pipeline.py`, provide any CSV with a target column

## Database

Supports both SQLite (default) and PostgreSQL.
Queues for ingestion, prediction buffers, and retraining are stored in the database.

**SQLite (default):**
- Uses `data/pipeline.db`
- No external setup needed

**PostgreSQL:**
1. Edit `.env`
2. Set `USE_POSTGRES=true`
3. Configure credentials

## Project Structure

```
├── services/           # 5 Microservices
│   ├── ingestion_api/
│   ├── prediction_service/
│   ├── drift_monitor/
│   └── retraining_worker/
├── ml/                 # ML Components
│   ├── training/
│   ├── evaluation/
│   └── feature_store/
├── dashboards/         # Monitoring Dashboard
├── shared/             # Shared Utilities
├── data/               # Dataset & Database
├── logs/               # Service Logs
└── models/             # Trained Models
```

## Commands

| Command | Description |
|---------|-------------|
| `run_all_services.bat` | Start all services (Windows, multi-window) |
| `stop_all_services.bat` | Stop all services |
| `python start_services.py` | Start all services (single terminal) |
| `python demo.py` | Run local demo |
| `python test_services.py` | Run tests |

## Requirements

- Python 3.9+
- 2GB RAM
- PostgreSQL (optional)

## Typical Actions

- Start services: `run_all_services.bat` or `python start_services.py`
- Ingest data: `POST /ingest/batch` or `POST /ingest/stream`
- Predict: `POST /predict`
- Trigger drift: `python inject_drift.py --scenario retail`
- View dashboard: http://localhost:8050

## Troubleshooting

**Services won't start:** Ensure dependencies are installed with `pip install -r requirements.txt` inside your conda env

**Port in use:** 
```bash
netstat -ano | findstr :8001
taskkill /PID <pid> /F
```

**Import errors:** 
```bash
pip install -r requirements.txt --force-reinstall
```

## License

Educational project - Final Year Project
