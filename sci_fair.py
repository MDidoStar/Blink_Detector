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
# CONFIGURATION
# ----------------------------
LOGO_WIDTH_PX = 250
LOGO_PDF_WIDTH = 150
LOGO_PDF_HEIGHT = 75

st.set_page_config(page_title="Blink - Eye Health Check", page_icon="👁️", layout="wide")

# ----------------------------
# Display Logo
# ----------------------------
def display_logo(width_px=LOGO_WIDTH_PX):
    try:
        # Priority 1: Specific path provided in your snippet
        logo = Image.open("/mnt/user-data/uploads/1770146718890_image.png")
        st.image(logo, width=width_px)
    except:
        try:
            # Priority 2: Local directory
            logo = Image.open("blink_logo.png")
            st.image(logo, width=width_px)
        except:
            st.info("💡 Logo not found. Place 'blink_logo.png' in the script folder.")

display_logo()

# ----------------------------
# Data load logic
# ----------------------------
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("countries.csv")
        return df
    except:
        return pd.DataFrame(columns=["Country", "City", "Currency_Code", "Number"])

df = load_data()

# ----------------------------
# PDF generation logic
# ----------------------------
def generate_pdf_from_text_and_image(text_content, image_bytes=None, logo_path=None):
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

    story.append(Paragraph("Eye Health Report", styles["Heading1"]))
    
    if image_bytes:
        img_buf = io.BytesIO(image_bytes)
        rl_img = RLImage(img_buf)
        rl_img._restrictSize(400, 300)
        story.append(rl_img)

    story.append(Paragraph(text_content.replace("\n", "<br/>"), styles["Normal"]))
    doc.build(story)
    return buffer.getvalue()

# ----------------------------
# THE FIX: Hidden Uploader & JavaScript
# ----------------------------

# 1. We create the uploader first so the DOM finds it
st.markdown('<div id="uploader-container">', unsafe_allow_html=True)
uploaded_file = st.file_uploader("Upload or Capture", type=["jpg", "png", "jpeg"])
st.markdown('</div>', unsafe_allow_html=True)

# 2. Hide the uploader UI using CSS
st.markdown("""
    <style>
        [data-testid="stFileUploader"] { display: none; }
    </style>
""", unsafe_allow_html=True)

def webcam_with_hidden_upload():
    html_code = """
    <div style="text-align: center; border: 2px solid #3498db; padding: 10px; border-radius: 10px;">
        <video id="video" width="400" height="300" autoplay style="border-radius: 5px;"></video><br>
        <button id="captureBtn" style="background: #2ecc71; color: white; padding: 10px; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px;">
            📸 Capture & Analyze
        </button>
        <canvas id="canvas" style="display:none;"></canvas>
    </div>

    <script>
        const video = document.getElementById('video');
        const captureBtn = document.getElementById('captureBtn');
        const canvas = document.getElementById('canvas');

        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => { video.srcObject = stream; });

        captureBtn.addEventListener('click', () => {
            const context = canvas.getContext('2d');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0);
            
            canvas.toBlob((blob) => {
                const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
                const container = new DataTransfer();
                container.items.add(file);
                
                // This targets the Streamlit File Uploader in the parent window
                const selector = 'input[type="file"]';
                const fileInput = window.parent.document.querySelector(selector);
                
                if (fileInput) {
                    fileInput.files = container.files;
                    fileInput.dispatchEvent(new Event('change', { bubbles: true }));
                } else {
                    alert("Streamlit input not found. Please refresh.");
                }
            }, 'image/jpeg');
        });
    </script>
    """
    components.html(html_code, height=450)

# ----------------------------
# Main App Execution
# ----------------------------
if not uploaded_file:
    webcam_with_hidden_upload()
else:
    st.success("Image Captured Successfully!")
    st.image(uploaded_file)
    
    if st.button("Generate AI Analysis"):
        img_data = uploaded_file.getvalue()
        response = model.generate_content([
            "Analyze this eye for health issues. Provide a clear summary.",
            {"mime_type": "image/jpeg", "data": img_data}
        ])
        st.write(response.text)
        
        pdf_bytes = generate_pdf_from_text_and_image(response.text, img_data)
        st.download_button("Download Report", pdf_bytes, "report.pdf")
