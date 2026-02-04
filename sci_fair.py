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
import streamlit.components.v1 as components

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
    except Exception as e:
        try:
            logo = Image.open("blink_logo.png")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(logo, width=width_px)
        except:
            st.info("💡 Tip: Place 'blink_logo.png' in the same directory.")

display_logo()

# ----------------------------
# Data load
# ----------------------------
@st.cache_data
def load_data():
    try:
        df = pd.read_csv(r"countries.csv")
        return df
    except:
        return pd.DataFrame(columns=["Country", "City", "Currency_Code", "Number"])

df = load_data()

# ----------------------------
# PDF generation
# ----------------------------
def generate_pdf_from_text_and_image(text_content: str, image_bytes: bytes | None = None, logo_path: str | None = None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    if logo_path:
        try:
            logo_img = RLImage(logo_path)
            logo_img._restrictSize(LOGO_PDF_WIDTH, LOGO_PDF_HEIGHT)
            story.append(logo_img)
        except: pass
    story.append(Paragraph("Eye Photo + Gemini Notes", styles["Heading1"]))
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
# Webcam Component - FIXED STRING
# ----------------------------
def webcam_with_hidden_upload():
    # ADDED: This is the target the JS looks for. We hide it with CSS.
    st.markdown("""
        <style>
            .stFileUploader { display: none; }
        </style>
    """, unsafe_allow_html=True)
    st.file_uploader("Hidden Upload", type=['jpg', 'png', 'jpeg'], key="hidden_uploader")

    html_code = """
    <div style="border: 2px solid #3498db; padding: 20px; border-radius: 10px; background-color: #f9f9f9; text-align: center;">
        <video id="video" width="640" height="480" autoplay style="border: 2px solid #333; border-radius: 8px; display: inline-block;"></video><br>
        <button id="startBtn" style="margin-top: 15px; padding: 12px 24px; font-size: 16px; background-color: #3498db; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">📸 Start Camera</button>
        <button id="captureBtn" style="margin-top: 15px; padding: 12px 24px; font-size: 16px; background-color: #2ecc71; color: white; border: none; border-radius: 6px; cursor: pointer; display: none; font-weight: bold;">Analyze Image</button>
        <canvas id="canvas" style="display:none;"></canvas>
    </div>
    <script>
        const video = document.getElementById('video');
        const startBtn = document.getElementById('startBtn');
        const captureBtn = document.getElementById('captureBtn');
        const canvas = document.getElementById('canvas');
        let stream = null;

        startBtn.onclick = async () => {
            stream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = stream;
            startBtn.style.display = 'none';
            captureBtn.style.display = 'inline-block';
        };

        captureBtn.onclick = () => {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            canvas.toBlob((blob) => {
                const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
                const container = new DataTransfer();
                container.items.add(file);
                const fileInput = window.parent.document.querySelector('input[type="file"]');
                if (fileInput) {
                    fileInput.files = container.files;
                    fileInput.dispatchEvent(new Event('change', { bubbles: true }));
                } else {
                    alert("Could not find upload element. Please refresh the page.");
                }
            }, 'image/jpeg');
        };
    </script>
    """
    components.html(html_code, height=600)

# ----------------------------
# Main Logic
# ----------------------------
webcam_with_hidden_upload()

# Check if an image was "uploaded" by the JS
if st.session_state.get("hidden_uploader"):
    image_data = st.session_state["hidden_uploader"].read()
    st.image(image_data, caption="Captured Image")
    
    # Gemini Analysis
    if st.button("Generate Report"):
        response = model.generate_content([
            "Analyze this eye image.",
            {"mime_type": "image/jpeg", "data": image_data}
        ])
        st.write(response.text)
        
        pdf = generate_pdf_from_text_and_image(response.text, image_data)
        st.download_button("Download PDF", pdf, "eye_report.pdf")
