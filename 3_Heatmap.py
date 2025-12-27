import os
import json
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from google import genai

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="AgriVue • Climate Risk Command Center",
    page_icon="🛰️",
    layout="wide"
)

API_KEY = "AIzaSyDmsCbY2SnY1OyUP73p7MsTWEXIFmOJvMQ"
client = genai.Client(api_key=API_KEY)

HISTORY_FILE = "farm_history.csv"

st.title("🛰️ Climate Risk Command Center")
st.caption("AI-powered field risk map • Clusters • Early warnings • What‑if simulator")

st.divider()

# ---------------- LOAD DATA ----------------
if not os.path.exists(HISTORY_FILE):
    st.warning("No data found. Capture geo-tagged images first.")
    st.stop()

df = pd.read_csv(HISTORY_FILE, on_bad_lines="skip")
st.write("Detected columns:", list(df.columns))

required_cols = {"latitude", "longitude", "risk_score"}
if not required_cols.issubset(df.columns):
    st.error("Geo-tagged data not available yet.")
    st.stop()

df = df.dropna(subset=["latitude", "longitude", "risk_score"])
if df.empty:
    st.warning("No valid geo-tagged entries yet.")
    st.stop()

# Parse timestamp if present
if "Timestamp" in df.columns:
    try:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    except Exception:
        pass

# ---------------- FILTERS ----------------
st.subheader("🎛️ Filters")

col1, col2, col3 = st.columns(3)

with col1:
    min_risk = st.slider(
        "Minimum risk to show",
        min_value=0.0,
        max_value=1.0,
        value=0.4,
        step=0.05,
    )

with col2:
    node_options = df["Node"].unique().tolist() if "Node" in df.columns else []
    node_filter = st.multiselect(
        "Nodes / Villages",
        options=node_options,
        default=node_options,
    )

with col3:
    if "Timestamp" in df.columns and pd.api.types.is_datetime64_any_dtype(df["Timestamp"]):
        max_date = df["Timestamp"].max().date()
        min_date = df["Timestamp"].min().date()

        default_start = max(min_date, max_date - timedelta(days=7))
        default_end = max_date

        start_date, end_date = st.date_input(
            "Time window",
            value=(default_start, default_end),
            min_value=min_date,
            max_value=max_date,
        )
    else:
        start_date, end_date = None, None

# Apply filters
if "Node" in df.columns and node_filter:
    df = df[df["Node"].isin(node_filter)]

df = df[df["risk_score"] >= min_risk]

if start_date and end_date and "Timestamp" in df.columns and pd.api.types.is_datetime64_any_dtype(df["Timestamp"]):
    mask = (df["Timestamp"].dt.date >= start_date) & (df["Timestamp"].dt.date <= end_date)
    df = df[mask]

if df.empty:
    st.warning("No data after filters. Try lowering minimum risk or widening dates.")
    st.stop()

# ---------------- MAP ----------------
st.subheader("🗺️ Live Field Risk Map")

map_df = df[["latitude", "longitude", "risk_score"]].copy()
st.map(
    map_df,
    latitude="latitude",
    longitude="longitude",
    size="risk_score",
    color="#FF3B30",
)
st.caption("Red circles show higher‑risk signals. Bigger = more risk.")

st.divider()

# ---------------- CLUSTERS & METRICS ----------------
st.subheader("📊 Cluster & risk summary")

avg_risk = df["risk_score"].mean()
max_risk = df["risk_score"].max()
min_risk_seen = df["risk_score"].min()
total_signals = len(df)


def risk_bucket(x: float) -> str:
    if x < 0.4:
        return "Low"
    elif x < 0.7:
        return "Medium"
    return "High"


df["risk_band"] = df["risk_score"].apply(risk_bucket)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total signals", total_signals)
with col2:
    st.metric("Average risk", f"{avg_risk:.2f}")
with col3:
    st.metric("Highest risk", f"{max_risk:.2f}")
with col4:
    st.metric(
        "Overall level",
        "🚨 HIGH" if avg_risk > 0.7 else ("⚠️ MODERATE" if avg_risk > 0.4 else "✅ LOW"),
    )

band_counts = df["risk_band"].value_counts().reindex(["Low", "Medium", "High"]).fillna(0).astype(int)
bc1, bc2, bc3 = st.columns(3)
bc1.metric("Low risk signals", band_counts["Low"])
bc2.metric("Medium risk signals", band_counts["Medium"])
bc3.metric("High risk signals", band_counts["High"])

