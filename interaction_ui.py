from datetime import datetime

import streamlit as st

from shuttle_simulation import build_eta_prediction, display_stop_name


def apply_shared_styles() -> None:
    st.markdown(
        """
    <style>
        .stButton>button {
            width: 100%;
            border-radius: 8px;
            height: 3em;
            font-weight: 600;
        }
        .status-card {
            background: #f4f6fb;
            border-radius: 14px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .mini-route-chip {
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 999px;
            color: white;
            font-size: 0.8rem;
            font-weight: 700;
            margin-right: 0.4rem;
            margin-bottom: 0.4rem;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )


def confidence_display(confidence: int) -> tuple[str, str]:
    if confidence >= 80:
        return "#02C39A", "High"
    if confidence >= 60:
        return "#028090", "Medium"
    return "#FF6B6B", "Low"


def _capacity_signal_label(capacity_pct: int) -> str:
    if capacity_pct >= 85:
        return "Crowded / Full"
    if capacity_pct >= 55:
        return "Moderate"
    return "Seats Available"


def _record_feedback_adjustments(bus_id: str, arrival_accurate: str, capacity_accurate: str, actual_capacity_pct: int | None) -> None:
    if arrival_accurate == "Yes":
        st.session_state.feedback_history.append(
            {
                "type": "accurate",
                "time": datetime.now(),
                "stop": st.session_state.user_stop,
            }
        )
    else:
        st.session_state.feedback_history.append(
            {
                "type": "wrong",
                "issue": "Arrival prediction mismatch",
                "time": datetime.now(),
                "stop": st.session_state.user_stop,
            }
        )

    if capacity_accurate == "No" and actual_capacity_pct is not None:
        st.session_state.shuttle_data[bus_id]["capacity_pct"] = actual_capacity_pct
        st.session_state.feedback_history.append(
            {
                "type": "capacity_update",
                "capacity_pct": actual_capacity_pct,
                "time": datetime.now(),
                "stop": st.session_state.user_stop,
            }
        )


def _render_prediction_summary(selected_stop: str, eta: dict) -> None:
    best_match = eta["best_match"]
    conf_color, conf_label = confidence_display(eta["confidence"])

    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("### AI Prediction")
        if best_match:
            st.markdown(
                f"""
                <div class="status-card">
                    <div style="font-size:0.95rem;color:#6b7280;">For riders waiting at {display_stop_name(selected_stop)}</div>
                    <div style="font-size:2rem;font-weight:700;margin-top:0.35rem;">{eta['min']}-{eta['max']} min</div>
                    <div style="margin-top:0.5rem;">Bus: <strong>{best_match['label']}</strong></div>
                    <div>Route: <strong>{best_match['route']}</strong></div>
                    <div>Capacity prediction: <strong>{best_match['capacity']}</strong> ({best_match['capacity_pct']}%)</div>
                    <div>Current segment: {display_stop_name(best_match['current_stop'])} → {display_stop_name(best_match['next_stop'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with right:
        st.markdown("### Why the AI Believes This")
        st.markdown(
            f"""
            <div class="status-card">
                <div style="font-size:2rem;font-weight:700;color:{conf_color};">{eta['confidence']}%</div>
                <div style="color:#6b7280;">{conf_label} confidence</div>
                <div style="margin-top:0.5rem;color:#4b5563;">
                    The estimate combines shuttle position, route progress, average speed, stop dwell behavior, and recent rider corrections.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(eta["confidence"] / 100)


def _render_bus_checkin(selected_stop: str, eta: dict) -> None:
    st.markdown("### Human Check-In")
    st.caption("When you board a shuttle, tell the app whether the AI's arrival and crowding predictions were right.")

    arrivals = [eta["best_match"], *eta["alternatives"]] if eta["best_match"] else []
    arrivals = [item for item in arrivals if item]

    if not arrivals:
        st.info("No active shuttle prediction is available for this stop yet.")
        return

    options = {item["shuttle_id"]: item for item in arrivals}
    bus_id = st.selectbox(
        "Which shuttle did you get on?",
        list(options.keys()),
        format_func=lambda shuttle_id: f"{options[shuttle_id]['label']} • {options[shuttle_id]['route']}",
        key="feedback_bus_selector",
    )

    chosen = options[bus_id]
    st.markdown(
        f"""
        <div class="status-card">
            <div style="font-weight:700;">{chosen['label']}</div>
            <div style="color:#4b5563;margin-top:0.35rem;">Predicted arrival: {chosen['eta_minutes']} min</div>
            <div style="color:#4b5563;">Predicted crowding: {_capacity_signal_label(chosen['capacity_pct'])} ({chosen['capacity_pct']}%)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("I'm on this bus", type="primary", use_container_width=True):
        st.session_state.selected_feedback_bus_id = bus_id
        st.session_state.show_boarding_feedback_form = True
        st.rerun()

    if st.session_state.get("show_boarding_feedback_form") and st.session_state.get("selected_feedback_bus_id") == bus_id:
        st.markdown("#### Rider Feedback Form")
        arrival_accurate = st.radio(
            "Was the predicted arrival time accurate?",
            ["Yes", "No"],
            horizontal=True,
            key=f"arrival_accuracy_{bus_id}",
        )
        capacity_accurate = st.radio(
            "Was the predicted crowding/capacity accurate?",
            ["Yes", "No"],
            horizontal=True,
            key=f"capacity_accuracy_{bus_id}",
        )

        actual_capacity_pct = None
        if capacity_accurate == "No":
            actual_capacity_pct = st.select_slider(
                "What was the actual crowding like?",
                options=[25, 50, 70, 95],
                value=70,
                format_func=lambda value: {
                    25: "Seats Available",
                    50: "Half Full",
                    70: "Standing Room",
                    95: "Very Crowded / Full",
                }[value],
                key=f"actual_capacity_{bus_id}",
            )

        comment = st.text_area(
            "Optional comment",
            placeholder="Example: bus arrived later because it waited at the previous stop",
            key=f"feedback_comment_{bus_id}",
        )

        submit_col, cancel_col = st.columns(2)
        with submit_col:
            if st.button("Submit rider feedback", type="primary", use_container_width=True, key=f"submit_feedback_{bus_id}"):
                report = {
                    "type": "rider_boarding_feedback",
                    "bus_id": bus_id,
                    "bus_label": chosen["label"],
                    "route": chosen["route"],
                    "stop": selected_stop,
                    "submitted_at": datetime.now(),
                    "predicted_eta_minutes": chosen["eta_minutes"],
                    "predicted_capacity_pct": chosen["capacity_pct"],
                    "arrival_prediction_accurate": arrival_accurate,
                    "capacity_prediction_accurate": capacity_accurate,
                    "actual_capacity_pct": actual_capacity_pct,
                    "comment": comment,
                }
                st.session_state.rider_feedback_reports.append(report)
                _record_feedback_adjustments(bus_id, arrival_accurate, capacity_accurate, actual_capacity_pct)
                st.session_state.recent_updates.append(
                    {
                        "time": datetime.now().strftime("%I:%M %p"),
                        "message": f"📝 Rider feedback saved for {chosen['label']} on {chosen['route']}",
                    }
                )
                st.session_state.show_boarding_feedback_form = False
                st.session_state.selected_feedback_bus_id = None
                st.success("Feedback saved. The app can now use this rider report to improve trust and future estimates.")
                st.rerun()

        with cancel_col:
            if st.button("Cancel", use_container_width=True, key=f"cancel_feedback_{bus_id}"):
                st.session_state.show_boarding_feedback_form = False
                st.session_state.selected_feedback_bus_id = None
                st.rerun()


def _render_feedback_log() -> None:
    st.markdown("### Recent Human-in-the-Loop Reports")
    reports = st.session_state.rider_feedback_reports[-6:]
    if not reports:
        st.caption("No boarding feedback yet. This is where rider validation becomes visible.")
        return

    for report in reversed(reports):
        timestamp = report["submitted_at"].strftime("%I:%M %p")
        arrival_text = "arrival accurate" if report["arrival_prediction_accurate"] == "Yes" else "arrival inaccurate"
        capacity_text = "capacity accurate" if report["capacity_prediction_accurate"] == "Yes" else "capacity corrected"
        detail = f"{timestamp} • {report['bus_label']} • {report['route']} • {arrival_text}, {capacity_text}"
        if report["comment"]:
            st.info(f"{detail}\n{report['comment']}")
        else:
            st.info(detail)


def render_feedback_section(selected_stop: str) -> None:
    eta = build_eta_prediction(selected_stop)
    st.markdown("## Human + AI Verification")
    st.caption(
        "AI makes the first guess about arrival time and crowding. Riders validate that guess after they board so the tracker can improve over time."
    )

    _render_prediction_summary(selected_stop, eta)
    st.divider()
    _render_bus_checkin(selected_stop, eta)
    st.divider()
    _render_feedback_log()
