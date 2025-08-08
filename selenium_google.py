import os
import pickle
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

EMAIL = os.getenv("GOOGLE_USER")
PASSWORD = os.getenv("GOOGLE_PASS")
COOKIE_FILE = "selenium_cookies.pkl"

def load_cookies(driver):
    """Load cookies if previously saved."""
    driver.get("https://www.google.com")
    if os.path.exists(COOKIE_FILE):
        for cookie in pickle.load(open(COOKIE_FILE, "rb")):
            driver.add_cookie(cookie)
        driver.refresh()

def save_cookies(driver):
    """Persist cookies to disk."""
    pickle.dump(driver.get_cookies(), open(COOKIE_FILE, "wb"))


def login_and_search():
    driver = webdriver.Chrome()
    load_cookies(driver)
    # If not already signed in, log in
    if "Sign in" in driver.page_source:
        driver.find_element(By.LINK_TEXT, "Sign in").click()
        driver.find_element(By.ID, "identifierId").send_keys(EMAIL, Keys.ENTER)
        time.sleep(2)
        driver.find_element(By.NAME, "password").send_keys(PASSWORD, Keys.ENTER)
        time.sleep(3)
        save_cookies(driver)
    # Perform a search
    search = driver.find_element(By.NAME, "q")
    search.send_keys("web automation with selenium", Keys.ENTER)
    time.sleep(5)
    driver.quit()


if __name__ == "__main__":
    if not EMAIL or not PASSWORD:
        raise EnvironmentError("Please set GOOGLE_USER and GOOGLE_PASS environment variables")
    login_and_search()
