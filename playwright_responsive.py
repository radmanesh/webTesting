"""Viewport and horizontal scroll testing using Playwright.

This script loads a target website in a 480px viewport width and tests for horizontal
scrolling capabilities. It reports the actual page width and scroll availability.
Takes screenshots before and after scroll in the 'out' folder.

Usage:
    python playwright_responsive.py
"""
import asyncio  # Async event loop handling for Playwright
import os  # Operating system interface for directory operations
from datetime import datetime  # Date and time utilities for filename generation
from pathlib import Path  # Path utilities for file system operations
from urllib.parse import urlparse  # URL parsing utilities for clean filenames
from playwright.async_api import async_playwright  # Async Playwright API

# ----------------------------- Configuration ---------------------------------
TARGET_URL = "https://www.airbnb.com"  # Target website URL for testing
VIEWPORT_WIDTH = 480  # Target viewport width in pixels
VIEWPORT_HEIGHT = 800  # Viewport height in pixels for mobile simulation
OUTPUT_DIR = Path("out")  # Directory for storing screenshots


def create_output_directory():
    """Create output directory for screenshots if it doesn't exist."""
    OUTPUT_DIR.mkdir(exist_ok=True)  # Create 'out' directory safely


def generate_screenshot_filename(url: str, action: str) -> str:
    """Generate descriptive filename for screenshots.

    Args:
        url (str): Website URL for naming context
        action (str): Action description (e.g., 'before-scroll', 'after-scroll')

    Returns:
        str: Formatted filename with URL, date, and action
    """
    # Parse URL to get clean domain name
    domain = urlparse(url).netloc.replace('www.', '')  # Extract domain without www

    # Get current date and time for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Format: YYYYMMDD_HHMMSS

    # Create descriptive filename
    filename = f"{domain}_{action}_{timestamp}.png"  # Combine domain, action, and timestamp

    return filename  # Return complete filename


async def test_responsiveness():
    """Test target website in 480px viewport and check horizontal scroll capability.

    This function loads the target website in a narrow viewport, measures the actual page width,
    and attempts horizontal scrolling to determine if content extends beyond viewport.
    Takes screenshots before and after scroll operations.
    """
    # Create output directory for screenshots
    create_output_directory()  # Ensure screenshots folder exists

    async with async_playwright() as pw:
        # Launch browser with specific viewport settings
        browser = await pw.chromium.launch(headless=False)  # Browser instance for testing
        context = await browser.new_context(
            viewport={'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT}  # Set mobile-like viewport
        )
        page = await context.new_page()  # Create new page with viewport settings

        # Navigate to target website
        await page.goto(TARGET_URL)  # Load target website
        await page.wait_for_load_state("networkidle")  # Wait for page to fully load

        # Take screenshot before any scrolling
        before_scroll_filename = generate_screenshot_filename(TARGET_URL, "before-scroll")  # Generate before-scroll filename
        before_scroll_path = OUTPUT_DIR / before_scroll_filename  # Complete path for before screenshot
        await page.screenshot(path=before_scroll_path, full_page=False)  # Take viewport screenshot
        print(f"Screenshot taken (before scroll): {before_scroll_path}")  # Report screenshot saved

        # Get initial scroll position
        initial_scroll_x = await page.evaluate("window.scrollX")  # Current horizontal scroll position

        # Measure actual page dimensions
        page_width = await page.evaluate("document.documentElement.scrollWidth")  # Total page width including overflow
        page_height = await page.evaluate("document.documentElement.scrollHeight")  # Total page height
        viewport_width = await page.evaluate("window.innerWidth")  # Actual viewport width
        viewport_height = await page.evaluate("window.innerHeight")  # Actual viewport height

        # Print viewport and page dimension information
        print(f"Viewport dimensions: {viewport_width}x{viewport_height}px")  # Display set viewport size
        print(f"Page content dimensions: {page_width}x{page_height}px")  # Display actual content size
        print(f"Initial horizontal scroll position: {initial_scroll_x}px")  # Show starting scroll position

        # Check if horizontal scrolling is possible
        horizontal_scroll_available = page_width > viewport_width  # Boolean check for scroll necessity
        print(f"Horizontal scroll needed: {horizontal_scroll_available}")  # Report if scrolling is required

        if horizontal_scroll_available:
            # Attempt to scroll horizontally to the right
            scroll_amount = min(200, page_width - viewport_width)  # Calculate safe scroll distance
            await page.evaluate(f"window.scrollTo({scroll_amount}, 0)")  # Perform horizontal scroll

            # Wait briefly for scroll to complete
            await page.wait_for_timeout(1000)  # 1-second pause after scroll

            # Take screenshot after scrolling
            after_scroll_filename = generate_screenshot_filename(TARGET_URL, "after-scroll")  # Generate after-scroll filename
            after_scroll_path = OUTPUT_DIR / after_scroll_filename  # Complete path for after screenshot
            await page.screenshot(path=after_scroll_path, full_page=False)  # Take viewport screenshot after scroll
            print(f"Screenshot taken (after scroll): {after_scroll_path}")  # Report screenshot saved

            # Verify scroll actually occurred
            new_scroll_x = await page.evaluate("window.scrollX")  # Get new scroll position
            print(f"Attempted scroll by {scroll_amount}px")  # Report scroll attempt
            print(f"New horizontal scroll position: {new_scroll_x}px")  # Show updated position

            # Check if scroll was successful
            scroll_successful = new_scroll_x > initial_scroll_x  # Verify position change
            print(f"Horizontal scroll successful: {scroll_successful}")  # Report scroll success

            # Scroll back to original position
            await page.evaluate("window.scrollTo(0, 0)")  # Reset to left edge
            final_scroll_x = await page.evaluate("window.scrollX")  # Confirm reset position
            print(f"Reset to scroll position: {final_scroll_x}px")  # Show reset confirmation
        else:
            print("No horizontal scrolling available - page fits within viewport width")  # Report no scroll needed
            # Still take an "after" screenshot even if no scroll occurred
            no_scroll_filename = generate_screenshot_filename(TARGET_URL, "no-scroll-needed")  # Generate no-scroll filename
            no_scroll_path = OUTPUT_DIR / no_scroll_filename  # Complete path for no-scroll screenshot
            await page.screenshot(path=no_scroll_path, full_page=False)  # Take screenshot for reference
            print(f"Screenshot taken (no scroll needed): {no_scroll_path}")  # Report screenshot saved        # Additional mobile responsiveness check
        await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('*');
                let overflowingElements = 0;
                elements.forEach(el => {
                    if (el.scrollWidth > el.clientWidth) {
                        overflowingElements++;
                    }
                });
                window.overflowCount = overflowingElements;
            }
        """)  # JavaScript to count elements with horizontal overflow

        overflow_count = await page.evaluate("window.overflowCount")  # Get overflow element count
        print(f"Elements with horizontal overflow: {overflow_count}")  # Report overflow elements

        # Brief pause for visual inspection if not headless
        await page.wait_for_timeout(3000)  # 3-second pause for observation

        await browser.close()  # Close browser instance


if __name__ == "__main__":  # Script entry point guard
    print("Testing website responsiveness at 480px viewport width...")  # Initial status message
    asyncio.run(test_responsiveness())  # Execute async test function
    print("Responsive test completed.")  # Completion message
