import pandas as pd
from langdetect import detect, DetectorFactory
import re

# Ensure deterministic results for langdetect
DetectorFactory.seed = 0

# Settings
INPUT_CSV = "../data/search_arena_user_messages.csv"
OUTPUT_CSV = "../data/search_arena_user_messages_filtered.csv"
MIN_WORDS = 2
MAX_WORDS = 30

# Load CSV
df = pd.read_csv(INPUT_CSV)

print(f"Loaded {len(df)} messages")

# Remove empty messages
df = df[df["query"].notnull() & (df["query"].str.strip() != "")]
print(f"After removing empty: {len(df)}")

# Filter English queries
def is_english(text):
    try:
        return detect(text) == "en"
    except:
        return False

df = df[df["query"].apply(is_english)]
print(f"After English filter: {len(df)}")

#  Filter by word count
df["word_count"] = df["query"].str.split().apply(len)
df = df[(df["word_count"] >= MIN_WORDS) & (df["word_count"] <= MAX_WORDS)]
print(f"After word count filter: {len(df)}")

# Remove duplicates
df = df.drop_duplicates(subset=["query"])
print(f"After removing duplicates: {len(df)}")

# remove queries with only numbers/special chars
df = df[df["query"].str.match(r"[A-Za-z]")]

# Save filtered CSV
df[["query"]].to_csv(OUTPUT_CSV, index=False)
print(f"Filtered queries saved to {OUTPUT_CSV}")