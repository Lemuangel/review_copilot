import os
import sys
import pandas as pd
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from tqdm import tqdm
os.environ["CHROMA_TELEMETRY"] = "False"

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def build_vector_store(df, collection_name="amazon_reviews"):
    if 'overall' in df.columns:
        bad_reviews = df[df['overall'] <= 2]
        print(f"Bad reviews: {len(bad_reviews)}")
    else:
        bad_reviews = df
        print("No 'overall' field, all reviews will be stored")
    documents = []
    for _, row in tqdm(bad_reviews.iterrows(), total=len(bad_reviews), desc="Building docs"):
        content = row.get('reviewText', '')
        if not content:
            continue
        doc = Document(
            page_content=content,
            metadata={
                'reviewerID': row.get('reviewerID', ''),
                'asin': row.get('asin', ''),
                'overall': row.get('overall', ''),
                'summary': row.get('summary', ''),
            }
        )
        documents.append(doc)
    if not documents:
        print("No valid documents")
        return
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    chunks = splitter.split_documents(documents)
    print(f"Chunks: {len(chunks)}")
    print(f"Loading embedding model from local: {config.EMBEDDING_MODEL}")
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
        collection_name=collection_name
    )
    print(f"Vector store saved to {config.CHROMA_DIR}, total {len(chunks)} vectors")

def main():
    print("Step 2: Vectorize and Store")
    in_path = os.path.join(config.OUTPUT_DIR, "cleaned_reviews.csv")
    if not os.path.exists(in_path):
        print("Please run load_and_clean.py first")
        return
    df = pd.read_csv(in_path, encoding='utf-8-sig')
    print(f"Loaded {len(df)} records")
    build_vector_store(df)

if __name__ == "__main__":
    main()