
import time
import cv2
import numpy as np
import streamlit as st
import mediapipe as mp
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
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
if "last_blink_check" not in st.session_state:
    st.session_state.last_blink_check = time.time()

# ------------------ Constants ------------------
BLINK_RATIO = 0.4
TOTAL_TIME = 5 * 60
NORMAL_MAX = 20

# Initialize MediaPipe Face Mesh outside of callback for better performance
mp_face = mp.solutions.face_mesh
face_mesh = mp_face.FaceMesh(
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

st.title("👁️ Blink Monitor")
st.markdown("### Monitor your blink rate to reduce eye strain")

# Display metrics at the top
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

def process_frame(frame: av.VideoFrame) -> av.VideoFrame:
    """Process video frame for blink detection"""
    try:
        # Convert frame to numpy array
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        
        # Convert to RGB for MediaPipe
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results = face_mesh.process(rgb)
        
        # Blink detection
        if results.multi_face_landmarks:
            face = results.multi_face_landmarks[0]
            
            # Get eye landmarks (upper and lower eyelid)
            # Using landmarks 159 (upper) and 145 (lower) for right eye
            top = face.landmark[159]
            bottom = face.landmark[145]
            
            # Calculate vertical eye opening
            eye_opening = abs(top.y - bottom.y)
            
            # Establish reference for open eye (calibration)
            if st.session_state.open_eye_reference is None or eye_opening > st.session_state.open_eye_reference:
                st.session_state.open_eye_reference = eye_opening
            
            ref = st.session_state.open_eye_reference
            
            # Detect blink based on ratio
            if ref and ref > 0:
                current_ratio = eye_opening / ref
                
                if current_ratio < BLINK_RATIO:
                    # Eye is closed
                    if not st.session_state.eyes_closed:
                        st.session_state.blink_count += 1
                        st.session_state.eyes_closed = True
                else:
                    # Eye is open
                    st.session_state.eyes_closed = False
        
        # Check if a minute has passed and reset counter
        current_time = time.time()
        if current_time - st.session_state.minute_start >= 60:
            st.session_state.blink_count = 0
            st.session_state.minute_start = current_time
        
        # Calculate remaining time
        total_elapsed = current_time - st.session_state.start_time
        remaining = max(0, TOTAL_TIME - int(total_elapsed))
        
        # Add overlay text to video
        cv2.putText(
            img, 
            f"Blinks/min: {st.session_state.blink_count} / {NORMAL_MAX}",
            (10, img.shape[0] - 10), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            (0, 255, 0), 
            2
        )
        
        cv2.putText(
            img, 
            f"Time left: {remaining//60}:{remaining%60:02d}",
            (10, 30), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            (200, 200, 200), 
            2
        )
        
        # Add eye state indicator
        eye_state = "CLOSED" if st.session_state.eyes_closed else "OPEN"
        color = (0, 0, 255) if st.session_state.eyes_closed else (0, 255, 0)
        cv2.putText(
            img,
            f"Eyes: {eye_state}",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2
        )
        
        return av.VideoFrame.from_ndarray(img, format="bgr24")
    
    except Exception as e:
        # Return original frame if processing fails
        print(f"Error processing frame: {e}")
        return frame

# Reset session button
if st.button("Reset Session"):
    st.session_state.blink_count = 0
    st.session_state.eyes_closed = False
    st.session_state.open_eye_reference = None
    st.session_state.minute_start = time.time()
    st.session_state.start_time = time.time()
    st.rerun()

# WebRTC configuration for better connectivity
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

# Start webcam streamer
webrtc_ctx = webrtc_streamer(
    key="blink-monitor",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIGURATION,
    video_frame_callback=process_frame,
    media_stream_constraints={"video": True, "audio": False},
    async_processing=True,
)

st.markdown("---")

# Instructions
st.markdown("""
### 📋 Instructions:
1. **Click "START"** to begin the camera
2. **Position your face** in the camera frame
3. **Blink naturally** - the app will track your blinks
4. Target: 15-20 blinks per minute for healthy eyes
5. Session duration: 5 minutes

### 💡 Tips:
- Ensure good lighting for accurate detection
- Keep your face centered in the frame
- If detection seems off, click "Reset Session" to recalibrate
- Remember to take breaks and blink regularly to prevent eye strain!
""")

# Debug info (optional - can be removed in production)
with st.expander("Debug Info"):
    st.write(f"Blink Count: {st.session_state.blink_count}")
    st.write(f"Eyes Closed: {st.session_state.eyes_closed}")
    st.write(f"Reference: {st.session_state.open_eye_reference}")
    st.write(f"Minute Start: {time.time() - st.session_state.minute_start:.1f}s ago")

