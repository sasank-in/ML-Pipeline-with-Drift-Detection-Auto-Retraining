# Project Structure

```
auto-trigger/
│
├── services/                      # 4 Microservices
│   ├── ingestion_api/
│   │   └── app.py                 # Flask API for data ingestion (port 8001)
│   ├── prediction_service/
│   │   └── app.py                 # Flask API for real-time predictions (port 8002)
│   ├── drift_monitor/
│   │   └── monitor.py             # Background drift detection loop
│   └── retraining_worker/
│       └── worker.py              # Background model retraining + rotation
│
├── ml/                            # ML Components
│   ├── training/
│   │   └── trainer.py             # RandomForest training with holdout split
│   ├── evaluation/
│   │   └── drift_detector.py      # KS-test + PSI + mean-shift drift detection
│   └── feature_store/
│       └── feature_store.py       # Feature persistence
│
├── dashboards/
│   └── monitoring_app.py          # Dash dashboard (port 8050)
│
├── shared/                        # Shared utilities (importable as a package)
│   ├── auth.py                    # X-API-Key auth decorator
│   ├── config.py                  # Env-driven config (Postgres/SQLite/drift)
│   ├── database.py                # DB layer with pooling + queue helpers
│   ├── logger.py                  # Structured logging
│   └── web_ui.py                  # Shared HTML/CSS for service home pages
│
├── registry/
│   └── mlflow/
│       └── mlflow_client.py       # MLFlow tracking (mock implementation)
│
├── data/
│   ├── .gitkeep
│   ├── pipeline.db                # SQLite database (if USE_POSTGRES=false)
│   ├── retail_data.csv            # Demo dataset for demo.py
│   └── seasonal/                  # UCI Online Retail per-quarter batches
│       ├── .gitkeep
│       ├── online_retail.xlsx     # (gitignored, ~23 MB)
│       ├── Q1.json … Q4.json      # (gitignored, per-quarter ingestion payloads)
│       └── summary.json
│
├── models/                        # Saved .pkl model bundles (gitignored)
│   └── .gitkeep
│
├── logs/                          # Daily service logs (gitignored)
│   └── .gitkeep
│
├── docs/
│   ├── FLOW.md                    # Pipeline data-flow narrative
│   ├── STRUCTURE.md               # This file
│   └── images/
│       ├── banner_1200x1200.png   # Square portfolio card
│       ├── banner_1500x500.png    # GitHub README banner
│       └── banner_1584x396.png    # LinkedIn cover
│
├── tests/
│   ├── test_demo.py
│   ├── test_drift_detector.py
│   └── test_pipeline.py
│
├── scripts/                       # Helper scripts
│   ├── build_seasonal_data.py     # Slice UCI dataset into Q1..Q4 JSON batches
│   ├── run_seasonal_demo.py       # End-to-end drift→retrain demo runner
│   ├── capture_banner.py          # Playwright-based dashboard screenshots
│   ├── check_errors.bat
│   ├── test_single_service.bat
│   └── verify_setup.bat
│
├── .env                           # Your environment variables (gitignored)
├── .env.example                   # Template
├── .gitignore
├── pyproject.toml                 # Python package configuration
├── README.md
├── requirements.txt
│
├── demo.py                        # Local demo with retail_data.csv
├── inject_drift.py                # Synthetic drift generator
├── run_pipeline.py                # CLI pipeline runner
├── start_services.py              # Single-terminal service launcher
├── test_services.py               # Import smoke tests
│
├── run_all_services.bat           # Windows multi-window launcher
├── setup.bat                      # Windows setup
└── stop_all_services.bat          # Windows graceful stop
```

## Entry Points

| File | Purpose |
|------|---------|
| `run_all_services.bat` | Starts all services in separate windows (Windows) |
| `start_services.py` | Starts all services in a single terminal |
| `demo.py` | Local pipeline demo on `data/retail_data.csv` |
| `scripts/run_seasonal_demo.py` | End-to-end drift→retrain demo on UCI Online Retail |
| `test_services.py` | Import + basic smoke tests |

## Services & Ports

| Service | Path | Port |
|---------|------|------|
| Ingestion API | `services/ingestion_api/app.py` | 8001 |
| Prediction Service | `services/prediction_service/app.py` | 8002 |
| Drift Monitor | `services/drift_monitor/monitor.py` | background |
| Retraining Worker | `services/retraining_worker/worker.py` | background |
| Dashboard | `dashboards/monitoring_app.py` | 8050 |

The two Flask services run on **waitress** (production WSGI) when installed; falls back to Flask dev server otherwise.

## ML Components

| Component | File | Purpose |
|-----------|------|---------|
| Trainer | `ml/training/trainer.py` | RandomForest with stratified holdout split; saves model + reference baseline together |
| Drift Detector | `ml/evaluation/drift_detector.py` | KS-test + PSI + mean-shift per feature |
| Feature Store | `ml/feature_store/feature_store.py` | Feature persistence via shared DB |

## Shared Utilities

| File | Purpose |
|------|---------|
| `shared/auth.py` | `X-API-Key` decorator (set `API_KEY` env to enforce) |
| `shared/config.py` | Loads env into dataclasses (DB, MLflow, Model, Drift, Service) |
| `shared/database.py` | DB layer with PG connection pooling, `_exec` cross-dialect helper, queue ops |
| `shared/logger.py` | Per-component file + console logging |
| `shared/web_ui.py` | Shared HTML/CSS palette for the service home pages |

## Database Tables

| Table | Purpose |
|-------|---------|
| `predictions` | Every prediction call logged (features, prediction, probability, model_version) |
| `drift_events` | Drift detection results (score, affected features, action taken) |
| `training_jobs` | Idempotent training-job log (upsert on `job_id`) |
| `model_registry` | Trained models with metrics and deployed flag |
| `feature_store` | Persisted features (key-value style) |
| `queues` | Cross-process queues: `data_queue`, `stream_queue`, `prediction_buffer`, `retraining_queue` |

## Configuration

Set in `.env` (template in `.env.example`):

| Var | Default | Purpose |
|-----|---------|---------|
| `USE_POSTGRES` | `false` | `true` to use Postgres, else SQLite |
| `API_KEY` | (unset) | If set, required header on POST endpoints |
| `BIND_HOST` | `127.0.0.1` | Service bind address |
| `CORS_ORIGINS` | (empty) | Comma-separated allowed origins |
| `MAX_CONTENT_LENGTH` | `10485760` | Max request body bytes |
| `MAX_BATCH_ROWS` | `10000` | Cap on `/ingest/batch` rows |
| `MAX_PREDICT_ROWS` | `1000` | Cap on `/predict` rows |
| `WAITRESS_THREADS` | `8` | Production WSGI threads |
| `PG_POOL_MIN` / `PG_POOL_MAX` | `1` / `10` | Postgres pool sizing |
| `KEEP_N_MODELS` | `5` | Retain latest N model `.pkl` files |
| `DRIFT_THRESHOLD` | `0.05` | KS p-value threshold |
| `DRIFT_WINDOW_SIZE` | `1000` | Samples per drift check |
| `DRIFT_MIN_SAMPLES` | `100` | Minimum buffer before checking |
| `DRIFT_CHECK_INTERVAL` | `300` | Seconds between checks |
