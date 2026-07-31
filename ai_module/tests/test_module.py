"""
测试脚本 - 验证 AI 模块各组件功能
"""
import os
import sys
import json

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.data_loader import AmazonReviewLoader
from app.generator import analyze_review, generate_reply, get_logistics_status
from app.vector_store import get_vector_store
from app.config import DATA_PATH


def test_data_loader():
    """测试数据加载器"""
    print("\n" + "=" * 60)
    print(" 测试 1: 数据加载器")
    print("=" * 60)

    loader = AmazonReviewLoader(DATA_PATH)
    reviews = loader.load_reviews(max_reviews=10)

    print(f"加载了 {len(reviews)} 条评论")

    if reviews:
        sample = reviews[0]
        print(f"\n样本数据:")
        print(f"  ASIN: {sample.get('asin', 'N/A')}")
        print(f"  评分: {sample.get('overall', 'N/A')}")
        print(f"  摘要: {sample.get('summary', 'N/A')[:50]}...")
        print(f"  正文: {sample.get('reviewText', 'N/A')[:100]}...")

    # 测试过滤
    negative = loader.filter_by_rating(reviews, max_rating=3.0)
    print(f"\n过滤后差评: {len(negative)} 条")

    # 测试 Document 转换
    docs = loader.to_documents(reviews)
    print(f"转换为 Document: {len(docs)} 个")

    return reviews


def test_vector_store():
    """测试向量库"""
    print("\n" + "=" * 60)
    print(" 测试 2: 向量库")
    print("=" * 60)

    try:
        vs = get_vector_store()
        # 加载数据
        loader = AmazonReviewLoader(DATA_PATH)
        reviews = loader.load_reviews(max_reviews=50)
        docs = loader.to_documents(reviews)

        # 构建向量库
        vs.build(docs)
        stats = vs.get_stats()
        print(f"向量库状态: {json.dumps(stats, ensure_ascii=False)}")

        # 检索测试
        query = "product arrived damaged"
        results = vs.similarity_search(query, k=3)
        print(f"\n检索 '{query}':")
        for i, (doc, score) in enumerate(results):
            print(f"  [{i+1}] 相似度: {score:.4f}, ASIN: {doc.metadata.get('asin', 'N/A')}")
            print(f"      内容: {doc.page_content[:100]}...")

        return True
    except Exception as e:
        print(f"向量库测试失败: {e}")
        return False


def test_analyze():
    """测试分析功能"""
    print("\n" + "=" * 60)
    print(" 测试 3: 差评分析")
    print("=" * 60)

    review_data = {
        "asin": "B08N5WRWNW",
        "reviewText": "The product arrived with a cracked screen. I was very disappointed because I waited two weeks for delivery. The packaging was not sufficient to protect the item during international shipping.",
        "overall": 1.0,
        "summary": "Arrived damaged, poor packaging",
        "style": {"Color": "Black", "Size": "Large"},
        "category": "Electronics",
        "country": "US",
    }

    try:
        result = analyze_review(review_data, use_rag=False)
        print("分析结果:")
        print(json.dumps(result["analysis"], ensure_ascii=False, indent=2))
        return result
    except Exception as e:
        print(f"分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_generate_reply(analysis_result):
    """测试回复生成"""
    print("\n" + "=" * 60)
    print(" 测试 4: 回复生成")
    print("=" * 60)

    review_text = "The product arrived with a cracked screen. Very disappointed."
    try:
        reply = generate_reply(
            analysis_result=analysis_result.get("analysis", {}),
            review_text=review_text,
            target_language="en",
        )
        print("回复结果:")
        print(json.dumps(reply, ensure_ascii=False, indent=2))
        return reply
    except Exception as e:
        print(f"回复生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_logistics():
    """测试物流状态推断"""
    print("\n" + "=" * 60)
    print(" 测试 5: 物流状态推断")
    print("=" * 60)

    test_cases = [
        ("The package arrived damaged and crushed.", "abnormal"),
        ("I've been waiting for 3 weeks and still haven't received it.", "in_transit"),
        ("I received the item but it doesn't work.", "delivered"),
        ("Great product, love it!", "unknown"),
    ]

    for text, expected in test_cases:
        status = get_logistics_status(text)
        marker = "✓" if status == expected else "✗"
        print(f" {marker} '{text[:60]}...' → {status} (期望: {expected})")


def main():
    print("=" * 60)
    print(" AI模块测试套件")
    print("=" * 60)

    # 测试数据加载
    test_data_loader()

    # 测试向量库
    test_vector_store()

    # 测试分析
    result = test_analyze()

    # 测试回复生成
    if result:
        test_generate_reply(result)

    # 测试物流状态
    test_logistics()

    print("\n" + "=" * 60)
    print(" 测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()