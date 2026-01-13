# Real-Time ML Pipeline with Auto-Retraining & Drift Detection

A production-ready machine learning pipeline with automatic drift detection and model retraining.

## Quick Start

```bash
# 1. Setup (first time only)
setup.bat

# 2. Start all services
run_all_services.bat

# 3. Run with ANY dataset (in new terminal)
venv\Scripts\activate
python run_pipeline.py --data your_data.csv --target target_column

# 4. View dashboard
# http://localhost:8050
```

## Using Your Own Data

```bash
# Basic usage
python run_pipeline.py --data data/lung_disease.csv --target Recovered

# Custom test size
python run_pipeline.py --data sales.csv --target revenue --test-size 0.25

# Skip drift detection
python run_pipeline.py --data customers.csv --target churn --no-drift

# See all options
python run_pipeline.py --help
```

The pipeline automatically:
- Handles missing values
- Encodes categorical columns
- Scales numeric features
- Splits train/test data

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

| Service | Port | Description |
|---------|------|-------------|
| Ingestion API | 8001 | Receives and validates incoming data |
| Prediction Service | 8002 | Serves ML model predictions |
| Drift Monitor | Background | Monitors for data drift |
| Retraining Worker | Background | Auto-retrains models when drift detected |
| Dashboard | 8050 | Real-time monitoring UI |

## API Endpoints

### Ingestion API (Port 8001)
- `GET /health` - Health check
- `POST /ingest/batch` - Ingest batch data
- `POST /ingest/stream` - Ingest streaming data
- `GET /stats` - Get statistics

### Prediction Service (Port 8002)
- `GET /health` - Health check
- `POST /predict` - Make predictions
- `POST /predict/batch` - Batch predictions

## Dataset

**File:** `data/lung_disease.csv`
- 40 patient samples
- 15 medical features
- Binary classification (lung disease prediction)

## Database

Supports both SQLite (default) and PostgreSQL.

**Switch to PostgreSQL:**
1. Edit `.env` file
2. Set `USE_POSTGRES=true`
3. Configure PostgreSQL credentials

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
| `setup.bat` | First-time setup |
| `run_all_services.bat` | Start all services |
| `stop_all_services.bat` | Stop all services |
| `python demo.py` | Run demonstration |
| `python test_services.py` | Run tests |

## Requirements

- Python 3.9+
- 2GB RAM
- PostgreSQL (optional)

## Troubleshooting

**Services won't start:** Run `setup.bat` first

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
