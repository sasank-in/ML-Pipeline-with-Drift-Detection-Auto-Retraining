# Project Structure

```
ml-pipeline/
│
├── services/                    # Microservices
│   ├── ingestion_api/
│   │   ├── __init__.py
│   │   └── app.py              # Flask API for data ingestion
│   │
│   ├── prediction_service/
│   │   ├── __init__.py
│   │   └── app.py              # Flask API for predictions
│   │
│   ├── drift_monitor/
│   │   ├── __init__.py
│   │   └── monitor.py          # Background drift detection
│   │
│   └── retraining_worker/
│       ├── __init__.py
│       └── worker.py           # Background model retraining
│
├── ml/                          # ML Components
│   ├── __init__.py
│   ├── training/
│   │   ├── __init__.py
│   │   └── trainer.py          # Model training logic
│   │
│   ├── evaluation/
│   │   ├── __init__.py
│   │   └── drift_detector.py   # Drift detection algorithms
│   │
│   └── feature_store/
│       ├── __init__.py
│       └── feature_store.py    # Feature management
│
├── dashboards/                  # Monitoring UI
│   ├── __init__.py
│   └── monitoring_app.py       # Dash dashboard
│
├── shared/                      # Shared Utilities
│   ├── __init__.py
│   ├── config.py               # Configuration management
│   ├── database.py             # PostgreSQL/SQLite operations
│   ├── logger.py               # Logging setup
│   └── redis_client.py         # Redis client (mock for demo)
│
├── registry/                    # Model Registry
│   ├── __init__.py
│   └── mlflow/
│       ├── __init__.py
│       └── mlflow_client.py    # MLFlow integration
│
├── data/                        # Data Files
│   ├── lung_disease.csv        # Sample dataset
│   └── pipeline.db             # SQLite database (if used)
│
├── logs/                        # Service Logs
│   └── *.log                   # Daily log files
│
├── models/                      # Saved Models
│   └── *.pkl                   # Trained model files
│
├── tests/                       # Test Files
│   ├── __init__.py
│   ├── test_drift_detector.py
│   └── test_pipeline.py
│
├── scripts/                     # Helper Scripts
│   ├── check_errors.bat
│   ├── test_single_service.bat
│   └── verify_setup.bat
│
├── docs/                        # Documentation
│   ├── FLOW.md                 # Pipeline flow explanation
│   └── STRUCTURE.md            # This file
│
├── .env                         # Environment variables (create from .env.example)
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
├── requirements.txt             # Python dependencies
├── README.md                    # Main documentation
│
├── setup.bat                    # Windows setup script
├── setup.sh                     # Linux/Mac setup script
├── run_all_services.bat         # Start all services (Windows)
├── run_all_services.sh          # Start all services (Linux/Mac)
├── stop_all_services.bat        # Stop all services (Windows)
├── stop_all_services.sh         # Stop all services (Linux/Mac)
│
├── demo.py                      # Demonstration script
├── test_services.py             # Service tests
└── test_postgres.py             # Database connection test
```

## Key Files Explained

### Entry Points
| File | Purpose |
|------|---------|
| `run_all_services.bat` | Starts all 5 microservices |
| `demo.py` | Demonstrates the full pipeline |
| `test_services.py` | Tests all components |

### Services
| Service | File | Port |
|---------|------|------|
| Ingestion API | `services/ingestion_api/app.py` | 8001 |
| Prediction Service | `services/prediction_service/app.py` | 8002 |
| Drift Monitor | `services/drift_monitor/monitor.py` | Background |
| Retraining Worker | `services/retraining_worker/worker.py` | Background |
| Dashboard | `dashboards/monitoring_app.py` | 8050 |

### ML Components
| Component | File | Purpose |
|-----------|------|---------|
| Trainer | `ml/training/trainer.py` | Train ML models |
| Drift Detector | `ml/evaluation/drift_detector.py` | Detect data drift |
| Feature Store | `ml/feature_store/feature_store.py` | Manage features |

### Shared Utilities
| File | Purpose |
|------|---------|
| `shared/config.py` | Load configuration from .env |
| `shared/database.py` | PostgreSQL/SQLite operations |
| `shared/logger.py` | Structured logging |
| `shared/redis_client.py` | Queue management |

### Configuration
| File | Purpose |
|------|---------|
| `.env` | Your environment variables |
| `.env.example` | Template for .env |
| `requirements.txt` | Python dependencies |

## Database Tables

| Table | Purpose |
|-------|---------|
| `predictions` | Logged predictions |
| `drift_events` | Drift detection history |
| `training_jobs` | Training job records |
| `model_registry` | Model versions |
| `feature_store` | Stored features |
