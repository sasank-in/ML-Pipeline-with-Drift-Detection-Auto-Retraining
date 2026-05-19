"""Retraining Worker - Handles model retraining jobs"""
import sys
import os
# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import time
import uuid
import glob

from shared.config import Config
from shared.logger import setup_logger
from shared.database import DatabaseManager
from ml.training.trainer import ModelTrainer
from registry.mlflow.mlflow_client import MLFlowClient

logger = setup_logger("retraining_worker")
config = Config()
db = DatabaseManager()
mlflow_client = MLFlowClient(config.mlflow.tracking_uri, config.mlflow.experiment_name)

class RetrainingWorker:
    """Worker that processes retraining jobs"""
    
    def __init__(self):
        self.running = False
        self.trainer = ModelTrainer(config.model)
        self.keep_n_models = int(os.getenv('KEEP_N_MODELS', '5'))

    def rotate_models(self):
        """Delete older .pkl files in models/, keeping only the newest N.

        Never deletes the currently-deployed model regardless of age.
        """
        try:
            active = db.get_active_model()
            active_path = os.path.abspath(active['model_path']) if active and active.get('model_path') else None

            files = glob.glob('models/*.pkl')
            files.sort(key=os.path.getmtime, reverse=True)
            to_delete = files[self.keep_n_models:]
            for path in to_delete:
                if os.path.abspath(path) == active_path:
                    continue
                try:
                    os.remove(path)
                    logger.info(f"Rotated out old model: {path}")
                except OSError as e:
                    logger.warning(f"Could not remove {path}: {e}")
        except Exception as e:
            logger.warning(f"Model rotation failed: {e}")
        
    def process_job(self, job_data: dict):
        """Process a retraining job"""
        job_id = str(uuid.uuid4())
        logger.info(f"Processing retraining job: {job_id}")
        
        # Log job start
        db.log_training_job(
            job_id=job_id,
            status='started',
            trigger_reason=job_data.get('trigger', 'manual')
        )
        
        try:
            # Get training data
            training_data = self.get_training_data()
            
            if training_data is None:
                logger.error("No training data available")
                db.log_training_job(job_id=job_id, status='failed')
                return
            
            X_train, y_train = training_data
            
            # Start MLFlow run
            run_id = mlflow_client.start_run(f"retrain_{job_id}")
            
            # Log parameters
            mlflow_client.log_params({
                'trigger': job_data.get('trigger'),
                'samples': len(X_train),
                'job_id': job_id
            })
            
            # Train model
            logger.info(f"Training model with {len(X_train)} samples...")
            metrics, model_version = self.trainer.train(X_train, y_train)
            
            # Log metrics to MLFlow
            mlflow_client.log_metrics(metrics)
            
            # Register model
            model_path = f"models/model_{model_version}.pkl"
            self.trainer.save_model(model_path)
            
            db.register_model(
                model_version=model_version,
                model_path=model_path,
                metrics=metrics,
                status='trained'
            )
            db.deploy_model(model_version)
            self.rotate_models()
            
            # Log success
            db.log_training_job(
                job_id=job_id,
                status='completed',
                metrics=metrics,
                model_version=model_version,
                trigger_reason=job_data.get('trigger'),
                mlflow_run_id=run_id
            )
            
            # End MLFlow run
            mlflow_client.end_run()
            
            logger.info(f"Retraining completed: {model_version}, "
                       f"Accuracy: {metrics['accuracy']:.4f}")
            
        except Exception as e:
            logger.error(f"Retraining failed: {str(e)}")
            db.log_training_job(job_id=job_id, status='failed')
            mlflow_client.end_run(status='FAILED')
            
    def get_training_data(self):
        """Get training data from batch queue and stream queue.

        Handles both shapes:
          - batch: {'features': [[...], [...]], 'labels': [y1, y2]}
          - stream: {'features': [...], 'label': y}
        Only rows with a label are kept (supervised training requires y).
        """
        import numpy as np

        data_buffer = []
        label_buffer = []

        def take(queue_name: str):
            for _ in range(config.drift.window_size):
                item = db.dequeue(queue_name)
                if not item:
                    break
                feats = item.get('features')
                if feats is None:
                    continue

                # Batch shape: 2D features + list of labels
                if isinstance(feats, list) and feats and isinstance(feats[0], (list, tuple)):
                    labels = item.get('labels')
                    if labels is None or len(labels) != len(feats):
                        continue
                    for row, y in zip(feats, labels):
                        if y is None:
                            continue
                        data_buffer.append(row)
                        label_buffer.append(y)
                else:
                    # Stream shape: single row + single label
                    y = item.get('label')
                    if y is None:
                        continue
                    data_buffer.append(feats)
                    label_buffer.append(y)

        take('data_queue')
        take('stream_queue')

        if data_buffer and label_buffer:
            return np.array(data_buffer), np.array(label_buffer)

        return None
        
    def run(self):
        """Main worker loop with bounded exponential backoff on errors."""
        self.running = True
        logger.info("Retraining worker started")

        backoff = 1.0
        max_backoff = 300.0

        while self.running:
            try:
                job_data = db.dequeue('retraining_queue')

                if job_data:
                    self.process_job(job_data)
                    backoff = 1.0
                    continue

                # Bootstrap training if no active model and data is available
                if db.get_active_model() is None:
                    bootstrap_job = {'trigger': 'bootstrap', 'timestamp': time.time()}
                    self.process_job(bootstrap_job)

                backoff = 1.0  # idle = not an error
                time.sleep(10)

            except Exception as e:
                logger.error(f"Worker error (retry in {backoff:.0f}s): {e}")
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                
    def stop(self):
        """Stop worker"""
        self.running = False
        logger.info("Retraining worker stopped")

if __name__ == '__main__':
    worker = RetrainingWorker()
    
    try:
        worker.run()
    except KeyboardInterrupt:
        worker.stop()
