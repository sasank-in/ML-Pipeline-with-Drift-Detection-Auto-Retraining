# Real-Time ML Pipeline with Auto-Retraining & Drift Detection

![ML Pipeline Monitor — live dashboard showing service health, KPIs, drift score timeline and per-feature drift heatmap](docs/images/banner_1500x500.png)

A production-ready machine learning pipeline with automatic drift detection and model retraining. Validated end-to-end on the UCI Online Retail dataset: Q4 holiday drift was correctly detected (score 0.75, 6 of 8 features) and triggered an auto-retrain that lifted holdout accuracy to **99.3 %** (F1 0.993).

## What This Application Can Do

- Ingest batch or stream data through an authenticated API
- Serve real-time predictions from the latest deployed model (auto-reloaded on deploy)
- Detect data drift with statistical tests (KS-test, PSI, mean-shift)
- Auto-retrain when drift is detected and atomically deploy the new model
- Visualise system health, drift, model performance, and queues in a live dashboard
- Run on PostgreSQL or SQLite, behind the production `waitress` WSGI server
- Reproduce drift end-to-end with the UCI Online Retail seasonal demo

## Quick Start (Windows + Conda)

```bash
# 1. Create and activate the conda env
conda create -n main python=3.9 -y
conda activate main

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start all services (opens 5 windows)
run_all_services.bat

# 4. Open the dashboard
# http://localhost:8050
```

Prefer a single terminal? Use `python start_services.py` instead of the `.bat`.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Ingestion API  │────▶│   Postgres /     │◀────│ Prediction Svc  │
│   (Port 8001)   │     │   SQLite +       │     │  (Port 8002)    │
└─────────────────┘     │   queue tables   │     └─────────────────┘
                        └──────────────────┘              │
                                ▲                          │
                                │                          ▼
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

## Services & Ports

| Service | Path | Port |
|---------|------|------|
| Ingestion API | `services/ingestion_api/app.py` | 8001 |
| Prediction Service | `services/prediction_service/app.py` | 8002 |
| Drift Monitor | `services/drift_monitor/monitor.py` | background |
| Retraining Worker | `services/retraining_worker/worker.py` | background |
| Dashboard | `dashboards/monitoring_app.py` | 8050 |

Flask services run on **waitress** (production WSGI) when installed; the dashboard runs on the Dash development server.

## API Endpoints

### Ingestion API (8001)
| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Service home UI |
| `GET` | `/health` | Health check (returns 503 on degraded DB) |
| `GET` | `/stats` | Queue length stats |
| `POST` | `/ingest/batch` | Ingest 2D `features` + `labels` |
| `POST` | `/ingest/stream` | Ingest a single row + optional `label` |

### Prediction Service (8002)
| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Service home UI |
| `GET` | `/health` | Health check (DB + model availability) |
| `POST` | `/predict` | Returns predictions + probabilities + model version |
| `POST` | `/reload_model` | Force-reload the active model from disk |

When `API_KEY` is set in `.env`, all `POST` endpoints require header `X-API-Key: <key>`.

## Running the Pipeline

### Local demo (no services needed)

```bash
python demo.py            # uses data/retail_data.csv
```

### CLI runner on any CSV

```bash
python run_pipeline.py --data your_data.csv --target target_column
python run_pipeline.py --data sales.csv --target revenue --test-size 0.25
python run_pipeline.py --data customers.csv --target churn --no-drift
python run_pipeline.py --help
```

### Synthetic drift injection

```bash
python inject_drift.py --feature-dim 8 --baseline 200 --drift 200 --drift-amount 2.5
python inject_drift.py --scenario retail --baseline 300 --drift 300 --drift-amount 1.5
```

### Realistic Drift Demo (UCI Online Retail)

Exercises the full `ingest → train → predict → drift → retrain` loop using real retail data sliced by quarter. The 2011 holiday surge in Q4 drives clear drift across multiple features.

```bash
# 1. Download dataset (~23 MB) and build per-quarter ingestion payloads
python scripts/build_seasonal_data.py

# 2. Speed up drift checks so results are visible in real time (PowerShell)
$env:DRIFT_CHECK_INTERVAL = "15"
$env:DRIFT_WINDOW_SIZE   = "1500"
$env:DRIFT_MIN_SAMPLES   = "300"

# 3. Start all services (run_all_services.bat or python start_services.py)

# 4. Run the demo against the running services
python scripts/run_seasonal_demo.py
```

Expected output: each season triggers retraining, with Q4 drift score reaching ~0.75 (6 of 8 features drifted).

## Project Files

### Top-level entry points

| File | Purpose |
|---|---|
| `demo.py` | Local pipeline demo on `data/retail_data.csv` (no services needed) |
| `inject_drift.py` | Generate synthetic data with controllable drift |
| `run_pipeline.py` | CLI runner: takes any CSV + target column, trains + checks drift |
| `start_services.py` | Launch all 5 services in a single terminal |
| `run_all_services.bat` | Launch all 5 services in separate Windows command windows |
| `stop_all_services.bat` | Gracefully stop services started via `run_all_services.bat` |
| `setup.bat` | First-time setup: creates `data/`, `logs/`, `models/` directories |

### Code packages

