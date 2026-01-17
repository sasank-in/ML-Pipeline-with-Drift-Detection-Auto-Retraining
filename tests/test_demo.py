"""Tests for demo pipeline"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pytest


def test_data_loading():
    """Test retail data loading"""
    from demo import load_retail_data
    
    X, y, features = load_retail_data()
    
    assert X is not None
    assert y is not None
    assert len(X) == len(y)
    assert len(features) == 8
    assert X.shape[1] == 8
    assert set(np.unique(y)) == {0, 1}
    print(f"Data: {X.shape}, Target distribution: {np.bincount(y)}")


def test_model_training():
    """Test model training with retail data"""
    from demo import load_retail_data
    from ml.training.trainer import ModelTrainer
    from sklearn.model_selection import train_test_split
    
    X, y, _ = load_retail_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    
    trainer = ModelTrainer(model_path="models/test_retail.pkl")
    metrics, version = trainer.train(X_train, y_train)
    
    assert metrics['accuracy'] > 0.7
    assert metrics['f1_score'] > 0.5
    assert trainer.model is not None
    print(f"Accuracy: {metrics['accuracy']:.4f}")


def test_predictions():
    """Test model predictions"""
    from demo import load_retail_data
    from ml.training.trainer import ModelTrainer
    from sklearn.model_selection import train_test_split
    
    X, y, _ = load_retail_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    
    trainer = ModelTrainer()
    trainer.train(X_train, y_train)
    
    predictions = trainer.model.predict(X_test)
    
    assert len(predictions) == len(y_test)
    assert set(np.unique(predictions)).issubset({0, 1})
    
    accuracy = np.mean(predictions == y_test)
    assert accuracy > 0.7
    print(f"Test accuracy: {accuracy:.4f}")


def test_drift_detection():
    """Test drift detection"""
    from demo import load_retail_data
    from ml.evaluation.drift_detector import DriftDetector
    from sklearn.model_selection import train_test_split
    
    X, y, _ = load_retail_data()
    X_train, X_test, _, _ = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    
    detector = DriftDetector(threshold=0.05)
    detector.set_reference(X_train)
    
    drift_normal, _ = detector.detect_drift(X_test)
    
    X_drifted = X_test + np.random.normal(2.0, 0.5, X_test.shape)
    drift_shifted, _ = detector.detect_drift(X_drifted)
    
    assert drift_shifted == True
    print(f"Normal drift: {drift_normal}, Shifted drift: {drift_shifted}")


def test_database_logging():
    """Test database operations"""
    from shared.database import DatabaseManager
    
    db = DatabaseManager()
    
    db.log_prediction(
        features=[1.0] * 8,
        prediction=1,
        probability=0.85,
        model_version="test_v1"
    )
    
    db.register_model(
        model_version="test_v1",
        model_path="models/test.pkl",
        metrics={'accuracy': 0.9},
        status='test'
    )
    
    print("Database operations successful")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("DEMO TESTS")
    print("=" * 60)
    
    tests = [
        ("Data Loading", test_data_loading),
        ("Model Training", test_model_training),
        ("Predictions", test_predictions),
        ("Drift Detection", test_drift_detection),
        ("Database", test_database_logging),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n[TEST] {name}")
        try:
            test_func()
            results.append((name, True))
            print(f"[PASS] {name}")
        except Exception as e:
            results.append((name, False))
            print(f"[FAIL] {name}: {e}")
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    print(f"Passed: {passed}/{len(results)}")
    
    return all(r for _, r in results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
