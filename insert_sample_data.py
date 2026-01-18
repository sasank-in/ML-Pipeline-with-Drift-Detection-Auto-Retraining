"""Insert sample predictions for dashboard observation"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import numpy as np
from shared.database import DatabaseManager

print("Inserting sample predictions into database...")
print("=" * 60)

db = DatabaseManager()

# Sample predictions with realistic data
samples = [
    # High-value customers
    (1, 0.89, "High-value customer"),
    (1, 0.92, "High-value customer"),
    (1, 0.85, "High-value customer"),
    (1, 0.91, "High-value customer"),
    (1, 0.88, "High-value customer"),
    (1, 0.94, "High-value customer"),
    (1, 0.87, "High-value customer"),
    
    # Regular customers
    (0, 0.78, "Regular customer"),
    (0, 0.82, "Regular customer"),
    (0, 0.75, "Regular customer"),
    (0, 0.80, "Regular customer"),
    (0, 0.76, "Regular customer"),
    (0, 0.83, "Regular customer"),
    (0, 0.79, "Regular customer"),
    (0, 0.81, "Regular customer"),
]

for i, (prediction, probability, desc) in enumerate(samples, 1):
    features = list(np.random.randn(8))
    
    db.log_prediction(
        features=features,
        prediction=prediction,
        probability=probability,
        model_version="retail_model"
    )
    
    pred_label = "High-Value" if prediction == 1 else "Regular"
    print(f"{i:2d}. {desc}: {pred_label} ({probability:.1%} confidence)")

print("\n" + "=" * 60)
print(f"Successfully inserted {len(samples)} sample predictions!")
print("\nRefresh the dashboard at http://localhost:8050 to see the data")
print("\nServices running:")
print("  - Ingestion API:      http://localhost:8001")
print("  - Prediction Service: http://localhost:8002")
print("  - Dashboard:          http://localhost:8050")
