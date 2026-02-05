import io
import re
import streamlit as st
import google.generativeai as genai
import pandas as pd
import cv2
import mediapipe as mp
import time
import numpy as np

from reportlab.platypus import (
    SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

# ----------------------------
# Page Configuration
# ----------------------------
st.set_page_config(
    page_title="Blink - Complete Eye Health Suite",
    page_icon="👁️",
    layout="wide"
)

# ----------------------------
# Gemini setup for Tab 1
# ----------------------------
genai.configure(api_key="AIzaSyD_13Y30NRcVRGNO9m4vTkhyvxusTY1qK8")
model = genai.GenerativeModel("gemini-2.5-flash")

# ----------------------------
# Data load for Tab 1
# ----------------------------
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("countries.csv")

        expected = {"Country", "City", "Currency_Code", "Number"}
        missing = expected - set(df.columns)
        if missing:
            st.error(f"countries.csv is missing columns: {missing}")
            return pd.DataFrame(columns=["Country", "City", "Currency_Code", "Number"])

        df["Country"] = df["Country"].astype(str)
        df["City"] = df["City"].astype(str)
        df["Currency_Code"] = df["Currency_Code"].astype(str)
        df["Number"] = pd.to_numeric(df["Number"], errors="coerce")

        return df

    except FileNotFoundError:
        st.error("Error: 'countries.csv' file not found. Please check the path.")
        return pd.DataFrame(columns=["Country", "City", "Currency_Code", "Number"])

    except Exception as e:
        st.error(f"Failed to load countries.csv: {e}")
        return pd.DataFrame(columns=["Country", "City", "Currency_Code", "Number"])


df = load_data()


def get_countries():
    if not df.empty:
        return sorted(df["Country"].dropna().unique().tolist())
    return []


def get_cities(country: str):
    if not df.empty and country:
        return sorted(df[df["Country"] == country]["City"].dropna().unique().tolist())
    return []


def get_numbers_from_file():
    if df.empty or "Number" not in df.columns:
        return []
    nums = df["Number"].dropna().unique().tolist()
    nums = sorted({int(x) for x in nums})
    return nums


# ----------------------------
# PDF generation for Tab 1
# ----------------------------
def generate_pdf_from_text_and_image(text_content: str, image_bytes: bytes | None = None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )

    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=14,
        leading=20
    )
    normal_style = ParagraphStyle(
        "CustomNormal",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=6,
        leading=14
    )

    story.append(Paragraph("Eye Photo + Gemini Notes", title_style))
    story.append(Spacer(1, 10))

    if image_bytes:
        img_buf = io.BytesIO(image_bytes)
        rl_img = RLImage(img_buf)
        rl_img._restrictSize(440, 280)
        story.append(rl_img)
        story.append(Spacer(1, 14))

    lines = text_content.split("\n")
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        if not stripped:
            story.append(Spacer(1, 8))
            i += 1
            continue

        if "|" in stripped and i + 1 < len(lines) and "|" in lines[i + 1]:
            table_data = []
            while i < len(lines) and "|" in lines[i].strip():
                row = lines[i].strip()

                if re.match(r"^[\|\s\-:]+$", row):
                    i += 1
                    continue

                cells = [cell.strip() for cell in row.split("|") if cell.strip() != ""]
                if cells:
                    table_data.append(cells)
                i += 1

            if table_data:
                t = Table(table_data, hAlign="CENTER")
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                    ("TOPPADDING", (0, 0), (-1, 0), 10),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                ]))
                story.append(t)
                story.append(Spacer(1, 12))
            continue

        story.append(Paragraph(stripped, normal_style))
        i += 1

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ----------------------------
# Webcam Component for Tab 1
# ----------------------------
def webcam_with_hidden_upload():
    """
    Captures frames and creates a Blob, then programmatically uploads via hidden file input
    """
    
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
    </head>
    <body>
        <div style="text-align: center;">
            <video id="video" width="640" height="480" autoplay style="border: 2px solid #3498db; border-radius: 8px;"></video>
            <br><br>
            <button id="startBtn" style="padding: 10px 20px; font-size: 16px; background-color: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px;">
                Start Camera
            </button>
            <button id="captureBtn" style="padding: 10px 20px; font-size: 16px; background-color: #27ae60; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px;" disabled>
                Capture & Upload 120 Frames
            </button>
            <canvas id="canvas" style="display: none;"></canvas>
            <p id="status" style="margin-top: 10px; font-size: 14px; color: #555;"></p>
            <p id="progress" style="margin-top: 5px; font-size: 14px; font-weight: bold; color: #3498db;"></p>
        </div>

        <script>
            const video = document.getElementById('video');
            const canvas = document.getElementById('canvas');
            const startBtn = document.getElementById('startBtn');
            const captureBtn = document.getElementById('captureBtn');
            const status = document.getElementById('status');
            const progress = document.getElementById('progress');
            const ctx = canvas.getContext('2d');
            
            let stream = null;

            startBtn.onclick = async () => {
                try {
                    status.textContent = 'Requesting camera access...';
                    stream = await navigator.mediaDevices.getUserMedia({ 
                        video: { width: 640, height: 480 } 
                    });
                    video.srcObject = stream;
                    status.textContent = '✅ Camera active! Ready to capture.';
                    captureBtn.disabled = false;
                    startBtn.disabled = true;
                } catch (err) {
                    status.textContent = '❌ Error: ' + err.message;
                    console.error('Camera error:', err);
                }
            };

            captureBtn.onclick = async () => {
                if (!stream) {
                    status.textContent = 'Please start the camera first!';
                    return;
                }

                captureBtn.disabled = true;
                status.textContent = '📸 Capturing frames... Look at camera and blink normally.';
                
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;

                const capturedFrames = [];
                
                // Capture 120 frames
                for (let i = 0; i < 120; i++) {
                    ctx.drawImage(video, 0, 0);
                    
                    // Convert to blob
                    const blob = await new Promise(resolve => {
                        canvas.toBlob(resolve, 'image/jpeg', 0.85);
                    });
                    
                    capturedFrames.push(blob);
                    progress.textContent = `Captured ${i + 1}/120 frames`;
                    await new Promise(resolve => setTimeout(resolve, 30));
                }

                status.textContent = '📦 Creating ZIP file...';
                progress.textContent = '';
                
                // Create ZIP
                const zip = new JSZip();
                for (let i = 0; i < capturedFrames.length; i++) {
                    zip.file(`frame_${String(i).padStart(3, '0')}.jpg`, capturedFrames[i]);
                }
                
                const zipBlob = await zip.generateAsync({type: 'blob'});
                
                status.textContent = '📤 Uploading to Streamlit...';
                
                // Find Streamlit's file uploader in parent document
                const fileUploader = window.parent.document.querySelector('input[type="file"][accept=".zip"]');
                
                if (fileUploader) {
                    // Create a File object from the blob
                    const file = new File([zipBlob], 'captured_frames.zip', { type: 'application/zip' });
                    
                    // Create DataTransfer to set files
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    fileUploader.files = dataTransfer.files;
                    
                    // Trigger change event
                    fileUploader.dispatchEvent(new Event('change', { bubbles: true }));
                    
                    status.textContent = '✅ Frames uploaded successfully!';
                    progress.textContent = 'You can now analyze the frames below.';
                } else {
                    status.textContent = '❌ Could not find file uploader. Please refresh and try again.';
                }
                
                captureBtn.disabled = false;
            };
        </script>
    </body>
    </html>
    """
    
    st.components.v1.html(html_code, height=680)


# ----------------------------
# Session State for Tab 2
# ----------------------------
def init_blink_session_state():
    if 'blink_count' not in st.session_state:
        st.session_state.blink_count = 0
    if 'eyes_closed' not in st.session_state:
        st.session_state.eyes_closed = False
    if 'open_eye_reference' not in st.session_state:
        st.session_state.open_eye_reference = None
    if 'minute_start' not in st.session_state:
        st.session_state.minute_start = time.time()
    if 'start_time' not in st.session_state:
        st.session_state.start_time = time.time()
    if 'show_reminder' not in st.session_state:
        st.session_state.show_reminder = False
    if 'reminder_start' not in st.session_state:
        st.session_state.reminder_start = 0
    if 'camera_active' not in st.session_state:
        st.session_state.camera_active = False


# ----------------------------
# Main App with Tabs
# ----------------------------

# Header
st.title("👁️ Blink - Complete Eye Health Suite")
st.markdown("### Professional eye health monitoring and blink rate tracking")

# Create tabs
tab1, tab2 = st.tabs(["🔬 AI Eye Health Check", "⏱️ Blink Rate Monitor"])

# ----------------------------
# TAB 1: Eye Health Check with Gemini AI
# ----------------------------
with tab1:
    try:
        st.image(
            "blink_logo.png",
            use_column_width=False,
            width=180
        )
    except:
        pass  # Skip logo if not found

    st.subheader("Step 1: Capture 120 frames")

    # Initialize session state
    if 'captured_frames' not in st.session_state:
        st.session_state.captured_frames = None

    # Render webcam component
    webcam_with_hidden_upload()

    # Hidden file uploader (will be auto-filled by JavaScript)
    uploaded_zip = st.file_uploader("", type=['zip'], key="auto_upload", label_visibility="collapsed")

    # Process uploaded ZIP
    if uploaded_zip is not None:
        import zipfile
        try:
            with zipfile.ZipFile(uploaded_zip, 'r') as zip_ref:
                frame_files = sorted([f for f in zip_ref.namelist() if f.endswith('.jpg')])
                
                if len(frame_files) < 1:
                    st.error("No JPG files found in the ZIP!")
                else:
                    frames_bytes = []
                    for frame_file in frame_files:
                        with zip_ref.open(frame_file) as f:
                            frames_bytes.append(f.read())
                    
                    st.session_state.captured_frames = frames_bytes
                    st.success(f"✅ Loaded {len(frames_bytes)} frames!")
                    
                    # Show first frame
                    st.image(frames_bytes[0], caption=f"First frame (total: {len(frames_bytes)} frames)", use_column_width=True)
        
        except Exception as e:
            st.error(f"Error reading ZIP file: {e}")

    st.write("---")

    st.subheader("Step 2: Where are you from?")
    patient_country = st.selectbox("Country:", get_countries(), key="h_country")
    patient_city = st.selectbox("City:", get_cities(patient_country), key="h_city")

    st.subheader("Step 3: Your Age")
    numbers = get_numbers_from_file()
    if not numbers:
        st.error("No numbers found in the 'Number' column in countries.csv.")
    else:
        age_num = st.selectbox("Age", numbers, key="an")

        st.write("---")

        if st.button("Step 4: 📊 Analyze Frames with AI", key="analyze_btn"):
            if st.session_state.captured_frames is None or len(st.session_state.captured_frames) == 0:
                st.error("⚠️ Please capture frames first using the button above!")
            else:
                frames = st.session_state.captured_frames
                
                try:
                    st.image(frames[0], caption="Analyzing this frame and others...", use_column_width=True)
                except Exception as e:
                    st.warning(f"Could not display preview image: {e}")

                prompt = f"""
