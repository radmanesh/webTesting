"""Responsive metrics testing for HTML files using Playwright and BeautifulSoup.

This module tests HTML files for responsive design metrics including:
- Font size validation (minimum 12px)
- Screenshot generation at different viewport sizes
- Visual comparison with ground truth images

Usage:
    python responsive-metrics.py
"""
import asyncio  # Async event loop for Playwright operations
import re  # Regular expressions for parsing CSS values
from pathlib import Path  # Path utilities for file operations
from typing import List, Dict, Tuple, Optional, Any  # Type hints for better code clarity
from datetime import datetime  # Timestamp generation for output files

from bs4 import BeautifulSoup  # HTML parsing library
from playwright.async_api import async_playwright, Page  # Async Playwright API
from PIL import Image  # Image processing library
import numpy as np  # Numerical operations for image comparison

# ----------------------------- Configuration ---------------------------------
DATA_DIR = Path("data")  # Directory containing test HTML files and ground truth images
OUTPUT_DIR = Path("out")  # Directory for generated screenshots and reports
SOURCE_HTML = "58-gpt5.html"  # Source HTML file to test

# Viewport configurations for responsive testing
VIEWPORTS = {
    "mobile": {"width": 375, "height": 0},  # Mobile viewport (iPhone standard)
    "tablet": {"width": 1024, "height": 0},  # Tablet viewport (iPad standard)
    "desktop": {"width": 1280, "height": 0},  # Desktop viewport (standard HD)
}  # Dictionary mapping device types to viewport dimensions

# Ground truth image filenames
GROUND_TRUTH_IMAGES = {
    "desktop": "58-gt-d.png",  # Desktop ground truth image
    "mobile": "58-gt-m.png",  # Mobile ground truth image
    "tablet": "58-gt-t.png",  # Tablet ground truth image
}  # Dictionary mapping device types to ground truth filenames

MIN_FONT_SIZE = 12  # Minimum acceptable font size in pixels


def create_output_directory():
    """Create output directory for screenshots and reports if it doesn't exist."""
    OUTPUT_DIR.mkdir(exist_ok=True)  # Create directory safely without error if exists


def parse_font_size(font_size_str: str) -> Optional[float]:
    """Parse font size string to numeric value in pixels.

    Args:
        font_size_str (str): Font size string (e.g., '14px', '1.2em', '120%')

    Returns:
        Optional[float]: Font size in pixels, or None if unparseable
    """
    if not font_size_str:  # Handle empty or None values
        return None

    # Extract numeric value and unit
    match = re.match(r'([\d.]+)(px|pt|em|rem|%)?', font_size_str.strip())  # Parse size and unit
    if not match:  # No valid pattern found
        return None

    value = float(match.group(1))  # Numeric part of size
    unit = match.group(2) or 'px'  # Unit (default to px if missing)

    # Convert to pixels (approximate conversions)
    if unit == 'px':  # Already in pixels
        return value
    elif unit == 'pt':  # Points to pixels
        return value * 1.333  # 1pt = 1.333px
    elif unit == 'em' or unit == 'rem':  # Relative units
        return value * 16  # Assuming 16px base font
    elif unit == '%':  # Percentage
        return (value / 100) * 16  # Assuming 16px base font

    return None  # Unparseable unit


