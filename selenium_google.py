import os  # Provides access to environment variables for credentials
import pickle  # Used to persist authentication cookies across runs
import time  # Fallback simple waits (avoid when possible)
from pathlib import Path  # For cleaner path management
from selenium import webdriver  # Selenium WebDriver main entry point
from selenium.webdriver.common.by import By  # Locator strategies
from selenium.webdriver.common.keys import Keys  # Keyboard interactions
from selenium.webdriver.support.ui import WebDriverWait  # Explicit wait utility
from selenium.webdriver.support import expected_conditions as EC  # Expected conditions for waits
from selenium.common.exceptions import TimeoutException, NoSuchElementException  # Error handling

# ----------------------------- Configuration ---------------------------------
EMAIL = os.getenv("GOOGLE_USER")  # Google account email read from environment
PASSWORD = os.getenv("GOOGLE_PASS")  # Google account password read from environment
SEARCH_QUERY = os.getenv("GOOGLE_SEARCH", "web automation with selenium")  # Default search term
COOKIE_FILE = Path("selenium_cookies.pkl")  # Path where session cookies are stored
BASE_URL = "https://www.google.com"  # Base URL for Google search / login
WAIT_SECONDS = 15  # Default explicit wait timeout (seconds)


def build_driver(headless: bool = False) -> webdriver.Chrome:
    """Create and return a Chrome WebDriver instance.

    Args:
        headless (bool): Whether to run Chrome in headless mode.
    Returns:
        webdriver.Chrome: Configured Chrome WebDriver.
    """
    options = webdriver.ChromeOptions()  # Chrome options object for custom flags
    if headless:  # Add headless flag if requested
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")  # Prevent potential GPU issues
    options.add_argument("--no-sandbox")  # Container compatibility
    options.add_argument("--window-size=1280,800")  # Consistent viewport size
    driver = webdriver.Chrome(options=options)  # Instantiate driver
    return driver  # Return ready driver


def load_cookies(driver: webdriver.Chrome) -> None:
    """Load cookies from disk into the current driver session if present.

    Args:
        driver (webdriver.Chrome): Active WebDriver instance.
    """
    driver.get(BASE_URL)  # Navigate to base URL to set domain before adding cookies
    if COOKIE_FILE.exists():  # Only attempt load if file present
        try:
            for cookie in pickle.loads(COOKIE_FILE.read_bytes()):  # Iterate stored cookies
                # Some cookies might have fields Selenium doesn't accept after serialization (e.g., 'sameSite')
                cookie.pop('sameSite', None)  # Remove unsupported field defensively
                try:
                    driver.add_cookie(cookie)  # Inject cookie into session
                except Exception:
                    continue  # Skip problematic cookie silently
            driver.refresh()  # Refresh to apply authentication context
        except Exception:
            pass  # Ignore corrupt cookie file silently (fresh login will occur)


def save_cookies(driver: webdriver.Chrome) -> None:
    """Persist current session cookies to disk for reuse in future runs.

    Args:
        driver (webdriver.Chrome): Active WebDriver instance.
    """
    try:
        data = driver.get_cookies()  # Retrieve cookies list
        COOKIE_FILE.write_bytes(pickle.dumps(data))  # Serialize to file
    except Exception:
        pass  # Non-fatal if we cannot save


def is_logged_in(driver: webdriver.Chrome) -> bool:
    """Best-effort heuristic to determine if the user appears logged in.

    Args:
        driver (webdriver.Chrome): Active WebDriver instance.
    Returns:
        bool: True if login appears established, False otherwise.
    """
    try:
        # Presence of the account avatar button is a strong signal (aria-label starts with 'Google Account')
        driver.find_element(By.CSS_SELECTOR, "a[aria-label*='Google Account'], img[alt*='Google Account']")
        return True  # Avatar found -> likely logged in
    except NoSuchElementException:
        return False  # Not logged in (or selector changed)


