# Quick Reference Guide

## 🚀 Start the Project

### Windows
```bash
quick_start.bat
```

### Linux/Mac
```bash
chmod +x quick_start.sh
./quick_start.sh
```

### Manual
```bash
docker-compose up -d
python example_pipeline.py
```

## 🌐 Access Services

- **Dashboard**: http://localhost:8050
- **Ingestion API**: http://localhost:8001
- **Prediction Service**: http://localhost:8002

## 📁 Key Files

- **README.md** - Complete setup & usage guide
- **ARCHITECTURE.md** - System design & architecture
- **example_pipeline.py** - Full demonstration script
- **docker-compose.yml** - Service orchestration

## 🛠️ Common Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Run tests
pytest tests/ -v

# Run example
python example_pipeline.py
```

## 📊 Project Structure

```
services/          # 4 microservices
ml/               # ML components
shared/           # Shared utilities
dashboards/       # Monitoring UI
registry/         # Model registry
tests/            # Unit tests
```

## 🎯 What This Project Does

1. **Ingests Data** - REST API for data input
2. **Makes Predictions** - Serves ML model
3. **Detects Drift** - Monitors data distribution
4. **Auto-Retrains** - Updates model when drift detected
5. **Monitors** - Real-time dashboard

## 📖 Documentation

- **README.md** - Start here for setup
- **ARCHITECTURE.md** - Understand the system design
