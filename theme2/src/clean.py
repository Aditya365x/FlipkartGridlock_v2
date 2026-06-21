"""
clean.py — Load the raw ASTraM event CSV, clean it, derive the impact labels, and
write a tidy Parquet for downstream feature engineering / modeling.

Run:
    python -m src.clean
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW_CSV = ROOT / "data" / "raw" / "astram_events.csv"
OUT_PARQUET = ROOT / "data" / "clean_events.parquet"
CAUSE_MAP = ROOT / "configs" / "cause_map.yaml"

# Bengaluru bounding box (approx) for geo validation.
BLR_BBOX = dict(lat_min=12.6, lat_max=13.3, lon_min=77.3, lon_max=77.9)

NULLISH = {"", "NULL", "null", "None", "nan", "NaN"}


def _clean_str(s: pd.Series) -> pd.Series:
    s = s.astype("string").str.strip()
    return s.mask(s.isin(NULLISH))


def _parse_dt(s: pd.Series) -> pd.Series:
    """Parse ISO-ish timestamps; tolerate trailing tz/fractional seconds."""
    s = _clean_str(s)
    return pd.to_datetime(s, errors="coerce", utc=True, format="mixed")


def load_raw(path: Path = RAW_CSV) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    with open(CAUSE_MAP, "r", encoding="utf-8") as fh:
        cmap = yaml.safe_load(fh)
    norm = cmap["normalize"]
    event_driven = set(cmap["event_driven"])

    out = pd.DataFrame()
    out["id"] = _clean_str(df["id"])
    out["event_type"] = _clean_str(df["event_type"]).str.lower()

    # normalize cause
    cause = _clean_str(df["event_cause"])
    out["event_cause"] = cause.map(lambda x: norm.get(x, str(x).lower()) if pd.notna(x) else "unknown")
    out["event_cause"] = out["event_cause"].fillna("unknown")
    out["is_event_driven"] = out["event_cause"].isin(event_driven)

    # geo
    for col in ["latitude", "longitude"]:
        out[col] = pd.to_numeric(_clean_str(df[col]), errors="coerce")
    bad_geo = (
        (out["latitude"].abs() < 1e-6) | (out["longitude"].abs() < 1e-6)
        | out["latitude"].isna() | out["longitude"].isna()
        | (out["latitude"] < BLR_BBOX["lat_min"]) | (out["latitude"] > BLR_BBOX["lat_max"])
        | (out["longitude"] < BLR_BBOX["lon_min"]) | (out["longitude"] > BLR_BBOX["lon_max"])
    )
    out["geo_valid"] = ~bad_geo

    # coarse spatial keys
    out["corridor"] = _clean_str(df["corridor"]).fillna("Non-corridor")
    out["zone"] = _clean_str(df["zone"]).fillna("unknown")
    out["junction"] = _clean_str(df["junction"]).fillna("unknown")
    out["address"] = _clean_str(df["address"]).fillna("unknown")  # 100% populated, unlike junction
    out["police_station"] = _clean_str(df["police_station"]).fillna("unknown")

    # impact labels
    pr = _clean_str(df["priority"]).str.lower()
    out["priority"] = pr.where(pr.isin(["high", "low"]))  # NA for the 2 bad rows
    out["is_high_priority"] = (out["priority"] == "high")

    rc = _clean_str(df["requires_road_closure"]).str.upper()
    out["requires_road_closure"] = rc.map({"TRUE": True, "FALSE": False})

    # timestamps
    start = _parse_dt(df["start_datetime"])
    resolved = _parse_dt(df["resolved_datetime"])
    closed = _parse_dt(df["closed_datetime"])
    end = _parse_dt(df["end_datetime"])
    modified = _parse_dt(df["modified_datetime"])
    out["start_datetime"] = start

    # best-available end time, with a confidence flag
    end_best = resolved.copy()
    src = pd.Series(np.where(resolved.notna(), "resolved", None), index=df.index, dtype="object")
    for name, col in [("closed", closed), ("end", end), ("modified", modified)]:
        take = end_best.isna() & col.notna()
        end_best = end_best.mask(take, col)
        src = src.mask(take & src.isna(), name)
    out["end_best_datetime"] = end_best
    out["duration_source"] = src
    out["duration_low_conf"] = src.eq("modified")  # only modified_datetime available

    dur_min = (end_best - start).dt.total_seconds() / 60.0
    dur_min = dur_min.where(dur_min >= 0)            # drop negatives
    dur_min = dur_min.clip(upper=48 * 60)            # cap at 48h
    out["duration_min"] = dur_min

    out["status"] = _clean_str(df["status"]).str.lower()
    out["veh_type"] = _clean_str(df["veh_type"]).fillna("none")

    # require a valid start time for any time-aware modeling
    out = out[out["start_datetime"].notna()].copy()
    return out.reset_index(drop=True)


def main() -> None:
    df = load_raw()
    clean_df = clean(df)
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_parquet(OUT_PARQUET, index=False)

    n = len(clean_df)
    print(f"Rows in  : {len(df)}")
    print(f"Rows out : {n}  -> {OUT_PARQUET.relative_to(ROOT)}")
    print(f"Date range: {clean_df['start_datetime'].min()}  ->  {clean_df['start_datetime'].max()}")
    print(f"geo_valid : {clean_df['geo_valid'].mean():.1%}")
    print(f"priority known: {clean_df['priority'].notna().mean():.1%}  | high rate: {clean_df['is_high_priority'].mean():.1%}")
    print(f"road_closure known: {clean_df['requires_road_closure'].notna().mean():.1%}  | true rate: {clean_df['requires_road_closure'].mean():.1%}")
    print(f"duration present: {clean_df['duration_min'].notna().mean():.1%}  | median: {clean_df['duration_min'].median():.1f} min")
    print(f"  duration source counts:\n{clean_df['duration_source'].value_counts(dropna=False).to_string()}")


if __name__ == "__main__":
    main()
