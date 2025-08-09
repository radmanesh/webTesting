import os
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

EMAIL = os.getenv("GOOGLE_USER") or ""  # Google account email from environment variable, always a string
PASSWORD = os.getenv("GOOGLE_PASS") or ""  # Google account password from environment variable, always a string
STATE_FILE = Path("playwright_state.json")  # Path to Playwright state file

async def login_and_search():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(
            storage_state=STATE_FILE if STATE_FILE.exists() else None
        )
        page = await context.new_page()
        await page.goto("https://www.google.com")

        if "Sign in" in await page.content():
            await page.get_by_text("Sign in").click()
            await page.fill("input[type='email']", EMAIL)
            await page.press("input[type='email']", "Enter")
            await page.fill("input[type='password']", PASSWORD)
            await page.press("input[type='password']", "Enter")
            await page.wait_for_load_state("networkidle")
            await context.storage_state(path=STATE_FILE)

        await page.fill("input[name='q']", "web automation with Playwright")
        await page.press("input[name='q']", "Enter")
        await page.wait_for_selector("#search")
        await browser.close()

if __name__ == "__main__":
    if not EMAIL or not PASSWORD:
        raise EnvironmentError("Please set GOOGLE_USER and GOOGLE_PASS environment variables")
    asyncio.run(login_and_search())
