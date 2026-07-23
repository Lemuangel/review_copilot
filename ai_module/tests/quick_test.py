"""
快速测试脚本 - 验证 AI 模块基本功能（不依赖网络）
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.data_loader import AmazonReviewLoader
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
        print(f"  国家: {sample.get('country', 'N/A')}")
        print(f"  类目: {sample.get('category', 'N/A')}")

    # 测试过滤
    negative = loader.filter_by_rating(reviews, max_rating=3.0)
    print(f"\n过滤后差评: {len(negative)} 条")

    # 测试 Document 转换
    docs = loader.to_documents(reviews)
    print(f"转换为 Document: {len(docs)} 个")
    if docs:
        d = docs[0]
        print(f"  第一个 Document:")
        print(f"    page_content: {d.page_content[:100]}...")
        print(f"    metadata keys: {list(d.metadata.keys())}")

    return reviews


def test_data_structure():
    """测试数据格式是否符合预期"""
    print("\n" + "=" * 60)
    print(" 测试 2: 数据格式验证")
    print("=" * 60)

    loader = AmazonReviewLoader(DATA_PATH)
    reviews = loader.load_reviews(max_reviews=5)

    if not reviews:
        print("无数据")
        return

    sample = reviews[0]
    expected_fields = [
        "reviewerID", "asin", "reviewerName", "vote", "style",
        "reviewText", "overall", "summary", "unixReviewTime", "reviewTime"
    ]

    print(f"字段检查:")
    for field in expected_fields:
        present = field in sample
        print(f"  {'✓' if present else '✗'} {field}")

    print(f"\n数据类型:")
    print(f"  overall: {type(sample['overall']).__name__} = {sample['overall']}")
    print(f"  style: {type(sample['style']).__name__} = {sample['style']}")
    print(f"  reviewText 长度: {len(sample.get('reviewText', ''))}")

    # 打印完整样本
    print(f"\n完整样本 (JSON):")
    print(json.dumps(sample, ensure_ascii=False, indent=2)[:500])


def test_prompt_format():
    """测试 Prompt 模板格式"""
    print("\n" + "=" * 60)
    print(" 测试 3: Prompt 模板")
    print("=" * 60)

    from app.prompts import (
        REVIEW_ANALYSIS_SYSTEM,
        REVIEW_ANALYSIS_HUMAN,
        TRANSLATION_SYSTEM,
        REPLY_GENERATION_SYSTEM,
        build_analysis_prompt,
        build_translation_prompt,
        build_reply_prompt,
    )

    print(f"分析 System Prompt 长度: {len(REVIEW_ANALYSIS_SYSTEM)} 字符")
    print(f"分析 Human Prompt 长度: {len(REVIEW_ANALYSIS_HUMAN)} 字符")
    print(f"翻译 System Prompt 长度: {len(TRANSLATION_SYSTEM)} 字符")
    print(f"回复 System Prompt 长度: {len(REPLY_GENERATION_SYSTEM)} 字符")

    # 验证变量
    analysis_prompt = build_analysis_prompt()
    print(f"\n分析 Prompt 变量: {analysis_prompt.input_variables}")

    reply_prompt = build_reply_prompt()
    print(f"回复 Prompt 变量: {reply_prompt.input_variables}")


def test_logistics_detection():
    """测试物流状态检测"""
    print("\n" + "=" * 60)
    print(" 测试 4: 物流状态检测")
    print("=" * 60)

    from app.generator import get_logistics_status

    test_cases = [
        ("The package arrived damaged and crushed.", "abnormal", "包装损坏"),
        ("I've been waiting for 3 weeks and still haven't received it.", "in_transit", "在途"),
        ("I received the item but it doesn't work correctly.", "delivered", "已签收"),
        ("Great product, love it!", "unknown", "好评(无物流问题)"),
        ("The box was completely crushed and the item inside was broken.", "abnormal", "包装破损"),
        ("Still waiting for my order after 2 months, never arrived.", "in_transit", "长时间未到"),
        ("The product arrived on time and works perfectly.", "delivered", "正常签收"),
    ]

    all_pass = True
    for text, expected, desc in test_cases:
        status = get_logistics_status(text, llm=None)
        passed = status == expected
        if not passed:
            all_pass = False
        print(f"  {'✓' if passed else '✗'} {desc}: '{text[:50]}...' → {status} (期望: {expected})")

    if all_pass:
        print("\n 全部通过!")
    else:
        print("\n 部分失败")


def main():
    print("=" * 60)
    print(" AI模块快速测试")
    print("=" * 60)

    test_data_loader()
    test_data_structure()
    test_prompt_format()
    test_logistics_detection()

    print("\n" + "=" * 60)
    print(" 快速测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()