#!/usr/bin/env python3
import pandas as pd
import json
import time
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_chrome(headless=True):
    """Setup Chrome with optimal settings"""
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.page_load_strategy = 'eager'  # Faster page loads
    
    if headless:
        chrome_options.add_argument('--headless=new')
    
    service = Service('/usr/local/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def extract_result(container, rank, query):
    """Extract result data"""
    result = {
        'rank': rank,
        'query': query,
        'title': None,
        'url': None,
        'domain': None,
        'snippet': None,
        'snippet_length': 0,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        try:
            h3 = container.find_element(By.TAG_NAME, 'h3')
            result['title'] = h3.text.strip() if h3.text else None
        except:
            pass
        
        try:
            link = container.find_element(By.TAG_NAME, 'a')
            url = link.get_attribute('href')
            if url and url.startswith('http'):
                result['url'] = url
                from urllib.parse import urlparse
                result['domain'] = urlparse(url).netloc
        except:
            pass
        
        snippets = []
        for selector in ['div.VwiC3b', 'div.lyLwlc', 'span.aCOpRe', 'div.IsZvec']:
            try:
                elements = container.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    if text and len(text) > 20:
                        snippets.append(text)
            except:
                continue
        
        if snippets:
            result['snippet'] = max(snippets, key=len)
            result['snippet_length'] = len(result['snippet'])
    except:
        pass
    
    return result

def search_query(driver, query, delay_after=2):
    """Search a single query with smart retry"""
    max_retries = 2
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            driver.get('https://www.google.com')
            time.sleep(0.5)
            
            search_box = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.NAME, 'q'))
            )
            search_box.clear()
            search_box.send_keys(query)
            search_box.submit()
            time.sleep(1.5)
            
            # Check if blocked
            if '/sorry/' in driver.current_url:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None, 'blocked'
            
            # Get results
            results = []
            result_containers = []
            for selector in ['div.g', 'div.MjjYud']:
                result_containers = driver.find_elements(By.CSS_SELECTOR, selector)
                if result_containers:
                    break
            
            if not result_containers:
                return [], 'no_results'
            
            for idx, container in enumerate(result_containers[:10]):
                try:
                    result = extract_result(container, idx + 1, query)
                    if result['title'] or result['url']:
                        results.append(result)
                except:
                    continue
            
            time.sleep(delay_after)
            return results, 'success'
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return None, str(e)
    
    return None, 'failed'

def save_results(results, output_dir, filename):
    """Save results"""
    if not results:
        return
    
    json_file = output_dir / f'{filename}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    df = pd.DataFrame(results)
    csv_file = output_dir / f'{filename}.csv'
    df.to_csv(csv_file, index=False, encoding='utf-8')

