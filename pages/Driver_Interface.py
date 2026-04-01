from datetime import datetime

import streamlit as st

from shuttle_simulation import initialize_simulation_state


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
        height: 100px;
        font-size: 20px;
        font-weight: 700;
    }
</style>
""",
    unsafe_allow_html=True,
)

initialize_simulation_state()

st.title("🚗 Driver Interface")
st.markdown("### Quick-Tap Status Updates")
st.caption("Driver actions update the same simulated fleet shown on the live map.")

st.sidebar.header("Driver Info")
driver_name = st.sidebar.text_input("Driver Name:", value="Mike")
shuttle_options = list(st.session_state.shuttle_data.keys())
selected_shuttle = st.sidebar.selectbox(
    "Shuttle:",
    shuttle_options,
    format_func=lambda shuttle_id: st.session_state.shuttle_data[shuttle_id]["label"],
)

st.sidebar.divider()
st.sidebar.info("Tap a button to publish an instant rider-facing update.")

shuttle = st.session_state.shuttle_data[selected_shuttle]

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Current Stop", shuttle["current_stop"])
with col2:
    st.metric("Next Stop", shuttle["next_stop"])
with col3:
    st.metric("Route", shuttle["route"])

st.divider()
st.markdown("### 📢 Quick Status Updates")


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


left, right = st.columns(2)
with left:
    if st.button("⏱️ Running 5 Min Late", use_container_width=True):
        shuttle["on_time"] = False
        add_update("delay", "Running 5 minutes late")
        st.warning("Delay update sent to riders.")

    if st.button("🚨 Running 10+ Min Late", use_container_width=True):
        shuttle["on_time"] = False
        add_update("major_delay", "Running 10+ minutes late")
        st.error("Major delay alert sent.")

with right:
    if st.button("👥 At Capacity (Full)", use_container_width=True):
        shuttle["capacity_pct"] = 95
        add_update("capacity", "Shuttle at full capacity")
        st.warning("Capacity alert sent.")

    if st.button("✅ Back on Schedule", use_container_width=True):
        shuttle["on_time"] = True
        add_update("on_time", "Back on schedule")
        st.success("Status updated to on time.")

st.divider()
extra1, extra2, extra3 = st.columns(3)
with extra1:
    if st.button("🚧 Construction Delay", use_container_width=True):
        shuttle["on_time"] = False
        add_update("construction", "Construction causing delays")
        st.warning("Construction delay reported.")
with extra2:
    if st.button("❄️ Weather Delay", use_container_width=True):
        shuttle["on_time"] = False
        add_update("weather", "Weather causing delays")
        st.info("Weather delay reported.")
with extra3:
    if st.button("🔄 Route Changed", use_container_width=True):
        add_update("route_change", "Route temporarily changed")
        st.warning("Route change reported.")

st.divider()
st.markdown("### 📝 Your Recent Updates")
if st.session_state.driver_updates:
    for update in reversed(st.session_state.driver_updates[-5:]):
        st.info(f"🕐 {update['time'].strftime('%I:%M %p')} - {update['message']}")
else:
    st.caption("No updates sent yet today")

st.divider()
impact1, impact2, impact3 = st.columns(3)
with impact1:
    st.metric("Updates Sent", len(st.session_state.driver_updates))
with impact2:
    delay_updates = sum(1 for update in st.session_state.driver_updates if "delay" in update["type"])
    st.metric("Delay Alerts", delay_updates)
with impact3:
    capacity_updates = sum(1 for update in st.session_state.driver_updates if update["type"] == "capacity")
    st.metric("Capacity Updates", capacity_updates)

st.success("Your updates feed directly into the live rider view.")
