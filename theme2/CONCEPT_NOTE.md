# GridLock — Event-Driven Congestion Forecasting & Resource Optimizer

**One-line pitch:** A data-driven decision-support system that learns from Bengaluru's historical
traffic-event log to **forecast the impact of planned and unplanned events** and **recommend optimal
manpower, barricading, and diversion plans** — closing the loop that today is purely experience-driven.

> Submission for the Flipkart GridLock challenge — Theme 2: *Event-Driven Congestion (Planned &
> Unplanned).* Built on the real **ASTraM event dataset** (8,173 Bengaluru traffic events, Nov 2023 –
> Apr 2024). Full technical detail in [`ARCHITECTURE.md`](./ARCHITECTURE.md); execution steps in
> [`build.md`](./build.md).

---

## 1. The problem

Political rallies, festivals, sports events, construction, breakdowns, and sudden gatherings create
**localized traffic breakdowns**. Today this is hard because:

- **Impact is not quantified in advance** — nobody knows how bad an event will be before it happens.
- **Resource deployment is experience-driven** — manpower, barricades, and diversions are decided by
  gut feel, not data.
- **There is no post-event learning system** — the same mistakes repeat; the city never gets smarter.

## 2. The opportunity in the data

The ASTraM log already contains everything needed to fix all three gaps:

| What the brief needs | What the data provides |
|----------------------|------------------------|
| Quantify impact | `priority` (High/Low), `requires_road_closure`, and clearance **duration** (start → resolved) — trainable impact labels |
| Spatial targeting | `corridor`, `zone`, `junction`, lat/long — 8k geocoded events |
| Temporal patterns | `start_datetime` over 5 months — hour-of-day, day-of-week, seasonality |
| Event semantics | `event_type` (planned/unplanned), `event_cause` (public_event, procession, vip_movement, protest, construction, accident, breakdown…) |
| Resource context | `police_station`, `assigned_to_police_id`, `route_path`, `direction` |

> **Honest framing:** this is *incident-report* data, not vehicle-flow/speed data. So we predict
> **disruption impact** (severity, road-closure need, clearance time, and where/when events cluster),
> not raw vehicle counts. These are precisely the quantities a deployment plan is built from.

## 3. Proposed solution — three engines + a learning loop

```
Historical ASTraM events ─┐
Upcoming/known events ─────┼──▶ [1] Impact Forecasting ──▶ [2] Resource Recommendation ──▶ Plan
Real-time incident feed ───┘            │                            │
                                        └──────── [3] Post-Event Learning Loop ◀───── actuals
```

1. **Impact Forecasting Engine** — two complementary models:
   - **Event-impact model:** given an event's attributes (type, cause, corridor, location, time),
     predict its **severity (priority)**, **probability it needs road closure**, and **expected
     clearance duration**.
   - **Spatio-temporal hotspot forecaster:** predict the **event load** (how many / how severe) per
     corridor/zone per time window, so resources can be pre-positioned before trouble starts.

2. **Resource Recommendation Engine** — turns forecasts into an **actionable plan**: how much
   **manpower** to deploy per zone/junction, where **barricading** is needed (from road-closure
   predictions), and which **diversions** to pre-plan (from corridor/route data) — solved as a
   constrained allocation, not a guess.

3. **Post-Event Learning Loop** — when an event closes, the actual severity, duration, and resources
   used are logged and fed back to retrain the models. This is the "post-event learning system" the
   brief says is missing today.

## 4. Key innovations

1. **Dual-resolution risk surface.** We fuse *per-event* impact prediction with a *spatio-temporal*
   hotspot forecast into a single map of "where and when congestion risk is highest" — richer than
   either model alone.
2. **Prediction → optimization, not just dashboards.** Most analytics stop at a chart. We convert
   forecasts into a concrete **manpower / barricade / diversion plan** via an optimization step that
   respects limited resources per zone.
