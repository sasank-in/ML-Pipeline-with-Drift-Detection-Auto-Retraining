"""Drift Monitor Service - Continuously monitors for data drift"""
import sys
import os
# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import time
import numpy as np
from threading import Thread

from shared.config import Config
from shared.logger import setup_logger
from shared.database import DatabaseManager
from shared.redis_client import RedisClient
from ml.evaluation.drift_detector import DriftDetector

logger = setup_logger("drift_monitor")
config = Config()
db = DatabaseManager()
redis_client = RedisClient(config.redis.host, config.redis.port)
drift_detector = DriftDetector(config.drift.threshold, config.drift.window_size)

class DriftMonitor:
    """Monitors for data drift and triggers retraining"""
    
    def __init__(self):
        self.running = False
        self.reference_data = None
        
    def load_reference_data(self):
        """Load reference data from database"""
        # In production, load from feature store
        logger.info("Loading reference data...")
        # For now, use cached data
        cached = redis_client.get('reference_data')
        if cached:
            self.reference_data = np.array(cached)
            drift_detector.set_reference(self.reference_data)
            logger.info(f"Reference data loaded: {self.reference_data.shape}")
        else:
            logger.warning("No reference data found")
            
    def collect_recent_data(self) -> np.ndarray:
        """Collect recent predictions from buffer"""
        buffer = []
        
        # Get from Redis prediction buffer
        for _ in range(config.drift.window_size):
            item = redis_client.rpop('prediction_buffer')
            if item:
                buffer.extend(item['features'])
            else:
                break
        
        if buffer:
            return np.array(buffer)
        return None
        
    def check_drift(self):
        """Check for drift in recent data"""
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
            logger.warning(f"⚠️  DRIFT DETECTED! Score: {drift_score:.2f}, "
                         f"Affected features: {len(affected_features)}")
            
            # Trigger retraining
            self.trigger_retraining(drift_metrics)
        else:
            logger.info(f"✅ No drift detected. Score: {drift_score:.2f}")
            
    def trigger_retraining(self, drift_metrics: dict):
        """Trigger retraining job"""
        job_data = {
            'trigger': 'drift_detected',
            'drift_metrics': drift_metrics,
            'timestamp': time.time()
        }
        
        redis_client.lpush('retraining_queue', job_data)
        logger.info("🔄 Retraining job triggered")
        
    def run(self):
        """Main monitoring loop"""
        self.running = True
        logger.info("Drift monitor started")
        
        while self.running:
            try:
                self.check_drift()
                time.sleep(config.drift.check_interval)
            except Exception as e:
                logger.error(f"Error in drift monitoring: {str(e)}")
                time.sleep(60)
                
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
