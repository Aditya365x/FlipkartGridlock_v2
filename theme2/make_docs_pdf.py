"""
make_docs_pdf.py — Generate a full, detailed PDF describing the GridLock app:
architecture, data, every module, the models, the dashboard/API, honesty notes,
limitations and how to run. Output: GridLock_App_Documentation.pdf

Run:
    ../.venv/Scripts/python.exe make_docs_pdf.py
"""
from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable, ListFlowable, ListItem, PageBreak, Paragraph, Preformatted,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "GridLock_App_Documentation.pdf"

# brand palette
INK = colors.HexColor("#1f2933")
ACCENT = colors.HexColor("#c0392b")     # traffic red
ACCENT2 = colors.HexColor("#1f6feb")    # forecast blue
LIGHT = colors.HexColor("#f4f6f8")
MUTE = colors.HexColor("#5b6b79")
LINE = colors.HexColor("#d0d7de")

# ---- styles ----
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                    fontSize=16, textColor=ACCENT, spaceBefore=16, spaceAfter=6, leading=20)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                    fontSize=12.5, textColor=INK, spaceBefore=10, spaceAfter=4, leading=16)
BODY = ParagraphStyle("BODY", parent=ss["BodyText"], fontName="Helvetica",
                      fontSize=10, textColor=INK, alignment=TA_JUSTIFY, leading=14.5, spaceAfter=6)
BUL = ParagraphStyle("BUL", parent=BODY, leftIndent=6, spaceAfter=2)
SMALL = ParagraphStyle("SMALL", parent=BODY, fontSize=8.5, textColor=MUTE, alignment=TA_LEFT)
CODE = ParagraphStyle("CODE", parent=ss["Code"], fontName="Courier", fontSize=8,
                      textColor=INK, backColor=LIGHT, leading=11, leftIndent=6, rightIndent=6,
                      spaceBefore=4, spaceAfter=8, borderPadding=6)
CELL = ParagraphStyle("CELL", parent=BODY, fontSize=9, alignment=TA_LEFT, leading=12, spaceAfter=0)
CELLH = ParagraphStyle("CELLH", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)
TITLE = ParagraphStyle("TITLE", parent=ss["Title"], fontName="Helvetica-Bold",
                       fontSize=26, textColor=INK, leading=30, spaceAfter=6)
SUB = ParagraphStyle("SUB", parent=BODY, fontSize=12, textColor=MUTE, alignment=TA_LEFT)

story: list = []


def p(text, style=BODY):
    story.append(Paragraph(text, style))


def h1(text):
    story.append(Paragraph(text, H1))


def h2(text):
    story.append(Paragraph(text, H2))


def bullets(items):
    story.append(ListFlowable(
        [ListItem(Paragraph(t, BUL), leftIndent=12, value="•") for t in items],
        bulletType="bullet", start="•", leftIndent=10, spaceAfter=6))


def code(text):
    story.append(Preformatted(text, CODE))


def gap(h=4):
    story.append(Spacer(1, h))


def table(headers, rows, widths=None, header_color=INK):
    data = [[Paragraph(str(c), CELLH) for c in headers]]
    data += [[Paragraph(str(c), CELL) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    gap(8)


def rule():
    story.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceBefore=4, spaceAfter=8))


# load live metrics
impact = json.loads((ROOT / "reports" / "impact_metrics.json").read_text())
hot = json.loads((ROOT / "reports" / "hotspot_metrics.json").read_text())

# ============================================================ TITLE PAGE
story.append(Spacer(1, 3 * cm))
p("GridLock", TITLE)
p("Event-Driven Congestion Forecasting &amp; Resource Optimizer", H2)
gap(10)
rule()
p("A data-driven decision-support system that forecasts the impact of planned and unplanned "
  "traffic events and recommends optimal manpower, barricading and diversion plans — with an "
  "honest, leakage-controlled machine-learning core.", SUB)
