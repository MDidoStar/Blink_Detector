import streamlit as st

# Import the two modules
import eye_health_check
import blink_monitor

# ----------------------------
# Page Configuration
# ----------------------------
st.set_page_config(
    page_title="Blink - Complete Eye Health Suite",
    page_icon="👁️",
    layout="wide"
)

# ----------------------------
# Main App Header
# ----------------------------
st.title("👁️ Blink - Complete Eye Health Suite")
st.markdown("### Professional eye health monitoring and blink rate tracking")

# ----------------------------
# Create Tabs
# ----------------------------
tab1, tab2 = st.tabs(["🔬 AI Eye Health Check", "⏱️ Blink Rate Monitor"])

# ----------------------------
# TAB 1: Eye Health Check with Gemini AI
# ----------------------------
with tab1:
    eye_health_check.run()

# ----------------------------
# TAB 2: Blink Rate Monitor
# ----------------------------
with tab2:
    blink_monitor.run()
