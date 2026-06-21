"""
feedback.py — Post-Event Learning Loop (Engine 3).

Closes the loop the problem statement asks for ("no post-event learning system"):

    predict  ->  log prediction  ->  record what ACTUALLY happened  ->  learn corrections
       ^                                                                      |
       +----------------- future predictions are auto-calibrated -------------+

Two learning mechanisms, both fully in code:
  1. Online calibration (always on, safe): from logged (prediction, actual) pairs we learn
     a duration correction factor and a road-closure probability shift, persisted to
     models/calibration.json and applied automatically by serve.predict_event().
  2. Full retrain (power action): re-run the training pipeline on all data.

Storage is a plain CSV (data/feedback_log.csv) so it is append-friendly and human-inspectable.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "data" / "feedback_log.csv"
CALIB_PATH = ROOT / "models" / "calibration.json"

LOG_COLS = [
    "id", "predicted_at", "event_type", "event_cause", "corridor", "zone", "day", "hour", "when",
    "pred_closure_prob", "pred_needs_barricade", "pred_duration_min", "pred_priority",
    "actual_closure", "actual_duration_min", "actual_high_priority", "resolved",
]

DUR_FACTOR_CLIP = (0.3, 3.0)     # don't let one weird event swing duration wildly
PROB_SHIFT_CLIP = (-0.5, 0.5)
MIN_FOR_CALIB = 5                 # need a few resolved events before trusting a correction


# --------------------------------------------------------------------------- log I/O
_BOOL_COLS = ["pred_needs_barricade", "actual_closure", "actual_high_priority", "resolved"]
_BOOL_MAP = {True: True, False: False, "True": True, "False": False, "true": True, "false": False,
             1: True, 0: False, 1.0: True, 0.0: False}


def _parse_bool(s: pd.Series) -> pd.Series:
    """Parse mixed bool/str/num (incl. CSV round-trip 'True'/'False') into nullable boolean.
    Avoids the trap where 'False'.astype(bool) == True (non-empty string is truthy)."""
    return s.map(_BOOL_MAP).astype("boolean")


def load_log() -> pd.DataFrame:
    if not LOG_PATH.exists():
        return pd.DataFrame(columns=LOG_COLS)
    df = pd.read_csv(LOG_PATH, dtype={"id": str})
    for c in LOG_COLS:                       # tolerate older/partial files
        if c not in df.columns:
            df[c] = np.nan
    for c in _BOOL_COLS:                      # robust, dtype-stable boolean columns
        df[c] = _parse_bool(df[c])
    return df[LOG_COLS]


_DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


def _sanitize(v):
    """Neutralize CSV/Excel formula injection: a leading =,+,-,@ makes Excel execute the cell.
    Prefix such string values with an apostrophe so they're treated as text."""
    if isinstance(v, str) and v and v[0] in _DANGEROUS:
        return "'" + v
    return v


def _save_log(df: pd.DataFrame) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = df[LOG_COLS].copy()
    for c in ["event_type", "event_cause", "corridor", "zone", "day", "when"]:  # user-influenced text
        out[c] = out[c].map(_sanitize)
    out.to_csv(LOG_PATH, index=False)


def log_prediction(event: dict, pred: dict, *, day: str | None = None, hour: int | None = None) -> str:
    """Append a prediction to the log with empty 'actual_*' fields. Returns the row id."""
    row = {
        "id": uuid.uuid4().hex[:8],
        "predicted_at": pd.Timestamp.now().isoformat(timespec="seconds"),
        "event_type": event.get("event_type"), "event_cause": event.get("event_cause"),
        "corridor": event.get("corridor"), "zone": event.get("zone"),
        "day": day, "hour": hour, "when": event.get("when"),
        "pred_closure_prob": pred.get("road_closure_prob"),
        "pred_needs_barricade": bool(pred.get("needs_barricade")),
        "pred_duration_min": pred.get("expected_duration_min"),
        "pred_priority": pred.get("predicted_priority"),
        "actual_closure": np.nan, "actual_duration_min": np.nan,
        "actual_high_priority": np.nan, "resolved": False,
    }
    df = pd.concat([load_log(), pd.DataFrame([row])], ignore_index=True)
    _save_log(df)
    return row["id"]


