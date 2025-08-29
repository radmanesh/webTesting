# webTesting

Selenium and Playwright examples for logging into Google, Facebook, and Instagram, performing basic actions (e.g., search), and reusing sessions via cookies/storage state.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install  # install browsers for Playwright
```

## Environment variables

- Google (Selenium/Playwright):
	- GOOGLE_USER, GOOGLE_PASS, optional GOOGLE_SEARCH
- Facebook (Selenium):
	- FB_USER, FB_PASS, optional FB_SEARCH, optional FB_HEADLESS=1
- Instagram:
	- IG_USER, IG_PASS, optional IG_HEADLESS=1

Use test accounts; 2FA or challenges can block automation.

## Run

```bash
# Google
python selenium_google.py
python playwright_google.py

# Facebook
python selenium_facebook.py

# Instagram
python selenium_instagram.py
python playwright_instagram.py

# Responsive testing (Amazon)
python playwright_responsive.py
```

## Session files

- Selenium: `selenium_cookies.pkl` (Google), `fb_cookies.pkl` (Facebook), `ig_cookies.pkl` (Instagram)
- Playwright: `playwright_state.json` (Google), `playwright_ig_state.json` (Instagram)

