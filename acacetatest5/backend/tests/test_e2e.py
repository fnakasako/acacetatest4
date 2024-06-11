import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

def test_user_flow():
    # Correct path to the chromedriver executable
    service = Service('/Users/frank/Desktop/chromedriver/chromedriver')
    driver = webdriver.Chrome(service=service)
    
    # Your test code here
    driver.get("https://www.google.com")
    print(driver.title)
    driver.quit()

# Run the test function
if __name__ == "__main__":
    test_user_flow()
