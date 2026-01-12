"""Retraining Worker - Handles model retraining jobs"""
import sys
import os
# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import time
import uuid

from shared.config import Config
from shared.logger import setup_logger
from shared.database import DatabaseManager
from shared.redis_client import RedisClient
from ml.training.trainer import ModelTrainer
from registry.mlflow.mlflow_client import MLFlowClient

logger = setup_logger("retraining_worker")
config = Config()
db = DatabaseManager()
redis_client = RedisClient(config.redis.host, config.redis.port)
mlflow_client = MLFlowClient(config.mlflow.tracking_uri, config.mlflow.experiment_name)

class RetrainingWorker:
    """Worker that processes retraining jobs"""
    
    def __init__(self):
        self.running = False
        self.trainer = ModelTrainer(config.model)
        
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
            
            logger.info(f"✅ Retraining completed: {model_version}, "
                       f"Accuracy: {metrics['accuracy']:.4f}")
            
            # Notify prediction service to reload model
            redis_client.set('model_update', {
                'version': model_version,
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.error(f"Retraining failed: {str(e)}")
            db.log_training_job(job_id=job_id, status='failed')
            mlflow_client.end_run(status='FAILED')
            
    def get_training_data(self):
        """Get training data from feature store or buffer"""
        # In production, fetch from feature store
        # For now, get from Redis buffer
        data_buffer = []
        label_buffer = []
        
        # Get recent data
        for _ in range(config.drift.window_size):
            item = redis_client.rpop('data_queue')
            if item:
                data_buffer.extend(item['features'])
                if item.get('labels'):
                    label_buffer.extend(item['labels'])
            else:
                break
        
        if data_buffer and label_buffer:
            import numpy as np
            return np.array(data_buffer), np.array(label_buffer)
        
        return None
        
    def run(self):
        """Main worker loop"""
        self.running = True
        logger.info("Retraining worker started")
        
        while self.running:
            try:
                # Check for jobs
                job_data = redis_client.rpop('retraining_queue')
                
                if job_data:
                    self.process_job(job_data)
                else:
                    time.sleep(10)  # Wait for jobs
                    
            except Exception as e:
                logger.error(f"Worker error: {str(e)}")
                time.sleep(30)
                
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
