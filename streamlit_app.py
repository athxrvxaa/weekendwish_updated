# streamlit_app.py
"""
Streamlit UI for WeekendWish (final)
- Price removed
- Photos removed
- Results rendered as visual cards (HTML boxes), sanitized with html.escape
- Uses online helpers (api.py or extras.py) if available, else offline CSV
"""

import os
import math
import html as html_lib
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from geopy.distance import geodesic

load_dotenv()

# Try to import helper functions from your repo (api.py or extras.py)
ONLINE_HELPERS = None
geocode_address = None
fsq_search_places = None
safe_get_main_coords = None
fsq_get_photo_url = None

try:
    from api import geocode_address, fsq_search_places, safe_get_main_coords, fsq_get_photo_url  # type: ignore
    ONLINE_HELPERS = "api"
except Exception:
    try:
        from extras import geocode_address, fsq_search_places, safe_get_main_coords, fsq_get_photo_url  # type: ignore
        ONLINE_HELPERS = "extras"
    except Exception:
        ONLINE_HELPERS = None

CSV_PATH = "pune_processed.csv"

st.set_page_config(page_title="WeekendWish", layout="centered")
st.title("WeekendWish — Find popular places nearby (Streamlit)")

col1, col2 = st.columns([3,1])
with col1:
    start_input = st.text_input("Starting location (address or lat,lng)", value="Kothrud, Pune")
with col2:
    use_offline = st.selectbox("Data source", ["Auto (try online then offline)", "Foursquare (online)", "Offline CSV"])

col3, col4 = st.columns([1,1])
with col3:
    budget = st.number_input("Budget (total) — kept for internal filtering", min_value=0.0, value=2000.0, step=100.0)
with col4:
    people = st.number_input("People", min_value=1, value=2, step=1)

radius = st.slider("Search radius (meters)", min_value=1000, max_value=30000, value=8000, step=500)

st.write("")  # gap
run_btn = st.button("Find places")

# ---- helpers ----
def parse_latlng(text):
    if not isinstance(text, str):
        return None, None
    if "," in text:
        parts = [p.strip() for p in text.split(",")]
        if len(parts) >= 2:
            try:
                return float(parts[0]), float(parts[1])
            except:
                return None, None
    return None, None

def budget_to_price_level(budget_pp):
    # simple heuristic, kept for internal filtering if online returns price tiers
    if budget_pp < 200:
        return 1
    if budget_pp < 500:
        return 2
    if budget_pp < 1200:
        return 3
    return 4

def score_popularity_pop(pop):
    try:
        p = float(pop)
        return p * math.log1p(p)
    except:
        return 0.0

def search_offline(lat, lon, radius_m, budget_pp, top_n=12):
    if not os.path.exists(CSV_PATH):
        st.warning(f"Offline CSV not found at {CSV_PATH}.")
        return []
    try:
        df = pd.read_csv(CSV_PATH)
    except Exception as e:
        st.warning(f"Failed to read CSV: {e}")
        return []

    if "lat" not in df.columns or "lon" not in df.columns:
        st.warning("CSV missing lat/lon columns.")
        return []

    def dist_m(r):
        return geodesic((lat, lon), (r["lat"], r["lon"])).meters

    # compute distances
    df["distance_m"] = df.apply(lambda r: dist_m(r), axis=1)
    df = df[df["distance_m"] <= radius_m].copy()

    price_col = "price_tier" if "price_tier" in df.columns else ("price" if "price" in df.columns else None)
    pop_col = "popularity" if "popularity" in df.columns else None

    if price_col:
        df["affordable"] = df[price_col].fillna(2).astype(float) <= budget_to_price_level(budget_pp)
        df = df[df["affordable"]]
    if pop_col:
        df["score"] = df[pop_col].fillna(0).apply(score_popularity_pop)
    else:
        df["score"] = 0.0

    df = df.sort_values("score", ascending=False)
    results = []
    for _, r in df.head(top_n).iterrows():
        results.append({
            "id": None,
            "name": r.get("name"),
            "address": r.get("address") or "",
            "popularity": r.get(pop_col) if pop_col else None,
            "lat": r["lat"],
            "lon": r["lon"],
            "distance_m": float(r["distance_m"])
        })
    return results