async def check_font_sizes_in_html(html_path: Path) -> Dict[str, Any]:
    """Check all text elements in HTML file for minimum font size compliance.

    Args:
        html_path (Path): Path to HTML file to analyze

    Returns:
        Dict: Results containing violations and statistics
    """
    # Read HTML file content
    html_content = html_path.read_text(encoding='utf-8')  # Load HTML as string
    soup = BeautifulSoup(html_content, 'html.parser')  # Parse HTML structure

    violations = []  # List to store font size violations
    total_checked_elements = 0  # Counter for elements with inline font-size

    # Find all elements with style attribute
    for element in soup.find_all(style=True):  # Iterate all elements with inline styles
        style = element["style"]  # Get style attribute value

        # Search for font-size property in style
        match = re.search(r"font-size\s*:\s*([^;]+)", style)  # Extract font-size value
        if match:  # Font-size found in inline style
            total_checked_elements += 1  # Increment counter
            size_str = match.group(1)  # Get font-size value string
            size_px = parse_font_size(size_str)  # Convert to pixels

            if size_px is not None and size_px < MIN_FONT_SIZE:  # Size below minimum threshold
                text = element.get_text(strip=True)  # Extract element text content
                violations.append({
                    'element': element.name,  # Element tag name
                    'text': text[:50] + '...' if len(text) > 50 else text,  # Truncated text sample
                    'font_size': f"{size_px:.1f}px",  # Formatted font size
                    'style': style,  # Full style attribute
                })  # Add violation record

    # Compile results
    results = {
        'html_file': html_path.name,  # Filename
        'total_checked_elements': total_checked_elements,  # Total elements with inline font-size
        'violations': violations,  # List of violations
        'violations_count': len(violations),  # Count of violations
        'min_font_size': MIN_FONT_SIZE,  # Minimum required size
        'passed': len(violations) == 0,  # Boolean pass/fail
    }  # Results dictionary

    return results  # Return analysis results


# --- Playwright-based check for computed font sizes across viewports ---
async def check_computed_font_sizes_with_playwright(html_path: Path) -> Dict[str, Any]:
    """Use Playwright to compute final (cascaded) font sizes of all visible text elements
    across all configured VIEWPORTS, and report violations w.r.t. MIN_FONT_SIZE.

    Args:
        html_path (Path): Path to the local HTML file.

    Returns:
        Dict[str, Any]: Summary + per-viewport details of violations.
    """
    # Prepare container for results
    per_viewport_results: Dict[str, Dict[str, Any]] = {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)

        for viewport_name, viewport_config in VIEWPORTS.items():
            # Create a new context for each viewport
            context = await browser.new_context(
                viewport={'width': viewport_config['width'], 'height': 800}
            )
            page = await context.new_page()

            file_url = f"file://{html_path.absolute()}"
            await page.goto(file_url)
            await page.wait_for_load_state("networkidle")

            # Evaluate in-page: gather all visible elements that actually render text,
            # compute their final (cascaded) font-size via getComputedStyle().
            results = await page.evaluate(
                """(minPx) => {
                    function isVisible(el) {
                        const style = getComputedStyle(el);
                        if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity) === 0) return false;
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    }
                    function cssPath(el) {
                        const path = [];
                        while (el && el.nodeType === 1 && el !== document.body) {
                            let selector = el.nodeName.toLowerCase();
                            if (el.id) {
                                selector += '#' + el.id;
                                path.unshift(selector);
                                break;
                            } else {
                                let sib = el, nth = 1;
                                while (sib = sib.previousElementSibling) {
                                    if (sib.nodeName === el.nodeName) nth++;
                                }
                                selector += `:nth-of-type(${nth})`;
                            }
                            path.unshift(selector);
                            el = el.parentElement;
                        }
                        return path.join(' > ');
                    }
                    const out = [];
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, null);
                    let node;
                    while ((node = walker.nextNode())) {
                        if (!isVisible(node)) continue;
                        const text = node.innerText ? node.innerText.trim() : "";
                        if (!text) continue; // skip elements without rendered text
                        const s = getComputedStyle(node);
                        const fs = s.fontSize;
                        const px = parseFloat(fs);
                        out.push({
                            tag: node.tagName.toLowerCase(),
                            selector: cssPath(node),
                            text: text.slice(0, 120),
                            font_size: fs,
                            font_size_px: px,
                            ok: !Number.isNaN(px) && px >= minPx
                        });
                    }
                    return out;
                }""",
                MIN_FONT_SIZE,
            )

            await context.close()

            total_text_elements = len(results)
            violations = [r for r in results if not r.get("ok", False)]

            per_viewport_results[viewport_name] = {
                "total_text_elements": total_text_elements,
                "violations_count": len(violations),
                "violations": violations,
            }

        await browser.close()

    # Build summary across all viewports
    total_elems = sum(v["total_text_elements"] for v in per_viewport_results.values())
    total_violations = sum(v["violations_count"] for v in per_viewport_results.values())

    return {
        "html_file": html_path.name,
        "min_font_size": MIN_FONT_SIZE,
        "total_text_elements": total_elems,
        "total_violations": total_violations,
        "by_viewport": per_viewport_results,
        "passed": total_violations == 0,
    }