You are given {len(frames)} sequential eye images (frames) from a webcam.
Task: Check for possible blinking problems or abnormal blinking patterns.
- You cannot diagnose.
- Give careful observations and safe advice only.
- Keep it short and focused.
- List urgent red flags that require an eye doctor.

Patient context:
- Country: {patient_country}
- City: {patient_city}
- Age: {age_num}
"""

                # Prepare content for Gemini
                contents = [prompt]
                for frame_bytes in frames:
                    contents.append({"mime_type": "image/jpeg", "data": frame_bytes})

                with st.spinner(f"Analyzing {len(frames)} frames with Gemini AI..."):
                    response = model.generate_content(contents)

                st.subheader("Analysis Results:")
                st.write(response.text)

                # Generate PDF
                pdf_content = generate_pdf_from_text_and_image(response.text, frames[0])

                if pdf_content:
                    st.subheader("Step 5: Download your Report")
                    st.download_button(
                        label="Download PDF Report ⬇️",
                        data=pdf_content,
                        file_name="eye_health_recommendations.pdf",
                        mime="application/pdf"
                    )


# ----------------------------
# TAB 2: Blink Rate Monitor
# ----------------------------
with tab2:
    # Initialize session state
    init_blink_session_state()
    
    # Constants
    BLINK_RATIO = 0.4
    TOTAL_TIME = 5 * 60  # 5 minutes
    REMINDER_DURATION = 10  # seconds
    NORMAL_MAX = 20

    # MediaPipe Setup
    mp_face = mp.solutions.face_mesh

    st.markdown("### Monitor your blink rate to reduce eye strain")

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        st.metric("Current Blinks", st.session_state.blink_count)

    with col2:
        total_elapsed = time.time() - st.session_state.start_time
        remaining = TOTAL_TIME - int(total_elapsed)
        minutes_left = remaining // 60
        seconds_left = remaining % 60
        st.metric("Time Remaining", f"{minutes_left}:{seconds_left:02d}")

    with col3:
        st.metric("Target", f"{NORMAL_MAX} blinks/min")

    st.markdown("---")

    # Control Buttons
    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        if st.button("🎥 Start Camera", disabled=st.session_state.camera_active, type="primary", key="start_blink_cam"):
            st.session_state.camera_active = True
            st.session_state.blink_count = 0
            st.session_state.eyes_closed = False
            st.session_state.open_eye_reference = None
            st.session_state.minute_start = time.time()
            st.session_state.start_time = time.time()
            st.session_state.show_reminder = False
            st.rerun()

    with col_btn2:
        if st.button("🛑 Stop Camera", disabled=not st.session_state.camera_active, type="secondary", key="stop_blink_cam"):
            st.session_state.camera_active = False
            st.rerun()

    # Camera Feed
    if st.session_state.camera_active:
        # Create placeholder for video
        video_placeholder = st.empty()
        
        # Open camera
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Initialize face mesh
        face_mesh = mp_face.FaceMesh(refine_landmarks=True)
        
        # Stop button for real-time control
        stop_button = st.button("⏹️ Stop", key="stop_realtime")
        
        while st.session_state.camera_active and not stop_button:
            success, frame = camera.read()
            if not success:
                st.error("Failed to access camera")
                break
            
            frame = cv2.flip(frame, 1)
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(image)
            
            # Blink Detection
            if results.multi_face_landmarks:
                face = results.multi_face_landmarks[0]
                
                top = face.landmark[159]
                bottom = face.landmark[145]
                
                eye_opening = abs(top.y - bottom.y)
                
                if st.session_state.open_eye_reference is None or eye_opening > st.session_state.open_eye_reference:
                    st.session_state.open_eye_reference = eye_opening
                
                if st.session_state.open_eye_reference:
                    if eye_opening < st.session_state.open_eye_reference * BLINK_RATIO:
                        if not st.session_state.eyes_closed:
                            st.session_state.blink_count += 1
                            st.session_state.eyes_closed = True
                    else:
                        st.session_state.eyes_closed = False
            
            # Minute Handling
            if time.time() - st.session_state.minute_start >= 60:
                if st.session_state.blink_count < NORMAL_MAX:
                    st.session_state.show_reminder = True
                    st.session_state.reminder_start = time.time()
                
                st.session_state.blink_count = 0
                st.session_state.minute_start = time.time()
            
            # Total Timer
            total_elapsed = time.time() - st.session_state.start_time
            if total_elapsed >= TOTAL_TIME:
                st.session_state.camera_active = False
                st.success("✅ Session completed! Great job!")
                break
            
            remaining = TOTAL_TIME - int(total_elapsed)
            minutes_left = remaining // 60
            seconds_left = remaining % 60
            
            # Display on Frame
            cv2.putText(
                frame,
                f"Blinks/min: {st.session_state.blink_count} / 20",
                (10, frame.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )
            
            cv2.putText(
                frame,
                f"Time left: {minutes_left}:{seconds_left:02d}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (200, 200, 200),
                2
            )
            
            # Gentle Reminder
            if st.session_state.show_reminder:
                if time.time() - st.session_state.reminder_start <= REMINDER_DURATION:
                    cx = frame.shape[1] - 60
                    cy = 50
                    
                    # Open eye
                    cv2.ellipse(frame, (cx, cy), (22, 11), 0, 0, 360, (255, 255, 255), 2)
                    
                    # Blinking pupil
                    blink_phase = int(time.time() * 2) % 2
                    if blink_phase == 0:
                        cv2.circle(frame, (cx, cy), 3, (255, 255, 255), -1)
                    
                    cv2.putText(
                        frame,
                        "Blink",
                        (cx - 20, cy + 25),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        2
                    )
                else:
                    st.session_state.show_reminder = False
            
            # Convert BGR to RGB for Streamlit
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Display frame with controlled size
            video_placeholder.image(frame_rgb, channels="RGB", width=640, caption="Your Video Feed")
            
            time.sleep(0.03)  # ~30 fps
        
        camera.release()
        face_mesh.close()
        
        if stop_button:
            st.session_state.camera_active = False
            st.rerun()

    else:
        st.info("👆 Click 'Start Camera' to begin monitoring your blink rate")
        st.markdown("""
        **How it works:**
        - The app tracks your blinks per minute in real-time
        - Aim for at least 20 blinks per minute to keep your eyes healthy
        - You'll see a gentle reminder (blinking eye icon) if you blink too little
        - Session duration: 5 minutes
        """)

    # Footer
    st.markdown("---")
    st.markdown("💡 **Tip**: Remember to take breaks and blink regularly to prevent eye strain!")
