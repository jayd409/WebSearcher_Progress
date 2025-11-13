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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
import glob

def setup_chrome(headless=True):
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.page_load_strategy = 'normal'
    if headless:
        chrome_options.add_argument('--headless=new')
    service = Service('/usr/local/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
    })
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def extract_comprehensive_result(container, rank):
    result = {
        'rank': rank,
        'title': None,
        'url': None,
        'displayed_url': None,
        'domain': None,
        'snippet': None,
        'full_text': None,
        'result_type': 'organic',
        'has_snippet': False,
        'snippet_length': 0,
    }
    try:
        result['full_text'] = container.text.strip() if container.text else None
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
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    result['domain'] = parsed.netloc
                except:
                    pass
        except:
            pass
        try:
            cite = container.find_element(By.TAG_NAME, 'cite')
            result['displayed_url'] = cite.text.strip() if cite.text else None
        except:
            pass
        snippet_selectors = [
            'div.VwiC3b', 'div.lyLwlc', 'span.aCOpRe', 'div.s',
            'div.BNeawe.s3v9rd', 'div[data-content-feature="1"]',
            'div.lEBKkf', 'span.st', 'div.IsZvec'
        ]
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
            result['has_snippet'] = True
            result['snippet_length'] = len(result['snippet'])
        if not result['snippet'] and result['full_text']:
            text_lines = [line.strip() for line in result['full_text'].split('\n') if line.strip()]
            if len(text_lines) > 1:
                result['snippet'] = ' '.join(text_lines[1:])[:500]
                result['snippet_length'] = len(result['snippet'])
    except Exception:
        pass
    return result

def search_query(driver, query, max_results=15):
    results = []
    metadata = {'query': query, 'search_url': None, 'featured_snippet_present': False, 'knowledge_panel_present': False}
    try:
        driver.get('https://www.google.com')
        search_box = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, 'q')))
        search_box.clear()
        search_box.send_keys(query)
        search_box.submit()
        time.sleep(3)
        if '/sorry/' in driver.current_url:
            return None, 'blocked', metadata
        metadata['search_url'] = driver.current_url
        try:
            featured = driver.find_elements(By.CSS_SELECTOR, 'div.kp-blk, div[data-attrid="FeaturedSnippet"]')
            if featured:
                metadata['featured_snippet_present'] = True
                featured_result = {
                    'rank': 0, 'title': 'Featured Snippet', 'result_type': 'featured_snippet',
                    'full_text': featured[0].text, 'snippet': featured[0].text,
                    'snippet_length': len(featured[0].text), 'has_snippet': True, 'query': query
                }
                results.append(featured_result)
        except:
            pass
        try:
            knowledge = driver.find_elements(By.CSS_SELECTOR, 'div.kp-wholepage')
            if knowledge:
                metadata['knowledge_panel_present'] = True
        except:
            pass
        result_containers = []
        for selector in ['div.g', 'div.MjjYud', 'div[data-sokoban-container]']:
            try:
                result_containers = driver.find_elements(By.CSS_SELECTOR, selector)
                if len(result_containers) > 0:
                    break
            except:
                continue
        if not result_containers:
            return [], 'no_results', metadata
        rank_offset = 1 if metadata['featured_snippet_present'] else 0
        for idx, container in enumerate(result_containers[:max_results]):
            try:
                result_data = extract_comprehensive_result(container, idx + rank_offset + 1)
                result_data['query'] = query
                result_data['timestamp'] = datetime.now().isoformat()
                if result_data['title'] or result_data['url'] or (result_data['full_text'] and len(result_data['full_text']) > 30):
                    results.append(result_data)
            except:
                continue
        return results, 'success', metadata
    except TimeoutException:
        return None, 'timeout', metadata
    except Exception as e:
        return None, str(e), metadata

def save_results(results, output_dir, filename='results'):
    if not results:
        return None, None
    json_file = output_dir / f'{filename}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    df = pd.DataFrame(results)
    csv_file = output_dir / f'{filename}.csv'
    df.to_csv(csv_file, index=False, encoding='utf-8')
    return json_file, csv_file

def get_last_completed_batch(output_dir):
    files = glob.glob(str(output_dir / "batch_*.json"))
    if not files:
        return 0
    batches = [int(Path(f).stem.split("_")[1]) for f in files if Path(f).stem.split("_")[1].isdigit()]
    return max(batches) if batches else 0

def main():
    INPUT_CSV = "data/search_arena_user_messages_filtered_20251109_1409.csv"
    OUTPUT_DIR = Path("data/optimized_results")
    MAX_QUERIES = None  # ← Run ALL queries now
    DELAY = 3
    HEADLESS = True
    SAVE_INTERVAL = 100  # ← Large batch size

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Loading queries...")
    df = pd.read_csv(INPUT_CSV)
    queries = df['query'].tolist()
    if MAX_QUERIES:
        queries = queries[:MAX_QUERIES]
    print(f"Total queries: {len(queries)}")
    last_batch = get_last_completed_batch(OUTPUT_DIR)
    print(f"Resuming from batch {last_batch + 1}\n")

    driver = setup_chrome(headless=HEADLESS)
    print("Chrome ready!\n")

    all_results, batch_results = [], []
    stats = {'successful': 0, 'failed': 0, 'blocked': 0, 'no_results': 0, 'featured_snippets': 0, 'knowledge_panels': 0}

    for i, query in enumerate(queries, 1):
        current_batch = (i - 1) // SAVE_INTERVAL + 1
        if current_batch <= last_batch:
            continue

        print(f"[{i}/{len(queries)}] {query[:60]}...", end=' ')
        results, status, metadata = search_query(driver, query, max_results=15)

        if status == 'success':
            print(f"✓ {len(results)} results")
            all_results.extend(results)
            batch_results.extend(results)
            stats['successful'] += 1
            if metadata['featured_snippet_present']:
                stats['featured_snippets'] += 1
            if metadata['knowledge_panel_present']:
                stats['knowledge_panels'] += 1
        elif status == 'blocked':
            print("✗ BLOCKED")
            stats['blocked'] += 1
            time.sleep(30)
        elif status == 'no_results':
            print("⚠ No results")
            stats['no_results'] += 1
        else:
            print(f"✗ Error: {status}")
            stats['failed'] += 1

        if i % SAVE_INTERVAL == 0 and batch_results:
            save_results(batch_results, OUTPUT_DIR, f'batch_{i//SAVE_INTERVAL}')
            print(f"💾 Saved batch {i//SAVE_INTERVAL}\n")
            batch_results = []
        time.sleep(DELAY)

    if batch_results:
        # Save any leftover results at the end
        save_results(batch_results, OUTPUT_DIR, f'batch_{(len(queries)-1)//SAVE_INTERVAL + 1}')
        print("💾 Final batch saved.")

    driver.quit()
    print("\nBrowser closed.")

if __name__ == '__main__':
    main()