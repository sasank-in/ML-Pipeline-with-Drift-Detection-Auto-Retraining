#!/bin/bash
# Run all services locally without Docker (Linux/Mac)

echo "=========================================="
echo "  Starting ML Pipeline Services"
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    exit 1
fi

echo "✅ Python is installed"
echo ""

# Create directories
echo "📁 Creating directories..."
mkdir -p data logs models
echo "✅ Directories created"
echo ""

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✅ Dependencies installed"
echo ""

# Start services in background
echo "🚀 Starting services..."
echo ""

# Function to start service
start_service() {
    local name=$1
    local script=$2
    local log=$3
    
    echo "  Starting $name..."
    nohup python $script > logs/$log 2>&1 &
    echo $! > logs/${name}.pid
    sleep 2
}

# Start all services
start_service "ingestion_api" "services/ingestion_api/app.py" "ingestion_api.log"
start_service "prediction_service" "services/prediction_service/app.py" "prediction_service.log"
start_service "drift_monitor" "services/drift_monitor/monitor.py" "drift_monitor.log"
start_service "retraining_worker" "services/retraining_worker/worker.py" "retraining_worker.log"
start_service "dashboard" "dashboards/monitoring_app.py" "dashboard.log"

echo ""
echo "=========================================="
echo "  All Services Started!"
echo "=========================================="
echo ""
echo "Services running:"
echo "  1. Ingestion API (Port 8001)"
echo "  2. Prediction Service (Port 8002)"
echo "  3. Drift Monitor (Background)"
echo "  4. Retraining Worker (Background)"
echo "  5. Dashboard (Port 8050)"
echo ""
echo "📊 Dashboard: http://localhost:8050"
echo "📝 Logs: logs/"
echo ""
echo "To stop: ./stop_all_services.sh"
echo ""
