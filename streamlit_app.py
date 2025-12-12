# streamlit_app.py
"""
WeekendWish — Streamlit app with Groq itinerary integration (safe fallback)
- Uses Groq SDK if available & GROQ_API_KEY is set
- Falls back to deterministic local itinerary generator when Groq isn't available
- Keeps search, ordering, cards, session-state, offline/online modes
"""

import os
import math
import html as html_lib
import pandas as pd
import streamlit as st
from geopy.distance import geodesic

# Optional local helper imports
ONLINE_HELPERS = None
geocode_address = None
fsq_search_places = None
safe_get_main_coords = None

try:
    from api import geocode_address, fsq_search_places, safe_get_main_coords  # type: ignore
    ONLINE_HELPERS = "api"
except Exception:
    try:
        from extras import geocode_address, fsq_search_places, safe_get_main_coords  # type: ignore
        ONLINE_HELPERS = "extras"
    except Exception:
        ONLINE_HELPERS = None

# Try groq SDK import (we use if available)
try:
    import groq  # type: ignore
    GROQ_SDK_AVAILABLE = True
except Exception:
    GROQ_SDK_AVAILABLE = False

# Config
CSV_PATH = "pune_processed.csv"
st.set_page_config(page_title="WeekendWish (Groq)", layout="wide")
st.title("WeekendWish — Itinerary ")

# ---------------------------
# Controls
# ---------------------------
start_location = st.text_input("Starting location (address or lat,lng)", value="Kothrud, Pune")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    data_mode = st.selectbox("Data source", ["Auto (online then offline)", "Foursquare (online)", "Offline CSV"])
with col2:
    layout_mode = st.selectbox("Card style", ["Compact", "Comfortable"])
with col3:
    category = st.selectbox(
        "Category (searchable)",
        [
            "any", "restaurant", "cafe", "bar", "pub", "fast_food", "bakery",
            "park", "garden", "museum", "theatre", "cinema", "mall",
            "viewpoint", "attraction", "historical", "monument",
            "temple", "church", "mosque", "zoo", "aquarium",
            "nightclub", "dessert", "street_food", "art_gallery",
            "market", "stadium", "hiking", "playground"
        ],
    )

colA, colB = st.columns([1, 1])
with colA:
    budget = st.number_input("Budget (total)", min_value=0.0, step=100.0, value=2000.0)
with colB:
    people = st.number_input("People", min_value=1, step=1, value=2)

radius = st.slider("Search radius (meters)", 1000, 30000, 8000, step=500)

with st.expander("Advanced"):
    n_columns = st.selectbox("Grid columns", [1, 2, 3], index=1)
    show_map = st.checkbox("Show map", value=True)
    sort_by = st.selectbox("Sort by", ["popularity", "distance"])

search_btn = st.button("Find places")
itinerary_btn = st.button("Generate Itinerary (Groq)")

# ---------------------------
# Helpers
# ---------------------------
def parse_latlng(text):
    if not text or not isinstance(text, str):
        return None, None
    if "," in text:
        try:
            a, b = text.split(",", 1)
            return float(a.strip()), float(b.strip())
        except:
            return None, None
    return None, None

def popularity_score(p):
    try:
        p = float(p)
        return p * math.log1p(p)
    except:
        return 0.0

def match_category_offline(row, cat):
    if not cat or cat == "any":
        return True
    txt = f"{row.get('name','')} {row.get('tags','')} {row.get('category','')}".lower()
    return cat.lower() in txt

def match_category_online(p, cat):
    if not cat or cat == "any":
        return True
    name = (p.get("name") or "").lower()
    if cat.lower() in name:
        return True
    cats = p.get("categories") or []
    for c in cats:
        nm = c.get("name") if isinstance(c, dict) else str(c)
        if cat.lower() in (nm or "").lower():
            return True
    return False

