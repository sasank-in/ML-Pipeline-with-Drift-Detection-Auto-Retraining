"""ML Pipeline Demo - Retail Customer Value Prediction"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder

from ml.training.trainer import ModelTrainer
from ml.evaluation.drift_detector import DriftDetector
from shared.database import DatabaseManager


def load_retail_data():
    """Load and prepare retail dataset for customer classification"""
    df = pd.read_csv('data/retail_data.csv')
    print(f"Loaded: {df.shape[0]:,} transactions")
    
    df = df.dropna(subset=['Customer ID'])
    df = df[(df['Quantity'] > 0) & (df['Price'] > 0)]
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['TotalAmount'] = df['Quantity'] * df['Price']
    
    reference_date = df['InvoiceDate'].max() + pd.Timedelta(days=1)
    
    customer_df = df.groupby('Customer ID').agg({
        'InvoiceDate': lambda x: (reference_date - x.max()).days,
        'Invoice': 'nunique',
        'TotalAmount': 'sum',
        'Quantity': 'sum',
        'StockCode': 'nunique',
        'Country': 'first'
    }).reset_index()
    
    customer_df.columns = ['CustomerID', 'Recency', 'Frequency', 'Monetary', 
                           'TotalItems', 'UniqueProducts', 'Country']
    
    customer_df['AvgOrderValue'] = customer_df['Monetary'] / customer_df['Frequency']
    customer_df['AvgItemsPerOrder'] = customer_df['TotalItems'] / customer_df['Frequency']
    customer_df['AvgItemPrice'] = customer_df['Monetary'] / customer_df['TotalItems']
    
    monetary_threshold = customer_df['Monetary'].quantile(0.75)
    customer_df['HighValue'] = (customer_df['Monetary'] >= monetary_threshold).astype(int)
    
    le = LabelEncoder()
    customer_df['CountryEncoded'] = le.fit_transform(customer_df['Country'])
    
    feature_cols = ['Recency', 'Frequency', 'TotalItems', 'UniqueProducts',
                   'AvgOrderValue', 'AvgItemsPerOrder', 'AvgItemPrice', 'CountryEncoded']
    
    X = customer_df[feature_cols].values
    y = customer_df['HighValue'].values
    
    scaler = StandardScaler()
    X = scaler.fit_transform(X)
    
    print(f"Customers: {len(X)}, Features: {len(feature_cols)}")
    print(f"High-value: {y.sum()} ({y.mean()*100:.1f}%)")
    
    return X, y, feature_cols


def run_pipeline():
    """Run the complete ML pipeline"""
    print("=" * 60)
    print("RETAIL CUSTOMER VALUE PREDICTION")
    print("=" * 60)
    
    X, y, features = load_retail_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    print(f"\nTrain: {len(X_train)}, Test: {len(X_test)}")
    
    print("\n[1] Training model...")
    trainer = ModelTrainer(model_path="models/retail_model.pkl")
    metrics, version = trainer.train(X_train, y_train)
    trainer.save_model()
    print(f"Accuracy: {metrics['accuracy']:.4f}, F1: {metrics['f1_score']:.4f}")
    
    print("\n[2] Making predictions...")
    predictions = trainer.model.predict(X_test)
    test_accuracy = np.mean(predictions == y_test)
    print(f"Test accuracy: {test_accuracy:.4f}")
    
    print("\n[3] Setting up drift detection...")
    detector = DriftDetector(threshold=0.05)
    detector.set_reference(X_train)
    
    print("\n[4] Checking for drift (normal data)...")
    drift_detected, drift_metrics = detector.detect_drift(X_test)
    print(f"Drift detected: {drift_detected}")
    
    print("\n[5] Simulating drift...")
    X_drifted = X_test + np.random.normal(2.0, 0.5, X_test.shape)
    drift_detected, drift_metrics = detector.detect_drift(X_drifted)
    print(f"Drift detected: {drift_detected}")
    
    if drift_detected:
        print("\n[6] Retraining on combined data...")
        X_combined = np.vstack([X_train, X_drifted])
        y_combined = np.hstack([y_train, y_test])
        metrics, version = trainer.train(X_combined, y_combined)
        trainer.save_model()
        print(f"New accuracy: {metrics['accuracy']:.4f}")
    
    print("\n[7] Logging to database...")
    db = DatabaseManager()
    db.register_model(
        model_version=version,
        model_path="models/retail_model.pkl",
        metrics=metrics,
        status='active'
    )
    print("Model registered")
    
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_pipeline()
