# streamlit_app.py
"""
Streamlit UI for WeekendWish — compact grid layout with searchable category selector
- Adds a searchable dropdown for category (type-ahead via Streamlit selectbox)
- Category filters are applied in both online (Foursquare) and offline (CSV) searches
- Compact/Comfortable views, grid columns, map panel remain as before
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

# Page config
st.set_page_config(page_title="WeekendWish", layout="wide")
st.title("WeekendWish — Find popular places nearby")

# Category options (adjust/extend as needed)
CATEGORIES = [
    "any", "restaurant", "cafe", "bar", "pub", "fast_food", "bakery",
    "park", "garden", "museum", "theatre", "cinema", "mall",
    "supermarket", "viewpoint", "attraction", "historical", "monument",
    "temple", "church", "mosque", "zoo", "aquarium", "library",
    "nightclub", "food_court", "ice_cream", "dessert", "street_food",
    "art_gallery", "market", "stadium", "hiking", "beach", "lake",
    "river", "campground", "playground", "amusement_park"
]

# Controls row
with st.container():
    cols = st.columns([3, 1, 1])
    with cols[0]:
        start_input = st.text_input("Starting location (address or lat,lng)", value="Kothrud, Pune")
    with cols[1]:
        data_mode = st.selectbox("Data source", ["Auto (online then offline)", "Foursquare (online)", "Offline CSV"])
    with cols[2]:
        layout_mode = st.selectbox("View", ["Compact", "Comfortable"], index=0)

# Category selectbox: supports type-ahead searching
category = st.selectbox("Category (start typing to search)", CATEGORIES, index=0, help="Type to search categories; choose 'any' to disable category filtering")

col_a, col_b = st.columns([1, 1])
with col_a:
    budget = st.number_input("Budget (total)", min_value=0.0, value=2000.0, step=100.0)
with col_b:
    people = st.number_input("People", min_value=1, value=2, step=1)

radius = st.slider("Search radius (meters)", min_value=1000, max_value=30000, value=8000, step=500)

# Extra small options
with st.expander("Advanced options (compact)"):
    n_columns = st.selectbox("Grid columns", [1, 2, 3], index=1, help="How many cards per row on wide screens")
    show_map = st.checkbox("Show map panel", value=True)
    sort_by = st.selectbox("Sort by", ["popularity", "distance"], index=0)

run_btn = st.button("Find places")

# Helpers
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

def travel_time_minutes(distance_km, avg_speed_kmph=20):
    try:
        return (distance_km / avg_speed_kmph) * 60
    except:
        return None

def matches_category_offline(row, category_selected):
    """
    Determine whether an offline CSV row matches the selected category.
    - checks 'category' column (exact or contains)
    - falls back to 'tags' column (string contains)
    """
    if not category_selected or category_selected == "any":
        return True
    # check category column
    cat_col = None
    if "category" in row.index:
        cat_col = row.get("category")
        if isinstance(cat_col, str) and category_selected.lower() in cat_col.lower():
            return True
    # fallback to 'tags'
    if "tags" in row.index:
        tags = row.get("tags") or ""
        if isinstance(tags, str) and category_selected.lower() in tags.lower():
            return True
    # also try name heuristics
    name = row.get("name") or ""
    if isinstance(name, str) and category_selected.lower() in name.lower():
        return True
    return False

def matches_category_online(place_obj, category_selected):
    """
    Check FSQ place categories list for a match.
    Each 'category' in FSQ may be dicts with 'name'.
    """
    if not category_selected or category_selected == "any":
        return True
    cats = place_obj.get("categories") or []
    for c in cats:
        # c might be dict or string
        if isinstance(c, dict):
            nm = c.get("name") or ""
        else:
            nm = str(c)
        if category_selected.lower() in nm.lower():
            return True
    # also inspect the 'categories' short names or 'tags' fallback
    # check name
    name = place_obj.get("name") or ""
    if isinstance(name, str) and category_selected.lower() in name.lower():
        return True
    return False

def search_offline(lat, lon, radius_m, budget_pp, top_n=50, category_selected="any"):
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

    df["distance_m"] = df.apply(lambda r: dist_m(r), axis=1)
    df = df[df["distance_m"] <= radius_m].copy()

    price_col = "price_tier" if "price_tier" in df.columns else ("price" if "price" in df.columns else None)
    pop_col = "popularity" if "popularity" in df.columns else None

    # category filtering
    if category_selected and category_selected != "any":
        # apply the matches_category_offline row-wise
        df = df[df.apply(lambda row: matches_category_offline(row, category_selected), axis=1)]

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

def search_online(lat, lon, radius_m, budget_pp, top_n=50, category_selected="any"):
    if ONLINE_HELPERS is None:
        raise RuntimeError("Online helpers not available.")
    raw = fsq_search_places(lat, lon, radius=radius_m, limit=60)
    max_price = budget_to_price_level(budget_pp)
    cleaned = []
    for p in raw:
        # category filter
        if category_selected and category_selected != "any":
            try:
                if not matches_category_online(p, category_selected):
                    continue
            except Exception:
                # if any error in checking, be conservative and include
                pass

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

# Compact card HTML templates
CARD_COMPACT = """
<div style="
  border:1px solid rgba(255,255,255,0.06);
  border-radius:8px;
  padding:8px 10px;
  margin:6px;
  background: rgba(0,0,0,0.02);
