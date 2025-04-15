import asyncio
import base64
import json
from typing import Dict, Optional
from playwright.async_api import async_playwright

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

async def _setup_browser():
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    return p, browser, page

async def _extract_text(el, selector: str, aria_label: Optional[str] = None) -> str:
    if aria_label:
        node = await el.query_selector(f'{selector}[aria-label*="{aria_label}"]')
    else:
        node = await el.query_selector(selector)
    return await node.inner_text() if node else "N/A"

async def _scrape_flight_info(flight) -> Dict[str, str]:
    departure_time = await _extract_text(flight, 'span', "Departure time")
    arrival_time   = await _extract_text(flight, 'span', "Arrival time")
    airline        = await _extract_text(flight, ".sSHqwe")
    duration       = await _extract_text(flight, "div.gvkrdb")
    stops          = await _extract_text(flight, "div.EfT7Ae span.ogfYpf")
    price          = await _extract_text(flight, "div.FpEdX span")
    co2            = await _extract_text(flight, "div.O7CXue")
    var            = await _extract_text(flight, "div.N6PNV")
    return {
        "Departure Time": departure_time,
        "Arrival Time":   arrival_time,
        "Airline Company":airline,
        "Flight Duration":duration,
        "Stops":           stops,
        "Price":           price,
        "co2 emissions":   co2,
        "emissions variation": var
    }

async def _fetch_first_nonstop(departure: str, destination: str, date: str) -> Dict[str, Optional[str]]:
    playwright, browser, page = await _setup_browser()
    try:
        url = FlightURLBuilder.build_url(departure, destination, date)
        await page.goto(url)
        await page.wait_for_selector(".pIav2d")
        flights = await page.query_selector_all(".pIav2d")
        for flight in flights:
            info = await _scrape_flight_info(flight)
            stops_text = info["Stops"].strip().lower()
            if "nonstop" in stops_text or stops_text in ("0 stops", "0"):
                return {"Flight Duration": info["Flight Duration"]}
        return {"Flight Duration": None}
    finally:
        await browser.close()
        await playwright.stop()

# Change the run_flight_scraper function to be async-friendly
async def run_flight_scraper_async(departure: str, destination: str, departure_date: str):
    """
    Asynchronous entry point. Returns flight duration data.
    """
    result = await _fetch_first_nonstop(departure, destination, departure_date)
    return result

