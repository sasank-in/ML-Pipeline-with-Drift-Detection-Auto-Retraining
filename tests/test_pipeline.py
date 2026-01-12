"""Unit tests for ML Pipeline"""
import pytest
import numpy as np
from sklearn.datasets import make_classification
from pipeline import MLPipeline
from config import Config

@pytest.fixture
def sample_data():
    """Generate sample data for testing"""
    X, y = make_classification(
        n_samples=1000,
        n_features=10,
        n_informative=8,
        n_redundant=2,
        n_classes=2,
        random_state=42
    )
    return X, y

@pytest.fixture
def pipeline():
    """Create pipeline instance"""
    config = Config()
    config.drift.window_size = 100
    config.pipeline.retrain_window = 100
    return MLPipeline(config)

def test_pipeline_initialization(pipeline, sample_data):
    """Test pipeline initialization"""
    X, y = sample_data
    metrics = pipeline.initialize(X, y)
    
    assert pipeline.is_initialized
    assert 'accuracy' in metrics
    assert 'f1_score' in metrics
    assert metrics['accuracy'] > 0.5

def test_prediction(pipeline, sample_data):
    """Test prediction functionality"""
    X, y = sample_data
    pipeline.initialize(X[:800], y[:800])
    
    result = pipeline.predict(X[800:900])
    
    assert 'predictions' in result
    assert 'probabilities' in result
    assert len(result['predictions']) == 100
    assert result['probabilities'].shape == (100, 2)

def test_label_update(pipeline, sample_data):
    """Test label buffer update"""
    X, y = sample_data
    pipeline.initialize(X[:800], y[:800])
    
    pipeline.predict(X[800:900])
    pipeline.update_labels(y[800:900])
    
    assert len(pipeline.label_buffer) == 100

def test_drift_detection(pipeline, sample_data):
    """Test drift detection"""
    X, y = sample_data
    pipeline.initialize(X[:500], y[:500])
    
    # Add normal data
    pipeline.predict(X[500:600])
    pipeline.update_labels(y[500:600])
    
    result = pipeline.check_and_retrain()
    assert result['checked']
    assert 'drift_detected' in result

def test_retraining_on_drift(pipeline):
    """Test automatic retraining on drift"""
    # Initial training
    X_init, y_init = make_classification(
        n_samples=500, n_features=10, random_state=42
    )
    pipeline.initialize(X_init, y_init)
    
    # Generate drifted data
    X_drift, y_drift = make_classification(
        n_samples=200, n_features=10, random_state=100
    )
    X_drift = X_drift + np.random.normal(3, 1, X_drift.shape)
    
    pipeline.predict(X_drift)
    pipeline.update_labels(y_drift)
    
    result = pipeline.check_and_retrain()
    
    # Drift should be detected with high probability
    assert result['checked']

def test_stats_retrieval(pipeline, sample_data):
    """Test statistics retrieval"""
    X, y = sample_data
    pipeline.initialize(X[:800], y[:800])
    pipeline.predict(X[800:900])
    
    stats = pipeline.get_stats()
    
    assert 'predictions_made' in stats
    assert 'buffer_size' in stats
    assert 'model_version' in stats
    assert stats['predictions_made'] == 100

def test_feature_importance(pipeline, sample_data):
    """Test feature importance extraction"""
    X, y = sample_data
    pipeline.initialize(X, y)
    
    importance = pipeline.get_feature_importance()
    
    assert importance is not None
    assert len(importance) == 10
