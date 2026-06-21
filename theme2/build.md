# BUILD PLAN — Event-Driven Congestion Forecasting & Resource Optimizer

Theme 2. Data: `Astram event data_anonymized ...csv` (8,173 Bengaluru events, Nov 2023 – Apr 2024).
CPU only (no GPU needed). Follow top to bottom.

---

## 0. Tech stack (final)

| Layer | Tech |
|-------|------|
| Language | Python 3.11+ |
| ETL / data | pandas, NumPy |
| ML | LightGBM, scikit-learn |
| Time-series baseline | Prophet or statsforecast |
| Geospatial | geopandas, shapely, h3 |
| Optimization | OR-Tools (or PuLP) |
| Explainability | SHAP |
| API | FastAPI + Uvicorn |
| Dashboard | Streamlit + pydeck/folium |
| Storage | SQLite/PostgreSQL + Parquet |
| Packaging | Docker |

`requirements.txt`: pandas numpy lightgbm scikit-learn prophet geopandas shapely h3 ortools shap fastapi uvicorn streamlit pydeck folium joblib

---

## 1. Repo structure (create)

```
theme2/
├─ data/
│  └─ raw/Astram event data...csv        # the dataset (already here)
├─ notebooks/01_eda.ipynb                # exploration
├─ src/
│  ├─ clean.py            # parse timestamps, derive duration, normalize causes, geo-validate
│  ├─ features.py         # temporal + spatial(H3) + event + lag/rolling features
│  ├─ impact_models.py    # severity / road-closure classifiers + duration regressor
│  ├─ hotspot.py          # spatio-temporal load forecaster
│  ├─ risk_surface.py     # fuse per-event impact + area load
│  ├─ recommend.py        # manpower optimization + barricade + diversion
│  ├─ learning_loop.py    # store predictions, compare to actuals, retrain, drift
│  └─ eval.py             # time-split metrics for all models
├─ api/main.py            # FastAPI: /predict_event, /forecast, /recommend
├─ dashboard/app.py       # Streamlit: hotspot map, what-if, deployment board
├─ models/                # saved models (gitignored)
├─ configs/
│  ├─ resources.yaml      # available officers/barricades per zone (assumptions)
│  └─ cause_map.yaml      # event_cause normalization
├─ requirements.txt
└─ Dockerfile
```

---

## 2. Build phases (in order)

### Phase 0 — Data cleaning + EDA
- [ ] Load CSV with pandas (`dtype=str` then parse) — handle `NULL`/empty.
- [ ] `clean.py`: parse all datetimes; build `duration_min` = coalesce(resolved, closed, end, modified) − start, clip [0, 48h], flag low-confidence.
- [ ] Normalize `event_cause` (case/spelling) via `configs/cause_map.yaml`.
- [ ] Geo-validate (drop lat/long=0 for spatial models; keep corridor/zone as coarse key).
- [ ] EDA notebook: distributions, time patterns (hour/dow), top corridors/zones, cause × priority, duration distribution. **Confirms the story for judges.**

### Phase 1 — Features + event-impact models
- [ ] `features.py`: temporal (hour, dow, weekend, month, festival flag), spatial (corridor, zone, junction, H3 cell), event (type, cause, is_event_driven), context (corridor avg duration, zone High-rate).
- [ ] `impact_models.py`:
  - [ ] Severity classifier (`priority`) — LightGBM, class-weighted.
  - [ ] Road-closure classifier (`requires_road_closure`) — LightGBM, `scale_pos_weight` (~11:1).
  - [ ] Duration regressor (`duration_min`, log-target) — LightGBM.
- [ ] SHAP explanations for each.
- [ ] **Time-based split** (train ≤ Feb 2024, test Mar–Apr 2024).

### Phase 2 — Spatio-temporal hotspot forecaster
- [ ] `hotspot.py`: aggregate events to (spatial key × time bucket); build lag/rolling features; train global LightGBM forecaster; Prophet baseline per top corridor.
- [ ] Output forecasted load per cell for next horizon.
- [ ] `risk_surface.py`: fuse per-event impact + area load into one scored surface.

### Phase 3 — Resource recommendation
- [ ] `configs/resources.yaml`: assumed officers/barricades per zone.
- [ ] `recommend.py`:
  - [ ] Manpower: OR-Tools LP maximizing severity-weighted coverage under capacity (greedy fallback).
  - [ ] Barricade: flag events with road_closure_prob ≥ τ → barricade list.
  - [ ] Diversion: retrieve historical `route_path`/`direction` for similar past events on that corridor.

### Phase 4 — Learning loop + serving
- [ ] `learning_loop.py`: store predictions at event start; on closure compare vs actual; track error/drift; scheduled retrain.
- [ ] `api/main.py`: `/predict_event` (impact for one event), `/forecast` (hotspots), `/recommend` (plan).
- [ ] `dashboard/app.py`:
  - [ ] Hotspot map (pydeck/folium) colored by risk for a chosen window.
  - [ ] **What-if simulator**: enter event (type, cause, corridor, time) → impact + plan.
  - [ ] Deployment board: manpower per zone, barricade points, diversions.
  - [ ] Analytics + model-accuracy-over-time panel.

### Phase 5 — Eval + package
- [ ] `eval.py`: all metrics (Phase-by-phase, §11 of ARCHITECTURE) on time splits.
- [ ] Dockerize; one command runs API + dashboard.

---

## 3. Targets & labels (from the data)

| Model | Label column | Notes |
|-------|-------------|-------|
| Severity | `priority` (High/Low) | 5030/3141 — mild imbalance |
| Road-closure | `requires_road_closure` (T/F) | 676/7497 — strong imbalance, weight it |
| Duration | derived `duration_min` | sparse/skewed — log-target, report median AE |
| Hotspot load | aggregated event count per cell×time | derived |

---

## 4. Definition of done

- Impact models predict severity, road-closure, and duration on held-out future months with reported P/R/F1/AUC and MAE/RMSE.
- Hotspot forecaster produces a per-corridor/zone risk surface with backtested error.
- Recommender outputs manpower per zone + barricade list + diversions for a given time window.
- What-if simulator returns impact + plan for a typed-in event (demo the Chinnaswamy cricket match).
- Learning-loop panel shows accuracy tracked over time.
- `docker` run launches API + Streamlit dashboard.

---

## 5. Start now (first 5 moves)

1. Create structure (§1) + `requirements.txt`; `pip install`.
2. `clean.py` → produce a clean Parquet (`duration_min` derived, causes normalized).
3. EDA notebook → confirm temporal/spatial patterns (also your demo visuals).
4. `features.py` + severity classifier end-to-end with a time split → first metric.
5. Expand to road-closure + duration, then Phases 2→5.
