import os
import sys
import pandas as pd
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def label_review(text):
    if not isinstance(text, str):
        return 'Other'
    text_lower = text.lower()
    price_kw = ['price', 'discount', 'sale', 'cost', 'expensive', 'cheap', 'value', 'money']
    product_kw = ['new', 'release', 'update', 'upgrade', 'feature', 'launch', 'version']
    sentiment_kw = ['bad', 'poor', 'terrible', 'disappointed', 'waste', 'complaint', 'issue', 'problem', 'useless', 'garbage']
    scores = {
        'Price': sum(1 for kw in price_kw if kw in text_lower),
        'Product': sum(1 for kw in product_kw if kw in text_lower),
        'Sentiment': sum(1 for kw in sentiment_kw if kw in text_lower),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else 'Other'

def main():
    print("Step 3: Label Data")
    in_path = os.path.join(config.OUTPUT_DIR, "cleaned_reviews.csv")
    if not os.path.exists(in_path):
        print("Please run load_and_clean.py first")
        return
    df = pd.read_csv(in_path, encoding='utf-8-sig')
    tqdm.pandas(desc="Labeling")
    df['label'] = df['reviewText'].progress_apply(label_review)
    print("Label distribution:")
    print(df['label'].value_counts())
    out_path = os.path.join(config.OUTPUT_DIR, "labeled_reviews.csv")
    df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"Saved to {out_path}")

if __name__ == "__main__":
    main()