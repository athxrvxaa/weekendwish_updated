# WeekendWish 🌆✨

**WeekendWish** is a smart local outing recommendation system that helps users discover nearby places and plan a budget-friendly weekend itinerary in **Pune**.
It combines **live location data**, **offline datasets**, and **popularity-based ranking** to suggest the best places around you.

---

## 🚀 Features

* 📍 Find nearby places based on starting location
* 💰 Budget-aware recommendations (per person)
* ⭐ Popularity-based ranking of places
* 🗺️ Distance & route optimization
* 🌐 Works **online (Foursquare API)** and **offline (CSV fallback)**
* 🖥️ Interactive UI built with **Streamlit**
* 🔌 REST API using **Flask**

---

## 🧠 Tech Stack

* **Python**
* **Streamlit** – Frontend UI
* **Flask** – Backend API (`/api/recommend`)
* **Foursquare Places API (2025)**
* **LocationIQ** – Geocoding
* **OpenStreetMap (OSM)** – Offline data
* **Pandas, NumPy, Geopy**

---

## 📂 Project Structure

```
├── streamlit_app.py      # Main Streamlit app
├── api_updated.py        # Flask API backend
├── api.py / extras.py    # Helper functions (geocoding, FSQ)
├── scrape.py             # OSM data scraper
├── json_to_csv.py        # Data preprocessing
├── pune_processed.csv    # Offline dataset
├── requirements.txt
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

### 4️⃣ Run API (Optional)

```bash
python api_updated.py
```

---

## 🔗 API Endpoint

**POST** `/api/recommend`

**Input**

```json
{
  "budget": 2000,
  "people": 2,
  "start": "Kothrud, Pune",
  "radius": 8000
}
```

**Output**

* Recommended places with name, location, popularity & photos

---

## 🎯 Use Case

* College project / evaluation
* Weekend planning app
* Location-based recommendation systems

---

## 🔮 Future Improvements

* ML-based personalization
* Time-based itinerary planning
* Multi-city support
* User preferences & history

---

