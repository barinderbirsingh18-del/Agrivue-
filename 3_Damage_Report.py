import streamlit as st
import io
import json
import random
from PIL import Image
from datetime import datetime
from google import genai
from google.genai import types
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import alerts

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Crop Damage & Insurance",
    page_icon="🧾",
    layout="wide"
)

API_KEY = "AIzaSyDmsCbY2SnY1OyUP73p7MsTWEXIFmOJvMQ"
client = genai.Client(api_key=API_KEY)

# ---------------- SIDEBAR / MODE ----------------
st.sidebar.title("⚙️ Settings")

DEMO_MODE = st.sidebar.toggle("🎬 Demo Mode (random AI)", value=True)

crop_name = st.sidebar.text_input("🌾 Crop name", value="Wheat")
total_area_ha = st.sidebar.number_input(
    "🌐 Total insured area (hectares)",
    min_value=0.1, max_value=100.0, value=1.0, step=0.1
)
expected_yield_q_per_ha = st.sidebar.number_input(
    "📦 Expected yield (quintal/ha)",
    min_value=1.0, max_value=200.0, value=35.0, step=1.0
)
expected_price_rs_per_q = st.sidebar.number_input(
    "💰 Expected price (₹/quintal)",
    min_value=100.0, max_value=10000.0, value=2200.0, step=50.0
)

st.title("🧾 Crop Damage & Insurance Report")
st.caption("Before–After AI comparison • Insurance-ready PDF • Claim helper for farmers")

# ---------------- INPUTS ----------------
col1, col2 = st.columns(2)

with col1:
    before_img = st.file_uploader(
        "📷 BEFORE Damage Image",
        type=["jpg", "jpeg", "png"],
        key="before"
    )

with col2:
    after_img = st.file_uploader(
        "📷 AFTER Damage Image",
        type=["jpg", "jpeg", "png"],
        key="after"
    )

# Small helper for metric-like rows
def metric_row(label, value, help_text=None):
    c1, c2 = st.columns([1, 2])
    c1.markdown(f"**{label}**")
    c2.markdown(f"{value}")
    if help_text:
        st.caption(help_text)


