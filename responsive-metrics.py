"""Responsive metrics testing for HTML files using Playwright and BeautifulSoup.

This module tests HTML files for responsive design metrics including:
- Font size validation (minimum 12px)
- Screenshot generation at different viewport sizes
- Visual comparison with ground truth images

Usage:
    python responsive-metrics.py [--html HTML_FILE]

Arguments:
    --html    Path to HTML file to test (default: data/58-v2-gpt5.html)
"""
import argparse  # Command-line argument parsing
import asyncio  # Async event loop for Playwright operations
import concurrent.futures  # Thread pool for running sync code in async context
import re  # Regular expressions for parsing CSS values
import tempfile  # Temporary file and directory creation with automatic cleanup
from pathlib import Path  # Path utilities for file operations
from typing import List, Dict, Tuple, Optional, Any  # Type hints for better code clarity
from datetime import datetime  # Timestamp generation for output files

from bs4 import BeautifulSoup  # HTML parsing library
from playwright.async_api import async_playwright, Page  # Async Playwright API
from PIL import Image  # Image processing library
import numpy as np  # Numerical operations for image comparison
from layout_similarity import layout_similarity # Layout similarity function

# ----------------------------- Configuration ---------------------------------
DATA_DIR = Path("data")  # Directory containing test HTML files and ground truth images
OUTPUT_DIR = Path("out")  # Directory for generated screenshots and reports
SOURCE_HTML = "58-v2-gpt5.html"  # Source HTML file to test
GROUND_TRUTH_HTML = "58.html"  # Ground truth HTML file for comparison

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
MIN_TAP_TARGET_SIZE = 48  # Minimum tap target size in pixels (48x48 for accessibility)
MIN_LINE_HEIGHT_RATIO = 1.5  # Minimum line-height to font-size ratio for readability


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


