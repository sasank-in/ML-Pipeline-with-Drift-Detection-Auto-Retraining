"""
Inject synthetic samples to trigger drift detection.

Usage:
  python inject_drift.py --feature-dim 8 --baseline 200 --drift 200 --drift-amount 2.5
  python inject_drift.py --scenario retail --baseline 300 --drift 300 --drift-amount 1.5
"""
import argparse
import time
import numpy as np
import requests

PREDICTION_URL = "http://localhost:8002/predict"


def post_batch(features):
    response = requests.post(PREDICTION_URL, json={"features": features}, timeout=10)
    return response.status_code == 200


def generate_batch(n, dim, mean=0.0, std=1.0, clip=6.0):
    data = np.random.normal(mean, std, size=(n, dim))
    data = np.clip(data, -clip, clip)
    return data.tolist()


def generate_retail_batch(n, drift=False, drift_amount=1.5):
    """
    Generate retail-like features matching demo.py:
    [Recency, Frequency, TotalItems, UniqueProducts,
     AvgOrderValue, AvgItemsPerOrder, AvgItemPrice, CountryEncoded]
    """
    recency = np.random.exponential(scale=30, size=n)  # days since last purchase
    frequency = np.random.poisson(lam=5, size=n) + 1
    total_items = np.random.poisson(lam=20, size=n) + 1
    unique_products = np.clip(total_items * np.random.uniform(0.2, 0.7, size=n), 1, None)
    avg_order_value = np.random.normal(loc=80, scale=25, size=n)
    avg_items_per_order = np.clip(total_items / frequency + np.random.normal(0, 0.5, size=n), 1, None)
    avg_item_price = np.clip(avg_order_value / avg_items_per_order + np.random.normal(0, 2, size=n), 1, None)
    country_encoded = np.random.randint(0, 10, size=n)

    features = np.column_stack([
        recency, frequency, total_items, unique_products,
        avg_order_value, avg_items_per_order, avg_item_price, country_encoded
    ])

    if drift:
        # Shift behavior: higher recency, lower frequency, higher order value
        features[:, 0] = features[:, 0] + drift_amount * 20
        features[:, 1] = np.clip(features[:, 1] - drift_amount * 1.5, 1, None)
        features[:, 4] = features[:, 4] + drift_amount * 40
        features[:, 6] = features[:, 6] + drift_amount * 5

    # Standardize scale a bit to avoid extreme outliers
    features = np.clip(features, 0, 500)
    return features.tolist()


def main():
    parser = argparse.ArgumentParser(description="Inject samples to simulate drift.")
    parser.add_argument("--feature-dim", type=int, default=8, help="Number of features per sample")
    parser.add_argument("--scenario", type=str, default="generic", choices=["generic", "retail"],
                        help="Synthetic scenario to generate")
    parser.add_argument("--baseline", type=int, default=200, help="Baseline samples to send")
    parser.add_argument("--drift", type=int, default=200, help="Drifted samples to send")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size per request")
    parser.add_argument("--drift-amount", type=float, default=2.5, help="Mean shift for drifted data")
    parser.add_argument("--delay", type=float, default=0.25, help="Delay between batches (seconds)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    np.random.seed(args.seed)

    print("Sending baseline samples...")
    remaining = args.baseline
    while remaining > 0:
        batch = min(args.batch_size, remaining)
        if args.scenario == "retail":
            features = generate_retail_batch(batch, drift=False, drift_amount=args.drift_amount)
        else:
            features = generate_batch(batch, args.feature_dim, mean=0.0, std=1.0)
        ok = post_batch(features)
        print(f"  Baseline batch: {batch} -> {'ok' if ok else 'failed'}")
        remaining -= batch
        time.sleep(args.delay)

    print("Sending drifted samples...")
    remaining = args.drift
    while remaining > 0:
        batch = min(args.batch_size, remaining)
        if args.scenario == "retail":
            features = generate_retail_batch(batch, drift=True, drift_amount=args.drift_amount)
        else:
            features = generate_batch(batch, args.feature_dim, mean=args.drift_amount, std=1.0)
        ok = post_batch(features)
        print(f"  Drift batch: {batch} -> {'ok' if ok else 'failed'}")
        remaining -= batch
        time.sleep(args.delay)

    print("Done. Check drift monitor logs and dashboard.")


if __name__ == "__main__":
    main()
