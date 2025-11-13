# scripts/run_all_queries.py
import os
import time
import csv
import math
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# ======================
# CONFIGURATION
# ======================
BATCH_SIZE = 100  # Number of queries per browser session
MAX_RETRIES = 3   # Retries per query
DATA_DIR = "data/final_results"
QUERY_FILE = "data/search_arena_user_messages_filtered_20251109_1409.csv"

os.makedirs(DATA_DIR, exist_ok=True)

# ======================
# FUNCTIONS
# ======================
def init_chrome():
    """Initialize a new Chrome session."""
    options = Options()
    options.add_argument("--headless")  # remove if you want to see browser
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    service = Service()  # use default chromedriver in PATH
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver

def load_queries(file_path):
    """Load queries from CSV file."""
    queries = []
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if row:  # skip empty rows
                queries.append(row[0])
    return queries

def save_results(results, batch_num):
    """Save batch results to CSV."""
    file_path = os.path.join(DATA_DIR, f"partial_results_batch{batch_num}_final.csv")
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["query", "result"])
        for query, result in results:
            writer.writerow([query, result])
    print(f"💾 Saved partial results: {file_path}")

def run_search(driver, query):
    """Run search using Selenium and return result (mocked here)."""
    # Replace the below with your actual search logic
    driver.get("https://www.google.com")
    time.sleep(1)
    return f"Result for '{query}'"

# ======================
# MAIN BATCH PROCESS
# ======================
def main():
    queries = load_queries(QUERY_FILE)
    total_batches = math.ceil(len(queries) / BATCH_SIZE)

    for batch_num in range(total_batches):
        batch_queries = queries[batch_num * BATCH_SIZE : (batch_num + 1) * BATCH_SIZE]
        print(f"\n🚀 Starting batch {batch_num + 1}/{total_batches} ({len(batch_queries)} queries)")
        results = []

        driver = init_chrome()

        for i, query in enumerate(batch_queries, start=1):
            for attempt in range(MAX_RETRIES):
                try:
                    print(f"[{i}/{len(batch_queries)}] Searching: '{query}'")
                    result = run_search(driver, query)
                    results.append((query, result))
                    break  # success
                except Exception as e:
                    print(f"⚠ Error with query '{query}': {e}")
                    if attempt < MAX_RETRIES - 1:
                        print("Retrying with new Chrome session...")
                        driver.quit()
                        driver = init_chrome()
                    else:
                        print("Max retries reached. Skipping query.")
                        results.append((query, "ERROR"))

        driver.quit()
        save_results(results, batch_num + 1)

if __name__ == "__main__":
    main()