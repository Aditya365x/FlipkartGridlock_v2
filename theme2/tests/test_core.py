"""
Core regression tests — lock in the edge-case fixes (BUG-1, BUG-2, BUG-4, BUG-5) and basic
sanity of the recommendation/prediction engines.

Runs with pytest *or* standalone:
    pytest tests/                     # if pytest is installed
    python tests/test_core.py        # no pytest required
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.recommend import allocate_manpower, build_deployment_plan          # noqa: E402
from src.serve import InvalidWhen, parse_when, predict_event               # noqa: E402
from src import feedback                                                    # noqa: E402

VALID = {"event_type": "planned", "event_cause": "public_event", "corridor": "CBD 2",
         "zone": "Central Zone 1", "latitude": 12.97, "longitude": 77.59,
         "when": "2024-04-15T19:00:00"}


# ---------------------------------------------------------------- BUG-1: manpower edge cases
def test_allocate_zero_officers_no_crash():
    assert allocate_manpower({"A": 5, "B": 3}, 0) == {"A": 0, "B": 0}


def test_allocate_negative_officers_no_crash():
    assert allocate_manpower({"A": 5, "B": 3}, -10) == {"A": 0, "B": 0}


def test_allocate_empty_demand():
    assert allocate_manpower({}, 30) == {}


def test_allocate_respects_total():
    alloc = allocate_manpower({"A": 10, "B": 5, "C": 1}, 12, min_floor=1)
    assert sum(alloc.values()) <= 12
    assert all(v >= 0 for v in alloc.values())


def test_allocate_prioritizes_higher_demand():
    alloc = allocate_manpower({"high": 100, "low": 1}, 20, min_floor=1)
    assert alloc["high"] > alloc["low"]


# ---------------------------------------------------------------- BUG-2: date parsing
def test_parse_when_bad_string_raises():
    for bad in ["NOT A DATE", "tomorrow", "13/13/2024"]:
        try:
            parse_when(bad)
            assert False, f"expected InvalidWhen for {bad!r}"
        except InvalidWhen:
            pass


def test_parse_when_empty_defaults_to_now():
    assert parse_when("") is not None
    assert parse_when(None) is not None


def test_predict_event_bad_date_raises_clean():
    try:
        predict_event({**VALID, "when": "NOT A DATE"})
        assert False, "expected InvalidWhen"
    except InvalidWhen:
        pass


# ---------------------------------------------------------------- BUG-4: OOD / confidence
def test_valid_input_high_confidence():
    p = predict_event(VALID)
    assert p["out_of_distribution"] is False
    assert 0.0 <= p["road_closure_prob"] <= 1.0
    assert p["expected_duration_min"] >= 0


def test_unknown_cause_flagged_ood_low_confidence():
    p = predict_event({**VALID, "event_cause": "zombie_invasion"})
    assert p["out_of_distribution"] is True
    assert p["confidence"] == "low"
    assert any("event_cause" in w for w in p["warnings"])


def test_empty_event_does_not_crash():
    p = predict_event({})
    assert "road_closure_prob" in p


# ---------------------------------------------------------------- BUG-5: CSV injection
def test_csv_injection_sanitized():
    assert feedback._sanitize("=cmd|calc!A1").startswith("'=")
    assert feedback._sanitize("+1+1").startswith("'+")
    assert feedback._sanitize("public_event") == "public_event"   # benign untouched


# ---------------------------------------------------------------- feedback round-trip
def test_feedback_bool_roundtrip(tmp_path=None):
    import pandas as pd
    orig = feedback.LOG_PATH
    feedback.LOG_PATH = ROOT / "data" / "_test_feedback.csv"
    try:
        rid = feedback.log_prediction(VALID, predict_event(VALID), day="Monday", hour=19)
        ok = feedback.record_actual(rid, actual_closure=False, actual_duration_min=55.0,
                                    actual_high_priority=True)
        assert ok
        df = feedback.load_log()
        row = df[df["id"] == rid].iloc[0]
        assert bool(row["actual_closure"]) is False          # 'False' must NOT become True
        assert bool(row["actual_high_priority"]) is True
        assert bool(row["resolved"]) is True
    finally:
        feedback.LOG_PATH.unlink(missing_ok=True)
        feedback.LOG_PATH = orig


# ---------------------------------------------------------------- deployment plan sanity
def test_deployment_plan_event_corridor_staffed():
    pred = predict_event(VALID)
    from src.serve import forecast_corridor_load
    plan = build_deployment_plan("CBD 2", pred, forecast_corridor_load(VALID["when"]), 30)
    assert plan["officers"].sum() <= 30
    ev_row = plan[plan["corridor"] == "CBD 2"]
    assert len(ev_row) == 1 and int(ev_row["officers"].iloc[0]) >= 1


def test_deployment_plan_zero_officers():
    pred = predict_event(VALID)
    plan = build_deployment_plan("CBD 2", pred, {}, 0)
    assert plan["officers"].sum() == 0


# ---------------------------------------------------------------- standalone runner
def _run_all():
    fns = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    passed = failed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed (of {len(fns)})")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
