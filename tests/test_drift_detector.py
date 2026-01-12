"""Unit tests for Drift Detector"""
import pytest
import numpy as np
from drift_detector import DriftDetector

@pytest.fixture
def detector():
    """Create drift detector instance"""
    return DriftDetector(threshold=0.05, window_size=100)

@pytest.fixture
def reference_data():
    """Generate reference data"""
    np.random.seed(42)
    return np.random.randn(1000, 5)

def test_set_reference(detector, reference_data):
    """Test setting reference data"""
    detector.set_reference(reference_data)
    assert detector.reference_data is not None
    assert detector.reference_data.shape == reference_data.shape

def test_no_drift_detection(detector, reference_data):
    """Test no drift on similar data"""
    detector.set_reference(reference_data)
    
    # Generate similar data
    np.random.seed(43)
    current_data = np.random.randn(500, 5)
    
    drift_detected, metrics = detector.detect_drift(current_data)
    
    assert isinstance(drift_detected, bool)
    assert 'features' in metrics
    assert 'summary' in metrics

def test_drift_detection_on_shifted_data(detector, reference_data):
    """Test drift detection on shifted distribution"""
    detector.set_reference(reference_data)
    
    # Generate shifted data
    current_data = reference_data[:500] + 3.0
    
    drift_detected, metrics = detector.detect_drift(current_data)
    
    # Should detect drift
    assert 'features' in metrics
    assert metrics['summary']['features_with_drift'] > 0

def test_psi_calculation(detector):
    """Test PSI calculation"""
    reference = np.random.randn(1000)
    current = np.random.randn(1000) + 2.0
    
    psi = detector._calculate_psi(reference, current)
    
    assert isinstance(psi, float)
    assert psi >= 0

def test_feature_names(detector, reference_data):
    """Test custom feature names"""
    feature_names = [f'custom_feature_{i}' for i in range(5)]
    detector.set_reference(reference_data, feature_names)
    
    assert detector.feature_names == feature_names
