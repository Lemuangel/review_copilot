"""
RAG 向量数据库模块

使用 Chroma 作为向量存储，BGE-M3 (via sentence-transformers) 作为 Embedding 模型。
支持持久化存储，便于复用。

所有重依赖（langchain_huggingface, langchain_chroma, sentence_transformers）
均采用 Lazy 导入，确保 FastAPI 秒级启动。
"""
from __future__ import annotations

import os
import json
from typing import List, Optional, Tuple, TYPE_CHECKING
from langchain_core.documents import Document

from app.config import VECTOR_DB_PATH, EMBEDDING_MODEL, RAG_TOP_K, RAG_SIMILARITY_THRESHOLD

if TYPE_CHECKING:
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
    from langchain_text_splitters import RecursiveCharacterTextSplitter


# ============================================================
# 1. Embedding 模型初始化
# ============================================================
def init_embeddings() -> "HuggingFaceEmbeddings":
    """初始化 Embedding 模型（Lazy: 首次调用时才加载模型）"""
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )


# ============================================================
# 2. 文本分割器
# ============================================================
def create_text_splitter(
    chunk_size: int = 500,
    chunk_overlap: int = 80
) -> "RecursiveCharacterTextSplitter":
    """
    创建文本分割器（Lazy: 首次调用时才导入 langchain_text_splitters）

    针对差评文本特点，使用中英文标点作为分隔符
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", "。", "! ", "！", "? ", "？", ", ", "，", " ", ""],
        length_function=len,
    )


# ============================================================
# 3. 向量库管理
# ============================================================
class ReviewVectorStore:
    """差评向量库管理器（Lazy 模式）"""

    def __init__(self):
        self._embeddings = None  # type: ignore
        self._splitter: Optional[RecursiveCharacterTextSplitter] = None
        self._vector_store = None  # type: ignore

    @property
    def embeddings(self) -> "HuggingFaceEmbeddings":
        """Lazy 加载 Embedding 模型"""
        if self._embeddings is None:
            self._embeddings = init_embeddings()
        return self._embeddings

    @property
    def splitter(self) -> "RecursiveCharacterTextSplitter":
        """Lazy 加载文本分割器"""
        if self._splitter is None:
            self._splitter = create_text_splitter()
        return self._splitter

    def build_or_load(self, documents: Optional[List[Document]] = None) -> "Chroma":
        """
        构建或加载向量库

        Args:
            documents: 如果提供且向量库为空，则从这些文档构建

        Returns:
            Chroma 向量库实例
        """
        from langchain_chroma import Chroma

        # 尝试加载已有向量库
        if os.path.exists(VECTOR_DB_PATH):
            try:
                vs = Chroma(
                    persist_directory=VECTOR_DB_PATH,
                    embedding_function=self.embeddings,
                    collection_name="negative_reviews",
                )
                if vs._collection.count() > 0:
                    print(f"[INFO] 从 {VECTOR_DB_PATH} 加载向量库，共 {vs._collection.count()} 条")
                    self._vector_store = vs
                    return vs
                else:
                    print("[INFO] 向量库为空，将重新构建")
            except Exception as e:
                print(f"[WARN] 加载向量库失败: {e}，将重新构建")

        # 构建新向量库
        if documents is None:
            raise ValueError("向量库不存在且未提供 documents，无法构建")

        return self.build(documents)

    def build(self, documents: List[Document]) -> "Chroma":
        """
        从文档构建向量库

        Args:
            documents: LangChain Document 列表

        Returns:
            Chroma 向量库实例
        """
        from langchain_chroma import Chroma

        # 分割文档
        chunks = self.splitter.split_documents(documents)
        print(f"[INFO] 文本分割: {len(documents)} 条 → {len(chunks)} 个块")

        # 构建向量库
        vs = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=VECTOR_DB_PATH,
            collection_name="negative_reviews",
        )
        print(f"[INFO] 向量库构建完成，共 {vs._collection.count()} 条，持久化至 {VECTOR_DB_PATH}")
        self._vector_store = vs
        return vs

    def get_retriever(self):
        """获取检索器"""
        if self._vector_store is None:
            self._vector_store = self.build_or_load()
        return self._vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": RAG_TOP_K,
                "score_threshold": RAG_SIMILARITY_THRESHOLD,
            }
        )

    def similarity_search(
        self, query: str, k: int = None, threshold: float = None
    ) -> List[Tuple[Document, float]]:
        """
        相似度检索

        Args:
            query: 查询文本
            k: 返回数量
            threshold: 相似度阈值

        Returns:
            (Document, score) 列表
        """
        if self._vector_store is None:
            self._vector_store = self.build_or_load()

        k = k or RAG_TOP_K
        threshold = threshold or RAG_SIMILARITY_THRESHOLD

        return self._vector_store.similarity_search_with_relevance_scores(
            query, k=k, score_threshold=threshold
        )

    def add_documents(self, documents: List[Document]):
        """添加新文档到向量库"""
        if self._vector_store is None:
            self._vector_store = self.build_or_load()

        chunks = self.splitter.split_documents(documents)
        self._vector_store.add_documents(chunks)
        print(f"[INFO] 添加 {len(chunks)} 个块到向量库")

    def get_stats(self) -> dict:
        """获取向量库统计信息"""
        if self._vector_store is None:
            try:
                from langchain_chroma import Chroma
                self._vector_store = Chroma(
                    persist_directory=VECTOR_DB_PATH,
                    embedding_function=self.embeddings
                )
            except Exception:
                return {"status": "empty", "count": 0}

        count = self._vector_store._collection.count()
        return {
            "status": "loaded",
            "count": count,
            "path": VECTOR_DB_PATH,
            "embedding_model": EMBEDDING_MODEL,
        }


# 全局单例
_vector_store_instance: Optional[ReviewVectorStore] = None


def get_vector_store() -> ReviewVectorStore:
    """获取全局向量库实例"""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = ReviewVectorStore()
    return _vector_store_instance