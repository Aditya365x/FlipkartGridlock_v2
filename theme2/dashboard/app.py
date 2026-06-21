"""
GridLock — Event-Driven Congestion dashboard.

Run:
    streamlit run dashboard/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import decision, feedback  # noqa: E402
from src.recommend import build_deployment_plan, recent_closures  # noqa: E402
from src.serve import forecast_corridor_load, predict_event  # noqa: E402

# ASTraM timestamps are already Bengaluru-local (see note in features.py) — no offset.
st.set_page_config(page_title="GridLock — Event Congestion", layout="wide")


def fmt_dur(minutes: float) -> str:
    """Minutes -> 'Xh YYm' (e.g. 76 -> '1h 16m', 36 -> '36m')."""
    if minutes is None or pd.isna(minutes):
        return "—"
    total = int(round(float(minutes)))
    h, m = divmod(total, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


@st.cache_data
def load_events() -> pd.DataFrame:
    df = pd.read_parquet(ROOT / "data" / "clean_events.parquet")
    df["local"] = df["start_datetime"]  # already local
    df["hour"] = df["local"].dt.hour
    df["dow"] = df["local"].dt.day_name()
    df["date"] = df["local"].dt.date
    return df


df = load_events()
CORRIDORS = sorted(df["corridor"].dropna().unique().tolist())
CAUSES = sorted(df["event_cause"].dropna().unique().tolist())
ZONES = sorted([z for z in df["zone"].dropna().unique().tolist() if z != "unknown"])

st.title("🚦 GridLock — Event-Driven Congestion Forecasting & Resource Optimizer")
st.caption("Built on the ASTraM event log · Bengaluru · 8,173 events · Nov 2023 – Apr 2024")

# Shared time axis for the whole app: a week anchored on a Monday, so the Event Planner,
# the Hotspot Map and the Analytics tab all speak the same (day-of-week, hour) language.
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
ANCHOR = pd.Timestamp("2024-04-15") - pd.Timedelta(days=pd.Timestamp("2024-04-15").dayofweek)  # a Monday


def scenario_banner() -> None:
    """One-line summary of the active Event Planner scenario, shown atop every tab so the three
    views are visibly describing the *same* situation rather than three disconnected queries."""
    s = st.session_state.get("scenario")
    if not s:
        st.caption("💡 Run a prediction in the **Event Planner** tab — the Map and Analytics tabs "
                   "will sync to it automatically.")
        return
    p = s["pred"]
    st.info(
        f"🔗 **Active scenario:** {s['cause']} · **{s['corridor']}** · {s['day']} {s['hour']:02d}:00 "
        f"  —  closure prob **{p['road_closure_prob']:.0%}**, impact **{fmt_dur(p['expected_duration_min'])}**, "
        f"priority **{p['predicted_priority']}**.  All three tabs are scoped to this scenario.")


tab1, tab2, tab3, tab4 = st.tabs(["🔮 Event Planner (What-if)", "🗺️ Hotspot Map", "📊 Analytics",
                                  "🔁 Post-Event Learning"])

# ---------------------------------------------------------------- Tab 1: what-if
with tab1:
    scenario_banner()
    st.subheader("Predict an event's impact and get a deployment plan")
    c1, c2, c3 = st.columns(3)
    with c1:
        etype = st.selectbox("Event type", ["planned", "unplanned"])
        cause = st.selectbox("Event cause", CAUSES, index=CAUSES.index("public_event") if "public_event" in CAUSES else 0)
    with c2:
        corridor = st.selectbox("Corridor", CORRIDORS, index=CORRIDORS.index("CBD 2") if "CBD 2" in CORRIDORS else 0,
                                key="planner_corridor")
        zone = st.selectbox("Zone", ZONES or ["unknown"])
    with c3:
        day = st.selectbox("Day of week", DAYS, index=0, key="planner_day")  # default Monday
        hour = st.slider("Hour of day (IST)", 0, 23, 19)
        total_officers = st.number_input("Available officers (city-wide)", 5, 500, 30)

    sub = df[df["corridor"] == corridor]
    lat = float(sub["latitude"].median()) if len(sub) else 12.97
    lon = float(sub["longitude"].median()) if len(sub) else 77.59
    # Same formula the Map and Analytics tabs use, so a scenario maps to one shared time window.
    when = (ANCHOR + pd.Timedelta(days=DAYS.index(day), hours=hour)).isoformat()

    bcol, xcol = st.columns([3, 1])
    go = bcol.button("Predict impact & recommend plan", type="primary")
    if st.session_state.get("scenario") and xcol.button("Clear scenario"):
        del st.session_state["scenario"]
        st.rerun()

    if go:
        pred = predict_event({"event_type": etype, "event_cause": cause, "corridor": corridor,
                              "zone": zone, "latitude": lat, "longitude": lon, "when": when})
        forecast_load = forecast_corridor_load(when)   # {corridor: predicted events this window}
        plan = build_deployment_plan(corridor, pred, forecast_load, int(total_officers), min_floor=1)
        # One shared scenario drives all three tabs. Persisting it also makes the result survive
        # reruns from other widgets/tabs (st.button is only True on the click rerun).
        st.session_state["scenario"] = {
            "corridor": corridor, "cause": cause, "etype": etype, "zone": zone,
            "day": day, "hour": hour, "when": when, "dow": DAYS.index(day),
            "pred": pred, "plan": plan, "total_officers": int(total_officers),
        }
        # Rerun so every tab's banner (incl. the one drawn ABOVE this block) reads the new
        # scenario in one consistent pass — otherwise the Planner's top banner lags one click.
        st.rerun()

    scen = st.session_state.get("scenario")
    if scen:
        # Warn when the dropdowns have drifted from the prediction on screen, so the user knows the
        # results (and the synced Map/Analytics tabs) reflect the *last predicted* event, not the
        # current selections, until they click Predict again.
        current = {"corridor": corridor, "cause": cause, "etype": etype, "zone": zone,
                   "day": day, "hour": hour, "total_officers": int(total_officers)}
        changed = [k for k in current if scen[k] != current[k]]
        if changed:
            st.warning(
                f"⚠️ Inputs changed — these results are for the **last prediction** "
                f"({scen['cause']} · {scen['corridor']} · {scen['day']} {scen['hour']:02d}:00). "
                f"Changed: {', '.join(changed)}. Click **Predict impact & recommend plan** to "
                "update this scenario across all three tabs.")
        pred = scen["pred"]
        plan = scen["plan"]
        res_corridor = scen["corridor"]
        res_cause = scen["cause"]
        res_total = scen["total_officers"]

        # ============================ DECISION-FIRST: the Action Plan headline ============================
        ev_off = int(plan.loc[plan["corridor"] == res_corridor, "officers"].sum())
        jx = (df[df["corridor"] == res_corridor]["junction"].value_counts().index.tolist()
              if "junction" in df.columns else [])
        brief = decision.decision_brief(res_corridor, pred, ev_off, jx)
        _banner = {"error": st.error, "warning": st.warning, "info": st.info}
        for al in brief["alerts"]:
            _banner[al["type"]](("🚨 " if al["type"] == "error" else "") + al["msg"])

        r, c = brief["risk"], brief["confidence"]
        st.markdown(
            f"<div style='background:{r['color']}1f;border-left:7px solid {r['color']};"
            f"padding:14px 20px;border-radius:10px;margin:8px 0;'>"
            f"<span style='font-size:1.5rem;font-weight:800;color:{r['color']};'>{r['icon']} RISK: {r['level']}</span>"
            f"<span style='opacity:.65;margin-left:12px;'>composite score {r['score']}/100 · "
            f"confidence {c['level']}</span></div>", unsafe_allow_html=True)
        d1, d2, d3 = st.columns(3)
        d1.metric("Expected disruption window", fmt_dur(brief["expected_impact_min"]))
        d2.metric("Prediction confidence", c["level"], help=c["reason"])
        d3.metric("Officers to event corridor", f"{ev_off} of {res_total}")
        st.markdown("**🛡️ Recommended actions**")
        for a in brief["actions"]:
            st.markdown(f"- {a}")
        st.caption("Decision synthesized from the model outputs below. Risk = closure probability + "
                   "sustained-disruption + severity. 'Disruption window' is the predicted traffic-impact "
                   "duration, not a separate delay model.")
        st.divider()
        st.markdown("##### 🔬 Model details (the raw predictions behind this plan)")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Road-closure prob", f"{pred['road_closure_prob']:.0%}",
                  help="The genuinely predictive output — probability this event needs a road closure.")
        m2.metric("Needs barricade?", "YES" if pred["needs_barricade"] else "no")
        m3.metric("Expected impact duration", fmt_dur(pred["expected_duration_min"]),
                  help="How long the event is expected to affect traffic — its disruption window. "
                       "Short for incidents (accident, breakdown); naturally long for planned public "
                       "events, processions and construction. NOT incident clean-up time.")
        m4.metric("Priority (corridor rule)", pred["predicted_priority"],
                  help="Not a real prediction: in this data, priority is ~99.9% an operational rule "
                       "(any named corridor = High). Shown for completeness, not as model skill.")
        st.caption("ℹ️ **Road-closure** and **impact duration** are the real predictions. **Priority** is "
                   "an operational rule (named corridor → High), so it reads High for any corridor.")
        # "Impact duration" is the event's traffic-disruption window, not incident clean-up time.
        # Ground it with a ROBUST historical median: prefer corridor+cause when we have enough
        # samples, else fall back to the cause city-wide; exclude the 48h-cap rows (defaulted /
        # missing end-times) so the anchor reflects real disruption, not data artifacts.
        EVENT_DRIVEN = {"public_event", "procession", "vip_movement", "protest", "construction"}
        CAP_MIN = 48 * 60
        _cc = df[(df["corridor"] == res_corridor) & (df["event_cause"] == res_cause)]
        _base = _cc if len(_cc) >= 15 else df[df["event_cause"] == res_cause]
        _bn = _base[_base["duration_min"] < CAP_MIN]
        if len(_bn):
            _med = _bn["duration_min"].median()
            _scope = f"{res_corridor}/{res_cause}" if len(_cc) >= 15 else f"{res_cause} (city-wide)"
            if res_cause in EVENT_DRIVEN:
                st.caption(
                    f"⏱️ This is the **traffic-impact window**, not incident clean-up time. Planned events "
                    f"like **{res_cause}** legitimately tie up roads for hours — the typical (median) is "
                    f"**{fmt_dur(_med)}** across {len(_bn):,} past {_scope} events. Treat the estimate as a "
                    "directional planning figure, not a precise ETA.")
            else:
                st.caption(
                    f"⏱️ Expected time for traffic to clear. Typical (median) for **{_scope}** is "
                    f"**{fmt_dur(_med)}** ({len(_bn):,} past events); the estimate is a rough guide, not a precise ETA.")
        if pred.get("confidence") == "low":
            why = ("some inputs are outside the training data" if pred.get("out_of_distribution")
                   else "the closure model is near its 50/50 decision boundary")
            st.caption(f"🟡 **Low-confidence prediction** — {why}; treat these outputs as indicative only.")
        if pred.get("calibrated"):
            rawp, rawd = pred.get("road_closure_prob_raw"), pred.get("expected_duration_min_raw")
            st.caption(f"🔁 **Calibrated by the Post-Event Learning loop** "
                       f"(raw model said {rawp:.0%} closure, {fmt_dur(rawd)} clearance). "
                       "Corrections learned from logged actuals — see the **Post-Event Learning** tab.")

        st.markdown("#### Recommended deployment (event-led, with forecast-based city cover)")
        st.caption(
            f"**{res_corridor}** is the event corridor → it gets priority from the predicted impact above. "
            "Remaining officers spread across other corridors by the **hotspot forecast** for this "
            "time window — so the city keeps baseline cover without ignoring the event.")
        st.dataframe(plan, width="stretch", hide_index=True)
        ev_off = int(plan.loc[plan["corridor"] == res_corridor, "officers"].sum())
        st.caption(f"Plan assigns **{ev_off} of {res_total}** officers to the event corridor "
                   f"(**{res_corridor}**); the rest provide forecast-weighted coverage elsewhere.")

        if pred["needs_barricade"]:
            st.markdown("#### Recent closures on this corridor (planning reference)")
            st.caption("Past road closures on this corridor, closest-matching cause first — a reference "
                       "for how similar disruptions were handled. This dataset has no route/diversion "
                       "data, so we show real historical closures, not computed diversions.")
            st.dataframe(recent_closures(res_corridor, res_cause), width="stretch", hide_index=True)

        st.divider()
        if st.button("📝 Log this prediction for post-event review"):
            ev = {"event_type": scen["etype"], "event_cause": scen["cause"],
                  "corridor": scen["corridor"], "zone": scen["zone"], "when": scen["when"]}
            rid = feedback.log_prediction(ev, scen["pred"], day=scen["day"], hour=scen["hour"])
            st.success(f"Logged as **{rid}**. After the event, record what actually happened in the "
                       "**🔁 Post-Event Learning** tab so the models can learn from it.")

# ---------------------------------------------------------------- Tab 2: map
@st.cache_data
def corridor_coords() -> pd.DataFrame:
    """Representative (median) lat/long per named corridor, for plotting forecasted load."""
    g = df[(df["corridor"] != "Non-corridor") & df["geo_valid"]]
    return g.groupby("corridor")[["latitude", "longitude"]].median().reset_index()


with tab2:
    scenario_banner()
    st.subheader("Expected Corridor Load — Based on Historical Patterns")
    st.caption("ℹ️ Predicts the *usual* number of events per corridor for the selected **day-of-week + "
               "time**, learned from history (a typical-load model). It is not wired to a live feed, so "
               "two dates with the same weekday and hour show the same expected load. "
               "(Roadmap: feed live recent counts to make it react to current conditions.)")
    view = st.radio("Map shows", ["🔮 Expected load (pick a time window)", "🕘 Historical density"],
                    horizontal=True)

    if view.startswith("🔮"):
        scen = st.session_state.get("scenario")
        sync = False
        if scen:
            sync = st.checkbox(
                f"🔗 Sync to Event Planner scenario — {scen['corridor']}, {scen['day']} {scen['hour']:02d}:00",
                value=True,
                help="On: the map locks to your scenario's day/hour and highlights the event corridor "
                     "in blue, so it shows the exact forecast the deployment plan was built from.")
        if sync and scen:                                   # locked to the planner scenario
            day, mhour = scen["day"], scen["hour"]
            event_corridor = scen["corridor"]
            st.caption(f"📅 **{day}** · 🕒 **{mhour:02d}:00** — locked to the scenario. "
                       "Untick the box above to explore other time windows.")
        else:                                               # free exploration
            event_corridor = None
            c1, c2 = st.columns(2)
            with c1:
                day = st.selectbox("Day of week", DAYS, index=5)              # default Saturday
            with c2:
                mhour = st.slider("Hour of day (IST)", 0, 23, 21, key="map_hour")  # default 9 PM
        when = (ANCHOR + pd.Timedelta(days=DAYS.index(day), hours=mhour)).isoformat()

        load = forecast_corridor_load(when)                              # {corridor: predicted events}
        plot = corridor_coords().copy()
        plot["pred"] = plot["corridor"].map(load).fillna(0.0)
        # NA-safe event flag (corridor is a nullable-string dtype, so `== None` yields <NA>, not False)
        plot["is_event"] = (plot["corridor"].astype("object").eq(event_corridor).fillna(False).astype(bool)
                            if event_corridor else False)
        # keep corridors with load, plus always keep the event corridor when synced
        plot = plot[(plot["pred"] > 0) | plot["is_event"]]
        plot = plot.sort_values("pred", ascending=False).reset_index(drop=True)

        if plot.empty:
            st.info("No forecasted load for this window.")
        else:
            mx = float(plot["pred"].max()) or 1.0
            plot["fill_color"] = plot.apply(
                lambda r: [0, 120, 255, 235] if r["is_event"]            # blue = the event corridor
                else [240, int(200 * (1 - r["pred"] / mx)), 30, 200], axis=1)  # yellow -> red by load
            plot["pred_txt"] = plot["pred"].round(2)
            layers = [pdk.Layer(
                "ColumnLayer", data=plot, get_position="[longitude, latitude]",
                get_elevation="pred", elevation_scale=3500, radius=550,
                get_fill_color="fill_color", pickable=True, auto_highlight=True, extruded=True)]
            # The event corridor can have a tiny forecast (flat column) — add a fixed-size blue
            # marker so it's always findable on the map, regardless of its forecast height.
            ev_pt = plot[plot["is_event"]]
            if not ev_pt.empty:
                layers.append(pdk.Layer(
                    "ScatterplotLayer", data=ev_pt, get_position="[longitude, latitude]",
                    get_fill_color="[0, 120, 255, 255]", get_radius=700, radius_min_pixels=9,
                    pickable=True))
            st.pydeck_chart(pdk.Deck(
                map_style=None,
                initial_view_state=pdk.ViewState(latitude=12.97, longitude=77.59, zoom=10.3, pitch=45),
                layers=layers,
                tooltip={"html": "<b>{corridor}</b><br/>forecast: {pred_txt} events / 3h"},
            ))
            if event_corridor:
                ev_load = float(plot.loc[plot["is_event"], "pred"].iloc[0])
                rank = int((plot["pred"] > ev_load).sum()) + 1
                tag = (f" — 🔵 **{event_corridor}** is your event corridor "
                       f"(forecast **{ev_load:.2f}** events/3h, rank #{rank} of {len(plot)})")
            else:
                tag = ""
            st.caption(f"Predicted event load for **{day} {mhour:02d}:00** — taller/redder = more events "
                       f"expected{tag}. Powered by the hotspot forecaster (`hotspot.joblib`); changes with "
                       "the time window above.")
            st.markdown("##### Top corridors by expected load (this window)")
            # always pin the event corridor at the top, then the highest-forecast others
            top = plot[~plot["is_event"]].head(8)
            show = pd.concat([plot[plot["is_event"]], top])[["corridor", "pred_txt", "is_event"]].copy()
            show["corridor"] = show.apply(
                lambda r: f"★ {r['corridor']}" if r["is_event"] else r["corridor"], axis=1)
            st.dataframe(show[["corridor", "pred_txt"]].rename(
                columns={"pred_txt": "forecast (events/3h)"}), width="stretch", hide_index=True)
    else:
        only_event = st.checkbox("Only event-driven causes (public_event, procession, VIP, protest, construction)", False)
        mdf = df[df["is_event_driven"]] if only_event else df
        mdf = mdf[(mdf["latitude"].between(12.6, 13.3)) & (mdf["longitude"].between(77.3, 77.9))]
        st.pydeck_chart(pdk.Deck(
            map_style=None,
            initial_view_state=pdk.ViewState(latitude=12.97, longitude=77.59, zoom=10.5, pitch=40),
            layers=[pdk.Layer("HexagonLayer", data=mdf[["latitude", "longitude"]],
                              get_position="[longitude, latitude]", radius=400, elevation_scale=8,
                              extruded=True, pickable=True, coverage=0.9)],
        ))
        st.caption(f"{len(mdf):,} historical events plotted. Taller/brighter hexes = more events.")

# ---------------------------------------------------------------- Tab 3: analytics
with tab3:
    scenario_banner()
    st.subheader("Historical patterns")

    # --- scope filter: city-wide (default) or a specific corridor/zone ---
    ALL = "All (city-wide)"
    # Resolve the 'follow planner' lock BEFORE rendering the dropdown, so the box always
    # displays exactly the corridor the charts use (no label/data mismatch).
    scen = st.session_state.get("scenario")
    # auto-follow the scenario by default once a prediction exists, so this tab opens already
    # scoped to the corridor the user asked about (uncheck to explore freely).
    sync = st.checkbox("🔗 Follow Event Planner's corridor", value=bool(scen))
    planner_corr = scen["corridor"] if scen else st.session_state.get("planner_corridor")
    locked = bool(sync and planner_corr in CORRIDORS)
    if locked:
        st.session_state["ana_corridor"] = planner_corr   # force the dropdown to match

    f1, f2 = st.columns(2)
    with f1:
        corr_scope = st.selectbox("Corridor scope", [ALL] + CORRIDORS, key="ana_corridor",
                                  disabled=locked)
        if locked:
            st.caption(f"🔗 Locked to Event Planner → **{planner_corr}**")
    with f2:
        # zone options depend on the chosen corridor — corridors & zones are largely independent,
        # so only ~90/242 combos exist; restricting avoids "no events match" dead ends.
        if corr_scope == ALL:
            zone_opts = ZONES
        else:
            zone_opts = sorted(z for z in df[df["corridor"] == corr_scope]["zone"].unique()
                               if z != "unknown")
        zone_scope = st.selectbox("Zone scope", [ALL] + zone_opts)  # no key: resets when corridor changes

    fdf = df
    if corr_scope != ALL:
        fdf = fdf[fdf["corridor"] == corr_scope]
    if zone_scope != ALL:
        fdf = fdf[fdf["zone"] == zone_scope]

    scope_label = " · ".join([s for s in [
        None if corr_scope == ALL else corr_scope,
        None if zone_scope == ALL else zone_scope] if s]) or "City-wide"

    if fdf.empty:
        st.warning("No events match this scope.")
    else:
        # --- stats header for the selected scope ---
        busiest_hour = int(fdf.groupby("hour").size().idxmax())
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Events", f"{len(fdf):,}")
        k2.metric("High-priority", f"{fdf['is_high_priority'].mean():.0%}")
        k3.metric("Need road closure", f"{fdf['requires_road_closure'].mean():.0%}")
        k4.metric("Median clearance", fmt_dur(fdf["duration_min"].median()))
        k5.metric("Busiest hour", f"{busiest_hour:02d}:00")
        st.caption(f"Scope: **{scope_label}** ({len(fdf):,} of {len(df):,} events)")

        # --- confidence panel: does history back the model's prediction for this scenario? ---
        if scen and corr_scope == scen["corridor"]:
            p = scen["pred"]
            on_corr = df[df["corridor"] == scen["corridor"]]
            same_cause = on_corr[on_corr["event_cause"] == scen["cause"]]
            base = same_cause if len(same_cause) >= 5 else on_corr   # need a few to be meaningful
            basis = (f"{len(base):,} past **{scen['cause']}** events on this corridor"
                     if base is same_cause else
                     f"{len(base):,} past events on this corridor (too few '{scen['cause']}' to isolate)")
            h_clo = float(base["requires_road_closure"].mean())
            h_high = float(base["is_high_priority"].mean())
            h_dur = float(base["duration_min"].median())

            st.markdown(f"##### 🔎 Does history back the prediction? — {scen['corridor']} / {scen['cause']}")
            d1, d2, d3 = st.columns(3)
            d1.metric("Road-closure prob (model)", f"{p['road_closure_prob']:.0%}",
                      delta=f"{(p['road_closure_prob'] - h_clo):+.0%} vs history",
                      delta_color="off")
            d1.caption(f"History: **{h_clo:.0%}** needed a closure")
            d2.metric("Priority (model)", p["predicted_priority"])
            d2.caption(f"History: **{h_high:.0%}** were high-priority")
            d3.metric("Clearance (model)", fmt_dur(p["expected_duration_min"]),
                      delta=f"{(p['expected_duration_min'] - h_dur):+.0f} min vs history",
                      delta_color="off")
            d3.caption(f"History: median **{fmt_dur(h_dur)}**")
            agree = abs(p["road_closure_prob"] - h_clo) <= 0.15
            st.caption(("✅ The prediction is **in line with** " if agree
                        else "⚠️ The prediction **diverges from** ")
                       + f"what actually happened here — based on {basis}. "
                       "Use this to sanity-check the model before committing officers.")

        a, b = st.columns(2)
        with a:
            by_cause = fdf["event_cause"].value_counts().head(12).reset_index()
            by_cause.columns = ["cause", "count"]
            st.plotly_chart(px.bar(by_cause, x="count", y="cause", orientation="h",
                                   title=f"Events by cause — {scope_label}"), width="stretch")
            by_hour = fdf.groupby("hour").size().reset_index(name="count")
            st.plotly_chart(px.line(by_hour, x="hour", y="count", markers=True,
                                   title="Events by hour of day (IST)"), width="stretch")
        with b:
            # if filtered to one corridor, corridor chart is uninformative -> show junctions instead
            if corr_scope != ALL and "junction" in fdf.columns:
                known_j = fdf[fdf["junction"] != "unknown"]
                top = known_j["junction"].value_counts().head(12).reset_index()
                top.columns = ["junction", "count"]
                st.plotly_chart(px.bar(top, x="count", y="junction", orientation="h",
                                       title=f"Top junctions — {corr_scope}"), width="stretch")
                st.caption(f"⚠️ Based on the {len(known_j):,}/{len(fdf):,} events with a recorded "
                           f"junction ({len(known_j)/len(fdf):.0%}); the rest are unlabelled.")
            else:
                top = fdf["corridor"].value_counts().head(12).reset_index()
                top.columns = ["corridor", "count"]
                st.plotly_chart(px.bar(top, x="count", y="corridor", orientation="h",
                                       title="Top corridors by event volume"), width="stretch")
            daily = fdf.groupby("date").size().reset_index(name="count")
            st.plotly_chart(px.line(daily, x="date", y="count", title="Events per day"),
                            width="stretch")

        st.markdown(f"##### Cause × road-closure — {scope_label}")
        st.caption("Road-closure is the predictive impact label (priority is just a corridor rule). "
                   "This shows which causes actually drive closures.")
        ct = pd.crosstab(fdf["event_cause"], fdf["requires_road_closure"].map({True: "closure", False: "no closure"}))
        if "closure" in ct.columns:
            ct = ct.sort_values("closure", ascending=False)
        st.dataframe(ct, width="stretch")

        # ---- "Tell me more" — extra supporting breakdowns, hidden until asked for ----
        st.markdown("#### 🔬 More detail")
        st.caption("Deeper breakdowns for this scope — open what you need. Every table respects the "
                   "corridor/zone filter above (and the active scenario when synced).")

        with st.expander("🛣️ Corridor breakdown (closure rate, clearance, priority)"):
            cg = df.groupby("corridor").agg(
                events=("corridor", "size"),
                closure_rate=("requires_road_closure", "mean"),
                high_priority=("is_high_priority", "mean"),
                median_clearance_min=("duration_min", "median"),
                busiest_hour=("hour", lambda s: int(s.value_counts().idxmax())),
            ).reset_index().sort_values("events", ascending=False)
            cg["closure_rate"] = (cg["closure_rate"] * 100).round(0)
            cg["high_priority"] = (cg["high_priority"] * 100).round(0)
            cg["median_clearance_min"] = cg["median_clearance_min"].round(0)
            cg = cg.rename(columns={"closure_rate": "closure %", "high_priority": "high-priority %",
                                    "median_clearance_min": "median clearance (min)"})
            if scen:
                cg = cg.copy()
                cg["corridor"] = cg["corridor"].apply(
                    lambda c: f"★ {c}" if c == scen["corridor"] else c)
            st.dataframe(cg, width="stretch", hide_index=True)

        with st.expander("📍 Zone breakdown for this scope"):
            zg = fdf[fdf["zone"] != "unknown"].groupby("zone").agg(
                events=("zone", "size"),
                closure_rate=("requires_road_closure", "mean"),
                median_clearance_min=("duration_min", "median"),
            ).reset_index().sort_values("events", ascending=False)
            if zg.empty:
                st.info("No labelled zones in this scope.")
            else:
                zg["closure_rate"] = (zg["closure_rate"] * 100).round(0)
                zg["median_clearance_min"] = zg["median_clearance_min"].round(0)
                st.dataframe(zg.rename(columns={"closure_rate": "closure %",
                             "median_clearance_min": "median clearance (min)"}),
                             width="stretch", hide_index=True)

        with st.expander("🕒 Time patterns (hour × day-of-week heatmap)"):
            order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            heat = fdf.groupby(["dow", "hour"]).size().reset_index(name="events")
            pivot = heat.pivot(index="dow", columns="hour", values="events").reindex(order).fillna(0)
            fig = px.imshow(pivot, aspect="auto", color_continuous_scale="YlOrRd",
                            labels={"x": "Hour (IST)", "y": "", "color": "events"},
                            title=f"When do events happen? — {scope_label}")
            if scen:
                fig.add_vline(x=scen["hour"], line_dash="dash", line_color="#0078ff")
                st.caption(f"🔵 Dashed line marks your scenario hour ({scen['hour']:02d}:00 on {scen['day']}).")
            st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- Tab 4: post-event learning
with tab4:
    st.subheader("🔁 Post-Event Learning Loop")
    st.caption("Closes the loop: **predict → log → record what actually happened → learn**. The "
               "system compares predictions against real outcomes and auto-corrects future "
               "predictions — so deployment stops being gut-feel and the city gets smarter over time.")

    log = feedback.load_log()
    metrics = feedback.learning_metrics()
    calib = feedback.load_calibration()

    if log.empty:
        st.info("No predictions logged yet. Log one from the **Event Planner** tab, or seed the loop "
                "with real historical outcomes below to see it work end-to-end.")
        if st.button("🌱 Seed loop with 40 real historical events (demo)"):
            with st.spinner("Predicting historical events and recording their true outcomes…"):
                n = feedback.seed_from_history(40)
            st.success(f"Seeded {n} prediction-vs-actual pairs and learned an initial calibration.")
            st.rerun()
    else:
        # ---- learning scoreboard ----
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Predictions logged", metrics["n_logged"])
        m2.metric("Reviewed (have actuals)", metrics["n_resolved"])
        m3.metric("Closure-call accuracy",
                  "—" if metrics["closure_accuracy"] is None else f"{metrics['closure_accuracy']:.0%}")
        if metrics["duration_mae_raw"] is not None:
            delta = None if metrics["duration_mae_calibrated"] is None else \
                round(metrics["duration_mae_calibrated"] - metrics["duration_mae_raw"], 1)
            m4.metric("Clearance error (MAE)", f"{metrics['duration_mae_raw']:.0f} min",
                      delta=None if delta is None else f"{delta:+.0f} min after learning",
                      delta_color="inverse")
        else:
            m4.metric("Clearance error (MAE)", "—")

        # ---- what the loop has learned ----
        st.markdown("##### What the loop has learned")
        if calib.get("active"):
            df_f = calib["duration_factor"]
            shift = calib["closure_prob_shift"]
            dpct = (df_f - 1) * 100
            st.success(
                f"✅ Calibration **active** (from {calib['n_resolved']} reviewed events). "
                f"Future predictions are auto-adjusted: clearance ×**{df_f:.2f}** "
                f"({dpct:+.0f}% — the model was running {'short' if dpct>0 else 'long'}), "
                f"closure probability **{shift:+.0%}**. These corrections apply across all tabs.")
        else:
            st.warning(f"Calibration inactive — need ≥{feedback.MIN_FOR_CALIB} reviewed events "
                       f"(have {metrics['n_resolved']}). Record outcomes below to activate it.")

        # ---- record actuals for a logged prediction ----
        st.markdown("##### Record what actually happened")
        pending = log[~log["resolved"].astype("boolean").fillna(False)]
        if pending.empty:
            st.caption("No predictions awaiting review. ✅")
        else:
            opts = {f"{r['id']} · {r['event_cause']} · {r['corridor']} · {r['day']} {int(r['hour']):02d}:00 "
                    f"(pred: {float(r['pred_closure_prob']):.0%} closure, {fmt_dur(r['pred_duration_min'])})": r["id"]
                    for _, r in pending.iterrows()}
            pick = st.selectbox("Pending prediction", list(opts.keys()))
            with st.form("record_actual"):
                ac1, ac2, ac3 = st.columns(3)
                a_clo = ac1.radio("Did it need a road closure?", ["yes", "no"], horizontal=True)
                a_dur = ac2.number_input("Actual clearance (minutes)", 0, 48 * 60, 60)
                a_high = ac3.radio("Was it high-priority?", ["yes", "no"], horizontal=True)
                if st.form_submit_button("Save outcome & learn", type="primary"):
                    feedback.record_actual(opts[pick], actual_closure=(a_clo == "yes"),
                                           actual_duration_min=float(a_dur),
                                           actual_high_priority=(a_high == "yes"))
                    st.success("Outcome recorded — calibration refreshed.")
                    st.rerun()

        # ---- accuracy trend + raw log ----
        with st.expander("📈 Prediction vs actual (reviewed events)"):
            done = log[log["resolved"].astype("boolean").fillna(False)].dropna(
                subset=["actual_duration_min", "pred_duration_min"])
            if done.empty:
                st.caption("No reviewed events with clearance actuals yet.")
            else:
                comp = done[["pred_duration_min", "actual_duration_min"]].astype(float)
                fig = px.scatter(comp, x="pred_duration_min", y="actual_duration_min",
                                 labels={"pred_duration_min": "Predicted clearance (min)",
                                         "actual_duration_min": "Actual clearance (min)"},
                                 title="Clearance: predicted vs actual (points on the diagonal = perfect)")
                hi = float(max(comp.max().max(), 1))
                fig.add_shape(type="line", x0=0, y0=0, x1=hi, y1=hi, line=dict(dash="dash"))
                st.plotly_chart(fig, width="stretch")

        with st.expander("🗂️ Feedback log"):
            st.dataframe(log.sort_values("predicted_at", ascending=False), width="stretch", hide_index=True)

        st.divider()
        b1, b2, b3 = st.columns(3)
        if b1.button("🌱 Add 40 more historical samples"):
            n = feedback.seed_from_history(40, seed=int(pd.Timestamp.now().value % 100000))
            st.success(f"Added {n} samples.")
            st.rerun()
        if b2.button("🔄 Recompute calibration"):
            feedback.update_calibration()
            st.success("Recomputed from current feedback.")
            st.rerun()
        if b3.button("🗑️ Clear feedback log"):
            feedback.LOG_PATH.unlink(missing_ok=True)
            feedback.CALIB_PATH.unlink(missing_ok=True)
            st.rerun()
