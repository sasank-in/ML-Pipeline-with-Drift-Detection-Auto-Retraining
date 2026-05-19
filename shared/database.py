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
        from psycopg2 import pool as pg_pool
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

# Module-level Postgres pool (lazy-initialized per-process on first use).
_pg_pool = None

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
        
    def _ensure_pg_pool(self):
        """Lazily create a process-wide Postgres connection pool."""
        global _pg_pool
        if _pg_pool is None:
            minconn = int(os.getenv('PG_POOL_MIN', '1'))
            maxconn = int(os.getenv('PG_POOL_MAX', '10'))
            _pg_pool = pg_pool.SimpleConnectionPool(minconn, maxconn, **self.pg_config)
            logger.info(f"PostgreSQL pool initialized (min={minconn}, max={maxconn})")
        return _pg_pool

    def _get_connection(self):
        """Get database connection.

        For Postgres, leases a connection from a process-wide SimpleConnectionPool
        so the 5 services don't open/close TCP+auth on every call.
        For SQLite, enables WAL mode + 10 s busy timeout for concurrent-writer
        tolerance.
        """
        if self.use_postgres:
            return self._ensure_pg_pool().getconn()

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=10000")
        except sqlite3.Error as e:
            logger.warning(f"Could not set SQLite pragmas: {e}")
        return conn

    def _release(self, conn):
        """Return a connection to the pool (Postgres) or close it (SQLite)."""
        if self.use_postgres and _pg_pool is not None:
            try:
                _pg_pool.putconn(conn)
                return
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass
    
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

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS queues (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    queue_name TEXT,
                    payload JSONB
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

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS queues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    queue_name TEXT,
                    payload TEXT
                )
            """)
        
        conn.commit()
        self._release(conn)
        
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
        self._release(conn)
        
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
        self._release(conn)
        logger.info(f"Drift event logged: detected={drift_detected}, action={action_taken}")
        
    def log_training_job(self, job_id: str, status: str, metrics: Dict = None,
                        model_version: str = None, trigger_reason: str = None,
                        mlflow_run_id: str = None):
        """Log a training job. Upserts on job_id so the same job can be
        logged twice (e.g. status='started' then status='completed')."""
        m = metrics or {}
        params = (
            job_id, status,
            m.get('accuracy'), m.get('f1_score'),
            m.get('precision'), m.get('recall'),
            m.get('training_time'), m.get('samples_count'),
            model_version, trigger_reason, mlflow_run_id,
        )
        if self.use_postgres:
            sql = """
                INSERT INTO training_jobs
                (job_id, status, accuracy, f1_score, precision_score, recall_score,
                 training_time, samples_count, model_version, trigger_reason, mlflow_run_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    accuracy = COALESCE(EXCLUDED.accuracy, training_jobs.accuracy),
                    f1_score = COALESCE(EXCLUDED.f1_score, training_jobs.f1_score),
                    precision_score = COALESCE(EXCLUDED.precision_score, training_jobs.precision_score),
                    recall_score = COALESCE(EXCLUDED.recall_score, training_jobs.recall_score),
                    training_time = COALESCE(EXCLUDED.training_time, training_jobs.training_time),
                    samples_count = COALESCE(EXCLUDED.samples_count, training_jobs.samples_count),
                    model_version = COALESCE(EXCLUDED.model_version, training_jobs.model_version),
                    trigger_reason = COALESCE(EXCLUDED.trigger_reason, training_jobs.trigger_reason),
                    mlflow_run_id = COALESCE(EXCLUDED.mlflow_run_id, training_jobs.mlflow_run_id)
            """
        else:
            sql = """
                INSERT INTO training_jobs
                (job_id, status, accuracy, f1_score, precision_score, recall_score,
                 training_time, samples_count, model_version, trigger_reason, mlflow_run_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status = excluded.status,
                    accuracy = COALESCE(excluded.accuracy, training_jobs.accuracy),
                    f1_score = COALESCE(excluded.f1_score, training_jobs.f1_score),
                    precision_score = COALESCE(excluded.precision_score, training_jobs.precision_score),
                    recall_score = COALESCE(excluded.recall_score, training_jobs.recall_score),
                    training_time = COALESCE(excluded.training_time, training_jobs.training_time),
                    samples_count = COALESCE(excluded.samples_count, training_jobs.samples_count),
                    model_version = COALESCE(excluded.model_version, training_jobs.model_version),
                    trigger_reason = COALESCE(excluded.trigger_reason, training_jobs.trigger_reason),
                    mlflow_run_id = COALESCE(excluded.mlflow_run_id, training_jobs.mlflow_run_id)
            """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)
            conn.commit()
        finally:
            self._release(conn)
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
        self._release(conn)
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
        self._release(conn)
        
        if row:
            metrics_data = row[2] if self.use_postgres else json.loads(row[2])
            return {
                'model_version': row[0],
                'model_path': row[1],
                'metrics': metrics_data
            }
        return None
    
    def _ph(self) -> str:
        """Return the SQL placeholder for the active backend ('%s' or '?')."""
        return '%s' if self.use_postgres else '?'

    def _exec(self, sql: str, params: tuple = (), fetch: str = None):
        """Run a query against the active backend.

        sql: use '?' as the placeholder; it's translated to '%s' for Postgres.
        fetch: None (write), 'one' (return single row), 'all' (return rows), 'count' (scalar int).
        """
        if self.use_postgres:
            sql = sql.replace('?', '%s')
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)
            if fetch == 'one':
                result = cursor.fetchone()
            elif fetch == 'all':
                result = cursor.fetchall()
            elif fetch == 'count':
                row = cursor.fetchone()
                result = int(row[0]) if row else 0
            else:
                result = None
            conn.commit()
            return result
        finally:
            self._release(conn)

    def ping(self) -> bool:
        """Cheap connectivity check for /health endpoints."""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            self._release(conn)
            return True
        except Exception as e:
            logger.warning(f"DB ping failed: {e}")
            return False

    def get_recent_drift_events(self, limit: int = 50) -> List[Dict]:
        """Most recent drift events (ordered newest-first)."""
        rows = self._exec(
            """
            SELECT timestamp, drift_detected, drift_score, affected_features,
                   drift_metrics, action_taken
            FROM drift_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
            fetch='all',
        ) or []
        out = []
        for r in rows:
            affected = r[3]
            metrics = r[4]
            if isinstance(affected, str):
                affected = json.loads(affected)
            if isinstance(metrics, str):
                metrics = json.loads(metrics)
            out.append({
                'timestamp': r[0],
                'drift_detected': bool(r[1]),
                'drift_score': float(r[2]) if r[2] is not None else None,
                'affected_features': affected or [],
                'drift_metrics': metrics or {},
                'action_taken': r[5],
            })
        return out

    def get_training_history(self, limit: int = 50) -> List[Dict]:
        """Most recent training jobs (newest first)."""
        rows = self._exec(
            """
            SELECT timestamp, status, accuracy, f1_score, precision_score, recall_score,
                   training_time, samples_count, model_version, trigger_reason
            FROM training_jobs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
            fetch='all',
        ) or []
        return [
            {
                'timestamp': r[0], 'status': r[1],
                'accuracy': float(r[2]) if r[2] is not None else None,
                'f1_score': float(r[3]) if r[3] is not None else None,
                'precision': float(r[4]) if r[4] is not None else None,
                'recall': float(r[5]) if r[5] is not None else None,
                'training_time': float(r[6]) if r[6] is not None else None,
                'samples_count': int(r[7]) if r[7] is not None else None,
                'model_version': r[8], 'trigger_reason': r[9],
            }
            for r in rows
        ]

    def get_queue_depths(self) -> Dict[str, int]:
        """Snapshot of all known queue depths in one query."""
        rows = self._exec(
            "SELECT queue_name, COUNT(*) FROM queues GROUP BY queue_name",
            fetch='all',
        ) or []
        return {r[0]: int(r[1]) for r in rows}

    def count_drift_detected(self) -> int:
        true_lit = 'TRUE' if self.use_postgres else '1'
        return self._exec(
            f"SELECT COUNT(*) FROM drift_events WHERE drift_detected = {true_lit}",
            fetch='count',
        )

    def count_models(self) -> int:
        return self._exec("SELECT COUNT(*) FROM model_registry", fetch='count')

    def get_predictions_over_time(self, bucket_minutes: int = 5, limit: int = 60) -> List[Dict]:
        """Time-bucketed prediction counts for trend chart."""
        if self.use_postgres:
            sql = """
                SELECT date_trunc('minute', timestamp) AS bucket, COUNT(*)
                FROM predictions
                GROUP BY bucket
                ORDER BY bucket DESC
                LIMIT %s
            """
            params = (limit,)
        else:
            # SQLite: floor to bucket_minutes
            sql = """
                SELECT strftime('%Y-%m-%d %H:%M', timestamp) AS bucket, COUNT(*)
                FROM predictions
                GROUP BY bucket
                ORDER BY bucket DESC
                LIMIT ?
            """
            params = (limit,)
        rows = self._exec(sql, params, fetch='all') or []
        return [{'bucket': r[0], 'count': int(r[1])} for r in reversed(rows)]

    def count_predictions(self) -> int:
        """Total number of predictions ever logged (cross-process accurate)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM predictions")
        count = cursor.fetchone()[0]
        self._release(conn)
        return int(count)

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
        self._release(conn)
        
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
        """Atomically mark a single model as deployed; undeploy all others.

        Uses a single transaction so there is no window where no model is deployed.
        """
        true_lit = 'TRUE' if self.use_postgres else '1'
        false_lit = 'FALSE' if self.use_postgres else '0'
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            ph = self._ph()
            cursor.execute(f"UPDATE model_registry SET deployed = {false_lit}")
            cursor.execute(
                f"UPDATE model_registry SET deployed = {true_lit} WHERE model_version = {ph}",
                (model_version,),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._release(conn)
        logger.info(f"Model deployed: {model_version}")

    def enqueue(self, queue_name: str, payload: Dict):
        """Enqueue a payload for a named queue (cross-process safe via DB)."""
        self._exec(
            "INSERT INTO queues (queue_name, payload) VALUES (?, ?)",
            (queue_name, json.dumps(payload)),
        )

    def dequeue(self, queue_name: str) -> Optional[Dict]:
        """Dequeue the oldest payload for a named queue."""
        row = self._exec(
            "SELECT id, payload FROM queues WHERE queue_name = ? ORDER BY id ASC LIMIT 1",
            (queue_name,),
            fetch='one',
        )
        if not row:
            return None
        queue_id, payload = row[0], row[1]
        self._exec("DELETE FROM queues WHERE id = ?", (queue_id,))
        if isinstance(payload, str):
            return json.loads(payload)
        return payload

    def peek_queue(self, queue_name: str, limit: int = 100) -> List[Dict]:
        """Read up to `limit` oldest payloads for a queue WITHOUT removing them."""
        rows = self._exec(
            "SELECT payload FROM queues WHERE queue_name = ? ORDER BY id ASC LIMIT ?",
            (queue_name, limit),
            fetch='all',
        ) or []
        results = []
        for row in rows:
            payload = row[0]
            if isinstance(payload, str):
                payload = json.loads(payload)
            results.append(payload)
        return results

    def trim_queue(self, queue_name: str, keep_last: int = 1000):
        """Delete all but the most recent `keep_last` items in a queue."""
        self._exec(
            """
            DELETE FROM queues
            WHERE queue_name = ?
              AND id NOT IN (
                  SELECT id FROM queues
                  WHERE queue_name = ?
                  ORDER BY id DESC
                  LIMIT ?
              )
            """,
            (queue_name, queue_name, keep_last),
        )

    def get_queue_length(self, queue_name: str) -> int:
        """Get current length of a named queue."""
        return self._exec(
            "SELECT COUNT(*) FROM queues WHERE queue_name = ?",
            (queue_name,),
            fetch='count',
        )
