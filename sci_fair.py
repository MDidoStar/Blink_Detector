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
# CONFIGURATION - Adjust these settings
# ----------------------------
LOGO_WIDTH_PX = 250  # Logo width in pixels for web display (try 200, 300, 400, 600, etc.)
LOGO_PDF_WIDTH = 150  # Logo width in PDF reports (try 100, 150, 200, 300, etc.)
LOGO_PDF_HEIGHT = 75  # Logo height in PDF reports (try 50, 100, 150, etc.)

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
    """Display the Blink logo at the top of the app
    
    Args:
        width_px: Width of the logo in pixels (default from LOGO_WIDTH_PX config)
    """
    try:
        # Try to open from uploads directory
        logo = Image.open("/mnt/user-data/uploads/1770146718890_image.png")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(logo, width=width_px)
    except Exception as e:
        # If that fails, try from current directory
        try:
            logo = Image.open("blink_logo.png")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(logo, width=width_px)
        except:
            st.info("💡 Tip: Place 'blink_logo.png' in the same directory as this script to display the logo.")

# Display logo
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

    # Add logo to PDF if available
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
# Browser-Compatible Webcam Component
# ----------------------------
def webcam_capture_component():
    """
    Cross-browser compatible webcam capture that downloads frames as ZIP
    Works on Chrome, Firefox, Safari, and Edge
    """
    html_code = """
    <!-- Load JSZip from CDN first -->
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
            📷 Capture & Download 120 Frames
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

            // Cross-browser getUserMedia
            const getUserMedia = navigator.mediaDevices?.getUserMedia || 
                                 navigator.webkitGetUserMedia || 
                                 navigator.mozGetUserMedia || 
                                 navigator.msGetUserMedia;

            startBtn.onclick = async () => {
                try {
                    // Request camera with cross-browser support
                    const constraints = {
                        video: {
                            width: { ideal: 1280 },
                            height: { ideal: 720 },
                            facingMode: 'user'
                        }
                    };

                    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                        stream = await navigator.mediaDevices.getUserMedia(constraints);
                    } else if (getUserMedia) {
                        stream = await new Promise((resolve, reject) => {
                            getUserMedia.call(navigator, constraints, resolve, reject);
                        });
                    } else {
                        throw new Error('Camera API not supported in this browser');
                    }

                    video.srcObject = stream;
                    
                    // Wait for video to be ready
                    await new Promise(resolve => {
                        video.onloadedmetadata = () => {
                            video.play();
                            resolve();
                        };
                    });

                    startBtn.style.display = 'none';
                    captureBtn.style.display = 'inline-block';
                    status.textContent = '✅ Camera ready! Click "Capture & Download 120 Frames" when ready.';
                    status.style.color = '#27ae60';
                } catch (err) {
                    console.error('Camera error:', err);
                    status.textContent = '❌ Camera access denied or not available: ' + err.message;
                    status.style.color = '#e74c3c';
                }
            };

            captureBtn.onclick = async () => {
                captureBtn.disabled = true;
                captureBtn.style.backgroundColor = '#95a5a6';
                captureBtn.style.cursor = 'not-allowed';
                status.textContent = '⏳ Preparing capture...';
                status.style.color = '#f39c12';

                try {
                    const frames = [];
                    const totalFrames = 120;
                    const interval = 100; // ms between frames

                    canvas.width = video.videoWidth || 640;
                    canvas.height = video.videoHeight || 480;

                    // Capture frames
                    for (let i = 0; i < totalFrames; i++) {
                        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                        
                        // Convert to blob with cross-browser support
                        const blob = await new Promise(resolve => {
                            if (canvas.toBlob) {
                                canvas.toBlob(resolve, 'image/jpeg', 0.85);
                            } else if (canvas.msToBlob) {
                                // IE/Edge legacy support
                                resolve(canvas.msToBlob());
                            } else {
                                // Fallback using data URL
                                const dataURL = canvas.toDataURL('image/jpeg', 0.85);
                                const byteString = atob(dataURL.split(',')[1]);
                                const ab = new ArrayBuffer(byteString.length);
                                const ia = new Uint8Array(ab);
                                for (let j = 0; j < byteString.length; j++) {
                                    ia[j] = byteString.charCodeAt(j);
                                }
                                resolve(new Blob([ab], { type: 'image/jpeg' }));
                            }
                        });
                        
                        frames.push(blob);
                        status.textContent = `📸 Captured ${i + 1}/${totalFrames} frames...`;
                        
                        // Small delay between captures
                        await new Promise(resolve => setTimeout(resolve, interval));
                    }

                    status.textContent = '🔄 Creating ZIP file...';
                    status.style.color = '#3498db';

                    // Check if JSZip is loaded
                    if (typeof JSZip === 'undefined') {
                        throw new Error('JSZip library not loaded. Please refresh the page.');
                    }

                    // Create ZIP file
                    const zip = new JSZip();
                    frames.forEach((blob, idx) => {
                        const frameNum = String(idx).padStart(3, '0');
                        zip.file(`frame_${frameNum}.jpg`, blob);
                    });

                    // Generate ZIP
                    const zipBlob = await zip.generateAsync({
                        type: 'blob',
                        compression: 'DEFLATE',
                        compressionOptions: { level: 6 }
                    });

                    // Create download link (works in all browsers)
                    const url = URL.createObjectURL(zipBlob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = 'captured_frames.zip';
                    document.body.appendChild(a);
                    a.click();
                    
                    // Cleanup
                    setTimeout(() => {
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                    }, 100);

                    status.textContent = '✅ Download complete! Please upload the ZIP file below.';
                    status.style.color = '#27ae60';

                    // Re-enable button
                    captureBtn.disabled = false;
                    captureBtn.style.backgroundColor = '#2ecc71';
                    captureBtn.style.cursor = 'pointer';

                } catch (err) {
                    console.error('Capture error:', err);
                    status.textContent = '❌ Error: ' + err.message;
                    status.style.color = '#e74c3c';
                    captureBtn.disabled = false;
                    captureBtn.style.backgroundColor = '#2ecc71';
                    captureBtn.style.cursor = 'pointer';
                }
            };

            // Cleanup on page unload
            window.addEventListener('beforeunload', () => {
                if (stream) {
                    stream.getTracks().forEach(track => track.stop());
                }
            });
        })();
    </script>
    """
    st.components.v1.html(html_code, height=680)

# ----------------------------
# Main App
# ----------------------------
# Create centered layout
col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    st.title("Check your Eye Health & Safety")
    
    st.subheader("Step 1: Capture 120 frames")
    
    # Initialize session state
    if 'captured_frames' not in st.session_state:
        st.session_state.captured_frames = None
    
    # Render webcam component
    webcam_capture_component()
    
    st.info("📥 After capturing, a ZIP file will download automatically. Upload it below:")
    
    # Manual file uploader
    uploaded_zip = st.file_uploader("Upload the captured frames ZIP file", type=['zip'], key="manual_upload")
    
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
        st.stop()
    
    age_num = st.selectbox("Age", numbers, key="an")
    
    st.write("---")
    
    if st.button("Step 4: 📊 Analyze Frames with AI", key="analyze_btn"):
        if st.session_state.captured_frames is None or len(st.session_state.captured_frames) == 0:
            st.error("⚠️ Please capture and upload frames first!")
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
    
            # Generate PDF with logo
            logo_path = None
            # Try to find logo in multiple locations
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
                    label="Download PDF Report ⬇️",
                    data=pdf_content,
                    file_name="eye_health_recommendations.pdf",
                    mime="application/pdf"
                )