async def capture_screenshot_at_viewport(
    html_path: Path,
    viewport_name: str,
    viewport_config: Dict[str, int],
    output_dir: Path
) -> Path:
    """Capture screenshot of HTML file at specified viewport size.

    Args:
        html_path (Path): Path to HTML file
        viewport_name (str): Name of viewport (mobile/tablet/desktop)
        viewport_config (Dict): Viewport dimensions (width and height)
        output_dir (Path): Directory to save screenshot

    Returns:
        Path: Path to saved screenshot file
    """
    async with async_playwright() as pw:  # Initialize Playwright context
        browser = await pw.chromium.launch(headless=True)  # Launch headless browser

        # Create context with specified viewport
        context = await browser.new_context(
            viewport={'width': viewport_config['width'], 'height': 800}  # Initial height for loading
        )  # Browser context with viewport

        page = await context.new_page()  # Create new page

        # Load HTML file
        file_url = f"file://{html_path.absolute()}"  # Convert to file URL
        await page.goto(file_url)  # Navigate to HTML file
        await page.wait_for_load_state("networkidle")  # Wait for full load

        # Get actual content height if height is 0 (full page)
        if viewport_config['height'] == 0:  # Full page screenshot requested
            content_height = await page.evaluate("""
                () => {
                    return Math.max(
                        document.body.scrollHeight,
                        document.documentElement.scrollHeight
                    );
                }
            """)  # Calculate total page height

            # Update viewport to include full height
            await page.set_viewport_size({
                'width': viewport_config['width'],
                'height': content_height
            })  # Set full page dimensions

        # Generate screenshot filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Timestamp for filename
        screenshot_filename = f"{html_path.stem}_{viewport_name}_{timestamp}.png"  # Descriptive filename
        screenshot_path = output_dir / screenshot_filename  # Full path

        # Capture screenshot
        await page.screenshot(path=screenshot_path, full_page=True)  # Take full page screenshot

        await browser.close()  # Clean up browser

    return screenshot_path  # Return path to screenshot


async def generate_all_screenshots(html_path: Path) -> Dict[str, Path]:
    """Generate screenshots for all viewport sizes.

    Args:
        html_path (Path): Path to HTML file to screenshot

    Returns:
        Dict[str, Path]: Mapping of viewport names to screenshot paths
    """
    create_output_directory()  # Ensure output directory exists

    screenshots = {}  # Dictionary to store screenshot paths

    # Generate screenshot for each viewport
    for viewport_name, viewport_config in VIEWPORTS.items():  # Iterate viewport configurations
        print(f"Generating {viewport_name} screenshot ({viewport_config['width']}px)...")  # Status message
        screenshot_path = await capture_screenshot_at_viewport(
            html_path,
            viewport_name,
            viewport_config,
            OUTPUT_DIR
        )  # Capture screenshot
        screenshots[viewport_name] = screenshot_path  # Store path
        print(f"  Saved: {screenshot_path}")  # Confirmation message

    return screenshots  # Return all screenshot paths


