"""Shared configuration across all services"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    database: str = os.getenv("DB_NAME", "ml_pipeline")
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "postgres")
    
@dataclass
class MLFlowConfig:
    """MLFlow tracking configuration"""
    tracking_uri: str = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    experiment_name: str = os.getenv("MLFLOW_EXPERIMENT", "drift_detection_pipeline")
    
@dataclass
class ModelConfig:
    """Model training configuration"""
    n_estimators: int = 100
    max_depth: int = 10
    min_samples_split: int = 2
    random_state: int = 42
    
@dataclass
class DriftConfig:
    """Drift detection configuration (all env-overridable)."""
    threshold: float = float(os.getenv("DRIFT_THRESHOLD", "0.05"))
    window_size: int = int(os.getenv("DRIFT_WINDOW_SIZE", "1000"))
    min_samples: int = int(os.getenv("DRIFT_MIN_SAMPLES", "100"))
    check_interval: int = int(os.getenv("DRIFT_CHECK_INTERVAL", "300"))  # seconds
    
@dataclass
class ServiceConfig:
    """Service-specific configuration"""
    ingestion_port: int = 8001
    prediction_port: int = 8002
    drift_monitor_port: int = 8003
    retraining_port: int = 8004
    dashboard_port: int = 8050
    
class Config:
    """Main configuration class"""
    def __init__(self):
        self.database = DatabaseConfig()
        self.mlflow = MLFlowConfig()
        self.model = ModelConfig()
        self.drift = DriftConfig()
        self.service = ServiceConfig()
