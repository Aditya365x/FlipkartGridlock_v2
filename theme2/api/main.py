"""
FastAPI service exposing the Event-Driven Congestion engines.

Run:
    uvicorn api.main:app --reload --port 8000
Then open http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import functools
import sys
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import math  # noqa: E402

from src import decision, feedback  # noqa: E402
from src.recommend import allocate_manpower, build_deployment_plan, recent_closures  # noqa: E402
from src.serve import (InvalidWhen, _known_vocab, forecast_corridor_load,  # noqa: E402
                       parse_when, predict_event)

app = FastAPI(title="EVENT Shield AI — Traffic Intelligence API", version="2.0")

# Allow the React dev server (Vite) to call the API in development.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


class EventIn(BaseModel):
    event_type: str = "unplanned"
    event_cause: str = "others"
    corridor: str = "Non-corridor"
    zone: str = "unknown"
    veh_type: str = "none"
    latitude: float = 12.97
    longitude: float = 77.59
    when: str | None = None

    @field_validator("when")
    @classmethod
    def _check_when(cls, v):
        if v is None:
            return v
        try:
            parse_when(v)          # reject unparseable dates at the schema boundary -> 422
        except InvalidWhen as e:
            raise ValueError(str(e))
        return v

    @field_validator("latitude")
    @classmethod
    def _check_lat(cls, v):
        if not -90 <= v <= 90:
            raise ValueError("latitude must be in [-90, 90]")
        return v

    @field_validator("longitude")
    @classmethod
    def _check_lon(cls, v):
        if not -180 <= v <= 180:
            raise ValueError("longitude must be in [-180, 180]")
        return v


class AllocIn(BaseModel):
    demand: dict[str, float]
    total_officers: int = 30
    min_floor: int = 1

    @field_validator("total_officers")
    @classmethod
    def _check_officers(cls, v):
        if v < 0:
            raise ValueError("total_officers must be >= 0")
        return v


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict_event")
def predict(event: EventIn):
    """Predict severity, road-closure need, and clearance duration for one event."""
    return predict_event(event.model_dump())


@app.post("/recommend_manpower")
def recommend(req: AllocIn):
    """Allocate a limited officer pool across zones by predicted demand."""
    alloc = allocate_manpower(req.demand, req.total_officers, req.min_floor)
    return {"allocation": alloc, "total_assigned": sum(alloc.values())}


@app.get("/corridor_closures/{corridor}")
def corridor_closures(corridor: str, event_cause: str | None = None):
    """Recent road closures on a corridor (planning reference; no route/diversion data exists)."""
    rows = recent_closures(corridor, event_cause).to_dict(orient="records")
    return {"corridor": corridor, "recent_closures": rows}


# =========================== EVENT Shield AI — command-center endpoints ===========================
ROOT = Path(__file__).resolve().parent.parent


@functools.lru_cache(maxsize=1)
def _corridor_coords() -> dict:
    """Representative (median) lat/lon per named corridor, for plotting on the live map."""
    try:
        df = pd.read_parquet(ROOT / "data" / "clean_events.parquet")
        g = df[df["corridor"] != "Non-corridor"]
        if "geo_valid" in g.columns:
            g = g[g["geo_valid"]]
        med = g.groupby("corridor")[["latitude", "longitude"]].median()
        return {str(k): {"lat": float(r["latitude"]), "lon": float(r["longitude"])}
                for k, r in med.iterrows()}
    except Exception:
        return {}


def _with_coords(items: list[dict]) -> list[dict]:
    coords = _corridor_coords()
    for it in items:
        c = coords.get(it["corridor"])
        if c:
            it["lat"], it["lon"] = c["lat"], c["lon"]
    return items


class PlanIn(EventIn):
    total_officers: int = 30

    @field_validator("total_officers")
    @classmethod
    def _check_officers(cls, v):
        if v < 0:
            raise ValueError("total_officers must be >= 0")
        return v


def _err(e: Exception):
    raise HTTPException(status_code=422, detail=str(e))


@app.get("/corridors")
def corridors():
    """All named corridors with representative coordinates (for the live map)."""
    return [{"corridor": c, **xy} for c, xy in sorted(_corridor_coords().items())]


@app.get("/meta")
def meta():
    """Dropdown vocab for the UI (event types, causes, corridors, zones)."""
    v = _known_vocab()
    return {k: sorted(v.get(k, [])) for k in ("event_type", "event_cause", "corridor", "zone")}


@app.post("/forecast")
def forecast(req: EventIn):
    """Expected corridor load (typical-load model) for the window containing `when`."""
    try:
        load = forecast_corridor_load(req.when)
    except InvalidWhen as e:
        _err(e)
    items = sorted(({"corridor": c, "expected_load": round(v, 3)} for c, v in load.items()),
                   key=lambda x: -x["expected_load"])
    return {"when": req.when, "corridors": _with_coords(items)}


def _build_plan(ev: dict, total_officers: int) -> dict:
    pred = predict_event(ev)
    load = forecast_corridor_load(ev.get("when"))
    plan = build_deployment_plan(ev["corridor"], pred, load, total_officers)
    ev_off = int(plan.loc[plan["corridor"] == ev["corridor"], "officers"].sum())
    brief = decision.decision_brief(ev["corridor"], pred, ev_off, [])
    return {"prediction": pred, "decision": brief, "officers_event": ev_off,
            "deployment": plan.to_dict(orient="records")}


@app.post("/action_plan")
def action_plan(req: PlanIn):
    """The hero endpoint: prediction + risk + confidence + alerts + deployment plan in one call."""
    data = req.model_dump()
    officers = data.pop("total_officers")
    try:
        return _build_plan(data, officers)
    except InvalidWhen as e:
        _err(e)


# representative causes used to synthesize a city "operational picture"
_ROSTER_CAUSES = ["public_event", "protest", "accident", "construction", "procession",
                  "vip_movement", "vehicle_breakdown", "water_logging", "tree_fall", "pot_holes"]


def _stable_idx(s: str, n: int) -> int:
    """Deterministic hash of a corridor name -> index. Assigns each corridor a cause by its NAME,
    not its load rank, so severity isn't always pinned to the busiest corridor."""
    h = 0
    for ch in s:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return h % n


