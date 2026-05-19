"""Drift Monitor Service - Continuously monitors for data drift"""
import sys
import os
# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import time
import numpy as np
import joblib

from shared.config import Config
from shared.logger import setup_logger
from shared.database import DatabaseManager
from ml.evaluation.drift_detector import DriftDetector

logger = setup_logger("drift_monitor")
config = Config()
db = DatabaseManager()
drift_detector = DriftDetector(config.drift.threshold, config.drift.window_size)

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'models'))


def _is_safe_model_path(path: str) -> bool:
    try:
        resolved = os.path.abspath(path)
        return resolved.startswith(MODELS_DIR + os.sep) and resolved.endswith('.pkl')
    except Exception:
        return False

class DriftMonitor:
    """Monitors for data drift and triggers retraining"""
    
    def __init__(self):
        self.running = False
        self.reference_data = None
        self.feature_length = None
        self.reference_model_version = None

    def _normalize_features(self, feature_rows):
        """Ensure all feature rows have the same length."""
        normalized = []
        expected_len = None
        for row in feature_rows:
            if not isinstance(row, (list, tuple, np.ndarray)):
                continue
            if expected_len is None:
                expected_len = len(row)
            if len(row) == expected_len:
                normalized.append(row)
        return normalized, expected_len
        
    def load_reference_data(self):
        """Load reference data from the active model's saved training distribution.

        Falls back to recent predictions only if the model file lacks a baseline
        (e.g. legacy models saved before the trainer was updated)."""
        logger.info("Loading reference data from active model...")
        active = db.get_active_model()

        if active and active.get('model_path') and os.path.exists(active['model_path']) \
                and _is_safe_model_path(active['model_path']):
            try:
                bundle = joblib.load(active['model_path'])
                ref = bundle.get('reference_data') if isinstance(bundle, dict) else None
                if ref is not None and len(ref) > 0:
                    self.reference_data = np.asarray(ref)
                    self.feature_length = self.reference_data.shape[1]
                    self.reference_model_version = active.get('model_version')
                    drift_detector.set_reference(self.reference_data)
                    logger.info(
                        f"Reference loaded from model {self.reference_model_version}: "
                        f"{self.reference_data.shape}"
                    )
                    return
            except Exception as e:
                logger.warning(f"Could not load reference from model: {e}")

        # Legacy fallback — only used if model has no embedded baseline
        logger.warning("No baseline in active model; falling back to recent predictions")
        predictions = db.get_recent_predictions(limit=config.drift.window_size)
        if predictions:
            features = [p['features'] for p in predictions]
            normalized, expected_len = self._normalize_features(features)
            if not normalized:
                logger.warning("Reference data invalid or empty")
                return
            self.feature_length = expected_len
            self.reference_data = np.array(normalized)
            drift_detector.set_reference(self.reference_data)
            logger.info(f"Reference data loaded (fallback): {self.reference_data.shape}")
            return

        logger.warning("No reference data found")

    def _refresh_reference_if_model_changed(self):
        """Reload reference baseline when the deployed model changes."""
        active = db.get_active_model()
        if not active:
            return
        if active.get('model_version') != self.reference_model_version:
            logger.info("Active model changed — refreshing drift reference")
            self.reference_data = None
            self.load_reference_data()
            
    def collect_recent_data(self) -> np.ndarray:
        """Collect recent predictions from buffer (non-destructive read)."""
        items = db.peek_queue('prediction_buffer', limit=config.drift.window_size)
        buffer = []
        for item in items:
            features = item.get('features') if isinstance(item, dict) else None
            if features:
                buffer.extend(features)

        # Keep buffer from growing without bound across runs.
        db.trim_queue('prediction_buffer', keep_last=config.drift.window_size)

        if buffer:
            normalized, expected_len = self._normalize_features(buffer)
            if not normalized:
                return None
            if self.feature_length is not None and expected_len != self.feature_length:
                normalized = [row for row in normalized if len(row) == self.feature_length]
                if not normalized:
                    return None
            return np.array(normalized)
        return None
        
    def check_drift(self):
        """Check for drift in recent data"""
        self._refresh_reference_if_model_changed()
        if self.reference_data is None:
            self.load_reference_data()
            if self.reference_data is None:
                return
        
        # Collect recent data
        recent_data = self.collect_recent_data()
        
        if recent_data is None or len(recent_data) < config.drift.min_samples:
            logger.debug(f"Insufficient data for drift check: {len(recent_data) if recent_data is not None else 0}")
            return
        
        logger.info(f"Checking drift on {len(recent_data)} samples...")
        
        # Detect drift
        drift_detected, drift_metrics = drift_detector.detect_drift(recent_data)
        
        # Calculate drift score
        drift_score = drift_metrics['summary']['drift_percentage'] / 100.0
        affected_features = [
            name for name, metrics in drift_metrics['features'].items()
            if metrics['drift_detected']
        ]
        
        # Log to database
        db.log_drift_event(
            drift_detected=drift_detected,
            drift_score=drift_score,
            affected_features=affected_features,
            drift_metrics=drift_metrics,
            action_taken='retraining_triggered' if drift_detected else 'none'
        )
        
        if drift_detected:
            logger.warning(f"DRIFT DETECTED. Score: {drift_score:.2f}, "
                         f"Affected features: {len(affected_features)}")
            
            # Trigger retraining
            self.trigger_retraining(drift_metrics)
        else:
            logger.info(f"No drift detected. Score: {drift_score:.2f}")
            
    def trigger_retraining(self, drift_metrics: dict):
        """Trigger retraining job"""
        job_data = {
            'trigger': 'drift_detected',
            'drift_metrics': drift_metrics,
            'timestamp': time.time()
        }
        
        db.enqueue('retraining_queue', job_data)
        logger.info("Retraining job triggered")
        
    def run(self):
        """Main monitoring loop with bounded exponential backoff on errors."""
        self.running = True
        logger.info("Drift monitor started")

        backoff = 1.0  # seconds
        max_backoff = 300.0

        while self.running:
            try:
                self.check_drift()
                backoff = 1.0  # reset on success
                time.sleep(config.drift.check_interval)
            except Exception as e:
                logger.error(f"Error in drift monitoring (retry in {backoff:.0f}s): {e}")
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                
    def stop(self):
        """Stop monitoring"""
        self.running = False
        logger.info("Drift monitor stopped")

if __name__ == '__main__':
    monitor = DriftMonitor()
    
    try:
        monitor.run()
    except KeyboardInterrupt:
        monitor.stop()
