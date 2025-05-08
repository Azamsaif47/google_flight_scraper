import asyncio
import base64
import json
import re
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    """Set up Chrome browser for Docker environment"""
    options = Options()
    
    # Required options for running Chrome in Docker
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Set default download location to /tmp
    options.add_experimental_option("prefs", {
        "download.default_directory": "/tmp",
        "download.prompt_for_download": False,
    })

    # Chrome is installed through the Dockerfile, no need for ChromeDriverManager
    driver = webdriver.Chrome(options=options)
    return driver


def _extract_text(element, selector: str, aria_label: Optional[str] = None) -> str:
    try:
        if aria_label:
            node = element.find_element(By.CSS_SELECTOR, f'{selector}[aria-label*="{aria_label}"]')
        else:
            node = element.find_element(By.CSS_SELECTOR, selector)
        return node.text if node else "N/A"
    except:
        return "N/A"


def _extract_text_by_xpath(driver, xpath: str) -> str:
    try:
        node = driver.find_element(By.XPATH, xpath)
        return node.text if node else "N/A"
    except:
        return "N/A"


def _parse_duration_to_minutes(duration_str: str) -> int:
    if not duration_str or duration_str == "N/A":
        return 0
    hours = int(re.search(r'(\d+)\s*hr', duration_str).group(1)) if re.search(r'(\d+)\s*hr', duration_str) else 0
    minutes = int(re.search(r'(\d+)\s*min', duration_str).group(1)) if re.search(r'(\d+)\s*min', duration_str) else 0
    return hours * 60 + minutes


def _format_duration(minutes: int) -> str:
    if minutes == 0:
        return "N/A"
    hours = minutes // 60
    mins = minutes % 60
    parts = []
    if hours:
        parts.append(f"{hours} hr")
    if mins:
        parts.append(f"{mins} min")
    return ' '.join(parts)


def _get_number_of_stops(stops_text: str) -> int:
    if not stops_text or stops_text.lower().strip() == "n/a":
        return 999
    text = stops_text.lower()
    if "nonstop" in text or text.startswith('0'):
        return 0
    nums = re.findall(r'\d+', text)
    return int(nums[0]) if nums else 999


def _scrape_flight_info(driver, flight) -> Dict[str, str]:
    try:
        departure_time = _extract_text(flight, 'span', "Departure time")
        arrival_time = _extract_text(flight, 'span', "Arrival time")
        airline = _extract_text(flight, ".sSHqwe")
        duration = _extract_text(flight, "div.gvkrdb")
        if duration == "N/A":
            duration = _extract_text(flight, "div[role='cell'] > div > div > div")
        stops = _extract_text(flight, "div.EfT7Ae span.ogfYpf")
        price = _extract_text(flight, "div.FpEdX span")
        co2 = _extract_text(flight, "div.O7CXue")
        var = _extract_text(flight, "div.N6PNV")
        
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
    except Exception as e:
        print(f"Error in scrape_flight_info: {e}")
        return {
            "Departure Time": "N/A",
            "Arrival Time": "N/A",
            "Airline Company": "N/A",
            "Flight Duration": "N/A",
            "Stops": "N/A",
            "Price": "N/A",
            "co2 emissions": "N/A",
            "emissions variation": "N/A"
        }


def _calculate_roundtrip_duration(one_way: str) -> str:
    mins = _parse_duration_to_minutes(one_way)
    return _format_duration(mins * 2)


def _fetch_best_flight(departure: str, destination: str, date: str) -> Dict[str, Optional[str]]:
    driver = _setup_browser()
    try:
        url = FlightURLBuilder.build_url(departure, destination, date)
        driver.get(url)
        
        # Increased timeout for better chance of loading
        wait = WebDriverWait(driver, 60)
        
        # Wait for flights to load - same selector for both nonstop and stops
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".pIav2d")))
            # Add a short delay to ensure all content is loaded
            time.sleep(3)
        except Exception as e:
            print(f"Error waiting for page to load: {e}")
            return {"One Way Duration": None, "Roundtrip Duration": None, "Stops": None, "Error": "Timeout loading flights"}
        
        # Get all flights
        flights = driver.find_elements(By.CSS_SELECTOR, ".pIav2d")
        
        # Handle case with no flights found
        if not flights:
            print("No flights found")
            return {"One Way Duration": None, "Roundtrip Duration": None, "Stops": None, "Error": "No flights found"}
        
        print(f"Found {len(flights)} flights")
        
        # First look for nonstop flights
        for flight in flights:
            info = _scrape_flight_info(driver, flight)
            if _get_number_of_stops(info['Stops']) == 0:
                one_way = info['Flight Duration']
                if one_way != "N/A":
                    print(f"Found nonstop flight with duration: {one_way}")
                    return {"One Way Duration": one_way, "Roundtrip Duration": _calculate_roundtrip_duration(one_way), "Stops": "Nonstop"}
        
        # If no nonstop flight found, find the flight with the fewest stops
        best_flight = None
        min_stops = 999
        
        for flight in flights:
            info = _scrape_flight_info(driver, flight)
            stops = _get_number_of_stops(info['Stops'])
            if stops < min_stops and info['Flight Duration'] != "N/A":
                min_stops = stops
                best_flight = info
        
        if best_flight:
            one_way = best_flight['Flight Duration']
            stops_text = best_flight['Stops']
            print(f"Best flight found: {one_way} with {stops_text}")
            return {"One Way Duration": one_way, "Roundtrip Duration": _calculate_roundtrip_duration(one_way), "Stops": stops_text}
        
        # If we couldn't find a valid flight with duration, return error
        return {"One Way Duration": None, "Roundtrip Duration": None, "Stops": None, "Error": "Could not find flight duration"}
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"One Way Duration": None, "Roundtrip Duration": None, "Stops": None, "Error": str(e)}
    finally:
        try:
            driver.quit()
        except:
            pass  # Ignore errors when closing the browser


def run_flight_scraper(departure: str, destination: str, departure_date: str) -> Dict[str, Optional[str]]:
    """
    Synchronous entry point. Returns flight duration data.
    """
    return _fetch_best_flight(departure, destination, departure_date)


async def run_flight_scraper_async(departure: str, destination: str, departure_date: str) -> Dict[str, Optional[str]]:
    """
    Asynchronous entry point that wraps the synchronous function in a thread.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        run_flight_scraper,
        departure,
        destination,
        departure_date
    )