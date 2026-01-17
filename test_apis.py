"""Test all APIs are working"""
import requests
import numpy as np

print("Testing APIs...")

print("\n1. Ingestion API")
r = requests.get('http://localhost:8001/health')
print(f"   Status: {r.json()['status']}")

print("\n2. Prediction API")
r = requests.get('http://localhost:8002/health')
print(f"   Status: {r.json()['status']}")
print(f"   Model loaded: {r.json()['model_loaded']}")

print("\n3. Dashboard")
r = requests.get('http://localhost:8050')
print(f"   Status: {r.status_code}")

print("\n4. Test ingestion")
data = {
    'features': np.random.randn(10, 8).tolist(),
    'labels': [0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
    'batch_id': 'test_batch'
}
r = requests.post('http://localhost:8001/ingest/batch', json=data)
print(f"   Ingested: {r.json()['samples_ingested']} samples")

print("\n5. Check stats")
r = requests.get('http://localhost:8001/stats')
print(f"   Queue size: {r.json()['batch_queue_size']}")

print("\nAll APIs working!")
