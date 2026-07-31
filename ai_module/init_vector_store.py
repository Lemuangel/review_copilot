"""
向量库初始化脚本

首次运行：加载数据 → 过滤差评 → 向量化入库
后续运行：如果向量库已存在且非空，可选择跳过或重建
"""
import os
import sys
import argparse

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.data_loader import AmazonReviewLoader, load_and_filter_negative_reviews
from app.vector_store import get_vector_store
from app.config import DATA_PATH


def init_vector_store(
    data_dir: str = None,
    max_reviews: int = 500,
    max_rating: float = 3.0,
    force_rebuild: bool = False,
):
    """
    初始化向量库

    Args:
        data_dir: 数据目录
        max_reviews: 最大加载条数
        max_rating: 差评阈值
        force_rebuild: 是否强制重建
    """
    data_dir = data_dir or DATA_PATH

    print("=" * 60)
    print(" 向量库初始化")
    print("=" * 60)
    print(f" 数据目录: {data_dir}")
    print(f" 最大加载数: {max_reviews}")
    print(f" 差评阈值: ≤{max_rating}星")
    print(f" 强制重建: {force_rebuild}")
    print("=" * 60)

    # 加载数据
    print("\n[1/3] 加载数据...")
    negative_reviews = load_and_filter_negative_reviews(
        data_dir=data_dir,
        max_reviews=max_reviews,
        max_rating=max_rating,
    )

    if not negative_reviews:
        print("[ERROR] 没有加载到差评数据，请检查数据目录")
        return

    # 转换为 Document
    print("\n[2/3] 转换为 Document...")
    loader = AmazonReviewLoader(data_dir)
    documents = loader.to_documents(negative_reviews)

    if not documents:
        print("[ERROR] 没有生成 Document")
        return

    # 构建向量库
    print("\n[3/3] 构建向量库...")
    vs = get_vector_store()

    if force_rebuild:
        # 删除旧向量库
        import shutil
        from app.config import VECTOR_DB_PATH
        if os.path.exists(VECTOR_DB_PATH):
            shutil.rmtree(VECTOR_DB_PATH)
            print(f"[INFO] 已删除旧向量库: {VECTOR_DB_PATH}")

    vs.build(documents)

    # 验证
    stats = vs.get_stats()
    print("\n" + "=" * 60)
    print(" 向量库初始化完成!")
    print(f" 状态: {stats['status']}")
    print(f" 文档数: {stats['count']}")
    print(f" 路径: {stats['path']}")
    print(f" 模型: {stats['embedding_model']}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="初始化向量库")
    parser.add_argument("--data-dir", type=str, default=None, help="数据目录路径")
    parser.add_argument("--max-reviews", type=int, default=500, help="最大加载数")
    parser.add_argument("--max-rating", type=float, default=3.0, help="差评阈值")
    parser.add_argument("--force", action="store_true", help="强制重建")
    args = parser.parse_args()

    init_vector_store(
        data_dir=args.data_dir,
        max_reviews=args.max_reviews,
        max_rating=args.max_rating,
        force_rebuild=args.force,
    )