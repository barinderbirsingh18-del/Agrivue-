from twilio.rest import Client
from translator import translate_text
from voice import generate_voice
import json
import os
import time

# ---------------- TWILIO CONFIG ----------------
TWILIO_SID = "AC5fc5c6ad85fb57f5318b0fd5c537d8ff"
TWILIO_TOKEN = "d8964469bce90324a2e5760a26af72ee"

TWILIO_WHATSAPP = "whatsapp:+14155238886"

# ⚠️ SINGLE FARMER (can be extended later)
YOUR_NUMBER = "whatsapp:+918872862277"

# 🔴 MUST MATCH RUNNING NGROK URL
NGROK_BASE_URL = "https://convectional-monte-alarmedly.ngrok-free.dev"

client = Client(TWILIO_SID, TWILIO_TOKEN)

DB_FILE = "farmers.json"

# ---------------- HELPERS ----------------
def normalize_whatsapp_number(number):
    if number.startswith("whatsapp:"):
        return number
    return f"whatsapp:{number}"

def get_farmer_language(phone):
    try:
        if not os.path.exists(DB_FILE):
            return "English"
        with open(DB_FILE, "r") as f:
            data = json.load(f)
        return data.get(phone, "English")
    except Exception:
        return "English"

# ---------------- ALERT ENGINE ----------------
def monitor_and_alert(node_name, data):
    """
    data: dict (already parsed JSON from app.py)
    Sends WhatsApp TEXT + VOICE alert
    """

    try:
        print("🔥 ALERT ENGINE HIT")
        print("Node:", node_name)
        print("Data:", data)

        alert_msg = None

        # 🌧️ RAIN ALERT
        if str(data.get("rain_prob", "")).lower() == "high":
            alert_msg = (
                f"🌧️ RAIN ALERT\n\n"
                f"Node: {node_name}\n"
                f"Condition: Heavy rain expected\n"
                f"Summary: {data.get('summary', 'N/A')}"
            )

        # 🌬️ WIND ALERT
        elif str(data.get("wind_speed", "")).lower() == "strong":
            alert_msg = (
                f"🌬️ HIGH WIND ALERT\n\n"
                f"Node: {node_name}\n"
                f"Condition: Strong winds detected\n"
                f"Summary: {data.get('summary', 'N/A')}"
            )

        # 🌱 SOIL ALERT
        elif float(data.get("moisture_pct", 100)) <= 25:
            alert_msg = (
                f"🚨 LOW SOIL MOISTURE ALERT\n\n"
                f"Node: {node_name}\n"
                f"Soil Moisture: {data.get('moisture_pct')}%\n"
                f"Health Index: {data.get('health_index', 'N/A')}"
            )

        if not alert_msg:
            print("ℹ️ No alert condition met")
            return False

        # ---------------- LANGUAGE ----------------
        to_number = normalize_whatsapp_number(YOUR_NUMBER)
        language = get_farmer_language(to_number)

        print("🌍 Language selected:", language)

        localized_msg = translate_text(alert_msg, language)

        # ================== SEND TEXT ==================
        print("📤 Sending WhatsApp TEXT")

        text_msg = client.messages.create(
            body=localized_msg,
            from_=TWILIO_WHATSAPP,
            to=to_number
        )

        print("✅ WhatsApp TEXT sent | SID:", text_msg.sid)

        # ================== SEND VOICE ==================
        try:
            print("🎧 Generating voice")
            voice_file = generate_voice(localized_msg, language)
            voice_url = f"{NGROK_BASE_URL}/audio/{voice_file}"

            time.sleep(1)  # WhatsApp stability

            print("🔊 Sending WhatsApp VOICE")

            voice_msg = client.messages.create(
                from_=TWILIO_WHATSAPP,
                to=to_number,
                media_url=[voice_url]
            )

            print("🔊 WhatsApp VOICE sent | SID:", voice_msg.sid)

        except Exception as ve:
            print("⚠️ Voice failed but TEXT already delivered:", ve)

        return True

    except Exception as e:
        print("❌ ALERT ENGINE ERROR:", e)
        return False
