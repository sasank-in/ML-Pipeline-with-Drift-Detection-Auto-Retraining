"""MLFlow client for experiment tracking"""
import sys
import os
# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shared.logger import setup_logger

logger = setup_logger("mlflow_client")

class MLFlowClient:
    """MLFlow tracking client (mock for now)"""
    
    def __init__(self, tracking_uri: str, experiment_name: str):
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        self.current_run_id = None
        logger.info(f"MLFlow client initialized: {tracking_uri}")
        
    def start_run(self, run_name: str) -> str:
        """Start a new MLFlow run"""
        import uuid
        self.current_run_id = str(uuid.uuid4())
        logger.info(f"Started MLFlow run: {run_name} ({self.current_run_id})")
        return self.current_run_id
        
    def log_params(self, params: dict):
        """Log parameters"""
        logger.debug(f"Logging params: {params}")
        
    def log_metrics(self, metrics: dict):
        """Log metrics"""
        logger.info(f"Logging metrics: {metrics}")
        
    def log_model(self, model, artifact_path: str):
        """Log model artifact"""
        logger.info(f"Logging model: {artifact_path}")
        
    def end_run(self, status: str = 'FINISHED'):
        """End current run"""
        logger.info(f"Ended MLFlow run: {self.current_run_id} ({status})")
        self.current_run_id = None
