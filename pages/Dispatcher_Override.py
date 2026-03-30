import streamlit as st
from datetime import datetime
import pandas as pd

st.set_page_config(
    page_title="Dispatcher Override - BC Shuttle Tracker",
    page_icon="🎛️",
    layout="wide"
)

st.title("🎛️ Dispatcher Override Panel")
st.markdown("### System-Wide Controls & Emergency Overrides")
st.caption("Override AI predictions for special events, emergencies, or campus-wide changes")

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

if 'dispatcher_overrides' not in st.session_state:
    st.session_state.dispatcher_overrides = []

if 'recent_updates' not in st.session_state:
    st.session_state.recent_updates = []

if 'system_alerts' not in st.session_state:
    st.session_state.system_alerts = []

# Sidebar - Dispatcher info
st.sidebar.header("Dispatcher Info")
dispatcher_name = st.sidebar.text_input("Name:", value="Admin")
st.sidebar.divider()
st.sidebar.warning("⚠️ Use override powers responsibly. These affect all users system-wide.")

# System status overview
st.markdown("### 📊 System Status Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    active_shuttles = len(st.session_state.shuttle_data)
    st.metric("Active Shuttles", active_shuttles)

with col2:
    on_time_count = sum(1 for s in st.session_state.shuttle_data.values() if s['on_time'])
    st.metric("On Time", f"{on_time_count}/{active_shuttles}")

with col3:
    full_count = sum(1 for s in st.session_state.shuttle_data.values() if s['capacity'] == 'Full')
    st.metric("At Capacity", full_count)

with col4:
    active_alerts = len(st.session_state.system_alerts)
    st.metric("Active Alerts", active_alerts)

st.divider()

# Emergency Override Section
st.markdown("### 🚨 Emergency Overrides")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Campus-Wide Delay")
    delay_minutes = st.number_input(
        "Add delay to all shuttles (minutes):",
        min_value=0,
        max_value=60,
        value=0,
        step=5
    )
    
    delay_reason = st.selectbox(
        "Reason:",
        ["Weather Emergency", "Campus-Wide Event", "Security Incident", "Maintenance", "Other"]
    )
    
    if st.button("Apply System-Wide Delay", type="primary"):
        override = {
            'dispatcher': dispatcher_name,
            'type': 'system_delay',
            'delay_minutes': delay_minutes,
            'reason': delay_reason,
            'time': datetime.now()
        }
        st.session_state.dispatcher_overrides.append(override)
        
        # Update all shuttles
        for shuttle in st.session_state.shuttle_data.values():
            shuttle['on_time'] = False
        
        st.session_state.system_alerts.append({
            'type': 'delay',
            'message': f'{delay_reason}: All shuttles delayed {delay_minutes} minutes',
            'time': datetime.now()
        })
        
        st.session_state.recent_updates.append({
            'time': datetime.now().strftime('%I:%M %p'),
            'message': f'🚨 System: {delay_reason} - {delay_minutes} min delay'
        })
        
        st.error(f"🚨 System-wide {delay_minutes}-minute delay activated!")
        st.info(f"📢 Reason: {delay_reason}")

with col2:
    st.markdown("#### Route Changes")
    
    affected_shuttle = st.selectbox(
        "Select shuttle:",
        ["All Shuttles", "Shuttle 1", "Shuttle 2"]
    )
    
    route_status = st.radio(
        "Route Status:",
        ["Temporary Detour", "Skip Next Stop", "Service Suspended"]
    )
    
    route_notes = st.text_area(
        "Route change details:",
        placeholder="e.g., 'Avoiding construction on Commonwealth Ave'"
    )
    
    if st.button("Override Route", type="primary"):
        override = {
            'dispatcher': dispatcher_name,
            'type': 'route_override',
            'shuttle': affected_shuttle,
            'status': route_status,
            'notes': route_notes,
            'time': datetime.now()
        }
        st.session_state.dispatcher_overrides.append(override)
        
        st.session_state.system_alerts.append({
            'type': 'route',
            'message': f'{affected_shuttle}: {route_status}',
            'time': datetime.now()
        })
        
        st.session_state.recent_updates.append({
            'time': datetime.now().strftime('%I:%M %p'),
            'message': f'🔄 Dispatcher: {affected_shuttle} - {route_status}'
        })
        
        st.warning(f"🔄 Route override applied to {affected_shuttle}")

st.divider()

# Active System Alerts
st.markdown("### 🔔 Active System Alerts")

if st.session_state.system_alerts:
    for i, alert in enumerate(reversed(st.session_state.system_alerts[-10:])):
        alert_time = alert['time'].strftime('%I:%M %p')
        
        if alert['type'] == 'delay':
            st.error(f"🚨 {alert_time} - {alert['message']}")
        elif alert['type'] == 'route':
            st.warning(f"🔄 {alert_time} - {alert['message']}")
else:
    st.success("✅ No active alerts - All systems operating normally")

st.divider()

# Override History
st.markdown("### 📜 Override History")

if st.session_state.dispatcher_overrides:
    # Create DataFrame for display
    override_data = []
    for override in reversed(st.session_state.dispatcher_overrides[-20:]):
        override_data.append({
            'Time': override['time'].strftime('%I:%M %p'),
            'Dispatcher': override['dispatcher'],
            'Type': override['type'].replace('_', ' ').title(),
            'Details': override.get('reason', override.get('notes', 'N/A'))
        })
    
    df = pd.DataFrame(override_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No overrides have been issued today")
