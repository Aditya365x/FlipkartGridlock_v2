"""
serve.py — Load trained models and score new/hypothetical events. Shared by the API and dashboard.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
# ASTraM timestamps are already Bengaluru-local (see note in features.py) — no UTC->IST offset.

CAT_FEATURES = ["event_type", "event_cause", "corridor", "zone", "veh_type", "part_of_day"]
FEATURES = [
    "event_type", "event_cause", "is_event_driven", "corridor", "zone", "veh_type",
    "hour", "dow", "is_weekend", "month", "week_of_year", "is_holiday", "part_of_day",
    "latitude", "longitude", "corridor_med_duration", "corridor_event_count",
    "corridor_closure_rate",
]
EVENT_DRIVEN = {"public_event", "procession", "vip_movement", "protest", "construction"}


HOTSPOT_FEATURES = ["corridor", "hour", "dow", "is_weekend",
                    "lag_1", "lag_8", "lag_56", "roll_mean_8", "roll_mean_56"]
_LAG_COLS = ["lag_1", "lag_8", "lag_56", "roll_mean_8", "roll_mean_56"]


class InvalidWhen(ValueError):
    """Raised when an event timestamp cannot be parsed — lets callers return a clean 4xx."""


def parse_when(when):
    """Parse an ISO/loose datetime string to a tz-naive (Bengaluru-local) Timestamp.

    Returns 'now' for None/empty; raises InvalidWhen for anything unparseable instead of
    letting pandas throw a raw DateParseError that 500s an API call.
    """
    if when is None or (isinstance(when, str) and not when.strip()):
        return pd.Timestamp.now()
    try:
        ts = pd.Timestamp(when)
    except Exception as e:                       # ValueError, DateParseError, OutOfBounds, ...
        raise InvalidWhen(f"Could not parse 'when'={when!r}; expected ISO format like "
                          f"'2024-04-15T19:00:00'.") from e
    if ts.tzinfo is not None:
        ts = ts.tz_localize(None)
    return ts


@lru_cache(maxsize=1)
def _load():
    models = {
        "severity": joblib.load(MODELS / "severity.joblib"),
        "road_closure": joblib.load(MODELS / "road_closure.joblib"),
        "duration": joblib.load(MODELS / "duration.joblib"),
    }
    priors = json.loads((MODELS / "priors.json").read_text())
    try:                                       # isotonic calibrator for road-closure probabilities
        models["road_closure_calibrator"] = joblib.load(MODELS / "road_closure_calibrator.joblib")
    except Exception:
        models["road_closure_calibrator"] = None
    return models, priors


@lru_cache(maxsize=1)
def _known_vocab() -> dict:
    """Known training categories, for out-of-distribution (OOD) detection. Degrades to {} if the
    clean dataset isn't available (predictions still work, just without the OOD vocab check)."""
    try:
        df = pd.read_parquet(ROOT / "data" / "clean_events.parquet")
        return {c: set(map(str, df[c].dropna().unique()))
                for c in ("event_type", "event_cause", "corridor", "zone") if c in df.columns}
    except Exception:
        return {}


@lru_cache(maxsize=1)
def _load_hotspot():
    """Hotspot regressor + 'typical recent activity' lags per (corridor, 3h-bucket-hour).

    For a what-if forecast we don't have live lags, so we use each corridor's *average*
    lag/rolling values at that hour-of-day as a representative recent-activity context.
    """
    from src.features import build_panel_features, load_clean  # local import: heavy deps
    reg = joblib.load(MODELS / "hotspot.joblib")
    panel = build_panel_features(load_clean())
    typ = panel.groupby(["corridor", "hour"], observed=True)[_LAG_COLS].mean().reset_index()
    return reg, typ


