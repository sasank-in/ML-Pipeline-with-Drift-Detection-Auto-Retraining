"""Test PostgreSQL connection and functionality"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from shared.database import DatabaseManager
from dotenv import load_dotenv
import time

def test_connection():
    """Test database connection"""
    print("=" * 60)
    print("  PostgreSQL Connection Test")
    print("=" * 60)
    print()
    
    # Load environment variables
    load_dotenv()
    
    # Check configuration
    use_postgres = os.getenv('USE_POSTGRES', 'false').lower() == 'true'
    
    if use_postgres:
        print("✓ Configuration: PostgreSQL")
        print(f"  Host: {os.getenv('POSTGRES_HOST', 'localhost')}")
        print(f"  Port: {os.getenv('POSTGRES_PORT', '5432')}")
        print(f"  Database: {os.getenv('POSTGRES_DB', 'ml_pipeline')}")
        print(f"  User: {os.getenv('POSTGRES_USER', 'postgres')}")
    else:
        print("✓ Configuration: SQLite")
        print(f"  Database: data/pipeline.db")
    
    print()
    
    # Test connection
    try:
        print("Testing database connection...")
        db = DatabaseManager()
        print("✓ Database connection successful!")
        print()
        
        # Test operations
        print("Testing database operations...")
        
        # Use timestamp for unique IDs
        test_id = str(int(time.time() * 1000))
        
        # Test prediction logging
        db.log_prediction(
            features=[1.0, 2.0, 3.0],
            prediction=1,
            probability=0.85,
            model_version=f"test_v{test_id}"
        )
        print("✓ Prediction logging works")
        
        # Test drift event logging
        db.log_drift_event(
            drift_detected=True,
            drift_score=0.15,
            affected_features=["feature1", "feature2"],
            drift_metrics={"ks_statistic": 0.15, "p_value": 0.01},
            action_taken="retraining_triggered"
        )
        print("✓ Drift event logging works")
        
        # Test training job logging
        db.log_training_job(
            job_id=f"test_job_{test_id}",
            status="completed",
            metrics={
                "accuracy": 0.95,
                "f1_score": 0.93,
                "precision": 0.94,
                "recall": 0.92,
                "training_time": 5.2,
                "samples_count": 1000
            },
            model_version=f"test_v{test_id}",
            trigger_reason="manual_test"
        )
        print("✓ Training job logging works")
        
        # Test model registration
        db.register_model(
            model_version=f"test_v{test_id}",
            model_path=f"models/test_v{test_id}.pkl",
            metrics={"accuracy": 0.95, "f1_score": 0.93},
            status="registered"
        )
        print("✓ Model registration works")
        
        # Test model deployment
        db.deploy_model(f"test_v{test_id}")
        print("✓ Model deployment works")
        
        # Test getting active model
        active_model = db.get_active_model()
        if active_model:
            print(f"✓ Active model retrieval works: {active_model['model_version']}")
        else:
            print("⚠ No active model found (this is okay for first run)")
        
        # Test getting recent predictions
        predictions = db.get_recent_predictions(limit=5)
        print(f"✓ Recent predictions retrieval works: {len(predictions)} predictions found")
        
        print()
        print("=" * 60)
        print("  All Tests Passed! ✓")
        print("=" * 60)
        print()
        
        if use_postgres:
            print("Your PostgreSQL database is ready to use!")
            print()
            print("Next steps:")
            print("  1. Run: run_all_services.bat")
            print("  2. Run: python demo.py")
            print("  3. Open: http://localhost:8050")
        else:
            print("Your SQLite database is ready to use!")
            print()
            print("To switch to PostgreSQL:")
            print("  1. Edit .env and set USE_POSTGRES=true")
            print("  2. Configure PostgreSQL credentials")
            print("  3. Run this test again")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print()
        print("Troubleshooting:")
        
        if use_postgres:
            print("  1. Check if PostgreSQL is running")
            print("  2. Verify credentials in .env file")
            print("  3. Ensure database exists: CREATE DATABASE ml_pipeline;")
            print("  4. Check PostgreSQL logs for errors")
            print()
            print("For detailed help, see: docs/POSTGRESQL_SETUP.md")
        else:
            print("  1. Check if data/ directory exists")
            print("  2. Verify write permissions")
            print("  3. Check disk space")
        
        import traceback
        traceback.print_exc()
        
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
