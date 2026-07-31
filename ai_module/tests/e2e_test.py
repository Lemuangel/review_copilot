"""
端到端测试 - 不依赖 FastAPI 服务器
测试: 分析 + RAG检索 + 回复生成
"""
import os, sys, json, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

from app.generator import analyze_review, generate_reply, get_logistics_status
from app.vector_store import get_vector_store

# 测试数据
test_review = {
    "asin": "B00006L9LC",
    "reviewText": "The product arrived completely damaged and leaking. The box was crushed and the bottle was broken. I'm very disappointed with the packaging quality. I waited two weeks for this delivery and it's unusable. Customer service has not responded to my email.",
    "overall": 1.0,
    "summary": "Arrived damaged and leaking, terrible packaging",
    "style": {"Size:": " 7.0 oz"},
    "category": "Beauty",
    "country": "US",
}

print("=" * 60)
print(" 端到端测试")
print("=" * 60)

# 1. 物流状态检测
print("\n[1] 物流状态检测...")
t0 = time.time()
status = get_logistics_status(test_review["reviewText"])
print(f"  → {status} ({time.time()-t0:.1f}s)")

# 2. 向量库检索
print("\n[2] RAG 检索相似案例...")
t0 = time.time()
vs = get_vector_store()
results = vs.similarity_search(test_review["reviewText"], k=3, threshold=0.3)
print(f"  找到 {len(results)} 个相似案例 ({time.time()-t0:.1f}s)")
for i, (doc, score) in enumerate(results):
    print(f"  [{i+1}] {score:.4f} | {doc.metadata['asin']} | {doc.page_content[:80]}...")

# 3. 差评分析 (需要 DeepSeek API)
print("\n[3] 差评分析 (调用 DeepSeek API)...")
t0 = time.time()
try:
    result = analyze_review(test_review, use_rag=True)
    analysis = result.get("analysis", {})
    print(f"  完成 ({time.time()-t0:.1f}s)")
    print(f"  根因: {analysis.get('root_cause', 'N/A')}")
    print(f"  紧急程度: {analysis.get('urgency', 'N/A')}")
    print(f"  标签: {analysis.get('tags', [])}")
    scores = analysis.get("scores", {})
    for dim, info in scores.items():
        if isinstance(info, dict) and info.get("score") is not None:
            print(f"    {dim}: {info['score']}/10")
except Exception as e:
    print(f"  ❌ 分析失败: {e}")
    result = None

# 4. 回复生成
if result:
    print("\n[4] 回复生成 (调用 DeepSeek API)...")
    t0 = time.time()
    try:
        reply = generate_reply(
            analysis_result=analysis,
            review_text=test_review["reviewText"],
            target_language="en",
        )
        print(f"  完成 ({time.time()-t0:.1f}s)")
        print(f"  Subject: {reply.get('subject', 'N/A')}")
        print(f"  Tone: {reply.get('tone', 'N/A')}")
        print(f"  Body: {reply.get('body', 'N/A')[:200]}...")
        print(f"  Compensation: {reply.get('compensation_suggestion', 'N/A')}")
    except Exception as e:
        print(f"  ❌ 回复生成失败: {e}")
else:
    print("\n[4] 跳过回复生成 (分析未完成)")

print("\n" + "=" * 60)
print(" 端到端测试完成!")
print("=" * 60)