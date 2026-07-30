"""
从 MySQL 读取差评数据，初始化 ChromaDB 向量库
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.database.database import SessionLocal
from app.models import Review
from langchain_core.documents import Document


def init_vector_from_mysql(force_rebuild: bool = False):
    """从 MySQL 读取所有差评，构建向量库"""
    db = SessionLocal()
    try:
        reviews = db.query(Review).all()
        print(f"[1/3] 从MySQL读取到 {len(reviews)} 条评论")

        # 只取有文本的差评
        documents = []
        for r in reviews:
            if r.review_text and r.review_text.strip():
                doc = Document(
                    page_content=r.review_text,
                    metadata={
                        "review_id": r.review_id,
                        "asin": r.asin or "",
                        "overall": r.rating or 0,
                        "label": r.label or "",
                        "review_time": str(r.review_time) if r.review_time else "",
                    }
                )
                documents.append(doc)

        print(f"[2/3] 生成 {len(documents)} 个Document")

        if not documents:
            print("[ERROR] 没有有效评论数据")
            return

        # 构建ChromaDB
        from ai_module.app.vector_store import get_vector_store
        vs = get_vector_store()

        if force_rebuild:
            import shutil
            from ai_module.app.config import VECTOR_DB_PATH
            if os.path.exists(VECTOR_DB_PATH):
                shutil.rmtree(VECTOR_DB_PATH)
                print(f"  已删除旧向量库: {VECTOR_DB_PATH}")

        vs.build(documents)

        stats = vs.get_stats()
        print(f"[3/3] 向量库初始化完成: {stats['count']} 条, 路径: {stats['path']}")

    finally:
        db.close()


if __name__ == "__main__":
    init_vector_from_mysql(force_rebuild=True)
