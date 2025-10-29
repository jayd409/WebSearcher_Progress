import os
import pandas as pd
from WebSearcher.searchers import SearchEngine

def main():
    # Queries to test
    queries = ["weather in San Francisco today", "best pizza near Boston"]

    # Output directory
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "test_results_requests.csv")

    # Initialize SearchEngine with REQUESTS mode
    searcher = SearchEngine()
    # Force searcher to use requests method (no Selenium)
    searcher.method = "REQUESTS"

    results_list = []

    for q in queries:
        print(f"Searching: {q}")
        try:
            searcher.search(q)       # Uses requests internally
            searcher.parse_results()  # Parse results
            if searcher.results:
                results_list.extend(searcher.results)
            else:
                print(" -> No results found for this query.")
        except Exception as e:
            print(f"Error: {e}")

    # Save results if any
    if results_list:
        df = pd.DataFrame(results_list)
        df.to_csv(output_file, index=False)
        print(f"Results saved to: {output_file}")
    else:
        print("No results collected in this test run.")

if __name__ == "__main__":
    main()