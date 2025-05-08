import base64
import asyncio
import re
from datetime import datetime
from playwright.async_api import async_playwright

def construct_flight_url(departure: str, arrival: str):
    binary_data = (
        b'\x08\x1c\x10\x01'
        b'\x1a\x12j\x07\x08\x01\x12\x03' + departure.encode() +
        b'r\x07\x08\x01\x12\x03' + arrival.encode() +
        b'\x1a\x12j\x07\x08\x01\x12\x03' + arrival.encode() +
        b'r\x07\x08\x01\x12\x03' + departure.encode() +
        b'@\x01H\x01p\x01\x82\x01\x0b'
        b'\x08\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01\x98\x01\x01'
    )
    encoded = base64.urlsafe_b64encode(binary_data).decode().rstrip('=')
    return f"https://www.google.com/travel/flights?tfs={encoded}&tfu=KgIIAw&hl=en-US&gl=US"

async def open_calendar_view(page):
    try:
        print("Waiting for calendar trigger element...")
        # Try both CSS selector and full XPath with increased timeout
        calendar_trigger = None
        try:
            # First try the original CSS selector as it might be more reliable
            calendar_trigger = await page.wait_for_selector('div.BLohnc.q5Vmde', timeout=5000)
            if calendar_trigger:
                print("Found calendar trigger with CSS selector")
        except Exception as css_error:
            print(f"CSS selector failed: {css_error}, trying XPath...")
            try:
                # Then try the full XPath
                calendar_trigger = await page.wait_for_selector('xpath=/html/body/c-wiz[2]/div/div[2]/c-wiz/div[1]/c-wiz/div[2]/div[1]/div[1]/div[1]/div/div[2]/div[2]/div/div/div[1]/div/div/div[1]/div/div[1]/div/div[1]', timeout=5000)
                if calendar_trigger:
                    print("Found calendar trigger with XPath")
            except Exception as xpath_error:
                print(f"XPath selector also failed: {xpath_error}")
                raise xpath_error

        if not calendar_trigger:
            print("Could not find calendar trigger with any selector")
            return False

        print("Clicking calendar trigger...")
        await calendar_trigger.click()
        
        print("Waiting for calendar to appear...")
        # Wait for the calendar container with both selectors
        calendar_container = None
        try:
            # First try CSS selector
            calendar_container = await page.wait_for_selector('div.oB61Xb.E0vWmf.k8qXw', timeout=5000)
            if calendar_container:
                print("Found calendar container with CSS selector")
        except Exception:
            print("CSS selector for calendar container failed, trying XPath...")
            try:
                # Then try XPath
                calendar_container = await page.wait_for_selector('xpath=/html/body/c-wiz[2]/div/div[2]/c-wiz/div[1]/c-wiz/div[2]/div[1]/div[1]/div[1]/div/div[2]/div[2]/div/div/div[2]/div/div[2]/div[2]/div/div', timeout=5000)
                if calendar_container:
                    print("Found calendar container with XPath")
            except Exception as e:
                print(f"All selectors for calendar container failed: {e}")
                
        # Try to find month rowgroup with both selectors
        rowgroup = None
        try:
            # First try CSS
            rowgroup = await page.wait_for_selector('div[role="rowgroup"].Bc6Ryd.ydXJud', timeout=5000)
            if rowgroup:
                print("Found month rowgroup with CSS selector")
        except Exception:
            print("CSS selector for month rowgroup failed, trying XPath...")
            try:
                # Then try XPath
                rowgroup = await page.wait_for_selector('xpath=/html/body/c-wiz[2]/div/div[2]/c-wiz/div[1]/c-wiz/div[2]/div[1]/div[1]/div[1]/div/div[2]/div[2]/div/div/div[2]/div/div[2]/div[2]/div/div/div[1]/div/div[1]', timeout=5000)
                if rowgroup:
                    print("Found month rowgroup with XPath")
            except Exception as e:
                print(f"All selectors for month rowgroup failed: {e}")
        
        if calendar_container or rowgroup:
            print("Calendar view is now open")
            return True
        else:
            print("Could not confirm calendar is open")
            return False
    except Exception as e:
        print(f"Failed to open calendar view: {e}")
        return False

