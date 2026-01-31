import io
import re
import base64
import json
import streamlit as st
import google.generativeai as genai
import pandas as pd
from streamlit.components.v1 import html

from reportlab.platypus import (
    SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

# ----------------------------
# Gemini setup
# ----------------------------
genai.configure(api_key="AIzaSyAKwnlK_HmJG1nOuadrjW68kF8adrvqu8I")
model = genai.GenerativeModel("gemini-2.5-flash")

# ----------------------------
# Data load
# ----------------------------
@st.cache_data
def load_data():
    try:
        df = pd.read_csv(r"countries.csv")

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
        st.error(r"Error: 'countries.csv' file not found. Please check the path.")
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
# PDF generation
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
# Direct JavaScript to Streamlit Communication
# ----------------------------
def webcam_direct_capture():
    """
    Captures frames directly and stores them in browser localStorage,
    then uses query params to trigger Streamlit to read them
    """
    
    # Get unique key for this session
    if 'capture_key' not in st.session_state:
        import random
        st.session_state.capture_key = f"frames_{random.randint(1000, 9999)}"
    
    capture_key = st.session_state.capture_key
    
    html_code = f"""
    <div style="text-align: center;">
        <video id="video" width="640" height="480" autoplay style="border: 2px solid #3498db; border-radius: 8px;"></video>
        <br><br>
        <button id="startBtn" style="padding: 10px 20px; font-size: 16px; background-color: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px;">
            Start Camera
        </button>
        <button id="captureBtn" style="padding: 10px 20px; font-size: 16px; background-color: #27ae60; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px;" disabled>
            Capture 120 Frames
        </button>
        <canvas id="canvas" style="display: none;"></canvas>
        <p id="status" style="margin-top: 10px; font-size: 14px; color: #555;"></p>
        <p id="progress" style="margin-top: 5px; font-size: 14px; font-weight: bold; color: #3498db;"></p>
        <input type="hidden" id="framesData" value="">
    </div>

    <script>
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const startBtn = document.getElementById('startBtn');
        const captureBtn = document.getElementById('captureBtn');
        const status = document.getElementById('status');
        const progress = document.getElementById('progress');
        const framesDataInput = document.getElementById('framesData');
        const ctx = canvas.getContext('2d');
        
        let stream = null;
        const BATCH_SIZE = 10; // Send frames in batches to avoid localStorage limits

        startBtn.onclick = async () => {{
            try {{
                status.textContent = 'Requesting camera access...';
                stream = await navigator.mediaDevices.getUserMedia({{ 
                    video: {{ width: 640, height: 480 }} 
                }});
                video.srcObject = stream;
                status.textContent = '✅ Camera active! Ready to capture.';
                captureBtn.disabled = false;
                startBtn.disabled = true;
            }} catch (err) {{
                status.textContent = '❌ Error: ' + err.message;
                console.error('Camera error:', err);
            }}
        }};

        captureBtn.onclick = async () => {{
            if (!stream) {{
                status.textContent = 'Please start the camera first!';
                return;
            }}

            captureBtn.disabled = true;
            status.textContent = '📸 Capturing... Look at camera and blink normally.';
            
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;

            const allFrames = [];
            
            // Capture frames
            for (let i = 0; i < 120; i++) {{
                ctx.drawImage(video, 0, 0);
                const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
                const base64 = dataUrl.split(',')[1];
                allFrames.push(base64);
                
                progress.textContent = `Captured ${{i + 1}}/120 frames`;
                await new Promise(resolve => setTimeout(resolve, 30));
            }}

            status.textContent = '📤 Sending frames to Streamlit...';
            progress.textContent = '';
            
            // Store frames in batches in localStorage
            const totalBatches = Math.ceil(allFrames.length / BATCH_SIZE);
            
            for (let batch = 0; batch < totalBatches; batch++) {{
                const start = batch * BATCH_SIZE;
                const end = Math.min(start + BATCH_SIZE, allFrames.length);
                const batchFrames = allFrames.slice(start, end);
                
                localStorage.setItem(`{capture_key}_batch_${{batch}}`, JSON.stringify(batchFrames));
            }}
            
            localStorage.setItem('{capture_key}_total_batches', totalBatches.toString());
            localStorage.setItem('{capture_key}_ready', 'true');
            
            // Signal Streamlit by setting value
            framesDataInput.value = 'READY';
            framesDataInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
            
            status.textContent = '✅ Frames captured! Click "Load Frames" button below to continue.';
            captureBtn.disabled = false;
        }};
        
        // Also expose function globally
        window.getFramesFromStorage = function() {{
            const ready = localStorage.getItem('{capture_key}_ready');
            if (!ready) return null;
            
            const totalBatches = parseInt(localStorage.getItem('{capture_key}_total_batches') || '0');
            const allFrames = [];
            
            for (let i = 0; i < totalBatches; i++) {{
                const batch = JSON.parse(localStorage.getItem(`{capture_key}_batch_${{i}}`) || '[]');
                allFrames.push(...batch);
            }}
            
            return allFrames;
        }};
    </script>
    """
    
    html(html_code, height=680)


# JavaScript to retrieve frames from localStorage
def get_frames_from_browser():
    """Get frames stored in browser localStorage"""
    if 'capture_key' not in st.session_state:
        return None
        
    capture_key = st.session_state.capture_key
    
    retrieval_code = f"""
    <script>
        const frames = window.parent.getFramesFromStorage ? 
                      window.parent.getFramesFromStorage() : 
                      null;
        
        if (frames && frames.length > 0) {{
            // Send to Streamlit via postMessage
            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                value: frames
            }}, '*');
        }}
    </script>
    """
    
    return st.components.v1.html(retrieval_code, height=0)


# ----------------------------
# Main App
# ----------------------------
st.title("Check your Eye Health & Safety")

st.subheader("Step 1: Camera Stream (capture 120 frames)")

# Initialize session state
if 'frames_ready' not in st.session_state:
    st.session_state.frames_ready = False
if 'captured_frames' not in st.session_state:
    st.session_state.captured_frames = None

# Render webcam
webcam_direct_capture()

# Button to load frames from browser storage
if st.button("🔄 Load Captured Frames", key="load_frames_btn"):
    with st.spinner("Loading frames from browser..."):
        result = get_frames_from_browser()
        
        # Try alternative: use JavaScript to inject frames into page
        st.markdown("""
        <script>
        setTimeout(() => {{
            const frames = localStorage.getItem('{}_ready') ? 
                         window.getFramesFromStorage() : null;
            if (frames) {{
                // Store in a global variable that Python can access
                window.capturedFramesData = frames;
                console.log('Frames loaded:', frames.length);
            }}
        }}, 500);
        </script>
        """.format(st.session_state.capture_key), unsafe_allow_html=True)
        
        st.info("⏳ If frames don't load, try refreshing the page after capturing.")

st.write("---")

st.subheader("Step 2: Where are you from?")
patient_country = st.selectbox("Country:", get_countries(), key="h_country")
patient_city = st.selectbox("City:", get_cities(patient_country), key="h_city")

st.subheader("Step 3: Your Age")
numbers = get_numbers_from_file()
if not numbers:
    st.error("No numbers found in the 'Number' column in countries.csv.")
    st.stop()

age_num = st.selectbox("Age", numbers, key="an")

st.write("---")

# Alternative: Direct text input for frames
st.subheader("Alternative: Paste Frames Data")
st.info("If automatic loading doesn't work, you can manually paste the frames data here.")

frames_json = st.text_area(
    "Paste frames JSON here (from browser console: `JSON.stringify(window.getFramesFromStorage())`)",
    height=100,
    key="frames_json"
)

if frames_json and frames_json.strip():
    try:
        frames_list = json.loads(frames_json)
        if isinstance(frames_list, list) and len(frames_list) > 0:
            st.session_state.captured_frames = frames_list
            st.success(f"✅ Loaded {len(frames_list)} frames from pasted data!")
    except json.JSONDecodeError:
        st.error("Invalid JSON format")

if st.button("Step 4: 📊 Analyze Frames with AI", key="analyze_btn"):
    if st.session_state.captured_frames is None or len(st.session_state.captured_frames) == 0:
        st.error("⚠️ No frames loaded! Please capture frames and click 'Load Captured Frames', or paste frames data manually.")
    else:
        frames = st.session_state.captured_frames
        
        # Decode first frame for display
        try:
            first_frame_bytes = base64.b64decode(frames[0])
            st.image(first_frame_bytes, caption="First captured frame", use_container_width=True)

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
            for frame_b64 in frames:
                frame_bytes = base64.b64decode(frame_b64)
                contents.append({"mime_type": "image/jpeg", "data": frame_bytes})

            with st.spinner(f"Analyzing {len(frames)} frames with Gemini AI..."):
                response = model.generate_content(contents)

            st.subheader("Analysis Results:")
            st.write(response.text)

            # Generate PDF
            pdf_content = generate_pdf_from_text_and_image(response.text, first_frame_bytes)

            if pdf_content:
                st.subheader("Step 5: Download and Save your data")
                st.download_button(
                    label="Download PDF Report ⬇️",
                    data=pdf_content,
                    file_name="eye_health_recommendations.pdf",
                    mime="application/pdf"
                )
        except Exception as e:
            st.error(f"Error processing frames: {e}")
