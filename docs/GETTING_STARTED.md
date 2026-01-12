# Getting Started Guide

## 📋 Prerequisites

- **Python**: 3.9 or higher
- **pip**: Python package manager (comes with Python)
- **RAM**: 2GB minimum
- **Disk Space**: 500MB free

## 🚀 Installation

### Step 1: Setup Environment

#### Windows
```bash
setup.bat
```

#### Linux/Mac
```bash
chmod +x *.sh
./setup.sh
```

This will:
- Create a Python virtual environment
- Install all required dependencies
- Create necessary directories (data/, logs/, models/)

### Step 2: Start Services

#### Windows
```bash
run_all_services.bat
```
This opens 5 separate windows, one for each service.

#### Linux/Mac
```bash
./run_all_services.sh
```
This runs all services in the background.

**Wait 10 seconds** for all services to initialize.

### Step 3: Run Demo

Open a **new terminal** and run:

#### Windows
```bash
venv\Scripts\activate
python example_pipeline.py
```

#### Linux/Mac
```bash
source venv/bin/activate
python example_pipeline.py
```

## 🌐 Access Services

Once services are running:

- **Dashboard**: http://localhost:8050
- **Ingestion API**: http://localhost:8001
- **Prediction Service**: http://localhost:8002

## 🛑 Stop Services

#### Windows
```bash
stop_all_services.bat
```
Or close all service windows manually.

#### Linux/Mac
```bash
./stop_all_services.sh
```

## 📊 What Each Service Does

1. **Ingestion API** (Port 8001)
   - Receives and validates incoming data
   - Queues data for processing

2. **Prediction Service** (Port 8002)
   - Serves ML model predictions
   - Caches predictions for drift monitoring

3. **Drift Monitor** (Background)
   - Continuously monitors for data drift
   - Triggers retraining when drift detected

4. **Retraining Worker** (Background)
   - Handles model retraining jobs
   - Updates model registry

5. **Dashboard** (Port 8050)
   - Real-time monitoring and visualization
   - Shows metrics, drift events, and training history

## 🔍 Verify Installation

After starting services, check:

```bash
# Check Ingestion API
curl http://localhost:8001/health

# Check Prediction Service
curl http://localhost:8002/health

# Open Dashboard
# Navigate to http://localhost:8050 in browser
```

## 📝 View Logs

Logs are stored in the `logs/` directory:

#### Windows
```bash
type logs\ingestion_api.log
type logs\prediction_service.log
```

#### Linux/Mac
```bash
tail -f logs/ingestion_api.log
tail -f logs/prediction_service.log
```

## 🧪 Run Tests

```bash
# Windows
venv\Scripts\activate
pytest tests/ -v

# Linux/Mac
source venv/bin/activate
pytest tests/ -v
```

## ❗ Troubleshooting

### Python Not Found
**Solution**: Install Python 3.9+ from [python.org](https://www.python.org/downloads/)

### Port Already in Use
**Windows**:
```bash
netstat -ano | findstr :8001
taskkill /PID <pid> /F
```

**Linux/Mac**:
```bash
lsof -ti:8001 | xargs kill -9
```

### Services Not Starting
1. Check logs in `logs/` directory
2. Ensure virtual environment is activated
3. Reinstall dependencies: Delete `venv/` and run setup again

### Import Errors
- Ensure you're in the project root directory
- Activate virtual environment before running

## 📚 Next Steps

1. Read [README.md](README.md) for complete documentation
2. Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design
3. Explore the code in `services/`, `ml/`, and `shared/`
4. Modify configuration in `shared/config.py`

## 🎓 For Presentation

1. **Before**: Run `setup.bat` or `./setup.sh` (one time)
2. **During**: Run `run_all_services.bat` or `./run_all_services.sh`
3. **Demo**: Run `python example_pipeline.py`
4. **Show**: Open http://localhost:8050
5. **Explain**: Walk through the architecture and features

## 💡 Tips

- Keep service windows/processes running while using the system
- Check `logs/` directory for debugging
- Use stop scripts before closing to clean up properly
- Run demo in a separate terminal from services
- Dashboard updates automatically every 5 seconds

## 🆘 Need Help?

- Check logs in `logs/` directory
- Review [README.md](README.md) for detailed information
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Check service health endpoints