async def check_tap_targets(html_path: Path, viewport_config: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """Check that graphic buttons/tap targets meet minimum size requirements (48x48px).

    Args:
        html_path (Path): Path to HTML file to analyze
        viewport_config (Dict): Optional viewport configuration (default uses mobile viewport)

    Returns:
        Dict: Results containing tap target violations and statistics
    """
    if viewport_config is None:  # Use mobile viewport if not specified
        viewport_config = VIEWPORTS["mobile"]  # Default to mobile viewport for tap target testing

    async with async_playwright() as p:  # Initialize Playwright context
        browser = await p.chromium.launch(headless=True)  # Launch headless browser
        page = await browser.new_page(
            viewport={'width': viewport_config['width'], 'height': 800}  # Set viewport dimensions
        )  # Create page with specified viewport

        # Load HTML file
        file_url = html_path.resolve().as_uri()  # Convert path to file:// URL
        await page.goto(file_url)  # Navigate to HTML file
        await page.wait_for_load_state("networkidle")  # Wait for full load

        # Evaluate tap targets in browser context
        results = await page.evaluate(
            """
            () => {
              // Candidate selectors for tap targets
              const candidates = Array.from(document.querySelectorAll(
                'button, a, input[type="button"], input[type="submit"], input[type="reset"]'
              ));

              function isGraphicButton(el) {
                // Heuristics: has <img>, <svg>, or icon classes
                if (el.querySelector('img, svg')) return true;

                const className = el.className || '';
                if (typeof className === 'string') {
                  const iconHints = ['icon', 'fa-', 'mdi-', 'material-icons'];
                  if (iconHints.some(h => className.includes(h))) return true;
                }

                // If it has no visible text but has aria-label -> likely graphic
                const text = (el.textContent || '').trim();
                if (!text && el.getAttribute('aria-label')) return true;

                return false;
              }

              return candidates.map(el => {
                const rect = el.getBoundingClientRect();
                const isGraphic = isGraphicButton(el);
                const passes = rect.width >= 48 && rect.height >= 48;

                return {
                  tag: el.tagName.toLowerCase(),
                  text: (el.textContent || '').trim().slice(0, 40),
                  ariaLabel: el.getAttribute('aria-label') || '',
                  isGraphic,
                  width: rect.width,
                  height: rect.height,
                  passes,
                };
              });
            }
            """
        )  # Execute JavaScript to analyze tap targets

        await browser.close()  # Clean up browser

    # Filter graphic buttons and check for violations
    graphic_buttons = [r for r in results if r['isGraphic']]  # Filter to graphic buttons only
    violations = [r for r in graphic_buttons if not r['passes']]  # Find violations

    # Compile results
    tap_results = {
        'html_file': html_path.name,  # Filename
        'viewport': f"{viewport_config['width']}px",  # Viewport width tested
        'total_tap_targets': len(results),  # Total interactive elements found
        'graphic_buttons': len(graphic_buttons),  # Count of graphic buttons
        'violations': violations,  # List of violations
        'violations_count': len(violations),  # Count of violations
        'min_tap_size': MIN_TAP_TARGET_SIZE,  # Minimum required size
        'passed': len(violations) == 0,  # Boolean pass/fail
    }  # Results dictionary

    return tap_results  # Return analysis results


async def check_line_spacing(html_path: Path, viewport_config: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """Check that line-height is at least 1.5x the font-size for all text elements.

    Args:
        html_path (Path): Path to HTML file to analyze
        viewport_config (Dict): Optional viewport configuration (default uses mobile viewport)

    Returns:
        Dict: Results containing line spacing violations and statistics
    """
    if viewport_config is None:  # Use mobile viewport if not specified
        viewport_config = VIEWPORTS["mobile"]  # Default to mobile viewport

    async with async_playwright() as p:  # Initialize Playwright context
        browser = await p.chromium.launch(headless=True)  # Launch headless browser
        context = await browser.new_context(
            viewport={'width': viewport_config['width'], 'height': 800}  # Set viewport dimensions
        )  # Create browser context with viewport
        page = await context.new_page()  # Create new page

        # Load HTML file
        file_url = html_path.resolve().as_uri()  # Convert path to file:// URL
        await page.goto(file_url)  # Navigate to HTML file
        await page.wait_for_load_state("networkidle")  # Wait for full load

        # Evaluate line spacing in browser context
        results = await page.evaluate(
            """(minRatio) => {
                function isVisible(el) {
                    const style = getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') return false;
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                }

                function cssPath(el) {
                    const path = [];
                    let current = el;
                    while (current && current.nodeType === 1 && current !== document.body) {
                        let selector = current.nodeName.toLowerCase();
                        if (current.id) {
                            selector += '#' + current.id;
                            path.unshift(selector);
                            break;
                        } else {
                            let sib = current;
                            let nth = 1;
                            while ((sib = sib.previousElementSibling)) {
                                if (sib.nodeName === current.nodeName) nth++;
                            }
                            selector += `:nth-of-type(${nth})`;
                        }
                        path.unshift(selector);
                        current = current.parentElement;
                    }
                    return path.join(' > ');
                }

                const results = [];
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_ELEMENT,
                    null
                );

                let node;
                while ((node = walker.nextNode())) {
                    if (!isVisible(node)) continue;

                    const text = node.innerText ? node.innerText.trim() : "";
                    if (!text) continue; // Skip elements without text

                    const style = getComputedStyle(node);
                    const fontSize = parseFloat(style.fontSize);
                    const lineHeight = parseFloat(style.lineHeight);

                    // Skip if lineHeight is NaN or not properly computed
                    if (isNaN(fontSize) || isNaN(lineHeight)) continue;

                    const ratio = lineHeight / fontSize;
                    const passes = ratio >= minRatio;

                    results.push({
                        tag: node.tagName.toLowerCase(),
                        selector: cssPath(node),
                        text: text.slice(0, 100),
                        fontSize: fontSize,
                        lineHeight: lineHeight,
                        ratio: ratio,
                        passes: passes
                    });
                }

                return results;
            }""",
            MIN_LINE_HEIGHT_RATIO
        )  # Execute JavaScript to analyze line spacing

        await browser.close()  # Clean up browser

    # Filter violations
    violations = [r for r in results if not r['passes']]  # Find violations

    # Compile results
    line_spacing_results = {
        'html_file': html_path.name,  # Filename
        'viewport': f"{viewport_config['width']}px",  # Viewport width tested
        'total_text_elements': len(results),  # Total text elements checked
        'violations': violations,  # List of violations
        'violations_count': len(violations),  # Count of violations
        'min_ratio': MIN_LINE_HEIGHT_RATIO,  # Minimum required ratio
        'passed': len(violations) == 0,  # Boolean pass/fail
    }  # Results dictionary

    return line_spacing_results  # Return analysis results


def check_viewport_meta_tag(html_path: Path) -> Dict[str, Any]:
    """Check if HTML file has proper viewport meta tag in head.

    Args:
        html_path (Path): Path to HTML file to analyze

    Returns:
        Dict: Results containing viewport meta tag presence and details
    """
    # Read HTML file content
    html_content = html_path.read_text(encoding='utf-8')  # Load HTML as string
    soup = BeautifulSoup(html_content, 'html.parser')  # Parse HTML structure

    # Find viewport meta tag in head
    viewport_meta = soup.find('meta', attrs={'name': 'viewport'})  # Look for viewport meta tag

    has_viewport_meta = viewport_meta is not None  # Check if tag exists
    viewport_content = None  # Initialize content value
    has_correct_attributes = False  # Initialize correctness flag

    if has_viewport_meta:  # If viewport meta tag exists
        viewport_content = viewport_meta.get('content', '')  # Get content attribute value

        # Check for required attributes in content
        content_lower = viewport_content.lower().replace(' ', '')  # Normalize content for comparison

        # Check if it contains the essential responsive attributes
        has_width_device = 'width=device-width' in content_lower  # Check for width=device-width
        has_initial_scale = 'initial-scale=1' in content_lower  # Check for initial-scale=1

        has_correct_attributes = has_width_device and has_initial_scale  # Both required

    # Compile results
    viewport_results = {
        'html_file': html_path.name,  # Filename
        'has_viewport_meta': has_viewport_meta,  # Tag exists
        'viewport_content': viewport_content,  # Content attribute value
        'has_correct_attributes': has_correct_attributes,  # Has required attributes
        'expected_content': 'width=device-width, initial-scale=1',  # Expected content
        'passed': has_viewport_meta and has_correct_attributes,  # Boolean pass/fail
    }  # Results dictionary

    return viewport_results  # Return analysis results


async def check_responsive_media(html_path: Path) -> Dict[str, Any]:
    """Check if images and videos use responsive sizing (percentage or max-width, not fixed pixels).

    Args:
        html_path (Path): Path to HTML file to analyze

    Returns:
        Dict: Results containing responsive media analysis
    """
    async with async_playwright() as pw:  # Initialize Playwright context
        browser = await pw.chromium.launch(headless=True)  # Launch headless browser
        context = await browser.new_context(viewport={'width': 375, 'height': 800})  # Mobile viewport
        page = await context.new_page()  # Create new page

        # Load HTML file
        file_url = f"file://{html_path.absolute()}"  # Convert to file URL
        await page.goto(file_url)  # Navigate to HTML file
        await page.wait_for_load_state("networkidle")  # Wait for full load

        # Check all img and video elements for responsive sizing
        media_elements = await page.evaluate("""
            () => {
                const elements = [];
                const mediaSelectors = ['img', 'video'];

                mediaSelectors.forEach(selector => {
                    const items = document.querySelectorAll(selector);
                    items.forEach(el => {
                        const computedStyle = window.getComputedStyle(el);
                        const inlineStyle = el.getAttribute('style') || '';
                        const widthAttr = el.getAttribute('width');
                        const heightAttr = el.getAttribute('height');

                        // Get width and max-width values
                        const width = computedStyle.width;
                        const maxWidth = computedStyle.maxWidth;
                        const inlineWidth = inlineStyle.match(/width\\s*:\\s*([^;]+)/i);
                        const inlineMaxWidth = inlineStyle.match(/max-width\\s*:\\s*([^;]+)/i);

                        // Check if using fixed pixel values
                        const hasFixedPixelWidth = (
                            (widthAttr && !widthAttr.includes('%')) ||
                            (inlineWidth && inlineWidth[1].trim().match(/^\\d+px$/))
                        );

                        const hasPercentageOrMaxWidth = (
                            (inlineWidth && inlineWidth[1].includes('%')) ||
                            (inlineMaxWidth && inlineMaxWidth[1].includes('%')) ||
                            maxWidth !== 'none'
                        );

                        // Determine if responsive
                        const isResponsive = !hasFixedPixelWidth || hasPercentageOrMaxWidth;

                        elements.push({
                            tag: selector,
                            src: el.src || el.getAttribute('src') || '(no src)',
                            width: width,
                            maxWidth: maxWidth,
                            inlineWidth: inlineWidth ? inlineWidth[1].trim() : null,
                            inlineMaxWidth: inlineMaxWidth ? inlineMaxWidth[1].trim() : null,
                            widthAttr: widthAttr,
                            heightAttr: heightAttr,
                            hasFixedPixelWidth: hasFixedPixelWidth,
                            isResponsive: isResponsive,
                            outerHTML: el.outerHTML.substring(0, 200)
                        });
                    });
                });

                return elements;
            }
        """)  # Get all media elements with their sizing properties

        await browser.close()  # Clean up browser

    # Analyze results
    total_media = len(media_elements)  # Total number of media elements
    non_responsive = [el for el in media_elements if not el['isResponsive']]  # Elements with fixed pixel sizing
    violations_count = len(non_responsive)  # Count violations

    # Compile results
    results = {
        'html_file': html_path.name,  # Filename
        'total_media_elements': total_media,  # Total img and video elements
        'responsive_count': total_media - violations_count,  # Elements using responsive sizing
        'violations_count': violations_count,  # Elements with fixed pixel sizing
        'violations': non_responsive,  # List of non-responsive elements
        'passed': violations_count == 0,  # Test passes if no violations
    }  # Results dictionary

    return results  # Return analysis results


async def check_relative_units(html_path: Path) -> Dict[str, Any]:
    """Check if containers use relative units (%, em, rem, vw, vh) instead of absolute units (px).

    This ensures text can reflow automatically when viewport changes.

    Args:
        html_path (Path): Path to HTML file to analyze

    Returns:
        Dict: Results containing violations of relative unit usage
    """
    async with async_playwright() as pw:  # Initialize Playwright context
        browser = await pw.chromium.launch(headless=True)  # Launch headless browser
        context = await browser.new_context(viewport={'width': 375, 'height': 800})  # Mobile viewport for testing
        page = await context.new_page()  # Create new page

        # Load HTML file
        file_url = f"file://{html_path.absolute()}"  # Convert to file URL
        await page.goto(file_url)  # Navigate to HTML file
        await page.wait_for_load_state("networkidle")  # Wait for full load

        # Check all container elements for absolute units
        results = await page.evaluate("""
            () => {
                // Properties to check for absolute units
                const propertiesToCheck = [
                    'width', 'maxWidth', 'minWidth',
                    'height', 'maxHeight', 'minHeight',
                    'fontSize', 'lineHeight',
                    'padding', 'paddingLeft', 'paddingRight', 'paddingTop', 'paddingBottom',
                    'margin', 'marginLeft', 'marginRight', 'marginTop', 'marginBottom'
                ];

                // Relative units that are good for responsive design
                const relativeUnits = ['%', 'em', 'rem', 'vw', 'vh', 'vmin', 'vmax', 'ch', 'ex'];

                // Absolute units to avoid
                const absoluteUnits = ['px', 'pt', 'cm', 'mm', 'in', 'pc'];

                function isVisible(el) {
                    const style = getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') return false;
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

                function checkUnit(value) {
                    if (!value || value === 'auto' || value === 'none' || value === 'normal' || value === '0px') {
                        return { type: 'auto', isAbsolute: false };
                    }

                    // Check for absolute units
                    for (const unit of absoluteUnits) {
                        if (value.includes(unit)) {
                            return { type: 'absolute', unit: unit, value: value, isAbsolute: true };
                        }
                    }

                    // Check for relative units
                    for (const unit of relativeUnits) {
                        if (value.includes(unit)) {
                            return { type: 'relative', unit: unit, value: value, isAbsolute: false };
                        }
                    }

                    // Unitless values (like line-height: 1.5)
                    if (!isNaN(parseFloat(value)) && value === parseFloat(value).toString()) {
                        return { type: 'unitless', value: value, isAbsolute: false };
                    }

                    return { type: 'unknown', value: value, isAbsolute: false };
                }

                function getInlineStyleValue(el, property) {
                    const inlineStyle = el.getAttribute('style') || '';
                    const regex = new RegExp(property + '\\\\s*:\\\\s*([^;]+)', 'i');
                    const match = inlineStyle.match(regex);
                    return match ? match[1].trim() : null;
                }

                const violations = [];

                // Check all container elements (divs, sections, articles, etc.)
                const containerSelectors = ['div', 'section', 'article', 'aside', 'header', 'footer', 'main', 'nav'];
                const containers = document.querySelectorAll(containerSelectors.join(','));

                containers.forEach(el => {
                    if (!isVisible(el)) return;

                    const elementViolations = [];
                    const computedStyle = getComputedStyle(el);

                    // Check each property
                    propertiesToCheck.forEach(prop => {
                        // First check inline styles (higher priority)
                        const inlineValue = getInlineStyleValue(el, prop);
                        if (inlineValue) {
                            const unitCheck = checkUnit(inlineValue);
                            if (unitCheck.isAbsolute) {
                                elementViolations.push({
                                    property: prop,
                                    value: inlineValue,
                                    unit: unitCheck.unit,
                                    source: 'inline'
                                });
                            }
                        }

                        // Also check computed styles for context
                        const computedValue = computedStyle[prop];
                        if (computedValue && !inlineValue) {
                            const unitCheck = checkUnit(computedValue);
                            // Only report computed absolute values for width/height related properties
                            if (unitCheck.isAbsolute &&
                                (prop.includes('width') || prop.includes('height') || prop === 'fontSize')) {
                                // Check if this might be inherited or from stylesheet
                                elementViolations.push({
                                    property: prop,
                                    value: computedValue,
                                    unit: unitCheck.unit,
                                    source: 'computed'
                                });
                            }
                        }
                    });

                    if (elementViolations.length > 0) {
                        const text = el.innerText ? el.innerText.trim().slice(0, 80) : '';
                        violations.push({
                            tag: el.tagName.toLowerCase(),
                            selector: cssPath(el),
                            violations: elementViolations,
                            text: text,
                            className: el.className || '',
                            id: el.id || ''
                        });
                    }
                });

                return violations;
            }
        """)  # Execute JavaScript to analyze unit usage

        await browser.close()  # Clean up browser

    # Analyze results
    total_containers_checked = len(results)  # Total containers analyzed
    containers_with_violations = len(results)  # Containers with absolute units

    # Count total violations across all containers
    total_violations = sum(len(r['violations']) for r in results)  # Total property violations

    # Compile results
    unit_results = {
        'html_file': html_path.name,  # Filename
        'total_containers_checked': total_containers_checked,  # Total containers analyzed
        'containers_with_violations': containers_with_violations,  # Containers using absolute units
        'total_violations': total_violations,  # Total property violations
        'violations': results,  # Detailed violation list
        'passed': total_violations == 0,  # Test passes if no absolute units found
        'recommendation': 'Use relative units (%, em, rem, vw, vh) instead of absolute units (px, pt) for responsive design'
    }  # Results dictionary

    return unit_results  # Return analysis results


# --- Playwright-based check for computed font sizes across viewports ---
async def check_computed_font_sizes_with_playwright(html_path: Path) -> Dict[str, Any]:
    """Use Playwright to compute final (cascaded) font sizes of all visible text elements
    across all configured VIEWPORTS, and report violations w.r.t. MIN_FONT_SIZE.

    Only checks elements that directly contain text, not parent containers.

    Args:
        html_path (Path): Path to the local HTML file.

    Returns:
        Dict[str, Any]: Summary + per-viewport details of violations.
    """
    # Prepare container for results
    per_viewport_results: Dict[str, Dict[str, Any]] = {}  # Results for each viewport

    async with async_playwright() as pw:  # Initialize Playwright context
        browser = await pw.chromium.launch(headless=True)  # Launch headless browser

        for viewport_name, viewport_config in VIEWPORTS.items():  # Iterate through each viewport
            # Create a new context for each viewport
            context = await browser.new_context(
                viewport={'width': viewport_config['width'], 'height': 800}  # Set viewport dimensions
            )  # Browser context with viewport
            page = await context.new_page()  # Create new page

            file_url = f"file://{html_path.absolute()}"  # Convert to file URL
            await page.goto(file_url)  # Navigate to HTML file
            await page.wait_for_load_state("networkidle")  # Wait for full load

            # Evaluate in-page: gather elements that directly contain text nodes,
            # not just parent containers. Check their computed font-size.
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

                    function hasDirectTextContent(el) {
                        // Check if element has text nodes as direct children (not nested in other elements)
                        for (let child of el.childNodes) {
                            if (child.nodeType === Node.TEXT_NODE && child.textContent.trim()) {
                                return true;
                            }
                        }
                        return false;
                    }

                    const out = [];
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, null);
                    let node;

                    while ((node = walker.nextNode())) {
                        if (!isVisible(node)) continue;

                        // Only check elements that directly contain text, not just parent containers
                        if (!hasDirectTextContent(node)) continue;

                        // Get direct text content only (not from child elements)
                        let directText = '';
                        for (let child of node.childNodes) {
                            if (child.nodeType === Node.TEXT_NODE) {
                                directText += child.textContent;
                            }
                        }
                        directText = directText.trim();

                        if (!directText) continue; // Skip if no direct text

                        const s = getComputedStyle(node);
                        const fs = s.fontSize;
                        const px = parseFloat(fs);

                        out.push({
                            tag: node.tagName.toLowerCase(),
                            selector: cssPath(node),
                            text: directText.slice(0, 120),
                            font_size: fs,
                            font_size_px: px,
                            ok: !Number.isNaN(px) && px >= minPx
                        });
                    }
                    return out;
                }""",
                MIN_FONT_SIZE,  # Minimum font size threshold
            )  # Execute JavaScript to analyze font sizes

            await context.close()  # Close browser context

            total_text_elements = len(results)  # Total elements checked
            violations = [r for r in results if not r.get("ok", False)]  # Filter violations

            per_viewport_results[viewport_name] = {
                "total_text_elements": total_text_elements,  # Total text elements
                "violations_count": len(violations),  # Number of violations
                "violations": violations,  # List of violation details
            }  # Store results for this viewport

        await browser.close()  # Close browser

    # Build summary across all viewports
    total_elems = sum(v["total_text_elements"] for v in per_viewport_results.values())  # Sum total elements
    total_violations = sum(v["violations_count"] for v in per_viewport_results.values())  # Sum violations

    return {
        "html_file": html_path.name,  # HTML filename
        "min_font_size": MIN_FONT_SIZE,  # Minimum font size threshold
        "total_text_elements": total_elems,  # Total text elements across all viewports
        "total_violations": total_violations,  # Total violations across all viewports
        "by_viewport": per_viewport_results,  # Per-viewport detailed results
        "passed": total_violations == 0,  # Test passed if no violations
    }  # Return complete results


async def capture_screenshot_at_viewport(
    html_path: Path,
    viewport_name: str,
    viewport_config: Dict[str, int],
    temp_dir: Path  # Temporary directory for screenshots
) -> Path:
    """Capture screenshot of HTML file at specified viewport size.

    Args:
        html_path (Path): Path to HTML file
        viewport_name (str): Name of viewport (mobile/tablet/desktop)
        viewport_config (Dict): Viewport dimensions (width and height)
        temp_dir (Path): Temporary directory to save screenshot

    Returns:
        Path: Path to saved screenshot file in temporary directory
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
        screenshot_path = temp_dir / screenshot_filename  # Full path in temp directory

        # Capture screenshot
        await page.screenshot(path=screenshot_path, full_page=True)  # Take full page screenshot

        await browser.close()  # Clean up browser

    return screenshot_path  # Return path to screenshot


