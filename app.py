import streamlit as st


navigation = st.navigation(
    [
        st.Page("map_page.py", title="Map", icon="🗺️", default=True),
        st.Page("pages/AI_Assistant.py", title="AI Assistant", icon="🤖"),
        st.Page("pages/Human_AI_Verification.py", title="Shuttle Prediction", icon="🤝"),
        st.Page("pages/Dispatcher_Override.py", title="Dispatcher Override", icon="🎛️"),
        st.Page("pages/Driver_Interface.py", title="Driver Interface", icon="🚗"),
    ],
    position="hidden",
)

navigation.run()
