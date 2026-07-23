import os
import sys
import json
import re
import gzip
import glob
import pandas as pd
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def load_json_filtered(filepath, max_lines=None):
    """只加载差评（overall <= 2），大幅减少数据量"""
    is_gz = filepath.endswith('.gz')
    open_func = gzip.open if is_gz else open
    mode = 'rt' if is_gz else 'r'
    data = []
    with open_func(filepath, mode, encoding='utf-8') as f:
        for i, line in enumerate(tqdm(f, desc=f"Loading {os.path.basename(filepath)}")):
            if max_lines and i >= max_lines:
                break
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                # 只保留差评 overall <= 2
                if obj.get('overall', 5) <= 2:
                    data.append(obj)
            except:
                continue
    return pd.DataFrame(data)


def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def load_all_bad_reviews():
    """只加载所有差评"""
    all_files = glob.glob(os.path.join(config.DATA_DIR, "*.json")) + \
                glob.glob(os.path.join(config.DATA_DIR, "*.json.gz"))
    if not all_files:
        raise FileNotFoundError(f"No JSON files found in {config.DATA_DIR}")

    df_list = []
    for filepath in all_files:
        print(f"\nProcessing {filepath}")
        df = load_json_filtered(filepath, max_lines=config.SAMPLE_SIZE)
        if not df.empty:
            common_cols = ['reviewerID', 'asin', 'reviewerName', 'reviewText', 'overall', 'summary', 'unixReviewTime']
            available = [c for c in common_cols if c in df.columns]
            df = df[available]
            df_list.append(df)
        else:
            print(f"No bad reviews in {filepath}")

    if not df_list:
        raise ValueError("No bad reviews found in any file.")

    return pd.concat(df_list, ignore_index=True)


def main():
    print("Step 1: Load and Clean Bad Reviews Only")
    df = load_all_bad_reviews()
    print(f"Total bad reviews: {len(df)}")

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