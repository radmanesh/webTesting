"""Facebook login and search automation using Selenium.

This script logs into Facebook with credentials supplied via environment
variables, optionally reuses saved cookies to avoid repeated logins, and
performs a search using Facebook's top search bar. Basic result titles are
printed (limited sampling) to stdout.

Environment Variables:
    FB_USER      - Facebook account email / phone.
    FB_PASS      - Facebook account password.
    FB_SEARCH    - (Optional) Search query. Defaults to 'selenium automation'.
    FB_HEADLESS  - (Optional) If set to '1', runs Chrome headless.

NOTE: Facebook frequently changes its UI and may employ anti-automation
measures. This script is a demonstrative baseline and may require selector
updates or manual intervention (e.g., for 2FA, checkpoint, or captcha).
"""

from __future__ import annotations  # Future annotations for forward references

import os  # Access to environment variables for credentials and config
import time  # Simple sleep for brief pauses (avoid large reliance)
import pickle  # Persist cookies across runs
from pathlib import Path  # Path utilities for cookie file handling
from typing import List  # Type hint for result list

from selenium import webdriver  # Selenium WebDriver entry point
from selenium.webdriver.common.by import By  # Locator strategies
from selenium.webdriver.common.keys import Keys  # Keyboard events
from selenium.webdriver.support.ui import WebDriverWait  # Explicit wait helper
from selenium.webdriver.support import expected_conditions as EC  # Wait conditions
from selenium.common.exceptions import TimeoutException, NoSuchElementException  # Error classes

# ----------------------------- Configuration ---------------------------------
FB_USER = os.getenv("FB_USER")  # Facebook email / phone from environment
FB_PASS = os.getenv("FB_PASS")  # Facebook password from environment
FB_SEARCH = os.getenv("FB_SEARCH", "selenium automation")  # Default search query
HEADLESS = os.getenv("FB_HEADLESS", "0") == "1"  # Headless mode flag
BASE_URL = "https://www.facebook.com"  # Base Facebook URL
LOGIN_URL = f"{BASE_URL}/login"  # Direct login URL
COOKIE_FILE = Path("fb_cookies.pkl")  # Cookie persistence file path
WAIT_SECONDS = 20  # Default explicit wait timeout in seconds


def build_driver(headless: bool = HEADLESS) -> webdriver.Chrome:
    """Instantiate and configure a Chrome WebDriver.

    Args:
        headless (bool): Whether to run in headless mode.
    Returns:
        webdriver.Chrome: Prepared WebDriver instance.
    """
    options = webdriver.ChromeOptions()  # Chrome options container
    if headless:  # Append headless argument if requested
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")  # Improve stability in some envs
    options.add_argument("--no-sandbox")  # Container / CI compatibility
    options.add_argument("--window-size=1366,900")  # Consistent viewport
    options.add_argument("--disable-blink-features=AutomationControlled")  # Mild stealth
    driver = webdriver.Chrome(options=options)  # Build driver instance
    driver.get(BASE_URL)  # Navigate to base immediately
    return driver  # Return configured driver


def load_cookies(driver: webdriver.Chrome) -> None:
    """Load previously saved cookies into the current session.

    Args:
        driver (webdriver.Chrome): Active WebDriver instance.
    """
    if not COOKIE_FILE.exists():  # Skip if no stored cookies
        return
    try:
        for cookie in pickle.loads(COOKIE_FILE.read_bytes()):  # Iterate stored cookies
            cookie.pop('sameSite', None)  # Remove field if unsupported
            try:
                driver.add_cookie(cookie)  # Inject cookie into session
            except Exception:
                continue  # Skip invalid cookie silently
        driver.refresh()  # Apply cookies
    except Exception:
        pass  # Ignore corrupt cookie data


def save_cookies(driver: webdriver.Chrome) -> None:
    """Persist current browser session cookies.

    Args:
        driver (webdriver.Chrome): Active WebDriver instance.
    """
    try:
        COOKIE_FILE.write_bytes(pickle.dumps(driver.get_cookies()))  # Serialize cookies
    except Exception:
        pass  # Non-fatal if save fails


def is_logged_in(driver: webdriver.Chrome) -> bool:
    """Check if user appears logged into Facebook.

    Args:
        driver (webdriver.Chrome): Active WebDriver instance.
    Returns:
        bool: True if a top-level profile / account element is found.
    """
    try:
        # Avatar / profile link often contains aria-label with the account name or 'profile'
        driver.find_element(By.CSS_SELECTOR, "[data-testid='facebar-composer'], div[aria-label*='Create a post']")
        return True  # Element found -> likely logged in
    except NoSuchElementException:
        return False  # Not logged in yet


