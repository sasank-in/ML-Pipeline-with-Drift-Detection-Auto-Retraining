"""Start all services"""
import subprocess
import sys
import time

services = [
    ("Ingestion API", "python services/ingestion_api/app.py"),
    ("Prediction Service", "python services/prediction_service/app.py"),
    ("Dashboard", "python dashboards/monitoring_app.py"),
]

print("Starting services...")
processes = []

for name, cmd in services:
    print(f"Starting {name}...")
    proc = subprocess.Popen(cmd, shell=True)
    processes.append((name, proc))
    time.sleep(2)

print("\nAll services started!")
print("\nEndpoints:")
print("  Ingestion API:      http://localhost:8001")
print("  Prediction Service: http://localhost:8002")
print("  Dashboard:          http://localhost:8050")
print("\nPress Ctrl+C to stop all services")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping services...")
    for name, proc in processes:
        proc.terminate()
    print("All services stopped")
