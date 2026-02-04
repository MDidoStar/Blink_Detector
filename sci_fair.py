"""
Standalone frame capture script - Run this first to capture 120 frames
Then upload the generated ZIP to the Streamlit app
"""

import cv2
import zipfile
import os
from datetime import datetime

def capture_120_frames():
    """Capture 120 frames from webcam and save as ZIP"""
    
    print("🎥 Starting webcam...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: Could not open webcam")
        return
    
    print("✅ Webcam ready!")
    print("📸 Press SPACE to start capturing 120 frames")
    print("Press ESC to quit")
    
    frames = []
    capturing = False
    frame_count = 0
    total_frames = 120
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            print("❌ Error: Can't receive frame")
            break
        
        # Display the frame
        cv2.imshow('Eye Capture - Press SPACE to capture 120 frames, ESC to quit', frame)
        
        # Capture frames if started
        if capturing and frame_count < total_frames:
            frames.append(frame.copy())
            frame_count += 1
            print(f"📸 Captured {frame_count}/{total_frames} frames...", end='\r')
            
            if frame_count >= total_frames:
                print(f"\n✅ Captured all {total_frames} frames!")
                capturing = False
                break
        
        # Wait for key press
        key = cv2.waitKey(1) & 0xFF
        
        if key == 27:  # ESC key
            print("\n❌ Cancelled by user")
            break
        elif key == 32 and not capturing:  # SPACE key
            print("\n⏳ Starting capture...")
            capturing = True
            frames = []
            frame_count = 0
    
    # Release webcam
    cap.release()
    cv2.destroyAllWindows()
    
    if len(frames) == total_frames:
        # Create ZIP file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"eye_frames_{timestamp}.zip"
        
        print(f"\n💾 Creating ZIP file: {zip_filename}")
        
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for i, frame in enumerate(frames):
                # Save frame to memory
                frame_filename = f"frame_{i:03d}.jpg"
                cv2.imwrite(frame_filename, frame)
                zipf.write(frame_filename)
                os.remove(frame_filename)
                
                print(f"💾 Adding frame {i+1}/{total_frames} to ZIP...", end='\r')
        
        print(f"\n✅ Successfully created {zip_filename}")
        print(f"📤 Upload this file to the Streamlit app!")
        return zip_filename
    else:
        print(f"\n❌ Only captured {len(frames)} frames. Need {total_frames}.")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("  EYE FRAME CAPTURE TOOL")
    print("=" * 60)
    print()
    
    result = capture_120_frames()
    
    if result:
        print(f"\n✅ Success! ZIP file ready: {result}")
        print("📤 Now upload this file to the Streamlit app")
    else:
        print("\n❌ Capture failed or cancelled")
    
    print("\nPress Enter to exit...")
    input()






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
genai.configure(api_key="AIzaSyD_13Y30NRcVRGNO9m4vTkhyvxusTY1qK8")
model = genai.GenerativeModel("gemini-2.5-flash")

# ----------------------------
# CONFIGURATION - Adjust these settings
# ----------------------------
LOGO_WIDTH_PX = 250
LOGO_PDF_WIDTH = 150
LOGO_PDF_HEIGHT = 75

# ----------------------------
# Page Config with Logo
# ----------------------------
st.set_page_config(
    page_title="Blink - Eye Health Check",
    page_icon="👁️",
    layout="wide"
)

# ----------------------------
# Display Logo at Top
# ----------------------------
def display_logo(width_px=LOGO_WIDTH_PX):
    """Display the Blink logo at the top of the app"""
    try:
        logo = Image.open("/mnt/user-data/uploads/1770146718890_image.png")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(logo, width=width_px)
    except Exception as e:
        try:
            logo = Image.open("blink_logo.png")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(logo, width=width_px)
        except:
            st.info("💡 Tip: Place 'blink_logo.png' in the same directory as this script to display the logo.")

display_logo()