@app.get("/dashboard")
def dashboard(when: str | None = None):
    """Command-center snapshot — a SIMULATED operational picture derived from the model:
    a roster of active events on the busiest corridors, featured by highest risk."""
    try:
        load = forecast_corridor_load(when)
    except InvalidWhen as e:
        _err(e)
    coords = _corridor_coords()
    top = sorted(load.items(), key=lambda kv: -kv[1])[:6]

    # build a roster: assign a cause by corridor NAME (not load rank), score each by risk
    roster = []
    for corr, ld in top:
        cause = _ROSTER_CAUSES[_stable_idx(corr, len(_ROSTER_CAUSES))]
        etype = "planned" if cause in ("public_event", "procession", "construction") else "unplanned"
        p = predict_event({"event_type": etype, "event_cause": cause, "corridor": corr,
                           "zone": "unknown", "when": when})
        r = decision.assess_risk(p)
        item = {"corridor": corr, "cause": cause, "event_type": etype, "expected_load": round(ld, 3),
                "risk": r["level"], "score": r["score"], "closure_prob": p["road_closure_prob"],
                "needs_barricade": p["needs_barricade"], "impact_min": p["expected_duration_min"]}
        c = coords.get(corr)
        if c:
            item["lat"], item["lon"] = c["lat"], c["lon"]
        roster.append(item)
    roster.sort(key=lambda x: -x["score"])

    feat = roster[0] if roster else {"corridor": "Mysore Road", "cause": "public_event", "event_type": "planned"}
    ev = {"event_type": feat["event_type"], "event_cause": feat["cause"], "corridor": feat["corridor"],
          "zone": "unknown", "when": when}
    plan = _build_plan(ev, 30)
    pred, brief = plan["prediction"], plan["decision"]
    return {
        "simulated": True,
        "generated_at": pd.Timestamp.now().isoformat(timespec="seconds"),
        "featured": {"corridor": feat["corridor"], "cause": feat["cause"]},
        "status": brief["risk"]["level"],
        "impact_score": brief["risk"]["score"],
        "closure_prob": pred["road_closure_prob"],
        "needs_barricade": pred["needs_barricade"],
        "expected_impact_min": pred["expected_duration_min"],
        "confidence": brief["confidence"],
        "officers": {"deployed": plan["officers_event"], "total": 30},
        "alerts": brief["alerts"],
        "actions": brief["actions"],
        "deployment": plan["deployment"],
        "active_events": roster,
        "top_corridors": _with_coords([{"corridor": c, "expected_load": round(v, 3)} for c, v in top]),
    }


