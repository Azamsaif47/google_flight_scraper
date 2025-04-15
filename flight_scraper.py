import asyncio
import base64
import json
import re
from typing import Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

class FlightURLBuilder:
    """Class to handle flight URL creation with base64 encoding."""
    
    @staticmethod
    def _create_one_way_bytes(departure: str, destination: str, date: str) -> bytes:
        return (
            b'\x08\x1c\x10\x02\x1a\x1e\x12\n' + date.encode() +
            b'j\x07\x08\x01\x12\x03' + departure.encode() +
            b'r\x07\x08\x01\x12\x03' + destination.encode() +
            b'@\x01H\x01p\x01\x82\x01\x0b\x08\xfc\x06`\x04\x08'
        )
    
    @staticmethod
    def _modify_base64(encoded_str: str) -> str:
        insert_index = len(encoded_str) - 6
        return encoded_str[:insert_index] + '_' * 7 + encoded_str[insert_index:]

    @classmethod
    def build_url(cls, departure: str, destination: str, departure_date: str) -> str:
        flight_bytes = cls._create_one_way_bytes(departure, destination, departure_date)
        base64_str = base64.b64encode(flight_bytes).decode('utf-8')
        modified_str = cls._modify_base64(base64_str)
        return f'https://www.google.com/travel/flights/search?tfs={modified_str}'

def _setup_browser():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Use webdriver_manager to handle driver installation
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    return driver

def _extract_text(driver, element, selector: str, aria_label: Optional[str] = None) -> str:
    try:
        if aria_label:
            node = element.find_element(By.CSS_SELECTOR, f'{selector}[aria-label*="{aria_label}"]')
        else:
            node = element.find_element(By.CSS_SELECTOR, selector)
        return node.text if node else "N/A"
    except:
        return "N/A"

def _scrape_flight_info(driver, flight) -> Dict[str, str]:
    departure_time = _extract_text(driver, flight, 'span', "Departure time")
    arrival_time = _extract_text(driver, flight, 'span', "Arrival time")
    airline = _extract_text(driver, flight, ".sSHqwe")
    duration = _extract_text(driver, flight, "div.gvkrdb")
    stops = _extract_text(driver, flight, "div.EfT7Ae span.ogfYpf")
    price = _extract_text(driver, flight, "div.FpEdX span")
    co2 = _extract_text(driver, flight, "div.O7CXue")
    var = _extract_text(driver, flight, "div.N6PNV")
    
    return {
        "Departure Time": departure_time,
        "Arrival Time": arrival_time,
        "Airline Company": airline,
        "Flight Duration": duration,
        "Stops": stops,
        "Price": price,
        "co2 emissions": co2,
        "emissions variation": var
    }

def _calculate_roundtrip_duration(one_way_duration: str) -> str:
    """
    Calculate the roundtrip duration by doubling the one-way duration.
    Input format could be like "1 hr 25 min" or "2 hr" or "45 min"
    """
    if one_way_duration == "N/A" or not one_way_duration:
        return "N/A"
    
    # Extract hours and minutes using regex
    hours_match = re.search(r'(\d+)\s*hr', one_way_duration)
    minutes_match = re.search(r'(\d+)\s*min', one_way_duration)
    
    hours = int(hours_match.group(1)) if hours_match else 0
    minutes = int(minutes_match.group(1)) if minutes_match else 0
    
    # Calculate total minutes for roundtrip
    total_minutes = 2 * (hours * 60 + minutes)
    
    # Convert back to hr/min format
    roundtrip_hours = total_minutes // 60
    roundtrip_minutes = total_minutes % 60
    
    # Format the result
    result = ""
    if roundtrip_hours > 0:
        result += f"{roundtrip_hours} hr"
    if roundtrip_minutes > 0:
        if result:
            result += " "
        result += f"{roundtrip_minutes} min"
    
    return result if result else "N/A"

def _fetch_first_nonstop(departure: str, destination: str, date: str) -> Dict[str, Optional[str]]:
    driver = _setup_browser()
    try:
        url = FlightURLBuilder.build_url(departure, destination, date)
        driver.get(url)
        
        # Wait for flights to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".pIav2d"))
        )
        
        flights = driver.find_elements(By.CSS_SELECTOR, ".pIav2d")
        
        for flight in flights:
            info = _scrape_flight_info(driver, flight)
            stops_text = info["Stops"].strip().lower()
            if "nonstop" in stops_text or stops_text in ("0 stops", "0"):
                one_way_duration = info["Flight Duration"]
                roundtrip_duration = _calculate_roundtrip_duration(one_way_duration)
                return {
                    "One Way Duration": one_way_duration,
                    "Roundtrip Duration": roundtrip_duration
                }
        
        return {
            "One Way Duration": None,
            "Roundtrip Duration": None
        }
    finally:
        driver.quit()

# Create a synchronous version for direct usage
def run_flight_scraper(departure: str, destination: str, departure_date: str):
    """
    Synchronous entry point. Returns flight duration data.
    """
    return _fetch_first_nonstop(departure, destination, departure_date)

# Create an async wrapper for FastAPI
async def run_flight_scraper_async(departure: str, destination: str, departure_date: str):
    """
    Asynchronous entry point that wraps the synchronous function in a thread.
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, 
        run_flight_scraper, 
        departure, 
        destination, 
        departure_date
    )
    return result