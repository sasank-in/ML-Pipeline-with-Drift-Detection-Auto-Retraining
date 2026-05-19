# ML Pipeline Flow

## How It Works

### 1. Data Ingestion

```
Client -> POST /ingest/batch -> Ingestion API (8001) -> data_queue -> Postgres/SQLite
                                                     -> Feature Store
```

**Steps:**
1. Client posts `{features, labels, batch_id}` to `/ingest/batch` (or `/ingest/stream` for single rows).
2. Ingestion API validates shape, applies `MAX_BATCH_ROWS` / `MAX_PREDICT_ROWS` caps and enforces `X-API-Key` if configured.
3. Payload is enqueued in the DB-backed `data_queue` (or `stream_queue`) for the Retraining Worker to consume.

### 2. Prediction

```
Client -> POST /predict -> Prediction Service (8002) -> Active model -> Response
                                                     -> predictions table
                                                     -> prediction_buffer queue
```

**Steps:**
1. Client posts `{features: [[…]]}` to `/predict`.
2. Service auto-reloads the latest deployed model when a new version is registered in `model_registry`.
3. Returns `{predictions, probabilities, model_version, prediction_time}`.
4. Logs every row to the `predictions` table and adds the batch to `prediction_buffer` for drift monitoring.

### 3. Drift Detection

```
prediction_buffer -> Drift Monitor (background) -> KS-test + PSI + mean-shift -> drift_events
                                                                              -> retraining_queue
```

**Steps:**
1. Monitor peeks (non-destructively) at recent items in `prediction_buffer`.
2. Loads the **reference baseline** (the model's training distribution, saved alongside the `.pkl`).
3. Runs three tests per feature: KS-test p-value, PSI, mean-shift in stddev units.
4. A feature drifts if `ks_pvalue < threshold` OR `psi > 0.2` OR `mean_shift > 2.0`.
5. Overall drift is flagged when **more than 20 %** of features drifted.
6. Logs the event to `drift_events`; if detected, pushes a job onto `retraining_queue`.

### 4. Auto-Retraining

```
retraining_queue -> Retraining Worker -> data_queue + stream_queue -> Train (RandomForest)
                                                                   -> Save .pkl + reference
                                                                   -> model_registry
                                                                   -> Deploy + rotate
```

**Steps:**
1. Worker pops the next job from `retraining_queue` (or bootstraps when no model is deployed).
2. Drains labelled rows from `data_queue` (batch shape) and `stream_queue` (single-row shape).
3. Trains a RandomForest with stratified 80/20 holdout; reports **holdout** metrics.
4. Saves the model bundle (`model + reference_data + timestamp`) to `models/`.
5. Registers and deploys it atomically in `model_registry` (one row flagged `deployed=True`).
6. Rotates older `.pkl` files keeping the most recent `KEEP_N_MODELS` (default 5).
7. The Prediction Service auto-detects the new active version on its next call.

### 5. Monitoring

```
All services -> Postgres/SQLite -> Dashboard (8050) -> live charts
```

The dashboard polls the DB every 5 s for KPIs, health, drift timeline, per-feature drift heatmap, training history, queue depths, and recent predictions.

## Complete Pipeline

```
[External Data]
     |
     v
+--------------+
| Ingestion    |---+
| API :8001    |   |
+--------------+   |
     |             v
     v        +----------+
+----------+  | Postgres |
| data_q   |  |  / DB    |
+----------+  +----------+
     |             ^
     v             |
+--------------+   |     +--------------+
| Prediction   |---+---->| prediction_  |
| Svc :8002    |---+     | buffer queue |
+--------------+   |     +--------------+
                   |            |
                   |            v
                   |     +--------------+
                   |     | Drift        |
                   |     | Monitor (bg) |
                   |     +--------------+
                   |            |
                   |            v
                   |     +--------------+
                   |     | retraining_q |
                   |     +--------------+
                   |            |
                   |            v
                   |     +--------------+
                   +<----| Retraining   |
                         | Worker (bg)  |
                         +--------------+
                                |
                                v
                         +--------------+
                         | Dashboard    |
                         | :8050        |
                         +--------------+
```

## Service Communication

| From | To | Method | Purpose |
|------|-----|--------|---------|
| Client | Ingestion API | HTTP POST | Ingest data |
| Client | Prediction Service | HTTP POST | Get predictions |
| Ingestion API | Database | SQL | Enqueue rows in `data_queue` / `stream_queue` |
| Prediction Service | Database | SQL | Log to `predictions`, buffer for drift |
| Drift Monitor | Database | SQL (peek + write) | Read buffer, write `drift_events`, enqueue retrain jobs |
| Retraining Worker | Database | SQL | Pop jobs, fetch labelled data, register models |
| Retraining Worker | Filesystem | joblib | Save `.pkl` model bundles to `models/` |
| Dashboard | Database | SQL | Read metrics, queue depths, drift, training history |

## Trigger Points

### Manual triggers
- `python demo.py` — local end-to-end pipeline on `data/retail_data.csv` (no services needed).
- `python scripts/run_seasonal_demo.py` — runs the UCI Online Retail seasonal demo through the live services.
- `POST /ingest/batch` — feed labelled data; eventually triggers retraining via the bootstrap path.
- `POST /predict` — populates `prediction_buffer` for drift monitoring.

### Automatic triggers
- **Drift detection** — runs every `DRIFT_CHECK_INTERVAL` seconds (default 300).
- **Retraining** — fires when drift is detected OR when no model is deployed (bootstrap).
- **Model reload** — Prediction Service re-reads the active model on its next call after `model_registry` changes.

## Configuration

All knobs are env-overridable (`.env` or shell):

```text
DRIFT_THRESHOLD       = 0.05     # KS-test p-value cutoff (per feature)
DRIFT_WINDOW_SIZE     = 1000     # samples per drift check
DRIFT_MIN_SAMPLES     = 100      # minimum buffer before running a check
DRIFT_CHECK_INTERVAL  = 300      # seconds between checks

n_estimators = 100    # Random Forest trees
max_depth    = 10     # Tree depth
random_state = 42     # Reproducibility
```

## Example Usage

### Ingest a batch

```python
import requests

requests.post(
    "http://localhost:8001/ingest/batch",
    json={
        "features": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
        "labels":   [0, 1],
        "batch_id": "batch_001",
    },
    headers={"X-API-Key": "..."},  # only required if API_KEY env is set
)
```

### Predict

```python
r = requests.post(
    "http://localhost:8002/predict",
    json={"features": [[1.0, 2.0, 3.0]]},
    headers={"X-API-Key": "..."},
)
print(r.json())
# {
#   "predictions":   [1],
#   "probabilities": [[0.13, 0.87]],
#   "model_version": "v_20260519_100952",
#   "prediction_time": 0.063,
#   "status": "success"
# }
```

### Health

```python
requests.get("http://localhost:8001/health", headers={"Accept": "application/json"})
requests.get("http://localhost:8002/health", headers={"Accept": "application/json"})
# Returns 200 healthy or 503 degraded with per-check breakdown
```

## Logs

Each service writes daily files to `logs/`:

```
ingestion_api_YYYYMMDD.log
prediction_service_YYYYMMDD.log
drift_monitor_YYYYMMDD.log
retraining_worker_YYYYMMDD.log
dashboard_YYYYMMDD.log
database_YYYYMMDD.log
drift_detector_YYYYMMDD.log
mlflow_client_YYYYMMDD.log
model_trainer_YYYYMMDD.log
auth_YYYYMMDD.log
```
