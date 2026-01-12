"""Complete example demonstrating the ML pipeline"""
import requests
import numpy as np
from sklearn.datasets import make_classification
import time

BASE_URL_INGESTION = "http://localhost:8001"
BASE_URL_PREDICTION = "http://localhost:8002"

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def check_services():
    """Check if services are running"""
    print_section("CHECKING SERVICES")
    
    services = [
        ("Ingestion API", f"{BASE_URL_INGESTION}/health"),
        ("Prediction Service", f"{BASE_URL_PREDICTION}/health"),
    ]
    
    for name, url in services:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print(f"✅ {name}: {response.json()}")
            else:
                print(f"❌ {name}: Not responding")
        except:
            print(f"❌ {name}: Not available")

def ingest_training_data():
    """Ingest initial training data"""
    print_section("PHASE 1: INGESTING TRAINING DATA")
    
    # Generate training data
    X_train, y_train = make_classification(
        n_samples=2000,
        n_features=20,
        n_informative=15,
        n_redundant=5,
        n_classes=3,
        random_state=42
    )
    
    print(f"Generated {X_train.shape[0]} samples with {X_train.shape[1]} features")
    
    # Ingest in batches
    batch_size = 500
    for i in range(0, len(X_train), batch_size):
        batch_X = X_train[i:i+batch_size]
        batch_y = y_train[i:i+batch_size]
        
        response = requests.post(
            f"{BASE_URL_INGESTION}/ingest/batch",
            json={
                'features': batch_X.tolist(),
                'labels': batch_y.tolist(),
                'batch_id': f'train_batch_{i//batch_size}'
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Batch {i//batch_size + 1}: Ingested {result['samples_ingested']} samples")
        else:
            print(f"❌ Batch {i//batch_size + 1}: Failed")
    
    print("\n⏳ Waiting for initial model training...")
    time.sleep(5)

def make_predictions():
    """Make predictions on normal data"""
    print_section("PHASE 2: MAKING PREDICTIONS (Normal Data)")
    
    for batch_num in range(10):
        # Generate test data
        X_test, _ = make_classification(
            n_samples=100,
            n_features=20,
            n_informative=15,
            n_redundant=5,
            n_classes=3,
            random_state=100 + batch_num
        )
        
        response = requests.post(
            f"{BASE_URL_PREDICTION}/predict",
            json={'features': X_test.tolist()}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Batch {batch_num + 1}: {len(result['predictions'])} predictions, "
                  f"time: {result['prediction_time']:.4f}s, "
                  f"model: {result['model_version']}")
        else:
            print(f"❌ Batch {batch_num + 1}: Prediction failed")
        
        time.sleep(0.5)

def introduce_drift():
    """Introduce data drift"""
    print_section("PHASE 3: INTRODUCING DATA DRIFT")
    
    for batch_num in range(10):
        # Generate drifted data
        shift_amount = (batch_num + 1) * 0.5
        
        X_drift, _ = make_classification(
            n_samples=100,
            n_features=20,
            n_informative=15,
            n_redundant=5,
            n_classes=3,
            random_state=200 + batch_num
        )
        
        # Apply drift
        X_drift = X_drift + np.random.normal(shift_amount, 0.5, X_drift.shape)
        
        response = requests.post(
            f"{BASE_URL_PREDICTION}/predict",
            json={'features': X_drift.tolist()}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Batch {batch_num + 1} (Shift: {shift_amount:.1f}): "
                  f"{len(result['predictions'])} predictions")
        else:
            print(f"❌ Batch {batch_num + 1}: Failed")
        
        time.sleep(0.5)
    
    print("\n⏳ Waiting for drift detection and retraining...")
    time.sleep(10)

def check_stats():
    """Check ingestion statistics"""
    print_section("PIPELINE STATISTICS")
    
    response = requests.get(f"{BASE_URL_INGESTION}/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"Batch Queue Size: {stats['batch_queue_size']}")
        print(f"Stream Queue Size: {stats['stream_queue_size']}")

def main():
    """Run complete pipeline example"""
    print("=" * 80)
    print("  REAL-TIME ML PIPELINE DEMONSTRATION")
    print("=" * 80)
    print("\nMake sure all services are running:")
    print("  docker-compose up -d")
    print("\nOr run services individually in separate terminals")
    print("=" * 80)
    
    input("\nPress Enter to start...")
    
    # Check services
    check_services()
    
    # Run pipeline
    ingest_training_data()
    make_predictions()
    introduce_drift()
    check_stats()
    
    print_section("DEMONSTRATION COMPLETE")
    print("\n📊 View the dashboard at: http://localhost:8050")
    print("📁 Check database: data/pipeline.db")
    print("📝 Check logs: logs/")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
