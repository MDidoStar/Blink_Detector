import io
import re
import time
import streamlit as st
import google.generativeai as genai
import pandas as pd
import av
import cv2

from streamlit_webrtc import webrtc_streamer, VideoProcessorBase

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
        # Use raw string to avoid backslash escaping on Windows
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
    """
    Returns the unique numbers from the 'Number' column as a sorted list of ints.
    Used for Age selectbox options.
    """
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

        # markdown-ish table support
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
# Webcam frame collector
# ----------------------------
class FrameCollector(VideoProcessorBase):
    def __init__(self):
        self.latest_bgr = None

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        self.latest_bgr = img
        return frame


def bgr_to_jpeg_bytes(bgr_img) -> bytes:
    ok, buf = cv2.imencode(".jpg", bgr_img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        return b""
    return buf.tobytes()


(cam_tab,) = st.tabs(["camera_tab"])


with cam_tab:
    st.title("Check your Eye health & Safety")
    st.subheader("Step 1: Camera Stream (capture 120 frames)")

    webrtc_ctx = webrtc_streamer(
        key="eye_cam",
        rtc_configuration={ 
            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
        },
        video_processor_factory=FrameCollector,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )
    st.subheader("Step 2: Where are you from?")
    patient_country = st.selectbox("Country:", get_countries(), key="h_country")
    patient_city = st.selectbox("City:", get_cities(patient_country), key="h_city")

    st.subheader("Step 3: your Age")
    numbers = get_numbers_from_file()
    if not numbers:
        st.error("No numbers found in the 'Number' column in countries.csv.")
        st.stop()

    age_num = st.selectbox("Age", numbers, key="an")

    st.write("---")
    st.caption("Look straight at the camera and blink normally for ~3–4 seconds after you press the button.")

    if st.button("Step 4: 📸 Capture 120 frames + Analyze", key="eye_check"):
        if not webrtc_ctx.state.playing or webrtc_ctx.video_processor is None:
            st.error("Webcam is not active. Please allow camera access and wait until the video starts.")
        else:
            frames_jpeg = []

            # Progress UI
            progress = st.progress(0)
            status = st.empty()

            total_frames = 120

            with st.spinner("Capturing 120 frames..."):
                for i in range(total_frames):
                    bgr = webrtc_ctx.video_processor.latest_bgr
                    if bgr is not None:
                        jpg = bgr_to_jpeg_bytes(bgr)
                        if jpg:
                            frames_jpeg.append(jpg)

                    # Progress bar: attempts (keeps behavior)
                    progress.progress(int(((i + 1) / total_frames) * 100))

                    # Optional improvement: show saved count too
                    status.write(f"Capturing frames: {i + 1}/{total_frames}  |  Saved: {len(frames_jpeg)}")

                    time.sleep(0.03)  # ~3.6 seconds total at ~30-33fps

            status.empty()

            if not frames_jpeg:
                st.error("Could not capture frames. Try again and make sure the camera is running.")
            else:
                first_frame = frames_jpeg[0]

                # Show ONLY the first frame
                st.image(first_frame, caption="First captured frame (only one shown)", use_container_width=True)

                prompt = f"""
You are given 120 sequential eye images (frames) from a webcam.
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
                for jpg in frames_jpeg:
                    contents.append({"mime_type": "image/jpeg", "data": jpg})

                with st.spinner("Analyzing frames with Gemini..."):
                    response = model.generate_content(contents)

                st.write(response.text)

                # PDF with first frame + Gemini text
                pdf_content = generate_pdf_from_text_and_image(response.text, first_frame)

                if pdf_content:
                    st.subheader("Step 5: Download and Save your data")
                    st.download_button(
                        label="Download PDF ⬇️",
                        data=pdf_content,
                        file_name="eye_health_recommendations.pdf",
                        mime="application/pdf"
                    )

