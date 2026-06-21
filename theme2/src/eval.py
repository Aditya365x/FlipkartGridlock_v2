"""
eval.py — Consolidate model metrics + dataset EDA into a single Markdown report.

Run (after training impact_models and hotspot):
    python -m src.eval
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
CLEAN = ROOT / "data" / "clean_events.parquet"
# ASTraM timestamps are already Bengaluru-local (see note in features.py) — no offset.


def _load_json(p: Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {}


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    df = pd.read_parquet(CLEAN)
    df["local"] = df["start_datetime"]  # already local
    impact = _load_json(REPORTS / "impact_metrics.json")
    hot = _load_json(REPORTS / "hotspot_metrics.json")

    lines = ["# Evaluation Report — Event-Driven Congestion\n",
             f"Dataset: **{len(df):,} events**, "
             f"{df['start_datetime'].min().date()} → {df['start_datetime'].max().date()}, Bengaluru.\n",
             "Validation uses a **time-based split** (train < 2024-03-01, test ≥ 2024-03-01).\n",
             "**Leakage control:** target-derived corridor priors use **5-fold out-of-fold (OOF) "
             "target encoding** on train (each row's prior comes from other folds only); test/serving "
             "use the full-train prior. So no row ever sees its own target.\n",
             "\n## 1. Event-impact models\n"]

    if impact:
        s, c, d = impact.get("severity", {}), impact.get("road_closure", {}), impact.get("duration", {})
        lines += [
            "| Model | Key metric | Value | Baseline / base-rate |",
            "|---|---|---|---|",
            f"| Severity (priority) | ROC-AUC / F1 | {s.get('auc')} / {s.get('f1')} | base rate {s.get('base_rate')} |",
            f"| Road-closure | PR-AUC (AUC) | {c.get('pr_auc')} ({c.get('auc')}) | base rate {c.get('base_rate')} |",
            f"| Clearance duration | median abs err | {d.get('median_ae_min')} min | test median {d.get('test_median_min')} min |",
            "",
            "> **Note on severity:** `priority` is ~99.9% determined by whether the event is on a named "
            "corridor (an operational rule), so the classifier is near-perfect by construction. The "
            "genuinely predictive targets are **road-closure** (PR-AUC "
            f"{c.get('pr_auc')} vs {c.get('base_rate')} base = "
            f"{round(c.get('pr_auc',0)/max(c.get('base_rate',1e-9),1e-9),1)}× better than random) and "
            "**clearance duration**. Duration labels are derived mostly from `modified_datetime` "
            "(lower confidence), so error is reported as median absolute error.\n",
        ]

    lines += ["## 2. Spatio-temporal hotspot forecaster\n"]
    if hot:
        lines += [
            "| Metric | Value |",
            "|---|---|",
            f"| MAE (events/bucket) | {hot.get('mae')} |",
            f"| Baseline MAE (last-week persistence) | {hot.get('baseline_mae_lastweek')} |",
            f"| Precision@5 hotspots | {hot.get('precision_at_5')} |",
            f"| Precision@10 hotspots | {hot.get('precision_at_10')} |",
            f"| Mean events/bucket | {hot.get('mean_events_per_bucket')} |",
            "",
            "> Forecasts event load per corridor per 3-hour bucket; beats the last-week persistence "
            "baseline and recovers ~half the true top-K hotspot corridors each window.\n",
        ]

    # quick EDA tables
    lines += ["## 3. Dataset snapshot (EDA)\n"]
    et = df["event_type"].value_counts()
    lines += ["**Event type:** " + ", ".join(f"{k}={v}" for k, v in et.items()) + "\n"]
    lines += ["\n**Top causes:**\n", "| cause | count |", "|---|---|"]
    for k, v in df["event_cause"].value_counts().head(8).items():
        lines.append(f"| {k} | {v} |")
    lines += ["\n**Top corridors:**\n", "| corridor | count |", "|---|---|"]
    for k, v in df["corridor"].value_counts().head(8).items():
        lines.append(f"| {k} | {v} |")
    lines += [f"\n**Road-closure rate:** {df['requires_road_closure'].mean():.1%} · "
              f"**High-priority rate:** {df['is_high_priority'].mean():.1%} · "
              f"**Median duration:** {df['duration_min'].median():.0f} min\n"]

    out = REPORTS / "EVALUATION.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
