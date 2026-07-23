import os
import sys
import pandas as pd
from tqdm import tqdm
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def build_structured_content(row):
    """构建结构化文本：评分 + 类别 + 标题 + 正文"""
    parts = []

    overall = row.get('overall', 0)
    parts.append(f"评分: {overall}星")

    label = row.get('label', 'Other')
    if label != 'Other':
        parts.append(f"问题类别: {label}")

    summary = row.get('summary', '')
    if summary and pd.notna(summary):
        parts.append(f"标题: {summary}")

    review_text = row.get('reviewText', '')
    if review_text and pd.notna(review_text):
        parts.append(f"内容: {review_text}")

    return "\n".join(parts)


def main():
    print("精细化向量化入库")

    in_path = os.path.join(config.OUTPUT_DIR, "labeled_reviews.csv")
    if not os.path.exists(in_path):
        print("请先运行 label_data.py")
        return

    df = pd.read_csv(in_path, encoding='utf-8-sig')
    print(f"数据量: {len(df)} 条")

    # 只处理差评
    if 'overall' in df.columns:
        df = df[df['overall'] <= 2]
        print(f"差评: {len(df)} 条")

    # 构建文档
    documents = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="构建文档"):
        content = build_structured_content(row)
        if not content or len(content) < 20:
            continue

        doc = Document(
            page_content=content,
            metadata={
                'asin': row.get('asin', ''),
                'overall': row.get('overall', 0),
                'label': row.get('label', 'Other'),
                'reviewerID': row.get('reviewerID', ''),
                'unixReviewTime': row.get('unixReviewTime', 0),
                'reviewTime': row.get('reviewTime', ''),
            }
        )
        documents.append(doc)

    print(f"有效文档: {len(documents)} 条")

    # 分块
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    chunks = splitter.split_documents(documents)
    print(f"分块后: {len(chunks)} 块")

    # 向量化入库
    embeddings = HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    os.makedirs(config.CHROMA_DIR, exist_ok=True)
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=config.CHROMA_DIR,
        collection_name="amazon_reviews"
    )

    print(f"入库完成: {len(chunks)} 条向量 -> {config.CHROMA_DIR}")


if __name__ == "__main__":
    main()