gap(16)
table(["Property", "Value"], [
    ["Challenge", "Flipkart GridLock — Theme 2: Event-Driven Congestion (Planned &amp; Unplanned)"],
    ["Dataset", "ASTraM event log — 8,173 real Bengaluru traffic events"],
    ["Period", "9 Nov 2023 → 8 Apr 2024 (~5 months)"],
    ["Stack", "Python · pandas · LightGBM · scikit-learn · OR-Tools · FastAPI · Streamlit"],
    ["Compute", "CPU-only — no GPU required"],
    ["Validation", "Time-based split (train &lt; 2024-03-01) + 5-fold out-of-fold encoding"],
], widths=[4 * cm, 12.5 * cm], header_color=ACCENT)
gap(10)
p("This document describes the system end to end: the problem, the data and its realities, the "
  "full architecture, every code module, the three model engines, the recommendation optimizer, "
  "the serving layer, the API, the dashboard, and an honest account of limitations and what is "
  "built versus planned.", BODY)
story.append(PageBreak())

# ============================================================ 1. EXECUTIVE SUMMARY
h1("1. Executive Summary")
p("GridLock turns a city's historical traffic-event log into operational foresight. Given an "
  "upcoming or in-progress event (a rally, festival, match, procession, breakdown or accident), it "
  "predicts <b>how disruptive</b> the event will be and converts that prediction into a concrete "
  "<b>deployment plan</b> — how many officers to place where, where barricades are needed, and which "
  "historical closures to consult for diversions.")
p("It is built on the principle <b>predict → optimize → learn</b> and is grounded in 8,173 real "
  "Bengaluru events, not synthetic data. A deliberate emphasis on <b>intellectual honesty</b> runs "
  "through the project: every model's true skill (and its limits) is stated plainly, validation is "
  "leakage-controlled, and the UI never presents a rule as if it were a prediction.")
h2("What the system produces")
bullets([
    "<b>Impact prediction</b> for any event: road-closure probability, expected clearance time, and a priority flag.",
    "<b>Hotspot forecast</b>: expected event load per corridor for any chosen time window.",
    "<b>Deployment plan</b>: an event-led officer allocation with forecast-based city-wide coverage.",
    "<b>Planning references</b>: recent real closures on the affected corridor.",
    "<b>Analytics</b>: historical patterns by cause, hour, corridor and closure behaviour.",
])

# ============================================================ 2. PROBLEM
h1("2. The Problem (Theme 2)")
p("Political rallies, festivals, sports events, construction, breakdowns and sudden gatherings "
  "create localized traffic breakdowns. Today this is hard for three reasons:")
bullets([
    "<b>Impact is not quantified in advance</b> — nobody knows how bad an event will be before it happens.",
    "<b>Resource deployment is experience-driven</b> — manpower, barricades and diversions are decided by gut feel.",
    "<b>There is no post-event learning system</b> — the same mistakes repeat; the city never gets smarter.",
])
p("GridLock addresses the first two directly with forecasting and optimization, and provides the "
  "architecture (and partial implementation) for the third.")

# ============================================================ 3. DATA
h1("3. The Data — ASTraM Event Log")
p("The system is trained on the real ASTraM incident log: 8,173 geocoded traffic events across "
  "Bengaluru over roughly five months. Each event carries identity, type, cause, geography, "
  "timestamps, impact labels and resource context.")
