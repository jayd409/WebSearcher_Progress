import pandas as pd
from datasets import load_dataset

# Load the dataset (use correct split 'test')
dataset = load_dataset("lmarena-ai/search-arena-24k", split="test")

# Extract 'messages_a' where role == 'user'
def extract_user_messages(example):
    return {"messages_a": [m["content"] for m in example["messages_a"] if m["role"] == "user"]}

dataset_clean = dataset.map(extract_user_messages)

# Flatten into a list of messages
all_messages = []
for item in dataset_clean:
    all_messages.extend(item["messages_a"])

# Remove empty messages and duplicates
all_messages = list(filter(None, all_messages))
all_messages = list(dict.fromkeys(all_messages))  # preserves order, removes duplicates

# Save to CSV
df = pd.DataFrame({"query": all_messages})
df.to_csv("../data/search_arena_user_messages.csv", index=False)
print(f"Saved {len(df)} cleaned messages to ../data/search_arena_user_messages.csv")