def load_ground_truth_images() -> Dict[str, Image.Image]:
    """Load ground truth images for comparison.

    Returns:
        Dict[str, Image.Image]: Mapping of viewport names to PIL Image objects
    """
    ground_truth = {}  # Dictionary to store loaded images

    for viewport_name, image_filename in GROUND_TRUTH_IMAGES.items():  # Iterate ground truth files
        image_path = DATA_DIR / image_filename  # Full path to image
        if image_path.exists():  # Check if file exists
            ground_truth[viewport_name] = Image.open(image_path)  # Load image
            print(f"Loaded ground truth: {image_filename}")  # Confirmation
        else:  # File not found
            print(f"Warning: Ground truth image not found: {image_path}")  # Warning message

    return ground_truth  # Return loaded images


def calculate_pixel_difference(img1: Image.Image, img2: Image.Image) -> Dict[str, float]:
    """Calculate pixel-level difference between two images.

    Args:
        img1 (Image.Image): First image
        img2 (Image.Image): Second image

    Returns:
        Dict[str, float]: Metrics including MSE, RMSE, and percentage difference
    """
    # Convert both images to RGB mode to ensure consistent channels
    if img1.mode != 'RGB':  # Check if first image needs conversion
        print(f"  Converting img1 from {img1.mode} to RGB")  # Info message
        img1 = img1.convert('RGB')  # Convert to RGB
    if img2.mode != 'RGB':  # Check if second image needs conversion
        print(f"  Converting img2 from {img2.mode} to RGB")  # Info message
        img2 = img2.convert('RGB')  # Convert to RGB

    # Resize images to match if needed
    if img1.size != img2.size:  # Size mismatch
        print(f"  Resizing images to match: {img1.size} vs {img2.size}")  # Info message
        # Resize smaller image to match larger
        max_width = max(img1.width, img2.width)  # Maximum width
        max_height = max(img1.height, img2.height)  # Maximum height
        img1 = img1.resize((max_width, max_height), Image.Resampling.LANCZOS)  # Resize first image
        img2 = img2.resize((max_width, max_height), Image.Resampling.LANCZOS)  # Resize second image

    # Convert to numpy arrays
    arr1 = np.array(img1)  # Image 1 as array
    arr2 = np.array(img2)  # Image 2 as array

    # Calculate mean squared error
    mse = np.mean((arr1 - arr2) ** 2)  # Mean squared error
    rmse = np.sqrt(mse)  # Root mean squared error

    # Calculate percentage difference
    max_possible_diff = 255.0  # Maximum pixel value difference
    percentage_diff = (rmse / max_possible_diff) * 100  # Percentage

    return {
        'mse': float(mse),  # Mean squared error
        'rmse': float(rmse),  # Root mean squared error
        'percentage_difference': float(percentage_diff),  # Percentage difference
    }  # Return metrics dictionary


async def compare_screenshots_with_ground_truth(
    screenshots: Dict[str, Path],
    ground_truth: Dict[str, Image.Image]
) -> Dict[str, Dict]:
    """Compare generated screenshots with ground truth images.

    Args:
        screenshots (Dict[str, Path]): Generated screenshot paths
        ground_truth (Dict[str, Image.Image]): Ground truth images

    Returns:
        Dict[str, Dict]: Comparison metrics for each viewport
    """
    comparisons = {}  # Dictionary to store comparison results

    for viewport_name, screenshot_path in screenshots.items():  # Iterate screenshots
        if viewport_name not in ground_truth:  # No ground truth available
            print(f"Skipping comparison for {viewport_name} (no ground truth)")  # Info message
            continue

        print(f"Comparing {viewport_name} screenshot with ground truth...")  # Status message

        # Load generated screenshot
        generated_img = Image.open(screenshot_path)  # Load screenshot
        ground_truth_img = ground_truth[viewport_name]  # Get ground truth

        # Calculate metrics
        metrics = calculate_pixel_difference(generated_img, ground_truth_img)  # Compare images

        comparisons[viewport_name] = {
            'screenshot_path': str(screenshot_path),  # Path to screenshot
            'ground_truth': GROUND_TRUTH_IMAGES[viewport_name],  # Ground truth filename
            'metrics': metrics,  # Comparison metrics
        }  # Store comparison results

        print(f"  MSE: {metrics['mse']:.2f}")  # Print MSE
        print(f"  RMSE: {metrics['rmse']:.2f}")  # Print RMSE
        print(f"  Difference: {metrics['percentage_difference']:.2f}%")  # Print percentage

    return comparisons  # Return all comparison results


