import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import re
import time

# Input keyword
text = input("Enter the keyword to search: ")

# Setup Chrome WebDriver
service = Service(executable_path="chromedriver.exe")
driver = webdriver.Chrome(service=service)

# Open the clinical trials website
driver.get("https://clinicaltrials.gov/")

# Wait until the search box is clickable and perform the search
WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.NAME, "advcond"))
)
input_element = driver.find_element(By.NAME, "advcond")
input_element.send_keys(text + Keys.ENTER)

# Wait for the search results to load
time.sleep(10)

# Extract the number of studies
try:
    results_text = driver.find_element(By.CSS_SELECTOR, "p.shown-range.font-body-md.ng-star-inserted").text
    print(f"Results text: {results_text}")
    total_studies = int(re.search(r'out of ([\d,]+) studies', results_text).group(1).replace(',', ''))
    print(f"Total number of studies: {total_studies}")
except Exception as e:
    print(f"Error extracting number of studies: {e}")
    total_studies = 0

# Calculate the number of pages
studies_per_page = 100
num_pages = (total_studies // studies_per_page) + 1

# Function to extract NCT IDs from a single page
def extract_nct_ids():
    time.sleep(5)  # Wait for the page to load
    nct_elements = driver.find_elements(By.CSS_SELECTOR, "div.nct-id")
    return [elem.text for elem in nct_elements]

# Initialize list to store all NCT IDs and URLs
all_nct_ids = []

# Loop through all pages and extract NCT IDs
for page_num in range(num_pages):
    url = f"https://clinicaltrials.gov/search?cond={text}&limit=100&rank={page_num*100+1}"
    driver.get(url)
    nct_ids = extract_nct_ids()
    all_nct_ids.extend(nct_ids)

# Create a DataFrame and generate URLs
data = []
for rank, nct_id in enumerate(all_nct_ids, start=1):
    study_url = f"https://clinicaltrials.gov/study/{nct_id}?cond={text}&limit=100&rank={rank}"
    data.append({"NCT-ID": nct_id, "URL": study_url})

# Define the file path
file_path = "nct_ids_with_urls.xlsx"

# Check if the file exists and delete it if it does
if os.path.exists(file_path):
    os.remove(file_path)
    print(f"Deleted existing file: {file_path}")

# Create a DataFrame and save to Excel
df = pd.DataFrame(data)
df.to_excel(file_path, index=False)

print(f"NCT IDs and URLs have been saved to {file_path}")

driver.quit()



