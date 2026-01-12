"""Model training module"""
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
import joblib
import time
from datetime import datetime
from typing import Dict, Tuple
import sys
sys.path.append('../..')

from shared.logger import setup_logger

logger = setup_logger("model_trainer")

class ModelTrainer:
    """Handles model training"""
    
    def __init__(self, model_config):
        self.config = model_config
        self.model = None
        
    def train(self, X: np.ndarray, y: np.ndarray) -> Tuple[Dict, str]:
        """Train a model"""
        logger.info(f"Training model with {len(X)} samples...")
        start_time = time.time()
        
        # Create model
        self.model = RandomForestClassifier(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            min_samples_split=self.config.min_samples_split,
            random_state=self.config.random_state,
            n_jobs=-1
        )
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X, y, cv=5, scoring='accuracy')
        logger.info(f"CV scores: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
        
        # Train on full dataset
        self.model.fit(X, y)
        
        # Evaluate
        y_pred = self.model.predict(X)
        training_time = time.time() - start_time
        
        metrics = {
            'accuracy': float(accuracy_score(y, y_pred)),
            'precision': float(precision_score(y, y_pred, average='weighted', zero_division=0)),
            'recall': float(recall_score(y, y_pred, average='weighted', zero_division=0)),
            'f1_score': float(f1_score(y, y_pred, average='weighted', zero_division=0)),
            'cv_mean': float(cv_scores.mean()),
            'cv_std': float(cv_scores.std()),
            'training_time': training_time,
            'samples_count': len(X)
        }
        
        model_version = f"v_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Training complete: accuracy={metrics['accuracy']:.4f}, "
                   f"f1={metrics['f1_score']:.4f}, time={training_time:.2f}s")
        
        return metrics, model_version
        
    def save_model(self, path: str):
        """Save trained model"""
        if self.model is None:
            raise ValueError("No model to save")
            
        joblib.dump({
            'model': self.model,
            'timestamp': datetime.now().isoformat()
        }, path)
        
        logger.info(f"Model saved: {path}")