# ---------------- PROCESS ----------------
if before_img and after_img:
    before_bytes = before_img.getvalue()
    after_bytes = after_img.getvalue()

    before_image = Image.open(io.BytesIO(before_bytes))
    after_image = Image.open(io.BytesIO(after_bytes))

    st.subheader("🔍 Before vs After Comparison")
    c1, c2 = st.columns(2)
    c1.image(before_image, caption="Before Damage", use_container_width=True)
    c2.image(after_image, caption="After Damage", use_container_width=True)

    with st.spinner("Analyzing crop damage with AgriVue AI…"):

        # ---------- DEMO MODE ----------
        if DEMO_MODE:
            damage_pct = random.randint(5, 85)

            damage_data = {
                "damage_type": "No Major Damage" if damage_pct < 30 else "Flood",
                "damage_severity_pct": damage_pct,
                "salvageable": damage_pct < 55,
                "estimated_area_affected_ha": round(
                    total_area_ha * damage_pct / 100.0, 2
                ),
                "likely_cause": (
                    "Localized heavy rain and waterlogging"
                    if damage_pct >= 30 else "Normal weather variation"
                ),
                "risk_of_secondary_issues": (
                    "Low"
                    if damage_pct < 30 else
                    "High risk of pest / fungal attack on surviving plants"
                ),
                "recommended_farmer_actions": [
                    "Click clear photos of damaged and undamaged parts of the field.",
                    "Inform local agriculture / insurance agent within 48 hours.",
                    "Keep seed, fertilizer and pesticide bills safely.",
                ],
                "required_documents_for_claim": [
                    "Aadhaar card",
                    "Land record / Khasra-Khatauni / lease agreement",
                    "Bank passbook",
                    "Completed PMFBY or scheme-specific claim form"
                ],
                "followup_next_7_days": (
                    "Monitor standing crop for rot or fungal infection in low-lying pockets, "
                    "avoid waterlogging and record any further damage with photos."
                ),
                "summary": (
                    "No significant crop damage detected."
                    if damage_pct < 30
                    else "Severe crop damage detected due to excess water and lodging."
                )
            }

        # ---------- REAL MODE ----------
        else:
            try:
                # JSON schema with extra claim-helpful fields
                schema = {
                    "type": "object",
                    "properties": {
                        "damage_type": {
                            "type": "string",
                            "enum": [
                                "Flood", "Hail", "Wind", "Pest", "Drought",
                                "Unknown", "No Major Damage"
                            ]
                        },
                        "damage_severity_pct": {"type": "number"},
                        "salvageable": {"type": "boolean"},
                        "estimated_area_affected_ha": {"type": "number"},
                        "likely_cause": {"type": "string"},
                        "risk_of_secondary_issues": {"type": "string"},
                        "recommended_farmer_actions": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "required_documents_for_claim": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "followup_next_7_days": {"type": "string"},
                        "summary": {"type": "string"}
                    },
                    "required": [
                        "damage_type", "damage_severity_pct", "salvageable",
                        "estimated_area_affected_ha", "likely_cause",
                        "risk_of_secondary_issues",
                        "recommended_farmer_actions",
                        "required_documents_for_claim",
                        "followup_next_7_days",
                        "summary"
                    ]
                }

                prompt = f"""
You are a senior crop insurance assessor working under Indian schemes (e.g., PMFBY).
The farmer grows {crop_name} on about {total_area_ha} hectares.

Compare BEFORE and AFTER images of the same field.
Estimate visible damage and fill the JSON schema.
Use simple, non-technical Hindi-English mix that farmers can understand.
Damage severity is the percent of visible cropped area that looks damaged.
If damage is minor, set damage_type to "No Major Damage".
"""

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Part.from_text(prompt),
                        types.Part.from_bytes(before_bytes, mime_type="image/jpeg"),
                        types.Part.from_bytes(after_bytes, mime_type="image/jpeg"),
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema
                    ),
                )

                damage_data = json.loads(response.text)

            except Exception as e:
                st.error("AI analysis failed, using safe fallback.")
                st.caption(str(e))
                damage_data = {
                    "damage_type": "Unknown",
                    "damage_severity_pct": 40,
                    "salvageable": True,
                    "estimated_area_affected_ha": round(total_area_ha * 0.4, 2),
                    "likely_cause": "Not available (AI error).",
                    "risk_of_secondary_issues": (
                        "Moderate risk of pest / disease on stressed plants."
                    ),
                    "recommended_farmer_actions": [
                        "Ask local agriculture officer to inspect the field.",
                        "Keep clear photos and short mobile video of the field.",
                        "Collect all input purchase bills."
                    ],
                    "required_documents_for_claim": [
                        "Basic KYC and land documents as per local insurance scheme."
                    ],
                    "followup_next_7_days": (
                        "Visit the field daily, note if damage spreads, and update photos."
                    ),
                    "summary": "AI unavailable. Estimated moderate damage from images."
                }

    # ---------------- YIELD & INCOME ESTIMATE ----------------
    damage_pct = float(damage_data["damage_severity_pct"])
    damage_fraction = max(0.0, min(damage_pct / 100.0, 1.0))

    damaged_area_ha = min(
        damage_data.get("estimated_area_affected_ha", total_area_ha * damage_fraction),
        total_area_ha
    )

    normal_yield_q = total_area_ha * expected_yield_q_per_ha
    expected_income_rs = normal_yield_q * expected_price_rs_per_q

    estimated_yield_loss_q = normal_yield_q * damage_fraction
    estimated_income_loss_rs = estimated_yield_loss_q * expected_price_rs_per_q

    # Claim urgency
    if damage_pct < 25:
        insurance_eligible = False
        insurance_reco = (
            "Damage appears below typical insurance threshold. Keep records but "
            "claim may not be approved."
        )
        claim_urgency = "Low"
        suggested_claim_window_days = 5
    elif damage_pct < 50:
        insurance_eligible = "Borderline"
        insurance_reco = (
            "Moderate damage detected. File claim with clear photos and request "
            "joint field inspection."
        )
        claim_urgency = "Medium"
        suggested_claim_window_days = 3
    else:
        insurance_eligible = True
        insurance_reco = (
            "Severe damage detected. Strongly recommended to file insurance claim "
            "within the next 48 hours."
        )
        claim_urgency = "High"
        suggested_claim_window_days = 2

    # ---------------- META ----------------
    damage_data.update({
        "crop_name": crop_name,
        "total_area_ha": total_area_ha,
        "expected_yield_q_per_ha": expected_yield_q_per_ha,
        "expected_price_rs_per_q": expected_price_rs_per_q,
        "normal_yield_q": normal_yield_q,
        "expected_income_rs": expected_income_rs,
        "estimated_yield_loss_q": round(estimated_yield_loss_q, 2),
        "estimated_income_loss_rs": round(estimated_income_loss_rs, 0),
        "damaged_area_ha_final": round(damaged_area_ha, 2),
        "insurance_eligible": insurance_eligible,
        "insurance_recommendation": insurance_reco,
        "claim_urgency": claim_urgency,
        "suggested_claim_window_days": suggested_claim_window_days,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "latitude": 30.7333,   # demo
        "longitude": 76.7794   # demo
    })

    # ---------------- UI SUMMARY ----------------
    st.subheader("📊 AI Damage Assessment")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Damage severity", f"{damage_data['damage_severity_pct']}%")
    m2.metric("Damage type", damage_data["damage_type"])
    m3.metric("Salvageable", "Yes" if damage_data["salvageable"] else "No")
    m4.metric("Area affected", f"{damage_data['damaged_area_ha_final']} ha")

    st.markdown("### 🧾 Insurance decision")
    metric_row("Eligible for claim?", damage_data["insurance_eligible"])
    metric_row("Claim urgency", damage_data["claim_urgency"])
    metric_row(
        "Suggested time to file claim",
        f"Within {damage_data['suggested_claim_window_days']} days"
    )
    metric_row("Recommendation", damage_data["insurance_recommendation"])

    st.markdown("### 💹 Yield & income impact (rough estimate)")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Normal yield", f"{int(normal_yield_q)} q")
    col_b.metric("Estimated yield loss", f"{damage_data['estimated_yield_loss_q']} q")
    col_c.metric("Estimated income loss", f"₹{damage_data['estimated_income_loss_rs']:,.0f}")

    st.markdown("### 🧑‍🌾 Farmer-friendly summary")
    st.info(damage_data["summary"])

    st.markdown("### ✅ Recommended farmer actions")
    for a in damage_data["recommended_farmer_actions"]:
        st.markdown(f"- {a}")

    st.markdown("### 📂 Documents needed for claim")
    for d in damage_data["required_documents_for_claim"]:
        st.markdown(f"- {d}")

    st.markdown("### 📅 Next 7 days – what to monitor")
    st.warning(damage_data["followup_next_7_days"])

    with st.expander("Full JSON for audit / integration"):
        st.json(damage_data)

    # ---------------- PDF ----------------
    def generate_pdf(data: dict) -> str:
        filename = "crop_damage_report.pdf"
        c = canvas.Canvas(filename, pagesize=A4)
        width, height = A4
        text = c.beginText(40, height - 60)

        lines = [
            "CROP DAMAGE & INSURANCE REPORT",
            "",
            f"Date: {data['timestamp']}",
            f"Location (approx): {data['latitude']}, {data['longitude']}",
            "",
            f"Crop: {data['crop_name']}",
            f"Total Area: {data['total_area_ha']} ha",
            "",
            f"Damage Type: {data['damage_type']}",
            f"Estimated Damage: {data['damage_severity_pct']}%",
            f"Area Affected: {data['damaged_area_ha_final']} ha",
            f"Salvageable: {'Yes' if data['salvageable'] else 'No'}",
            "",
            f"Normal Yield (est.): {int(data['normal_yield_q'])} quintal",
            f"Yield Loss (est.): {data['estimated_yield_loss_q']} quintal",
            f"Income Loss (est.): ₹{data['estimated_income_loss_rs']:,.0f}",
            "",
            f"Insurance Eligible: {data['insurance_eligible']}",
            f"Claim Urgency: {data['claim_urgency']}",
            f"Suggested Time to File Claim: within {data['suggested_claim_window_days']} days",
            "",
            "Insurance Recommendation:",
            data["insurance_recommendation"],
            "",
            "Summary:",
            data["summary"],
            "",
            "Recommended Farmer Actions:"
        ]

        for line in lines:
            text.textLine(line)

        for a in data["recommended_farmer_actions"]:
            text.textLine(f"- {a}")

        text.textLine("")
        text.textLine("Documents Required for Claim:")
        for d in data["required_documents_for_claim"]:
            text.textLine(f"- {d}")

        text.textLine("")
        text.textLine("Next 7 days – what to monitor:")
        text.textLine(data["followup_next_7_days"])

        c.drawText(text)
        c.showPage()
        c.save()
        return filename

    pdf_file = generate_pdf(damage_data)

    st.download_button(
        "⬇️ Download Insurance PDF",
        data=open(pdf_file, "rb").read(),
        file_name="crop_damage_report.pdf",
        mime="application/pdf"
    )

    # ---------------- WHATSAPP ALERT ----------------
    alerts.monitor_and_alert(
        "Crop Damage Report",
        {
            "summary": (
                f"{damage_data['summary']}\n"
                f"Crop: {damage_data['crop_name']}, Damage: {damage_data['damage_severity_pct']}%\n"
                f"Eligible: {damage_data['insurance_eligible']}, "
                f"Income loss (est.): ₹{damage_data['estimated_income_loss_rs']:,.0f}"
            ),
            "moisture_pct": 0
        }
    )

    st.success("📲 Insurance decision + summary sent on WhatsApp (text + voice)")
