from datetime import datetime

import streamlit as st

from shuttle_simulation import DEFAULT_SHUTTLES, initialize_simulation_state


st.set_page_config(
    page_title="Driver Interface - BC Shuttle Tracker",
    page_icon="🚗",
    layout="wide",
)

st.markdown(
    """
<style>
    .stButton>button {
        width: 100%;
        height: 90px;
        font-size: 18px;
        font-weight: 700;
    }
    .shuttle-header {
        background: #f4f6fb;
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 20px;
        border-left: 6px solid #1d4ed8;
    }
</style>
""",
    unsafe_allow_html=True,
)

initialize_simulation_state()

st.title("🚗 Driver Interface")
st.caption("Driver actions update the same simulated fleet shown on the live map.")

st.sidebar.header("Driver Info")
driver_name = st.sidebar.text_input("Driver Name:", value="Mike")
st.sidebar.divider()
st.sidebar.info("Select the bus you are driving below, then tap a button to publish an instant rider-facing update.")

# --- Shuttle selector ---
st.markdown("### Select Your Bus")
shuttle_options = list(st.session_state.shuttle_data.keys())
selected_shuttle = st.selectbox(
    "Which bus are you driving?",
    shuttle_options,
    format_func=lambda sid: st.session_state.shuttle_data[sid]["label"],
)

shuttle = st.session_state.shuttle_data[selected_shuttle]
base_speed = DEFAULT_SHUTTLES[selected_shuttle]["speed_mph"]

# Read status from driver_shuttle_overrides (never reset by initialize_simulation_state)
overrides = st.session_state.driver_shuttle_overrides.get(selected_shuttle, {})
delay = overrides.get("delay_minutes", 0)
is_express = overrides.get("is_express", False)

if delay > 0:
    delay_status = f"⚠️ +{delay} min delay"
    delay_color = "#dc2626"
elif delay < 0:
    delay_status = f"⏰ Running {abs(delay)} min early"
    delay_color = "#16a34a"
else:
    delay_status = "✅ On time"
    delay_color = "#16a34a"

express_status = "🚀 Express mode ON" if is_express else "🛑 All stops"
express_color = "#7c3aed" if is_express else "#6b7280"