| Path | What's inside |
|---|---|
| `services/ingestion_api/app.py` | Flask API for batch + stream ingestion |
| `services/prediction_service/app.py` | Flask API for real-time predictions |
| `services/drift_monitor/monitor.py` | Background drift-detection loop |
| `services/retraining_worker/worker.py` | Background worker for training + atomic deploy |
| `ml/training/trainer.py` | RandomForest training with stratified holdout split; saves model + reference baseline together |
| `ml/evaluation/drift_detector.py` | KS-test + PSI + mean-shift drift detection |
| `ml/feature_store/feature_store.py` | Feature persistence helper |
| `dashboards/monitoring_app.py` | Dash dashboard (6 charts, 3 tables, service health strip) |
| `shared/auth.py` | `X-API-Key` decorator |
| `shared/config.py` | Env-driven configuration dataclasses |
| `shared/database.py` | Postgres pool + SQLite WAL, cross-dialect `_exec` helper, queue ops |
| `shared/logger.py` | Per-component logger setup |
| `shared/web_ui.py` | Shared HTML/CSS for service home pages |
| `registry/mlflow/mlflow_client.py` | MLflow tracking (mock implementation) |

### Helper scripts (`scripts/`)

| File | Purpose |
|---|---|
| `build_seasonal_data.py` | Download UCI Online Retail and slice into Q1–Q4 JSON batches |
| `run_seasonal_demo.py` | Run the full bootstrap → drift → retrain demo end-to-end |
| `capture_banner.py` | Playwright-based screenshots of the dashboard for README banners |

### Tests (`tests/`)

| File | Purpose |
|---|---|
| `test_pipeline.py` | Unit tests for the pipeline modules |
| `test_drift_detector.py` | Unit tests for the drift detector |

Run with `pytest`.

### Documentation (`docs/`)

| File | Purpose |
|---|---|
| `FLOW.md` | Detailed data-flow narrative through all 5 services |
| `STRUCTURE.md` | Annotated tree of every directory and file |
| `images/banner_1200x1200.png` | Square portfolio card |
| `images/banner_1500x500.png` | GitHub README banner (used above) |
| `images/banner_1584x396.png` | LinkedIn project cover |

## Configuration

Set in `.env` (template in `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `USE_POSTGRES` | `false` | `true` to use Postgres, else SQLite |
| `API_KEY` | *(unset)* | If set, required header `X-API-Key` on POST endpoints |
| `CORS_ORIGINS` | *(empty)* | Comma-separated allowed origins for browser clients |
| `BIND_HOST` | `127.0.0.1` | Interface to bind (use `0.0.0.0` only with `API_KEY` set) |
| `MAX_CONTENT_LENGTH` | `10485760` | Max request body bytes (10 MB) |
| `MAX_BATCH_ROWS` | `10000` | Max rows per `/ingest/batch` call |
| `MAX_PREDICT_ROWS` | `1000` | Max rows per `/predict` call |
| `WAITRESS_THREADS` | `8` | WSGI worker threads |
| `PG_POOL_MIN` / `PG_POOL_MAX` | `1` / `10` | Postgres connection pool size |
| `KEEP_N_MODELS` | `5` | Retain this many recent `.pkl` files (older are rotated out) |
| `DRIFT_THRESHOLD` | `0.05` | KS-test p-value threshold |
| `DRIFT_WINDOW_SIZE` | `1000` | Samples per drift check |
| `DRIFT_MIN_SAMPLES` | `100` | Minimum buffer size before checking |
| `DRIFT_CHECK_INTERVAL` | `300` | Seconds between drift checks |

## Database

Both SQLite (default) and PostgreSQL are supported. Queues (`data_queue`, `stream_queue`, `prediction_buffer`, `retraining_queue`) are stored in the same database to keep cross-process state consistent.

**SQLite:** uses `data/pipeline.db`, WAL journal mode enabled, 10 s busy timeout.
**PostgreSQL:** set `USE_POSTGRES=true` and configure `POSTGRES_*` env vars; runs through a `SimpleConnectionPool`.

## Requirements

- Python 3.9+
- ~2 GB RAM
- Optional: PostgreSQL 13+

See `requirements.txt` for Python deps.

## Common Actions

| Task | Command |
|---|---|
| Start everything | `run_all_services.bat` (or `python start_services.py`) |
| Stop everything | `stop_all_services.bat` |
| Ingest data | `POST /ingest/batch` to port 8001 |
| Make a prediction | `POST /predict` to port 8002 |
| Trigger synthetic drift | `python inject_drift.py --scenario retail` |
| Trigger real drift | `python scripts/run_seasonal_demo.py` |
| View dashboard | http://localhost:8050 |
| Refresh portfolio banners | `python scripts/capture_banner.py` (services + dashboard must be running) |

## Troubleshooting

**Services won't start** — make sure deps are installed in the right env:
```bash
conda activate main
pip install -r requirements.txt
```

**Port already in use:**
```bash
netstat -ano | findstr :8001
taskkill /PID <pid> /F
```

**Module not found** — you may be on the wrong conda env. Verify:
```bash
python -c "import sys; print(sys.executable)"
# Should print: C:\Users\<you>\miniconda3\envs\main\python.exe
```

**Postgres connection refused** — set `USE_POSTGRES=false` in `.env` to fall back to SQLite, or start your local Postgres and confirm credentials.

## License

Educational project — Final Year Project.
