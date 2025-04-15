# ✈️ Airports Flight Duration API

A Fast Api that gives you the one way flight duration of specific route and the roundtrip flight duration of that specific route

---

## 🚀 Features

- Retrieve a 2 objects 
1. one way flight duration time.
2. roundtrip flight duration time.

---

## 🛠️ Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/Azamsaif47/google_flight_scraper.git
   ```

2. **Navigate to the project directory:**

   ```bash
   cd google_flight_scraper
   ```

3. **Run with Docker Compose:**

   ```bash
   docker-compose up
   ```

---

## 📡 Usage

1. Ensure the project is running.
2. Open your browser and go to:  
   [http://localhost:5001/docs](http://localhost:5001/docs)
3. Test the available API endpoint:
   - `GET /flights` – gives the one way trip and roudtrip data of route
   - Query params = origin , destination and date 

   