"""
impact_models.py — Train the three event-impact models with a TIME-BASED split:
  1. severity      : will this event be High priority?        (LightGBM classifier)
  2. road_closure  : will it require a road closure?          (LightGBM classifier, imbalanced)
  3. duration      : how long until cleared, in minutes?      (LightGBM regressor, log-target)

Saves models to models/ and prints held-out metrics.

Run:
    python -m src.impact_models
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.metrics import (
    average_precision_score, f1_score, mean_absolute_error,
    mean_squared_error, precision_score, recall_score, roc_auc_score,
)
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import precision_recall_curve
from sklearn.model_selection import KFold, StratifiedKFold

from src.features import build_event_features, load_clean

OOF_SPLITS = 5
OOF_SEED = 42

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
SPLIT_DATE = pd.Timestamp("2024-03-01", tz="UTC")  # train < Mar 2024, test >= Mar 2024

FEATURES = [
    "event_type", "event_cause", "is_event_driven", "corridor", "zone", "veh_type",
    "hour", "dow", "is_weekend", "month", "week_of_year", "is_holiday", "part_of_day",
    "latitude", "longitude", "corridor_med_duration", "corridor_event_count",
    "corridor_closure_rate",
]
CAT_FEATURES = ["event_type", "event_cause", "corridor", "zone", "veh_type", "part_of_day"]


def add_train_priors(train: pd.DataFrame, test: pd.DataFrame):
    """Corridor priors with OUT-OF-FOLD (OOF) target encoding to prevent in-fold leakage.

    `corridor_med_duration` is *target-derived* (computed from duration_min). If we computed it
    over the whole training set and applied it to every training row, each row would see its own
    target -> leakage. Instead we use K-fold OOF: each training row's prior is computed from the
    OTHER folds only. Test rows (and the persisted serving prior) use the full-train median, which
    is correct because they are genuinely unseen.

    `corridor_event_count` is a plain count (not target-derived) -> full-train is fine.
    """
    train = train.copy()
    test = test.copy()
    global_med = float(train["duration_min"].median())
    global_closure = float(train["requires_road_closure"].astype(float).mean())

    # --- OOF corridor priors for TRAIN rows (median duration + closure rate, both target-derived) ---
    idx = train.index.to_numpy()
    oof_dur = pd.Series(index=train.index, dtype="float64")
    oof_clo = pd.Series(index=train.index, dtype="float64")
    kf = KFold(n_splits=OOF_SPLITS, shuffle=True, random_state=OOF_SEED)
    for fit_pos, val_pos in kf.split(idx):
        fit_idx, val_idx = idx[fit_pos], idx[val_pos]
        med_fold = train.loc[fit_idx].groupby("corridor", observed=True)["duration_min"].median()
        clo_fold = train.loc[fit_idx].groupby("corridor", observed=True)["requires_road_closure"].apply(
            lambda s: float(s.astype(float).mean()))
        fold_global_med = float(train.loc[fit_idx, "duration_min"].median())
        fold_global_clo = float(train.loc[fit_idx, "requires_road_closure"].astype(float).mean())
        oof_dur.loc[val_idx] = train.loc[val_idx, "corridor"].map(med_fold).fillna(fold_global_med).to_numpy()
        oof_clo.loc[val_idx] = train.loc[val_idx, "corridor"].map(clo_fold).fillna(fold_global_clo).to_numpy()
    train["corridor_med_duration"] = oof_dur.fillna(global_med).astype("float64")
    train["corridor_closure_rate"] = oof_clo.fillna(global_closure).astype("float64")

    # --- full-train priors for TEST + serving ---
    med_full = train.groupby("corridor", observed=True)["duration_min"].median()
    cnt = train.groupby("corridor", observed=True)["id"].size()
    clo_full = train.groupby("corridor", observed=True)["requires_road_closure"].apply(
        lambda s: float(s.astype(float).mean()))
    test["corridor_med_duration"] = test["corridor"].map(med_full).fillna(global_med).astype("float64")
    test["corridor_closure_rate"] = test["corridor"].map(clo_full).fillna(global_closure).astype("float64")
    for split in (train, test):
        split["corridor_event_count"] = split["corridor"].map(cnt).fillna(0).astype("float64")

    MODELS.mkdir(exist_ok=True)
    priors = {
        "global_med_duration": global_med,
        "global_closure_rate": global_closure,
        "oof_splits": OOF_SPLITS,
        "corridor_med_duration": {str(k): float(v) for k, v in med_full.items()},
        "corridor_event_count": {str(k): int(v) for k, v in cnt.items()},
        "corridor_closure_rate": {str(k): float(v) for k, v in clo_full.items()},
    }
    (MODELS / "priors.json").write_text(json.dumps(priors, indent=2))
    return train, test


def _to_int_bool(s: pd.Series) -> pd.Series:
    return s.astype("boolean").fillna(False).astype(int)


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # categoricals: arrow/string -> pandas category
    for c in CAT_FEATURES:
        df[c] = df[c].astype("string").astype("category")
    # boolean-ish features/targets -> plain int (handles NA from the 2 bad priority rows)
    for c in ["is_event_driven", "is_weekend", "is_holiday", "is_high_priority", "requires_road_closure"]:
        df[c] = _to_int_bool(df[c])
    # numeric features -> float64 numpy
    for c in ["hour", "dow", "month", "week_of_year", "latitude", "longitude", "duration_min"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    return df


def time_split(df: pd.DataFrame):
    train = df[df["start_datetime"] < SPLIT_DATE]
    test = df[df["start_datetime"] >= SPLIT_DATE]
    return train, test


def train_severity(train, test, metrics):
    X_tr, y_tr = train[FEATURES], train["is_high_priority"].astype(int)
    X_te, y_te = test[FEATURES], test["is_high_priority"].astype(int)
    clf = LGBMClassifier(
        n_estimators=400, learning_rate=0.03, num_leaves=31,
        subsample=0.8, colsample_bytree=0.8, class_weight="balanced", verbose=-1,
    )
    clf.fit(X_tr, y_tr, categorical_feature=CAT_FEATURES)
    p = clf.predict_proba(X_te)[:, 1]
    pred = (p >= 0.5).astype(int)
    metrics["severity"] = {
        "n_test": int(len(y_te)),
        "auc": round(float(roc_auc_score(y_te, p)), 4),
        "f1": round(float(f1_score(y_te, pred)), 4),
        "precision": round(float(precision_score(y_te, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_te, pred, zero_division=0)), 4),
        "base_rate": round(float(y_te.mean()), 4),
    }
    joblib.dump(clf, MODELS / "severity.joblib")
    return clf


def _fit_closure_lgbm(X, y) -> LGBMClassifier:
    pos_weight = float((y == 0).sum() / max((y == 1).sum(), 1))
    clf = LGBMClassifier(
        n_estimators=500, learning_rate=0.03, num_leaves=31,
        subsample=0.8, colsample_bytree=0.8, scale_pos_weight=pos_weight, verbose=-1,
    )
    clf.fit(X, y, categorical_feature=CAT_FEATURES)
    return clf


def train_closure(train, test, metrics):
    X_tr, y_tr = train[FEATURES], train["requires_road_closure"].astype(int)
    X_te, y_te = test[FEATURES], test["requires_road_closure"].astype(int)

    # --- OOF probabilities on TRAIN -> isotonic calibrator + F2-optimal threshold (no leakage) ---
    Xa = X_tr.reset_index(drop=True)
    ya = pd.Series(y_tr.to_numpy())
    oof = np.zeros(len(Xa))
    skf = StratifiedKFold(n_splits=OOF_SPLITS, shuffle=True, random_state=OOF_SEED)
    for fit_pos, val_pos in skf.split(Xa, ya):
        m = _fit_closure_lgbm(Xa.iloc[fit_pos], ya.iloc[fit_pos])
        oof[val_pos] = m.predict_proba(Xa.iloc[val_pos])[:, 1]
    iso = IsotonicRegression(out_of_bounds="clip").fit(oof, ya.to_numpy())
    oof_cal = iso.transform(oof)
    prec, rec, thr = precision_recall_curve(ya.to_numpy(), oof_cal)
    beta = 1.5                                                  # mild recall lean: closures are costly to miss
    fb = ((1 + beta**2) * prec * rec) / (beta**2 * prec + rec + 1e-9)
    best_thr = float(thr[int(np.argmax(fb[:-1]))]) if len(thr) else 0.5

    # --- final model on full train (for serving) + persist calibrator ---
    clf = _fit_closure_lgbm(X_tr, y_tr)
    joblib.dump(clf, MODELS / "road_closure.joblib")
    joblib.dump(iso, MODELS / "road_closure_calibrator.joblib")

    # --- evaluate on TEST: default 0.5 vs calibrated + tuned threshold ---
    p_raw = clf.predict_proba(X_te)[:, 1]
    p_cal = iso.transform(p_raw)
    pred_05 = (p_raw >= 0.5).astype(int)
    pred_tuned = (p_cal >= best_thr).astype(int)
    metrics["road_closure"] = {
        "n_test": int(len(y_te)),
        "pr_auc": round(float(average_precision_score(y_te, p_cal)), 4),
        "auc": round(float(roc_auc_score(y_te, p_cal)), 4),
        "precision@0.5": round(float(precision_score(y_te, pred_05, zero_division=0)), 4),
        "recall@0.5": round(float(recall_score(y_te, pred_05, zero_division=0)), 4),
        "threshold_tuned": round(best_thr, 4),
        "precision@tuned": round(float(precision_score(y_te, pred_tuned, zero_division=0)), 4),
        "recall@tuned": round(float(recall_score(y_te, pred_tuned, zero_division=0)), 4),
        "f1@tuned": round(float(f1_score(y_te, pred_tuned)), 4),
        "base_rate": round(float(y_te.mean()), 4),
    }
    # persist tuned threshold for serving
    pri = json.loads((MODELS / "priors.json").read_text())
    pri["closure_threshold"] = round(best_thr, 4)
    (MODELS / "priors.json").write_text(json.dumps(pri, indent=2))
    return clf


DURATION_CAP_MIN = 48 * 60   # rows pinned at exactly 48h are censored/defaulted end-times (artifacts)


def train_duration(train, test, metrics):
    # Exclude the 48h-cap artifact rows: they're missing/defaulted end-times, not real durations,
    # and they dominate the mean error and inflate predictions. Train & evaluate on real durations.
    tr = train[train["duration_min"].notna() & (train["duration_min"] < DURATION_CAP_MIN)]
    te = test[test["duration_min"].notna() & (test["duration_min"] < DURATION_CAP_MIN)]
    n_drop_tr = int((train["duration_min"] >= DURATION_CAP_MIN).sum())
    n_drop_te = int((test["duration_min"] >= DURATION_CAP_MIN).sum())
    X_tr, y_tr = tr[FEATURES], np.log1p(tr["duration_min"])
    X_te, y_te = te[FEATURES], te["duration_min"]
    reg = LGBMRegressor(
        n_estimators=500, learning_rate=0.03, num_leaves=31,
        subsample=0.8, colsample_bytree=0.8, verbose=-1,
    )
    reg.fit(X_tr, y_tr, categorical_feature=CAT_FEATURES)
    pred = np.expm1(reg.predict(X_te))
    pred = np.clip(pred, 0, 48 * 60)
    metrics["duration"] = {
        "n_test": int(len(y_te)),
        "n_cap_rows_excluded_train": n_drop_tr,
        "n_cap_rows_excluded_test": n_drop_te,
        "mae_min": round(float(mean_absolute_error(y_te, pred)), 1),
        "rmse_min": round(float(np.sqrt(mean_squared_error(y_te, pred))), 1),
        "median_ae_min": round(float(np.median(np.abs(y_te.values - pred))), 1),
        "test_median_min": round(float(y_te.median()), 1),
    }
    joblib.dump(reg, MODELS / "duration.joblib")
    return reg


def main() -> None:
    MODELS.mkdir(exist_ok=True)
    df = _prep(build_event_features(load_clean()))
    train, test = time_split(df)
    train, test = add_train_priors(train.copy(), test.copy())
    print(f"train: {len(train)}  test: {len(test)}  (split @ {SPLIT_DATE.date()})")

    metrics: dict = {}
    train_severity(train, test, metrics)
    train_closure(train, test, metrics)
    train_duration(train, test, metrics)

    # persist feature schema for serving
    schema = {"features": FEATURES, "cat_features": CAT_FEATURES,
              "split_date": str(SPLIT_DATE.date())}
    (MODELS / "schema.json").write_text(json.dumps(schema, indent=2))
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "impact_metrics.json").write_text(json.dumps(metrics, indent=2))

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
