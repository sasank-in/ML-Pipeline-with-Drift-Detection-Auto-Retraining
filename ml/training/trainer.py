"""Model training module"""
import os
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, train_test_split
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
        self.reference_data = None  # Baseline X for drift detection

    def _cfg(self, key, default):
        # Support both dict and dataclass model_config
        if isinstance(self.config, dict):
            return self.config.get(key, default)
        return getattr(self.config, key, default)

    def train(self, X: np.ndarray, y: np.ndarray, test_size: float = 0.2) -> Tuple[Dict, str]:
        """Train a model with a holdout split. Metrics are computed on the test set."""
        logger.info(f"Training model with {len(X)} samples...")
        start_time = time.time()

        # Holdout split — stratify when possible
        stratify = y if len(np.unique(y)) > 1 and len(y) >= 10 else None
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=test_size,
                random_state=self._cfg('random_state', 42),
                stratify=stratify,
            )
        except ValueError:
            # Fallback for tiny datasets where stratify fails
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=self._cfg('random_state', 42)
            )

        self.model = RandomForestClassifier(
            n_estimators=self._cfg('n_estimators', 100),
            max_depth=self._cfg('max_depth', 10),
            min_samples_split=self._cfg('min_samples_split', 2),
            random_state=self._cfg('random_state', 42),
            n_jobs=-1,
        )

        # Cross-validation on the training fold only
        cv_folds = min(5, max(2, len(X_train) // 5))
        cv_scores = cross_val_score(self.model, X_train, y_train, cv=cv_folds, scoring='accuracy')
        logger.info(f"CV scores (train fold): {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

        self.model.fit(X_train, y_train)

        # Holdout evaluation — these are the headline metrics now
        y_pred = self.model.predict(X_test)
        training_time = time.time() - start_time

        metrics = {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'precision': float(precision_score(y_test, y_pred, average='weighted', zero_division=0)),
            'recall': float(recall_score(y_test, y_pred, average='weighted', zero_division=0)),
            'f1_score': float(f1_score(y_test, y_pred, average='weighted', zero_division=0)),
            'cv_mean': float(cv_scores.mean()),
            'cv_std': float(cv_scores.std()),
            'training_time': training_time,
            'samples_count': int(len(X)),
            'train_samples': int(len(X_train)),
            'test_samples': int(len(X_test)),
        }

        # Save training-time feature distribution as drift baseline
        self.reference_data = np.asarray(X_train)

        model_version = f"v_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(
            f"Training complete (holdout): accuracy={metrics['accuracy']:.4f}, "
            f"f1={metrics['f1_score']:.4f}, time={training_time:.2f}s"
        )

        return metrics, model_version

    def save_model(self, path: str = None):
        """Save trained model and drift baseline together."""
        if self.model is None:
            raise ValueError("No model to save")

        save_path = path or self.model_path
        os.makedirs(os.path.dirname(save_path) or '.', exist_ok=True)

        joblib.dump({
            'model': self.model,
            'reference_data': self.reference_data,
            'timestamp': datetime.now().isoformat(),
        }, save_path)

        logger.info(f"Model saved: {save_path}")