async def run_complete_test():
    """Run complete responsive metrics test suite."""
    print("=" * 70)  # Header separator
    print("RESPONSIVE METRICS TEST")  # Title
    print("=" * 70)  # Header separator

    # 1. Check font sizes
    print("\n1. Checking font sizes...")  # Section header
    html_path = DATA_DIR / SOURCE_HTML  # Path to source HTML

    if not html_path.exists():  # Check if file exists
        print(f"ERROR: Source HTML file not found: {html_path}")  # Error message
        return  # Exit early

    font_results = await check_font_sizes_in_html(html_path)  # Analyze font sizes

    print(f"\nFont Size Analysis Results:")  # Results header
    print(f"  Elements checked (with inline font-size): {font_results['total_checked_elements']}")  # Total count
    print(f"  Violations found: {font_results['violations_count']}")  # Violation count
    print(f"  Test passed: {'✓ YES' if font_results['passed'] else '✗ NO'}")  # Pass/fail

    if font_results['violations']:  # Display violations if any
        print(f"\n  Violations (font size < {MIN_FONT_SIZE}px):")  # Violations header
        for i, violation in enumerate(font_results['violations'][:10], 1):  # Show first 10
            print(f"    {i}. <{violation['element']}> {violation['font_size']}")  # Violation details
            print(f"       Text: {violation['text']}")  # Text sample

    # 1a. Check computed (final) font sizes via Playwright
    print(f"\n1a. Checking computed font sizes with Playwright across viewports...")
    computed_results = await check_computed_font_sizes_with_playwright(html_path)

    print(f"\nComputed Font Size Results:")
    print(f"  Total text elements (all viewports): {computed_results['total_text_elements']}")
    print(f"  Total violations (all viewports): {computed_results['total_violations']}")
    print(f"  Test passed: {'✓ YES' if computed_results['passed'] else '✗ NO'}")

    for vp, vp_res in computed_results["by_viewport"].items():
        print(f"\n  Viewport: {vp}")
        print(f"    Text elements: {vp_res['total_text_elements']}")
        print(f"    Violations: {vp_res['violations_count']}")
        for i, v in enumerate(vp_res["violations"][:10], 1):
            print(f"      {i}. <{v['tag']}> {v['font_size']} (selector: {v['selector']})")
            print(f"         Text: {v['text']}")

    # 2. Generate screenshots
    print(f"\n2. Generating screenshots at different viewports...")  # Section header
    screenshots = await generate_all_screenshots(html_path)  # Generate all screenshots

    # 3. Load ground truth images
    print(f"\n3. Loading ground truth images...")  # Section header
    ground_truth = load_ground_truth_images()  # Load ground truth

    # 4. Compare screenshots with ground truth
    print(f"\n4. Comparing screenshots with ground truth...")  # Section header
    comparisons = await compare_screenshots_with_ground_truth(screenshots, ground_truth)  # Run comparisons

    # Summary
    print("\n" + "=" * 70)  # Footer separator
    print("TEST SUMMARY")  # Summary title
    print("=" * 70)  # Footer separator
    print(f"Font size validation: {'PASSED' if font_results['passed'] else 'FAILED'}")  # Font test result
    print(f"Computed font-size validation: {'PASSED' if computed_results['passed'] else 'FAILED'}")
    print(f"Screenshots generated: {len(screenshots)}")  # Screenshot count
    print(f"Comparisons completed: {len(comparisons)}")  # Comparison count
    print("=" * 70)  # Footer separator


if __name__ == "__main__":  # Script entry point
    asyncio.run(run_complete_test())  # Execute complete test suite
