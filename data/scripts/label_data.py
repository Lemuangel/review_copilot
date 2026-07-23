import os
import sys
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# 加载环境变量
load_dotenv(os.path.join(config.BASE_DIR, "..", ".env"))

# 初始化 DeepSeek
llm = ChatOpenAI(
    model=os.getenv("MODEL_PRO", "deepseek-v4-flash"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1"),
    temperature=0.0,
)

LABEL_PROMPT = """请判断以下亚马逊差评属于哪个类别，只输出类别名称，不要输出其他内容。

类别说明：
- Logistics: 物流问题，如配送延迟、丢包、包装破损
- ProductQuality: 产品质量问题，如功能失效、不耐用、做工差
- DescriptionMismatch: 描述不符，如尺寸/颜色/功能与页面描述不一致
- Price: 价格问题，如定价过高、性价比低
- CustomerService: 客服问题，如售后响应慢、退货困难
- Other: 不属于以上任何类别

差评内容：{review_text}
类别："""


def sample_data(df, n=100):
    """简单随机抽样"""
    if len(df) <= n:
        return df
    return df.sample(n=n, random_state=42).reset_index(drop=True)


def llm_label(text):
    """调用 DeepSeek 对单条差评进行分类"""
    if not isinstance(text, str) or len(text) < 5:
        return 'Other'
    try:
        prompt = LABEL_PROMPT.format(review_text=text[:2000])
        response = llm.invoke(prompt)
        label = response.content.strip()
        valid_labels = ['Logistics', 'ProductQuality', 'DescriptionMismatch', 'Price', 'CustomerService', 'Other']
        if label not in valid_labels:
            return 'Other'
        return label
    except Exception as e:
        print(f"LLM call failed: {e}")
        return 'Other'


def main():
    print("Step: Sample 100 bad reviews and label with LLM")

    in_path = os.path.join(config.OUTPUT_DIR, "cleaned_reviews.csv")
    if not os.path.exists(in_path):
        print("Please run load_and_clean.py first")
        return

    df = pd.read_csv(in_path, encoding='utf-8-sig')
    print(f"Total bad reviews: {len(df)}")

    # 1. 抽样 100 条
    print("Sampling 100 reviews...")
    sample_df = sample_data(df, n=100)
    print(f"Sampled: {len(sample_df)} reviews")

    # 2. LLM 标注
    print("Labeling with LLM...")
    tqdm.pandas(desc="LLM Labeling")
    sample_df['label'] = sample_df['reviewText'].progress_apply(llm_label)

    # 3. 输出分布
    print("\nLabel distribution (LLM):")
    print(sample_df['label'].value_counts())

    # 4. 保存
    out_path = os.path.join(config.OUTPUT_DIR, "labeled_reviews.csv")
    sample_df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()