from datetime import datetime

import pandas as pd
import streamlit as st

from shuttle_simulation import initialize_simulation_state


st.set_page_config(
    page_title="Dispatcher Override - BC Shuttle Tracker",
    page_icon="🎛️",
    layout="wide",
)

initialize_simulation_state()

st.title("🎛️ Dispatcher Override Panel")
st.markdown("### System-Wide Controls & Emergency Overrides")
st.caption("Dispatcher actions feed into the live map alerts and shuttle state.")

st.sidebar.header("Dispatcher Info")
dispatcher_name = st.sidebar.text_input("Name:", value="Admin")
st.sidebar.divider()
st.sidebar.warning("Use override powers carefully. These updates affect all riders.")

st.markdown("### 📊 System Status Overview")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Active Shuttles", len(st.session_state.shuttle_data))
with col2:
    on_time = sum(1 for shuttle in st.session_state.shuttle_data.values() if shuttle["on_time"])
    st.metric("On Time", f"{on_time}/{len(st.session_state.shuttle_data)}")
with col3:
    full_count = sum(1 for shuttle in st.session_state.shuttle_data.values() if shuttle["capacity_pct"] >= 85)
    st.metric("At Capacity", full_count)
with col4:
    st.metric("Active Alerts", len(st.session_state.system_alerts))

st.divider()
st.markdown("### 🚨 Emergency Overrides")

left, right = st.columns(2)
with left:
    delay_minutes = st.number_input("Add delay to all shuttles (minutes):", min_value=0, max_value=60, value=5, step=5)
    delay_reason = st.selectbox(
        "Reason:",
        ["Weather Emergency", "Campus-Wide Event", "Security Incident", "Maintenance", "Other"],
    )

    if st.button("Apply System-Wide Delay", type="primary"):
        st.session_state.dispatcher_overrides.append(
            {
                "dispatcher": dispatcher_name,
                "type": "system_delay",
                "delay_minutes": delay_minutes,
                "reason": delay_reason,
                "time": datetime.now(),
            }
        )
        for shuttle in st.session_state.shuttle_data.values():
            shuttle["on_time"] = False
        st.session_state.system_alerts.append(
            {
                "type": "delay",
                "message": f"{delay_reason}: all shuttles delayed {delay_minutes} minutes",
                "time": datetime.now(),
            }
        )
        st.session_state.recent_updates.append(
            {
                "time": datetime.now().strftime("%I:%M %p"),
                "message": f"🚨 Dispatch: {delay_reason} - {delay_minutes} min delay",
            }
        )
        st.error(f"System-wide {delay_minutes}-minute delay activated.")

with right:
    shuttle_choices = ["All Shuttles"] + list(st.session_state.shuttle_data.keys())
    affected_shuttle = st.selectbox(
        "Select shuttle:",
        shuttle_choices,
        format_func=lambda option: "All Shuttles" if option == "All Shuttles" else st.session_state.shuttle_data[option]["label"],
    )
    route_status = st.radio("Route Status:", ["Temporary Detour", "Skip Next Stop", "Service Suspended"])
    route_notes = st.text_area("Route change details:", placeholder="Example: Avoiding road closure on Commonwealth Ave")

    if st.button("Override Route", type="primary"):
        st.session_state.dispatcher_overrides.append(
            {
                "dispatcher": dispatcher_name,
                "type": "route_override",
                "shuttle": affected_shuttle,
                "status": route_status,
                "notes": route_notes,
                "time": datetime.now(),
            }
        )
        st.session_state.system_alerts.append(
            {
                "type": "route",
                "message": f"{affected_shuttle}: {route_status}",
                "time": datetime.now(),
            }
        )
        st.session_state.recent_updates.append(
            {
                "time": datetime.now().strftime("%I:%M %p"),
                "message": f"🔄 Dispatch: {affected_shuttle} - {route_status}",
            }
        )
        st.warning(f"Route override applied to {affected_shuttle}.")

st.divider()
st.markdown("### 🔔 Active System Alerts")
if st.session_state.system_alerts:
    for alert in reversed(st.session_state.system_alerts[-10:]):
        timestamp = alert["time"].strftime("%I:%M %p")
        if alert["type"] == "delay":
            st.error(f"🚨 {timestamp} - {alert['message']}")
        else:
            st.warning(f"🔄 {timestamp} - {alert['message']}")
else:
    st.success("No active alerts. All services normal.")

st.divider()
st.markdown("### 📜 Override History")
if st.session_state.dispatcher_overrides:
    rows = []
    for override in reversed(st.session_state.dispatcher_overrides[-20:]):
        rows.append(
            {
                "Time": override["time"].strftime("%I:%M %p"),
                "Dispatcher": override["dispatcher"],
                "Type": override["type"].replace("_", " ").title(),
                "Details": override.get("reason", override.get("status", "N/A")),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("No overrides have been issued today.")