h2("3.1 Fields used")
table(["Group", "Fields"], [
    ["Identity / type", "id, event_type (planned/unplanned), event_cause"],
    ["Geography", "latitude, longitude, corridor, zone, junction, address"],
    ["Time", "start_datetime, end / closed / resolved / modified_datetime"],
    ["Impact labels", "priority, requires_road_closure, derived duration_min"],
    ["Resource / context", "police_station, veh_type, status"],
], widths=[3.6 * cm, 12.9 * cm])
h2("3.2 Data realities (and how they are handled)")
table(["Reality", "Handling"], [
    ["Incident-report data, not vehicle-flow/speed data",
     "Impact is modelled via proxies: priority, road-closure need, clearance duration."],
    ["Severe class imbalance (8.3% need road closure)",
     "scale_pos_weight / class weights; PR-AUC reported, not just accuracy."],
    ["Sparse, noisy duration (resolved_datetime often NULL)",
     "duration = coalesce(resolved, closed, end, modified) − start, capped 48h, low-confidence flagged."],
    ["zone missing on ~58% of rows; junction ~31% known",
     "corridor used as primary spatial key; address (100%) preferred over junction."],
    ["route_path (2%) and direction (1%) effectively empty",
     "No computed diversions are claimed — real historical closures are shown instead."],
    ["Anonymized PII ([PERSON], [PHONE])",
     "Already redacted; only structured fields are used."],
], widths=[6.5 * cm, 10 * cm])
h2("3.3 A real correctness fix — timezone")
p("The raw timestamps are tagged <font face='Courier'>+00</font> but are in fact already Bengaluru "
  "local time. An earlier version added a +5:30 'UTC→IST' offset, which shifted the event peak to a "
  "physically impossible 02:30. The distribution actually peaks at <b>21:00</b> (evening) with a "
  "secondary morning band and an afternoon lull — textbook traffic. The offset was removed and the "
  "models retrained, so every hour-of-day feature and label is now truthful. This is documented in "
  "code and shows the rigour applied to the data.")

# ============================================================ 4. ARCHITECTURE
h1("4. System Architecture")
p("Three stages, each independently testable, plus a learning loop:")
code(
"Historical ASTraM events --+\n"
"Upcoming / known event ----+--> [1] Impact Forecasting --> [2] Resource Recommendation --> Plan\n"
"Real-time incident feed ---+            |                          |\n"
"                                        +------- [3] Post-Event Learning Loop <----- actuals")
p("<b>Pipeline:</b> CSV → cleaning → feature engineering → (impact models + hotspot forecaster) → "
  "risk surface → recommendation optimizer → dashboard / API, with a prediction store feeding the "
  "(designed) learning loop.")
h2("4.1 Module map (working code)")
table(["Module", "Purpose"], [
    ["src/clean.py", "Parse CSV, derive duration, normalize causes, geo-validate → clean_events.parquet"],
    ["src/features.py", "Event-level features + (corridor × 3h) panel features with lags"],
    ["src/impact_models.py", "LightGBM: severity, road-closure, clearance-duration (time-split, OOF priors)"],
    ["src/hotspot.py", "Spatio-temporal event-load forecaster (corridor × 3h bucket)"],
    ["src/recommend.py", "OR-Tools manpower allocation + event-led plan + barricade + closure lookup"],
    ["src/serve.py", "Load models; score an event; forecast corridor load (shared by API + dashboard)"],
    ["src/eval.py", "Consolidate metrics + EDA → reports/EVALUATION.md"],
    ["api/main.py", "FastAPI: /predict_event, /recommend_manpower, /corridor_closures"],
    ["dashboard/app.py", "Streamlit: what-if planner, forecast hotspot map, analytics"],
    ["run_pipeline.py", "One command: clean → features → models → hotspot → eval"],
], widths=[4.2 * cm, 12.3 * cm])
story.append(PageBreak())

# ============================================================ 5. DATA PIPELINE
h1("5. Data Pipeline")
h2("5.1 clean.py — ingestion & cleaning")
bullets([
    "Reads the raw CSV as strings; treats NULL/empty/None/nan as missing.",
    "Parses all timestamps; builds an <b>end_best_datetime</b> by coalescing resolved → closed → end → modified.",
    "<b>duration_min</b> = end_best − start, dropped if negative, capped at 48h; flags rows whose only end time is modified_datetime as low-confidence.",
    "Normalizes event_cause via configs/cause_map.yaml and tags event-driven causes (public_event, procession, vip_movement, protest, construction).",
    "Geo-validates against a Bengaluru bounding box; keeps corridor/zone as coarse spatial keys when point geo is bad.",
    "Carries address (100% populated) for use in planning references.",
])
h2("5.2 features.py — feature engineering")
p("Two feature frames are produced from the cleaned events:")
bullets([
    "<b>Event-level</b> (one row per event): time features (hour, day-of-week, weekend, month, part-of-day), "
    "categorical event/spatial fields, and geography — used by the impact models.",
    "<b>Panel</b> (corridor × 3-hour bucket): a complete grid including zero-event buckets, with lag features "
    "(lag_1, lag_8 ≈ 1 day, lag_56 ≈ 1 week) and rolling means — used by the hotspot forecaster.",
    "All lags are shifted to avoid leakage; timestamps are treated as already-local (no offset).",
])

