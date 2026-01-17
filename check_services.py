"""Check if all services are accessible"""
import requests
import time

services = [
    ("Ingestion API", "http://localhost:8001/health"),
    ("Prediction Service", "http://localhost:8002/health"),
    ("Dashboard", "http://localhost:8050"),
]

print("Checking services...\n")

for name, url in services:
    try:
        r = requests.get(url, timeout=2)
        if r.status_code == 200:
            print(f"[OK] {name}: {url}")
            if 'json' in r.headers.get('content-type', ''):
                print(f"     {r.json()}")
        else:
            print(f"[FAIL] {name}: Status {r.status_code}")
    except Exception as e:
        print(f"[FAIL] {name}: {e}")

print("\nTo start services, run:")
print("  python start_services.py")
print("\nOr use batch file:")
print("  run_all_services.bat")
