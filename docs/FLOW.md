# ML Pipeline Flow

## How It Works

### 1. Data Ingestion Flow

```
External Data → Ingestion API → Validation → Feature Store → Database
                 (Port 8001)
```

**Steps:**
1. Client sends data to `/ingest/batch` or `/ingest/stream`
2. API validates the data format
3. Data is stored in Feature Store
4. Saved to PostgreSQL/SQLite database

### 2. Prediction Flow

```
Client Request → Prediction Service → Load Model → Make Prediction → Return Result
                   (Port 8002)                                            ↓
                                                                   Log to Database
```

**Steps:**
1. Client sends features to `/predict`
2. Service loads the active model
3. Model makes prediction
4. Result returned to client
5. Prediction logged for drift monitoring

### 3. Drift Detection Flow

```
Prediction Logs → Drift Monitor → Statistical Tests → Drift Detected?
                                                            ↓
                                                    Yes: Trigger Retraining
                                                    No: Continue Monitoring
```

**Detection Methods:**
- KS-Test (Kolmogorov-Smirnov)
- PSI (Population Stability Index)
- Distribution Analysis

### 4. Auto-Retraining Flow

```
Drift Alert → Retraining Worker → Fetch Data → Train Model → Evaluate
                                                                  ↓
                                                          Register in MLFlow
                                                                  ↓
                                                          Deploy New Model
                                                                  ↓
                                                          Notify Prediction Service
```

**Steps:**
1. Drift Monitor triggers retraining
2. Worker fetches recent data from Feature Store
3. New model trained with updated data
4. Model evaluated against metrics
5. If better, registered and deployed
6. Prediction Service reloads new model

### 5. Monitoring Flow

```
All Services → Logs → Dashboard → Real-time Visualization
                        ↓
              - Prediction counts
              - Drift scores
              - Model performance
              - System health
```

## Complete Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   [External Data]                                                    │
│         │                                                            │
│         ▼                                                            │
│   ┌─────────────┐                                                    │
│   │ Ingestion   │──────────────────────────────────┐                │
│   │ API :8001   │                                  │                │
│   └─────────────┘                                  │                │
│         │                                          │                │
│         ▼                                          ▼                │
│   ┌─────────────┐                          ┌─────────────┐          │
│   │ Feature     │                          │ PostgreSQL/ │          │
│   │ Store       │◄────────────────────────▶│ SQLite DB   │          │
│   └─────────────┘                          └─────────────┘          │
│         │                                          ▲                │
│         ▼                                          │                │
│   ┌─────────────┐                                  │                │
│   │ Prediction  │──────────────────────────────────┤                │
│   │ Svc :8002   │                                  │                │
│   └─────────────┘                                  │                │
│         │                                          │                │
│         ▼                                          │                │
│   ┌─────────────┐     ┌─────────────┐              │                │
│   │ Drift       │────▶│ Retraining  │──────────────┘                │
│   │ Monitor     │     │ Worker      │                               │
│   └─────────────┘     └─────────────┘                               │
│         │                   │                                        │
│         └───────┬───────────┘                                        │
│                 ▼                                                    │
│         ┌─────────────┐                                              │
│         │ Dashboard   │                                              │
│         │ :8050       │                                              │
│         └─────────────┘                                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Service Communication

| From | To | Method | Purpose |
|------|-----|--------|---------|
| Client | Ingestion API | HTTP POST | Send data |
| Client | Prediction Service | HTTP POST | Get predictions |
| Ingestion API | Database | SQL | Store data |
| Prediction Service | Database | SQL | Log predictions |
| Drift Monitor | Database | SQL | Read predictions |
| Drift Monitor | Retraining Worker | Internal | Trigger retraining |
| Retraining Worker | Database | SQL | Fetch training data |
| Retraining Worker | Model Registry | File | Save model |
| Dashboard | Database | SQL | Read metrics |

## Trigger Points

### Manual Triggers
- `python demo.py` - Runs full pipeline demo
- API calls to `/ingest/batch` - Ingest data
- API calls to `/predict` - Make predictions

### Automatic Triggers
- **Drift Detection**: When prediction distribution changes significantly
- **Retraining**: When drift score exceeds threshold (default: 0.05)
- **Model Reload**: When new model is deployed

## Configuration

### Drift Detection Settings
```python
threshold = 0.05      # Drift score threshold
window_size = 1000    # Samples to analyze
min_samples = 100     # Minimum samples before checking
check_interval = 300  # Seconds between checks
```

### Model Settings
```python
n_estimators = 100    # Random Forest trees
max_depth = 10        # Tree depth
random_state = 42     # Reproducibility
```

## Example Usage

### 1. Ingest Data
```python
import requests

response = requests.post(
    "http://localhost:8001/ingest/batch",
    json={
        "features": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
        "labels": [0, 1],
        "batch_id": "batch_001"
    }
)
```

### 2. Make Prediction
```python
response = requests.post(
    "http://localhost:8002/predict",
    json={"features": [[1.0, 2.0, 3.0]]}
)
print(response.json())
# {"predictions": [1], "probabilities": [0.85]}
```

### 3. Check Health
```python
# Ingestion API
requests.get("http://localhost:8001/health")

# Prediction Service
requests.get("http://localhost:8002/health")
```

## Logs

All services log to `logs/` directory:
- `ingestion_api_YYYYMMDD.log`
- `prediction_service_YYYYMMDD.log`
- `drift_monitor_YYYYMMDD.log`
- `retraining_worker_YYYYMMDD.log`
- `dashboard_YYYYMMDD.log`
