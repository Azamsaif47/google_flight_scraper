from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from flight_scraper import run_flight_scraper_async
import json

app = FastAPI()

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to your frontend's URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/flights")
async def get_flights(
    origin: str = Query(..., description="Origin airport code"),
    destination: str = Query(..., description="Destination airport code"),
    date: str = Query(..., description="Flight date in YYYY-MM-DD format")
):
    result = await run_flight_scraper_async(origin, destination, date)
    return result  # FastAPI will automatically convert dict to JSON