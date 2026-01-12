#!/bin/bash
# Stop all services (Linux/Mac)

echo "=========================================="
echo "  Stopping ML Pipeline Services"
echo "=========================================="
echo ""

# Function to stop service
stop_service() {
    local name=$1
    local pidfile="logs/${name}.pid"
    
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if ps -p $pid > /dev/null 2>&1; then
            echo "  Stopping $name (PID: $pid)..."
            kill $pid
            rm "$pidfile"
        else
            echo "  $name not running"
            rm "$pidfile"
        fi
    else
        echo "  $name PID file not found"
    fi
}

# Stop all services
stop_service "ingestion_api"
stop_service "prediction_service"
stop_service "drift_monitor"
stop_service "retraining_worker"
stop_service "dashboard"

echo ""
echo "✅ All services stopped"
echo ""