def perform_login(driver: webdriver.Chrome) -> None:
    """Execute Facebook login if not already authenticated.

    Args:
        driver (webdriver.Chrome): Active WebDriver instance.
    """
    if is_logged_in(driver):  # Skip if already logged in
        return
    driver.get(LOGIN_URL)  # Go directly to login page
    try:
        email_box = WebDriverWait(driver, WAIT_SECONDS).until(
            EC.visibility_of_element_located((By.ID, "email"))  # Wait for email input
        )
        email_box.clear()  # Clear pre-filled content
        email_box.send_keys(FB_USER)  # Input username
        pass_box = WebDriverWait(driver, WAIT_SECONDS).until(
            EC.visibility_of_element_located((By.ID, "pass"))  # Wait for password input
        )
        pass_box.clear()  # Clear if needed
        pass_box.send_keys(FB_PASS + Keys.ENTER)  # Enter password and submit
    except TimeoutException:
        return  # Cannot proceed if inputs not found

    # Wait for login completion heuristically
    try:
        WebDriverWait(driver, WAIT_SECONDS).until(lambda d: is_logged_in(d))  # Poll for logged-in state
        save_cookies(driver)  # Save session cookies
    except TimeoutException:
        # Could be blocked by 2FA or checkpoint; proceed without save
        pass  # Non-fatal


def perform_search(driver: webdriver.Chrome, query: str) -> List[str]:
    """Execute a Facebook search using the top search bar and return result titles.

    Args:
        driver (webdriver.Chrome): Active WebDriver instance.
        query (str): Search string.
    Returns:
        List[str]: A list of trimmed result label strings.
    """
    # Ensure base loaded (search bar lives on main or persistent navbar)
    if BASE_URL not in driver.current_url:
        driver.get(BASE_URL)  # Navigate home

    # Possible search input selectors: aria-label variations. We'll try multiple.
    search_input_selectors = [
        "input[aria-label='Search Facebook']",  # Common main search input
        "input[placeholder='Search Facebook']",  # Placeholder variant
        "input[aria-label='Search']",  # Fallback generic
    ]  # List of candidate selectors for the search field

    search_box = None  # Will hold located search element
    for selector in search_input_selectors:  # Iterate possible selectors
        try:
            search_box = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))  # Wait for clickable input
            )
            break  # Stop when found
        except TimeoutException:
            continue  # Try next selector

    if not search_box:  # Could not find search input
        return []  # Return empty result list

    search_box.clear()  # Clear any text
    search_box.send_keys(query + Keys.ENTER)  # Type search query and submit

    # Wait for search results container heuristically (role='feed' or list of results)
    try:
        WebDriverWait(driver, WAIT_SECONDS).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed'], div[role='main']"))  # Wait for results container
        )
    except TimeoutException:
        return []  # No results container detected

    # Collect candidate result headings / link texts
    results = []  # Accumulator for result texts
    candidate_selectors = [
        "div[role='article'] h2 a span",  # Article heading spans
        "div[role='article'] strong span",  # Strong highlighted names
        "a[role='link'] span[class][dir='auto']",  # Generic link spans
    ]  # Potential selectors for result labels

    for sel in candidate_selectors:  # Iterate selectors
        for elem in driver.find_elements(By.CSS_SELECTOR, sel):  # Find all matching elements
            text = elem.text.strip()  # Extract text
            if text and text not in results:  # Deduplicate
                results.append(text)  # Append unique text
            if len(results) >= 10:  # Cap number of results collected
                return results  # Return early when limit reached
    return results  # Final list (possibly empty)


def login_and_search(headless: bool = HEADLESS) -> None:
    """Primary entry: handle login (with cookie reuse) and perform a search.

    Args:
        headless (bool): Whether to run browser headless.
    """
    driver = build_driver(headless=headless)  # Build driver
    try:
        load_cookies(driver)  # Attempt cookie reuse
        perform_login(driver)  # Perform login if needed
        results = perform_search(driver, FB_SEARCH)  # Execute search
        print("Facebook search results (sample):")  # Header line for output
        for idx, title in enumerate(results, 1):  # Enumerate collected titles
            print(f"{idx:02d}. {title}")  # Print numbered result
        if not results:  # If no results captured
            print("No results captured (selectors may need update or access restricted).")  # Diagnostic message
    finally:
        time.sleep(2)  # Brief pause for inspection (especially non-headless)
        driver.quit()  # Always close driver


if __name__ == "__main__":  # Script entry guard
    if not FB_USER or not FB_PASS:  # Validate required credentials
        raise EnvironmentError("Please set FB_USER and FB_PASS environment variables")  # Raise with helpful message
    login_and_search(headless=HEADLESS)  # Execute workflow