# =========================== Post-Event Learning (live, backed by feedback.py) ===========================
def _num(v):
    try:
        f = float(v)
        return None if math.isnan(f) else round(f, 2)
    except (TypeError, ValueError):
        return None


def _opt_bool(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    try:
        return bool(v)
    except Exception:
        return None


def _learning_state() -> dict:
    df = feedback.load_log().tail(50)
    log = [{
        "id": str(r["id"]), "corridor": r["corridor"], "event_cause": r["event_cause"],
        "pred_closure_prob": _num(r["pred_closure_prob"]), "pred_duration_min": _num(r["pred_duration_min"]),
        "resolved": bool(_opt_bool(r["resolved"])),
        "actual_closure": _opt_bool(r["actual_closure"]),
        "actual_duration_min": _num(r["actual_duration_min"]),
    } for _, r in df.iterrows()]
    return {"metrics": feedback.learning_metrics(), "calibration": feedback.load_calibration(), "log": log}


class RecordIn(BaseModel):
    id: str
    actual_closure: bool
    actual_duration_min: float
    actual_high_priority: bool = False


@app.get("/learning")
def learning():
    """Live post-event-learning state: metrics, learned calibration, and the feedback log."""
    return _learning_state()


@app.post("/learning/log")
def learning_log(event: EventIn):
    """Log a prediction (from the Event Planner) as PENDING — its real outcome is recorded later."""
    ev = event.model_dump()
    pred = predict_event(ev)
    w = parse_when(ev.get("when"))
    rid = feedback.log_prediction(ev, pred, day=w.day_name(), hour=int(w.hour))
    state = _learning_state()
    state["logged_id"] = rid
    return state


@app.post("/learning/seed")
def learning_seed(n: int = 30):
    """Bootstrap the loop with real historical events + their true outcomes, then recalibrate."""
    feedback.seed_from_history(max(1, min(n, 200)))
    return _learning_state()


@app.post("/learning/record")
def learning_record(req: RecordIn):
    """Record what actually happened for a logged prediction; calibration refreshes automatically."""
    ok = feedback.record_actual(req.id, actual_closure=req.actual_closure,
                                actual_duration_min=req.actual_duration_min,
                                actual_high_priority=req.actual_high_priority)
    if not ok:
        raise HTTPException(status_code=404, detail=f"prediction id {req.id} not found")
    return _learning_state()


@app.post("/learning/clear")
def learning_clear():
    """Reset the loop (clear feedback log + calibration)."""
    feedback.LOG_PATH.unlink(missing_ok=True)
    feedback.CALIB_PATH.unlink(missing_ok=True)
    return _learning_state()


# =========================== Serve the built React app (single-service deploy) ===========================
# When the frontend is built (e.g. in the Docker image for Hugging Face), FastAPI serves it too, so the
# whole product runs on one URL with no CORS. Skipped in local dev (no dist) — use `npm run dev` there.
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

_DIST = ROOT / "frontend" / "dist"
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def _spa(full_path: str):
        """Serve real static files; fall back to index.html so client-side routes (e.g. /simulation) work."""
        candidate = _DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")
