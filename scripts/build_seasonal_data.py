"""Slice UCI Online Retail dataset into quarterly seasons and emit JSON batches
ready to POST to the ingestion API.

Output:
  data/seasonal/Q1.json … Q4.json — each contains {"features": [[...8 numeric...]],
  "labels": [0/1], "batch_id": "qN_<period>"} ready for /ingest/batch.

Time periods (UTC): Online Retail spans 2010-12-01 to 2011-12-09. We split into:
  Q1 = 2010-12-01 -> 2011-02-28   (winter / post-holiday)
  Q2 = 2011-03-01 -> 2011-05-31   (spring)
  Q3 = 2011-06-01 -> 2011-08-31   (summer)
  Q4 = 2011-09-01 -> 2011-12-09   (autumn / holiday surge)

The label `HighValue` is derived per-season using that season's 75th-pctile of
Monetary, so each season has a meaningful positive class. The 8 features match
the schema the prediction service advertises.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "seasonal"
SRC = OUT_DIR / "online_retail.xlsx"

QUARTERS = [
    ("Q1", "2010-12-01", "2011-02-28"),
    ("Q2", "2011-03-01", "2011-05-31"),
    ("Q3", "2011-06-01", "2011-08-31"),
    ("Q4", "2011-09-01", "2011-12-09"),
]

FEATURE_COLS = [
    "Recency", "Frequency", "TotalItems", "UniqueProducts",
    "AvgOrderValue", "AvgItemsPerOrder", "AvgItemPrice", "CountryEncoded",
]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map both the original UCI columns and the newer cleaned-CSV columns to
    a single canonical set."""
    rename = {
        "InvoiceNo": "Invoice",
        "UnitPrice": "Price",
        "CustomerID": "Customer ID",
    }
    return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})


def load_raw() -> pd.DataFrame:
    if not SRC.exists():
        sys.exit(f"Missing {SRC}. Run the download step first.")
    print(f"Reading {SRC} ...")
    df = pd.read_excel(SRC, engine="openpyxl")
    df = _normalize_columns(df)
    df = df.dropna(subset=["Customer ID"])
    df = df[(df["Quantity"] > 0) & (df["Price"] > 0)]
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["TotalAmount"] = df["Quantity"] * df["Price"]
    print(f"  {len(df):,} clean rows across {df['Customer ID'].nunique():,} customers")
    return df


def aggregate_customers(df: pd.DataFrame, period_end: pd.Timestamp) -> pd.DataFrame:
    """Aggregate transactions into one row per customer using the standard
    RFM-style features the prediction service expects."""
    ref = period_end + pd.Timedelta(days=1)
    agg = df.groupby("Customer ID").agg(
        Recency=("InvoiceDate", lambda x: (ref - x.max()).days),
        Frequency=("Invoice", "nunique"),
        Monetary=("TotalAmount", "sum"),
        TotalItems=("Quantity", "sum"),
        UniqueProducts=("StockCode", "nunique"),
        Country=("Country", "first"),
    ).reset_index()
    agg["AvgOrderValue"] = agg["Monetary"] / agg["Frequency"]
    agg["AvgItemsPerOrder"] = agg["TotalItems"] / agg["Frequency"]
    agg["AvgItemPrice"] = agg["Monetary"] / agg["TotalItems"]
    return agg


def build_quarter(df_all: pd.DataFrame, country_encoder: LabelEncoder,
                  scaler: StandardScaler | None, name: str,
                  start: str, end: str) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    df = df_all[(df_all["InvoiceDate"] >= start_ts) & (df_all["InvoiceDate"] <= end_ts)].copy()
    if df.empty:
        sys.exit(f"No rows for {name}")

    cust = aggregate_customers(df, end_ts)

    # Encode Country using a stable encoder fit on the full dataset.
    cust["CountryEncoded"] = country_encoder.transform(cust["Country"])

    # HighValue label = top quartile of Monetary FOR THIS SEASON.
    threshold = cust["Monetary"].quantile(0.75)
    cust["HighValue"] = (cust["Monetary"] >= threshold).astype(int)

    X_raw = cust[FEATURE_COLS].astype(float).values
    y = cust["HighValue"].values

    # Fit scaler on Q1 only; reuse for later quarters so distribution shifts
    # show up as real drift instead of being normalised away.
    if scaler is None:
        scaler = StandardScaler().fit(X_raw)
        print(f"  [{name}] fit scaler on this quarter (baseline)")
    X = scaler.transform(X_raw)

    print(
        f"  [{name}] {start} -> {end}: "
        f"{len(cust):,} customers, "
        f"{int(y.sum())} high-value ({y.mean()*100:.1f}%), "
        f"monetary 75th-pctile = {threshold:,.2f}"
    )
    return cust, X, y, scaler


def write_batch(name: str, X: np.ndarray, y: np.ndarray):
    payload = {
        "features": X.round(6).tolist(),
        "labels": y.tolist(),
        "batch_id": f"{name.lower()}_seasonal",
    }
    out = OUT_DIR / f"{name}.json"
    out.write_text(json.dumps(payload))
    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"  -> {out.name} ({size_mb:.2f} MB)")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_raw()

    # Fit a global Country encoder so all quarters share the same encoding.
    country_encoder = LabelEncoder().fit(df["Country"])
    print(f"Country encoder fit on {len(country_encoder.classes_)} countries")

    scaler = None  # Will be fit on Q1, reused for Q2/Q3/Q4
    rows = []
    for name, start, end in QUARTERS:
        _cust, X, y, scaler = build_quarter(df, country_encoder, scaler, name, start, end)
        write_batch(name, X, y)
        rows.append({
            "season": name,
            "period": f"{start} to {end}",
            "samples": len(X),
            "high_value_pct": round(float(y.mean()) * 100, 1),
            "feature_means": X.mean(axis=0).round(3).tolist(),
        })

    summary = OUT_DIR / "summary.json"
    summary.write_text(json.dumps(rows, indent=2))
    print(f"\nSummary -> {summary}")
    print("\nFeature means per season (post-scaler-fit-on-Q1):")
    header = ["Season"] + FEATURE_COLS
    print("  " + " | ".join(f"{h:>16}" for h in header))
    for r in rows:
        cells = [r["season"]] + [f"{v:>16.3f}" for v in r["feature_means"]]
        print("  " + " | ".join(f"{c:>16}" if isinstance(c, str) else c for c in cells))


if __name__ == "__main__":
    main()