# ---------------------------
# Search implementations (same as before, with safe geocode extraction)
# ---------------------------
def search_offline(lat0, lon0, radius_m, budget_pp, category_selected, top_n=50):
    if not os.path.exists(CSV_PATH):
        st.error(f"Offline CSV not found at {CSV_PATH}.")
        return []
    try:
        df = pd.read_csv(CSV_PATH)
    except Exception as e:
        st.error(f"Failed to read CSV: {e}")
        return []
    if "lat" not in df.columns or "lon" not in df.columns:
        st.error("CSV missing lat/lon columns.")
        return []
    df["distance_m"] = df.apply(lambda r: geodesic((lat0, lon0), (r["lat"], r["lon"])).meters, axis=1)
    df = df[df["distance_m"] <= radius_m].copy()
    if category_selected and category_selected != "any":
        df = df[df.apply(lambda row: match_category_offline(row, category_selected), axis=1)]
    popcol = "popularity" if "popularity" in df.columns else None
    if popcol:
        df["score"] = df[popcol].fillna(0).apply(popularity_score)
    else:
        df["score"] = 0.0
    df = df.sort_values("score", ascending=False)
    results = []
    for _, r in df.head(top_n).iterrows():
        results.append({
            "name": r.get("name"),
            "address": r.get("address", ""),
            "popularity": r.get(popcol) if popcol else None,
            "lat": r["lat"],
            "lon": r["lon"],
            "distance_m": float(r["distance_m"])
        })
    return results

def search_online(lat0, lon0, radius_m, budget_pp, category_selected, top_n=50):
    try:
        raw = fsq_search_places(lat0, lon0, radius=radius_m, limit=60)
    except Exception as e:
        st.warning(f"Foursquare search failed: {e}")
        return []
    cleaned = []
    for p in raw:
        if category_selected and category_selected != "any":
            try:
                if not match_category_online(p, category_selected):
                    continue
            except:
                pass
        name = p.get("name")
        pop = p.get("popularity") or 0
        # Safe coordinates extraction (works with FSQ v3 geocodes)
        lat2 = p.get("geocodes", {}).get("main", {}).get("latitude")
        lon2 = p.get("geocodes", {}).get("main", {}).get("longitude")
        try:
            d = geodesic((lat0, lon0), (lat2, lon2)).meters if lat2 and lon2 else None
        except:
            d = None
        cleaned.append({
            "name": name,
            "address": (p.get("location") or {}).get("formatted_address") or (p.get("location") or {}).get("address") or "",
            "popularity": pop,
            "lat": lat2,
            "lon": lon2,
            "distance_m": d,
            "score": popularity_score(pop)
        })
    return sorted(cleaned, key=lambda x: x.get("score", 0), reverse=True)[:top_n]

# ---------------------------
# perform_search central function
# ---------------------------
def perform_search():
    latlng = parse_latlng(start_location)
    lat0, lon0 = latlng if latlng != (None, None) else (None, None)

    if (lat0 is None or lon0 is None) and ONLINE_HELPERS and geocode_address:
        try:
            lat0, lon0 = geocode_address(start_location)
        except Exception as e:
            st.warning(f"Geocoding failed: {e}")
            lat0 = lon0 = None

    if lat0 is None or lon0 is None:
        st.error("Starting coordinates unavailable. Enter 'lat,lng' or enable geocoding helper.")
        st.session_state["results"] = []
        st.session_state["start_coords"] = None
        return []

    budget_pp = float(budget) / max(1, int(people))
    results_local = []

    try:
        if data_mode == "Offline CSV":
            results_local = search_offline(lat0, lon0, radius, budget_pp, category)
        elif data_mode == "Foursquare (online)":
            results_local = search_online(lat0, lon0, radius, budget_pp, category)
        else:  # Auto
            if ONLINE_HELPERS:
                results_local = search_online(lat0, lon0, radius, budget_pp, category)
                if not results_local:
                    results_local = search_offline(lat0, lon0, radius, budget_pp, category)
            else:
                results_local = search_offline(lat0, lon0, radius, budget_pp, category)
    except Exception as e:
        st.error(f"Search failed: {e}")
        results_local = []

    if results_local:
        if sort_by == "popularity":
            results_local = sorted(results_local, key=lambda x: x.get("popularity") or 0, reverse=True)
        else:
            results_local = sorted(results_local, key=lambda x: x.get("distance_m") or 1e9)

    st.session_state["results"] = results_local
    st.session_state["start_coords"] = (lat0, lon0)
    return results_local

# ---------------------------
# Ordering
# ---------------------------
def order_route(pois, start_lat, start_lon):
    remaining = pois.copy()
    ordered = []
    current = (start_lat, start_lon)
    while remaining:
        valid = [p for p in remaining if p.get("lat") is not None and p.get("lon") is not None]
        if not valid:
            ordered.extend(remaining)
            break
        nearest = min(valid, key=lambda p: geodesic(current, (p["lat"], p["lon"])).meters)
        ordered.append(nearest)
        current = (nearest["lat"], nearest["lon"])
        remaining.remove(nearest)
    return ordered

