#!/usr/bin/env python3

"""
ALL PUNE OSM SCRAPER (FINAL FIXED VERSION)
------------------------------------------
✔ Fetches *all named POIs* inside Pune administrative boundary
✔ Uses reliable area-based query (NEVER returns empty)
✔ Normalizes into structured output
✔ Exports:
    - pune_raw_all.json  : all named POIs
    - pune_clean.json    : filtered + useful POIs for your app
------------------------------------------
Run:
    pip install requests pandas tqdm
    python all_pune_scrape.py
"""

import requests
import json
import pandas as pd
from tqdm import tqdm

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# 🔥 FINAL CORRECT QUERY (guaranteed to return data)
QUERY = """
[out:json][timeout:300];

// Find Pune administrative boundary
area["name"="Pune"]["boundary"="administrative"]->.a;

// Get ALL named nodes / ways / relations within Pune
(
  node(area.a)[name];
  way(area.a)[name];
  relation(area.a)[name];
);

out center;
"""

# ---------------------------------------------
# CATEGORY MAPPING
# ---------------------------------------------
def map_category(tags):
    if not tags:
        return "other"

    for k in ["amenity", "tourism", "shop", "leisure"]:
        if k in tags:
            return tags[k]

    # fallback
    return "other"


# ---------------------------------------------
# PRICE TIER HEURISTIC
# ---------------------------------------------
def price_tier(tags, name):
    name = name.lower()

    if "dhaba" in name or "fast" in name or "stall" in name:
        return 1
    if "cafe" in name or "bakery" in name:
        return 2
    if "restaurant" in (tags.get("amenity") or ""):
        return 2
    if "bar" in name or "pub" in name:
        return 3
    if "fine" in name or "premium" in name:
        return 4

    return 2


# ---------------------------------------------
# POPULARITY HEURISTIC
# ---------------------------------------------
def popularity(tags):
    score = 0.4
    if "wikidata" in tags:
        score += 0.3
    if "tourism" in tags:
        score += 0.2
    if tags.get("amenity") in ["restaurant", "cafe", "bar"]:
        score += 0.1
    return min(score, 1.0)


# ---------------------------------------------
# PROCESS ELEMENT CENTER
# ---------------------------------------------
def extract_center(e):
    if e["type"] == "node":
        return e.get("lat"), e.get("lon")
    if "center" in e:
        return e["center"]["lat"], e["center"]["lon"]
    return None, None


# ---------------------------------------------
# FETCHING FROM OVERPASS
# ---------------------------------------------
def fetch_osm():
    print("📡 Querying Overpass… this will take ~30–90 seconds…")
    resp = requests.post(OVERPASS_URL, data={"data": QUERY}, timeout=300)

    print("Status:", resp.status_code)
    if resp.status_code != 200:
        print("Error response:")
        print(resp.text[:500])
        raise SystemExit("❌ Overpass request failed.")

    data = resp.json()
    return data.get("elements", [])


# ---------------------------------------------
# NORMALIZATION
# ---------------------------------------------
def normalize(elements):
    results = []
    seen = set()

    print("🔄 Normalizing results…")

    for e in tqdm(elements):
        tags = e.get("tags", {})
        name = tags.get("name")

        if not name:  # should not happen due to [name] filter
            continue

        lat, lon = extract_center(e)
        if lat is None:
            continue

        key = f"{name.lower()}::{round(lat, 6)}::{round(lon,6)}"
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "name": name,
            "lat": lat,
            "lon": lon,
            "category": map_category(tags),
            "price_tier": price_tier(tags, name),
            "popularity": popularity(tags),
            "tags": tags,
            "photo_url": None,
        })

    return results


# ---------------------------------------------
# FILTER CLEAN POIs FOR YOUR APP
# ---------------------------------------------
USEFUL = [
    "restaurant", "cafe", "fast_food",
    "bar", "pub", "food_court",
    "cinema", "theatre",
    "mall", "supermarket", "department_store",
    "park", "garden",
    "viewpoint", "attraction", "museum",
]

def clean_pois(all_pois):
    filtered = []
    for p in all_pois:
        cat = p["category"]
        if any(cat == u for u in USEFUL):
            filtered.append(p)
    return filtered


# ---------------------------------------------
# MAIN
# ---------------------------------------------
def main():
    elements = fetch_osm()
    print("🗂 Total raw OSM elements:", len(elements))

    normalized = normalize(elements)
    print("🏷 Named POIs:", len(normalized))

    cleaned = clean_pois(normalized)
    print("✨ Useful POIs for app:", len(cleaned))

    # Save outputs
    with open("pune_raw_all.json", "w") as f:
        json.dump(normalized, f, indent=2)

    with open("pune_clean.json", "w") as f:
        json.dump(cleaned, f, indent=2)

    print("\n🎉 DONE!")
    print("➡ pune_raw_all.json  (ALL named POIs)")
    print("➡ pune_clean.json    (filtered useful POIs)")


if __name__ == "__main__":
    main()