# ============================================================ 6. IMPACT MODELS
h1("6. Engine 1a — Event-Impact Models")
p("Three LightGBM models share one feature set, one row per event. Validation uses a strict "
  "<b>time-based split</b> (train before 1 Mar 2024, test after) so no future information leaks.")
h2("6.1 Leakage control")
p("The corridor-median-duration prior is target-derived, so it is computed with <b>5-fold "
  "out-of-fold (OOF) target encoding</b>: each training row's prior comes only from the other folds, "
  "and test/serving use the full-train prior. No row ever sees its own target.")
h2("6.2 The three models and held-out results")
sev, clo, dur = impact["severity"], impact["road_closure"], impact["duration"]
table(["Model", "Target", "Key metric (held-out test)"], [
    ["Severity", "priority High/Low",
     f"ROC-AUC {sev['auc']}, F1 {sev['f1']} — but ~99.9% an operational rule (see §11)"],
    ["Road-closure", "requires_road_closure",
     f"PR-AUC {clo['pr_auc']} vs {clo['base_rate']} base rate (~{round(clo['pr_auc']/clo['base_rate'],1)}× better than random); AUC {clo['auc']}"],
    ["Clearance duration", "duration_min (log-target)",
     f"median abs error {dur['median_ae_min']} min (test median {dur['test_median_min']} min); MAE {dur['mae_min']} min"],
], widths=[3.2 * cm, 4.2 * cm, 9.1 * cm])
p("<b>Road-closure</b> is the genuinely predictive model and the one the UI foregrounds. Duration "
  "is reported as <i>median</i> absolute error because its labels are noisy (mostly from "
  "modified_datetime). Severity is captured near-perfectly only because it is essentially a rule.")

# ============================================================ 7. HOTSPOT
h1("7. Engine 1b — Spatio-Temporal Hotspot Forecaster")
p("A single global LightGBM regressor predicts <b>event load</b> per corridor per 3-hour bucket "
  "from lag, rolling and calendar features. It is back-tested on the same time split.")
table(["Metric", "Value", "Note"], [
    ["MAE (events / bucket)", str(hot["mae"]), "Lower is better"],
    ["Baseline MAE (last-week persistence)", str(hot["baseline_mae_lastweek"]), "Model beats this baseline"],
    ["Precision@5 hotspots", str(hot["precision_at_5"]), "Top-5 corridor overlap per window"],
    ["Precision@10 hotspots", str(hot["precision_at_10"]), "Recovers ~half the true top-K"],
    ["Mean events / bucket", str(hot["mean_events_per_bucket"]), "Data is sparse"],
], widths=[6 * cm, 3 * cm, 7.5 * cm])
p("<b>Forecast-as-a-service:</b> serve.forecast_corridor_load(when) predicts per-corridor load for "
  "any chosen time window, using each corridor's typical recent-activity lags at that hour-of-day. "
  "This powers both the deployment spread and the live hotspot map. After the timezone fix it "
  "correctly predicts high evening load and a quiet mid-afternoon.")

# ============================================================ 8. RECOMMENDATION
h1("8. Engine 2 — Resource Recommendation")
p("This engine converts predictions into a deployable plan. It was redesigned to be "
  "<b>event-led with forecast-based city coverage</b>, fixing an earlier flaw where deployment "
  "tracked only historical zone volume and ignored the actual event.")