3. **What-if event simulator.** Planners enter a known upcoming event (e.g. *"cricket match at
   Chinnaswamy Stadium, 7 PM"* — which is literally in the data) and instantly get predicted impact +
   a recommended deployment plan, *before* the event.
4. **Closed-loop, self-improving.** Every resolved event updates the models, so accuracy compounds
   over time — directly addressing the "no post-event learning" gap.

## 5. How each engine works (summary)

| Engine | Inputs | Output | Method |
|--------|--------|--------|--------|
| Event-impact | event_type, cause, corridor, zone, hour, day-of-week, location | priority class, road-closure prob, duration (min) | Gradient-boosted trees (LightGBM): 2 classifiers + 1 regressor |
| Hotspot forecast | event history aggregated per corridor/zone × time bucket | predicted event count & severity per window | Time-series with lag/calendar features (LightGBM / Prophet) |
| Resource recommendation | forecasted load + severity + road-closure per zone, available manpower | manpower per zone, barricade list, diversion suggestions | Rule layer + optimization (OR-Tools / PuLP) |
| Learning loop | actual vs predicted on closed events | retrained models + error tracking | scheduled retrain + drift metrics |

Full model specs, features, and the optimization formulation are in
[`ARCHITECTURE.md`](./ARCHITECTURE.md).

## 6. What the user sees (dashboard)

- **Hotspot map** — corridors/zones colored by forecasted risk for a chosen time window.
- **Event planner / what-if** — enter an upcoming event → impact prediction + recommended plan.
- **Deployment board** — manpower per zone, barricade points, diversion routes.
- **Analytics** — historical trends, top corridors, cause breakdown, model accuracy over time.

## 7. Evaluation plan

| Component | Metrics |
|-----------|---------|
| Severity classifier (priority) | Accuracy, Precision, Recall, F1, ROC-AUC |
| Road-closure classifier | Precision/Recall (imbalanced — 676/8173 positives), PR-AUC |
| Duration regressor | MAE, RMSE (report median too — distribution is skewed) |
| Hotspot forecaster | MAE/RMSE on counts; Precision@K for top-K predicted hotspots |
| Resource recommendation | back-test vs history: % of High-priority events covered, response adequacy |

All validated with **time-based splits** (train on earlier months, test on later) to avoid leakage.

## 8. Data realities & how we handle them

- **Severe class imbalance** (unplanned ≫ planned; breakdowns dominate) → class weights, PR-focused
  metrics, stratification.
- **Sparse duration** (`resolved_datetime` often NULL) → derive duration from the best available of
  `resolved/closed/end/modified` timestamps; model missingness explicitly.
- **Mixed-language free text** (`description` in Kannada/English) → optional NLP feature; not required
  for the core models.
- **Anonymized PII** (`[PERSON]`, `[PHONE]`, `[LOCATION]`) → already redacted; we use structured
  fields, not raw text identifiers.
- **No flow/speed data** → impact is modeled via severity/closure/duration proxies, stated honestly.

## 9. Why this wins

It is **real-data-grounded** (8k actual Bengaluru events, not a toy demo), it produces an **actionable
plan** rather than just predictions, it includes the **self-learning loop** the brief explicitly calls
out as missing, and the **what-if simulator** makes the value obvious to a judge in one click.

## 10. Roadmap

| Phase | Scope |
|-------|-------|
| **Phase 1** | Data cleaning + EDA + feature engineering; event-impact models (severity, closure, duration). |
| **Phase 2** | Spatio-temporal hotspot forecaster; combined risk surface. |
| **Phase 3** | Resource recommendation (optimization) + what-if simulator; Streamlit dashboard with maps. |
| **Phase 4** | Post-event learning loop + drift tracking; evaluation report; packaging. |

---

*Architecture & models: [`ARCHITECTURE.md`](./ARCHITECTURE.md) · Execution steps: [`build.md`](./build.md)*
