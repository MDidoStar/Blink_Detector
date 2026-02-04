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
# Main App
# ----------------------------
# Create centered layout
col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    st.title("Check your Eye Health & Safety")
    
    st.subheader("Step 1: Capture Eye Photos")
    
    # Initialize session state
    if 'captured_frames' not in st.session_state:
        st.session_state.captured_frames = []
    
    if 'photo_count' not in st.session_state:
        st.session_state.photo_count = 0
    
    # Instructions
    st.info("📸 Take multiple photos of your eye blinking. Try to capture different blink stages. Aim for at least 5-10 photos for better analysis.")
    
    # Camera input
    camera_photo = st.camera_input("Take a photo of your eye")
    
    # Process captured photo
    if camera_photo is not None:
        # Convert to bytes
        photo_bytes = camera_photo.read()
        
        # Add to session state if it's a new photo
        if len(st.session_state.captured_frames) == 0 or photo_bytes != st.session_state.captured_frames[-1]:
            st.session_state.captured_frames.append(photo_bytes)
            st.session_state.photo_count += 1
            st.success(f"✅ Photo {st.session_state.photo_count} captured!")
    
    # Display captured photos count
    if st.session_state.photo_count > 0:
        st.write(f"**Total photos captured: {st.session_state.photo_count}**")
        
        # Show thumbnails of captured photos
        if st.session_state.captured_frames:
            st.write("Captured photos:")
            cols = st.columns(min(5, len(st.session_state.captured_frames)))
            for idx, frame in enumerate(st.session_state.captured_frames[:5]):
                with cols[idx]:
                    st.image(frame, caption=f"Photo {idx+1}", use_column_width=True)
            
            if len(st.session_state.captured_frames) > 5:
                st.write(f"...and {len(st.session_state.captured_frames) - 5} more photos")
        
        # Reset button
        if st.button("🔄 Clear All Photos and Start Over"):
            st.session_state.captured_frames = []
            st.session_state.photo_count = 0
            st.rerun()
    
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
    
    if st.button("Step 4: 📊 Analyze Photos with AI", key="analyze_btn", type="primary"):
        if not st.session_state.captured_frames or len(st.session_state.captured_frames) == 0:
            st.error("⚠️ Please capture at least one photo first using the camera above!")
        else:
            frames = st.session_state.captured_frames
            
            # Display first photo
            try:
                st.image(frames[0], caption=f"Analyzing {len(frames)} photo(s)...", use_column_width=True)
            except Exception as e:
                st.warning(f"Could not display preview image: {e}")
    
            prompt = f"""
You are given {len(frames)} eye image(s) from a camera.

Task: Check for possible blinking problems or abnormal blinking patterns based on the provided images.
- You cannot diagnose.
- Give careful observations and safe advice only.
- Keep it short and focused.
- List urgent red flags that require an eye doctor.

Patient context:
- Country: {patient_country}
- City: {patient_city}
- Age: {age_num}

Please provide:
1. General observations about the eye appearance
2. Any visible concerns (redness, swelling, asymmetry, etc.)
3. Blinking pattern observations (if multiple images show different blink stages)
4. Safe recommendations
5. Red flags that need immediate medical attention
"""
    
            # Prepare content for Gemini
            contents = [prompt]
            for frame_bytes in frames:
                contents.append({"mime_type": "image/jpeg", "data": frame_bytes})
    
            with st.spinner(f"Analyzing {len(frames)} photo(s) with Gemini AI..."):
                try:
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
                            label="📄 Download PDF Report",
                            data=pdf_content,
                            file_name="eye_health_recommendations.pdf",
                            mime="application/pdf"
                        )
                except Exception as e:
                    st.error(f"Error during AI analysis: {e}")
                    st.error("This might be due to API limits or connectivity issues. Please try again.")

# Footer
st.write("---")
st.caption("⚠️ **Disclaimer**: This tool is for informational purposes only and does not replace professional medical advice. Always consult with an eye care professional for proper diagnosis and treatment.")