def perform_login(driver: webdriver.Chrome) -> None:
    """Execute Google login flow if user not already authenticated.

    Args:
        driver (webdriver.Chrome): Active WebDriver instance.
    """
    if is_logged_in(driver):  # Skip if already logged in via cookies
        return  # Early exit when session already authenticated

    # Attempt to locate and click the sign-in link/button
    try:
        sign_in_link = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Sign in"))  # Wait until sign-in link is clickable
        )
        sign_in_link.click()  # Trigger navigation to login
    except TimeoutException:
        # If link not found, maybe redirected directly to account page or variant UI; continue attempt
        pass  # Proceed without raising

    # Enter email / identifier
    WebDriverWait(driver, WAIT_SECONDS).until(
        EC.visibility_of_element_located((By.ID, "identifierId"))  # Wait for email field visibility
    ).send_keys(EMAIL + Keys.ENTER)  # Submit email and continue

    # Wait for password field (Google sometimes loads an iframe; simple approach here)
    WebDriverWait(driver, WAIT_SECONDS).until(
        EC.visibility_of_element_located((By.NAME, "password"))  # Wait for password input visibility
    ).send_keys(PASSWORD + Keys.ENTER)  # Enter password and submit

    # Wait for navigation back or account avatar to appear
    try:
        WebDriverWait(driver, WAIT_SECONDS).until(lambda d: is_logged_in(d))  # Poll until logged-in state
        save_cookies(driver)  # Persist cookies for next run
    except TimeoutException:
        # Could not confirm login; continue (search may fail if auth required)
        pass  # Non-fatal, but user may need to investigate (2FA, challenge, etc.)


def perform_search(driver: webdriver.Chrome, query: str) -> list:
    """Execute a Google search and return result titles.

    Args:
        driver (webdriver.Chrome): Active WebDriver instance.
        query (str): Search query string.
    Returns:
        list: Collected result title strings (best-effort, limited subset).
    """
    # Focus search box (name='q') – ensure page is on base google URL
    if BASE_URL not in driver.current_url:
        driver.get(BASE_URL)  # Navigate back to main page if needed

    box = WebDriverWait(driver, WAIT_SECONDS).until(
        EC.element_to_be_clickable((By.NAME, "q"))  # Ensure search box is interactable
    )
    box.clear()  # Clear any residual text
    box.send_keys(query + Keys.ENTER)  # Type query and submit

    # Wait for results container (#search) to appear
    WebDriverWait(driver, WAIT_SECONDS).until(
        EC.presence_of_element_located((By.ID, "search"))  # Wait until results container present
    )

    # Extract result titles (CSS selectors may change; using robust pattern)
    results = []  # Container for collected titles
    for elem in driver.find_elements(By.CSS_SELECTOR, "div#search h3"):  # Iterate over h3 elements in search results
        text = elem.text.strip()  # Clean text
        if text:  # Only keep non-empty titles
            results.append(text)  # Append to list
        if len(results) >= 10:  # Limit to first 10 to reduce noise
            break  # Stop early once limit reached
    return results  # Return collected titles


def login_and_search(headless: bool = False) -> None:
    """High-level orchestration: initialize driver, login (if needed), perform search.

    Args:
        headless (bool): Run browser in headless mode if True.
    """
    driver = build_driver(headless=headless)  # Initialize WebDriver
    try:
        load_cookies(driver)  # Try to restore prior session
        perform_login(driver)  # Perform login if required
        titles = perform_search(driver, SEARCH_QUERY)  # Execute the search
        # Simple output of collected titles
        print("Collected result titles:")  # Informational print for user
        for idx, title in enumerate(titles, 1):  # Enumerate through titles
            print(f"{idx:02d}. {title}")  # Print numbered title list
    finally:
        time.sleep(2)  # Brief pause to visually inspect (if not headless)
        driver.quit()  # Always close browser


if __name__ == "__main__":  # Entrypoint guard
    if not EMAIL or not PASSWORD:  # Validate necessary environment values
        raise EnvironmentError("Please set GOOGLE_USER and GOOGLE_PASS environment variables")  # Inform user
    login_and_search(headless=False)  # Execute workflow (headless can be toggled)
