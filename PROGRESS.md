# Project Progress - WebSearcher Work
**Date:** 2025-11-13

## Overview
This repository contains updates on the WebSearcher_Progress project. It now includes:

- Extraction of user messages from the `search-arena-24k` dataset.
- Comprehensive filtering of queries for English, meaningful content, and relevance.
- Optimized scraping of Google search results using Selenium.
- Batch-wise incremental saving of results.
- Test script for verifying scraping on a small set of queries.

---

## Project Structure

```
WebSearcher_Progress/
│
├─ data/
│   ├─ search_arena_user_messages.csv
│   ├─ search_arena_user_messages_filtered_<timestamp>.csv
│   └─ optimized_results/
│       ├─ batch_1.json
│       └─ batch_1.csv
│
├─ scripts/
│   ├─ clean_message_a.py       # Extracts 'messages_a' from dataset
│   ├─ filter_queries.py        # Cleans and filters queries
│   ├─ optimized_search.py      # Main Google scraping script with batch saving
│   └─ test_search.py           # Small test script to verify searches
│
└─ PROGRESS.md                  # This file
```

---

## Scripts Explanation

### 1. `clean_message_a.py`
- Loads the `search-arena-24k` dataset (`split='test'`).
- Extracts messages where `role == user`.
- Removes empty messages and duplicates.
- Saves the cleaned queries to: `data/search_arena_user_messages.csv`.

**Command to run:**
```bash
poetry run python scripts/clean_message_a.py
```

---

### 2. `filter_queries.py`
- Cleans queries (removes extra whitespace, normalizes text).
- Filters:
  - English-only queries.
  - Meaningful content (not gibberish or nonsensical).
  - Appropriate length: 3+ words, 10-500 characters.
  - Removes duplicates and irrelevant/spammy queries.
- Output file: `data/search_arena_user_messages_filtered_<timestamp>.csv`

**Command to run:**
```bash
poetry run python scripts/filter_queries.py
```

---

### 3. `optimized_search.py`
- Searches Google for all filtered queries.
- Extracts:
  - Title, URL, displayed URL, domain.
  - Snippets and full text of search results.
  - Featured snippets and knowledge panels.
- Saves results incrementally in batches (default 100 queries per batch) in both JSON and CSV.
- Supports resuming from the last saved batch to avoid data loss.

**Command to run:**
```bash
poetry run python scripts/optimized_search.py
```

---

### 4. `test_search.py`
- Runs 3 sample queries from `data/sample_queries.csv`.
- Useful to verify Google scraping setup before running full-scale scraping.
- Saves JSON and CSV in `data/test_results/`.

**Command to run:**
```bash
poetry run python scripts/test_search.py
```

---

## Workflow Summary

1. **Clean Messages**
```bash
poetry run python scripts/clean_message_a.py
```

2. **Filter Queries**
```bash
poetry run python scripts/filter_queries.py
```

3. **Run Optimized Search**
```bash
poetry run python scripts/optimized_search.py
```

4. **Run Test Search (optional)**
```bash
poetry run python scripts/test_search.py
```

**Notes:**
- Use `HEADLESS=True` in `optimized_search.py` for faster execution.
- Adjust `DELAY` in scraping scripts to avoid Google rate limiting.
- Always resume from last saved batch to prevent loss of results.

---

## Pending / Issues
- Ensure Chrome and ChromeDriver compatibility.
- Avoid Google blocks for large-scale scraping.
- SERP API could be an alternative if scraping issues persist.
- Monitor incremental batch saving.

---

## References
- GitHub Repository: [https://github.com/jayd409/WebSearcher_Progress](https://github.com/jayd409/WebSearcher_Progress)
- Dataset: `data/search_arena_user_messages_filtered_<timestamp>.csv`