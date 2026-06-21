"""
decision.py — Turn raw model outputs into commander-grade DECISIONS.

Traffic police don't think in probabilities; they think in actions. This module converts a
prediction (+ deployment plan) into: a Risk Level, a confidence call, smart alerts, and a concrete
recommended action plan. Pure functions, no Streamlit/IO — reused by the dashboard and the API.
"""
from __future__ import annotations

# Risk bands on a 0-100 composite score. Tuned so a long planned event with low closure still
# registers (sustained disruption), while a high closure-probability incident escalates fast.
RISK_BANDS = [(70, "CRITICAL", "🔴", "#ef4444"),
              (45, "HIGH", "🟠", "#f97316"),
              (20, "MEDIUM", "🟡", "#eab308"),
              (0, "LOW", "🟢", "#22c55e")]


def risk_score(pred: dict) -> float:
    """Composite 0-100: closure probability dominates, sustained disruption and severity add on."""
    clo = float(pred.get("road_closure_prob", 0.0))           # 0..1
    dur_h = float(pred.get("expected_duration_min", 0.0)) / 60.0
    sev = float(pred.get("severity_high_prob", 0.0))          # 0..1
    score = clo * 60.0 + min(dur_h / 12.0, 1.0) * 25.0 + sev * 15.0
    return round(min(score, 100.0), 1)


def assess_risk(pred: dict) -> dict:
    score = risk_score(pred)
    for thr, label, icon, color in RISK_BANDS:
        if score >= thr:
            return {"level": label, "icon": icon, "color": color, "score": score}
    return {"level": "LOW", "icon": "🟢", "color": "#22c55e", "score": score}


def confidence_label(pred: dict) -> dict:
    """Surface the model's own confidence (OOD + decision-boundary) for non-technical users."""
    conf = pred.get("confidence", "high")
    if pred.get("out_of_distribution"):
        reason = "limited/unseen historical data for this scenario"
    elif conf == "low":
        reason = "the closure model is near its decision boundary"
    else:
        reason = "inputs are well within the historical data"
    return {"level": conf.upper(), "reason": reason}


def recommend_actions(corridor: str, pred: dict, risk: dict, event_officers: int,
                      junctions: list[str] | None = None) -> list[str]:
    """Concrete, ordered to-do list a commander can act on immediately."""
    junctions = [j for j in (junctions or []) if j and j != "unknown"][:2]
    actions: list[str] = [f"Deploy **{event_officers} officers** to **{corridor}**"]

    if pred.get("needs_barricade") or float(pred.get("road_closure_prob", 0)) >= 0.35:
        where = f" near {', '.join(junctions)}" if junctions else ""
        actions.append(f"Stage **barricades** on {corridor}{where}")
        actions.append(f"Pre-plan a **diversion** for {corridor} (use the historical-closure playbook)")

    if risk["level"] in ("HIGH", "CRITICAL"):
        actions.append("Put **1 emergency unit** (ambulance / tow) on standby")
    if risk["level"] == "CRITICAL":
        actions.append("Brief control room — escalate to **incident command**")

    if pred.get("confidence") == "low":
        actions.append("⚠️ Verify on-ground — model confidence is **low** for this scenario")

    actions.append(f"Monitor **{corridor}** on the Hotspot Map for the event window")
    return actions


def smart_alerts(corridor: str, pred: dict, risk: dict) -> list[dict]:
    """Top-of-screen alerts. type ∈ {error, warning, info} maps to red/orange/blue banners."""
    alerts: list[dict] = []
    if risk["level"] == "CRITICAL":
        alerts.append({"type": "error",
                       "msg": f"CRITICAL: Severe disruption likely on {corridor} — barricades + diversion recommended"})
    elif risk["level"] == "HIGH":
        alerts.append({"type": "warning",
                       "msg": f"HIGH risk on {corridor} — pre-stage deployment and barricades now"})
    if pred.get("needs_barricade"):
        alerts.append({"type": "warning", "msg": f"Road closure recommended on {corridor}"})
    if pred.get("out_of_distribution"):
        alerts.append({"type": "info", "msg": "Low confidence: limited/unseen historical data for this scenario"})
    return alerts


def decision_brief(corridor: str, pred: dict, event_officers: int,
                   junctions: list[str] | None = None) -> dict:
    """One call -> everything the UI/API needs to render a decision."""
    risk = assess_risk(pred)
    return {
        "risk": risk,
        "confidence": confidence_label(pred),
        "expected_impact_min": pred.get("expected_duration_min"),
        "alerts": smart_alerts(corridor, pred, risk),
        "actions": recommend_actions(corridor, pred, risk, event_officers, junctions),
    }