async def extract_month_prices(page, month_container):
    highest_price = -1.0
    highest_price_element = None

    try:
        # Reduced wait for prices to load
        await page.wait_for_timeout(1000)

        # Updated to use full XPath for calendar grid
        calendar_grid = await month_container.query_selector('div[jsname="Mgvhmd"]')
        if not calendar_grid:
            print("Calendar grid not found in month container")
            return highest_price_element, highest_price

        rows = await calendar_grid.query_selector_all('div[role="row"]')
        print(f"Found {len(rows)} rows in calendar grid")

        for row in rows:
            cells = await row.query_selector_all(':scope > *')
            for cell in cells:
                cell_text = (await cell.inner_text()).strip()
                if not cell_text:
                    continue

                price_match = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", cell_text)
                if price_match:
                    try:
                        price = float(price_match.group(1).replace(",", ""))
                        print(f"Found price: ${price}")
                        if price > highest_price:
                            highest_price = price
                            highest_price_element = cell
                            print(f"New highest price: ${price}")
                    except (ValueError, IndexError) as e:
                        print(f"Error parsing price: {e}")

    except Exception as e:
        print(f"Error extracting prices: {e}")

    return highest_price_element, highest_price

async def check_visible_months(page, target_month):
    try:
        # Try both CSS and XPath selectors for the rowgroup
        try:
            await page.wait_for_selector('div[role="rowgroup"].Bc6Ryd.ydXJud', timeout=3000)
            print("Found rowgroup with CSS selector")
        except Exception:
            print("CSS selector for rowgroup failed, trying XPath...")
            try:
                await page.wait_for_selector('xpath=/html/body/c-wiz[2]/div/div[2]/c-wiz/div[1]/c-wiz/div[2]/div[1]/div[1]/div[1]/div/div[2]/div[2]/div/div/div[2]/div/div[2]/div[2]/div/div/div[1]/div/div[1]', timeout=3000)
                print("Found rowgroup with XPath")
            except Exception as e:
                print(f"All selectors for rowgroup failed: {e}")
        
        # Get month containers using both approaches
        css_containers = await page.query_selector_all('div[role="rowgroup"].Bc6Ryd.ydXJud')
        xpath_containers = []
        
        # Try to get containers by XPath
        xpath1 = await page.query_selector('xpath=/html/body/c-wiz[2]/div/div[2]/c-wiz/div[1]/c-wiz/div[2]/div[1]/div[1]/div[1]/div/div[2]/div[2]/div/div/div[2]/div/div[2]/div[2]/div/div/div[1]/div/div[1]')
        if xpath1:
            xpath_containers.append(xpath1)
            
        xpath2 = await page.query_selector('xpath=/html/body/c-wiz[2]/div/div[2]/c-wiz/div[1]/c-wiz/div[2]/div[1]/div[1]/div[1]/div/div[2]/div[2]/div/div/div[2]/div/div[2]/div[2]/div/div/div[1]/div/div[2]')
        if xpath2:
            xpath_containers.append(xpath2)
            
        # Use whichever approach found containers
        month_containers = css_containers if len(css_containers) > 0 else xpath_containers
        
        # Filter out None values
        month_containers = [container for container in month_containers if container]
        print(f"Found {len(month_containers)} month containers")

        for i, month_container in enumerate(month_containers):
            month_name_elem = await month_container.query_selector('div.BgYkof.B5dqIf.qZwLKe')
            if not month_name_elem:
                print(f"Month name element not found in container {i}")
                continue

            month_name = (await month_name_elem.inner_text()).strip()
            print(f"Found month: {month_name}")

            if target_month.lower() in month_name.lower():
                print(f"Target month '{target_month}' found in '{month_name}'")
                # Added increased wait time after finding the target month
                print(f"Increasing wait time for target month...")
                await page.wait_for_timeout(4000)  # Increased from default to 4 seconds
                return month_container, True

        print(f"Target month '{target_month}' not found in visible months")
        return None, False
    except Exception as e:
        print(f"Error checking visible months: {e}")
        return None, False