def main():
    # Configuration - OPTIMIZED FOR SPEED + RELIABILITY
    INPUT_CSV = "data/search_arena_user_messages_filtered_20251109_1409.csv"
    OUTPUT_DIR = Path("data/smart_batch_results")
    MAX_QUERIES = None  # Set to None for all queries
    BASE_DELAY = 2  # Base delay between queries
    BATCH_SIZE = 100
    HEADLESS = True
    
    # Adaptive delay - starts fast, slows down if blocked
    current_delay = BASE_DELAY
    blocked_count = 0
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("Loading queries...")
    df = pd.read_csv(INPUT_CSV)
    queries = df['query'].tolist()
    
    if MAX_QUERIES:
        queries = queries[:MAX_QUERIES]
    
    total_queries = len(queries)
    print(f"Processing {total_queries} queries")
    print(f"Headless: {HEADLESS}")
    print(f"Initial delay: {BASE_DELAY}s")
    print(f"Estimated time: {total_queries * 4 / 60:.1f} minutes\n")
    
    print("Starting Chrome...")
    driver = setup_chrome(headless=HEADLESS)
    print("Chrome ready!\n")
    
    all_results = []
    batch_results = []
    stats = {'successful': 0, 'failed': 0, 'blocked': 0, 'no_results': 0}
    batch_num = 1
    start_time = time.time()
    
    print(f"{'='*70}")
    print("Starting smart batch search...")
    print(f"{'='*70}\n")
    
    for i, query in enumerate(queries, 1):
        print(f"[{i}/{total_queries}] {query[:55]}...", end=' ')
        
        results, status = search_query(driver, query, delay_after=current_delay)
        
        if status == 'success':
            num_results = len(results) if results else 0
            if num_results > 0:
                avg_snippet = sum(r.get('snippet_length', 0) for r in results) / num_results
                print(f"✓ {num_results} results ({avg_snippet:.0f} chars)")
                all_results.extend(results)
                batch_results.extend(results)
                stats['successful'] += 1
                blocked_count = 0  # Reset on success
                
                # Speed up if going well
                if i % 20 == 0 and blocked_count == 0:
                    current_delay = max(1.5, current_delay - 0.2)
            else:
                print("⚠ No results")
                stats['no_results'] += 1
                
        elif status == 'blocked':
            print("✗ BLOCKED - Slowing down...")
            stats['blocked'] += 1
            blocked_count += 1
            
            # Adaptive slowdown
            current_delay = min(10, current_delay + 2)
            time.sleep(30)  # Long pause after block
            
        else:
            print(f"✗ {status}")
            stats['failed'] += 1
        
        # Save batch
        if i % BATCH_SIZE == 0 and batch_results:
            save_results(batch_results, OUTPUT_DIR, f'batch_{batch_num}')
            print(f"  💾 Saved batch {batch_num} | Delay: {current_delay:.1f}s\n")
            batch_results = []
            batch_num += 1
        
        # Progress report
        if i % 25 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed * 60
            remaining = total_queries - i
            eta = remaining / rate if rate > 0 else 0
            success_rate = stats['successful'] / i * 100
            
            print(f"\n  📊 Progress Report:")
            print(f"      Completed: {i}/{total_queries} ({i/total_queries*100:.1f}%)")
            print(f"      Success rate: {success_rate:.1f}%")
            print(f"      Rate: {rate:.1f} queries/min")
            print(f"      Current delay: {current_delay:.1f}s")
            print(f"      ETA: {eta:.1f} minutes")
            print(f"      Blocked: {stats['blocked']} times\n")
    
    # Cleanup
    driver.quit()
    print("\nBrowser closed.")
    
    # Save final batch
    if batch_results:
        save_results(batch_results, OUTPUT_DIR, f'batch_{batch_num}')
    
    # Save combined results
    if all_results:
        save_results(all_results, OUTPUT_DIR, 'final_results')
        
        elapsed = time.time() - start_time
        total_snippets = sum(1 for r in all_results if r.get('snippet'))
        avg_snippet = sum(r.get('snippet_length', 0) for r in all_results) / len(all_results) if all_results else 0
        
        print(f"\n{'='*70}")
        print("✅ COMPLETE!")
        print(f"{'='*70}")
        print(f"Total queries: {total_queries}")
        print(f"Successful: {stats['successful']} ({stats['successful']/total_queries*100:.1f}%)")
        print(f"No results: {stats['no_results']}")
        print(f"Blocked: {stats['blocked']}")
        print(f"Failed: {stats['failed']}")
        print(f"\nResults captured: {len(all_results)}")
        print(f"With snippets: {total_snippets} ({total_snippets/len(all_results)*100:.1f}%)")
        print(f"Avg snippet: {avg_snippet:.0f} chars")
        print(f"Avg per query: {len(all_results)/stats['successful']:.1f}")
        print(f"\nPerformance:")
        print(f"  Time: {elapsed/60:.1f} minutes ({elapsed/3600:.2f} hours)")
        print(f"  Rate: {total_queries/elapsed*60:.1f} queries/min")
        print(f"\nSaved to: {OUTPUT_DIR}/")
        print(f"  final_results.json")
        print(f"  final_results.csv")
        print(f"{'='*70}\n")
    else:
        print("\n⚠ No results captured")

if __name__ == '__main__':
    main()