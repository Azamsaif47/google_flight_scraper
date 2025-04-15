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
   [http://localhost:8000/docs](http://localhost:5000/docs)
3. Test the available API endpoint:
   - `GET /airports` – List all airports
   - `GET /airport/{iataCode}` – Get details for a specific airport
   - `GET /distance/from={from}&to={to}` – Calculate distance between two airports
4. Use the **"Try it out"** button on Swagger to interact with each endpoint.
5. Input 3-letter **IATA codes** (e.g., `JFK`, `LAX`) as parameters.
6. Click **Execute** to get the distance result in the **Response Body**.