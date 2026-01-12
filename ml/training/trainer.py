"""Model training module"""
import sys
import os
# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
import joblib
import time
from datetime import datetime
from typing import Dict, Tuple

from shared.logger import setup_logger

logger = setup_logger("model_trainer")

class ModelTrainer:
    """Handles model training"""
    
    def __init__(self, model_config=None, model_path="models/model.pkl"):
        self.config = model_config if model_config else {}
        self.model = None
        self.model_path = model_path
        
    def train(self, X: np.ndarray, y: np.ndarray) -> Tuple[Dict, str]:
        """Train a model"""
        logger.info(f"Training model with {len(X)} samples...")
        start_time = time.time()
        
        # Create model
        self.model = RandomForestClassifier(
            n_estimators=self.config.get('n_estimators', 100),
            max_depth=self.config.get('max_depth', 10),
            min_samples_split=self.config.get('min_samples_split', 2),
            random_state=self.config.get('random_state', 42),
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
        
    def save_model(self, path: str = None):
        """Save trained model"""
        if self.model is None:
            raise ValueError("No model to save")
        
        save_path = path or self.model_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
        joblib.dump({
            'model': self.model,
            'timestamp': datetime.now().isoformat()
        }, save_path)
        
        logger.info(f"Model saved: {save_path}")
