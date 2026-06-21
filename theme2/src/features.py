"""
features.py — Build model-ready feature frames from the cleaned events.

Two feature sets:
  * event-level features  -> for the impact models (one row per event)
  * panel features        -> (spatial cell x time bucket) for the hotspot forecaster

Run:
    python -m src.features
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CLEAN = ROOT / "data" / "clean_events.parquet"
EVENT_FEATS = ROOT / "data" / "event_features.parquet"
PANEL_FEATS = ROOT / "data" / "panel_features.parquet"

# NOTE: ASTraM timestamps are tagged `+00` but are actually already Bengaluru *local* time
# (the event distribution peaks at ~21:00 and bottoms out mid-afternoon — textbook traffic;
# adding a +5:30 "UTC->IST" offset shifted the peak to a nonsensical 02:30). So we use the
# stored wall-clock hour directly — no offset.

CATEGORICALS = ["event_type", "event_cause", "corridor", "zone", "veh_type", "part_of_day"]

# Bengaluru / Karnataka public holidays + major festivals over the data window (2023-11 → 2024-04).
# Festivals reliably shift traffic (processions, gatherings, closures), so is_holiday is a real signal.
HOLIDAYS = frozenset(pd.Timestamp(d).normalize() for d in [
    "2023-11-12", "2023-11-13", "2023-11-27", "2023-12-25",          # Deepavali, Balipadyami, Guru Nanak, Christmas
    "2024-01-01", "2024-01-15", "2024-01-26",                         # New Year, Sankranti, Republic Day
    "2024-03-08", "2024-03-25", "2024-03-29",                         # Maha Shivaratri, Holi, Good Friday
    "2024-04-09", "2024-04-11", "2024-04-17",                         # Ugadi, Eid-ul-Fitr, Ram Navami
])


def is_holiday_date(ts) -> bool:
    """Whether a timestamp falls on a known holiday/festival (used at train and serve time)."""
    try:
        return pd.Timestamp(ts).normalize() in HOLIDAYS
    except Exception:
        return False


def load_clean() -> pd.DataFrame:
    return pd.read_parquet(CLEAN)


def add_time_features(df: pd.DataFrame, ts_col: str = "start_datetime") -> pd.DataFrame:
    local = df[ts_col]  # stored time is already Bengaluru-local (see note above)
    df["hour"] = local.dt.hour
    df["dow"] = local.dt.dayofweek
    df["is_weekend"] = df["dow"].isin([5, 6])
    df["month"] = local.dt.month
    df["day"] = local.dt.day
    df["week_of_year"] = local.dt.isocalendar().week.astype(int)   # seasonal pattern
    df["is_holiday"] = local.dt.normalize().isin(HOLIDAYS)         # festival/holiday signal
    df["part_of_day"] = pd.cut(
        df["hour"], bins=[-1, 5, 10, 16, 20, 23],
        labels=["night", "morning_peak", "midday", "evening_peak", "late"],
    ).astype("string").fillna("night")
    return df


def build_event_features(df: pd.DataFrame) -> pd.DataFrame:
    """Raw event + time + space features. NOTE: no target-derived priors here — those
    are fit on the training split only (see impact_models.add_train_priors) to avoid leakage."""
    df = df.copy()
    df = add_time_features(df)
    for c in CATEGORICALS:
        df[c] = df[c].astype("category")
    return df


def build_panel_features(df: pd.DataFrame, freq: str = "3h") -> pd.DataFrame:
    """Aggregate events to (corridor x time-bucket) and add lag/rolling features."""
    d = df.copy()
    d["bucket"] = d["start_datetime"].dt.floor(freq)  # already local (see note above)

    grp = d.groupby(["corridor", "bucket"])
    panel = grp.agg(
        n_events=("id", "size"),
        n_high=("is_high_priority", "sum"),
        n_closure=("requires_road_closure", "sum"),
    ).reset_index()

    # build a complete corridor x time grid so "no events" buckets exist (needed for forecasting)
    buckets = pd.date_range(panel["bucket"].min(), panel["bucket"].max(), freq=freq)
    corridors = panel["corridor"].unique()
    full = pd.MultiIndex.from_product([corridors, buckets], names=["corridor", "bucket"]).to_frame(index=False)
    panel = full.merge(panel, on=["corridor", "bucket"], how="left").fillna(
        {"n_events": 0, "n_high": 0, "n_closure": 0}
    )
    panel = panel.sort_values(["corridor", "bucket"]).reset_index(drop=True)

    # calendar features on the bucket
    panel["hour"] = panel["bucket"].dt.hour
    panel["dow"] = panel["bucket"].dt.dayofweek
    panel["is_weekend"] = panel["dow"].isin([5, 6])

    # lag & rolling features per corridor (shifted to avoid leakage)
    g = panel.groupby("corridor")["n_events"]
    panel["lag_1"] = g.shift(1)
    panel["lag_8"] = g.shift(8)            # ~1 day back at 3h freq
    panel["lag_56"] = g.shift(56)          # ~1 week back
    panel["roll_mean_8"] = g.shift(1).rolling(8, min_periods=1).mean().reset_index(level=0, drop=True)
    panel["roll_mean_56"] = g.shift(1).rolling(56, min_periods=1).mean().reset_index(level=0, drop=True)
    panel[["lag_1", "lag_8", "lag_56"]] = panel[["lag_1", "lag_8", "lag_56"]].fillna(0)
    panel["corridor"] = panel["corridor"].astype("category")
    return panel


def main() -> None:
    df = load_clean()
    ev = build_event_features(df)
    pan = build_panel_features(df)
    ev.to_parquet(EVENT_FEATS, index=False)
    pan.to_parquet(PANEL_FEATS, index=False)
    print(f"event_features: {ev.shape} -> {EVENT_FEATS.relative_to(ROOT)}")
    print(f"panel_features: {pan.shape} -> {PANEL_FEATS.relative_to(ROOT)}")
    print(f"  panel corridors: {pan['corridor'].nunique()} | buckets: {pan['bucket'].nunique()}")
    print(f"  mean events/bucket: {pan['n_events'].mean():.3f} | max: {pan['n_events'].max():.0f}")


if __name__ == "__main__":
    main()
