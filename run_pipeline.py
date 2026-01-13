"""
Universal ML Pipeline Runner
============================
Works with ANY dataset - just specify your CSV file and target column.

Usage:
    python run_pipeline.py --data your_data.csv --target target_column
    python run_pipeline.py --data data/lung_disease.csv --target Recovered
    python run_pipeline.py --data sales.csv --target revenue --test-size 0.25
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import argparse
import pandas as pd
import numpy as np
import requests
import time
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

# API endpoints
BASE_URL_INGESTION = "http://localhost:8001"
BASE_URL_PREDICTION = "http://localhost:8002"


def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def check_services():
    """Check if services are running"""
    print_section("CHECKING SERVICES")
    
    services = [
        ("Ingestion API", f"{BASE_URL_INGESTION}/health"),
        ("Prediction Service", f"{BASE_URL_PREDICTION}/health"),
    ]
    
    all_running = True
    for name, url in services:
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                print(f"✓ {name}: Running")
            else:
                print(f"✗ {name}: Not responding")
                all_running = False
        except:
            print(f"✗ {name}: Not available")
            all_running = False
    
    if not all_running:
        print("\n⚠ Services not running!")
        print("Start them first: run_all_services.bat")
        return False
    return True


def load_and_preprocess(csv_path: str, target_column: str):
    """Load any CSV and preprocess it automatically"""
    print_section("LOADING DATASET")
    
    # Load CSV
    print(f"Loading: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"Shape: {df.shape[0]} rows, {df.shape[1]} columns")
    
    # Check if target column exists
    if target_column not in df.columns:
        print(f"\n✗ Error: Target column '{target_column}' not found!")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)
    
    print(f"Target column: {target_column}")
    
    # Show data info
    print(f"\nFeature columns ({len(df.columns) - 1}):")
    for col in df.columns:
        if col != target_column:
            dtype = "numeric" if df[col].dtype in ['int64', 'float64'] else "categorical"
            nulls = df[col].isnull().sum()
            print(f"  - {col} ({dtype}, {nulls} nulls)")
    
    # Preprocess
    print_section("PREPROCESSING")
    df_processed = df.copy()
    
    # Remove duplicates
    before = len(df_processed)
    df_processed.drop_duplicates(inplace=True)
    after = len(df_processed)
    if before != after:
        print(f"✓ Removed {before - after} duplicate rows")
    
    # Handle missing values
    numeric_cols = df_processed.select_dtypes(include=['int64', 'float64']).columns
    categorical_cols = df_processed.select_dtypes(include=['object', 'category', 'bool']).columns
    
    for col in numeric_cols:
        if df_processed[col].isnull().sum() > 0:
            df_processed[col] = df_processed[col].fillna(df_processed[col].median())
            print(f"✓ Filled missing values in '{col}' with median")
    
    for col in categorical_cols:
        if df_processed[col].isnull().sum() > 0:
            df_processed[col] = df_processed[col].fillna(df_processed[col].mode()[0])
            print(f"✓ Filled missing values in '{col}' with mode")
    
    # Encode categorical columns
    encoders = {}
    for col in categorical_cols:
        le = LabelEncoder()
        df_processed[col] = le.fit_transform(df_processed[col].astype(str))
        encoders[col] = le
        print(f"✓ Encoded '{col}' ({len(le.classes_)} categories)")
    
    # Separate features and target
    X = df_processed.drop(target_column, axis=1).values
    y = df_processed[target_column].values
    
    # Scale numeric features
    scaler = StandardScaler()
    X = scaler.fit_transform(X)
    print(f"✓ Scaled features")
    
    feature_names = [c for c in df_processed.columns if c != target_column]
    
    # Target distribution
    unique, counts = np.unique(y, return_counts=True)
    print(f"\nTarget distribution:")
    for u, c in zip(unique, counts):
        print(f"  Class {u}: {c} samples ({c/len(y)*100:.1f}%)")
    
    return X, y, feature_names


def ingest_data(X_train, y_train, batch_size=20):
    """Ingest training data to the pipeline"""
    print_section("INGESTING TRAINING DATA")
    
    print(f"Training samples: {len(X_train)}")
    print(f"Features per sample: {X_train.shape[1]}")
    
    total_batches = (len(X_train) + batch_size - 1) // batch_size
    success_count = 0
    
    for i in range(0, len(X_train), batch_size):
        batch_X = X_train[i:i+batch_size]
        batch_y = y_train[i:i+batch_size]
        
        try:
            response = requests.post(
                f"{BASE_URL_INGESTION}/ingest/batch",
                json={
                    'features': batch_X.tolist(),
                    'labels': batch_y.tolist(),
                    'batch_id': f'batch_{i//batch_size}'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                success_count += 1
                print(f"✓ Batch {i//batch_size + 1}/{total_batches}: {len(batch_X)} samples")
            else:
                print(f"✗ Batch {i//batch_size + 1}: Failed")
                
        except Exception as e:
            print(f"✗ Batch {i//batch_size + 1}: Error - {str(e)}")
    
    print(f"\n✓ Ingested {success_count}/{total_batches} batches successfully")
    
    print("\n⏳ Waiting for model training (5 seconds)...")
    time.sleep(5)


def make_predictions(X_test, y_test, batch_size=10):
    """Make predictions on test data"""
    print_section("MAKING PREDICTIONS")
    
    print(f"Test samples: {len(X_test)}")
    
    all_predictions = []
    total_batches = (len(X_test) + batch_size - 1) // batch_size
    
    for i in range(0, len(X_test), batch_size):
        batch_X = X_test[i:i+batch_size]
        
        try:
            response = requests.post(
                f"{BASE_URL_PREDICTION}/predict",
                json={'features': batch_X.tolist()},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                predictions = result['predictions']
                all_predictions.extend(predictions)
                print(f"✓ Batch {i//batch_size + 1}/{total_batches}: {len(predictions)} predictions")
            else:
                print(f"✗ Batch {i//batch_size + 1}: Failed")
                
        except Exception as e:
            print(f"✗ Batch {i//batch_size + 1}: Error - {str(e)}")
        
        time.sleep(0.3)
    
    # Calculate metrics
    if len(all_predictions) == len(y_test):
        accuracy = np.mean(np.array(all_predictions) == y_test)
        print(f"\n✓ Accuracy: {accuracy:.2%}")
        
        # Per-class accuracy
        unique_classes = np.unique(y_test)
        if len(unique_classes) <= 10:
            print("\nPer-class accuracy:")
            for cls in unique_classes:
                mask = y_test == cls
                cls_acc = np.mean(np.array(all_predictions)[mask] == y_test[mask])
                print(f"  Class {cls}: {cls_acc:.2%}")
    
    return all_predictions


def introduce_drift(X_test, drift_amount=2.0):
    """Introduce drift to test drift detection"""
    print_section("INTRODUCING DATA DRIFT")
    
    print(f"Drift amount: {drift_amount}")
    print("Sending drifted data to trigger drift detection...")
    
    X_drifted = X_test.copy()
    X_drifted = X_drifted + np.random.normal(drift_amount, 0.5, X_drifted.shape)
    X_drifted = np.clip(X_drifted, -10, 10)
    
    batch_size = 10
    for i in range(0, min(len(X_drifted), 50), batch_size):
        batch_X = X_drifted[i:i+batch_size]
        
        try:
            requests.post(
                f"{BASE_URL_PREDICTION}/predict",
                json={'features': batch_X.tolist()},
                timeout=10
            )
            print(f"✓ Sent drifted batch {i//batch_size + 1}")
        except:
            pass
        
        time.sleep(0.3)
    
    print("\n⏳ Waiting for drift detection (10 seconds)...")
    time.sleep(10)


def show_stats():
    """Show pipeline statistics"""
    print_section("PIPELINE STATISTICS")
    
    try:
        response = requests.get(f"{BASE_URL_INGESTION}/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            for key, value in stats.items():
                print(f"  {key}: {value}")
    except:
        print("  Could not retrieve stats")


def main():
    parser = argparse.ArgumentParser(
        description="Universal ML Pipeline Runner - Works with any dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py --data data/lung_disease.csv --target Recovered
  python run_pipeline.py --data sales.csv --target revenue
  python run_pipeline.py --data customers.csv --target churn --test-size 0.3
  python run_pipeline.py --data iris.csv --target species --no-drift
        """
    )
    
    parser.add_argument('--data', '-d', required=True,
                        help='Path to CSV file')
    parser.add_argument('--target', '-t', required=True,
                        help='Name of target column to predict')
    parser.add_argument('--test-size', type=float, default=0.3,
                        help='Test set size (default: 0.3)')
    parser.add_argument('--batch-size', type=int, default=20,
                        help='Batch size for ingestion (default: 20)')
    parser.add_argument('--no-drift', action='store_true',
                        help='Skip drift detection demo')
    parser.add_argument('--drift-amount', type=float, default=2.0,
                        help='Amount of drift to introduce (default: 2.0)')
    
    args = parser.parse_args()
    
    # Header
    print("=" * 70)
    print("  UNIVERSAL ML PIPELINE")
    print("=" * 70)
    print(f"\n  Dataset: {args.data}")
    print(f"  Target:  {args.target}")
    print(f"  Test Size: {args.test_size}")
    
    # Check services
    if not check_services():
        return
    
    # Load and preprocess data
    X, y, feature_names = load_and_preprocess(args.data, args.target)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=42
    )
    
    print_section("DATA SPLIT")
    print(f"Training: {len(X_train)} samples")
    print(f"Testing:  {len(X_test)} samples")
    
    try:
        # Ingest training data
        ingest_data(X_train, y_train, args.batch_size)
        
        # Make predictions
        predictions = make_predictions(X_test, y_test)
        
        # Drift detection (optional)
        if not args.no_drift:
            introduce_drift(X_test, args.drift_amount)
        
        # Show stats
        show_stats()
        
        # Summary
        print_section("COMPLETE")
        print("\n✓ Pipeline demonstration finished!")
        print("\n  Dashboard: http://localhost:8050")
        print("  Logs: logs/")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
