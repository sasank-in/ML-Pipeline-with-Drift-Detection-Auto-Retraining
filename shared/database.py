"""Database utilities for all services"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import json
from shared.logger import setup_logger

logger = setup_logger("database")

class DatabaseManager:
    """Centralized database management"""
    
    def __init__(self, db_path: str = "data/pipeline.db"):
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self):
        """Initialize all database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Predictions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                features TEXT NOT NULL,
                prediction INTEGER NOT NULL,
                probability REAL,
                true_label INTEGER,
                model_version TEXT,
                service_id TEXT
            )
        """)
        
        # Drift events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drift_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                drift_detected BOOLEAN NOT NULL,
                drift_score REAL,
                affected_features TEXT,
                drift_metrics TEXT,
                action_taken TEXT
            )
        """)
        
        # Training jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                job_id TEXT UNIQUE,
                status TEXT,
                accuracy REAL,
                f1_score REAL,
                precision_score REAL,
                recall_score REAL,
                training_time REAL,
                samples_count INTEGER,
                model_version TEXT,
                trigger_reason TEXT,
                mlflow_run_id TEXT
            )
        """)
        
        # Model registry table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                model_version TEXT UNIQUE,
                model_path TEXT,
                metrics TEXT,
                status TEXT,
                deployed BOOLEAN DEFAULT 0
            )
        """)
        
        # Feature store table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feature_store (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                feature_name TEXT,
                feature_value REAL,
                entity_id TEXT,
                feature_group TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
        
    def log_prediction(self, features: List[float], prediction: int, 
                      probability: float = None, true_label: Optional[int] = None, 
                      model_version: str = "v1", service_id: str = "prediction_service"):
        """Log a prediction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO predictions 
            (features, prediction, probability, true_label, model_version, service_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (json.dumps(features), prediction, probability, true_label, model_version, service_id))
        
        conn.commit()
        conn.close()
        
    def log_drift_event(self, drift_detected: bool, drift_score: float,
                       affected_features: List[str], drift_metrics: Dict, 
                       action_taken: str):
        """Log a drift detection event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO drift_events 
            (drift_detected, drift_score, affected_features, drift_metrics, action_taken)
            VALUES (?, ?, ?, ?, ?)
        """, (drift_detected, drift_score, json.dumps(affected_features), 
              json.dumps(drift_metrics), action_taken))
        
        conn.commit()
        conn.close()
        logger.info(f"Drift event logged: detected={drift_detected}, action={action_taken}")
        
    def log_training_job(self, job_id: str, status: str, metrics: Dict = None,
                        model_version: str = None, trigger_reason: str = None,
                        mlflow_run_id: str = None):
        """Log a training job"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if metrics:
            cursor.execute("""
                INSERT INTO training_jobs 
                (job_id, status, accuracy, f1_score, precision_score, recall_score,
                 training_time, samples_count, model_version, trigger_reason, mlflow_run_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (job_id, status, metrics.get('accuracy'), metrics.get('f1_score'),
                  metrics.get('precision'), metrics.get('recall'),
                  metrics.get('training_time'), metrics.get('samples_count'),
                  model_version, trigger_reason, mlflow_run_id))
        else:
            cursor.execute("""
                INSERT INTO training_jobs (job_id, status)
                VALUES (?, ?)
            """, (job_id, status))
        
        conn.commit()
        conn.close()
        logger.info(f"Training job logged: {job_id} - {status}")
        
    def register_model(self, model_version: str, model_path: str, 
                      metrics: Dict, status: str = "registered"):
        """Register a model in the registry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO model_registry (model_version, model_path, metrics, status)
            VALUES (?, ?, ?, ?)
        """, (model_version, model_path, json.dumps(metrics), status))
        
        conn.commit()
        conn.close()
        logger.info(f"Model registered: {model_version}")
        
    def get_active_model(self) -> Optional[Dict]:
        """Get the currently deployed model"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT model_version, model_path, metrics 
            FROM model_registry 
            WHERE deployed = 1 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'model_version': row[0],
                'model_path': row[1],
                'metrics': json.loads(row[2])
            }
        return None
