"""
向量数据库服务 — Chroma + bge-m3

配置对齐 data/config.py（沈东阳），共用同一个 Chroma 库和模型。
导入 MySQL 的同时写入 Chroma，保持两个库同步。

使用方式:
    from app.services.vector_service import sync_reviews_to_chroma, search_similar_reviews
"""

import os
import sys
import logging

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# 复用沈东阳 data/config.py 的配置，共用同一个 Chroma 库和模型
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(_project_root, "data"))
from config import CHROMA_DIR, EMBEDDING_MODEL  # noqa: E402

COLLECTION_NAME = "amazon_reviews"  # 与 vectorize.py 保持一致

# 全局单例
_embeddings = None
_vector_store = None


def _get_embeddings():
    """懒加载 embedding 模型（路径使用同学 data/config.py 的配置）"""
    global _embeddings
    if _embeddings is None:
        model_path = EMBEDDING_MODEL
        if not os.path.exists(model_path):
            model_path = "BAAI/bge-m3"  # 自动从 HuggingFace 下载
            logger.info("本地未找到 bge-m3 模型，将从 HuggingFace 自动下载...")
        _embeddings = HuggingFaceEmbeddings(
            model_name=model_path,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def _get_vector_store():
    """懒加载 Chroma 向量库"""
    global _vector_store
    if _vector_store is None:
        os.makedirs(CHROMA_DIR, exist_ok=True)
        _vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=_get_embeddings(),
            persist_directory=CHROMA_DIR,
        )
    return _vector_store


def build_structured_content(review) -> str:
    """
    构建结构化文本，对齐沈东阳 vectorize.py 的格式。
    格式：评分: X星\n问题类别: Y\n标题: Z\n内容: W
    """
    parts = []

    rating = getattr(review, "rating", 0) or 0
    parts.append(f"评分: {rating}星")

    label = getattr(review, "label", "") or "Other"
    parts.append(f"问题类别: {label}")

    summary = getattr(review, "summary", "")
    if summary:
        parts.append(f"标题: {summary}")

    review_text = getattr(review, "review_text", "") or ""
    if review_text:
        parts.append(f"内容: {review_text}")

    return "\n".join(parts)


def sync_reviews_to_chroma(reviews: list) -> int:
    """
    将评论列表同步到 Chroma 向量库。

    参数:
        reviews: Review ORM 对象列表（至少包含 review_id, rating, label, summary, review_text,
                 reviewer_id, asin, review_time）

    返回: 新增向量数量
    """
    if not reviews:
        return 0

    vector_store = _get_vector_store()
    count = 0

    for r in reviews:
        content = build_structured_content(r)
        if not content or len(content) < 20:
            continue

        doc = Document(
            page_content=content,
            metadata={
                "review_id": getattr(r, "review_id", 0),
                "asin": getattr(r, "asin", "") or "",
                "overall": getattr(r, "rating", 0) or 0,
                "label": getattr(r, "label", "") or "Other",
                "reviewer_id": getattr(r, "reviewer_id", "") or "",
                "review_time": str(getattr(r, "review_time", "")) or "",
            },
        )
        vector_store.add_documents([doc])
        count += 1

    logger.info(f"同步 {count} 条向量到 Chroma: {CHROMA_DIR}")
    return count


def search_similar_reviews(query: str, k: int = 5) -> list[dict]:
    """
    语义搜索相似差评。

    参数:
        query: 搜索文本
        k:     返回条数

    返回: [{"content": "...", "metadata": {...}}, ...]
    """
    vector_store = _get_vector_store()
    results = vector_store.similarity_search(query, k=k)
    return [
        {"content": doc.page_content, "metadata": doc.metadata}
        for doc in results
    ]


def get_chroma_stats() -> dict:
    """获取向量库统计信息"""
    try:
        vector_store = _get_vector_store()
        collection = vector_store._collection
        return {
            "collection_name": COLLECTION_NAME,
            "vector_count": collection.count(),
            "persist_directory": CHROMA_DIR,
        }
    except Exception:
        return {"error": "向量库未初始化"}
