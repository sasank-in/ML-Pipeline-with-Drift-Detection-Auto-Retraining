"""End-to-end seasonal drift demo against running services.

Assumes: ingestion API on :8001, prediction service on :8002, drift monitor
and retraining worker running in the background.

Sequence:
  Q1 -> bootstrap training (worker auto-trains when no active model)
  Q2 -> ingest, predict, sleep through one drift check
  Q3 -> ingest, predict, sleep through one drift check
  Q4 -> ingest, predict, sleep through one drift check

Reports per-quarter:
  - drift events recorded (score, affected features)
  - retraining jobs triggered (status, accuracy)
  - active model version after the season
"""
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.database import DatabaseManager  # noqa: E402

INGEST_URL = "http://127.0.0.1:8001/ingest/batch"
PREDICT_URL = "http://127.0.0.1:8002/predict"
HEALTH_URL = "http://127.0.0.1:8002/health"
SEASONAL_DIR = ROOT / "data" / "seasonal"


def load_season(name: str):
    path = SEASONAL_DIR / f"{name}.json"
    return json.loads(path.read_text())


def ingest(season_name: str) -> int:
    payload = load_season(season_name)
    r = requests.post(INGEST_URL, json=payload, timeout=60)
    r.raise_for_status()
    body = r.json()
    print(f"  ingest {season_name}: {body['samples_ingested']} samples queued")
    return body["samples_ingested"]


def predict_sample(features: list, label: int | None = None) -> dict:
    r = requests.post(PREDICT_URL, json={"features": [features]}, timeout=30)
    if r.status_code != 200:
        return {"error": r.status_code, "body": r.text}
    body = r.json()
    out = {
        "predicted": body["predictions"][0],
        "confidence": round(max(body["probabilities"][0]), 3),
        "model_version": body.get("model_version"),
    }
    if label is not None:
        out["actual"] = label
        out["correct"] = bool(body["predictions"][0] == label)
    return out


def predict_batch(features: list[list], chunk: int = 200) -> dict:
    """Stream a whole season through /predict in chunks so the drift monitor's
    prediction_buffer fills up and drift detection can actually run."""
    total = len(features)
    sent = 0
    correct_preds = []
    versions = set()
    while sent < total:
        slice_ = features[sent:sent + chunk]
        r = requests.post(PREDICT_URL, json={"features": slice_}, timeout=60)
        r.raise_for_status()
        body = r.json()
        versions.add(body.get("model_version"))
        correct_preds.extend(body["predictions"])
        sent += len(slice_)
    return {"sent": sent, "model_versions_seen": list(versions),
            "first_predictions": correct_preds[:5]}


def health() -> dict:
    r = requests.get(HEALTH_URL, headers={"Accept": "application/json"}, timeout=10)
    return {"code": r.status_code, **r.json()}


