# webTesting

This repository demonstrates simple Selenium and Playwright scripts that log into Google
using a username and password, perform a search, and store session data so
subsequent runs skip the login step.

## Setup

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install  # downloads browsers for Playwright
```

Set environment variables with your credentials:

```bash
export GOOGLE_USER="you@example.com"
export GOOGLE_PASS="your_password"
```

Use a test account without 2FA. Google may block automated logins.

## Running the scripts

- **Selenium**: `python selenium_google.py`
- **Playwright**: `python playwright_google.py`

Each script saves authentication state (`selenium_cookies.pkl` or
`playwright_state.json`) so later executions can reuse the session.
