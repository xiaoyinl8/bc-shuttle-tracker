import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime, timedelta
import random

# Page configuration
st.set_page_config(
    page_title="BC Shuttle Tracker",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        font-weight: 600;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .confidence-bar {
        height: 20px;
        background: linear-gradient(to right, #02C39A 0%, #028090 100%);
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    """Initialize all session state variables"""
    if 'has_seen_onboarding' not in st.session_state:
        st.session_state.has_seen_onboarding = False
    
    if 'shuttle_data' not in st.session_state:
        # Simulated shuttle data
        st.session_state.shuttle_data = {
            'shuttle_1': {
                'lat': 42.3360,
                'lon': -71.1690,
                'current_stop': 'Library',
                'next_stop': 'Student Center',
                'capacity': 'Medium',
                'capacity_pct': 60,
                'speed': 15,  # mph
                'on_time': True
            },
            'shuttle_2': {
                'lat': 42.3345,
                'lon': -71.1670,
                'current_stop': 'Parking Lot A',
                'next_stop': 'Dorms',
                'capacity': 'Full',
                'capacity_pct': 95,
                'speed': 12,
                'on_time': False
            }
        }
    
    if 'stops' not in st.session_state:
        st.session_state.stops = {
            'Student Center': {'lat': 42.3351, 'lon': -71.1685},
            'Library': {'lat': 42.3360, 'lon': -71.1690},
            'Parking Lot A': {'lat': 42.3345, 'lon': -71.1670},
            'Dorms': {'lat': 42.3355, 'lon': -71.1695},
        }
    
    if 'user_stop' not in st.session_state:
        st.session_state.user_stop = 'Student Center'
    
    if 'eta_prediction' not in st.session_state:
        st.session_state.eta_prediction = {
            'min': 4,
            'max': 6,
            'confidence': 87
        }
    
    if 'feedback_history' not in st.session_state:
        st.session_state.feedback_history = []
    
    if 'show_feedback_modal' not in st.session_state:
        st.session_state.show_feedback_modal = False
    
    if 'recent_updates' not in st.session_state:
        st.session_state.recent_updates = []

init_session_state()

def calculate_eta(shuttle, stop_name):
    """Calculate ETA with confidence level"""
    # Simulated calculation based on distance and historical data
    stop = st.session_state.stops[stop_name]
    
    # Calculate distance (simplified)
    lat_diff = abs(shuttle['lat'] - stop['lat'])
    lon_diff = abs(shuttle['lon'] - stop['lon'])
    distance = ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 69  # Rough miles
    
    # Base ETA calculation
    base_eta = (distance / shuttle['speed']) * 60  # minutes
    
    # Add variability
    min_eta = max(1, int(base_eta * 0.8))
    max_eta = int(base_eta * 1.2)
    
    # Calculate confidence based on various factors
    confidence = 85
    
    # Reduce confidence if shuttle is not on time
    if not shuttle['on_time']:
        confidence -= 15
    
    # Reduce confidence if there are recent negative feedbacks
    recent_negative = sum(1 for f in st.session_state.feedback_history[-5:] if f['type'] == 'wrong')
    confidence -= recent_negative * 5
    
    # Increase confidence for recent positive feedbacks
    recent_positive = sum(1 for f in st.session_state.feedback_history[-5:] if f['type'] == 'accurate')
    confidence += recent_positive * 2
    
    confidence = max(45, min(95, confidence))
    
    return min_eta, max_eta, confidence

def show_onboarding():
    """Display onboarding flow for first-time users"""
    st.title("🚌 Welcome to BC Shuttle Tracker")
    st.markdown("### Human-AI Collaboration for Reliable Transit")
    
    st.info("This system combines AI predictions with human verification to provide the most accurate shuttle information.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### ✅ What AI Can Do")
        st.success("""
        - **Track shuttle GPS positions** in real-time
        - **Predict arrival times** based on historical data
        - **Estimate capacity** from past ridership patterns
        - **Calculate confidence levels** for predictions
        """)
    
    with col2:
        st.markdown("#### ❌ What AI CANNOT Do")
        st.warning("""
        - **Know about today's delays** (construction, weather)
        - **See actual shuttle crowding** right now
        - **Predict unexpected events** (breakdowns, detours)
        - **Judge subjective 'too crowded'** thresholds
        """)
    
    st.markdown("---")
    
    st.markdown("#### 🤝 Your Role: Verify & Correct")
    st.markdown("""
    When you see a prediction, you can:
    - ✓ **Confirm** if it's accurate (helps AI learn)
    - ✗ **Report** if it's wrong (updates everyone instantly)
    - 📢 **Share** real-time issues (delays, capacity, route changes)
    
    Your feedback makes the system better for everyone!
    """)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚀 Get Started", use_container_width=True, type="primary"):
            st.session_state.has_seen_onboarding = True
            st.rerun()

def display_main_app():
    """Display the main application interface"""
    
    # Header
    st.title("🚌 BC Shuttle Tracker")
    st.caption("Real-time shuttle tracking powered by AI + human verification")
    
    # Sidebar
    with st.sidebar:
        st.header("📍 Your Location")
        
        selected_stop = st.selectbox(
            "Select your stop:",
            list(st.session_state.stops.keys()),
            index=list(st.session_state.stops.keys()).index(st.session_state.user_stop)
        )
        
        if selected_stop != st.session_state.user_stop:
            st.session_state.user_stop = selected_stop
            # Recalculate ETA
            shuttle = st.session_state.shuttle_data['shuttle_1']
            min_eta, max_eta, confidence = calculate_eta(shuttle, selected_stop)
            st.session_state.eta_prediction = {
                'min': min_eta,
                'max': max_eta,
                'confidence': confidence
            }
            st.rerun()
        
        st.divider()
        
        st.markdown("### 🔄 Recent Updates")
        if st.session_state.recent_updates:
            for update in st.session_state.recent_updates[-3:]:
                st.info(f"🕐 {update['time']}\n{update['message']}")
        else:
            st.caption("No recent updates")
        
        st.divider()
        
        st.markdown("### ℹ️ About")
        st.info("This system uses AI to predict arrivals, but needs YOUR feedback to stay accurate!")
        
        if st.button("🔄 Reset Onboarding"):
            st.session_state.has_seen_onboarding = False
            st.rerun()
    
    # Main content layout
    col_map, col_info = st.columns([2, 1])
    
    with col_map:
        st.subheader("🗺️ Live Shuttle Map")
        
        # Create map
        center_lat = 42.3351
        center_lon = -71.1685
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=15,
            tiles='OpenStreetMap'
        )
        
        # Add shuttle markers
        for shuttle_id, shuttle in st.session_state.shuttle_data.items():
            # Shuttle icon
            folium.Marker(
                [shuttle['lat'], shuttle['lon']],
                popup=f"""
                <b>{shuttle_id.replace('_', ' ').title()}</b><br>
                Current: {shuttle['current_stop']}<br>
                Next: {shuttle['next_stop']}<br>
                Capacity: {shuttle['capacity']} ({shuttle['capacity_pct']}%)
                """,
                tooltip=f"{shuttle_id.replace('_', ' ').title()} - Click for details",
                icon=folium.Icon(color='blue', icon='bus', prefix='fa')
            ).add_to(m)
        
        # Add stop markers
        for stop_name, coords in st.session_state.stops.items():
            color = 'green' if stop_name == st.session_state.user_stop else 'gray'
            folium.Marker(
                [coords['lat'], coords['lon']],
                popup=f"<b>{stop_name}</b>",
                tooltip=stop_name,
                icon=folium.Icon(color=color, icon='map-pin', prefix='fa')
            ).add_to(m)
        
        # Add route line (simplified)
        route_coords = [[stop['lat'], stop['lon']] for stop in st.session_state.stops.values()]
        folium.PolyLine(
            route_coords,
            color='#028090',
            weight=3,
            opacity=0.7,
            dash_array='10'
        ).add_to(m)
        
        st_folium(m, width=700, height=500, returned_objects=[])
    
    with col_info:
        st.subheader(f"📍 {st.session_state.user_stop}")
        
        # ETA Prediction
        eta = st.session_state.eta_prediction
        st.markdown("### 🚌 Next Shuttle")
        st.metric(
            "Predicted Arrival",
            f"{eta['min']}-{eta['max']} min",
            delta=None
        )
        
        # Confidence Level
        st.markdown("### 🎯 AI Confidence")
        confidence = eta['confidence']
        
        # Color-coded confidence
        if confidence >= 80:
            conf_color = "#02C39A"  # Green
            conf_label = "High"
        elif confidence >= 60:
            conf_color = "#028090"  # Teal
            conf_label = "Medium"
        else:
            conf_color = "#FF6B6B"  # Red
            conf_label = "Low"
        
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem;">
            <h2 style="margin: 0; color: {conf_color};">{confidence}%</h2>
            <p style="margin: 0.5rem 0 0 0; color: #666;">{conf_label} Confidence</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.progress(confidence / 100)
        
        # Capacity Information
        st.markdown("### 👥 Capacity")
        shuttle = st.session_state.shuttle_data['shuttle_1']
        
        capacity_color = {
            'Empty': '#02C39A',
            'Medium': '#028090',
            'Full': '#FF6B6B'
        }
        
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem;">
            <h3 style="margin: 0; color: {capacity_color.get(shuttle['capacity'], '#666')};">{shuttle['capacity']}</h3>
            <p style="margin: 0.5rem 0 0 0; color: #666;">{shuttle['capacity_pct']}% occupied</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.progress(shuttle['capacity_pct'] / 100)
        
        st.divider()
        
        # Verification Section
        st.markdown("### ✅ Verify Prediction")
        st.caption("Does this prediction look accurate?")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✓ Yes", use_container_width=True, type="primary"):
                # Record positive feedback
                st.session_state.feedback_history.append({
                    'type': 'accurate',
                    'time': datetime.now(),
                    'stop': st.session_state.user_stop
                })
                
                # Increase confidence slightly
                st.session_state.eta_prediction['confidence'] = min(
                    95,
                    st.session_state.eta_prediction['confidence'] + 3
                )
                
                st.session_state.recent_updates.append({
                    'time': datetime.now().strftime('%I:%M %p'),
                    'message': '✅ User verified prediction'
                })
                
                st.success("✅ Thanks! Your feedback helps improve predictions.")
                st.rerun()
        
        with col2:
            if st.button("✗ No", use_container_width=True):
                st.session_state.show_feedback_modal = True
                st.rerun()
        
        with col3:
            if st.button("📢 Report", use_container_width=True):
                st.session_state.show_feedback_modal = True
                st.rerun()
        
        # Feedback Modal
        if st.session_state.show_feedback_modal:
            st.markdown("---")
            st.markdown("#### What's actually happening?")
            
            issue_type = st.selectbox(
                "Select issue:",
                ["Shuttle is late", "Shuttle is full", "Different route", "Construction delay", "Weather delay", "Other"]
            )
            
            additional_info = st.text_area(
                "Additional details (optional):",
                placeholder="e.g., 'About 10 minutes late' or 'Completely packed, no space'"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Submit Feedback", use_container_width=True, type="primary"):
                    # Record feedback
                    st.session_state.feedback_history.append({
                        'type': 'wrong',
                        'issue': issue_type,
                        'details': additional_info,
                        'time': datetime.now(),
                        'stop': st.session_state.user_stop
                    })
                    
                    # Adjust prediction based on feedback
                    if "late" in issue_type.lower():
                        st.session_state.eta_prediction['min'] += 3
                        st.session_state.eta_prediction['max'] += 5
                        st.session_state.eta_prediction['confidence'] = max(45, st.session_state.eta_prediction['confidence'] - 20)
                    
                    if "full" in issue_type.lower():
                        st.session_state.shuttle_data['shuttle_1']['capacity'] = 'Full'
                        st.session_state.shuttle_data['shuttle_1']['capacity_pct'] = 95
                    
                    st.session_state.recent_updates.append({
                        'time': datetime.now().strftime('%I:%M %p'),
                        'message': f'⚠️ Issue reported: {issue_type}'
                    })
                    
                    st.session_state.show_feedback_modal = False
                    st.success(f"✅ Updated! ETA adjusted to {st.session_state.eta_prediction['min']}-{st.session_state.eta_prediction['max']} min based on your report.")
                    st.info("📢 Other users will see this update in real-time!")
                    st.rerun()
            
            with col2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.show_feedback_modal = False
                    st.rerun()
    
    # How AI Calculated This
    with st.expander("🤖 How AI Calculated This Prediction"):
        st.markdown("#### Calculation Breakdown")
        
        shuttle = st.session_state.shuttle_data['shuttle_1']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**AI Confidence Based On:**")
            st.markdown(f"""
            ✓ GPS position: {shuttle['current_stop']} → {st.session_state.user_stop}  
            ✓ Historical average: {eta['min']}-{eta['max']} min  
            ✓ Current speed: {shuttle['speed']} mph  
            ✓ Traffic patterns: Normal for this time  
            """)
        
        with col2:
            st.markdown("**Confidence Level:**")
            if eta['confidence'] >= 80:
                st.success(f"**{eta['confidence']}% - High Confidence**\nGPS + historical data align well")
            elif eta['confidence'] >= 60:
                st.warning(f"**{eta['confidence']}% - Medium Confidence**\nSome variability in recent data")
            else:
                st.error(f"**{eta['confidence']}% - Low Confidence**\nRecent delays or high variability")
        
        st.markdown("---")
        st.markdown("**Recent User Feedback Impact:**")
        if st.session_state.feedback_history:
            recent_feedback = st.session_state.feedback_history[-3:]
            for fb in reversed(recent_feedback):
                if fb['type'] == 'accurate':
                    st.success(f"✅ {fb['time'].strftime('%I:%M %p')} - Verified accurate (+3% confidence)")
                else:
                    st.warning(f"⚠️ {fb['time'].strftime('%I:%M %p')} - Reported: {fb.get('issue', 'Issue')} (-15% confidence)")
        else:
            st.info("No recent feedback yet. Your input helps calibrate predictions!")

# Main app routing
if not st.session_state.has_seen_onboarding:
    show_onboarding()
else:
    display_main_app()