def record_actual(row_id: str, *, actual_closure: bool | None = None,
                  actual_duration_min: float | None = None,
                  actual_high_priority: bool | None = None) -> bool:
    """Fill in what actually happened for a logged prediction, then refresh calibration."""
    df = load_log()
    m = df["id"] == row_id
    if not m.any():
        return False
    if actual_closure is not None:
        df.loc[m, "actual_closure"] = bool(actual_closure)
    if actual_duration_min is not None:
        df.loc[m, "actual_duration_min"] = float(actual_duration_min)
    if actual_high_priority is not None:
        df.loc[m, "actual_high_priority"] = bool(actual_high_priority)
    df.loc[m, "resolved"] = True
    _save_log(df)
    update_calibration()
    return True


# --------------------------------------------------------------------------- learning
def _resolved(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["resolved"].astype("boolean").fillna(False)].copy()


def update_calibration() -> dict:
    """Learn correction terms from resolved feedback and persist them. Returns the calibration."""
    df = _resolved(load_log())
    calib = {"n_resolved": int(len(df)), "duration_factor": 1.0, "closure_prob_shift": 0.0,
             "updated_at": pd.Timestamp.now().isoformat(timespec="seconds"), "active": False}

    if len(df) >= MIN_FOR_CALIB:
        # duration: scalar correction factor that MINIMIZES mean absolute error on reviewed events
        # (factor=1.0 is in the search grid, so the learned factor can never be worse than raw).
        d = df.dropna(subset=["actual_duration_min", "pred_duration_min"])
        d = d[d["pred_duration_min"] > 0]
        if len(d) >= MIN_FOR_CALIB:
            p = d["pred_duration_min"].astype(float).to_numpy()
            a = d["actual_duration_min"].astype(float).to_numpy()
            grid = np.arange(DUR_FACTOR_CLIP[0], DUR_FACTOR_CLIP[1] + 1e-9, 0.01)
            mae = [np.mean(np.abs(f * p - a)) for f in grid]
            calib["duration_factor"] = float(round(grid[int(np.argmin(mae))], 3))

        # closure: shift predicted probability toward the observed closure rate
        c = df.dropna(subset=["actual_closure", "pred_closure_prob"])
        if len(c) >= MIN_FOR_CALIB:
            observed = float(c["actual_closure"].astype(float).mean())
            pred_mean = float(c["pred_closure_prob"].astype(float).mean())
            calib["closure_prob_shift"] = float(np.clip(observed - pred_mean, *PROB_SHIFT_CLIP))

        calib["active"] = True

    CALIB_PATH.parent.mkdir(parents=True, exist_ok=True)
    CALIB_PATH.write_text(json.dumps(calib, indent=2))
    return calib


def load_calibration() -> dict:
    if not CALIB_PATH.exists():
        return {"duration_factor": 1.0, "closure_prob_shift": 0.0, "active": False, "n_resolved": 0}
    try:
        return json.loads(CALIB_PATH.read_text())
    except Exception:
        return {"duration_factor": 1.0, "closure_prob_shift": 0.0, "active": False, "n_resolved": 0}


def apply_calibration(pred: dict, calib: dict | None = None) -> dict:
    """Return a calibrated copy of a prediction, keeping the raw values for transparency."""
    calib = calib or load_calibration()
    out = dict(pred)
    out["road_closure_prob_raw"] = pred.get("road_closure_prob")
    out["expected_duration_min_raw"] = pred.get("expected_duration_min")
    out["calibrated"] = bool(calib.get("active"))
    if not calib.get("active"):
        return out

    factor = float(calib.get("duration_factor", 1.0))
    shift = float(calib.get("closure_prob_shift", 0.0))
    if pred.get("expected_duration_min") is not None:
        out["expected_duration_min"] = round(float(np.clip(pred["expected_duration_min"] * factor, 0, 48 * 60)), 1)
    if pred.get("road_closure_prob") is not None:
        newp = float(np.clip(pred["road_closure_prob"] + shift, 0.0, 1.0))
        out["road_closure_prob"] = round(newp, 3)
        out["needs_barricade"] = newp >= 0.5
    return out


