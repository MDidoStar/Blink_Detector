import io
import re
import base64
import streamlit as st
import google.generativeai as genai
import pandas as pd
from reportlab.platypus import (
    SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from PIL import Image

# ----------------------------
# Gemini setup
# ----------------------------
genai.configure(api_key="AIzaSyD-UBEMP78gtwa1DVBj2zeaFZaPfRCiZAE")
model = genai.GenerativeModel("gemini-2.5-flash")

# ----------------------------
# CONFIGURATION
# ----------------------------
LOGO_WIDTH_PX = 250
LOGO_PDF_WIDTH = 150
LOGO_PDF_HEIGHT = 75

# ----------------------------
# Page Config
# ----------------------------
st.set_page_config(
    page_title="Blink - Eye Health Check",
    page_icon="👁️",
    layout="wide"
)

# ----------------------------
# Display Logo
# ----------------------------
def display_logo(width_px=LOGO_WIDTH_PX):
    try:
        logo = Image.open("/mnt/user-data/uploads/1770146718890_image.png")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(logo, width=width_px)
    except:
        try:
            logo = Image.open("blink_logo.png")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(logo, width=width_px)
        except:
            st.info("💡 Tip: Place 'blink_logo.png' in the same directory to display the logo.")

display_logo()

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
        st.error(r"Error: 'countries.csv' file not found.")
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
def generate_pdf_from_text_and_image(text_content: str, image_bytes: bytes | None = None, logo_path: str | None = None):
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

    if logo_path:
        try:
            logo_img = RLImage(logo_path)
            logo_img._restrictSize(LOGO_PDF_WIDTH, LOGO_PDF_HEIGHT)
            story.append(logo_img)
            story.append(Spacer(1, 10))
        except Exception as e:
            print(f"Could not add logo to PDF: {e}")

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
# Webcam Component - DOWNLOAD ONLY
# ----------------------------
def webcam_capture_component():
    """Pure download approach - no auto-upload attempts"""
    html_code = """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
    
    <div style="border: 2px solid #3498db; padding: 20px; border-radius: 10px; background-color: #f9f9f9; text-align: center;">
        <video id="video" width="640" height="480" autoplay playsinline style="border: 2px solid #333; border-radius: 8px; display: inline-block;"></video><br>
        <button id="startBtn" style="
            margin-top: 15px; 
            padding: 12px 24px; 
            font-size: 16px; 
            background-color: #3498db; 
            color: white; 
            border: none; 
            border-radius: 6px; 
            cursor: pointer;
            font-weight: bold;
        ">
            📸 Start Camera
        </button>
        <button id="captureBtn" style="
            margin-top: 15px; 
            padding: 12px 24px; 
            font-size: 16px; 
            background-color: #2ecc71; 
            color: white; 
            border: none; 
            border-radius: 6px; 
            cursor: pointer;
            display: none;
            font-weight: bold;
        ">
            📷 Capture 120 Frames
        </button>
        <div id="status" style="margin-top: 15px; font-size: 16px; color: #555; font-weight: 500;">
            Click "Start Camera" to begin
        </div>
        <canvas id="canvas" style="display:none;"></canvas>
    </div>

    <script>
        (function() {
            const video = document.getElementById('video');
            const startBtn = document.getElementById('startBtn');
            const captureBtn = document.getElementById('captureBtn');
            const canvas = document.getElementById('canvas');
            const ctx = canvas.getContext('2d');
            const status = document.getElementById('status');
            let stream = null;

            startBtn.onclick = async () => {
                try {
                    const constraints = {
                        video: {
                            width: { ideal: 1280 },
                            height: { ideal: 720 },
                            facingMode: 'user'
                        }
                    };

                    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                        stream = await navigator.mediaDevices.getUserMedia(constraints);
                    } else {
                        throw new Error('Camera not supported');
                    }

                    video.srcObject = stream;
                    await new Promise(resolve => {
                        video.onloadedmetadata = () => {
                            video.play();
                            resolve();
                        };
                    });

                    startBtn.style.display = 'none';
                    captureBtn.style.display = 'inline-block';
                    status.textContent = '✅ Camera ready! Click "Capture 120 Frames"';
                    status.style.color = '#27ae60';
                } catch (err) {
                    status.textContent = '❌ Camera error: ' + err.message;
                    status.style.color = '#e74c3c';
                }
            };

            captureBtn.onclick = async () => {
                captureBtn.disabled = true;
                captureBtn.style.backgroundColor = '#95a5a6';
                status.textContent = '⏳ Capturing frames...';
                status.style.color = '#f39c12';

                try {
                    const frames = [];
                    const totalFrames = 120;
                    canvas.width = video.videoWidth || 640;
                    canvas.height = video.videoHeight || 480;

                    for (let i = 0; i < totalFrames; i++) {
                        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                        const blob = await new Promise(resolve => {
                            canvas.toBlob(resolve, 'image/jpeg', 0.85);
                        });
                        frames.push(blob);
                        status.textContent = `📸 Captured ${i + 1}/${totalFrames}...`;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }

                    status.textContent = '🔄 Creating ZIP...';

                    if (typeof JSZip === 'undefined') {
                        throw new Error('JSZip not loaded. Refresh page.');
                    }

                    const zip = new JSZip();
                    frames.forEach((blob, idx) => {
                        zip.file(`frame_${String(idx).padStart(3, '0')}.jpg`, blob);
                    });

                    const zipBlob = await zip.generateAsync({
                        type: 'blob',
                        compression: 'DEFLATE',
                        compressionOptions: { level: 6 }
                    });

                    // Download the file
                    const url = URL.createObjectURL(zipBlob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'captured_frames.zip';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);

                    status.textContent = '✅ ZIP downloaded! Now upload it below ⬇️';
                    status.style.color = '#27ae60';

                    // Stop camera
                    if (stream) {
                        stream.getTracks().forEach(track => track.stop());
                        video.srcObject = null;
                    }

                    captureBtn.disabled = false;
                    captureBtn.style.backgroundColor = '#2ecc71';

                } catch (err) {
                    status.textContent = '❌ Error: ' + err.message;
                    status.style.color = '#e74c3c';
                    captureBtn.disabled = false;
                    captureBtn.style.backgroundColor = '#2ecc71';
                }
            };
        })();
    </script>
    """
    st.components.v1.html(html_code, height=680)

# ----------------------------
# Main App
# ----------------------------
col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    st.title("Check your Eye Health & Safety")
    
    st.subheader("Step 1: Capture 120 frames")
    
    if 'captured_frames' not in st.session_state:
        st.session_state.captured_frames = None
    
    webcam_capture_component()
    
    st.markdown("---")
    st.subheader("Step 2: Upload the ZIP file")
    st.info("👆 After capturing above, a ZIP file will download. Upload it here:")
    
    uploaded_zip = st.file_uploader("Upload captured_frames.zip", type=['zip'], key="zip_upload")
    
    if uploaded_zip is not None:
        import zipfile
        try:
            with zipfile.ZipFile(uploaded_zip, 'r') as zip_ref:
                frame_files = sorted([f for f in zip_ref.namelist() if f.endswith('.jpg')])
                if len(frame_files) < 1:
                    st.error("No JPG files found in ZIP!")
                else:
                    frames_bytes = []
                    for frame_file in frame_files:
                        with zip_ref.open(frame_file) as f:
                            frames_bytes.append(f.read())
                    
                    st.session_state.captured_frames = frames_bytes
                    st.success(f"✅ Loaded {len(frames_bytes)} frames!")
                    st.image(frames_bytes[0], caption=f"Preview (total: {len(frames_bytes)} frames)", use_column_width=True)
        except Exception as e:
            st.error(f"Error reading ZIP: {e}")
    
    st.write("---")
    st.subheader("Step 3: Patient Information")
    
    patient_country = st.selectbox("Country:", get_countries(), key="country")
    patient_city = st.selectbox("City:", get_cities(patient_country), key="city")
    
    st.subheader("Step 4: Your Age")
    
    numbers = get_numbers_from_file()
    if not numbers:
        st.error("No numbers in countries.csv 'Number' column.")
        st.stop()
    
    age_num = st.selectbox("Age", numbers, key="age")
    
    st.write("---")
    
    if st.button("Step 5: 📊 Analyze with AI", key="analyze"):
        if st.session_state.captured_frames is None or len(st.session_state.captured_frames) == 0:
            st.error("⚠️ Please capture and upload frames first!")
        else:
            frames = st.session_state.captured_frames
            
            try:
                st.image(frames[0], caption="Analyzing...", use_column_width=True)
            except:
                pass
    
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
    
            contents = [prompt]
            for frame_bytes in frames:
                contents.append({"mime_type": "image/jpeg", "data": frame_bytes})
    
            with st.spinner(f"Analyzing {len(frames)} frames..."):
                response = model.generate_content(contents)
    
            st.subheader("Analysis Results:")
            st.write(response.text)
    
            logo_path = None
            for path in ["/mnt/user-data/uploads/1770146718890_image.png", "blink_logo.png"]:
                try:
                    with open(path, 'rb'):
                        logo_path = path
                        break
                except:
                    continue
            
            pdf_content = generate_pdf_from_text_and_image(response.text, frames[0], logo_path)
    
            if pdf_content:
                st.subheader("Step 6: Download Report")
                st.download_button(
                    label="📄 Download PDF Report",
                    data=pdf_content,
                    file_name="eye_health_report.pdf",
                    mime="application/pdf"
                )
