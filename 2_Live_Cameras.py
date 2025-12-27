import streamlit as st
import cv2
import time
import numpy as np
from datetime import datetime
from google import genai
from google.genai import types
from PIL import Image, ImageDraw
import io
import json
import streamlit.components.v1 as components

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="AgriVue Live Cameras",
    page_icon="📡",
    layout="wide"
)

API_KEY = "AIzaSyDmsCbY2SnY1OyUP73p7MsTWEXIFmOJvMQ"  # <-- put your key
MODEL = "gemini-2.5-flash"

client = genai.Client(api_key=API_KEY)

# ---------------- CAMERA STREAMS ----------------
CAMERAS = {
    "🌧 Sky Node (Rain)": "http://10.52.1.215:8080/video",
    "🌬 Wind Node (Movement)": "http://10.52.1.204:8080/video",
    "🌱 Soil Node": "http://10.52.3.75:8080/video",
    "🍃 Leaf Node (Stress)": "http://10.52.3.55:8080/video",
}

# ---------------- SIDEBAR ----------------
st.sidebar.header("⚙ Live Controls")

FPS = st.sidebar.slider("Refresh FPS", 1, 10, 3)
SNAPSHOT_INTERVAL_MIN = st.sidebar.slider("Snapshot interval (minutes)", 1, 30, 5)
MOTION_THRESHOLD = st.sidebar.slider("Motion sensitivity", 1000, 10000, 3500)

st.sidebar.info("📡 Live Feed • 🌬 Motion • 🧠 Gemini AI")

# ---------------- UI ----------------
st.title("📡 AgriVue Live Farm Intelligence")
st.caption("Live Camera • Motion Detection • Snapshot AI")

cols = st.columns(2)
cols += st.columns(2)

video_boxes = {}
motion_boxes = {}
ai_status_boxes = {}
ai_result_boxes = {}

for i, name in enumerate(CAMERAS.keys()):
    with cols[i]:
        st.subheader(name)
        video_boxes[name] = st.empty()
        motion_boxes[name] = st.empty()
        ai_status_boxes[name] = st.empty()
        ai_result_boxes[name] = st.empty()

# ---------------- HELPERS ----------------
def add_watermark(frame, text="AgriVue"):
    """Add date & time on bottom-left of frame."""
    pil_img = Image.fromarray(frame)
    draw = ImageDraw.Draw(pil_img)
    w, h = pil_img.size
    dt_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    label = f"{text} • {dt_text}"
    draw.text((10, h - 30), label, fill=(255, 255, 255))
    return np.array(pil_img)

def no_signal_frame():
    img = np.zeros((360, 640, 3), dtype=np.uint8)
    cv2.putText(img, "NO SIGNAL", (180, 180),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
    cv2.putText(img, "AgriVue Camera Offline", (140, 230),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return img

def analyze_with_gemini(image_bytes, node):
    """Call Gemini and return parsed JSON dict."""
    prompt = (
        "You are an agricultural AI assistant. "
        f"Analyze this image from node: {node}. "
        "Return ONLY valid JSON with these keys: "
        '{"rain_likelihood":"Low|Medium|High",'
        '"wind_level":"Calm|Moderate|Strong",'
        '"crop_stress":"Low|Medium|High",'
        '"summary":"short farmer-friendly sentence"}'
    )

    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type="image/jpeg",
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=[prompt, image_part],
    )

    text = (response.text or "").strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end <= start:
        return {"error": "Bad JSON from Gemini", "summary": text[:80]}

    try:
        return json.loads(text[start:end])
    except Exception:
        return {"error": "JSON parse failed", "summary": text[:80]}

# ---------------- STATE ----------------
last_snapshot = {k: 0.0 for k in CAMERAS}
prev_gray = {}

# ---------------- LIVE STREAM HTML ----------------
def render_live_feed(title, url):
    """Realtime MJPEG stream with date/time overlay in HTML."""
    dt_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_code = f"""
    <div style="position:relative; border:2px solid #2ecc71; border-radius:10px; overflow:hidden;">
        <img src="{url}" width="100%" style="border-radius:10px;" />
        <div style="
            position:absolute;
            bottom:8px;
            right:12px;
            color:rgba(255,255,255,0.8);
            font-size:12px;
            font-weight:bold;
            text-shadow: 0 0 4px rgba(0,0,0,0.8);
        ">
            AgriVue © • {dt_text}
        </div>
    </div>
    """
    components.html(html_code, height=320)

# ---------------- MAIN LOOP ----------------
snapshot_interval_sec = SNAPSHOT_INTERVAL_MIN * 60

while True:
    for node, url in CAMERAS.items():
        # ---- LIVE MJPEG DISPLAY ----
        with video_boxes[node]:
            render_live_feed(node, url)

        # ---- SNAPSHOT AI + MOTION ----
        cap = cv2.VideoCapture(url)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            frame = no_signal_frame()
            motion_boxes[node].metric("🌬 Wind / Motion Score", "N/A")
            ai_status_boxes[node].warning("Camera offline – no AI analysis")
            continue

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = add_watermark(frame, text=node)

        # ---- MOTION DETECTION ----
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        motion = 0
        if node in prev_gray:
            delta = cv2.absdiff(prev_gray[node], gray)
            thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
            motion = int(np.sum(thresh))

        prev_gray[node] = gray
        wind_score = min(100, motion // 500)
        motion_boxes[node].metric("🌬 Wind / Motion Score", wind_score)

        # ---- SNAPSHOT + AI ----
        now = time.time()
        need_snapshot = (
            now - last_snapshot[node] > snapshot_interval_sec
            or motion > MOTION_THRESHOLD
        )

        seconds_left = max(0, int(snapshot_interval_sec - (now - last_snapshot[node])))
        mins_left = seconds_left // 60
        secs_left = seconds_left % 60

        if need_snapshot:
            last_snapshot[node] = now

            img_pil = Image.fromarray(frame)
            buf = io.BytesIO()
            img_pil.save(buf, format="JPEG")
            image_bytes = buf.getvalue()

            ai_status_boxes[node].info(
                f"🧠 AI analysing snapshot… taken at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            try:
                result = analyze_with_gemini(image_bytes, node)
                ai_result_boxes[node].json(result)
            except Exception as e:
                ai_result_boxes[node].error(f"Gemini analysis failed: {e}")
        else:
            ai_status_boxes[node].write(
                f"Next AI snapshot in ~{mins_left} min {secs_left} sec "
                f"or sooner if motion exceeds threshold."
            )

    time.sleep(1 / FPS)