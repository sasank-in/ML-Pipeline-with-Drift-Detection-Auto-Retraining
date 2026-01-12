# 🚀 Real-Time ML Pipeline with Auto-Retraining & Drift Detection

> A production-grade, microservices-based machine learning pipeline that automatically detects data drift and triggers model retraining in real-time.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-brightgreen.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![MLOps](https://img.shields.io/badge/MLOps-Production%20Ready-orange.svg)]()

## �️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ML Pipeline System                        │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Ingestion   │───▶│  Prediction  │───▶│    Drift     │
│     API      │    │   Service    │    │   Monitor    │
│   :8001      │    │    :8002     │    │              │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                               │
                                               ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Dashboard   │◀───│   Database   │◀───│  Retraining  │
│   :8050      │    │   (SQLite)   │    │    Worker    │
└──────────────┘    └──────────────┘    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   MLFlow     │
                    │   Registry   │
                    └──────────────┘
```

## 📁 Project Structure

```
automl_stream/
│
├── services/                    # Microservices
│   ├── ingestion_api/          # Data ingestion endpoint
│   │   ├── app.py
│   │   └── Dockerfile
│   ├── prediction_service/     # Model serving
│   │   ├── app.py
│   │   └── Dockerfile
│   ├── drift_monitor/          # Drift detection
│   │   ├── monitor.py
│   │   └── Dockerfile
│   └── retraining_worker/      # Auto-retraining
│       ├── worker.py
│       └── Dockerfile
│
├── ml/                          # ML components
│   ├── training/
│   │   └── trainer.py          # Model training
│   ├── evaluation/
│   │   └── drift_detector.py   # Drift detection algorithms
│   └── feature_store/          # Feature management
│
├── registry/                    # Model registry
│   └── mlflow/
│       └── mlflow_client.py    # MLFlow integration
│
├── dashboards/                  # Monitoring UI
│   ├── monitoring_app.py       # Dash dashboard
│   └── Dockerfile
│
├── shared/                      # Shared utilities
│   ├── config.py               # Configuration
│   ├── database.py             # Database manager
│   ├── logger.py               # Logging
│   └── redis_client.py         # Cache/Queue
│
├── docker-compose.yml           # Orchestration
├── requirements.txt             # Dependencies
└── README.md                    # This file
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.9+ (for local development)

### Run with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Services & Ports

| Service | Port | Description |
|---------|------|-------------|
| Ingestion API | 8001 | Data ingestion endpoint |
| Prediction Service | 8002 | Model predictions |
| Drift Monitor | - | Background drift detection |
| Retraining Worker | - | Background retraining |
| Dashboard | 8050 | Monitoring UI |

### Access Dashboard

Open browser: `http://localhost:8050`

## 💻 Local Development

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run Services Individually

```bash
# Terminal 1: Ingestion API
python services/ingestion_api/app.py

# Terminal 2: Prediction Service
python services/prediction_service/app.py

# Terminal 3: Drift Monitor
python services/drift_monitor/monitor.py

# Terminal 4: Retraining Worker
python services/retraining_worker/worker.py

# Terminal 5: Dashboard
python dashboards/monitoring_app.py
```

## 📊 API Usage

### 1. Ingest Data

```bash
curl -X POST http://localhost:8001/ingest/batch \
  -H "Content-Type: application/json" \
  -d '{
    "features": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
    "labels": [0, 1],
    "batch_id": "batch_001"
  }'
```

### 2. Make Predictions

```bash
curl -X POST http://localhost:8002/predict \
  -H "Content-Type: application/json" \
  -d '{
    "features": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
  }'
```

### 3. Health Checks

```bash
# Check all services
curl http://localhost:8001/health  # Ingestion
curl http://localhost:8002/health  # Prediction
```

## 🔄 How It Works

### 1. Data Flow
1. **Ingestion API** receives data and queues it
2. **Prediction Service** makes predictions using active model
3. Predictions are buffered for drift monitoring

### 2. Drift Detection
1. **Drift Monitor** periodically checks recent predictions
2. Uses KS-test, PSI, and statistical analysis
3. Triggers retraining if drift detected

### 3. Auto-Retraining
1. **Retraining Worker** picks up retraining jobs
2. Trains new model with recent data
3. Logs to MLFlow and registers model
4. Notifies Prediction Service to reload

### 4. Monitoring
1. **Dashboard** displays real-time metrics
2. Shows accuracy trends, drift events, predictions
3. Updates every 5 seconds

## 🎯 Key Features

### Microservices Architecture
✅ Independent, scalable services  
✅ Docker containerization  
✅ Service discovery and health checks  

### Drift Detection
✅ Multiple statistical tests (KS, PSI, distribution)  
✅ Configurable thresholds  
✅ Feature-level drift analysis  

### Auto-Retraining
✅ Triggered by drift detection  
✅ MLFlow experiment tracking  
✅ Model versioning and registry  

### Monitoring
✅ Real-time dashboard  
✅ Performance metrics  
✅ Drift visualization  
✅ Training history  

### Production Ready
✅ Logging and error handling  
✅ Database persistence  
✅ Caching with Redis  
✅ Configuration management  

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

## � Monitoring Dashboard

The dashboard provides:

- **Statistics Cards**: Total predictions, drift events, retraining count, accuracy
- **Accuracy Chart**: Model performance over time
- **Drift Chart**: Drift detection events
- **Prediction Distribution**: Class distribution
- **Training Time**: Time per retraining job

## ⚙️ Configuration

Edit `shared/config.py` to customize:

```python
# Model parameters
n_estimators = 100
max_depth = 10

# Drift detection
threshold = 0.05
window_size = 1000
check_interval = 300  # seconds

# Service ports
ingestion_port = 8001
prediction_port = 8002
dashboard_port = 8050
```

## 🔧 Environment Variables

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ml_pipeline

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# MLFlow
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT=drift_detection_pipeline
```

## � Database Schema

### predictions
- Stores all predictions with features and labels

### drift_events
- Logs drift detection results and actions

### training_jobs
- Tracks all training jobs and metrics

### model_registry
- Model versions and deployment status

## 🚢 Deployment

### Production Considerations

1. **Replace SQLite with PostgreSQL**
2. **Use real Redis for caching/queues**
3. **Add authentication (JWT)**
4. **Implement rate limiting**
5. **Set up Prometheus/Grafana monitoring**
6. **Use Kubernetes for orchestration**
7. **Add CI/CD pipeline**

### Kubernetes Deployment

```bash
# Apply configurations
kubectl apply -f k8s/

# Check status
kubectl get pods
kubectl get services
```

## 🎓 For Final Year Project

This project demonstrates:

✅ **Microservices Architecture** - Industry-standard design  
✅ **MLOps** - Complete ML lifecycle management  
✅ **Real-Time Systems** - Stream processing  
✅ **Drift Detection** - Statistical analysis  
✅ **Auto-Retraining** - Automated ML pipeline  
✅ **Monitoring** - Real-time dashboards  
✅ **Docker** - Containerization  
✅ **API Design** - RESTful services  
✅ **Database Design** - Data persistence  
✅ **Testing** - Unit and integration tests  

## 📚 Documentation

- [Technical Documentation](DOCUMENTATION.md)
- [API Reference](API.md)
- [Deployment Guide](DEPLOYMENT.md)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📄 License

MIT License - Free to use for your final year project!

## 👨‍💻 Author

[Your Name] - Final Year Project 2024

## 🙏 Acknowledgments

Built with modern MLOps practices and microservices architecture.
