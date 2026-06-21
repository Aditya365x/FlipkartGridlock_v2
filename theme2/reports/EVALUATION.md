# Evaluation Report — Event-Driven Congestion

Dataset: **8,173 events**, 2023-11-09 → 2024-04-08, Bengaluru.

Validation uses a **time-based split** (train < 2024-03-01, test ≥ 2024-03-01).

**Leakage control:** target-derived corridor priors use **5-fold out-of-fold (OOF) target encoding** on train (each row's prior comes from other folds only); test/serving use the full-train prior. So no row ever sees its own target.


## 1. Event-impact models

| Model | Key metric | Value | Baseline / base-rate |
|---|---|---|---|
| Severity (priority) | ROC-AUC / F1 | 1.0 / 0.999 | base rate 0.6048 |
| Road-closure | PR-AUC (AUC) | 0.320 (0.765) | base rate 0.0998 |
| Road-closure (operating point) | recall / precision | 0.58 / 0.26 @ tuned thr 0.14 (vs 0.45 / 0.35 @ 0.5) | isotonic-calibrated |
| Impact duration | MAE / median abs err | 116.6 / 47.9 min | test median 116.6 min |

> **Note on severity:** `priority` is ~99.9% determined by whether the event is on a named corridor (an operational rule), so the classifier is near-perfect by construction. The genuinely predictive targets are **road-closure** (PR-AUC 0.3376 vs 0.0998 base = 3.4× better than random) and **impact duration**.
>
> **Note on road-closure:** probabilities are **isotonic-calibrated** (a shown 60% means ~60% empirically), and the barricade decision uses an **F1.5-tuned operating threshold (0.14)** chosen on out-of-fold train predictions — recall-leaning because missing a real closure is costlier than a false barricade (recall 0.45→0.58). Added domain features (is_holiday, week_of_year, OOF corridor-closure-rate) left ranking flat (PR-AUC ~0.32, within noise) — this dataset has limited closure signal; the honest gains are calibration + the tuned operating point, not raw AUC.
>
> **Note on duration:** the label is censored — 696 events (8.5%) are pinned at exactly 48h (defaulted/missing end-times). These artifact rows are **excluded** from training and evaluation, which cut MAE from 379→117 min. "Duration" is the event's traffic-impact window (long for planned public events/processions, short for accidents), not incident clean-up time.

## 2. Spatio-temporal hotspot forecaster

| Metric | Value |
|---|---|
| MAE (events/bucket) | 0.3996 |
| Baseline MAE (last-week persistence) | 0.4661 |
| Precision@5 hotspots | 0.4714 |
| Precision@10 hotspots | 0.5133 |
| Mean events/bucket | 0.3792 |

> Forecasts event load per corridor per 3-hour bucket; beats the last-week persistence baseline and recovers ~half the true top-K hotspot corridors each window.

## 3. Dataset snapshot (EDA)

**Event type:** unplanned=7706, planned=467


**Top causes:**

| cause | count |
|---|---|
| vehicle_breakdown | 4896 |
| others | 638 |
| pot_holes | 537 |
| construction | 480 |
| water_logging | 458 |
| accident | 365 |
| tree_fall | 284 |
| road_conditions | 170 |

**Top corridors:**

| corridor | count |
|---|---|
| Non-corridor | 3144 |
| Mysore Road | 743 |
| Bellary Road 1 | 610 |
| Tumkur Road | 458 |
| Bellary Road 2 | 379 |
| Hosur Road | 298 |
| ORR North 1 | 275 |
| Old Madras Road | 263 |

**Road-closure rate:** 8.3% · **High-priority rate:** 61.6% · **Median duration:** 127 min