st.markdown(
    f"""
    <div class="shuttle-header">
        <div style="font-size:1.2rem;font-weight:700;">Updating: {shuttle['label']}</div>
        <div style="color:#6b7280;margin-top:4px;">Route: {shuttle['route']}</div>
        <div style="margin-top:10px;display:flex;gap:1rem;flex-wrap:wrap;">
            <span style="color:{delay_color};font-weight:700;">{delay_status}</span>
            <span style="color:{express_color};font-weight:700;">{express_status}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Current Stop", shuttle["current_stop"])
with col2:
    st.metric("Next Stop", shuttle["next_stop"])
with col3:
    st.metric("Route", shuttle["route"])

st.divider()


def set_override(key: str, value) -> None:
    """Persist a driver override so it survives shuttle_data rebuilds."""
    st.session_state.driver_shuttle_overrides.setdefault(selected_shuttle, {})[key] = value
    st.session_state.shuttle_data[selected_shuttle][key] = value


def clear_override(key: str) -> None:
    st.session_state.driver_shuttle_overrides.get(selected_shuttle, {}).pop(key, None)
    st.session_state.shuttle_data[selected_shuttle].pop(key, None)


def add_update(update_type: str, message: str) -> None:
    st.session_state.driver_updates.append(
        {
            "driver": driver_name,
            "shuttle": selected_shuttle,
            "type": update_type,
            "message": message,
            "time": datetime.now(),
        }
    )
    st.session_state.recent_updates.append(
        {
            "time": datetime.now().strftime("%I:%M %p"),
            "message": f"🚗 {st.session_state.shuttle_data[selected_shuttle]['label']}: {message}",
        }
    )


# --- Delay / On-time updates ---
st.markdown("### ⏱️ Delay Status")
left, right = st.columns(2)
with left:
    if st.button("⏱️ Running 5 Min Late", use_container_width=True):
        set_override("on_time", False)
        set_override("delay_minutes", 5)
        add_update("delay", "Running 5 minutes late")
        st.toast("Delay update sent to riders.", icon="⏱️")
        st.rerun()

    if st.button("🚨 Running 10+ Min Late", use_container_width=True):
        set_override("on_time", False)
        set_override("delay_minutes", 10)
        add_update("major_delay", "Running 10+ minutes late")
        st.toast("Major delay alert sent.", icon="🚨")
        st.rerun()

with right:
    if st.button("⏰ Arrived / Running Early", use_container_width=True):
        set_override("on_time", True)
        set_override("delay_minutes", -2)
        add_update("early", "Running approximately 2 minutes early")
        st.toast("Early arrival notice sent to riders.", icon="⏰")
        st.rerun()

    if st.button("✅ Back on Schedule", use_container_width=True):
        set_override("on_time", True)
        set_override("delay_minutes", 0)
        set_override("speed_mph", base_speed)
        add_update("on_time", "Back on schedule")
        st.toast("Status updated to on time.", icon="✅")
        st.rerun()

st.divider()

# --- Express / stops ---
st.markdown("### 🚀 Service Mode")
mode_left, mode_right = st.columns(2)
with mode_left:
    if st.button("🚀 Running Express (Skip Stops)", use_container_width=True):
        set_override("is_express", True)
        set_override("speed_mph", round(base_speed * 1.35))
        add_update("express", "Running express — limited stops")
        st.toast("Express mode activated. Riders notified.", icon="🚀")
        st.rerun()

with mode_right:
    if st.button("🛑 Resuming All Stops", use_container_width=True):
        set_override("is_express", False)
        set_override("speed_mph", base_speed)
        add_update("all_stops", "Resuming service at all stops")
        st.toast("Returned to all-stops service.", icon="🛑")
        st.rerun()

st.divider()

# --- Capacity / other alerts ---
st.markdown("### 📢 Other Updates")
extra1, extra2 = st.columns(2)
with extra1:
    if st.button("👥 At Capacity (Full)", use_container_width=True):
        set_override("capacity_pct", 95)
        add_update("capacity", "Shuttle at full capacity")
        st.toast("Capacity alert sent.", icon="👥")
        st.rerun()
with extra2:
    if st.button("🔄 Route Changed", use_container_width=True):
        add_update("route_change", "Route temporarily changed")
        st.toast("Route change reported.", icon="🔄")
        st.rerun()

extra3, extra4 = st.columns(2)
with extra3:
    if st.button("🚧 Construction Delay", use_container_width=True):
        set_override("on_time", False)
        add_update("construction", "Construction causing delays")
        st.toast("Construction delay reported.", icon="🚧")
        st.rerun()
with extra4:
    if st.button("❄️ Weather Delay", use_container_width=True):
        set_override("on_time", False)
        add_update("weather", "Weather causing delays")
        st.toast("Weather delay reported.", icon="❄️")
        st.rerun()

st.divider()

# --- Recent updates log ---
st.markdown("### 📝 Your Recent Updates")
if st.session_state.driver_updates:
    for update in reversed(st.session_state.driver_updates[-5:]):
        shuttle_label = st.session_state.shuttle_data[update["shuttle"]]["label"]
        st.info(f"🕐 {update['time'].strftime('%I:%M %p')} · **{shuttle_label}** — {update['message']}")
else:
    st.caption("No updates sent yet today")

st.divider()
impact1, impact2, impact3 = st.columns(3)
with impact1:
    st.metric("Updates Sent", len(st.session_state.driver_updates))
with impact2:
    delay_updates = sum(1 for u in st.session_state.driver_updates if "delay" in u["type"])
    st.metric("Delay Alerts", delay_updates)
with impact3:
    capacity_updates = sum(1 for u in st.session_state.driver_updates if u["type"] == "capacity")
    st.metric("Capacity Updates", capacity_updates)

st.success("Your updates feed directly into the live rider view and map.")
