import pandas as pd
import json
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def patch_driver_for_stealth(driver):
    """Add stealth JavaScript to avoid detection"""
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
    })
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

def main():
    # Configuration
    INPUT_CSV = "data/sample_queries.csv"
    OUTPUT_DIR = "data/test_results"
    MAX_QUERIES = 3
    
    # Create output directory
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    # Load queries
    print("Loading queries...")
    df = pd.read_csv(INPUT_CSV)
    queries = df['query'].tolist()[:MAX_QUERIES]
    print(f"Loaded {len(queries)} queries\n")
    
    # Setup Chrome
    print("Starting Chrome...")
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    service = Service('/usr/local/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    patch_driver_for_stealth(driver)
    
    print("Chrome started!\n")
    
    all_results = []
    
    # Search each query
    for i, query in enumerate(queries, 1):
        print(f"[{i}/{len(queries)}] Searching: '{query}'")
        
        try:
            driver.get('https://www.google.com')
            time.sleep(3)
            
            # Check for CAPTCHA
            if '/sorry/' in driver.current_url:
                print("  ⚠ CAPTCHA detected! Solve it manually, then press Enter...")
                input()
            
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, 'q'))
            )
            search_box.clear()
            search_box.send_keys(query)
            search_box.submit()
            time.sleep(4)
            
            current_url = driver.current_url
            
            if '/sorry/' in current_url:
                print("  ✗ Blocked by Google")
                continue
            
            # Find results
            result_containers = []
            for selector in ['div.g', 'div.MjjYud']:
                result_containers = driver.find_elements(By.CSS_SELECTOR, selector)
                if result_containers:
                    break
            
            print(f"  Found {len(result_containers)} containers")
            
            # Parse results
            parsed = 0
            for idx, container in enumerate(result_containers[:10]):
                try:
                    title = None
                    try:
                        title = container.find_element(By.TAG_NAME, 'h3').text
                    except:
                        pass
                    
                    url = None
                    try:
                        url = container.find_element(By.TAG_NAME, 'a').get_attribute('href')
                    except:
                        pass
                    
                    snippet = None
                    for sel in ['div.VwiC3b', 'div.lyLwlc']:
                        try:
                            snippet = container.find_element(By.CSS_SELECTOR, sel).text
                            if snippet:
                                break
                        except:
                            continue
                    
                    if title or url:
                        all_results.append({
                            'query': query,
                            'rank': idx + 1,
                            'title': title,
                            'url': url,
                            'snippet': snippet
                        })
                        parsed += 1
                        
                        if idx == 0:
                            print(f"  Sample: {title[:50] if title else 'No title'}...")
                
                except:
                    continue
            
            print(f"  ✓ Parsed {parsed} results\n")
            time.sleep(7)
            
        except Exception as e:
            print(f"  ✗ Error: {e}\n")
    
    driver.quit()
    print("Browser closed.\n")
    
    # Save results
    if all_results:
        json_file = f"{OUTPUT_DIR}/results.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        csv_file = f"{OUTPUT_DIR}/results.csv"
        pd.DataFrame(all_results).to_csv(csv_file, index=False)
        
        print(f"✅ SUCCESS! Captured {len(all_results)} results")
        print(f"JSON: {json_file}")
        print(f"CSV: {csv_file}\n")
        
        for result in all_results[:3]:
            print(f"  • {result['title'][:60] if result['title'] else 'No title'}...")
    else:
        print("⚠ No results captured")

if __name__ == '__main__':
    main()