def forecast_corridor_load(when: str | None = None, exclude_non_corridor: bool = True) -> dict:
    """Predict event load per corridor for the 3-hour window containing `when` (local time).

    Returns {corridor: predicted_events}. Powers the 'forecast spread' in deployment planning.
    """
    reg, typ = _load_hotspot()
    w = parse_when(when)
    bucket_hour = (int(w.hour) // 3) * 3          # panel buckets are floored to 3h
    dow = int(w.dayofweek)

    f = typ[typ["hour"] == bucket_hour].copy()
    if f.empty:                                    # hour not seen -> corridor-average lags
        f = typ.groupby("corridor", observed=True)[_LAG_COLS].mean().reset_index()
        f["hour"] = bucket_hour
    f["dow"] = dow
    f["is_weekend"] = int(dow in (5, 6))
    f["corridor"] = f["corridor"].astype("string").astype("category")
    f["pred"] = np.clip(reg.predict(f[HOTSPOT_FEATURES]), 0, None)

    out = {str(c): float(p) for c, p in zip(f["corridor"], f["pred"])}
    if exclude_non_corridor:
        out.pop("Non-corridor", None)
    return out


def _part_of_day(hour: int) -> str:
    bins = [(-1, 5, "night"), (5, 10, "morning_peak"), (10, 16, "midday"),
            (16, 20, "evening_peak"), (20, 23, "late")]
    for lo, hi, name in bins:
        if lo < hour <= hi:
            return name
    return "night"


def make_feature_row(event: dict) -> pd.DataFrame:
    """event: {event_type, event_cause, corridor, zone, veh_type, latitude, longitude, when(ISO)}"""
    _, priors = _load()
    from src.features import is_holiday_date          # local import: avoid heavy deps at module load
    # `when`'s wall-clock is interpreted as Bengaluru-local, matching the training data.
    local = parse_when(event.get("when"))
    corridor = event.get("corridor", "Non-corridor")
    hour = int(local.hour)
    global_closure = float(priors.get("global_closure_rate", 0.1))
    row = {
        "event_type": event.get("event_type", "unplanned"),
        "event_cause": event.get("event_cause", "others"),
        "is_event_driven": int(event.get("event_cause", "others") in EVENT_DRIVEN),
        "corridor": corridor,
        "zone": event.get("zone", "unknown"),
        "veh_type": event.get("veh_type", "none"),
        "hour": hour,
        "dow": int(local.dayofweek),
        "is_weekend": int(local.dayofweek in (5, 6)),
        "month": int(local.month),
        "week_of_year": int(local.isocalendar().week),
        "is_holiday": int(is_holiday_date(local)),
        "part_of_day": _part_of_day(hour),
        "latitude": float(event.get("latitude", 12.97) or 12.97),
        "longitude": float(event.get("longitude", 77.59) or 77.59),
        "corridor_med_duration": float(priors["corridor_med_duration"].get(corridor, priors["global_med_duration"])),
        "corridor_event_count": float(priors["corridor_event_count"].get(corridor, 0)),
        "corridor_closure_rate": float(priors.get("corridor_closure_rate", {}).get(corridor, global_closure)),
    }
    df = pd.DataFrame([row])[FEATURES]
    for c in CAT_FEATURES:
        df[c] = df[c].astype("category")
    return df


def predict_event(event: dict, calibrate: bool = True) -> dict:
    models, priors = _load()
    X = make_feature_row(event)
    sev = float(models["severity"].predict_proba(X)[:, 1][0])
    clo = float(models["road_closure"].predict_proba(X)[:, 1][0])
    dur = float(np.expm1(models["duration"].predict(X)[0]))
    dur = float(np.clip(dur, 0, 48 * 60))

    # Calibrate closure probability (isotonic) and decide barricade at the TUNED threshold, not 0.5.
    cal = models.get("road_closure_calibrator")
    if cal is not None:
        clo = float(np.clip(cal.transform([clo])[0], 0.0, 1.0))
    closure_threshold = float(priors.get("closure_threshold", 0.5))

    pred = {
        "severity_high_prob": round(sev, 3),
        "predicted_priority": "High" if sev >= 0.5 else "Low",
        "road_closure_prob": round(clo, 3),
        "needs_barricade": clo >= closure_threshold,
        "closure_threshold": round(closure_threshold, 3),
        "expected_duration_min": round(dur, 1),
    }

    # --- OOD detection + uncertainty scoring: never present confident output for garbage input ---
    vocab = _known_vocab()
    warnings = [f"unknown {f}={event.get(f)!r}" for f in ("event_type", "event_cause", "corridor", "zone")
                if vocab.get(f) and event.get(f) is not None and str(event.get(f)) not in vocab[f]]
    ood = bool(warnings)
    closure_uncertain = abs(clo - closure_threshold) < 0.12   # near the (tuned) decision boundary
    pred["out_of_distribution"] = ood
    pred["warnings"] = warnings
    pred["confidence"] = "low" if (ood or closure_uncertain) else "high"

    if calibrate:
        # Post-Event Learning Loop: apply corrections learned from logged actuals (no-op until
        # enough feedback exists). Lazy import keeps serve importable even if feedback is absent.
        try:
            from src.feedback import apply_calibration
            pred = apply_calibration(pred)
        except Exception:
            pass
    return pred


if __name__ == "__main__":
    demo = {"event_type": "planned", "event_cause": "public_event",
            "corridor": "CBD 2", "zone": "Central Zone 2",
            "latitude": 12.9788, "longitude": 77.5995, "when": "2024-04-15T13:30:00"}
    print("Event:", demo)
    print("Prediction:", json.dumps(predict_event(demo), indent=2))
