"""Amazon viewport and horizontal scroll testing using Playwright.

This script loads Amazon.com in a 480px viewport width and tests for horizontal
scrolling capabilities. It reports the actual page width and scroll availability.

Usage:
    python playwright_responsive.py
"""
import asyncio  # Async event loop handling for Playwright
from playwright.async_api import async_playwright  # Async Playwright API

# ----------------------------- Configuration ---------------------------------
AMAZON_URL = "https://www.amazon.com"  # Amazon homepage URL
VIEWPORT_WIDTH = 480  # Target viewport width in pixels
VIEWPORT_HEIGHT = 800  # Viewport height in pixels for mobile simulation


async def test_amazon_responsive():
    """Test Amazon page in 480px viewport and check horizontal scroll capability.

    This function loads Amazon in a narrow viewport, measures the actual page width,
    and attempts horizontal scrolling to determine if content extends beyond viewport.
    """
    async with async_playwright() as pw:
        # Launch browser with specific viewport settings
        browser = await pw.chromium.launch(headless=False)  # Browser instance for testing
        context = await browser.new_context(
            viewport={'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT}  # Set mobile-like viewport
        )
        page = await context.new_page()  # Create new page with viewport settings

        # Navigate to Amazon homepage
        await page.goto(AMAZON_URL)  # Load Amazon main page
        await page.wait_for_load_state("networkidle")  # Wait for page to fully load

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

        # Additional mobile responsiveness check
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
    print("Testing Amazon responsiveness at 480px viewport width...")  # Initial status message
    asyncio.run(test_amazon_responsive())  # Execute async test function
    print("Amazon responsive test completed.")  # Completion message
