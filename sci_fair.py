import io
import re
import base64
import streamlit as st
import google.generativeai as genai
import pandas as pd
import streamlit.components.v1 as components
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
# Logo Display
# ----------------------------
try:
    logo = Image.open("blink_logo.png")
    st.image(logo, width=250)
except:
    pass

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

# ----------------------------
# Form Inputs
# ----------------------------
selected_country = st.selectbox("Select Country", get_countries())
selected_city = st.selectbox("Select City", get_cities(selected_country))
age = st.number_input("Enter Age", min_value=0, max_value=120, value=25)

# ----------------------------
# PDF generation
# ----------------------------
def generate_pdf_from_text_and_image(text_content: str, image_bytes: bytes | None = None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    story = [Paragraph("Eye Photo + Gemini Notes", styles["Heading1"]), Spacer(1, 10)]
    if image_bytes:
        img_buf = io.BytesIO(image_bytes)
        rl_img = RLImage(img_buf)
        rl_img._restrictSize(440, 280)
        story.append(rl_img)
    story.append(Paragraph(text_content.replace("\n", "<br/>"), styles["Normal"]))
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# ----------------------------
# Webcam Component - RESTORED 120 FRAMES
# ----------------------------
def webcam_with_hidden_upload():
    st.markdown("<style>.stFileUploader { display: none; }</style>", unsafe_allow_html=True)
    captured_zip = st.file_uploader("Upload", type=['zip'], key="webcam_zip")

    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com"></script>
    </head>
    <body>
        <div style="text-align: center;">
            <video id="video" width="640" height="480" autoplay style="border: 2px solid #3498db; border-radius: 8px;"></video>
            <br><br>
            <button id="startBtn" style="padding: 10px 20px; font-size: 16px; background-color: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer;">Start Camera</button>
            <button id="captureBtn" style="padding: 10px 20px; font-size: 16px; background-color: #27ae60; color: white; border: none; border-radius: 5px; cursor: pointer;" disabled>Capture & Upload 120 Frames</button>
            <canvas id="canvas" style="display: none;"></canvas>
            <p id="status" style="margin-top: 10px; font-size: 14px; color: #555;"></p>
        </div>

        <script>
            const video = document.getElementById('video');
            const startBtn = document.getElementById('startBtn');
            const captureBtn = document.getElementById('captureBtn');
            const status = document.getElementById('status');
            const canvas = document.getElementById('canvas');
            const zip = new JSZip();
            
            startBtn.onclick = async () => {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                video.srcObject = stream;
                captureBtn.disabled = false;
            };

            captureBtn.onclick = async () => {
                captureBtn.disabled = true;
                const totalFrames = 120;
                for (let i = 0; i < totalFrames; i++) {
                    status.textContent = `📸 Capturing frame ${i+1}/${totalFrames}...`;
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    canvas.getContext('2d').drawImage(video, 0, 0);
                    const blob = await new Promise(res => canvas.toBlob(res, 'image/jpeg'));
                    zip.file(`frame_${i}.jpg`, blob);
                    await new Promise(r => setTimeout(r, 30)); // Frame interval
                }
                status.textContent = "📦 Processing ZIP...";
                const content = await zip.generateAsync({type: "blob"});
                const file = new File([content], "capture.zip", {type: "application/zip"});
                const container = new DataTransfer();
                container.items.add(file);
                const fileInput = window.parent.document.querySelector('input[type="file"]');
                if (fileInput) {
                    fileInput.files = container.files;
                    fileInput.dispatchEvent(new Event('change', { bubbles: true }));
                }
            };
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=650)
    return captured_zip

# ----------------------------
# Execution Logic
# ----------------------------
zip_result = webcam_with_hidden_upload()

if zip_result:
    st.success("120 frames uploaded successfully.")