def search_online(lat, lon, radius_m, budget_pp, top_n=12):
    if ONLINE_HELPERS is None:
        raise RuntimeError("Online helpers (api.py/extras.py) not available.")
    raw = fsq_search_places(lat, lon, radius=radius_m, limit=40)
    max_price = budget_to_price_level(budget_pp)
    cleaned = []
    for p in raw:
        pid = p.get("fsq_place_id") or p.get("id")
        name = p.get("name")
        price = p.get("price")
        pop = p.get("popularity") or 0
        lat2, lon2 = safe_get_main_coords(p)
        if price is not None and isinstance(price, (int,float)) and price > max_price:
            continue
        try:
            dist_m = geodesic((lat, lon), (lat2, lon2)).meters if (lat2 and lon2) else None
        except:
            dist_m = None
        cleaned.append({
            "id": pid,
            "name": name,
            "address": (p.get("location") or {}).get("formatted_address") or (p.get("location") or {}).get("address") or "",
            "popularity": pop,
            "lat": lat2,
            "lon": lon2,
            "distance_m": dist_m,
            "score": score_popularity_pop(pop)
        })
    cleaned = sorted(cleaned, key=lambda x: x.get("score", 0), reverse=True)[:top_n]
    return cleaned

# ---- display helpers ----
CARD_STYLE = """
<div style="
  border:1px solid #e6e6e6;
  border-radius:10px;
  padding:12px;
  margin-bottom:12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
">
  <div style="font-size:18px;font-weight:600;margin-bottom:6px;">{name}</div>
  <div style="color:#555;margin-bottom:6px;">{address}</div>
  <div style="font-size:13px;color:#333">Popularity: <strong>{pop}</strong> &nbsp;&nbsp; Distance: <strong>{dist}</strong></div>
</div>
"""

# ---- main action ----
if run_btn:
    lat0, lon0 = parse_latlng(start_input)
    if lat0 is None or lon0 is None:
        try:
            lat0, lon0 = geocode_address(start_input)
        except Exception as e:
            st.error("Geocoding failed: " + str(e))
            lat0 = lon0 = None

    if lat0 is None:
        st.error("Couldn't get coordinates for starting location. Try lat,lng or check geocoding keys.")
    else:
        st.info(f"Searching around {lat0:.6f}, {lon0:.6f} within {radius} meters ...")
        budget_pp = float(budget) / max(1, int(people))

        results = []
        mode = use_offline
        if mode == "Auto (try online then offline)":
            if ONLINE_HELPERS:
                try:
                    results = search_online(lat0, lon0, radius, budget_pp)
                    if not results:
                        results = search_offline(lat0, lon0, radius, budget_pp)
                except Exception as e:
                    st.warning("Online search failed; falling back to offline. (" + str(e) + ")")
                    results = search_offline(lat0, lon0, radius, budget_pp)
            else:
                results = search_offline(lat0, lon0, radius, budget_pp)
        elif mode == "Foursquare (online)":
            if not ONLINE_HELPERS:
                st.error("Online helper functions not found. Falling back to offline.")
                results = search_offline(lat0, lon0, radius, budget_pp)
            else:
                try:
                    results = search_online(lat0, lon0, radius, budget_pp)
                except Exception as e:
                    st.error("Online search error: " + str(e))
                    results = []
        else:
            results = search_offline(lat0, lon0, radius, budget_pp)

        if not results:
            st.write("No places found.")
        else:
            # Render visual cards (sanitized)
            for r in results:
                name = html_lib.escape(r.get("name") or "")
                address = html_lib.escape(r.get("address") or "")
                pop_text = html_lib.escape(str(r.get("popularity") if r.get("popularity") is not None else "—"))
                dist_text = f"{(r.get('distance_m')/1000):.2f} km" if r.get('distance_m') is not None else "—"

                html = CARD_STYLE.format(name=name, address=address, pop=pop_text, dist=dist_text)
                st.markdown(html, unsafe_allow_html=True)

            # Map
            try:
                map_df = pd.DataFrame([{"lat": r["lat"], "lon": r["lon"], "name": r["name"]} for r in results if r.get("lat") and r.get("lon")])
                if not map_df.empty:
                    st.map(map_df.rename(columns={"lon":"lon", "lat":"lat"}))
            except Exception:
                pass