def learning_metrics() -> dict:
    """Accuracy of predictions vs actuals, and how much calibration would improve duration error."""
    df = _resolved(load_log())
    calib = load_calibration()
    out = {"n_logged": int(len(load_log())), "n_resolved": int(len(df)),
           "closure_accuracy": None, "duration_mae_raw": None, "duration_mae_calibrated": None,
           "priority_accuracy": None}
    if df.empty:
        return out

    c = df.dropna(subset=["actual_closure", "pred_closure_prob"])
    if len(c):
        pred_label = c["pred_closure_prob"].astype(float) >= 0.5
        out["closure_accuracy"] = round(float((pred_label == c["actual_closure"].astype(bool)).mean()), 3)

    d = df.dropna(subset=["actual_duration_min", "pred_duration_min"])
    if len(d):
        err_raw = (d["pred_duration_min"].astype(float) - d["actual_duration_min"].astype(float)).abs()
        out["duration_mae_raw"] = round(float(err_raw.mean()), 1)
        cal_pred = d["pred_duration_min"].astype(float) * float(calib.get("duration_factor", 1.0))
        err_cal = (cal_pred - d["actual_duration_min"].astype(float)).abs()
        out["duration_mae_calibrated"] = round(float(err_cal.mean()), 1)

    p = df.dropna(subset=["actual_high_priority", "pred_priority"])
    if len(p):
        pred_high = p["pred_priority"].astype(str).str.lower().eq("high")
        out["priority_accuracy"] = round(float((pred_high == p["actual_high_priority"].astype(bool)).mean()), 3)
    return out


# --------------------------------------------------------------------------- demo seeding
def seed_from_history(n: int = 40, seed: int = 0) -> int:
    """Bootstrap the loop with REAL prediction-vs-actual pairs: sample historical events, predict
    them (uncalibrated), and record their genuine outcomes as the 'actuals'. Lets the learning loop
    be demonstrated immediately, using true labels rather than fabricated ones. Returns rows added."""
    from src.serve import predict_event  # lazy import avoids serve<->feedback circularity

    clean = ROOT / "data" / "clean_events.parquet"
    if not clean.exists():
        return 0
    src_df = pd.read_parquet(clean)
    src_df = src_df[src_df["duration_min"].notna()]
    if src_df.empty:
        return 0
    sample = src_df.sample(min(n, len(src_df)), random_state=seed)

    rows = []
    for _, r in sample.iterrows():
        when = pd.Timestamp(r["start_datetime"])
        ev = {"event_type": r.get("event_type", "unplanned"),
              "event_cause": r.get("event_cause", "others"),
              "corridor": r.get("corridor", "Non-corridor"), "zone": r.get("zone", "unknown"),
              "latitude": float(r.get("latitude", 12.97) or 12.97),
              "longitude": float(r.get("longitude", 77.59) or 77.59),
              "when": when.isoformat()}
        pred = predict_event(ev, calibrate=False)
        rows.append({
            "id": uuid.uuid4().hex[:8],
            "predicted_at": pd.Timestamp.now().isoformat(timespec="seconds"),
            "event_type": ev["event_type"], "event_cause": ev["event_cause"],
            "corridor": ev["corridor"], "zone": ev["zone"],
            "day": when.day_name(), "hour": int(when.hour), "when": ev["when"],
            "pred_closure_prob": pred["road_closure_prob"],
            "pred_needs_barricade": bool(pred["needs_barricade"]),
            "pred_duration_min": pred["expected_duration_min"],
            "pred_priority": pred["predicted_priority"],
            "actual_closure": bool(r["requires_road_closure"]),
            "actual_duration_min": float(r["duration_min"]),
            "actual_high_priority": bool(r["is_high_priority"]),
            "resolved": True,
        })
    df = pd.concat([load_log(), pd.DataFrame(rows)], ignore_index=True)
    _save_log(df)
    update_calibration()
    return len(rows)


if __name__ == "__main__":
    added = seed_from_history(40)
    print(f"Seeded {added} feedback rows.")
    print("Calibration:", json.dumps(load_calibration(), indent=2))
    print("Metrics:", json.dumps(learning_metrics(), indent=2))
