import streamlit as st

st.set_page_config(
    page_title="Blink Smart",
    page_icon="👁️",
    layout="wide"
)

# Main landing page with logo
col_logo, col_title = st.columns([1, 3])
with col_logo:
    st.image("1771169157130_image.png", width=180)
with col_title:
    st.title("👁️ Blink Smart")
    st.markdown("### Complete eye health monitoring and analysis")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📸 Blink Analysis")
    st.markdown("""
    **Capture and analyze your blinking patterns**
    - Capture 120 frames from webcam
    - AI-powered analysis with Gemini
    - Generate detailed PDF reports
    - Get personalized recommendations
    """)
    if st.button("🔍 Go to Blink Analysis", type="primary", use_container_width=True):
        st.switch_page("pages/Blink_Analysis.py")

with col2:
    st.markdown("### ⏱️ Blink Monitor")
    st.markdown("""
    **Real-time blink rate monitoring**
    - Track blinks per minute live
    - 5-minute monitoring sessions
    - Gentle reminders to blink
    - Prevent eye strain
    """)
    if st.button("📊 Go to Blink Monitor", type="primary", use_container_width=True):
        st.switch_page("pages/Blink_Monitor.py")

st.markdown("---")

st.markdown("""
### About Eye Health Suite

This comprehensive eye health application helps you:
- **Analyze** your blinking patterns with AI
- **Monitor** your blink rate in real-time
- **Prevent** eye strain and related issues
- **Track** your eye health over time

#### Why Blinking Matters
Regular blinking is essential for:
- Keeping eyes moist and comfortable
- Preventing dry eye syndrome
- Reducing digital eye strain
- Maintaining optimal vision

#### Recommended Usage
- Use **Blink Analysis** for detailed assessment
- Use **Blink Monitor** during work sessions
- Aim for 15-20 blinks per minute
- Take regular breaks from screens
""")

st.markdown("---")
st.markdown("💡 **Tip**: Choose the tool that best fits your current needs!")
