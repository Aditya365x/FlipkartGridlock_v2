"""
recommend.py — Resource recommendation engine.

Turns predicted demand into an actionable plan:
  * manpower   : allocate a limited officer pool across zones (OR-Tools LP, greedy fallback)
  * barricade  : flag locations whose road-closure probability exceeds a threshold
  * diversion  : retrieve historical diversions on the affected corridor (case-based)

Run a demo:
    python -m src.recommend
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean_events.parquet"

try:
    from ortools.linear_solver import pywraplp
    _HAS_ORTOOLS = True
except Exception:  # pragma: no cover
    _HAS_ORTOOLS = False


def allocate_manpower(demand: dict[str, float], total_officers: int,
                      min_floor: int = 1, max_per_zone: int | None = None) -> dict[str, int]:
    """Allocate `total_officers` across zones to maximize severity-weighted, diminishing-returns
    coverage of demand. Coverage uses sqrt(officers) to model diminishing marginal value.

    Solved as an integer program with OR-Tools; falls back to a transparent greedy allocation.
    """
    zones = [z for z in demand if demand[z] > 0]
    if not zones:
        return {}
    if total_officers <= 0:                       # nothing to allocate -> everyone gets zero
        return {z: 0 for z in zones}
    if max_per_zone is None:
        max_per_zone = total_officers

    # Pre-tabulate marginal value of the k-th officer in a zone: w * (sqrt(k) - sqrt(k-1)).
    def marginal(z: str, k: int) -> float:
        return demand[z] * (math.sqrt(k) - math.sqrt(k - 1))

    if _HAS_ORTOOLS:
        solver = pywraplp.Solver.CreateSolver("CBC")
        if solver is not None:
            x = {}  # x[z,k] = 1 if zone z gets at least k officers
            obj = solver.Objective()
            for z in zones:
                for k in range(1, max_per_zone + 1):
                    x[z, k] = solver.IntVar(0, 1, f"x_{z}_{k}")
                    obj.SetCoefficient(x[z, k], marginal(z, k))
                # ordering: the k-th officer requires the (k-1)-th
                for k in range(2, max_per_zone + 1):
                    solver.Add(x[z, k] <= x[z, k - 1])
                # min floor
                for k in range(1, min_floor + 1):
                    solver.Add(x[z, k] == 1)
            solver.Add(solver.Sum(x[z, k] for z in zones for k in range(1, max_per_zone + 1)) <= total_officers)
            obj.SetMaximization()
            if solver.Solve() == pywraplp.Solver.OPTIMAL:
                return {z: int(sum(round(x[z, k].solution_value()) for k in range(1, max_per_zone + 1)))
                        for z in zones}

    # ---- greedy fallback (also a clear, explainable baseline) ----
    alloc = {z: 0 for z in zones}
    remaining = total_officers
    # satisfy floors first
    for z in zones:
        give = min(min_floor, remaining, max_per_zone)
        alloc[z] += give
        remaining -= give
    # then assign each remaining officer to the best marginal gain
    while remaining > 0:
        best_z, best_val = None, -1.0
        for z in zones:
            if alloc[z] >= max_per_zone:
                continue
            val = marginal(z, alloc[z] + 1)
            if val > best_val:
                best_z, best_val = z, val
        if best_z is None:
            break
        alloc[best_z] += 1
        remaining -= 1
    return alloc


def event_officer_need(pred: dict, base: float = 3.0) -> float:
    """How many officers the event *itself* warrants, sized by its predicted impact:

        need = base + 4*P(high) + 12*P(closure) + 1.5*min(duration_hours, 6)

    A minor accident lands around 5-11 officers; a long, closure-likely public event ~25.
    (Duration is capped at 6h because the duration label is noisy on the long tail.)
    """
    sev = float(pred.get("severity_high_prob", 0.0))
    clo = float(pred.get("road_closure_prob", 0.0))
    dur_h = min(float(pred.get("expected_duration_min", 0.0)) / 60.0, 6.0)
    return base + 4.0 * sev + 12.0 * clo + 1.5 * dur_h


def build_deployment_plan(event_corridor: str, pred: dict, forecast_load: dict[str, float],
                          total_officers: int, min_floor: int = 1, top_n: int = 10,
                          reserve_frac: float = 0.25) -> pd.DataFrame:
    """Fuse the per-event impact prediction with the corridor-level hotspot forecast into one plan.

    1. The event's corridor is staffed to `event_officer_need(pred)` (sized by predicted impact),
       capped so at least `reserve_frac` of the pool stays available for the rest of the city.
    2. The *remaining* officers are spread across other corridors by their forecasted event load
       for that time window (severity-weighted, diminishing returns) — so the city keeps cover.

    This makes the plan respond to *both* what the event is (impact) and where it is (corridor),
    fixing the old behaviour where deployment ignored the event and tracked only history.
    """
    need = event_officer_need(pred)
    max_event = max(1, int(round(total_officers * (1.0 - reserve_frac))))
    event_officers = int(min(round(need), max_event, total_officers))
    remaining = total_officers - event_officers

    others = {c: max(float(v), 0.05) for c, v in forecast_load.items() if c != event_corridor}
    top = dict(sorted(others.items(), key=lambda kv: -kv[1])[:top_n])
    cover = allocate_manpower(top, remaining, min_floor=min_floor) if remaining > 0 and top else {}

    rows = [{"corridor": event_corridor, "officers": event_officers,
             "demand_weight": round(need, 1), "role": "★ EVENT"}]
    rows += [{"corridor": c, "officers": n, "demand_weight": round(top[c], 2),
              "role": "forecast cover"}
             for c, n in sorted(cover.items(), key=lambda kv: -kv[1]) if n > 0]
    return pd.DataFrame(rows)


def barricade_recommendations(events: pd.DataFrame, tau: float = 0.5) -> pd.DataFrame:
    """events must have columns: id/location, corridor, zone, closure_prob, severity."""
    flagged = events[events["closure_prob"] >= tau].copy()
    flagged = flagged.sort_values("closure_prob", ascending=False)
    return flagged[["corridor", "zone", "closure_prob", "severity"]].reset_index(drop=True)


EVENT_DRIVEN_CAUSES = {"public_event", "procession", "vip_movement", "protest", "construction"}


def recent_closures(corridor: str, event_cause: str | None = None, top: int = 3) -> pd.DataFrame:
    """Past road *closures* on this corridor, as a planning reference (NOT computed diversions —
    this dataset has no usable route/direction data, so we surface real historical closures).

    Relevance: prefer the same cause; for an event-driven cause (procession/VIP/etc.) fall back to
    other event-driven closures before any closure. Uses `address` (100% populated) rather than
    `junction` (~31%). Duration is omitted: its labels are too noisy to show here.
    """
    df = pd.read_parquet(CLEAN)
    on_corridor = df[df["corridor"] == corridor]
    pool = on_corridor[on_corridor["requires_road_closure"] == True]  # noqa: E712
    if pool.empty:
        pool = on_corridor

    if event_cause:                                    # tiered relevance filter
        same = pool[pool["event_cause"] == event_cause]
        if not same.empty:
            pool = same
        elif event_cause in EVENT_DRIVEN_CAUSES:
            ed = pool[pool["event_cause"].isin(EVENT_DRIVEN_CAUSES)]
            if not ed.empty:
                pool = ed

    cols = [c for c in ["start_datetime", "address", "event_cause"] if c in pool.columns]
    out = pool.sort_values("start_datetime", ascending=False).head(top)[cols].copy()
    if "start_datetime" in out.columns:
        out["start_datetime"] = out["start_datetime"].dt.date
        out = out.rename(columns={"start_datetime": "date"})
    return out.reset_index(drop=True)


def _demo() -> None:
    demand = {"Central Zone 2": 18.0, "West Zone 1": 9.0, "North Zone 2": 7.0,
              "South Zone 1": 3.0, "East Zone 1": 2.0}
    alloc = allocate_manpower(demand, total_officers=30, min_floor=2)
    print("Manpower allocation (30 officers):")
    for z, n in sorted(alloc.items(), key=lambda kv: -kv[1]):
        print(f"  {z:16s} demand={demand[z]:5.1f} -> {n} officers")
    print(f"  total assigned: {sum(alloc.values())}  | solver: {'OR-Tools' if _HAS_ORTOOLS else 'greedy'}")

    print("\nRecent closures on 'Mysore Road' (planning reference):")
    print(recent_closures("Mysore Road").to_string(index=False))


if __name__ == "__main__":
    _demo()
