"""Database utilities for all services - PostgreSQL and SQLite support"""
import os
from datetime import datetime
from typing import List, Dict, Optional
import json

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from shared.logger import setup_logger

logger = setup_logger("database")

# Check if we should use PostgreSQL or SQLite
USE_POSTGRES = os.getenv('USE_POSTGRES', 'false').lower() == 'true'

if USE_POSTGRES:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        POSTGRES_AVAILABLE = True
        logger.info("PostgreSQL driver loaded successfully")
    except ImportError:
        logger.warning("psycopg2 not installed, falling back to SQLite")
        POSTGRES_AVAILABLE = False
        USE_POSTGRES = False
else:
    POSTGRES_AVAILABLE = False

if not USE_POSTGRES:
    import sqlite3

class DatabaseManager:
    """Centralized database management - supports both PostgreSQL and SQLite"""
    
    def __init__(self, db_path: str = "data/pipeline.db"):
        self.db_path = db_path
        self.use_postgres = USE_POSTGRES and POSTGRES_AVAILABLE
        
        # PostgreSQL connection parameters
        self.pg_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'ml_pipeline'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
        }
        
        if self.use_postgres:
            logger.info(f"Using PostgreSQL database: {self.pg_config['database']} at {self.pg_config['host']}")
        else:
            logger.info(f"Using SQLite database: {db_path}")
            
        self._init_database()
        
    def _get_connection(self):
        """Get database connection"""
        if self.use_postgres:
            return psycopg2.connect(**self.pg_config)
        else:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            return sqlite3.connect(self.db_path)
    
    def _init_database(self):
        """Initialize database tables"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            # PostgreSQL table creation
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    features JSONB,
                    prediction INTEGER,
                    probability REAL,
                    true_label INTEGER,
                    model_version TEXT,
                    service_id TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drift_events (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    drift_detected BOOLEAN,
                    drift_score REAL,
                    affected_features JSONB,
                    drift_metrics JSONB,
                    action_taken TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS training_jobs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_registry (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    model_version TEXT UNIQUE,
                    model_path TEXT,
                    metrics JSONB,
                    status TEXT,
                    deployed BOOLEAN DEFAULT FALSE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feature_store (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    feature_name TEXT,
                    feature_value REAL,
                    entity_id TEXT,
                    feature_group TEXT
                )
            """)
            
        else:
            # SQLite table creation
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    features TEXT,
                    prediction INTEGER,
                    probability REAL,
                    true_label INTEGER,
                    model_version TEXT,
                    service_id TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drift_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    drift_detected BOOLEAN,
                    drift_score REAL,
                    affected_features TEXT,
                    drift_metrics TEXT,
                    action_taken TEXT
                )
            """)
            
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
        
        db_type = "PostgreSQL" if self.use_postgres else "SQLite"
        logger.info(f"{db_type} database initialized successfully")
        
    def log_prediction(self, features: List[float], prediction: int, 
                      probability: float = None, true_label: Optional[int] = None, 
                      model_version: str = "v1", service_id: str = "prediction_service"):
        """Log a prediction"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("""
                INSERT INTO predictions 
                (features, prediction, probability, true_label, model_version, service_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (json.dumps(features), prediction, probability, true_label, model_version, service_id))
        else:
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
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("""
                INSERT INTO drift_events 
                (drift_detected, drift_score, affected_features, drift_metrics, action_taken)
                VALUES (%s, %s, %s, %s, %s)
            """, (drift_detected, drift_score, json.dumps(affected_features), 
                  json.dumps(drift_metrics), action_taken))
        else:
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
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            if metrics:
                cursor.execute("""
                    INSERT INTO training_jobs 
                    (job_id, status, accuracy, f1_score, precision_score, recall_score,
                     training_time, samples_count, model_version, trigger_reason, mlflow_run_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (job_id, status, metrics.get('accuracy'), metrics.get('f1_score'),
                      metrics.get('precision'), metrics.get('recall'),
                      metrics.get('training_time'), metrics.get('samples_count'),
                      model_version, trigger_reason, mlflow_run_id))
            else:
                cursor.execute("""
                    INSERT INTO training_jobs (job_id, status)
                    VALUES (%s, %s)
                """, (job_id, status))
        else:
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
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("""
                INSERT INTO model_registry (model_version, model_path, metrics, status)
                VALUES (%s, %s, %s, %s)
            """, (model_version, model_path, json.dumps(metrics), status))
        else:
            cursor.execute("""
                INSERT INTO model_registry (model_version, model_path, metrics, status)
                VALUES (?, ?, ?, ?)
            """, (model_version, model_path, json.dumps(metrics), status))
        
        conn.commit()
        conn.close()
        logger.info(f"Model registered: {model_version}")
        
    def get_active_model(self) -> Optional[Dict]:
        """Get the currently deployed model"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("""
                SELECT model_version, model_path, metrics 
                FROM model_registry 
                WHERE deployed = TRUE 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
        else:
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
            metrics_data = row[2] if self.use_postgres else json.loads(row[2])
            return {
                'model_version': row[0],
                'model_path': row[1],
                'metrics': metrics_data
            }
        return None
    
    def get_recent_predictions(self, limit: int = 100) -> List[Dict]:
        """Get recent predictions for drift monitoring"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("""
                SELECT features, prediction, timestamp 
                FROM predictions 
                ORDER BY timestamp DESC 
                LIMIT %s
            """, (limit,))
        else:
            cursor.execute("""
                SELECT features, prediction, timestamp 
                FROM predictions 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        predictions = []
        for row in rows:
            features_data = row[0] if self.use_postgres else json.loads(row[0])
            predictions.append({
                'features': features_data,
                'prediction': row[1],
                'timestamp': row[2]
            })
        
        return predictions
    
    def deploy_model(self, model_version: str):
        """Mark a model as deployed and undeploy others"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("UPDATE model_registry SET deployed = FALSE")
            cursor.execute("""
                UPDATE model_registry 
                SET deployed = TRUE 
                WHERE model_version = %s
            """, (model_version,))
        else:
            cursor.execute("UPDATE model_registry SET deployed = 0")
            cursor.execute("""
                UPDATE model_registry 
                SET deployed = 1 
                WHERE model_version = ?
            """, (model_version,))
        
        conn.commit()
        conn.close()
        logger.info(f"Model deployed: {model_version}")