if "Node" in df.columns:
    st.markdown("#### Node‑wise risk leaderboard")
    node_summary = (
        df.groupby("Node")
        .agg(
            signals=("risk_score", "count"),
            avg_risk=("risk_score", "mean"),
            high_risk_signals=("risk_band", lambda s: (s == "High").sum()),
        )
        .reset_index()
        .sort_values(["high_risk_signals", "avg_risk"], ascending=False)
    )
    st.dataframe(node_summary, use_container_width=True)

if "crop" in df.columns:
    st.markdown("#### Crop‑wise risk snapshot")
    crop_summary = (
        df.groupby("crop")
        .agg(
            signals=("risk_score", "count"),
            avg_risk=("risk_score", "mean"),
        )
        .reset_index()
        .sort_values("avg_risk", ascending=False)
    )
    st.dataframe(crop_summary, use_container_width=True)

st.divider()

# ---------------- NODE DRILLDOWN + AI ADVICE ----------------
st.subheader("📍 Drill down into one node / village")

if "Node" in df.columns and len(df["Node"].unique()) > 0:
    selected_node = st.selectbox("Choose node / village", sorted(df["Node"].unique()))
    node_df = df[df["Node"] == selected_node]

    st.markdown(f"**Signals for {selected_node}**")
    st.dataframe(
        node_df[
            [c for c in ["Timestamp", "latitude", "longitude", "risk_score", "summary", "Action"] if c in node_df.columns]
        ].sort_values("Timestamp", ascending=False),
        use_container_width=True,
    )

    # JSON‑safe records (Timestamp -> ISO string)
    node_records = json.loads(
        node_df.to_json(orient="records", date_format="iso")
    )

    node_prompt = f"""
You are AgriVue AI, climate assistant.

Below are risk signals for one village/node: {selected_node}.
Each record: {{"risk_score": 0–1, "summary": "...", "Action": "..."}}.

DATA (JSON):
{json.dumps(node_records)[:5000]}

1. Explain in 3–4 sentences what is happening in this node.
2. Give 3 short, actionable recommendations for farmers in this node (when to irrigate, spray, or stay alert).
Keep language simple Hinglish.
"""

    try:
        node_res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=node_prompt,
        )
        st.markdown(node_res.text)
    except Exception as e:
        st.error(f"AgriVue AI node advice unavailable: {e}")

st.divider()

# ---------------- EARLY WARNING PANEL ----------------
st.subheader("⏭️ Next 3‑day early‑warning outlook")

sample_records = df.copy()
if len(sample_records) > 300:
    sample_records = sample_records.sample(300, random_state=42)

# JSON‑safe records
records = json.loads(
    sample_records.to_json(orient="records", date_format="iso")
)

warning_prompt = f"""
You are AgriVue AI.

These are geo risk signals (JSON list):
{json.dumps(records)[:6000]}

Imagine you must brief a district agriculture officer. Create:

1. A short paragraph: what *could* go wrong in the next 3 days (heat, heavy rain, waterlogging, pest explosion, etc.).
2. A bullet list of 4–6 specific precautions farmers should take in these 3 days.
3. One line for officers: where to prioritize field visits (which bands/nodes).

Be concise, plain language, no heavy jargon.
"""

try:
    warn_res = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=warning_prompt,
    )
    st.markdown(warn_res.text)
except Exception as e:
    st.error(f"Early‑warning AI summary unavailable: {e}")

st.divider()

# ---------------- WHAT-IF SIMULATOR ----------------
st.subheader("🤖 What‑if climate simulator")

what_if_q = st.text_input(
    "Ask a what‑if about this area (example: “What if rainfall is 30% above normal?”, “What if I delay irrigation by 2 days?”)"
)

if what_if_q:
    sim_prompt = f"""
You are AgriVue AI.

Current micro‑climate risk signals (JSON list):
{json.dumps(records)[:6000]}

Farmer question: "{what_if_q}"

In 3–5 sentences:
- Explain roughly what might happen under this scenario.
- Give one clear recommendation (do / don't) and timing.

Avoid numbers you cannot see; talk in trends (higher/lower risk). Use simple Hinglish.
"""

    try:
        sim_res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=sim_prompt,
        )
        st.info(sim_res.text)
    except Exception as e:
        st.error(f"What‑if simulator error: {e}")

st.divider()

# ---------------- RAW SIGNALS TABLE ----------------
st.subheader("📋 Raw geo signals (for audit)")

cols_to_show = [
    c
    for c in ["Timestamp", "Node", "crop", "latitude", "longitude", "risk_score", "summary", "Action"]
    if c in df.columns
]

st.dataframe(
    df[cols_to_show].sort_values("Timestamp", ascending=False) if "Timestamp" in cols_to_show else df[cols_to_show],
    use_container_width=True,
)

st.caption("This table is useful for debugging, export, or linking with external dashboards.")
