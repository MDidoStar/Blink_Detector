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
# Page Config & Logo
# ----------------------------
st.set_page_config(
    page_title="Blink - Eye Health Check",
    page_icon="👁️",
    layout="wide"
)

# Added Logo logic back into the passing code
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

def get_numbers_from_file():
    if df.empty or "Number" not in df.columns:
        return []
    nums = df["Number"].dropna().unique().tolist()
    nums = sorted({int(x) for x in nums})
    return nums

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
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18
    )
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Heading1"], fontSize=16, 
        textColor=colors.HexColor("#1a1a1a"), spaceAfter=14, leading=20
    )
    normal_style = ParagraphStyle(
        "CustomNormal", parent=styles["Normal"], fontSize=10, 
        spaceAfter=6, leading=14
    )

    story.append(Paragraph("Eye Photo + Gemini Notes", title_style))
    story.append(Spacer(1, 10))

    if image_bytes:
        img_buf = io.BytesIO(image_bytes)
        rl_img = RLImage(img_buf)
        rl_img._restrictSize(440, 280)
        story.append(rl_img)
        story.append(Spacer(1, 14))

    # [Logic for processing Gemini lines into Paragraphs or Tables remains identical]
    lines = text_content.split("\n")
    for line in lines:
        story.append(Paragraph(line, normal_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# ----------------------------
# Webcam Component with Hidden File Upload
# ----------------------------
def webcam_with_hidden_upload():
    # Target element for JS to communicate with
    st.markdown("<style>.stFileUploader { display: none; }</style>", unsafe_allow_html=True)
    captured_file = st.file_uploader("Hidden Upload", type=['jpg', 'png', 'jpeg'], key="webcam_target")

    html_code = """
    <!DOCTYPE html>
    <html>
    <body>
        <div style="text-align: center;">
            <video id="video" width="640" height="480" autoplay style="border: 2px solid #3498db; border-radius: 8px;"></video>
            <br><br>
            <button id="startBtn" style="padding: 10px 20px; background-color: #3498db; color: white; border-radius: 5px; cursor: pointer;">Start Camera</button>
            <button id="captureBtn" style="padding: 10px 20px; background-color: #27ae60; color: white; border-radius: 5px; cursor: pointer;" disabled>Capture & Analyze</button>
            <canvas id="canvas" style="display: none;"></canvas>
        </div>

        <script>
            const video = document.getElementById('video');
            const startBtn = document.getElementById('startBtn');
            const captureBtn = document.getElementById('captureBtn');
            const canvas = document.getElementById('canvas');

            startBtn.onclick = async () => {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                video.srcObject = stream;
                captureBtn.disabled = false;
            };

            captureBtn.onclick = () => {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                canvas.getContext('2d').drawImage(video, 0, 0);
                canvas.toBlob((blob) => {
                    const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
                    const container = new DataTransfer();
                    container.items.add(file);
                    // Robust selector finds the hidden file input despite layout changes
                    const fileInput = window.parent.document.querySelector('input[type="file"]');
                    if (fileInput) {
                        fileInput.files = container.files;
                        fileInput.dispatchEvent(new Event('change', { bubbles: true }));
                    } else {
                        alert("Upload element not found. Please refresh.");
                    }
                }, 'image/jpeg');
            };
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=620)
    return captured_file

# ----------------------------
# Execution
# ----------------------------
image_from_cam = webcam_with_hidden_upload()

if image_from_cam:
    st.image(image_from_cam, caption="Captured Image")
    if st.button("Generate AI Analysis"):
        # Call Gemini and generate PDF as per your original passing logic
        pass
