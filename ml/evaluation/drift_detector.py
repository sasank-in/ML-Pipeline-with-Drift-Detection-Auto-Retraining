"""Drift detection algorithms"""
import numpy as np
from scipy import stats
from typing import Dict, Tuple, List
import sys
sys.path.append('../..')

from shared.logger import setup_logger

logger = setup_logger("drift_detector")

class DriftDetector:
    """Detects data drift using statistical tests"""
    
    def __init__(self, threshold: float = 0.05, window_size: int = 1000):
        self.threshold = threshold
        self.window_size = window_size
        self.reference_data = None
        self.feature_names = None
        
    def set_reference(self, data: np.ndarray, feature_names: List[str] = None):
        """Set reference data"""
        self.reference_data = data
        self.feature_names = feature_names or [f'feature_{i}' for i in range(data.shape[1])]
        logger.info(f"Reference data set: {data.shape}")
        
    def detect_drift(self, current_data: np.ndarray) -> Tuple[bool, Dict]:
        """Detect drift using multiple methods"""
        if self.reference_data is None:
            raise ValueError("Reference data not set")
            
        results = {
            'overall_drift': False,
            'features': {},
            'summary': {}
        }
        
        drift_count = 0
        
        for i in range(current_data.shape[1]):
            feature_name = self.feature_names[i]
            
            # KS test
            ks_stat, ks_pvalue = stats.ks_2samp(
                self.reference_data[:, i],
                current_data[:, i]
            )
            
            # PSI
            psi = self._calculate_psi(
                self.reference_data[:, i],
                current_data[:, i]
            )
            
            # Mean shift
            ref_mean = np.mean(self.reference_data[:, i])
            curr_mean = np.mean(current_data[:, i])
            ref_std = np.std(self.reference_data[:, i])
            mean_shift = abs(curr_mean - ref_mean) / (ref_std + 1e-10)
            
            # Drift detected?
            drift_detected = (
                ks_pvalue < self.threshold or 
                psi > 0.2 or 
                mean_shift > 2.0
            )
            
            if drift_detected:
                drift_count += 1
                
            results['features'][feature_name] = {
                'ks_statistic': float(ks_stat),
                'ks_pvalue': float(ks_pvalue),
                'psi': float(psi),
                'mean_shift': float(mean_shift),
                'drift_detected': drift_detected
            }
        
        # Overall drift
        results['overall_drift'] = drift_count > (len(self.feature_names) * 0.2)
        results['summary'] = {
            'total_features': len(self.feature_names),
            'features_with_drift': drift_count,
            'drift_percentage': (drift_count / len(self.feature_names)) * 100
        }
        
        return results['overall_drift'], results
        
    def _calculate_psi(self, reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
        """Calculate Population Stability Index"""
        breakpoints = np.percentile(reference, np.linspace(0, 100, bins + 1))
        breakpoints = np.unique(breakpoints)
        
        if len(breakpoints) < 2:
            return 0.0
        
        ref_counts, _ = np.histogram(reference, bins=breakpoints)
        curr_counts, _ = np.histogram(current, bins=breakpoints)
        
        ref_dist = ref_counts / len(reference)
        curr_dist = curr_counts / len(current)
        
        ref_dist = np.where(ref_dist == 0, 0.0001, ref_dist)
        curr_dist = np.where(curr_dist == 0, 0.0001, curr_dist)
        
        psi = np.sum((curr_dist - ref_dist) * np.log(curr_dist / ref_dist))
        
        return psi
