import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Blink Monitor - Smart Tracking", layout="centered")

if st.button("← Back to Home"):
    st.switch_page("sci_fair.py")

st.title("👁️ Blink Monitor (HTML5 Version)")
st.markdown("### Monitor your blink rate to reduce eye strain")
st.info("🎥 This version uses HTML5 camera API for better compatibility")

html_code = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js" crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js" crossorigin="anonymous"></script>

  <style>
    body { font-family: Arial, sans-serif; text-align:center; margin:0; padding:20px; background:#f5f5f5; }
    #videoContainer { position:relative; display:inline-block; margin:20px auto; }
    #video { border:3px solid #3498db; border-radius:10px; box-shadow:0 4px 6px rgba(0,0,0,.1); }
    #canvas { position:absolute; top:0; left:0; }

    .metrics { display:flex; justify-content:center; gap:30px; margin:20px 0; flex-wrap:wrap; }
    .metric { background:white; padding:15px 30px; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,.1); }
    .metric-value { font-size:32px; font-weight:bold; color:#3498db; }
    .metric-label { font-size:14px; color:#666; margin-top:5px; }

    button { padding:12px 30px; font-size:16px; border:none; border-radius:5px; cursor:pointer; margin:10px; transition:all .3s; }
    #startBtn { background:#3498db; color:white; }
    #startBtn:hover { background:#2980b9; }
    #resetBtn { background:#e74c3c; color:white; }
    #resetBtn:hover { background:#c0392b; }

    #status { margin:20px 0; padding:10px; border-radius:5px; font-size:16px; }
    .status-ready { background:#d4edda; color:#155724; }
    .status-error { background:#f8d7da; color:#721c24; }
    .status-warning { background:#fff3cd; color:#856404; }

    #eyeStatus {
      position:absolute; top:10px; right:10px; padding:8px 12px; border-radius:5px;
      font-weight:bold; font-size:14px;
    }
    .eyes-open { background:#27ae60; color:white; }
    .eyes-closed { background:#e74c3c; color:white; }

    #debugBox{
      position:absolute; left:10px; top:10px; background:rgba(0,0,0,0.55);
      color:white; padding:8px 10px; border-radius:6px; font-size:12px; text-align:left;
      min-width:170px;
    }

    #blinkReminder { position:absolute; top:50px; right:60px; display:none; text-align:center; }
    .reminder-text { color:white; font-size:14px; font-weight:bold; margin-top:5px; text-shadow:2px 2px 4px rgba(0,0,0,.5); }
  </style>
</head>

<body>
  <div class="metrics">
    <div class="metric">
      <div class="metric-value" id="blinkCount">0</div>
      <div class="metric-label">Blinks This Minute</div>
    </div>
    <div class="metric">
      <div class="metric-value" id="timeRemaining">5:00</div>
      <div class="metric-label">Time Remaining</div>
    </div>
    <div class="metric">
      <div class="metric-value">15-20</div>
      <div class="metric-label">Target Blinks/Min</div>
    </div>
  </div>

  <button id="startBtn">Start Camera</button>
  <button id="resetBtn">Reset Session</button>

  <div id="status" class="status-warning">Click "Start Camera" to begin monitoring</div>

  <div id="videoContainer">
    <video id="video" width="640" height="480" autoplay muted playsinline></video>
    <canvas id="canvas" width="640" height="480"></canvas>

    <div id="debugBox">
      EAR: <span id="earVal">-</span><br/>
      Base: <span id="baseVal">-</span><br/>
      Thr: <span id="thrVal">-</span><br/>
      Face: <span id="faceVal">No</span>
    </div>

    <div id="eyeStatus" class="eyes-open">Eyes: OPEN</div>

    <div id="blinkReminder">
      <svg width="44" height="44" viewBox="0 0 44 44">
        <ellipse cx="22" cy="22" rx="22" ry="11" fill="none" stroke="white" stroke-width="2"/>
        <circle id="pupil" cx="22" cy="22" r="3" fill="white"/>
      </svg>
      <div class="reminder-text">Blink</div>
    </div>
  </div>

  <script type="module">
    const FaceMesh = window.FaceMesh;

    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');

    const startBtn = document.getElementById('startBtn');
    const resetBtn = document.getElementById('resetBtn');
    const statusDiv = document.getElementById('status');

    const blinkCountDiv = document.getElementById('blinkCount');
    const timeRemainingDiv = document.getElementById('timeRemaining');
    const eyeStatusDiv = document.getElementById('eyeStatus');

    const blinkReminder = document.getElementById('blinkReminder');
    const pupil = document.getElementById('pupil');

    const earVal = document.getElementById('earVal');
    const baseVal = document.getElementById('baseVal');
    const thrVal = document.getElementById('thrVal');
    const faceVal = document.getElementById('faceVal');

    let blinkCount = 0;
    let minuteStart = Date.now();
    let sessionStart = Date.now();

    let faceMesh = null;

    // Reminder state
    let showReminder = false;
    let reminderStart = 0;
    const REMINDER_DURATION = 10000;

    // Session params
    const TOTAL_TIME = 5 * 60 * 1000;
    const NORMAL_MAX = 20;

    // Blink detection params (EAR based)
    const R = { p1:33, p2:160, p3:158, p4:133, p5:153, p6:144 };
    const L = { p1:362, p2:385, p3:387, p4:263, p5:373, p6:380 };

    let emaBaseEAR = null;
    const EMA_ALPHA = 0.08;
    const THRESH_RATIO = 0.72;
    const MIN_CLOSED_FRAMES = 2;
    let closedFrames = 0;
    let inBlink = false;

    // ------------------ Beep (winsound-like) SAFE ------------------
    // This is intentionally wrapped so audio failures NEVER break blink detection.
    // Browsers may block audio in iframes unless it follows a user gesture.
    let audioCtx = null;

    function ensureAudioSafe(){
      try{
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        if (audioCtx.state === "suspended") audioCtx.resume();
        return true;
      } catch(e){
        console.warn("Audio disabled:", e);
        return false;
      }
    }

    // Similar to winsound.Beep(800, 1000)
    function beepSafe(freq = 800, durationMs = 1000, volume = 0.06){
      try{
        if (!audioCtx) return; // if audio isn't available, do nothing

        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();

        osc.type = "sine";
        osc.frequency.value = freq;

        // exponential ramp requires strictly positive values
        const v = Math.max(0.0001, volume);
        gain.gain.value = v;

        osc.connect(gain);
        gain.connect(audioCtx.destination);

        const t0 = audioCtx.currentTime;
        osc.start(t0);

        // gentle fade to avoid click
        gain.gain.setValueAtTime(v, t0);
        gain.gain.exponentialRampToValueAtTime(0.0001, t0 + durationMs/1000);

        osc.stop(t0 + durationMs/1000);
      } catch(e){
        console.warn("Beep failed (ignored):", e);
      }
    }
    // ---------------------------------------------------------------

    function dist(a, b){
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      return Math.sqrt(dx*dx + dy*dy);
    }

    function eyeEAR(lm, eye){
      const p1 = lm[eye.p1], p2 = lm[eye.p2], p3 = lm[eye.p3],
            p4 = lm[eye.p4], p5 = lm[eye.p5], p6 = lm[eye.p6];

      const vert1 = dist(p2, p6);
      const vert2 = dist(p3, p5);
      const horiz = dist(p1, p4);

      if (horiz <= 1e-6) return null;
      return (vert1 + vert2) / (2.0 * horiz);
    }

    async function startCamera() {
      try {
        // Unlock audio on user gesture (but never fail if blocked)
        ensureAudioSafe();

        statusDiv.textContent = 'Initializing camera...';
        statusDiv.className = 'status-warning';

        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width:{ideal:640}, height:{ideal:480}, frameRate:{ideal:30} }
        });
        video.srcObject = stream;

        faceMesh = new FaceMesh({
          locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`
        });

        faceMesh.setOptions({
          maxNumFaces: 1,
          refineLandmarks: true,
          minDetectionConfidence: 0.5,
          minTrackingConfidence: 0.5
        });

        faceMesh.onResults(onResults);

        await video.play();
        processFrame();

        statusDiv.textContent = '✅ Camera active! Blink naturally and look at the camera.';
        statusDiv.className = 'status-ready';

        startBtn.disabled = true;
        startBtn.style.opacity = '0.5';

        updateTimer();
        animateReminder();

      } catch (err) {
        console.error('Camera error:', err);
        statusDiv.textContent = '❌ Camera failed. Allow camera permissions and refresh. (Some browsers block camera in iframes.)';
        statusDiv.className = 'status-error';
      }
    }

    async function processFrame(){
      if (faceMesh && video.readyState === 4){
        await faceMesh.send({ image: video });
      }
      requestAnimationFrame(processFrame);
    }

    function onResults(results){
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const hasFace = results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0;
      faceVal.textContent = hasFace ? "Yes" : "No";

      if (!hasFace) {
        eyeStatusDiv.textContent = 'Eyes: OPEN';
        eyeStatusDiv.className = 'eyes-open';
        return;
      }

      const lm = results.multiFaceLandmarks[0];

      const earR = eyeEAR(lm, R);
      const earL = eyeEAR(lm, L);
      if (earR == null || earL == null) return;

      const ear = (earR + earL) / 2.0;

      // Update baseline only when likely open to avoid dragging down during blinks
      if (emaBaseEAR === null) {
        emaBaseEAR = ear;
      } else {
        const floor = emaBaseEAR * 0.6; // loose open condition
        if (ear > floor) {
          emaBaseEAR = (1 - EMA_ALPHA) * emaBaseEAR + EMA_ALPHA * ear;
        }
      }

      const threshold = emaBaseEAR * THRESH_RATIO;

      earVal.textContent = ear.toFixed(4);
      baseVal.textContent = emaBaseEAR.toFixed(4);
      thrVal.textContent = threshold.toFixed(4);

      // Blink state machine
      if (ear < threshold) {
        closedFrames++;
        eyeStatusDiv.textContent = 'Eyes: CLOSED';
        eyeStatusDiv.className = 'eyes-closed';

        if (!inBlink && closedFrames >= MIN_CLOSED_FRAMES) {
          inBlink = true;
        }

      } else {
        eyeStatusDiv.textContent = 'Eyes: OPEN';
        eyeStatusDiv.className = 'eyes-open';

        if (inBlink) {
          blinkCount++;
          blinkCountDiv.textContent = blinkCount;
        }
        inBlink = false;
        closedFrames = 0;
      }

      // Optional debug points
      ctx.fillStyle = "rgba(52,152,219,0.9)";
      const pA = lm[33], pB = lm[133];
      ctx.beginPath(); ctx.arc(pA.x*canvas.width, pA.y*canvas.height, 3, 0, Math.PI*2); ctx.fill();
      ctx.beginPath(); ctx.arc(pB.x*canvas.width, pB.y*canvas.height, 3, 0, Math.PI*2); ctx.fill();
    }

    function updateTimer(){
      const now = Date.now();

      // Minute check
      if (now - minuteStart >= 60000) {
        if (blinkCount < NORMAL_MAX) {
          showReminder = true;
          reminderStart = now;
          blinkReminder.style.display = 'block';

          // winsound.Beep equivalent (SAFE)
          beepSafe(800, 1000, 0.06);
        }

        blinkCount = 0;
        blinkCountDiv.textContent = blinkCount;
        minuteStart = now;
      }

      // Reminder hide
      if (showReminder && (now - reminderStart >= REMINDER_DURATION)) {
        showReminder = false;
        blinkReminder.style.display = 'none';
      }

      // Session timer
      const elapsed = now - sessionStart;
      const remaining = Math.max(0, TOTAL_TIME - elapsed);
      const minutes = Math.floor(remaining / 60000);
      const seconds = Math.floor((remaining % 60000) / 1000);
      timeRemainingDiv.textContent = `${minutes}:${seconds.toString().padStart(2,'0')}`;

      if (remaining > 0) {
        setTimeout(updateTimer, 1000);
      } else {
        statusDiv.textContent = '⏰ Session complete! Great job monitoring your blinks!';
        statusDiv.className = 'status-ready';
      }
    }

    function animateReminder(){
      if (showReminder) {
        const phase = Math.floor(Date.now()/500) % 2;
        pupil.style.opacity = phase === 0 ? '1' : '0';
      }
      requestAnimationFrame(animateReminder);
    }

    function resetSession(){
      blinkCount = 0;
      minuteStart = Date.now();
      sessionStart = Date.now();

      emaBaseEAR = null;
      closedFrames = 0;
      inBlink = false;

      showReminder = false;
      reminderStart = 0;
      blinkReminder.style.display = 'none';

      blinkCountDiv.textContent = blinkCount;
      eyeStatusDiv.textContent = 'Eyes: OPEN';
      eyeStatusDiv.className = 'eyes-open';

      statusDiv.textContent = 'Session reset! Camera still active.';
      statusDiv.className = 'status-ready';

      updateTimer();
    }

    startBtn.addEventListener('click', startCamera);
    resetBtn.addEventListener('click', resetSession);
  </script>
</body>
</html>
"""

components.html(html_code, height=900)

st.markdown("---")

st.markdown("""
### 📋 Instructions:
1. Click "Start Camera" to begin
2. Allow camera permissions when prompted
3. Position your face in the frame
4. Blink naturally - the system will track automatically
5. Session runs for 5 minutes
6. If blinks < 20 in a minute, you’ll see the reminder **and hear a beep** (if browser allows audio)
""")
