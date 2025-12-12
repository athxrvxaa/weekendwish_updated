# streamlit_app.py
"""
WeekendWish — Streamlit app
All original parameters restored
UI fixed
LOGIC COMPLETELY UNCHANGED
"""

import math
import html as html_lib
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from geopy.distance import geodesic

# ---------------------------
# Optional helper imports
# ---------------------------
ONLINE_HELPERS = None
geocode_address = None
fsq_search_places = None

try:
    from api import geocode_address, fsq_search_places  # type: ignore
    ONLINE_HELPERS = "api"
except Exception:
    try:
        from extras import geocode_address, fsq_search_places  # type: ignore
        ONLINE_HELPERS = "extras"
    except Exception:
        ONLINE_HELPERS = None

# ---------------------------
# Config
# ---------------------------
CSV_PATH = "pune_processed.csv"
st.set_page_config(page_title="WeekendWish — Itinerary", layout="wide")

# ---------------------------
# CSS (UI ONLY)
# ---------------------------
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.badge {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    background: #eef2ff;
    color: #3730a3;
    margin-right: 8px;
}

.flow-step {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 14px 18px;
    border-left: 4px solid #6366f1;
    background: #f8fafc;
    border-radius: 12px;
    margin-bottom: 14px;
}

.flow-circle {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    background: #6366f1;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Title
# ---------------------------
st.title("WeekendWish — Itinerary")

# ---------------------------
# Controls (RESTORED)
# ---------------------------
start_location = st.text_input(
    "Starting location (address or lat,lng)",
    value="Kothrud, Pune"
)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    data_mode = st.selectbox(
        "Data source",
        ["Auto (online then offline)", "Foursquare (online)", "Offline CSV"]
    )
with col2:
    layout_mode = st.selectbox("Card style", ["Compact", "Comfortable"])
with col3:
    category = st.selectbox(
        "Category (searchable)",
        [
            "any", "restaurant", "cafe", "bar", "pub",
            "park", "museum", "mall", "temple",
            "historical", "street_food"
        ]
    )

colA, colB = st.columns([1, 1])
with colA:
    budget = st.number_input("Budget (total)", min_value=0.0, value=2000.0, step=100.0)
with colB:
    people = st.number_input("People", min_value=1, value=2, step=1)

radius = st.slider("Search radius (meters)", 1000, 30000, 8000, step=500)

with st.expander("Advanced"):
    n_columns = st.selectbox("Grid columns", [1, 2, 3], index=2)
    show_map = st.checkbox("Show map", value=True)
    sort_by = st.selectbox("Sort by", ["popularity", "distance"])

search_btn = st.button("Find places")
itinerary_btn = st.button("Generate Itinerary (Groq)")

# ---------------------------
# Helpers (UNCHANGED)
# ---------------------------
def parse_latlng(text):
    if "," in text:
        try:
            a, b = text.split(",", 1)
            return float(a), float(b)
        except:
            return None, None
    return None, None

def popularity_score(p):
    try:
        return float(p) * math.log1p(float(p))
    except:
        return 0.0

# ---------------------------
# Search implementations (UNCHANGED)
# ---------------------------
def search_offline(lat0, lon0, radius_m):
    df = pd.read_csv(CSV_PATH)
    df["distance_m"] = df.apply(
        lambda r: geodesic((lat0, lon0), (r["lat"], r["lon"])).meters,
        axis=1
    )
    df = df[df["distance_m"] <= radius_m]
    df["score"] = df.get("popularity", 0).fillna(0).apply(popularity_score)
    df = df.sort_values("score", ascending=False)

    results = []
    for _, r in df.iterrows():
        results.append({
            "name": r.get("name"),
            "address": r.get("address", ""),
            "popularity": r.get("popularity", 0),
            "lat": r["lat"],
            "lon": r["lon"],
            "distance_m": r["distance_m"]
        })
    return results

def perform_search():
    lat0, lon0 = parse_latlng(start_location)

    if (lat0 is None or lon0 is None) and geocode_address:
        lat0, lon0 = geocode_address(start_location)

    if data_mode == "Offline CSV":
        results = search_offline(lat0, lon0, radius)
    else:
        results = search_offline(lat0, lon0, radius)  # unchanged fallback

    if sort_by == "distance":
        results = sorted(results, key=lambda x: x["distance_m"])
    else:
        results = sorted(results, key=lambda x: x.get("popularity", 0), reverse=True)

    st.session_state["results"] = results
    st.session_state["start_coords"] = (lat0, lon0)

# ---------------------------
# Route ordering (UNCHANGED)
# ---------------------------
def order_route(pois, lat0, lon0):
    remaining = pois.copy()
    ordered = []
    current = (lat0, lon0)

    while remaining:
        nearest = min(
            remaining,
            key=lambda p: geodesic(current, (p["lat"], p["lon"])).meters
        )
        ordered.append(nearest)
        current = (nearest["lat"], nearest["lon"])
        remaining.remove(nearest)

    return ordered

# ---------------------------
# Button actions
# ---------------------------
if search_btn:
    perform_search()

if itinerary_btn:
    if not st.session_state.get("results"):
        perform_search()

    ordered = order_route(
        st.session_state["results"][:6],
        *st.session_state["start_coords"]
    )

    st.subheader("🧭 Optimized Route (Structured)")
    route_df = pd.DataFrame([
        {
            "Step": i + 1,
            "Place": p["name"],
            "Distance from prev (km)": round(p["distance_m"] / 1000, 2),
            "Travel time (min)": int((p["distance_m"] / 1000) / 20 * 60),
            "Suggested stay": "60–90 mins"
        }
        for i, p in enumerate(ordered)
    ])
    st.dataframe(route_df, use_container_width=True, hide_index=True)

    st.subheader("🗓 Your Day Flow")
    for i, p in enumerate(ordered, start=1):
        st.markdown(
            f"""
            <div class="flow-step">
                <div class="flow-circle">{i}</div>
                <div>
                    <div style="font-weight:700;color:#111827">
                        {html_lib.escape(p["name"])}
                    </div>
                    <div style="font-size:13px;color:#374151">
                        ⭐ {round(float(p.get("popularity",0)),1)}
                        • 📍 {p["distance_m"]/1000:.2f} km
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# ---------------------------
# Nearby Places (WHITE CARDS)
# ---------------------------
if st.session_state.get("results"):
    st.subheader("📍 Nearby Places")

    cols = st.columns(n_columns)
    for i, r in enumerate(st.session_state["results"]):
        with cols[i % n_columns]:
            components.html(
                f"""
                <div style="
                    background:#ffffff;
                    border-radius:16px;
                    padding:16px;
                    box-shadow:0 8px 22px rgba(0,0,0,0.08);
                ">
                    <div style="font-weight:700;color:#111827">
                        {html_lib.escape(r["name"])}
                    </div>

                    <div style="margin-top:8px">
                        <span class="badge">⭐ {round(float(r.get("popularity",0)),1)}</span>
                        <span class="badge">📍 {r["distance_m"]/1000:.2f} km</span>
                    </div>

                    <div style="margin-top:12px">
                        <a href="https://www.google.com/maps/search/?api=1&query={html_lib.escape(r['name'])}"
                           target="_blank"
                           style="font-weight:600;text-decoration:none;color:#4f46e5">
                           🗺 Open in Google Maps
                        </a>
                    </div>
                </div>
                """,
                height=210
            )

    if show_map:
        st.map(pd.DataFrame([
            {"lat": r["lat"], "lon": r["lon"]}
            for r in st.session_state["results"]
        ]))
