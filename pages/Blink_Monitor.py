
import time
import cv2
import numpy as np
import streamlit as st
import mediapipe as mp
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import av

st.set_page_config(page_title="Blink Monitor - Smart Tracking", layout="centered")

# ------------------ Session State ------------------
if "blink_count" not in st.session_state:
    st.session_state.blink_count = 0
if "eyes_closed" not in st.session_state:
    st.session_state.eyes_closed = False
if "open_eye_reference" not in st.session_state:
    st.session_state.open_eye_reference = None
if "minute_start" not in st.session_state:
    st.session_state.minute_start = time.time()
if "start_time" not in st.session_state:
    st.session_state.start_time = time.time()

# ------------------ Constants ------------------
BLINK_RATIO = 0.4
TOTAL_TIME = 5 * 60
NORMAL_MAX = 20

st.title("👁️ Blink Monitor")
st.markdown("### Monitor your blink rate to reduce eye strain")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Current Blinks", st.session_state.blink_count)
with col2:
    total_elapsed = time.time() - st.session_state.start_time
    remaining = max(0, TOTAL_TIME - int(total_elapsed))
    st.metric("Time Remaining", f"{remaining//60}:{remaining%60:02d}")
with col3:
    st.metric("Target", f"{NORMAL_MAX} blinks/min")

st.markdown("---")

mp_face = mp.solutions.face_mesh
face_mesh = mp_face.FaceMesh(refine_landmarks=True)

def process_frame(frame: av.VideoFrame) -> av.VideoFrame:
    img = frame.to_ndarray(format="bgr24")
    img = cv2.flip(img, 1)

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    # Blink detection (same idea you used)
    if results.multi_face_landmarks:
        face = results.multi_face_landmarks[0]
        top = face.landmark[159]
        bottom = face.landmark[145]
        eye_opening = abs(top.y - bottom.y)

        if st.session_state.open_eye_reference is None or eye_opening > st.session_state.open_eye_reference:
            st.session_state.open_eye_reference = eye_opening

        ref = st.session_state.open_eye_reference
        if ref:
            if eye_opening < ref * BLINK_RATIO:
                if not st.session_state.eyes_closed:
                    st.session_state.blink_count += 1
                    st.session_state.eyes_closed = True
            else:
                st.session_state.eyes_closed = False

    # Minute reset + reminder logic
    if time.time() - st.session_state.minute_start >= 60:
        st.session_state.blink_count = 0
        st.session_state.minute_start = time.time()

    # Overlay
    total_elapsed = time.time() - st.session_state.start_time
    remaining = max(0, TOTAL_TIME - int(total_elapsed))
    cv2.putText(img, f"Blinks/min: {st.session_state.blink_count} / {NORMAL_MAX}",
                (10, img.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    cv2.putText(img, f"Time left: {remaining//60}:{remaining%60:02d}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 2)

    return av.VideoFrame.from_ndarray(img, format="bgr24")

# Start time reset button
if st.button("Reset Session"):
    st.session_state.blink_count = 0
    st.session_state.eyes_closed = False
    st.session_state.open_eye_reference = None
    st.session_state.minute_start = time.time()
    st.session_state.start_time = time.time()
    st.rerun()

webrtc_streamer(
    key="blink",
    mode=WebRtcMode.SENDRECV,
    video_frame_callback=process_frame,
    media_stream_constraints={"video": True, "audio": False},
)

st.markdown("---")
st.markdown("💡 **Tip**: Remember to take breaks and blink regularly to prevent eye strain!")

