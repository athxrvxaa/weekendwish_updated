import os
import requests
from dotenv import load_dotenv
from geopy.distance import geodesic

load_dotenv()
FSQ_API_KEY = os.getenv("FSQ_API_KEY")

# 1) Geocode via Nominatim (free)
def geocode_address(address):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": f"{address}, Pune, India", "format": "json", "limit": 1}
    r = requests.get(url, params=params, headers={"User-Agent":"WeekendWish/1.0"})
    r.raise_for_status()
    data = r.json()
    if not data:
        return None, None
    return float(data[0]["lat"]), float(data[0]["lon"])

# 2) Distance and travel-time approx (haversine via geopy)
def distance_km(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).km

def travel_time_min(lat1, lon1, lat2, lon2, avg_speed_kmph=20):
    dist = distance_km(lat1, lon1, lat2, lon2)
    return (dist / avg_speed_kmph) * 60

# 3) Foursquare: search places around a lat/lon
def fsq_search_places(lat, lon, radius=8000, limit=30, categories=None):
    """
    categories: comma-separated category ids or None to let FSQ return mixed results
    """
    url = "https://api.foursquare.com/v3/places/search"
    headers = {"Authorization": FSQ_API_KEY, "Accept": "application/json"}
    params = {
        "ll": f"{lat},{lon}",
        "radius": radius,
        "limit": limit
    }
    if categories:
        params["categories"] = categories
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json().get("results", [])

# 4) Foursquare: get a photo for a place (first photo)
def fsq_get_photo_url(fsq_id):
    url = f"https://api.foursquare.com/v3/places/{fsq_id}/photos"
    headers = {"Authorization": FSQ_API_KEY}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return None
    photos = resp.json()
    if not photos:
        return None
    p = photos[0]
    # Construct full URL: prefix + size + suffix (use "original" to be safe)
    return f"{p.get('prefix', '')}original{p.get('suffix', '')}"
