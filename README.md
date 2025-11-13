# webTesting

A comprehensive web testing framework using Selenium and Playwright for authentication automation, responsive design testing, and layout analysis. This project includes examples for logging into popular platforms (Google, Facebook, Instagram), performing responsive design validation, and calculating layout similarity metrics.

## Features

### 🔐 Authentication & Session Management
- **Google**: Login automation with Selenium and Playwright
- **Facebook**: Login automation with Selenium
- **Instagram**: Login automation with Selenium and Playwright
- **Session persistence**: Cookie/storage state reuse across sessions

### 📱 Responsive Design Testing
- **Viewport testing**: Test websites at mobile (375px), tablet (1024px), and desktop (1280px) viewports
- **Horizontal scroll detection**: Identify responsive design issues
- **Screenshot generation**: Capture screenshots at multiple viewport sizes

### 📊 Responsive Metrics Analysis
Comprehensive HTML file analysis with the following metrics:

#### Viewport & Meta Tags
- Viewport meta tag validation (presence and correctness)
- Responsive media elements (images/videos) sizing analysis
- Relative vs absolute units detection (%, em, rem vs px, pt)

#### Typography & Accessibility
- **Font size validation**: Minimum 12px across all viewports (mobile/tablet/desktop)
- **Line spacing**: Line-height to font-size ratio validation (minimum 1.5:1)
- **Tap target sizes**: Interactive elements minimum 48x48px (accessibility compliance)

#### Visual Comparison
- Screenshot comparison with ground truth images
- Pixel-level difference metrics (MSE, RMSE, percentage difference)
- Layout Similarity Score (LSS) using weighted IoU

## Setup

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install
```

## Environment Variables

Configure credentials for authentication scripts:

### Google (Selenium/Playwright)
- `GOOGLE_USER`: Google account email
- `GOOGLE_PASS`: Google account password
- `GOOGLE_SEARCH`: (Optional) Search query to perform after login

### Facebook (Selenium)
- `FB_USER`: Facebook account email/username
- `FB_PASS`: Facebook account password
- `FB_SEARCH`: (Optional) Search query to perform after login
- `FB_HEADLESS`: (Optional) Set to `1` to run browser in headless mode

### Instagram
- `IG_USER`: Instagram username
- `IG_PASS`: Instagram password
- `IG_HEADLESS`: (Optional) Set to `1` to run browser in headless mode

**Note**: Use test accounts only. 2FA or security challenges may block automation.

## Usage

### Authentication Scripts

#### Google
```bash
# Selenium
python selenium_google.py

# Playwright
python playwright_google.py
```

#### Facebook
```bash
python selenium_facebook.py
```

#### Instagram
```bash
# Selenium
python selenium_instagram.py

# Playwright
python playwright_instagram.py
```

### Responsive Testing

#### Website Responsiveness Test (`playwright_responsive.py`)
Tests a target website at 480px viewport width for horizontal scrolling issues:
```bash
python playwright_responsive.py
```

**Metrics:**
- Viewport dimensions (width × height)
- Page content dimensions (scroll width × scroll height)
- Horizontal scroll availability
- Horizontal scroll position tracking
- Overflow element count

**Output**: Screenshots saved in `out/` directory:
- `{domain}_before-scroll_{timestamp}.png`
- `{domain}_after-scroll_{timestamp}.png` (if scrolling occurred)
- `{domain}_no-scroll-needed_{timestamp}.png` (if no scrolling needed)

#### Responsive Metrics Analysis (`responsive-metrics.py`)
Comprehensive HTML file analysis for responsive design compliance:

```bash
# Use default file (data/58-v2-gpt5.html)
python responsive-metrics.py

