"""Instagram login automation using Selenium.

Logs into Instagram using credentials from environment variables. Reuses
cookies across runs to avoid repeated logins.

Environment Variables:
    IG_USER       - Instagram username / email / phone.
    IG_PASS       - Instagram password.
    IG_HEADLESS   - (Optional) '1' to run Chrome headless.

Usage:
    export IG_USER=your_user
    export IG_PASS=your_pass
    python selenium_instagram.py
"""
from __future__ import annotations  # Future annotations support

import os  # Access environment variables for credentials
import pickle  # Persist cookies between runs
import time  # Small pauses (kept minimal)
from pathlib import Path  # Path utilities for cookie file
from typing import Optional  # Type hints for optional values

from selenium import webdriver  # Selenium WebDriver entry point
from selenium.webdriver.common.by import By  # Locator strategies
from selenium.webdriver.common.keys import Keys  # Keyboard interactions
from selenium.webdriver.support.ui import WebDriverWait  # Explicit wait utility
from selenium.webdriver.support import expected_conditions as EC  # Wait conditions
from selenium.common.exceptions import TimeoutException  # Error handling for waits

# ----------------------------- Configuration ---------------------------------
IG_USER = os.getenv("IG_USER")  # Instagram username/email (env var)
IG_PASS = os.getenv("IG_PASS")  # Instagram password (env var)
HEADLESS = os.getenv("IG_HEADLESS", "0") == "1"  # Headless flag from env
LOGIN_URL = "https://www.instagram.com/accounts/login/"  # Direct login URL
BASE_URL = "https://www.instagram.com/"  # Base site URL
COOKIE_FILE = Path("ig_cookies.pkl")  # Cookie persistence file path
WAIT_SECONDS = 20  # Default explicit wait timeout


def build_driver(headless: bool = HEADLESS) -> webdriver.Chrome:
    """Create and configure a Chrome WebDriver instance.

    Args:
        headless (bool): Run browser headless if True.
    Returns:
        webdriver.Chrome: Configured driver.
    """
    options = webdriver.ChromeOptions()  # Chrome options container
    if headless:  # Add headless flag when requested
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")  # Stability in some environments
    options.add_argument("--no-sandbox")  # Container / CI compatibility
    options.add_argument("--window-size=1280,900")  # Consistent viewport size
    driver = webdriver.Chrome(options=options)  # Instantiate driver
    driver.get(BASE_URL)  # Navigate to base for domain before cookies
    return driver  # Return driver instance


def load_cookies(driver: webdriver.Chrome) -> None:
    """Load stored cookies into the current browser session if available.

    Args:
        driver (webdriver.Chrome): Active driver instance.
    """
    if not COOKIE_FILE.exists():  # Skip if no cookie file
        return  # Nothing to load
    try:
        for cookie in pickle.loads(COOKIE_FILE.read_bytes()):  # Iterate stored cookie dicts
            cookie.pop('sameSite', None)  # Remove unsupported field defensively
            try:
                driver.add_cookie(cookie)  # Inject cookie
            except Exception:
                continue  # Skip problematic cookie
        driver.refresh()  # Apply cookies by refreshing
    except Exception:
        pass  # Silently ignore corrupt cookie file


def save_cookies(driver: webdriver.Chrome) -> None:
    """Persist current session cookies to disk.

    Args:
        driver (webdriver.Chrome): Active driver instance.
    """
    try:
        COOKIE_FILE.write_bytes(pickle.dumps(driver.get_cookies()))  # Serialize cookies list
    except Exception:
        pass  # Non-fatal if save fails


def is_logged_in(driver: webdriver.Chrome) -> bool:
    """Heuristic check to determine if session appears logged in.

    Args:
        driver (webdriver.Chrome): Active driver instance.
    Returns:
        bool: True if login appears successful.
    """
    try:
        # After login the profile icon/menu or search input should be present.
        driver.find_element(By.CSS_SELECTOR, "nav a[href*='explore']")  # Explore link appears when logged in
        return True  # Logged in state inferred
    except Exception:
        return False  # Not logged in


def perform_login(driver: webdriver.Chrome) -> None:
    """Execute login flow if not already authenticated.

    Args:
        driver (webdriver.Chrome): Active driver instance.
    """
    if is_logged_in(driver):  # Skip if cookies already authenticated
        return  # Early exit

    driver.get(LOGIN_URL)  # Navigate to login page directly

    # Handle potential cookie consent dialog (best-effort, optional)
    try:
        consent_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.='Allow all cookies' or .='Accept All']"))  # Cookie consent buttons
        )
        consent_button.click()  # Accept cookies
    except TimeoutException:
        pass  # No consent dialog or different text

    # Wait for username input
    try:
        user_input = WebDriverWait(driver, WAIT_SECONDS).until(
            EC.visibility_of_element_located((By.NAME, "username"))  # Username field
        )
        user_input.clear()  # Clear any pre-filled text
        user_input.send_keys(IG_USER)  # Input username
        pass_input = WebDriverWait(driver, WAIT_SECONDS).until(
            EC.visibility_of_element_located((By.NAME, "password"))  # Password field
        )
        pass_input.clear()  # Clear field
        pass_input.send_keys(IG_PASS + Keys.ENTER)  # Enter password and submit
    except TimeoutException:
        return  # Cannot proceed without fields

    # Wait for successful navigation / login indicator
    try:
        WebDriverWait(driver, WAIT_SECONDS).until(lambda d: is_logged_in(d))  # Poll until logged in
        save_cookies(driver)  # Persist cookies on success
    except TimeoutException:
        pass  # Login may have failed / challenged


def login(headless: bool = HEADLESS) -> None:
    """High-level orchestrator for Instagram login with cookie reuse.

    Args:
        headless (bool): Run browser headless if True.
    """
    driver = build_driver(headless=headless)  # Build driver
    try:
        load_cookies(driver)  # Attempt cookie reuse
        perform_login(driver)  # Perform login if needed
        status = "Logged in" if is_logged_in(driver) else "Not logged in"  # Status message
        print(f"Instagram login status: {status}")  # Output status to console
    finally:
        time.sleep(2)  # Brief pause
        driver.quit()  # Close browser


if __name__ == "__main__":  # Script entry point
    if not IG_USER or not IG_PASS:  # Validate credentials availability
        raise EnvironmentError("Please set IG_USER and IG_PASS environment variables")  # Raise error
    login(headless=HEADLESS)  # Execute login workflow