async def click_next_button(page):
    try:
        # Try multiple methods to find and click the next button
        
        # 1. Try with full XPath
        next_button_xpath = '/html/body/c-wiz[2]/div/div[2]/c-wiz/div[1]/c-wiz/div[2]/div[1]/div[1]/div[1]/div/div[2]/div[2]/div/div/div[2]/div/div[2]/div[2]/div/div/div[3]/div/div/button/div[3]'
        try:
            # First try with Playwright's locator API
            next_button = page.locator('xpath=' + next_button_xpath)
            is_visible = await next_button.is_visible(timeout=2000)
            if is_visible:
                await next_button.click()
                print("Next button clicked with primary XPath selector")
                await page.wait_for_timeout(1000)
                return True
            else:
                print("Next button not visible with primary XPath selector")
        except Exception as e:
            print(f"Error with primary XPath selector (locator): {e}")
            
            # If locator fails, try with querySelector
            try:
                next_button_element = await page.query_selector('xpath=' + next_button_xpath)
                if next_button_element:
                    await next_button_element.click()
                    print("Next button clicked with XPath using querySelector")
                    await page.wait_for_timeout(1000)
                    return True
                else:
                    print("Next button not found with XPath using querySelector")
            except Exception as e2:
                print(f"Error with XPath using querySelector: {e2}")
        
        # 2. Try with original div#ow14 selector
        try:
            original_selector = "div#ow14 > div:nth-of-type(2) > div > div:nth-of-type(2) > div:nth-of-type(2) > div > div > div:nth-of-type(3) > div > div > button > div:nth-of-type(3)"
            orig_button = page.locator(original_selector)
            is_visible = await orig_button.is_visible(timeout=1000)
            if is_visible:
                await orig_button.click()
                print("Next button clicked with original selector")
                await page.wait_for_timeout(1000)
                return True
            else:
                print("Next button not visible with original selector")
        except Exception as e:
            print(f"Error with original selector: {e}")
        
        # 3. Try alternative selectors as fallback
        alternative_selectors = [
            "button[aria-label*='next']",
            "div[role='button'][aria-label*='next']",
            "div:nth-of-type(3) > div > div > button[aria-label*='next']"
        ]
        for selector in alternative_selectors:
            try:
                alt_button = page.locator(selector)
                if await alt_button.is_visible(timeout=1000):
                    await alt_button.click()
                    print(f"Next button clicked with alternative selector: {selector}")
                    await page.wait_for_timeout(1000)
                    return True
            except Exception as e2:
                print(f"Failed with alternative selector {selector}: {e2}")

        print("Could not find or click next button with any selector")
        return False
    except Exception as e:
        print(f"Error in click_next_button: {e}")
        return False

