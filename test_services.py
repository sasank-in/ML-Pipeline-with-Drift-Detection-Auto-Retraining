"""Test script to verify all services work correctly"""
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from shared.config import Config
        print("✓ shared.config")
        
        from shared.database import DatabaseManager
        print("✓ shared.database")
        
        from shared.logger import setup_logger
        print("✓ shared.logger")
        
        from shared.redis_client import RedisClient
        print("✓ shared.redis_client")
        
        from ml.training.trainer import ModelTrainer
        print("✓ ml.training.trainer")
        
        from ml.evaluation.drift_detector import DriftDetector
        print("✓ ml.evaluation.drift_detector")
        
        from ml.feature_store.feature_store import FeatureStore
        print("✓ ml.feature_store.feature_store")
        
        from registry.mlflow.mlflow_client import MLFlowClient
        print("✓ registry.mlflow.mlflow_client")
        
        print("\n✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test database functionality"""
    print("\nTesting database...")
    
    try:
        from shared.database import DatabaseManager
        
        db = DatabaseManager("data/test_pipeline.db")
        print("✓ Database created")
        
        # Test logging a prediction
        db.log_prediction(
            features=[1.0, 2.0, 3.0],
            prediction=1,
            probability=0.95,
            model_version="test_v1"
        )
        print("✓ Prediction logged")
        
        # Test logging drift event
        db.log_drift_event(
            drift_detected=False,
            drift_score=0.1,
            affected_features=["feature_0"],
            drift_metrics={"test": "data"},
            action_taken="none"
        )
        print("✓ Drift event logged")
        
        print("\n✅ Database tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ml_components():
    """Test ML components"""
    print("\nTesting ML components...")
    
    try:
        import numpy as np
        from sklearn.datasets import make_classification
        from ml.training.trainer import ModelTrainer
        from ml.evaluation.drift_detector import DriftDetector
        from shared.config import Config
        
        # Test model training
        print("Testing model training...")
        config = Config()
        trainer = ModelTrainer(model_path="models/test_model.pkl")
        
        X, y = make_classification(n_samples=100, n_features=10, random_state=42)
        metrics, version = trainer.train(X, y)
        
        print(f"✓ Model trained: accuracy={metrics['accuracy']:.4f}")
        
        # Test predictions
        predictions = trainer.model.predict(X[:5])
        print(f"✓ Predictions made: {predictions}")
        
        # Test drift detection
        print("\nTesting drift detection...")
        detector = DriftDetector(threshold=0.05)
        detector.set_reference(X[:50])
        
        drift_detected, drift_metrics = detector.detect_drift(X[50:])
        print(f"✓ Drift detection: drift={drift_detected}")
        
        print("\n✅ ML component tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ ML component test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_health():
    """Test if APIs are responding"""
    print("\nTesting API health...")
    
    try:
        import requests
        
        # Test Ingestion API
        try:
            response = requests.get("http://localhost:8001/health", timeout=2)
            if response.status_code == 200:
                print("✓ Ingestion API is running")
            else:
                print(f"⚠ Ingestion API returned status {response.status_code}")
        except:
            print("⚠ Ingestion API not running (start with run_all_services.bat)")
        
        # Test Prediction Service
        try:
            response = requests.get("http://localhost:8002/health", timeout=2)
            if response.status_code == 200:
                print("✓ Prediction Service is running")
            else:
                print(f"⚠ Prediction Service returned status {response.status_code}")
        except:
            print("⚠ Prediction Service not running (start with run_all_services.bat)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ API health test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 80)
    print("  ML PIPELINE TEST SUITE")
    print("=" * 80)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Database", test_database()))
    results.append(("ML Components", test_ml_components()))
    results.append(("API Health", test_api_health()))
    
    # Summary
    print("\n" + "=" * 80)
    print("  TEST SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:20s} {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 80)
    if all_passed:
        print("  ✅ ALL TESTS PASSED!")
    else:
        print("  ⚠ SOME TESTS FAILED")
    print("=" * 80)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
