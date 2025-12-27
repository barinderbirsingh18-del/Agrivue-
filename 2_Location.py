import os
from datetime import datetime, timedelta
import math

import pandas as pd
import streamlit as st

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="AgriVue • Location Intelligence",
    page_icon="📍",
    layout="wide"
)

st.title("📍 Location Intelligence")
st.caption("Geo‑Tagged Weather Insights • Area Coverage Mapping")

st.divider()

# ---------------- HELPERS ----------------
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# ---------------- MANUAL LOCATION INPUT ----------------
st.subheader("🌍 Set focus location")

col1, col2 = st.columns(2)
with col1:
    latitude = st.text_input("Latitude", placeholder="e.g. 30.7333")
with col2:
    longitude = st.text_input("Longitude", placeholder="e.g. 76.7794")

radius = st.slider(
    "Coverage radius (km)",
    min_value=1,
    max_value=25,
    value=5,
)

if latitude and longitude:
    try:
        lat = float(latitude)
        lon = float(longitude)

        st.success(f"📍 Location set: ({lat:.4f}, {lon:.4f})")
        st.info(f"🌐 Coverage area: ~{radius} km radius")

        # ---------------- MAP VIEW ----------------
        st.subheader("🗺️ Area map")

        map_df = pd.DataFrame({"lat": [lat], "lon": [lon]})
        st.map(map_df, zoom=10)

    except ValueError:
        st.error("❌ Invalid coordinates. Please enter numeric values.")
        lat = lon = None
else:
    st.warning("⚠️ Enter latitude and longitude to enable location intelligence.")
    lat = lon = None

st.divider()

# ---------------- HISTORICAL LOGS ----------------
st.subheader("📊 Geo‑tagged weather logs")

HISTORY_FILE = "farm_history.csv"

if not os.path.exists(HISTORY_FILE):
    st.info("No logs available. Run analyses from Command Center.")
    st.stop()

df = pd.read_csv(HISTORY_FILE, on_bad_lines="skip")

if "Timestamp" in df.columns:
    try:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    except Exception:
        pass

if "latitude" not in df.columns or "longitude" not in df.columns:
    st.info("No geo‑tagged data found yet.")
    st.stop()

# ---- basic filters ----
colf1, colf2 = st.columns(2)
with colf1:
    last_n_days = st.selectbox(
        "Show data from last…",
        options=[1, 3, 7, 15, 30, 90],
        index=2,
    )
with colf2:
    node_options = df["Node"].dropna().unique().tolist() if "Node" in df.columns else []
    node_filter = st.multiselect(
        "Filter by node / device",
        options=node_options,
        default=node_options,
    )

if "Timestamp" in df.columns:
    cutoff = datetime.now() - timedelta(days=last_n_days)
    df = df[df["Timestamp"] >= cutoff]

if node_filter and "Node" in df.columns:
    df = df[df["Node"].isin(node_filter)]

if df.empty:
    st.warning("No logs after filters.")
    st.stop()

# ---- distance & inside‑radius tagging ----
if lat is not None and lon is not None:
    df["distance_km"] = df.apply(
        lambda r: haversine_km(lat, lon, r["latitude"], r["longitude"]),
        axis=1,
    )
    df["inside_radius"] = df["distance_km"] <= radius
    in_radius = df[df["inside_radius"]]
else:
    df["distance_km"] = None
    df["inside_radius"] = False
    in_radius = df.iloc[0:0]

# ---- metrics ----
colm1, colm2, colm3 = st.columns(3)
colm1.metric("Total geo‑logs", len(df))
colm2.metric("Logs inside radius", len(in_radius))
if lat is not None:
    unique_nodes = in_radius["Node"].nunique() if "Node" in in_radius.columns else 0
    colm3.metric("Active nodes in area", unique_nodes)
else:
    colm3.metric("Active nodes in area", "-")

# ---- map of logs near location ----
if lat is not None and not in_radius.empty:
    st.subheader("🛰️ Signals inside coverage area")
    map_logs = in_radius.rename(columns={"latitude": "lat", "longitude": "lon"})[
        ["lat", "lon"]
    ]
    st.map(map_logs, zoom=11)
    st.caption("Dots show all geo‑tagged insights inside the selected radius.")
elif lat is not None:
    st.info("No historical signals fall inside this radius yet.")

# ---- tables ----
st.markdown("#### Detailed logs")

cols = [
    c
    for c in ["Timestamp", "Node", "latitude", "longitude", "distance_km", "summary", "Action"]
    if c in df.columns
]

st.dataframe(
    df[cols].sort_values("Timestamp", ascending=False),
    use_container_width=True,
)

if lat is not None:
    st.caption("Distance column shows how far each event is from the chosen point (km).")
else:
    st.caption("Set a location above to see distance and coverage insights.")
