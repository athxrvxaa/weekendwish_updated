"""
api.py
Updated for NEW 2025 Foursquare Places API + Rate Limit Protection
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

FSQ_SERVICE_KEY = os.getenv("FSQ_SERVICE_KEY")
LOCATIONIQ_KEY = os.getenv("LOCATIONIQ_KEY")
FSQ_VERSION = "2025-06-17"  # required version header


# ----------------------------------------------------
# LocationIQ Geocoding
# ----------------------------------------------------
def geocode_address(address):
    if not LOCATIONIQ_KEY:
        print("LocationIQ key missing!")
        return None, None

    url = "https://us1.locationiq.com/v1/search"
    params = {
        "key": LOCATIONIQ_KEY,
        "q": f"{address}, Pune, Maharashtra, India",
        "format": "json",
        "limit": 1
    }

    try:
        r = requests.get(url, params=params, timeout=6)
        r.raise_for_status()
        data = r.json()
        if not data:
            return None, None
        return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        print("Geocoding failed:", e)
        return None, None


# ----------------------------------------------------
# Foursquare Search (NEW API, safe against 429)
# ----------------------------------------------------
def fsq_search_places(lat, lon, radius=8000, limit=10):
    """Safe FSQ search with minimal fields + new API rules."""
    if not FSQ_SERVICE_KEY:
        raise RuntimeError("FSQ_SERVICE_KEY missing in .env")

    url = "https://places-api.foursquare.com/places/search"

    headers = {
        "Authorization": f"Bearer {FSQ_SERVICE_KEY}",
        "Accept": "application/json",
        "X-Places-Api-Version": FSQ_VERSION
    }

    params = {
        "ll": f"{lat},{lon}",
        "radius": radius,
        "limit": limit,

        # ⭐ required to get name/categories/etc
        "fields": "fsq_place_id,name,categories,location,price,popularity"
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("Foursquare rate limit hit (429). Returning empty list.")
            return []
        print("FSQ Search Error:", e)
        return []
    except Exception as e:
        print("FSQ Search Error:", e)
        return []


# ----------------------------------------------------
# Extract coordinates from new API schema
# ----------------------------------------------------
def safe_get_main_coords(place):
    try:
        loc = place.get("location", {})
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        if lat is None:
            return None, None
        return float(lat), float(lon)
    except:
        return None, None


# ----------------------------------------------------
# Photo Fetching (NEW API)
# ----------------------------------------------------
def fsq_get_photo_url(fsq_place_id):
    if not FSQ_SERVICE_KEY:
        print("Missing FSQ SERVICE KEY")
        return None

    url = f"https://places-api.foursquare.com/places/{fsq_place_id}/photos"

    headers = {
        "Authorization": f"Bearer {FSQ_SERVICE_KEY}",
        "Accept": "application/json",
        "X-Places-Api-Version": FSQ_VERSION
    }

    try:
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code != 200:
            return None

        data = r.json()
        if not data:
            return None

        p = data[0]
        return f"{p['prefix']}original{p['suffix']}"

    except Exception:
        return None


# ----------------------------------------------------
# Photo fetcher for top N places
# ----------------------------------------------------
def fetch_photos_for_top_places(places, top_n=8):
    for p in places[:top_n]:
        pid = p.get("fsq_place_id")
        p["photo_url"] = fsq_get_photo_url(pid)
