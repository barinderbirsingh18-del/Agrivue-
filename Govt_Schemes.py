import streamlit as st
from google import genai

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Voice AI Government Scheme Assistant",
    page_icon="🎙️",
    layout="wide"
)

API_KEY = "AIzaSyDmsCbY2SnY1OyUP73p7MsTWEXIFmOJvMQ"  # <-- put your key once
MODEL = "gemini-2.5-flash"

client = genai.Client(api_key=API_KEY)

# ---------------- SIDEBAR NAV ----------------
st.sidebar.title("🧭 AgriVue Navigation")
st.sidebar.page_link("app.py", label="🏠 Main Dashboard")
st.sidebar.page_link("pages/Govt_Schemes.py", label="🏛️ Govt Schemes AI")

# ---------------- GEMINI STATUS CHECK ----------------
def check_gemini():
    try:
        client.models.generate_content(
            model=MODEL,
            contents="Reply OK"
        )
        return True
    except Exception:
        return False

GEMINI_OK = check_gemini()

if GEMINI_OK:
    st.sidebar.success("🟢 Gemini AI Connected")
else:
    st.sidebar.error("🔴 Gemini AI Offline (Safe Mode)")

# ---------------- HEADER ----------------
st.title("🎙️ Voice AI Government Scheme Assistant")
st.caption(
    "Auto-detects farm situation • State-specific schemes • Speaks farmer’s language"
)

# ---------------- LANGUAGE & STATE ----------------
st.sidebar.divider()
st.sidebar.header("🌐 Language & State")

LANGUAGES = {
    "English": "English",
    "हिंदी": "Hindi",
    "ਪੰਜਾਬੀ": "Punjabi",
    "मराठी": "Marathi",
    "தமிழ்": "Tamil",
    "తెలుగు": "Telugu",
}

STATES = [
    "Punjab", "Haryana", "Uttar Pradesh",
    "Maharashtra", "Tamil Nadu", "Karnataka",
    "Rajasthan", "Bihar",
]

language_ui = st.sidebar.selectbox("Language", list(LANGUAGES.keys()))
farmer_language = LANGUAGES[language_ui]

state = st.sidebar.selectbox("State", STATES)

st.sidebar.success(f"🗣️ AI replies in {language_ui}")
st.sidebar.info(f"📍 Schemes tailored for {state}")

# ---------------- FARM CONTEXT ----------------
st.divider()
st.subheader("📡 Live Farm Situation (from AgriVue AI)")

damage_pct = st.slider("Crop Damage (%)", 0, 100, 55)
crop_stress = st.selectbox("Crop Stress", ["Low", "Medium", "High"])
soil_moisture = st.slider("Soil Moisture (%)", 0, 100, 22)

# ---------------- CATEGORY LOGIC ----------------
if damage_pct >= 50:
    category = "INSURANCE_AND_COMPENSATION"
elif damage_pct >= 30:
    category = "PARTIAL_RELIEF"
elif crop_stress == "High":
    category = "FARMER_SUPPORT"
elif soil_moisture < 30:
    category = "IRRIGATION_SUPPORT"
else:
    category = "NO_SCHEME_REQUIRED"

st.info(f"🧠 **Detected Category:** `{category}`")

# ---------------- SCHEME REGISTRY ----------------
GOVT_SCHEMES = {
    "INSURANCE_AND_COMPENSATION": [
        {
            "name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
            "benefit": "Crop insurance compensation for natural disasters",
            "eligibility": "Insured farmer with verified crop loss",
            "link": "https://pmfby.gov.in/",
        },
        {
            "name": "State Disaster Relief Fund (SDRF)",
            "benefit": "Compensation for flood, drought, hailstorm",
            "eligibility": "Damage notified by district authority",
            "link": "https://ndrf.gov.in/",
        },
    ],
    "PARTIAL_RELIEF": [
        {
            "name": "PMFBY (Assessment Based)",
            "benefit": "Partial insurance payout",
            "eligibility": "30–50% crop damage",
            "link": "https://pmfby.gov.in/",
        }
    ],
    "FARMER_SUPPORT": [
        {
            "name": "PM-KISAN",
            "benefit": "₹6000 yearly income support",
            "eligibility": "Small & marginal farmers",
            "link": "https://pmkisan.gov.in/",
        },
        {
            "name": "Soil Health Card Scheme",
            "benefit": "Free soil testing & advisory",
            "eligibility": "All farmers",
            "link": "https://soilhealth.dac.gov.in/",
        },
    ],
    "IRRIGATION_SUPPORT": [
        {
            "name": "PM Krishi Sinchai Yojana",
            "benefit": "Drip irrigation & water subsidy",
            "eligibility": "Farmers needing irrigation",
            "link": "https://pmksy.gov.in/",
        }
    ],
}