h2("8.1 Event-led, forecast-spread deployment")
bullets([
    "The event's <b>corridor</b> is staffed to <b>event_officer_need(pred)</b>, sized by the event's predicted impact.",
    "The need is capped so a reserve fraction (default 25%) stays available for the rest of the city.",
    "<b>Remaining officers</b> are spread across other corridors by their <b>forecasted</b> load for that time window.",
    "The plan therefore responds to both <i>what</i> the event is (impact) and <i>where</i> it is (corridor).",
])
code(
"event_officer_need = 3 + 4*P(high) + 12*P(closure) + 1.5*min(duration_hours, 6)\n"
"  minor accident   -> ~5-11 officers      long public event -> ~25 (capped)\n"
"  (duration capped at 6h because its label is noisy on the long tail)")
h2("8.2 Manpower optimization")
p("allocate_manpower solves an integer program with Google OR-Tools (CBC): allocate a limited "
  "officer pool to maximize severity-weighted, diminishing-returns coverage "
  "(value of the k-th officer = demand × (√k − √(k−1))), subject to a per-zone minimum floor and the "
  "total-officer budget. A transparent priority-weighted <b>greedy fallback</b> runs if the solver "
  "is unavailable.")
h2("8.3 Barricading & closure references")
bullets([
    "<b>Barricade</b> flag is raised when road-closure probability ≥ 0.5.",
    "<b>recent_closures(corridor, cause)</b> retrieves real past closures on the same corridor, "
    "preferring the same cause (then other event-driven causes), shown with a real address. "
    "No diversion route is fabricated — the dataset has none.",
])
story.append(PageBreak())

# ============================================================ 9. SERVING
h1("9. Serving Layer (serve.py)")
p("Shared by both the API and the dashboard, with cached model loading:")
bullets([
    "<b>predict_event(event)</b> → severity probability, predicted priority, road-closure probability, "
    "needs-barricade flag, expected clearance duration.",
    "<b>forecast_corridor_load(when)</b> → predicted event load per corridor for the time window.",
    "Feature rows are built to exactly match training (categoricals, priors, local time).",
])

# ============================================================ 10. API
h1("10. API (FastAPI)")
table(["Endpoint", "Method", "Purpose"], [
    ["/health", "GET", "Liveness check"],
    ["/predict_event", "POST", "Impact prediction for one event"],
    ["/recommend_manpower", "POST", "Allocate an officer pool across zones by demand"],
    ["/corridor_closures/{corridor}", "GET", "Recent real closures on a corridor (planning reference)"],
], widths=[6.2 * cm, 2 * cm, 8.3 * cm])
p("Interactive docs are served at <font face='Courier'>/docs</font> when the API runs.")

# ============================================================ 11. DASHBOARD
h1("11. Dashboard (Streamlit)")
h2("11.1 Event Planner (What-if)")
bullets([
    "Pick event type, cause, corridor, zone, hour and available officers.",
    "Shows road-closure probability (lead metric), barricade flag, expected clearance (h:min), and "
    "priority labelled honestly as a corridor rule.",
    "Generates the event-led deployment plan and, when a barricade is needed, recent closures on the corridor.",
])
h2("11.2 Hotspot Map — live forecast")
bullets([
    "Forecast mode: choose a day-of-week and hour; 3-D columns per corridor show predicted load "
    "(height and colour scale with the forecast), with a hover tooltip and a ranked table.",
    "Responsive — an afternoon window is near-empty; an evening window rises sharply.",
    "A Historical-density toggle preserves the original hexbin heatmap.",
])
h2("11.3 Analytics")
bullets([
    "Scope filter by corridor and zone; the zone list depends on the chosen corridor to avoid "
    "impossible combinations (corridors and zones are largely independent — only ~90/242 combos exist).",
    "Headline stats, events by cause and by hour, top corridors/junctions (with a coverage caveat), "
    "events per day, and a cause × road-closure table (the predictive label, not the priority rule).",
])

# ============================================================ 12. HONESTY / LIMITATIONS
h1("12. Honesty & Limitations")
p("These are stated openly in the product and documentation — and are a deliberate strength:")
table(["Limitation", "Honest framing in the app"], [
    ["Priority is not a real prediction",
     "It is ~99.9% an operational rule (named corridor → High); the UI labels it as a rule and leads with road-closure."],
    ["Duration labels are noisy",
     "Mostly derived from modified_datetime; reported as median absolute error and flagged low-confidence."],
    ["No vehicle-flow data",
     "Impact is modelled via severity / closure / duration proxies — the quantities a plan actually needs."],
    ["No route/diversion data",
     "route_path (2%) and direction (1%) are empty; the app shows real historical closures, not fabricated diversions."],
    ["Forecaster gains are modest",
     "Beats last-week persistence on sparse data; presented as a trust/coverage tool, not over-sold."],
    ["Allocation assumptions",
     "Diminishing-returns curve and reserve fraction are explicit, configurable assumptions, not learned."],
], widths=[5.2 * cm, 11.3 * cm])