async def generate_all_screenshots(html_path: Path) -> Tuple[Dict[str, Path], tempfile.TemporaryDirectory]:
    """Generate screenshots for all viewport sizes in a temporary directory.

    Args:
        html_path (Path): Path to HTML file to screenshot

    Returns:
        Tuple[Dict[str, Path], tempfile.TemporaryDirectory]:
            - Mapping of viewport names to screenshot paths
            - TemporaryDirectory object (caller must keep reference for cleanup)
    """
    # Create temporary directory for screenshots
    temp_dir_obj = tempfile.TemporaryDirectory(prefix="responsive_screenshots_")  # Auto-cleanup temp directory
    temp_dir = Path(temp_dir_obj.name)  # Convert to Path object

    screenshots = {}  # Dictionary to store screenshot paths

    # Generate screenshot for each viewport
    for viewport_name, viewport_config in VIEWPORTS.items():  # Iterate viewport configurations
        print(f"Generating {viewport_name} screenshot ({viewport_config['width']}px)...")  # Status message
        screenshot_path = await capture_screenshot_at_viewport(
            html_path,
            viewport_name,
            viewport_config,
            temp_dir  # Use temporary directory
        )  # Capture screenshot
        screenshots[viewport_name] = screenshot_path  # Store path
        print(f"  Saved: {screenshot_path}")  # Confirmation message

    return screenshots, temp_dir_obj  # Return screenshots and temp directory object


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


