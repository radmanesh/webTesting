"""Instagram login automation using Playwright (async).

Logs into Instagram using credentials from environment variables. Reuses
storage state (cookies, localStorage) across runs if saved.

Environment Variables:
    IG_USER       - Instagram username / email / phone.
    IG_PASS       - Instagram password.
    IG_HEADLESS   - (Optional) '1' to run headless mode.

Usage:
    export IG_USER=your_user
    export IG_PASS=your_pass
    python playwright_instagram.py
"""
import os  # Access environment variables for credentials
import asyncio  # Async event loop handling for Playwright
from pathlib import Path  # Path utilities for state file management
from playwright.async_api import async_playwright  # Async Playwright API

# ----------------------------- Configuration ---------------------------------
IG_USER = os.getenv("IG_USER") or ""  # Username string (empty default)
IG_PASS = os.getenv("IG_PASS") or ""  # Password string (empty default)
HEADLESS = os.getenv("IG_HEADLESS", "0") == "1"  # Headless mode toggle
STATE_FILE = Path("playwright_ig_state.json")  # Path to persist auth state
LOGIN_URL = "https://www.instagram.com/accounts/login/"  # Login page URL
BASE_URL = "https://www.instagram.com/"  # Base site URL


async def is_logged_in(page) -> bool:
    """Best-effort check if the session appears authenticated.

    Args:
        page: Playwright Page object.
    Returns:
        bool: True if a post-login UI element is detected.
    """
    try:
        # Post-login nav bar (Explore / Messages) presence check
        await page.wait_for_selector("nav a[href*='explore']", timeout=3000)
        return True
    except Exception:
        return False


async def perform_login(page) -> None:
    """Execute Instagram login flow if not already authenticated.

    Args:
        page: Playwright Page object.
    """
    if await is_logged_in(page):  # Skip if already logged in
        return

    await page.goto(LOGIN_URL)  # Navigate to login URL

    # Handle cookie consent dialog (best-effort)
    try:
        consent_sel = "//button[.='Allow all cookies' or .='Accept All' or .='Accept']"
        btn = await page.wait_for_selector(consent_sel, timeout=3000)
        await btn.click()
    except Exception:
        pass  # No consent popup

    # Fill username
    await page.fill("input[name='username']", IG_USER)
    # Fill password
    await page.fill("input[name='password']", IG_PASS)
    # Submit via Enter key
    await page.press("input[name='password']", "Enter")

    # Wait for navigation or logged-in indicator
    try:
        await page.wait_for_selector("nav a[href*='explore']", timeout=15000)
    except Exception:
        pass  # Might be challenge / 2FA


async def login(headless: bool = HEADLESS):
    """High-level orchestrator: create browser, reuse state, perform login.

    Args:
        headless (bool): Run browser headless if True.
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context_args = {}
        if STATE_FILE.exists():  # Load saved state if available
            context_args["storage_state"] = STATE_FILE
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        await page.goto(BASE_URL)

        await perform_login(page)  # Ensure login

        if not await is_logged_in(page):  # Check final status
            print("Instagram login status: Not logged in (check credentials / 2FA).")
        else:
            print("Instagram login status: Logged in.")
            await context.storage_state(path=STATE_FILE)  # Persist state

        await browser.close()


if __name__ == "__main__":  # Script entry guard
    if not IG_USER or not IG_PASS:  # Validate environment credentials
        raise EnvironmentError("Please set IG_USER and IG_PASS environment variables")  # Raise helpful error
    asyncio.run(login(headless=HEADLESS))  # Run async login coroutine
