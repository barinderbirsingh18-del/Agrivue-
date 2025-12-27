from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import json
import os
from flask import send_file
app = Flask(__name__)

DB_FILE = "farmers.json"
@app.route("/audio/<filename>")
def serve_audio(filename):
    return send_file(filename, mimetype="audio/mpeg")

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    incoming_msg = request.values.get("Body", "").strip()
    from_number = request.values.get("From")

    db = load_db()
    resp = MessagingResponse()
    msg = resp.message()

    # STEP 1: START MESSAGE
    if incoming_msg.upper() == "START":
        msg.body(
            "👋 Welcome to AgriVue 🌱\n\n"
            "Choose your language:\n"
            "1️⃣ English\n"
            "2️⃣ हिंदी\n"
            "3️⃣ ਪੰਜਾਬੀ\n"
            "4️⃣ मराठी\n\n"
            "Reply with 1, 2, 3 or 4"
        )
        return str(resp)

    # STEP 2: LANGUAGE SELECTION
    if incoming_msg in ["1", "2", "3", "4"]:
        language_map = {
            "1": "English",
            "2": "Hindi",
            "3": "Punjabi",
            "4": "Marathi"
        }

        selected_language = language_map[incoming_msg]
        db[from_number] = selected_language
        save_db(db)

        msg.body(
            f"✅ Language set to {selected_language}\n\n"
            "You will now receive all weather alerts in this language 🌾"
        )
        return str(resp)

    # DEFAULT FALLBACK
    msg.body(
        "❓ I didn’t understand.\n\n"
        "Send *START* to choose language."
    )
    return str(resp)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
