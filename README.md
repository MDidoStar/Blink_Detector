# Blink_Detector
# 👁️ Eye Health Suite

A comprehensive Streamlit application for eye health monitoring and analysis, combining AI-powered blink pattern analysis with real-time blink rate monitoring.

## Features

### 📸 Blink Analysis
- Capture 120 frames from your webcam
- AI-powered analysis using Google Gemini
- Generate detailed PDF reports
- Get personalized recommendations based on location and age

### ⏱️ Blink Monitor
- Real-time blink rate tracking
- 5-minute monitoring sessions
- Visual and on-screen reminders to blink
- Prevent digital eye strain

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Webcam access
- Google Gemini API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd eye-health-suite
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create required files**
   
   Create a `countries.csv` file in the root directory with the following structure:
   ```csv
   Country,City,Currency_Code,Number
   USA,New York,USD,25
   USA,Los Angeles,USD,30
   UK,London,GBP,35
   Canada,Toronto,CAD,28
   ```
   
   Add a `blink_logo.png` file for the logo (optional)

4. **Configure Secrets**
   
   Create a `.streamlit/secrets.toml` file:
   ```toml
   GEMINI_API_KEY = "your-gemini-api-key-here"
   ```
   
   Or set environment variable:
   ```bash
   export GEMINI_API_KEY="your-gemini-api-key-here"
   ```

### Running the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## Project Structure

```
eye-health-suite/
├── app.py                      # Main landing page
├── pages/
│   ├── 1_Blink_Analysis.py    # AI-powered analysis page
│   └── 2_Blink_Monitor.py     # Real-time monitoring page
├── requirements.txt            # Python dependencies
├── countries.csv              # Location and age data
├── blink_logo.png            # Application logo (optional)
└── README.md                  # This file
```

## Usage

### Blink Analysis
1. Click "Go to Blink Analysis" on the home page
2. Start your camera and capture 120 frames
3. Enter your country, city, and age
4. Click "Analyze Frames with AI"
5. Review the AI-generated insights
6. Download your PDF report

### Blink Monitor
1. Click "Go to Blink Monitor" on the home page
2. Click "Start Camera"
3. Look at the camera naturally
4. Monitor your blink rate for 5 minutes
5. Follow on-screen reminders if you blink too little

## Deployment to Streamlit Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Set `app.py` as the main file
5. Add your `GEMINI_API_KEY` in the Secrets section
6. Deploy!

## Health & Safety Notes

- This app is for educational and wellness purposes only
- It does not provide medical diagnosis
- Consult an eye care professional for health concerns
- Take regular breaks from screens (20-20-20 rule)

## Technologies Used

- **Streamlit** - Web framework
- **Google Gemini AI** - Image analysis
- **MediaPipe** - Real-time face detection
- **OpenCV** - Computer vision
- **ReportLab** - PDF generation
- **Pandas** - Data management

## License

MIT License - feel free to use and modify for your projects

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues or questions, please open an issue on GitHub.
