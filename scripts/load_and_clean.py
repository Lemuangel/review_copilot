import os
import sys
import json
import re
import gzip
import pandas as pd
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def load_json(filepath, max_lines=None):
    is_gz = filepath.endswith('.gz')
    open_func = gzip.open if is_gz else open
    mode = 'rt' if is_gz else 'r'
    data = []
    with open_func(filepath, mode, encoding='utf-8') as f:
        for i, line in enumerate(tqdm(f, desc="Loading")):
            if max_lines and i >= max_lines:
                break
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except:
                continue
    return pd.DataFrame(data)

def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def main():
    print("Step 1: Load and Clean Data")
    if not os.path.exists(config.DATA_FILE):
        print(f"File not found: {config.DATA_FILE}")
        return
    df = load_json(config.DATA_FILE, max_lines=config.SAMPLE_SIZE)
    print(f"Raw records: {len(df)}")

    available = ['reviewerID', 'asin', 'reviewerName', 'vote', 'reviewText', 'overall', 'summary', 'unixReviewTime']
    df = df[[c for c in available if c in df.columns]]
    df['reviewText'] = df['reviewText'].apply(clean_text)
    if 'summary' in df.columns:
        df['summary'] = df['summary'].apply(clean_text)
    before = len(df)
    df = df.drop_duplicates(subset=['reviewerID', 'asin', 'reviewText'])
    print(f"Dedup: {before} -> {len(df)}")
    df = df[df['reviewText'].str.len() > 10]
    print(f"After filtering short reviews: {len(df)}")

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(config.OUTPUT_DIR, "cleaned_reviews.csv")
    df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"Saved to {out_path}")

if __name__ == "__main__":
    main()