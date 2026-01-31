import io
import re
import base64
import zipfile
import streamlit as st
import google.generativeai as genai
import pandas as pd

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
# JavaScript Webcam Component
# ----------------------------
def webcam_capture_interface():
    """Renders webcam capture with download option"""
    html_code = """
    <div style="text-align: center;">
        <video id="video" width="640" height="480" autoplay style="border: 2px solid #3498db; border-radius: 8px;"></video>
        <br><br>
        <button id="startBtn" style="padding: 10px 20px; font-size: 16px; background-color: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px;">
            Start Camera
        </button>
        <button id="captureBtn" style="padding: 10px 20px; font-size: 16px; background-color: #27ae60; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px;" disabled>
            Capture 120 Frames
        </button>
        <button id="downloadBtn" style="padding: 10px 20px; font-size: 16px; background-color: #e74c3c; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px; display: none;">
            Download ZIP
        </button>
        <canvas id="canvas" style="display: none;"></canvas>
        <p id="status" style="margin-top: 10px; font-size: 14px; color: #555;"></p>
        <p id="progress" style="margin-top: 5px; font-size: 14px; font-weight: bold; color: #3498db;"></p>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
    <script>
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const startBtn = document.getElementById('startBtn');
        const captureBtn = document.getElementById('captureBtn');
        const downloadBtn = document.getElementById('downloadBtn');
        const status = document.getElementById('status');
        const progress = document.getElementById('progress');
        const ctx = canvas.getContext('2d');
        
        let stream = null;
        let capturedFrames = [];

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

            capturedFrames = [];
            captureBtn.disabled = true;
            status.textContent = '📸 Capturing... Look at camera and blink normally.';
            
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;

            for (let i = 0; i < 120; i++) {
                ctx.drawImage(video, 0, 0);
                canvas.toBlob((blob) => {
                    capturedFrames.push(blob);
                }, 'image/jpeg', 0.85);
                
                progress.textContent = `Captured ${i + 1}/120 frames`;
                await new Promise(resolve => setTimeout(resolve, 30));
            }
            
            // Wait a bit for all blobs to be created
            await new Promise(resolve => setTimeout(resolve, 100));

            status.textContent = '✅ Capture complete! Click "Download ZIP" to save frames.';
            progress.textContent = '';
            downloadBtn.style.display = 'inline-block';
            captureBtn.disabled = false;
        };

        downloadBtn.onclick = async () => {
            if (capturedFrames.length === 0) {
                status.textContent = 'No frames to download!';
                return;
            }

            status.textContent = '📦 Creating ZIP file...';
            const zip = new JSZip();
            
            for (let i = 0; i < capturedFrames.length; i++) {
                const blob = capturedFrames[i];
                zip.file(`frame_${String(i).padStart(3, '0')}.jpg`, blob);
            }
            
            const zipBlob = await zip.generateAsync({type: 'blob'});
            const url = URL.createObjectURL(zipBlob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'eye_frames.zip';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            status.textContent = '✅ ZIP downloaded! Upload it below to analyze.';
        };
    </script>
    """
    
    st.components.v1.html(html_code, height=680)


# ----------------------------
# Main App
# ----------------------------
st.title("Check your Eye Health & Safety")

st.subheader("Step 1A: Capture Frames with Your Camera")
st.info("📱 Use the camera below to capture 120 frames, then download the ZIP file and upload it in Step 1B.")

webcam_capture_interface()

st.write("---")

st.subheader("Step 1B: Upload Your Captured Frames")
uploaded_zip = st.file_uploader("Upload the ZIP file you downloaded above", type=['zip'], key="zip_upload")

# Initialize session state
if 'frames_bytes' not in st.session_state:
    st.session_state.frames_bytes = None

# Process uploaded ZIP
if uploaded_zip is not None:
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
                
                st.session_state.frames_bytes = frames_bytes
                st.success(f"✅ Loaded {len(frames_bytes)} frames from ZIP!")
                
                # Show first frame
                st.image(frames_bytes[0], caption=f"First frame preview (total: {len(frames_bytes)} frames)", use_container_width=True)
    
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
    st.stop()

age_num = st.selectbox("Age", numbers, key="an")

st.write("---")

if st.button("Step 4: 📊 Analyze Frames with AI", key="analyze_btn"):
    if st.session_state.frames_bytes is None:
        st.error("⚠️ Please upload your captured frames ZIP file first!")
    else:
        frames = st.session_state.frames_bytes
        
        # Show first frame again
        st.image(frames[0], caption="Analyzing this frame and others...", use_container_width=True)

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

        with st.spinner(f"Analyzing {len(frames)} frames with Gemini AI... This may take a moment."):
            response = model.generate_content(contents)

        st.subheader("Analysis Results:")
        st.write(response.text)

        # Generate PDF
        pdf_content = generate_pdf_from_text_and_image(response.text, frames[0])

        if pdf_content:
            st.subheader("Step 5: Download and Save your data")
            st.download_button(
                label="Download PDF Report ⬇️",
                data=pdf_content,
                file_name="eye_health_recommendations.pdf",
                mime="application/pdf"
            )