# ----------------------------
# Data load
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
# PDF generation with logo
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
# Webcam Component with 120 Frames - DOWNLOAD ZIP
# ----------------------------
def webcam_with_download_zip():
    """
    Captures 120 frames and provides a download link for the ZIP file
    This is the most reliable method that actually works
    """
    html_code = """
    <div style="border: 2px solid #3498db; padding: 20px; border-radius: 10px; background-color: #f9f9f9; text-align: center;">
        <video id="video" width="640" height="480" autoplay style="border: 2px solid #333; border-radius: 8px; display: inline-block;"></video><br>
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
        <a id="downloadBtn" style="
            margin-top: 15px; 
            padding: 12px 24px; 
            font-size: 16px; 
            background-color: #e74c3c; 
            color: white; 
            border: none; 
            border-radius: 6px; 
            cursor: pointer;
            display: none;
            text-decoration: none;
            font-weight: bold;
        " download="captured_frames.zip">
            📥 Download ZIP File
        </a>
        <div id="status" style="margin-top: 15px; font-size: 16px; color: #555;"></div>
        <canvas id="canvas" style="display:none;"></canvas>
    </div>

    <script>
        const video = document.getElementById('video');
        const startBtn = document.getElementById('startBtn');
        const captureBtn = document.getElementById('captureBtn');
        const downloadBtn = document.getElementById('downloadBtn');
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        const status = document.getElementById('status');
        let stream = null;

        startBtn.onclick = async () => {
            try {
                stream = await navigator.mediaDevices.getUserMedia({ video: true });
                video.srcObject = stream;
                startBtn.style.display = 'none';
                captureBtn.style.display = 'inline-block';
                status.textContent = '✅ Camera ready! Click "Capture 120 Frames" when ready.';
                status.style.color = 'green';
            } catch (err) {
                status.textContent = '❌ Camera access denied: ' + err.message;
                status.style.color = 'red';
            }
        };

        function stopCamera() {
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
                video.srcObject = null;
                stream = null;
            }
        }

        captureBtn.onclick = async () => {
            captureBtn.disabled = true;
            captureBtn.style.backgroundColor = '#95a5a6';
            status.textContent = '⏳ Capturing frames...';
            status.style.color = 'orange';

            const frames = [];
            const totalFrames = 120;
            const interval = 100;

            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;

            for (let i = 0; i < totalFrames; i++) {
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8));
                frames.push(blob);
                status.textContent = `📸 Captured ${i + 1}/${totalFrames} frames...`;
                await new Promise(resolve => setTimeout(resolve, interval));
            }

            stopCamera();
            status.textContent = '🔄 Creating ZIP file...';
            
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js';
            script.onload = async () => {
                const zip = new JSZip();
                
                for (let i = 0; i < frames.length; i++) {
                    zip.file(`frame_${String(i).padStart(3, '0')}.jpg`, frames[i]);
                    if (i % 10 === 0) {
                        status.textContent = `🔄 Adding frame ${i}/${totalFrames} to ZIP...`;
                    }
                }

                const zipBlob = await zip.generateAsync({type: 'blob'});
                const url = URL.createObjectURL(zipBlob);
                
                downloadBtn.href = url;
                downloadBtn.style.display = 'inline-block';
                captureBtn.style.display = 'none';
                
                status.textContent = '✅ ZIP file ready! Click "Download ZIP File" button, then upload it below.';
                status.style.color = 'green';
                
                captureBtn.disabled = false;
                captureBtn.style.backgroundColor = '#2ecc71';
            };
            
            script.onerror = () => {
                status.textContent = '❌ Failed to load JSZip library. Please check your internet connection.';
                status.style.color = 'red';
                captureBtn.disabled = false;
                captureBtn.style.backgroundColor = '#2ecc71';
                stopCamera();
            };
            
            document.head.appendChild(script);
        };
    </script>
    """
    st.components.v1.html(html_code, height=720)