">
  <div style="font-size:15px;font-weight:600;margin-bottom:4px;">{name}</div>
  <div style="font-size:12px;color:#6c757d;margin-bottom:6px;">{address}</div>
  <div style="font-size:12px;color:#333">Popularity: <strong>{pop}</strong> &nbsp; • &nbsp; Distance: <strong>{dist}</strong></div>
  <div style="margin-top:6px;font-size:12px;"><a href="{maps}" target="_blank">Open in Maps</a></div>
</div>
"""

CARD_COMFORT = """
<div style="
  border:1px solid #e6e6e6;
  border-radius:10px;
  padding:12px;
  margin:8px 6px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
">
  <div style="font-size:18px;font-weight:600;margin-bottom:6px;">{name}</div>
  <div style="color:#555;margin-bottom:6px;">{address}</div>
  <div style="font-size:13px;color:#333">Popularity: <strong>{pop}</strong> &nbsp;&nbsp; Distance: <strong>{dist}</strong></div>
  <div style="margin-top:8px"><a href="{maps}" target="_blank">Open in Google Maps</a></div>
</div>
"""

# Main action
if run_btn:
    lat0, lon0 = parse_latlng(start_input)
    if lat0 is None or lon0 is None:
        try:
            lat0, lon0 = geocode_address(start_input)
        except Exception as e:
            st.error("Geocoding failed: " + str(e))
            lat0 = lon0 = None

    if lat0 is None:
        st.error("Couldn't determine starting coordinates. Try lat,lng or check geocoding keys.")
    else:
        st.info(f"Searching around {lat0:.6f}, {lon0:.6f} within {radius} meters ...")
        budget_pp = float(budget) / max(1, int(people))

        # get results according to mode
        results = []
        try:
            if data_mode == "Auto (online then offline)":
                if ONLINE_HELPERS:
                    try:
                        results = search_online(lat0, lon0, radius, budget_pp, top_n=80, category_selected=category)
                        if not results:
                            results = search_offline(lat0, lon0, radius, budget_pp, top_n=80, category_selected=category)
                    except Exception as e:
                        st.warning("Online search failed; falling back to offline. (" + str(e) + ")")
                        results = search_offline(lat0, lon0, radius, budget_pp, top_n=80, category_selected=category)
                else:
                    results = search_offline(lat0, lon0, radius, budget_pp, top_n=80, category_selected=category)
            elif data_mode == "Foursquare (online)":
                if not ONLINE_HELPERS:
                    st.error("Online helper functions not found. Falling back to offline.")
                    results = search_offline(lat0, lon0, radius, budget_pp, top_n=80, category_selected=category)
                else:
                    results = search_online(lat0, lon0, radius, budget_pp, top_n=80, category_selected=category)
            else:
                results = search_offline(lat0, lon0, radius, budget_pp, top_n=80, category_selected=category)
        except Exception as e:
            st.error("Search failed: " + str(e))
            results = []

        if not results:
            st.write("No places found.")
        else:
            # optional sort
            if sort_by == "popularity":
                results = sorted(results, key=lambda x: x.get("popularity") or 0, reverse=True)
            else:
                results = sorted(results, key=lambda x: x.get("distance_m") or 1e9)

            # Layout: optional map column
            if show_map:
                left_col, right_col = st.columns([3, 1])
            else:
                left_col = st.container()
                right_col = None

            # Prepare map data list
            map_points = []

            # Render grid in left_col
            with left_col:
                ncols = max(1, int(n_columns))
                grid_cols = st.columns(ncols)
                for idx, r in enumerate(results):
                    col_idx = idx % ncols
                    c = grid_cols[col_idx]
                    name = html_lib.escape(r.get("name") or "")
                    address = html_lib.escape(r.get("address") or "")
                    pop_text = html_lib.escape(str(r.get("popularity") if r.get("popularity") is not None else "—"))
                    dist_km = (r.get("distance_m") or 0) / 1000.0
                    dist_text = f"{dist_km:.2f} km" if r.get("distance_m") is not None else "—"
                    maps_q = html_lib.escape(f"{r.get('name','')} {r.get('address','')}")
                    maps_url = f"https://www.google.com/maps/search/?api=1&query={maps_q}"

                    card_html = CARD_COMPACT.format(name=name, address=address, pop=pop_text, dist=dist_text, maps=maps_url) \
                        if layout_mode == "Compact" else CARD_COMFORT.format(name=name, address=address, pop=pop_text, dist=dist_text, maps=maps_url)

                    c.markdown(card_html, unsafe_allow_html=True)
                    with c.expander("Details"):
                        st.write("**Name:**", r.get("name"))
                        if r.get("address"):
                            st.write("**Address:**", r.get("address"))
                        st.write("**Popularity:**", r.get("popularity"))
                        if r.get("distance_m") is not None:
                            st.write("**Distance:**", f"{(r.get('distance_m')/1000):.2f} km")
                            eta = travel_time_minutes((r.get("distance_m")/1000.0), avg_speed_kmph=20)
                            if eta is not None:
                                st.write("**Approx travel time:**", f"{int(eta)} min (by road, ~20 km/h)")

                    if r.get("lat") and r.get("lon"):
                        map_points.append({"lat": r["lat"], "lon": r["lon"], "name": r["name"]})

            # Render map in right column if enabled
            if right_col is not None:
                with right_col:
                    st.write("Map")
                    try:
                        if map_points:
                            map_df = pd.DataFrame(map_points)
                            st.map(map_df)
                        else:
                            st.write("No map points to show.")
                    except Exception as e:
                        st.write("Map error:", e)

# end main