def wait_for_model(db: DatabaseManager, since_version: str | None, timeout: int = 90):
    """Block until a NEW deployed model version appears in the registry."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        active = db.get_active_model()
        if active and active["model_version"] != since_version:
            print(f"    new model deployed: {active['model_version']}")
            return active
        time.sleep(2)
    print(f"    TIMEOUT: no new model after {timeout}s")
    return None


def fetch_recent_drift_events(db: DatabaseManager, since_ts: float) -> list:
    conn = db._get_connection()
    cur = conn.cursor()
    ph = "%s" if db.use_postgres else "?"
    cur.execute(
        f"SELECT timestamp, drift_detected, drift_score, affected_features, action_taken "
        f"FROM drift_events WHERE EXTRACT(EPOCH FROM timestamp) > {ph} ORDER BY id DESC"
        if db.use_postgres else
        f"SELECT timestamp, drift_detected, drift_score, affected_features, action_taken "
        f"FROM drift_events WHERE strftime('%s', timestamp) > {ph} ORDER BY id DESC",
        (since_ts,),
    )
    rows = cur.fetchall()
    db._release(conn)
    out = []
    for r in rows:
        affected = r[3]
        if isinstance(affected, str):
            affected = json.loads(affected)
        out.append({
            "ts": str(r[0]),
            "detected": r[1],
            "score": float(r[2]) if r[2] is not None else None,
            "affected": affected,
            "action": r[4],
        })
    return out


def fetch_recent_training(db: DatabaseManager, since_ts: float) -> list:
    conn = db._get_connection()
    cur = conn.cursor()
    ph = "%s" if db.use_postgres else "?"
    cur.execute(
        f"SELECT timestamp, status, accuracy, f1_score, model_version, trigger_reason, samples_count "
        f"FROM training_jobs WHERE EXTRACT(EPOCH FROM timestamp) > {ph} ORDER BY id DESC"
        if db.use_postgres else
        f"SELECT timestamp, status, accuracy, f1_score, model_version, trigger_reason, samples_count "
        f"FROM training_jobs WHERE strftime('%s', timestamp) > {ph} ORDER BY id DESC",
        (since_ts,),
    )
    rows = cur.fetchall()
    db._release(conn)
    return [
        {
            "ts": str(r[0]), "status": r[1],
            "accuracy": float(r[2]) if r[2] is not None else None,
            "f1": float(r[3]) if r[3] is not None else None,
            "version": r[4], "trigger": r[5], "samples": r[6],
        }
        for r in rows
    ]


def run_season(db: DatabaseManager, name: str, drift_wait: int, predict_label: int | None = None):
    print(f"\n=== {name} ===")
    season_start = time.time()
    active_before = db.get_active_model()
    before_version = active_before["model_version"] if active_before else None

    # Ingest (with labels) so the retraining worker has labeled training data.
    ingest(name)

    # Stream this season's features through /predict so the drift monitor's
    # prediction_buffer fills with realistic production-shape data.
    payload = load_season(name)
    pred_result = predict_batch(payload["features"])
    print(f"  predicted {pred_result['sent']} rows through /predict "
          f"(versions seen: {pred_result['model_versions_seen']})")

    # Now wait for the drift monitor to consume the buffer and decide.
    print(f"  waiting {drift_wait}s for drift check + possible retraining...")
    time.sleep(drift_wait)

    sample = payload["features"][0]
    label = payload["labels"][0]
    result = predict_sample(sample, label=label)
    print(f"  predict[0]: {result}")

    # Drift events & training jobs since this season started
    drift_events = fetch_recent_drift_events(db, season_start)
    train_jobs = fetch_recent_training(db, season_start)

    print(f"  drift events: {len(drift_events)}")
    for ev in drift_events[:3]:
        affected = ev["affected"]
        affected_str = f"{len(affected) if isinstance(affected, list) else 'n/a'} features"
        print(f"    - detected={ev['detected']} score={ev['score']:.3f} action={ev['action']} ({affected_str})")
    print(f"  training jobs: {len(train_jobs)}")
    for tj in train_jobs[:3]:
        acc = f"{tj['accuracy']:.3f}" if tj["accuracy"] is not None else "n/a"
        print(f"    - {tj['status']} v={tj['version']} acc={acc} trigger={tj['trigger']}")

    active_after = db.get_active_model()
    if active_after and active_after["model_version"] != before_version:
        print(f"  >>> ACTIVE MODEL CHANGED: {before_version} -> {active_after['model_version']}")
    elif active_after:
        print(f"  active model unchanged: {active_after['model_version']}")

    return {
        "season": name,
        "drift_events": drift_events,
        "training_jobs": train_jobs,
        "active_before": before_version,
        "active_after": active_after["model_version"] if active_after else None,
    }


def main():
    db = DatabaseManager()

    # Health gate
    h = health()
    print(f"Prediction /health: {h['code']} status={h['status']} model={h.get('model_version')}")

    # Q1 — bootstrap (if no active model exists, worker will train automatically;
    # otherwise this just adds samples to the queue for the next retraining)
    print("\n=== Q1 (BASELINE) ===")
    print("Ingesting Q1 to bootstrap model...")
    ingest("Q1")
    print("Waiting up to 90s for bootstrap training to complete...")
    waited = 0
    while waited < 90:
        active = db.get_active_model()
        if active:
            print(f"  bootstrap model deployed: {active['model_version']}")
            break
        time.sleep(3); waited += 3
    else:
        print("  WARNING: no model after 90s")
        return

    # Run drift seasons
    drift_wait = 35  # > DRIFT_CHECK_INTERVAL=20 so at least one cycle elapses
    summaries = [{"season": "Q1", "active_after": active["model_version"]}]
    for name in ("Q2", "Q3", "Q4"):
        summaries.append(run_season(db, name, drift_wait))

    # Final summary
    print("\n" + "=" * 70)
    print("DEMO SUMMARY")
    print("=" * 70)
    print(f"{'Season':<8} {'Drift?':<8} {'Score':<8} {'Retrained':<10} {'Active Model':<32}")
    for s in summaries:
        if s["season"] == "Q1":
            print(f"{'Q1':<8} {'-':<8} {'-':<8} {'bootstrap':<10} {s['active_after']:<32}")
            continue
        events = s.get("drift_events", [])
        detected = any(e["detected"] for e in events)
        max_score = max((e["score"] for e in events if e["score"] is not None), default=None)
        retrained = s["active_before"] != s["active_after"]
        score_str = f"{max_score:.3f}" if max_score is not None else "n/a"
        print(
            f"{s['season']:<8} {('YES' if detected else 'no'):<8} {score_str:<8} "
            f"{('YES' if retrained else 'no'):<10} {s['active_after']:<32}"
        )


if __name__ == "__main__":
    main()