# Specify custom HTML file
python responsive-metrics.py --html path/to/file.html
```

**Metrics Tested:**
1. **Viewport Meta Tag**: Validates presence and correctness
2. **Responsive Media**: Checks if images/videos use responsive sizing
3. **Relative Units**: Detects absolute pixel usage in containers
4. **Font Sizes**: Validates minimum 12px across all viewports
5. **Tap Targets**: Ensures interactive elements meet 48×48px minimum
6. **Line Spacing**: Validates line-height ratio (minimum 1.5:1)
7. **Screenshot Generation**: Creates screenshots for mobile/tablet/desktop
8. **Visual Comparison**: Compares with ground truth images (MSE, RMSE, % diff)
9. **Layout Similarity**: Calculates LSS (Layout Similarity Score) using weighted IoU

**Output**: Console report with pass/fail status for each metric, plus temporary screenshots for visual inspection.

### Layout Similarity (`layout_similarity.py`)
Calculates layout similarity between predicted and reference HTML files:

```bash
python layout_similarity.py
```

**Metrics:**
- **Weighted IoU Score**: Overall layout similarity (0-1 scale)
- **Multi-scale Scores**: Per-element-type similarity breakdown (video, image, text_block, form_table, button, nav_bar, divider)

**Algorithm**: Uses Shapely geometric operations for accurate bounding box intersection calculations.

## Project Structure

```
webTesting/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Pytest configuration
│
├── Authentication Scripts
│   ├── selenium_google.py       # Google login (Selenium)
│   ├── playwright_google.py     # Google login (Playwright)
│   ├── selenium_facebook.py     # Facebook login (Selenium)
│   ├── selenium_instagram.py    # Instagram login (Selenium)
│   └── playwright_instagram.py  # Instagram login (Playwright)
│
├── Responsive Testing
│   ├── playwright_responsive.py # Website viewport testing
│   └── responsive-metrics.py    # HTML file metrics analysis
│
├── Layout Analysis
│   ├── layout_similarity.py     # Layout similarity calculation
│   └── html_utils.py            # Visual component extraction utilities
│
├── Data & Output
│   ├── data/                    # Test HTML files and ground truth images
│   │   ├── *.html               # HTML test files
│   │   ├── *-gt-*.png           # Ground truth screenshots
│   │   └── eval/                # Evaluation dataset
│   ├── out/                     # Generated screenshots
│   └── output_visual_scores/    # Layout similarity results
│
├── Session Files (Generated)
│   ├── selenium_cookies.pkl     # Google (Selenium)
│   ├── fb_cookies.pkl           # Facebook (Selenium)
│   ├── ig_cookies.pkl           # Instagram (Selenium)
│   ├── playwright_state.json    # Google (Playwright)
│   └── playwright_ig_state.json # Instagram (Playwright)
│
└── tests/                       # Unit tests
    ├── __init__.py
    └── test_hello.py
```

## Dependencies

Key libraries used:

- **selenium** (≥4.8.0): Web browser automation
- **playwright** (≥1.32.0): Modern browser automation
- **beautifulsoup4** (≥4.12.0): HTML parsing
- **Pillow** (≥10.0.0): Image processing
- **numpy** (≥1.24.0): Numerical computations
- **shapely** (≥2.0.1): Geometric operations
- **pytest** (≥7.0.0): Testing framework
- **tqdm** (≥4.65.0): Progress bars

See `requirements.txt` for complete list.

## Metrics Reference

### Responsive Design Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| **Viewport Meta Tag** | Present & Correct | Must include `width=device-width, initial-scale=1` |
| **Font Size** | ≥12px | Minimum readable font size across all viewports |
| **Tap Target Size** | ≥48×48px | Accessibility requirement for interactive elements |
| **Line Spacing** | ≥1.5:1 | Line-height to font-size ratio for readability |
| **Responsive Media** | Percentage/Max-width | Images/videos should use flexible sizing |
| **Relative Units** | Preferred | Use %, em, rem, vw, vh instead of px, pt |

### Visual Comparison Metrics

| Metric | Description |
|--------|-------------|
| **MSE** | Mean Squared Error (pixel-level difference) |
| **RMSE** | Root Mean Squared Error |
| **% Difference** | Percentage difference between images |
| **Layout Similarity Score (LSS)** | Weighted IoU of visual components (0-1 scale) |

### Layout Components Analyzed

The layout similarity analysis extracts and compares:
- **Video**: `<video>` elements
- **Image**: `<img>` elements
- **Text Block**: Text-containing elements (p, span, h1-h6, li, td, th, etc.)
- **Form/Table**: Form and table elements
- **Button**: Interactive buttons and inputs
- **Navigation Bar**: Navigation elements
- **Divider**: Horizontal rules and separators

## Examples

### Example 1: Test Website Responsiveness
```bash
# Edit TARGET_URL in playwright_responsive.py if needed
python playwright_responsive.py
# Check out/ directory for screenshots
```

### Example 2: Analyze HTML File
```bash
# Test default HTML file
python responsive-metrics.py

# Test custom file
python responsive-metrics.py --html data/my-page.html
```

### Example 3: Calculate Layout Similarity
```python
from layout_similarity import layout_similarity

predict_html_list = ["data/page1.html", "data/page2.html"]
reference_html = "data/reference.html"

scores, multi_scores = layout_similarity([predict_html_list, reference_html])
print(f"Layout Similarity Score: {scores[0]:.4f}")
```

## Troubleshooting

### Playwright Installation Issues
If `playwright install` fails, try:
```bash
python -m playwright install chromium
```

### Session Persistence Issues
- Ensure write permissions in project directory
- Delete old session files if experiencing authentication errors
- Check that cookies/storage state files are not corrupted

### Responsive Metrics Errors
- Ensure HTML file path is correct
- Check that `data/` directory exists for ground truth images
- Verify HTML files are valid (check for syntax errors)

## License

[Add your license here]

## Contributing

[Add contributing guidelines here]