async def scrape_calendar_view(url: str, target_month: str, headless: bool = True, screenshots_dir: str = None):
    """
    Scrape flight prices for a specific month from Google Flights calendar view.
    
    Args:
        url (str): The Google Flights URL to scrape.
        target_month (str): The month to scrape prices for (e.g., "June").
        headless (bool, optional): Whether to run the browser in headless mode. Defaults to True.
        screenshots_dir (str, optional): Directory to save screenshots for debugging. If None, no screenshots are taken.
        
    Returns:
        float: The highest price found for the target month, or -1 if no prices were found.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        print(f"Navigating to {url}")
        await page.goto(url)
        await page.wait_for_timeout(5000)  # Increased initial page load wait
        
        # Enable page debugging (will show console logs)
        page.on("console", lambda msg: print(f"BROWSER LOG: {msg.text}"))
        
        # Take screenshots if directory is provided
        if screenshots_dir:
            screenshot_path = f"{screenshots_dir}/before_calendar_view.png"
            await page.screenshot(path=screenshot_path)
            print(f"Took screenshot: {screenshot_path}")

        if not await open_calendar_view(page):
            print("Failed to open calendar view, exiting")
            if screenshots_dir:
                screenshot_path = f"{screenshots_dir}/failed_calendar_view.png"
                await page.screenshot(path=screenshot_path)
                print(f"Took screenshot: {screenshot_path}")
            await browser.close()
            return -1

        await page.wait_for_timeout(3000)  # Increased wait for calendar render
        if screenshots_dir:
            screenshot_path = f"{screenshots_dir}/after_calendar_view.png"
            await page.screenshot(path=screenshot_path)
            print(f"Took screenshot: {screenshot_path}")

        # Try both CSS and XPath to get the first month container
        first_month_container = None
        
        # First try with CSS
        try:
            first_month_container = await page.query_selector('div[role="rowgroup"].Bc6Ryd.ydXJud')
            if first_month_container:
                print("Found first month container with CSS")
        except Exception as e:
            print(f"Error finding month container with CSS: {e}")
            
        # If CSS fails, try with XPath
        if not first_month_container:
            try:
                first_month_container = await page.query_selector('xpath=/html/body/c-wiz[2]/div/div[2]/c-wiz/div[1]/c-wiz/div[2]/div[1]/div[1]/div[1]/div/div[2]/div[2]/div/div/div[2]/div/div[2]/div[2]/div/div/div[1]/div/div[1]')
                if first_month_container:
                    print("Found first month container with XPath")
            except Exception as e:
                print(f"Error finding month container with XPath: {e}")
                
        if not first_month_container:
            print("No month containers found with any selector")
            if screenshots_dir:
                screenshot_path = f"{screenshots_dir}/no_month_container.png"
                await page.screenshot(path=screenshot_path)
                print(f"Took screenshot: {screenshot_path}")
            await browser.close()
            return -1

        month_name_elem = await first_month_container.query_selector('div.BgYkof.B5dqIf.qZwLKe')
        if not month_name_elem:
            print("First month name element not found")
            if screenshots_dir:
                screenshot_path = f"{screenshots_dir}/no_month_name.png"
                await page.screenshot(path=screenshot_path)
            await browser.close()
            return -1

        current_month_name = (await month_name_elem.inner_text()).strip()
        print(f"Current month from calendar: {current_month_name}")

        # Map month names to numbers
        month_numbers = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        # Extract just the month name without year if it contains a year
        current_month_parts = current_month_name.lower().split()
        current_month_only = next((part for part in current_month_parts if part in month_numbers), current_month_name.lower())
        
        current_month_num = month_numbers.get(current_month_only, None)
        target_month_num = month_numbers.get(target_month.lower(), None)
        if current_month_num is None or target_month_num is None:
            print(f"Invalid month provided. Current: {current_month_only}, Target: {target_month.lower()}")
            await browser.close()
            return -1

        # Calculate the difference in months assuming the target is in the future (possibly next year)
        if target_month_num >= current_month_num:
            diff = target_month_num - current_month_num
        else:
            diff = 12 - current_month_num + target_month_num
            
        # Special handling for the last month in sequence (the month right before current month)
        # If target month is one month before current month, keep original logic
        last_month_num = current_month_num - 1 if current_month_num > 1 else 12
        last_month = [k for k, v in month_numbers.items() if v == last_month_num][0].capitalize()
        
        if target_month.lower() == last_month.lower():
            clicks_needed = max(diff - 1, 0)  # Original logic for last month
            print(f"Target is {target_month} (month before current), using original click logic: {clicks_needed}")
        else:
            clicks_needed = max(diff, 0)  # Add one more click for other months
            print(f"Calculated clicks needed to reach {target_month} in first view: {clicks_needed}")

        # Click the next button the required number of times
        for i in range(clicks_needed):
            if await click_next_button(page):
                print(f"Clicked next button {i + 1} time(s)")
                await page.wait_for_timeout(50)
            else:
                print("Failed to click next button, aborting")
                if screenshots_dir:
                    screenshot_path = f"{screenshots_dir}/next_button_failed.png"
                    await page.screenshot(path=screenshot_path)
                await browser.close()
                return -1

        # Now check if the target month is visible
        target_month_container, found = await check_visible_months(page, target_month)
        if not found:
            print(f"Target month {target_month} not found after clicking")
            if screenshots_dir:
                screenshot_path = f"{screenshots_dir}/target_month_not_found.png"
                await page.screenshot(path=screenshot_path)
            await browser.close()
            return -1

        # Extract prices from the target month
        highest_price_element, month_highest_price = await extract_month_prices(page, target_month_container)
        if month_highest_price > 0:
            highest_price = month_highest_price
            print(f"Successfully found highest price: ${highest_price}")
        else:
            print(f"No prices found for {target_month}.")
            highest_price = -1

        await browser.close()
        return highest_price

async def get_highest_price(departure: str, arrival: str, target_month: str, headless: bool = True, screenshots_dir: str = None):
    """
    Get the highest flight price for a specific route and month.
    
    This is the main function to call from FastAPI endpoints.
    
    Args:
        departure (str): Departure airport code (e.g., "HAM")
        arrival (str): Arrival airport code (e.g., "CDG")
        target_month (str): The month to check prices for (e.g., "June")
        headless (bool, optional): Whether to run the browser in headless mode. Defaults to True.
        screenshots_dir (str, optional): Directory to save screenshots for debugging. Defaults to None.
        
    Returns:
        float: The highest price found, or -1 if no prices were found
    """
    url = construct_flight_url(departure, arrival)
    print(f"Constructed URL for {departure} to {arrival}: {url}")
    
    highest_price = await scrape_calendar_view(url, target_month, headless, screenshots_dir)
    
    return highest_price