# ----------------------------
# Main App
# ----------------------------
col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    st.title("Check your Eye Health & Safety")
    
    st.subheader("Step 1: Capture 120 frames")
    st.info("📸 **Instructions**: Click 'Start Camera' → Click 'Capture 120 Frames' → Click 'Download ZIP File' → Upload the ZIP file below")
    
    # Initialize session state
    if 'captured_frames' not in st.session_state:
        st.session_state.captured_frames = None
    
    # Render webcam component
    webcam_with_download_zip()
    
    st.write("---")
    st.subheader("📤 Upload the captured ZIP file")
    
    uploaded_zip = st.file_uploader("Upload the ZIP file you just downloaded", type=['zip'], key="zip_upload")
    
    # Process uploaded ZIP
    if uploaded_zip is not None:
        import zipfile
        try:
            with zipfile.ZipFile(uploaded_zip, 'r') as zip_ref:
                frame_files = sorted([f for f in zip_ref.namelist() if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                if len(frame_files) < 1:
                    st.error("No image files found in the ZIP!")
                else:
                    frames_bytes = []
                    for frame_file in frame_files:
                        with zip_ref.open(frame_file) as f:
                            frames_bytes.append(f.read())
                    
                    st.session_state.captured_frames = frames_bytes
                    st.success(f"✅ Loaded {len(frames_bytes)} frames!")
                    
                    # Show first and last frame
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.image(frames_bytes[0], caption=f"First frame", use_column_width=True)
                    with col_b:
                        st.image(frames_bytes[-1], caption=f"Last frame", use_column_width=True)
                    
                    st.write(f"**Total frames: {len(frames_bytes)}**")
        except Exception as e:
            st.error(f"Error reading ZIP file: {e}")
    
    st.write("---")
    st.subheader("Step 2: Where are you from?")
    
    countries_list = get_countries()
    if not countries_list:
        st.warning("No countries available. Please check countries.csv file.")
        patient_country = ""
    else:
        patient_country = st.selectbox("Country:", countries_list, key="h_country")
    
    cities_list = get_cities(patient_country) if patient_country else []
    if not cities_list and patient_country:
        st.warning(f"No cities found for {patient_country}")
        patient_city = ""
    else:
        patient_city = st.selectbox("City:", cities_list if cities_list else [""], key="h_city")
    
    st.subheader("Step 3: Your Age")
    
    numbers = get_numbers_from_file()
    if not numbers:
        st.error("No numbers found in the 'Number' column in countries.csv.")
        st.stop()
    
    age_num = st.selectbox("Age", numbers, key="an")
    
    st.write("---")
    
    if st.button("Step 4: 📊 Analyze Frames with AI", key="analyze_btn", type="primary"):
        if st.session_state.captured_frames is None or len(st.session_state.captured_frames) == 0:
            st.error("⚠️ Please upload the ZIP file with captured frames first!")
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
                try:
                    response = model.generate_content(contents)
                    
                    st.subheader("Analysis Results:")
                    st.write(response.text)
    
                    # Generate PDF with logo
                    logo_path = None
                    for path in ["/mnt/user-data/uploads/1770146718890_image.png", "blink_logo.png", "/home/claude/blink_logo.png"]:
                        try:
                            with open(path, 'rb'):
                                logo_path = path
                                break
                        except:
                            continue
                    
                    pdf_content = generate_pdf_from_text_and_image(response.text, frames[0], logo_path)
    
                    if pdf_content:
                        st.subheader("Step 5: Download your Report")
                        st.download_button(
                            label="📄 Download PDF Report",
                            data=pdf_content,
                            file_name="eye_health_recommendations.pdf",
                            mime="application/pdf"
                        )
                except Exception as e:
                    st.error(f"Error during AI analysis: {e}")
                    st.error("This might be due to API limits or connectivity issues. Please try again.")

st.write("---")
st.caption("⚠️ **Disclaimer**: This tool is for informational purposes only and does not replace professional medical advice. Always consult with an eye care professional for proper diagnosis and treatment.")









