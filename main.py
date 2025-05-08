from fastapi import FastAPI, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from flight_scraper import run_flight_scraper_async
from new_check import get_highest_price

app = FastAPI(
    title="Flight Information API",
    description="API to get flight duration and price information for specific routes",
    version="1.0.0"
)

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to your frontend's URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/flights/duration")
async def get_flights_duration(
    origin: str = Query(..., description="Origin airport code (e.g., LAX)"),
    destination: str = Query(..., description="Destination airport code (e.g., JFK)"),
    date: str = Query(..., description="Flight date in YYYY-MM-DD format (e.g., 2025-05-20)")
):
    """
    Retrieve flight duration information for a specific route.
    
    Returns both one-way and roundtrip flight durations.
    """
    # Input validation
    if len(origin) != 3 or not origin.isalpha():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Origin must be a valid 3-letter airport code"
        )
    
    if len(destination) != 3 or not destination.isalpha():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Destination must be a valid 3-letter airport code"
        )
    
    # Date format validation could be added here
    
    result = await run_flight_scraper_async(origin.upper(), destination.upper(), date)
    
    # Handle errors from scraper
    if result.get("Error"):
        error_message = result.get("Error")
        if "Timeout" in error_message:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Timeout while fetching flight information. Please try again later."
            )
        elif "No flights found" in error_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No flights found for route {origin}-{destination} on {date}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching flight information: {error_message}"
            )
    
    # Check if we have actual flight duration data
    if not result.get("One Way Duration"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not retrieve flight duration for {origin} to {destination} on {date}"
        )
    
    return result

@app.get("/flights/prices")
async def get_flight_prices(
    departure: str = Query(..., description="Departure airport code (e.g., LAX)"),
    arrival: str = Query(..., description="Arrival airport code (e.g., JFK)"),
    month: str = Query(..., description="Month for price check (e.g., May)")
):
    """
    Retrieve the highest flight price for a specific route during a given month.
    """
    # Input validation - similar to the duration endpoint
    if len(departure) != 3 or not departure.isalpha():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Departure must be a valid 3-letter airport code"
        )
    
    if len(arrival) != 3 or not arrival.isalpha():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arrival must be a valid 3-letter airport code"
        )
    
    try:
        price = await get_highest_price(
            departure=departure.upper(),
            arrival=arrival.upper(),
            target_month=month,
            headless=True  # Set to False for debugging
        )
        
        if price > 0:
            return {
                "departure": departure.upper(),
                "arrival": arrival.upper(),
                "month": month,
                "highest_price": price
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Could not find price data"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching flight price information: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)