async def run_complete_test(html_file: Optional[str] = None):
    """Run complete responsive metrics test suite.

    Args:
        html_file (Optional[str]): Path to HTML file to test.
                                   If None, uses default from SOURCE_HTML constant.
    """
    print("=" * 70)  # Header separator
    print("RESPONSIVE METRICS TEST")  # Title
    print("=" * 70)  # Header separator

    temp_dir_obj = None  # Initialize temporary directory object

    try:  # Wrap in try-finally for cleanup
        # 0. Check viewport meta tag
        print("\n0. Checking viewport meta tag...")  # Section header

        # Determine HTML file path
        if html_file:  # If custom HTML file provided
            html_path = Path(html_file)  # Use provided path
        else:  # Use default
            html_path = DATA_DIR / SOURCE_HTML  # Path to source HTML

        print(f"Testing file: {html_path}")  # Show which file is being tested

        if not html_path.exists():  # Check if file exists
            print(f"ERROR: Source HTML file not found: {html_path}")  # Error message
            return  # Exit early

        viewport_meta_results = check_viewport_meta_tag(html_path)  # Check viewport meta tag

        print(f"\nViewport Meta Tag Results:")  # Results header
        print(f"  Has viewport meta tag: {'✓ YES' if viewport_meta_results['has_viewport_meta'] else '✗ NO'}")  # Tag presence
        if viewport_meta_results['has_viewport_meta']:  # If tag exists
            print(f"  Content: {viewport_meta_results['viewport_content']}")  # Show content
            print(f"  Has correct attributes: {'✓ YES' if viewport_meta_results['has_correct_attributes'] else '✗ NO'}")  # Correctness
        else:  # Tag missing
            print(f"  Expected: <meta name=\"viewport\" content=\"{viewport_meta_results['expected_content']}\" />")  # Show expected
        print(f"  Test passed: {'✓ YES' if viewport_meta_results['passed'] else '✗ NO'}")  # Pass/fail

        # 0a. Check responsive media (images and videos)
        print("\n0a. Checking responsive media (images and videos)...")  # Section header
        media_results = await check_responsive_media(html_path)  # Check media responsiveness

        print(f"\nResponsive Media Results:")  # Results header
        print(f"  Total media elements (img, video): {media_results['total_media_elements']}")  # Total media count
        print(f"  Responsive elements: {media_results['responsive_count']}")  # Responsive count
        print(f"  Non-responsive (fixed pixel width): {media_results['violations_count']}")  # Violations count
        print(f"  Test passed: {'✓ YES' if media_results['passed'] else '✗ NO'}")  # Pass/fail

        if media_results['violations']:  # Display violations if any
            print(f"\n  Violations (using fixed pixel width without max-width or percentage):")  # Violations header
            for i, violation in enumerate(media_results['violations'][:10], 1):  # Show first 10
                print(f"    {i}. <{violation['tag']}> width={violation['width']}")  # Element details
                if violation['widthAttr']:  # If has width attribute
                    print(f"       width attribute: {violation['widthAttr']}px")  # Width attr
                if violation['inlineWidth']:  # If has inline width style
                    print(f"       inline width: {violation['inlineWidth']}")  # Inline width
                print(f"       src: {violation['src'][:60]}...")  # Source (truncated)

        # 0b. Check for relative units usage
        print("\n0b. Checking for relative units (avoid absolute/pixel measures)...")  # Section header
        unit_results = await check_relative_units(html_path)  # Check unit usage

        print(f"\nRelative Units Analysis Results:")  # Results header
        print(f"  Total containers checked: {unit_results['total_containers_checked']}")  # Total containers
        print(f"  Containers with absolute units: {unit_results['containers_with_violations']}")  # Violations count
        print(f"  Total property violations: {unit_results['total_violations']}")  # Total violations
        print(f"  Test passed: {'✓ YES' if unit_results['passed'] else '✗ NO'}")  # Pass/fail

        if unit_results['violations']:  # Display violations if any
            print(f"\n  Violations (using absolute units like px, pt):")  # Violations header
            for i, violation in enumerate(unit_results['violations'][:10], 1):  # Show first 10
                print(f"    {i}. <{violation['tag']}> {violation['selector']}")  # Element details
                if violation['id']:  # If has ID
                    print(f"       id: {violation['id']}")  # Show ID
                if violation['className']:  # If has classes
                    print(f"       class: {violation['className'][:50]}")  # Show classes
                for v in violation['violations'][:3]:  # Show first 3 property violations
                    print(f"       - {v['property']}: {v['value']} ({v['source']})")  # Property violation
                if violation['text']:  # If has text content
                    print(f"       Text: {violation['text'][:60]}...")  # Text sample

        print(f"\n  Recommendation: {unit_results['recommendation']}")  # Show recommendation

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

        # 1b. Check tap targets (graphic buttons)
        print(f"\n1b. Checking tap targets (graphic buttons) - minimum {MIN_TAP_TARGET_SIZE}x{MIN_TAP_TARGET_SIZE}px...")  # Section header
        tap_results = await check_tap_targets(html_path)  # Analyze tap targets using mobile viewport

        print(f"\nTap Target Analysis Results:")  # Results header
        print(f"  Viewport: {tap_results['viewport']}")  # Viewport used
        print(f"  Total tap targets (buttons/links): {tap_results['total_tap_targets']}")  # Total interactive elements
        print(f"  Graphic buttons detected: {tap_results['graphic_buttons']}")  # Graphic button count
        print(f"  Violations found: {tap_results['violations_count']}")  # Violation count
        print(f"  Test passed: {'✓ YES' if tap_results['passed'] else '✗ NO'}")  # Pass/fail

        if tap_results['violations']:  # Display violations if any
            print(f"\n  Violations (size < {MIN_TAP_TARGET_SIZE}x{MIN_TAP_TARGET_SIZE}px):")  # Violations header
            for i, violation in enumerate(tap_results['violations'][:10], 1):  # Show first 10
                label = violation['ariaLabel'] or violation['text'] or '(no label)'  # Get label or text
                print(f"    {i}. <{violation['tag']}> {violation['width']:.1f}x{violation['height']:.1f}px")  # Violation details
                print(f"       Label/Text: {label[:40]}")  # Label or text sample

        # 1c. Check line spacing (line-height to font-size ratio)
        print(f"\n1c. Checking line spacing - minimum ratio {MIN_LINE_HEIGHT_RATIO}:1...")  # Section header
        line_spacing_results = await check_line_spacing(html_path)  # Analyze line spacing using mobile viewport

        print(f"\nLine Spacing Analysis Results:")  # Results header
        print(f"  Viewport: {line_spacing_results['viewport']}")  # Viewport used
        print(f"  Total text elements checked: {line_spacing_results['total_text_elements']}")  # Total elements
        print(f"  Violations found: {line_spacing_results['violations_count']}")  # Violation count
        print(f"  Test passed: {'✓ YES' if line_spacing_results['passed'] else '✗ NO'}")  # Pass/fail

        if line_spacing_results['violations']:  # Display violations if any
            print(f"\n  Violations (line-height/font-size < {MIN_LINE_HEIGHT_RATIO}):")  # Violations header
            for i, violation in enumerate(line_spacing_results['violations'][:10], 1):  # Show first 10
                print(f"    {i}. <{violation['tag']}> ratio={violation['ratio']:.2f} (font:{violation['fontSize']:.1f}px, line-height:{violation['lineHeight']:.1f}px)")  # Violation details
                print(f"       Selector: {violation['selector']}")  # CSS selector
                print(f"       Text: {violation['text'][:60]}")  # Text sample

        # 2. Generate screenshots in temporary directory
        print(f"\n2. Generating screenshots at different viewports in temporary directory...")  # Section header
        screenshots, temp_dir_obj = await generate_all_screenshots(html_path)  # Generate all screenshots
        print(f"  Temporary directory: {temp_dir_obj.name}")  # Show temp directory location

        # 3. Load ground truth images
        print(f"\n3. Loading ground truth images...")  # Section header
        ground_truth = load_ground_truth_images()  # Load ground truth

        # 4. Compare screenshots with ground truth
        print(f"\n4. Comparing screenshots with ground truth...")  # Section header
        comparisons = await compare_screenshots_with_ground_truth(screenshots, ground_truth)  # Run comparisons

        # 5. Layout Similarity Summary
        print(f"\n5. Calculating layout similarity with ground truth...")  # Section header

        # Run layout_similarity in a separate thread to avoid async/sync conflict
        loop = asyncio.get_event_loop()  # Get current event loop
        input_list = [[str(html_path)], str(DATA_DIR / GROUND_TRUTH_HTML)]  # Prepare input paths

        # Execute layout_similarity in thread pool to avoid Playwright sync/async conflict
        with concurrent.futures.ThreadPoolExecutor() as executor:  # Create thread pool executor
            future = loop.run_in_executor(
                executor,
                layout_similarity,
                input_list
            )  # Submit layout_similarity to thread pool
            final_layout_scores, layout_multi_scores = await future  # Wait for completion

        print(f"Final Layout Similarity Score (LSS) between {html_path.name} and ground truth: {final_layout_scores[0]:.4f}")  # Show LSS
        print(f"Layout score size: {len(layout_multi_scores)}, final score size: {len(final_layout_scores)}")  # Show counts
        print(f"Layout multi-scale scores: {layout_multi_scores[0]}")  # Show per-viewport LSS

        # Summary
        print("\n" + "=" * 70)  # Footer separator
        print("TEST SUMMARY")  # Summary title
        print("=" * 70)  # Footer separator
        print(f"Viewport meta tag: {'PASSED' if viewport_meta_results['passed'] else 'FAILED'}")  # Viewport meta test result
        print(f"Responsive media (images/videos): {'PASSED' if media_results['passed'] else 'FAILED'}")  # Responsive media test result
        print(f"Relative units (avoid px): {'PASSED' if unit_results['passed'] else 'FAILED'}")  # Relative units test result
        print(f"Computed font-size validation: {'PASSED' if computed_results['passed'] else 'FAILED'}")  # Computed font test result
        print(f"Tap target validation: {'PASSED' if tap_results['passed'] else 'FAILED'}")  # Tap target test result
        print(f"Line spacing validation: {'PASSED' if line_spacing_results['passed'] else 'FAILED'}")  # Line spacing test result
        print(f"Screenshots generated: {len(screenshots)}")  # Screenshot count
        print(f"Comparisons completed: {len(comparisons)}")  # Comparison count
        print("=" * 70)  # Footer separator

    finally:  # Cleanup temporary directory
        if temp_dir_obj is not None:  # If temporary directory was created
            temp_dir_obj.cleanup()  # Clean up temporary files
            print(f"\nTemporary screenshot directory cleaned up.")  # Cleanup confirmation


if __name__ == "__main__":  # Script entry point
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Test HTML files for responsive design metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python responsive-metrics.py                          # Use default file
  python responsive-metrics.py --html data/58.html     # Test specific file
  python responsive-metrics.py --html /path/to/page.html
        """
    )  # Create argument parser

    parser.add_argument(
        '--html',
        type=str,
        default=None,
        help=f'Path to HTML file to test (default: {DATA_DIR / SOURCE_HTML})'
    )  # Add HTML file argument

    args = parser.parse_args()  # Parse arguments

    asyncio.run(run_complete_test(args.html))  # Execute complete test suite with custom HTML file
