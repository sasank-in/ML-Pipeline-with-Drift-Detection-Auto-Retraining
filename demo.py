"""Complete demonstration of ML pipeline using real lung disease data"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
import requests
import time
from sklearn.model_selection import train_test_split

BASE_URL_INGESTION = "http://localhost:8001"
BASE_URL_PREDICTION = "http://localhost:8002"

def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def load_lung_disease_data():
    """Load and prepare lung disease dataset"""
    print_section("LOADING LUNG DISEASE DATASET")
    
    try:
        # Load the CSV file
        df = pd.read_csv('data/lung_disease.csv')
        print(f"✓ Dataset loaded: {df.shape[0]} samples, {df.shape[1]} columns")
        
        # Separate features and target
        X = df.drop('lung_disease', axis=1).values
        y = df['lung_disease'].values
        
        feature_names = df.drop('lung_disease', axis=1).columns.tolist()
        
        print(f"✓ Features: {len(feature_names)}")
        print(f"✓ Target distribution: {np.bincount(y)}")
        
        return X, y, feature_names
        
    except FileNotFoundError:
        print("❌ lung_disease.csv not found in data/ directory")
        print("Creating sample dataset...")
        
        # Create sample data if file doesn't exist
        np.random.seed(42)
        n_samples = 100
        
        X = np.random.randint(0, 2, size=(n_samples, 15))
        X[:, 0] = np.random.randint(35, 75, size=n_samples)  # age
        y = np.random.randint(0, 2, size=n_samples)
        
        feature_names = ['age', 'gender', 'smoking', 'yellow_fingers', 'anxiety',
                        'peer_pressure', 'chronic_disease', 'fatigue', 'allergy',
                        'wheezing', 'alcohol', 'coughing', 'shortness_of_breath',
                        'swallowing_difficulty', 'chest_pain']
        
        print(f"✓ Sample dataset created: {n_samples} samples")
        return X, y, feature_names

def check_services():
    """Check if services are running"""
    print_section("CHECKING SERVICES")
    
    services = [
        ("Ingestion API", f"{BASE_URL_INGESTION}/health"),
        ("Prediction Service", f"{BASE_URL_PREDICTION}/health"),
    ]
    
    all_running = True
    for name, url in services:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print(f"✓ {name}: Running")
            else:
                print(f"❌ {name}: Not responding properly")
                all_running = False
        except:
            print(f"❌ {name}: Not available")
            all_running = False
    
    if not all_running:
        print("\n⚠️  Some services are not running!")
        print("Please run: run_all_services.bat (Windows) or ./run_all_services.sh (Linux/Mac)")
        print("Wait 10 seconds, then run this demo again.")
        return False
    
    return True

def ingest_training_data(X_train, y_train):
    """Ingest training data to the pipeline"""
    print_section("PHASE 1: INGESTING TRAINING DATA")
    
    print(f"Training data: {X_train.shape[0]} samples, {X_train.shape[1]} features")
    
    # Ingest in batches
    batch_size = 20
    total_batches = (len(X_train) + batch_size - 1) // batch_size
    
    for i in range(0, len(X_train), batch_size):
        batch_X = X_train[i:i+batch_size]
        batch_y = y_train[i:i+batch_size]
        
        try:
            response = requests.post(
                f"{BASE_URL_INGESTION}/ingest/batch",
                json={
                    'features': batch_X.tolist(),
                    'labels': batch_y.tolist(),
                    'batch_id': f'train_batch_{i//batch_size}'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Batch {i//batch_size + 1}/{total_batches}: Ingested {result['samples_ingested']} samples")
            else:
                print(f"❌ Batch {i//batch_size + 1}: Failed - {response.text}")
                
        except Exception as e:
            print(f"❌ Batch {i//batch_size + 1}: Error - {str(e)}")
    
    print("\n⏳ Waiting for initial model training (5 seconds)...")
    time.sleep(5)

def make_predictions(X_test, y_test, phase_name="NORMAL OPERATION"):
    """Make predictions on test data"""
    print_section(f"PHASE 2: {phase_name}")
    
    batch_size = 10
    total_batches = (len(X_test) + batch_size - 1) // batch_size
    
    all_predictions = []
    
    for i in range(0, len(X_test), batch_size):
        batch_X = X_test[i:i+batch_size]
        
        try:
            response = requests.post(
                f"{BASE_URL_PREDICTION}/predict",
                json={'features': batch_X.tolist()},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                predictions = result['predictions']
                all_predictions.extend(predictions)
                
                print(f"Batch {i//batch_size + 1}/{total_batches}: "
                      f"{len(predictions)} predictions, "
                      f"time: {result['prediction_time']:.4f}s")
            else:
                print(f"❌ Batch {i//batch_size + 1}: Failed")
                
        except Exception as e:
            print(f"❌ Batch {i//batch_size + 1}: Error - {str(e)}")
        
        time.sleep(0.5)
    
    # Calculate accuracy
    if len(all_predictions) == len(y_test):
        accuracy = np.mean(np.array(all_predictions) == y_test)
        print(f"\n✓ Prediction Accuracy: {accuracy:.2%}")
    
    return all_predictions

def introduce_drift(X_test, drift_amount=2.0):
    """Introduce drift by modifying features"""
    print_section("PHASE 3: INTRODUCING DATA DRIFT")
    
    print(f"Applying drift with shift amount: {drift_amount}")
    
    # Add noise to numeric features
    X_drifted = X_test.copy()
    X_drifted = X_drifted + np.random.normal(drift_amount, 0.5, X_drifted.shape)
    
    # Clip to valid range
    X_drifted = np.clip(X_drifted, 0, 100)
    
    batch_size = 10
    total_batches = (len(X_drifted) + batch_size - 1) // batch_size
    
    for i in range(0, len(X_drifted), batch_size):
        batch_X = X_drifted[i:i+batch_size]
        
        try:
            response = requests.post(
                f"{BASE_URL_PREDICTION}/predict",
                json={'features': batch_X.tolist()},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"Batch {i//batch_size + 1}/{total_batches}: "
                      f"{len(result['predictions'])} predictions (drifted data)")
            else:
                print(f"❌ Batch {i//batch_size + 1}: Failed")
                
        except Exception as e:
            print(f"❌ Batch {i//batch_size + 1}: Error - {str(e)}")
        
        time.sleep(0.5)
    
    print("\n⏳ Waiting for drift detection and retraining (10 seconds)...")
    time.sleep(10)

def check_stats():
    """Check ingestion statistics"""
    print_section("PIPELINE STATISTICS")
    
    try:
        response = requests.get(f"{BASE_URL_INGESTION}/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            print(f"Batch Queue Size: {stats.get('batch_queue_size', 'N/A')}")
            print(f"Stream Queue Size: {stats.get('stream_queue_size', 'N/A')}")
        else:
            print("⚠️  Could not retrieve stats")
    except Exception as e:
        print(f"⚠️  Stats error: {str(e)}")

def main():
    """Run complete pipeline demonstration"""
    print("=" * 80)
    print("  LUNG DISEASE PREDICTION - ML PIPELINE DEMONSTRATION")
    print("=" * 80)
    print("\nThis demo uses real lung disease data to demonstrate:")
    print("  1. Data ingestion")
    print("  2. Model training")
    print("  3. Predictions")
    print("  4. Drift detection")
    print("  5. Auto-retraining")
    print("=" * 80)
    
    # Check if services are running
    if not check_services():
        return
    
    # Load data
    X, y, feature_names = load_lung_disease_data()
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    
    print(f"\nData split:")
    print(f"  Training: {len(X_train)} samples")
    print(f"  Testing: {len(X_test)} samples")
    
    # Run pipeline
    try:
        # Phase 1: Ingest training data
        ingest_training_data(X_train, y_train)
        
        # Phase 2: Make predictions
        predictions = make_predictions(X_test, y_test, "MAKING PREDICTIONS")
        
        # Phase 3: Introduce drift
        introduce_drift(X_test, drift_amount=2.0)
        
        # Check stats
        check_stats()
        
        # Final summary
        print_section("DEMONSTRATION COMPLETE")
        print("\n✅ Successfully demonstrated:")
        print("  ✓ Data ingestion")
        print("  ✓ Model predictions")
        print("  ✓ Drift introduction")
        print("  ✓ Pipeline statistics")
        
        print("\n📊 View the dashboard at: http://localhost:8050")
        print("📁 Check database: data/pipeline.db")
        print("📝 Check logs: logs/")
        
        print("\n" + "=" * 80)
        print("  Thank you for using the ML Pipeline!")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
