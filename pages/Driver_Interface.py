import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="Driver Interface - BC Shuttle Tracker",
    page_icon="🚗",
    layout="wide"
)

# Custom CSS for large driver-safe buttons
st.markdown("""
<style>
    .driver-button {
        font-size: 24px !important;
        padding: 2rem !important;
        margin: 1rem 0 !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
    }
    .stButton>button {
        width: 100%;
        height: 100px;
        font-size: 20px;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

st.title("🚗 Driver Interface")
st.markdown("### Quick-Tap Status Updates")
st.caption("Large buttons designed for driver safety - no typing while driving!")

# Initialize session state
if 'shuttle_data' not in st.session_state:
    st.session_state.shuttle_data = {
        'shuttle_1': {
            'current_stop': 'Library',
            'next_stop': 'Student Center',
            'capacity': 'Medium',
            'on_time': True
        }
    }

if 'driver_updates' not in st.session_state:
    st.session_state.driver_updates = []

if 'recent_updates' not in st.session_state:
    st.session_state.recent_updates = []

# Driver selection
st.sidebar.header("Driver Info")
driver_name = st.sidebar.text_input("Driver Name:", value="Mike")
shuttle_id = st.sidebar.selectbox("Shuttle:", ["Shuttle 1", "Shuttle 2"])

st.sidebar.divider()
st.sidebar.info("👆 Tap a button below to send instant updates to all riders")

# Current status display
col1, col2, col3 = st.columns(3)

shuttle = st.session_state.shuttle_data['shuttle_1']

with col1:
    st.metric("Current Location", shuttle['current_stop'])

with col2:
    st.metric("Next Stop", shuttle['next_stop'])

with col3:
    status_emoji = "✅" if shuttle['on_time'] else "⏰"
    status_text = "On Time" if shuttle['on_time'] else "Delayed"
    st.metric("Status", f"{status_emoji} {status_text}")

st.divider()

# Main action buttons - 2x2 grid
st.markdown("### 📢 Quick Status Updates")

col1, col2 = st.columns(2)

with col1:
    # Running Late Button
    if st.button(
        "⏱️ Running 5 Min Late",
        use_container_width=True,
        key="late_5"
    ):
        update = {
            'driver': driver_name,
            'shuttle': shuttle_id,
            'type': 'delay',
            'message': 'Running 5 minutes late',
            'time': datetime.now()
        }
        st.session_state.driver_updates.append(update)
        st.session_state.shuttle_data['shuttle_1']['on_time'] = False
        
        st.session_state.recent_updates.append({
            'time': datetime.now().strftime('%I:%M %p'),
            'message': f'⏱️ Driver: Running 5 min late'
        })
        
        st.success("✅ Update sent! All riders notified of 5-minute delay.")
        st.balloons()

    st.markdown("")
    
    # Running Very Late Button
    if st.button(
        "🚨 Running 10+ Min Late",
        use_container_width=True,
        key="late_10"
    ):
        update = {
            'driver': driver_name,
            'shuttle': shuttle_id,
            'type': 'major_delay',
            'message': 'Running 10+ minutes late',
            'time': datetime.now()
        }
        st.session_state.driver_updates.append(update)
        st.session_state.shuttle_data['shuttle_1']['on_time'] = False
        
        st.session_state.recent_updates.append({
            'time': datetime.now().strftime('%I:%M %p'),
            'message': f'🚨 Driver: Running 10+ min late'
        })
        
        st.error("🚨 Major delay alert sent to all riders!")

with col2:
    # At Capacity Button
    if st.button(
        "👥 At Capacity (Full)",
        use_container_width=True,
        key="full"
    ):
        update = {
            'driver': driver_name,
            'shuttle': shuttle_id,
            'type': 'capacity',
            'message': 'Shuttle at full capacity',
            'time': datetime.now()
        }
        st.session_state.driver_updates.append(update)
        st.session_state.shuttle_data['shuttle_1']['capacity'] = 'Full'
        st.session_state.shuttle_data['shuttle_1']['capacity_pct'] = 95
        
        st.session_state.recent_updates.append({
            'time': datetime.now().strftime('%I:%M %p'),
            'message': f'👥 Driver: Shuttle at capacity'
        })
        
        st.warning("⚠️ Capacity alert sent! Waiting riders will be notified.")
    
    st.markdown("")
    
    # Back on Schedule Button
    if st.button(
        "✅ Back on Schedule",
        use_container_width=True,
        key="on_time"
    ):
        update = {
            'driver': driver_name,
            'shuttle': shuttle_id,
            'type': 'on_time',
            'message': 'Back on schedule',
            'time': datetime.now()
        }
        st.session_state.driver_updates.append(update)
        st.session_state.shuttle_data['shuttle_1']['on_time'] = True
        
        st.session_state.recent_updates.append({
            'time': datetime.now().strftime('%I:%M %p'),
            'message': f'✅ Driver: Back on schedule'
        })
        
        st.success("✅ Status updated! Riders know you're on time.")

st.divider()

# Additional status buttons
st.markdown("### 🚧 Special Situations")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🚧 Construction Delay", use_container_width=True):
        update = {
            'driver': driver_name,
            'shuttle': shuttle_id,
            'type': 'construction',
            'message': 'Construction causing delays',
            'time': datetime.now()
        }
        st.session_state.driver_updates.append(update)
        
        st.session_state.recent_updates.append({
            'time': datetime.now().strftime('%I:%M %p'),
            'message': f'🚧 Driver: Construction delay'
        })
        
        st.warning("🚧 Construction delay reported!")

with col2:
    if st.button("❄️ Weather Delay", use_container_width=True):
        update = {
            'driver': driver_name,
            'shuttle': shuttle_id,
            'type': 'weather',
            'message': 'Weather causing delays',
            'time': datetime.now()
        }
        st.session_state.driver_updates.append(update)
        
        st.session_state.recent_updates.append({
            'time': datetime.now().strftime('%I:%M %p'),
            'message': f'❄️ Driver: Weather delay'
        })
        
        st.info("❄️ Weather delay reported!")

with col3:
    if st.button("🔄 Route Changed", use_container_width=True):
        update = {
            'driver': driver_name,
            'shuttle': shuttle_id,
            'type': 'route_change',
            'message': 'Route temporarily changed',
            'time': datetime.now()
        }
        st.session_state.driver_updates.append(update)
        
        st.session_state.recent_updates.append({
            'time': datetime.now().strftime('%I:%M %p'),
            'message': f'🔄 Driver: Route changed'
        })
        
        st.warning("🔄 Route change reported!")

st.divider()

# Recent updates log
st.markdown("### 📝 Your Recent Updates")
if st.session_state.driver_updates:
    for update in reversed(st.session_state.driver_updates[-5:]):
        time_str = update['time'].strftime('%I:%M %p')
        st.info(f"🕐 {time_str} - {update['message']}")
else:
    st.caption("No updates sent yet today")

st.divider()

# Impact summary
st.markdown("### 📊 Your Impact Today")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Updates Sent", len(st.session_state.driver_updates))

with col2:
    delay_updates = sum(1 for u in st.session_state.driver_updates if u['type'] in ['delay', 'major_delay'])
    st.metric("Delay Alerts", delay_updates)

with col3:
    capacity_updates = sum(1 for u in st.session_state.driver_updates if u['type'] == 'capacity')
    st.metric("Capacity Updates", capacity_updates)

st.success("👏 Thank you for keeping riders informed! Your updates help everyone make better decisions.")
