# WeekendWish 🌆✨

**WeekendWish** is a location-based recommendation system that helps users discover nearby places in **Pune** and plan a budget-friendly weekend outing.
It supports **live API-based search** as well as **offline data fallback**, with an interactive UI and a REST API.

---

## 🚀 Features

* 📍 Nearby place discovery from a starting location
* 💰 Budget-based filtering (per person)
* ⭐ Popularity-based ranking
* 🗺️ Distance calculation & route ordering
* 🌐 Online (Foursquare + LocationIQ) & Offline (CSV) support
* 🖥️ Streamlit frontend + Flask backend API

---

## 🧠 Tech Stack

* **Python**
* **Streamlit** – UI
* **Flask** – REST API
* **Foursquare Places API (2025)**
* **LocationIQ**
* **OpenStreetMap (OSM)**
* Pandas, NumPy, Geopy

---

## 📂 Project Structure

```
weekendwish_updated/
│
├── streamlit_app.py        # Main Streamlit application
├── api_updated.py          # Flask API (/api/recommend)
├── api.py                  # API helper functions
├── extras.py               # Fallback helpers
├── scrape.py               # OSM data scraper
├── json_to_csv.py          # JSON → CSV processing
├── pune_processed.csv      # Offline dataset
│
├── static/
│   └── js/
│       └── app.js          # Frontend JS
│
├── templates/
│   └── nearby.html         # API demo UI
│
├── not-needed/
│   └── eda.ipynb           # Exploratory analysis
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ How to Run

### 1️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 2️⃣ Create `.env` file

```env
FSQ_SERVICE_KEY=your_foursquare_api_key
LOCATIONIQ_KEY=your_locationiq_key
```

### 3️⃣ Run Streamlit App (Recommended)

```bash
streamlit run streamlit_app.py
```

### 4️⃣ Run Flask API (Optional)

```bash
python api_updated.py
```

---

## 🔗 API Endpoint

**POST** `/api/recommend`

**Sample Input**

```json
{
  "budget": 2000,
  "people": 2,
  "start": "Kothrud, Pune",
  "radius": 8000
}
```

**Returns**

* Ranked nearby places with location, popularity & photos

---

## 🎯 Use Case

* College / academic project
* Location-based recommendation system
* Weekend outing planner

---

## 🔮 Future Scope

* ML-based personalization
* Multi-city support
* Time-aware itineraries
* User preference learning

---

