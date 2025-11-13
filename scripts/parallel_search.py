#!/usr/bin/env python3
"""
Parallel search script for large-scale queries (10K+)
Uses multiple Chrome instances to speed up collection
"""

import pandas as pd
import json
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Global lock for thread-safe file operations
save_lock = Lock()

def setup_chrome(headless=True):
    """Setup Chrome instance"""
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-images')  # Faster
    chrome_options.page_load_strategy = 'eager'  # Don't wait for everything
    
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
        
        snippet_selectors = ['div.VwiC3b', 'div.lyLwlc', 'span.aCOpRe', 'div.IsZvec']
        snippets = []
        for selector in snippet_selectors:
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

def search_worker(query, worker_id):
    """Worker function to search a single query"""
    driver = None
    try:
        driver = setup_chrome(headless=True)
        
        driver.get('https://www.google.com')
        search_box = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.NAME, 'q'))
        )
        search_box.clear()
        search_box.send_keys(query)
        search_box.submit()
        time.sleep(2)
        
        if '/sorry/' in driver.current_url:
            return None, 'blocked'
        
        results = []
        result_containers = []
        for selector in ['div.g', 'div.MjjYud']:
            result_containers = driver.find_elements(By.CSS_SELECTOR, selector)
            if result_containers:
                break
        
        for idx, container in enumerate(result_containers[:10]):
            try:
                result = extract_result(container, idx + 1, query)
                if result['title'] or result['url']:
                    results.append(result)
            except:
                continue
        
        driver.quit()
        return results, 'success'
        
    except Exception as e:
        if driver:
            driver.quit()
        return None, str(e)

def save_batch_threadsafe(results, output_dir, batch_num):
    """Thread-safe batch saving"""
    with save_lock:
        if not results:
            return
        
        json_file = output_dir / f'batch_{batch_num}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        df = pd.DataFrame(results)
        csv_file = output_dir / f'batch_{batch_num}.csv'
        df.to_csv(csv_file, index=False, encoding='utf-8')

def main():
    # Configuration
    INPUT_CSV = "data/search_arena_user_messages_filtered_20251109_1409.csv"
    OUTPUT_DIR = Path("data/parallel_results")
    MAX_QUERIES = 100  # Test with 100 first, then set to None for all
    NUM_WORKERS = 3  # Number of parallel Chrome instances (3-5 is safe)
    BATCH_SIZE = 50
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("Loading queries...")
    df = pd.read_csv(INPUT_CSV)
    queries = df['query'].tolist()
    
    if MAX_QUERIES:
        queries = queries[:MAX_QUERIES]
    
    print(f"Processing {len(queries)} queries")
    print(f"Parallel workers: {NUM_WORKERS}")
    print(f"Estimated time: {len(queries) / (NUM_WORKERS * 20):.1f} minutes\n")
    
    all_results = []
    batch_results = []
    stats = {'successful': 0, 'failed': 0, 'blocked': 0}
    batch_num = 1
    start_time = time.time()
    
    print(f"{'='*70}")
    print("Starting parallel searches...")
    print(f"{'='*70}\n")
    
    # Process queries in parallel
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        # Submit all queries
        future_to_query = {
            executor.submit(search_worker, query, i): (i, query) 
            for i, query in enumerate(queries)
        }
        
        completed = 0
        
        # Process as they complete
        for future in as_completed(future_to_query):
            completed += 1
            query_idx, query = future_to_query[future]
            
            try:
                results, status = future.result()
                
                if status == 'success' and results:
                    num_results = len(results)
                    avg_snippet = sum(r.get('snippet_length', 0) for r in results) / num_results
                    print(f"[{completed}/{len(queries)}] ✓ {query[:50]}... ({num_results} results, {avg_snippet:.0f} chars)")
                    
                    all_results.extend(results)
                    batch_results.extend(results)
                    stats['successful'] += 1
                    
                elif status == 'blocked':
                    print(f"[{completed}/{len(queries)}] ✗ BLOCKED: {query[:50]}...")
                    stats['blocked'] += 1
                    
                else:
                    print(f"[{completed}/{len(queries)}] ✗ FAILED: {query[:50]}...")
                    stats['failed'] += 1
                
                # Save batch
                if len(batch_results) >= BATCH_SIZE:
                    save_batch_threadsafe(batch_results, OUTPUT_DIR, batch_num)
                    print(f"  💾 Saved batch {batch_num}\n")
                    batch_results = []
                    batch_num += 1
                
                # Show progress
                if completed % 20 == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed * 60
                    remaining = len(queries) - completed
                    eta = remaining / rate if rate > 0 else 0
                    print(f"  📊 Progress: {completed}/{len(queries)} | Rate: {rate:.1f} q/min | ETA: {eta:.1f} min\n")
                
            except Exception as e:
                print(f"[{completed}/{len(queries)}] ✗ ERROR: {query[:50]}... - {e}")
                stats['failed'] += 1
    
    # Save final batch
    if batch_results:
        save_batch_threadsafe(batch_results, OUTPUT_DIR, batch_num)
    
    # Save final combined results
    if all_results:
        json_file = OUTPUT_DIR / 'final_results.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        df = pd.DataFrame(all_results)
        csv_file = OUTPUT_DIR / 'final_results.csv'
        df.to_csv(csv_file, index=False, encoding='utf-8')
        
        elapsed = time.time() - start_time
        total_snippets = sum(1 for r in all_results if r.get('snippet'))
        avg_snippet = sum(r.get('snippet_length', 0) for r in all_results) / len(all_results)
        
        print(f"\n{'='*70}")
        print("✅ COMPLETE!")
        print(f"{'='*70}")
        print(f"Total queries: {len(queries)}")
        print(f"Successful: {stats['successful']}")
        print(f"Blocked: {stats['blocked']}")
        print(f"Failed: {stats['failed']}")
        print(f"\nResults captured: {len(all_results)}")
        print(f"With snippets: {total_snippets} ({total_snippets/len(all_results)*100:.1f}%)")
        print(f"Avg snippet: {avg_snippet:.0f} chars")
        print(f"Avg per query: {len(all_results)/stats['successful']:.1f}")
        print(f"\nTime: {elapsed/60:.1f} minutes")
        print(f"Rate: {len(queries)/elapsed*60:.1f} queries/min")
        print(f"Speedup: {NUM_WORKERS}x faster than single-threaded")
        print(f"\nSaved to:")
        print(f"  JSON: {json_file}")
        print(f"  CSV: {csv_file}")
        print(f"{'='*70}\n")
        
        print("Sample results:")
        for result in all_results[:2]:
            print(f"\n  Query: {result['query']}")
            print(f"  Title: {result.get('title', 'N/A')[:60]}...")
            print(f"  Snippet: {result.get('snippet', 'N/A')[:100]}...")
    else:
        print("\n⚠ No results captured")

if __name__ == '__main__':
    main()