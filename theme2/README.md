# GridLock — Event-Driven Congestion Forecasting & Resource Optimizer

Data-driven decision support that **forecasts the impact of planned & unplanned traffic events** and
**recommends manpower / barricading / diversion plans**, with a **post-event learning loop**. Built on
the real **ASTraM event log** (8,173 Bengaluru events, Nov 2023 – Apr 2024).

> Flipkart GridLock — Theme 2: *Event-Driven Congestion (Planned & Unplanned).*
> Design docs: [`CONCEPT_NOTE.md`](./CONCEPT_NOTE.md) · [`ARCHITECTURE.md`](./ARCHITECTURE.md) · [`build.md`](./build.md)

## What's built (working code)

| Module | Purpose |
|--------|---------|
| `src/clean.py` | Parse CSV, derive `duration_min`, normalize causes, geo-validate → `data/clean_events.parquet` |
| `src/features.py` | Event-level + (corridor × time-bucket) panel features with lags |
| `src/impact_models.py` | LightGBM: severity, road-closure, clearance-duration (time-split) |
| `src/hotspot.py` | Spatio-temporal event-load forecaster (corridor × 3h) |
| `src/recommend.py` | OR-Tools manpower allocation + barricade flags + diversion lookup |
| `src/serve.py` | Load models, score a single/hypothetical event |
| `src/eval.py` | Consolidated metrics + EDA → `reports/EVALUATION.md` |
| `api/main.py` | FastAPI: `/predict_event`, `/recommend_manpower`, `/diversions/{corridor}` |
| `dashboard/app.py` | Streamlit: what-if planner, hotspot map, analytics |

## Setup (uses the in-repo venv on D: — nothing installed to C:)

```bash
# from theme2/
../.venv/Scripts/python.exe -m pip install -r requirements.txt
```

## Run

```bash
# full offline pipeline: clean -> features -> models -> hotspot -> eval
../.venv/Scripts/python.exe run_pipeline.py

# API
../.venv/Scripts/python.exe -m uvicorn api.main:app --port 8000      # http://127.0.0.1:8000/docs

# dashboard
../.venv/Scripts/python.exe -m streamlit run dashboard/app.py
```

## Results (held-out test, train < 2024-03-01)

> Leakage control: time-based split + **5-fold out-of-fold target encoding** for corridor priors
> (no row sees its own target). Details in `reports/EVALUATION.md`.


- **Road-closure** model: PR-AUC ≈ 0.34 vs 0.10 base rate (~3.4× better than random).
- **Clearance duration**: median absolute error ≈ 68 min (labels are noisy — mostly from `modified_datetime`).
- **Hotspot forecaster**: beats last-week persistence baseline; Precision@10 ≈ 0.51 on top hotspots.
- **Severity** (`priority`) is ~99.9% a corridor-based operational rule — captured near-perfectly, and
  documented honestly as such in [`reports/EVALUATION.md`](./reports/EVALUATION.md).

## Honest data notes

This is **incident-report** data, not vehicle-flow data → impact is modeled via
severity / road-closure / clearance-duration proxies. Duration is derived from the best available
timestamp and flagged when low-confidence. See `CONCEPT_NOTE.md` §8.
