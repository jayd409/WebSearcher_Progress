import pandas as pd
import re
from datetime import datetime
from langdetect import detect, LangDetectException

INPUT_FILE = "data/search_arena_user_messages.csv"
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
OUTPUT_FILE = f"data/search_arena_user_messages_filtered_{timestamp}.csv"

def clean_text(text):
    """Clean and normalize text"""
    if not isinstance(text, str):
        return ""
    
    # Remove extra whitespace
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    
    return text

def is_english(text):
    """Check if text is in English"""
    try:
        lang = detect(text)
        return lang == 'en'
    except LangDetectException:
        return False

def has_meaningful_content(text):
    """Check if query has actual words (not just symbols/numbers)"""
    # Must have at least some alphabetic characters
    if not re.search(r'[a-zA-Z]', text):
        return False
    
    # Count alphabetic characters
    alpha_count = sum(c.isalpha() for c in text)
    
    # At least 50% should be letters
    if len(text) > 0 and alpha_count / len(text) < 0.5:
        return False
    
    return True

def is_nonsensical(text):
    """Detect nonsensical or gibberish queries"""
    # Check for excessive repeated characters (e.g., "aaaaaaa", "hahahaha")
    if re.search(r'(.)\1{4,}', text):
        return True
    
    # Check for random keyboard mashing (too many consonants in a row)
    if re.search(r'[bcdfghjklmnpqrstvwxyz]{7,}', text.lower()):
        return True
    
    # Check for excessive special characters
    special_char_count = sum(not c.isalnum() and not c.isspace() for c in text)
    if len(text) > 0 and special_char_count / len(text) > 0.3:
        return True
    
    return False

def is_irrelevant(text):
    """Filter out common irrelevant query patterns"""
    text_lower = text.lower()
    
    # Common test/spam patterns
    irrelevant_patterns = [
        r'^test\s*\d*$',
        r'^hello+$',
        r'^hi+$',
        r'^\d+$',  # Just numbers
        r'^[.]+$',  # Just dots
        r'^aaa+$',
        r'^xxx+$',
        r'^\s*$',  # Empty or whitespace only
    ]
    
    for pattern in irrelevant_patterns:
        if re.match(pattern, text_lower):
            return True
    
    # Check for common spam keywords
    spam_keywords = ['buy now', 'click here', 'free money', 'limited offer']
    if any(keyword in text_lower for keyword in spam_keywords):
        return True
    
    return False

def is_valid_query(q):
    """Main validation function - comprehensive checks"""
    if not isinstance(q, str):
        return False
    
    q = q.strip()
    
    # Length checks
    word_count = len(q.split())
    char_count = len(q)
    
    # Too short (less than 3 words OR less than 10 characters)
    if word_count < 3 or char_count < 10:
        return False
    
    # Too long (likely spam or garbage)
    if char_count > 500:
        return False
    
    # Check for meaningful content
    if not has_meaningful_content(q):
        return False
    
    # Check if nonsensical
    if is_nonsensical(q):
        return False
    
    # Check if irrelevant
    if is_irrelevant(q):
        return False
    
    # Check if English
    if not is_english(q):
        return False
    
    return True

def main():
    print(f"{'='*70}")
    print("Query Filtering Script")
    print(f"{'='*70}\n")
    
    print(f"Input: {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}\n")
    
    # Load data
    print("Loading queries...")
    df = pd.read_csv(INPUT_FILE)
    total_queries = len(df)
    print(f"  Loaded {total_queries:,} queries\n")
    
    # Clean text
    print("Step 1: Cleaning text...")
    df["query"] = df["query"].astype(str).apply(clean_text)
    print("  ✓ Text cleaned\n")
    
    # Remove duplicates
    print("Step 2: Removing duplicates...")
    before = len(df)
    df = df.drop_duplicates(subset=["query"])
    duplicates_removed = before - len(df)
    print(f"  ✓ Removed {duplicates_removed:,} duplicates ({duplicates_removed/total_queries*100:.1f}%)\n")
    
    # Filter by validation rules
    print("Step 3: Filtering invalid queries...")
    print("  Checking for:")
    print("    - English language")
    print("    - Meaningful content (not gibberish)")
    print("    - Appropriate length (3+ words, 10-500 chars)")
    print("    - Relevant search queries")
    
    before = len(df)
    
    # Show progress
    valid_mask = df["query"].apply(is_valid_query)
    df = df[valid_mask]
    
    invalid_removed = before - len(df)
    print(f"  ✓ Removed {invalid_removed:,} invalid queries ({invalid_removed/before*100:.1f}%)\n")
    
    # Save results
    print(f"Step 4: Saving filtered queries...")
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"  ✓ Saved to {OUTPUT_FILE}\n")
    
    # Summary
    final_count = len(df)
    total_removed = total_queries - final_count
    
    print(f"{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Original queries:     {total_queries:,}")
    print(f"Duplicates removed:   {duplicates_removed:,}")
    print(f"Invalid removed:      {invalid_removed:,}")
    print(f"Total removed:        {total_removed:,} ({total_removed/total_queries*100:.1f}%)")
    print(f"Final valid queries:  {final_count:,} ({final_count/total_queries*100:.1f}%)")
    print(f"{'='*70}\n")
    
    # Show sample queries
    print("Sample filtered queries (first 10):")
    for i, query in enumerate(df['query'].head(10), 1):
        print(f"  {i}. {query[:70]}...")
    
    print(f"\n✅ Done! Filtered dataset saved to:\n   {OUTPUT_FILE}")

if __name__ == "__main__":
    main()