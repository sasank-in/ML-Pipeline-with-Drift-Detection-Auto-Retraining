# System Architecture Documentation

## Overview

This ML Pipeline is built using a **microservices architecture** where each service has a specific responsibility and can scale independently.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│  (Web Apps, Mobile Apps, IoT Devices, Batch Jobs)              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (Future)                        │
│              (Load Balancing, Authentication, Rate Limiting)     │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│  Ingestion API │ │  Prediction    │ │   Dashboard    │
│    :8001       │ │   Service      │ │    :8050       │
│                │ │    :8002       │ │                │
│ - Validates    │ │ - Serves model │ │ - Visualizes   │
│ - Queues data  │ │ - Caches       │ │ - Monitors     │
└───────┬────────┘ └───────┬────────┘ └───────┬────────┘
        │                  │                  │
        │                  │                  │
        ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Database   │  │    Redis     │  │  File Store  │         │
│  │   (SQLite)   │  │  (Cache/Q)   │  │   (Models)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ Drift Monitor  │ │  Retraining    │ │   MLFlow       │
│  (Background)  │ │    Worker      │ │   Registry     │
│                │ │  (Background)  │ │                │
│ - Checks drift │ │ - Trains model │ │ - Tracks exp   │
│ - Triggers job │ │ - Registers    │ │ - Versions     │
└────────────────┘ └────────────────┘ └────────────────┘
```

## Service Descriptions

### 1. Ingestion API (Port 8001)
**Purpose**: Entry point for all data

**Responsibilities**:
- Validate incoming data
- Queue data for processing
- Handle batch and streaming ingestion
- Provide ingestion statistics

**Technology**: Flask REST API

**Endpoints**:
- `POST /ingest/batch` - Batch data ingestion
- `POST /ingest/stream` - Stream single sample
- `GET /stats` - Ingestion statistics
- `GET /health` - Health check

### 2. Prediction Service (Port 8002)
**Purpose**: Serve model predictions

**Responsibilities**:
- Load and cache active model
- Make predictions
- Buffer predictions for drift monitoring
- Handle batch predictions
- Reload model after retraining

**Technology**: Flask REST API

**Endpoints**:
- `POST /predict` - Single/batch predictions
- `POST /predict/batch` - Optimized batch predictions
- `POST /reload_model` - Reload model
- `GET /health` - Health check

### 3. Drift Monitor (Background Service)
**Purpose**: Continuously monitor for data drift

**Responsibilities**:
- Collect recent predictions
- Run statistical drift tests
- Log drift events
- Trigger retraining when drift detected

**Technology**: Python background worker

**Drift Detection Methods**:
- Kolmogorov-Smirnov test
- Population Stability Index (PSI)
- Mean/Std deviation analysis

### 4. Retraining Worker (Background Service)
**Purpose**: Handle model retraining jobs

**Responsibilities**:
- Process retraining queue
- Train new models
- Log to MLFlow
- Register models
- Notify prediction service

**Technology**: Python background worker

**Process**:
1. Pick job from queue
2. Fetch training data
3. Train model with cross-validation
4. Evaluate and log metrics
5. Register model
6. Notify services

### 5. Dashboard (Port 8050)
**Purpose**: Real-time monitoring and visualization

**Responsibilities**:
- Display real-time metrics
- Visualize drift events
- Show training history
- Monitor system health

**Technology**: Dash (Plotly)

**Features**:
- Auto-refresh every 5 seconds
- Interactive charts
- Statistics cards
- Historical analysis

## Data Flow

### Prediction Flow
```
1. Client → Ingestion API
   - Validates data
   - Queues in Redis

2. Ingestion API → Prediction Service
   - Fetches from queue
   - Makes prediction

3. Prediction Service → Redis Buffer
   - Stores for drift monitoring

4. Prediction Service → Database
   - Logs prediction

5. Prediction Service → Client
   - Returns result
```

### Drift Detection Flow
```
1. Drift Monitor (periodic)
   - Collects recent predictions from buffer

2. Drift Monitor → Drift Detector
   - Runs statistical tests

3. If Drift Detected:
   - Logs to database
   - Pushes job to retraining queue

4. Retraining Worker
   - Picks up job
   - Trains new model
   - Registers model

5. Prediction Service
   - Reloads new model
```

## Technology Stack

### Backend
- **Python 3.9+**: Main language
- **Flask**: REST APIs
- **scikit-learn**: ML algorithms
- **NumPy/SciPy**: Numerical computing

### Data Storage
- **SQLite**: Database (dev), PostgreSQL (prod)
- **Redis**: Caching and message queues
- **File System**: Model storage

### Monitoring
- **Dash/Plotly**: Dashboard
- **MLFlow**: Experiment tracking
- **Logging**: Structured logs

### DevOps
- **Docker**: Containerization
- **Docker Compose**: Orchestration
- **pytest**: Testing

## Scalability Considerations

### Horizontal Scaling
- **Prediction Service**: Multiple instances behind load balancer
- **Retraining Worker**: Multiple workers for parallel training
- **Drift Monitor**: Sharded by feature groups

### Vertical Scaling
- **Database**: Upgrade to PostgreSQL with read replicas
- **Cache**: Redis cluster
- **Model Serving**: GPU instances for deep learning

### Performance Optimizations
1. **Caching**: Redis for model and predictions
2. **Batch Processing**: Vectorized operations
3. **Async Operations**: Non-blocking I/O
4. **Connection Pooling**: Database connections
5. **Model Compression**: Quantization, pruning

## Security

### Current (Development)
- Basic validation
- No authentication
- Local network only

### Production Requirements
1. **Authentication**: JWT tokens
2. **Authorization**: Role-based access
3. **Encryption**: TLS/SSL for all communication
4. **Input Validation**: Strict schema validation
5. **Rate Limiting**: Per-user quotas
6. **Audit Logging**: All API calls logged

## Monitoring & Observability

### Metrics to Track
1. **System Metrics**:
   - CPU, Memory, Disk usage
   - Network I/O
   - Container health

2. **Application Metrics**:
   - Request rate, latency
   - Error rate
   - Queue sizes

3. **ML Metrics**:
   - Prediction accuracy
   - Drift score
   - Training time
   - Model size

### Logging Strategy
- **Structured Logging**: JSON format
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Centralized**: ELK stack or CloudWatch
- **Retention**: 30 days

### Alerting
- Drift detected
- Model accuracy drop
- Service down
- High error rate
- Queue backup

## Deployment

### Development
```bash
docker-compose up -d
```

### Production (Kubernetes)
```yaml
# Deployment with:
- Multiple replicas
- Auto-scaling
- Health checks
- Resource limits
- Persistent volumes
```

## Future Enhancements

### Short Term
1. Add API Gateway (Kong, Nginx)
2. Implement authentication
3. Add Prometheus metrics
4. Set up Grafana dashboards

### Long Term
1. Kubernetes deployment
2. A/B testing framework
3. Multi-model serving
4. Feature store (Feast)
5. Model explainability
6. Distributed training
