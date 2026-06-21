"""
hotspot.py — Spatio-temporal forecaster for event LOAD per (corridor x time-bucket).

Predicts how many events to expect in each corridor in an upcoming time window, using
lag/rolling/calendar features. Trained with a time-based split and back-tested.

Run:
    python -m src.hotspot
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.features import build_panel_features, load_clean

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
SPLIT_DATE = pd.Timestamp("2024-03-01", tz="UTC")  # buckets carry tz; compare tz-aware

FEATURES = ["corridor", "hour", "dow", "is_weekend",
            "lag_1", "lag_8", "lag_56", "roll_mean_8", "roll_mean_56"]
CAT = ["corridor"]


def _prep(panel: pd.DataFrame) -> pd.DataFrame:
    panel = panel.copy()
    panel["corridor"] = panel["corridor"].astype("string").astype("category")
    panel["is_weekend"] = panel["is_weekend"].astype(int)
    for c in ["hour", "dow", "lag_1", "lag_8", "lag_56", "roll_mean_8", "roll_mean_56", "n_events"]:
        panel[c] = pd.to_numeric(panel[c], errors="coerce").astype("float64")
    return panel


def precision_at_k(test: pd.DataFrame, k: int = 10) -> float:
    """For each time bucket, do the predicted top-K corridors overlap the actual top-K?"""
    hits, total = 0, 0
    for _, grp in test.groupby("bucket"):
        if (grp["n_events"] > 0).sum() == 0:
            continue
        top_pred = set(grp.nlargest(k, "pred")["corridor"])
        top_true = set(grp.nlargest(k, "n_events")["corridor"])
        hits += len(top_pred & top_true)
        total += min(k, len(top_true))
    return hits / total if total else float("nan")


def main() -> None:
    MODELS.mkdir(exist_ok=True)
    panel = _prep(build_panel_features(load_clean()))
    train = panel[panel["bucket"] < SPLIT_DATE]
    test = panel[panel["bucket"] >= SPLIT_DATE].copy()
    print(f"panel train: {len(train)}  test: {len(test)}")

    reg = LGBMRegressor(
        n_estimators=600, learning_rate=0.03, num_leaves=63,
        subsample=0.8, colsample_bytree=0.8, verbose=-1,
    )
    reg.fit(train[FEATURES], train["n_events"], categorical_feature=CAT)
    test["pred"] = np.clip(reg.predict(test[FEATURES]), 0, None)

    # baseline: persistence (last week same bucket = lag_56)
    base_mae = mean_absolute_error(test["n_events"], test["lag_56"])
    metrics = {
        "n_test_buckets": int(test["bucket"].nunique()),
        "n_test_rows": int(len(test)),
        "mae": round(float(mean_absolute_error(test["n_events"], test["pred"])), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(test["n_events"], test["pred"]))), 4),
        "baseline_mae_lastweek": round(float(base_mae), 4),
        "precision_at_5": round(float(precision_at_k(test, 5)), 4),
        "precision_at_10": round(float(precision_at_k(test, 10)), 4),
        "mean_events_per_bucket": round(float(test["n_events"].mean()), 4),
    }
    joblib.dump(reg, MODELS / "hotspot.joblib")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "hotspot_metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