# ---------------------------
# Groq-based itinerary (if available) OR deterministic fallback
# ---------------------------
def generate_itinerary_via_groq_or_fallback(ordered_pois, budget_total, people_count):
    """
    Attempt to generate an itinerary using Groq SDK if available and GROQ_API_KEY is set.
    If Groq is not available or fails, return a deterministic, helpful itinerary constructed locally.
    """
    # Build simple POI lines for the prompt / fallback
    poi_lines = []
    for idx, p in enumerate(ordered_pois, start=1):
        name = p.get("name", "unknown")
        addr = p.get("address", "")
        km = (p.get("distance_m") or 0) / 1000.0
        pop = p.get("popularity") if p.get("popularity") is not None else "unknown"
        poi_lines.append(f"{idx}. {name} — {addr} — {km:.2f} km from previous — popularity: {pop}")

    # If Groq SDK available and key present, try it
    groq_key = os.environ.get("GROQ_API_KEY")
    if GROQ_SDK_AVAILABLE and groq_key:
        try:
            # Use groq client if available.
            # The exact SDK usage can differ depending on groq version; we attempt the common pattern.
            # If your environment's groq client requires a different call shape, adjust here.
            client = groq.Groq(api_key=groq_key) if hasattr(groq, "Groq") else groq.Client(api_key=groq_key)
            # build a human-friendly prompt
            prompt = f"""
You are a practical travel assistant. Create a concise day itinerary for {int(people_count)} people with total budget ₹{int(budget_total)}.
Use these places in this order and for each place include arrival time (approx), duration, travel time from previous, and a short reason to visit.

Places:
{chr(10).join(poi_lines)}

Return a numbered itinerary.
"""
            # Attempt a generic generation call (SDKs differ; this is best-effort)
            if hasattr(client, "generate"):  # common method name
                resp = client.generate(model=os.environ.get("GROQ_MODEL", "llama-3.1-70b-mini"), prompt=prompt, max_tokens=700)
                # Attempt to extract text from common response shapes
                if isinstance(resp, dict):
                    # try typical keys
                    text = resp.get("output_text") or resp.get("text") or resp.get("result") or str(resp)
                else:
                    text = getattr(resp, "output_text", None) or getattr(resp, "text", None) or str(resp)
                if text:
                    return f"(Generated by Groq)\n\n{text}"
                else:
                    # fallback to str(resp)
                    return f"(Groq response)\n\n{str(resp)}"
            elif hasattr(client, "chat") and hasattr(client.chat, "complete"):
                # hypothetical chat API
                resp = client.chat.complete(model=os.environ.get("GROQ_MODEL", "llama-3.1-70b-mini"), messages=[{"role":"user","content":prompt}])
                text = getattr(resp, "output_text", None) or (resp.get("output_text") if isinstance(resp, dict) else None) or str(resp)
                return f"(Generated by Groq chat)\n\n{text}"
            else:
                # SDK present but unknown interface — raise to fallback
                raise RuntimeError("Groq SDK present but client interface unrecognized in this environment.")
        except Exception as e:
            st.warning(f"Groq generation attempt failed: {e}. Falling back to local generator.")
            # fall through to deterministic fallback

    # Deterministic fallback itinerary generator (always available)
    # This returns a clear, human-readable itinerary built from distances and simple time heuristics.
    lines = []
    curr_time_minutes = 9 * 60  # start at 9:00 AM by default
    avg_speed_kmph = 20.0
    for idx, p in enumerate(ordered_pois, start=1):
        name = p.get("name", "unknown")
        addr = p.get("address", "")
        dist_km = (p.get("distance_m") or 0) / 1000.0
        # travel time from previous in minutes
        travel_min = int(max(1, (dist_km / avg_speed_kmph) * 60)) if idx > 1 else 0
        arrival_min = curr_time_minutes + travel_min
        # choose a suggested duration heuristically based on popularity
        pop = p.get("popularity")
        if pop is None:
            duration_min = 45
        else:
            try:
                pfloat = float(pop)
                if pfloat >= 8:
                    duration_min = 90
                elif pfloat >= 5:
                    duration_min = 60
                else:
                    duration_min = 40
            except:
                duration_min = 45
        # format times
        def fmt(mins):
            h = mins // 60
            m = mins % 60
            return f"{h:02d}:{m:02d}"
        arrival_str = fmt(arrival_min)
        depart_min = arrival_min + duration_min
        depart_str = fmt(depart_min)
        lines.append(f"{idx}. {name} — {addr}\n   Arrival: {arrival_str} — Duration: {duration_min} min — Depart: {depart_str}\n   Travel from previous: {travel_min} min\n   Why visit: Popularity ~ {p.get('popularity','—')}\n")
        curr_time_minutes = depart_min

    header = f"Deterministic itinerary (fallback). Start time ~09:00. Budget ₹{int(budget_total)} for {int(people_count)} people.\n\n"
    return header + "\n".join(lines)

