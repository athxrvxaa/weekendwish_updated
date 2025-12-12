# api_updated.py
"""
Flask wrapper for WeekendWish:
- imports geocoding & FSQ helper functions from your api.py/extras.py
- exposes POST /api/recommend
- enables CORS and serves the demo UI at '/'
"""

import os
from math import log1p
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Import the helper functions from your existing code
# Your repo already has functions: geocode_address, fsq_search_places, safe_get_main_coords, fsq_get_photo_url
# They are defined in api.py and extras.py — we import them here (adjust imports if you put them elsewhere)
try:
    # If your helper functions are in top-level api.py
    from api import geocode_address, fsq_search_places, safe_get_main_coords, fsq_get_photo_url
except Exception:
    # fallback to extras
    from extras import geocode_address, fsq_search_places, safe_get_main_coords, fsq_get_photo_url

app = Flask(__name__, static_folder="static")
CORS(app)

@app.route("/", methods=["GET"])
def serve_ui():
    # Serve demo page that lives in templates/nearby.html
    return send_from_directory("templates", "nearby.html")


@app.route("/api/recommend", methods=["POST"])
def recommend_places():
    """
    Expects JSON:
    {
      "budget": <number>,      # total budget (currency units)
      "people": <int>,
      "start": "Address" or "lat,lng",
      "radius": optional radius in meters (default 8000)
    }

    Returns:
      JSON with list of recommended places (top 10-12)
    """
    data = request.get_json() or {}
    try:
        budget = float(data.get("budget", 0) or 0)
    except:
        budget = 0.0
    try:
        people = int(data.get("people", 1) or 1)
    except:
        people = 1

    start = data.get("start")
    radius = int(data.get("radius", 8000))

    if not start:
        return jsonify({"error": "starting location missing"}), 400

    # Parse "lat,lng" if provided
    lat = lon = None
    if isinstance(start, str) and "," in start:
        parts = [s.strip() for s in start.split(",")]
        if len(parts) >= 2:
            try:
                lat = float(parts[0]); lon = float(parts[1])
            except Exception:
                lat = lon = None

    if lat is None or lon is None:
        lat, lon = geocode_address(start)
    if lat is None or lon is None:
        return jsonify({"error": "Could not geocode starting location"}), 400

    # Call Foursquare search (or your configured search function)
    raw_places = []
    try:
        raw_places = fsq_search_places(lat, lon, radius=radius, limit=40)
    except Exception as e:
        # Return a helpful error while keeping endpoint alive
        return jsonify({"error": "Foursquare search failed", "details": str(e)}), 500

    budget_per_person = budget / max(1, people)

    # Map budget per person -> allowed FSQ price level
    def allowed_price_level(budget_pp):
        # Tweak these thresholds to match your currency / area
        if budget_pp < 200:
            return 1
        elif budget_pp < 500:
            return 2
        elif budget_pp < 1200:
            return 3
        return 4

    max_price_lvl = allowed_price_level(budget_per_person)

    cleaned = []
    for p in raw_places:
        pid = p.get("fsq_place_id") or p.get("fsq_id") or p.get("fsqId") or p.get("id")
        name = p.get("name")
        price = p.get("price")  # FSQ returns price or None
        popularity = p.get("popularity") or 0
        lat2, lon2 = safe_get_main_coords(p)
        location = p.get("location") or {}

        # Budget filter (if price present)
        if (price is not None) and (isinstance(price, (int, float)) and price > max_price_lvl):
            continue

        # Popularity-based score
        try:
            score = float(popularity) * log1p(float(popularity or 0))
        except Exception:
            score = float(popularity or 0)

        cleaned.append({
            "id": pid,
            "name": name,
            "price": price,
            "popularity": popularity,
            "score": score,
            "lat": lat2,
            "lon": lon2,
            "address": location.get("formatted_address") or location.get("address") or location.get("locality")
        })

    # Sort and keep top 12
    cleaned.sort(key=lambda x: x.get("score", 0), reverse=True)
    top = cleaned[:12]

    # attach photos (best-effort)
    for item in top:
        try:
            if item.get("id"):
                item["photo"] = fsq_get_photo_url(item["id"])
            else:
                item["photo"] = None
        except Exception:
            item["photo"] = None

    return jsonify({
        "start_coords": {"lat": lat, "lon": lon},
        "budget_per_person": budget_per_person,
        "results": top
    })


if __name__ == "__main__":
    # Running as script: start Flask dev server
    # Note: dev server is fine for testing locally
    app.run(host="0.0.0.0", port=5000, debug=True)
