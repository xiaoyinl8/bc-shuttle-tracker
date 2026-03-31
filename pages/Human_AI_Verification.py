import streamlit as st

from interaction_ui import apply_shared_styles, render_feedback_section
from shuttle_simulation import initialize_simulation_state


st.set_page_config(
    page_title="Shuttle Prediction - BC Shuttle Tracker",
    page_icon="🤝",
    layout="wide",
)

apply_shared_styles()
initialize_simulation_state()

st.title("🤝 Shuttle Prediction")
st.caption("This page showcases the human-in-the-loop layer: AI predicts first, riders verify after boarding, and the system improves over time.")

stop_names = sorted(st.session_state.stops.keys())
selected_stop = st.selectbox(
    "Which stop are you evaluating?",
    stop_names,
    index=stop_names.index(st.session_state.user_stop),
)

if selected_stop != st.session_state.user_stop:
    st.session_state.user_stop = selected_stop
    st.rerun()

render_feedback_section(st.session_state.user_stop)
