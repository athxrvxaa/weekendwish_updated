WeekendWish — updated package
Files added/updated:
- api_updated.py : original functions + Flask /api/recommend endpoint
- templates/nearby.html : simple demo UI
- static/js/app.js : frontend JS to call /api/recommend
- requirements_updated.txt : requirements with Flask & python-dotenv added

How to run:
1. Create .env with FSQ_SERVICE_KEY and LOCATIONIQ_KEY
2. pip install -r requirements_updated.txt
3. python api_updated.py
4. Open the nearby.html file via static server or integrate into your app.

Notes:
- api_updated.py contains a Flask app that uses functions already in api.py (geocoding / FSQ calls).
- If you prefer the route merged into your existing app, replace api.py with api_updated.py or copy the recommend_places function.