# ---------------- AUTO SCHEME DISPLAY ----------------
st.divider()
st.subheader("✅ Automatically Applicable Government Schemes")

schemes = GOVT_SCHEMES.get(category, [])

if not schemes:
    st.success("✅ No government scheme required at present.")
else:
    for s in schemes:
        st.markdown(
            f"""
### 🧾 {s['name']}
**Benefit:** {s['benefit']}  
**Eligibility:** {s['eligibility']}

👉 [Apply on Official Website]({s['link']})
""",
            unsafe_allow_html=True,
        )

# ---------------- CHATBOT ----------------
st.divider()
st.subheader("🎤 Talk to Government AI Officer")

st.caption(
    """
Ask naturally, for example:
• “Meri fasal barish se kharab ho gayi”
• “Insurance ka paisa kaise milega?”
• “Punjab mein kaun si scheme milegi?”
"""
)

if "chat" not in st.session_state:
    st.session_state.chat = []

user_msg = st.chat_input("🎤 Speak or type your problem…")


def ask_gemini_voice(question: str) -> str:
    q = question.lower().strip()

    # Greetings
    if any(w in q for w in ["hello", "hi", "namaste", "sat sri akal", "salaam"]):
        greetings = {
            "Hindi": "नमस्ते किसान भाई। मैं आपकी मदद के लिए यहाँ हूँ।",
            "Punjabi": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਜੀ। ਮੈਂ ਤੁਹਾਡੀ ਮਦਦ ਲਈ ਹਾਜ਼ਰ ਹਾਂ।",
            "Marathi": "नमस्कार शेतकरी मित्रा.",
            "Tamil": "வணக்கம். உங்கள் பிரச்சினையை சொல்லுங்கள்.",
            "Telugu": "నమస్తే రైతు సోదరా.",
        }
        return greetings.get(farmer_language, "Hello farmer. How can I help you?")

    if not GEMINI_OK:
        return "AI सेवा अभी उपलब्ध नहीं है। कृपया बाद में पूछें।"

    # ------- DO NOT EDIT ANYTHING INSIDE THIS PARENTHESES BLOCK -------
    prompt = (
        "You are a senior Indian government agriculture officer."
        f"Reply ONLY in {farmer_language}."
        "Simple words. Short sentences."
        f"State: {state}"
        f"Situation category: {category}"
        "Explain for the farmer:"
        "1. Applicable schemes"
        "2. Required documents"
        "3. How to apply (offline/online)"
        "4. Reassurance and next steps"
        f"Farmer says:{question}"
    )
    # ------------------------------------------------------------------

    try:
        resp = client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )
        return resp.text
    except Exception:
        return "AI व्यस्त है। कृपया थोड़ी देर बाद पूछें।"


if user_msg:
    st.session_state.chat.append(("user", user_msg))
    st.session_state.chat.append(("ai", ask_gemini_voice(user_msg)))

for role, msg in st.session_state.chat:
    with st.chat_message("user" if role == "user" else "assistant"):
        st.write(msg)

# ---------------- QUICK APPLY ACTIONS ----------------
if schemes:
    st.divider()
    st.subheader("🚀 Quick Government Actions")
    for s in schemes:
        st.link_button(f"Apply: {s['name']}", s["link"])

# ---------------- FOOTER ----------------
st.divider()
st.success("🚜 This AI behaves like a REAL government officer — not a chatbot.")