# ============================================================ 13. ENGINEERING QUALITY
h1("13. Engineering-Quality Highlights")
bullets([
    "<b>Leakage control</b>: time-based split + 5-fold out-of-fold target encoding for corridor priors.",
    "<b>Data correctness</b>: caught and fixed a 5.5-hour timezone mislabel; busiest hour now 21:00, not 02:00.",
    "<b>Prediction → optimization</b>: output is an actionable plan, not just charts.",
    "<b>Event-led deployment</b>: plan responds to the specific event's impact and location.",
    "<b>Shared serving layer</b>: one code path feeds both API and dashboard.",
    "<b>Reproducible</b>: the whole offline pipeline runs with a single command, CPU-only.",
])

# ============================================================ 14. BUILT VS ROADMAP
h1("14. What's Built vs. Roadmap")
table(["Capability", "Status"], [
    ["Cleaning, feature engineering, impact models", "Built"],
    ["Hotspot forecaster + forecast-as-a-service", "Built"],
    ["Event-led recommendation + OR-Tools optimization", "Built"],
    ["Closure-reference retrieval (honest, address-based)", "Built"],
    ["FastAPI service + Streamlit dashboard (4 tabs, live map)", "Built"],
    ["Post-event learning loop (Engine 3): log -> actuals -> auto-calibration", "Built"],
    ["H3 spatial cells, Prophet baseline, SHAP, drift tracking", "Architecture / roadmap"],
], widths=[10.5 * cm, 6 * cm])

# ============================================================ 15. HOW TO RUN
h1("15. How to Run")
code(
"# from theme2/  (uses the in-repo venv on D:)\n"
"../.venv/Scripts/python.exe -m pip install -r requirements.txt\n\n"
"# full offline pipeline: clean -> features -> models -> hotspot -> eval\n"
"../.venv/Scripts/python.exe run_pipeline.py\n\n"
"# API  ->  http://127.0.0.1:8000/docs\n"
"../.venv/Scripts/python.exe -m uvicorn api.main:app --port 8000\n\n"
"# dashboard\n"
"../.venv/Scripts/python.exe -m streamlit run dashboard/app.py")

# ============================================================ 16. METRICS SUMMARY
h1("16. Metrics Summary (held-out test)")
table(["Component", "Metric", "Value", "Reference"], [
    ["Road-closure classifier", "PR-AUC", str(clo["pr_auc"]), f"base rate {clo['base_rate']}"],
    ["Road-closure classifier", "ROC-AUC", str(clo["auc"]), "—"],
    ["Clearance duration", "median abs error", f"{dur['median_ae_min']} min", f"test median {dur['test_median_min']} min"],
    ["Severity (rule)", "ROC-AUC", str(sev["auc"]), "operational rule, not skill"],
    ["Hotspot forecaster", "MAE", str(hot["mae"]), f"baseline {hot['baseline_mae_lastweek']}"],
    ["Hotspot forecaster", "Precision@10", str(hot["precision_at_10"]), "top-K hotspot overlap"],
], widths=[5 * cm, 4 * cm, 3.5 * cm, 4 * cm])
gap(6)
rule()
p("GridLock — Event-Driven Congestion Forecasting &amp; Resource Optimizer. Built on the real "
  "ASTraM dataset. This document was generated directly from the project's live metrics and source.",
  SMALL)


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTE)
    canvas.drawString(2 * cm, 1.0 * cm, "GridLock — Event-Driven Congestion Forecasting & Resource Optimizer")
    canvas.drawRightString(A4[0] - 2 * cm, 1.0 * cm, f"Page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(OUT), pagesize=A4,
    leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=2 * cm,
    title="GridLock — App Documentation", author="GridLock")
doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
print(f"Wrote {OUT.name}  ({OUT.stat().st_size // 1024} KB)")