# ---------------------------
# Card templates
# ---------------------------
CARD_COMPACT = """<div style="border:1px solid #eee;border-radius:8px;padding:8px;margin:6px;">
  <div style="font-weight:600">{name}</div>
  <div style="color:#666;font-size:12px">{address}</div>
  <div style="font-size:12px;margin-top:6px">Popularity: <b>{pop}</b> • Distance: <b>{dist}</b></div>
  <div style="margin-top:6px"><a href="{maps}" target="_blank">Open in Maps</a></div>
</div>"""

CARD_COMFORT = """<div style="border:1px solid #ddd;border-radius:10px;padding:12px;margin:8px;">
  <div style="font-size:16px;font-weight:700">{name}</div>
  <div style="color:#444;margin-top:6px">{address}</div>
  <div style="margin-top:8px">Popularity: <b>{pop}</b> • Distance: <b>{dist}</b></div>
  <div style="margin-top:8px"><a href="{maps}" target="_blank">Open in Google Maps</a></div>
</div>"""

# ---------------------------
# Session state initialization
# ---------------------------
if "results" not in st.session_state:
    st.session_state["results"] = []
if "start_coords" not in st.session_state:
    st.session_state["start_coords"] = None

# ---------------------------
# Button actions
# ---------------------------
if search_btn:
    perform_search()

if itinerary_btn:
    # If no prior results, run search first
    if not st.session_state.get("results"):
        perform_search()

    results_local = st.session_state.get("results", [])
    start_coords = st.session_state.get("start_coords")

    if not results_local:
        st.warning("No POIs found. Cannot generate itinerary.")
    elif not start_coords:
        st.error("Starting coordinates missing; cannot route.")
    else:
        lat0, lon0 = start_coords
        N = min(6, len(results_local))
        chosen = results_local[:N]
        ordered = order_route(chosen, lat0, lon0)

        st.subheader("Ordered Route")
        for i, p in enumerate(ordered, start=1):
            d = (p.get("distance_m") or 0) / 1000.0
            st.write(f"{i}. {p.get('name')} — {d:.2f} km from previous")

        # Attempt Groq generation (or fallback)
        try:
            with st.spinner("Generating itinerary (Groq / fallback)..."):
                itinerary_text = generate_itinerary_via_groq_or_fallback(ordered, budget, people)
            st.subheader("Generated Itinerary")
            st.markdown(itinerary_text)
        except Exception as e:
            st.error(f"Itinerary generation failed unexpectedly: {e}")
            st.info("Showing ordered route as fallback.")
            for i, p in enumerate(ordered, start=1):
                d = (p.get("distance_m") or 0) / 1000.0
                st.write(f"{i}. {p.get('name')} — {d:.2f} km — {p.get('address','')}")

# ---------------------------
# If previous results exist, display them
# ---------------------------
if st.session_state.get("results"):
    results_to_show = st.session_state["results"]
    st.subheader("Results")
    if show_map:
        left, right = st.columns([3, 1])
    else:
        left = st.container()
        right = None

    with left:
        cols = st.columns(n_columns)
        for i, r in enumerate(results_to_show):
            col = cols[i % n_columns]
            name = html_lib.escape(str(r.get("name", "")))
            address = html_lib.escape(str(r.get("address", "")))
            pop = r.get("popularity", "—")
            dist = f"{(r.get('distance_m') or 0)/1000:.2f} km" if r.get("distance_m") else "—"
            q = html_lib.escape(f"{r.get('name','')} {r.get('address','')}")
            maps = f"https://www.google.com/maps/search/?api=1&query={q}"
            card = CARD_COMPACT if layout_mode == "Compact" else CARD_COMFORT
            col.markdown(card.format(name=name, address=address, pop=pop, dist=dist, maps=maps), unsafe_allow_html=True)

    if right:
        st.write("Map")
        mp = [{"lat": r["lat"], "lon": r["lon"]} for r in results_to_show if r.get("lat") and r.get("lon")]
        if mp:
            st.map(pd.DataFrame(mp))
