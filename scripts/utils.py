import pandas as pd
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import glob

def setup_chrome_driver(chrome_path="/usr/local/bin/chromedriver"):
    """Initialize ChromeDriver with stealth options"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    service = Service(chrome_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Stealth patch
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                     'AppleWebKit/537.36 (KHTML, like Gecko) '
                     'Chrome/142.0.0.0 Safari/537.36'
    })
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def chunk_queries(df, chunk_size=500):
    """Split DataFrame into chunks"""
    return [df[i:i+chunk_size] for i in range(0, len(df), chunk_size)]

def save_partial_results(all_results, output_dir, batch_name):
    """Save intermediate results"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    file_path = f"{output_dir}/partial_results_{batch_name}.csv"
    pd.DataFrame(all_results).to_csv(file_path, index=False)
    print(f"💾 Saved partial results: {file_path}")

def merge_partial_results(output_dir, final_csv=None):
    """Merge all partial CSVs in output_dir into one final CSV"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    partial_files = glob.glob(f"{output_dir}/partial_results_*.csv")
    if not partial_files:
        print("⚠ No partial files found.")
        return None
    merged_df = pd.concat([pd.read_csv(f) for f in partial_files], ignore_index=True)
    merged_df.drop_duplicates(subset=["query", "url"], inplace=True)
    if not final_csv:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        final_csv = f"{output_dir}/google_results_all_{timestamp}.csv"
    merged_df.to_csv(final_csv, index=False)
    print(f"🎯 Merged all partial results into: {final_csv}")
    return final_csv