"""
AI算法模块 - FastAPI 主入口

对外API接口：
- POST /ai/analyze        差评8维分析
- POST /ai/generate_reply  多语言回复生成
- POST /ai/rag_retrieve    历史案例检索
- GET  /ai/health          健康检查
- GET  /ai/stats           向量库统计
- GET  /ai/cache/stats     分析缓存统计
- POST /ai/chain           全链路处理（分析+RAG+回复）
- POST /ai/agent           Agent自主调度
- POST /ai/batch           批量并发分析
"""
import json
import time
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import DEEPSEEK_MODEL
from app.generator import analyze_review, generate_reply, get_logistics_status, _ANALYSIS_CACHE
from app.vector_store import get_vector_store
from app.translation_eval import evaluate_translation, batch_evaluate
from app.prompt_ab import prompt_version_manager, ABTestRunner
from app.agent import get_agent

# ============================================================
# FastAPI 应用
# ============================================================
app = FastAPI(
    title="AI差评分析引擎",
    description="基于 DeepSeek + LangChain 的跨境电商差评智能分析系统",
    version="1.0.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Pydantic 模型
# ============================================================
class AnalyzeRequest(BaseModel):
    """差评分析请求"""
    review_text: str
    asin: Optional[str] = "unknown"
    category: Optional[str] = "unknown"
    overall: Optional[float] = 1.0
    summary: Optional[str] = ""
    style: Optional[dict] = {}
    country: Optional[str] = "unknown"
    reviewer_id: Optional[str] = ""
    use_rag: Optional[bool] = True


class GenerateReplyRequest(BaseModel):
    """回复生成请求"""
    review_text: str
    analysis_result: dict
    target_language: Optional[str] = "en"


class RAGRetrieveRequest(BaseModel):
    """RAG检索请求"""
    query: str
    top_k: Optional[int] = 5


class ChainRequest(BaseModel):
    """全链路处理请求"""
    review_text: str
    asin: Optional[str] = "unknown"
    category: Optional[str] = "unknown"
    overall: Optional[float] = 1.0
    summary: Optional[str] = ""
    style: Optional[dict] = {}
    country: Optional[str] = "unknown"
    target_language: Optional[str] = "en"


# ============================================================
# API 路由
# ============================================================
@app.get("/ai/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "model": DEEPSEEK_MODEL,
        "service": "AI差评分析引擎",
    }


@app.get("/ai/stats")
async def vector_store_stats():
    """向量库统计信息"""
    vs = get_vector_store()
    return vs.get_stats()


@app.post("/ai/analyze")
async def analyze_endpoint(req: AnalyzeRequest):
    """
    差评8维分析

    输入：差评文本、SKU、类目、国家等
    输出：8维评分、根因、紧急程度、标签
    """
    try:
        review_data = {
            "reviewText": req.review_text,
            "asin": req.asin,
            "category": req.category,
            "overall": req.overall,
            "summary": req.summary,
            "style": req.style,
            "country": req.country,
            "reviewerID": req.reviewer_id,
        }

        result = analyze_review(review_data, use_rag=req.use_rag)

        return {
            "status": "success",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/generate_reply")
async def generate_reply_endpoint(req: GenerateReplyRequest):
    """
    多语言回复生成

    输入：差评文本、分析结果、目标语言
    输出：回复主题、正文、语气、补偿建议、跟进动作
    """
    try:
        reply = generate_reply(
            analysis_result=req.analysis_result,
            review_text=req.review_text,
            target_language=req.target_language,
        )

        return {
            "status": "success",
            "data": reply,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/rag_retrieve")
async def rag_retrieve_endpoint(req: RAGRetrieveRequest):
    """
    RAG历史案例检索

    输入：差评文本、Top-K
    输出：历史策略列表及相似度
    """
    try:
        vs = get_vector_store()
        results = vs.similarity_search(req.query, k=req.top_k)

        cases = []
        for doc, score in results:
            cases.append({
                "similarity": round(score, 4),
                "asin": doc.metadata.get("asin", ""),
                "overall": doc.metadata.get("overall", 0),
                "content": doc.page_content[:500],
                "review_time": doc.metadata.get("review_time", ""),
                "style": doc.metadata.get("style", {}),
            })

        return {
            "status": "success",
            "data": {
                "found": len(cases) > 0,
                "count": len(cases),
                "cases": cases,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/chain")
async def chain_endpoint(req: ChainRequest):
    """
    全链路处理：分析 → RAG检索 → 回复生成

    输入：差评完整信息
    输出：分析结果 + 相似案例 + 回复文案
    """
    try:
        # Step 1: 分析
        review_data = {
            "reviewText": req.review_text,
            "asin": req.asin,
            "category": req.category,
            "overall": req.overall,
            "summary": req.summary,
            "style": req.style,
            "country": req.country,
        }

        analysis_result = analyze_review(review_data, use_rag=True)

        # Step 2: 生成回复
        reply = generate_reply(
            analysis_result=analysis_result.get("analysis", {}),
            review_text=req.review_text,
            target_language=req.target_language,
        )

        return {
            "status": "success",
            "data": {
                "analysis": analysis_result.get("analysis", {}),
                "similar_cases": analysis_result.get("similar_cases", []),
                "reply": reply,
                "translated_text": analysis_result.get("translated_text"),
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/agent")
async def agent_endpoint(req: ChainRequest):
    """
    Agent 自主调度处理

    输入：差评文本
    输出：Agent 自主决策调用工具，完成分析+检索+回复
    """
    try:
        agent = get_agent()

        # 构建输入
        review_json = json.dumps({
            "reviewText": req.review_text,
            "asin": req.asin,
            "category": req.category,
            "overall": req.overall,
            "summary": req.summary,
            "style": req.style,
            "country": req.country,
        }, ensure_ascii=False)

        user_message = f"""请处理以下差评，完成完整分析流程：

{review_json}

目标语言: {req.target_language}

请依次调用工具完成分析、检索、回复生成。"""

        result = agent.invoke({"messages": [{"role": "user", "content": user_message}]})

        # 提取最后一条消息作为输出
        messages = result.get("messages", [])
        final_output = messages[-1].content if messages else "Agent 处理完成"

        return {
            "status": "success",
            "data": {
                "agent_output": final_output,
                "message_count": len(messages),
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 缓存统计
# ============================================================
class BatchAnalysisRequest(BaseModel):
    """批量分析请求"""
    reviews: List[dict]  # 差评列表
    use_rag: Optional[bool] = True
    max_workers: Optional[int] = 3


@app.get("/ai/cache/stats")
async def cache_stats():
    """获取分析缓存统计"""
    return {
        "status": "success",
        "data": {
            "cache_size": len(_ANALYSIS_CACHE),
            "cache_max": 200,
            "cache_ttl": 3600,
            "cached_items": [
                {"key": k[:8] + "...", "age_seconds": int(time.time() - v[0])}
                for k, v in list(_ANALYSIS_CACHE.items())[:10]
            ]
        }
    }


@app.post("/ai/cache/clear")
async def cache_clear():
    """清空分析缓存"""
    count = len(_ANALYSIS_CACHE)
    _ANALYSIS_CACHE.clear()
    return {"status": "success", "data": {"cleared": count}}


class TranslationEvalRequest(BaseModel):
    """翻译评估请求"""
    original: str
    translated: str
    reference: Optional[str] = None
    keywords: Optional[List[str]] = None
    use_semantic: Optional[bool] = False


class BatchTranslationEvalRequest(BaseModel):
    """批量翻译评估请求"""
    translations: List[dict]
    use_semantic: Optional[bool] = False


@app.post("/ai/eval/translation")
async def eval_translation(req: TranslationEvalRequest):
    """
    翻译质量评估
    
    输入：原文、译文、参考译文（可选）
    输出：综合评分(0-100)、等级、详细指标、问题列表
    """
    try:
        result = evaluate_translation(
            original=req.original,
            translated=req.translated,
            reference=req.reference,
            keywords=req.keywords,
            use_semantic=req.use_semantic,
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/eval/translation/batch")
async def eval_translation_batch(req: BatchTranslationEvalRequest):
    """
    批量翻译质量评估
    
    输入：翻译对列表
    输出：批量评估报告
    """
    try:
        result = batch_evaluate(
            translations=req.translations,
            use_semantic=req.use_semantic,
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Prompt 版本管理 + A/B 测试
# ============================================================
# 全局 A/B 测试实例
_ab_test_instance: Optional[ABTestRunner] = None


def get_ab_test() -> ABTestRunner:
    global _ab_test_instance
    if _ab_test_instance is None:
        _ab_test_instance = ABTestRunner(prompt_version_manager, "analysis_prompt_test")
        _ab_test_instance.setup_test(["v1_original", "v2_enhanced"], weights=[0.5, 0.5])
    return _ab_test_instance


class ABFeedbackRequest(BaseModel):
    """A/B测试反馈请求"""
    version: str
    rating: str  # "good" | "bad" | "neutral"
    comment: Optional[str] = ""
    review_id: Optional[str] = ""
    reviewer: Optional[str] = "anonymous"


@app.get("/ai/prompt/versions")
async def list_prompt_versions():
    """列出所有 Prompt 版本"""
    return {
        "status": "success",
        "data": prompt_version_manager.list_versions()
    }


@app.post("/ai/prompt/activate")
async def activate_prompt_version(version: str):
    """切换活跃 Prompt 版本"""
    try:
        prompt_version_manager.set_active(version)
        return {"status": "success", "data": {"active": version}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/ai/ab/report")
async def ab_test_report():
    """获取 A/B 测试报告"""
    ab = get_ab_test()
    return {"status": "success", "data": ab.report()}


@app.post("/ai/ab/feedback")
async def ab_test_feedback(req: ABFeedbackRequest):
    """提交 A/B 测试人工反馈"""
    ab = get_ab_test()
    ab.add_feedback(req.version, {
        "rating": req.rating,
        "comment": req.comment,
        "review_id": req.review_id,
        "reviewer": req.reviewer,
    })
    return {"status": "success", "data": {"version": req.version, "rating": req.rating}}


@app.post("/ai/batch")
async def batch_analyze(req: BatchAnalysisRequest):
    """
    批量并发分析差评
    
    输入：差评列表
    输出：每条差评的分析结果
    """
    t0 = time.time()
    results = []
    errors = []
    
    def analyze_one(review: dict, idx: int):
        try:
            review_data = {
                "reviewText": review.get("review_text", review.get("reviewText", "")),
                "asin": review.get("asin", "unknown"),
                "category": review.get("category", "unknown"),
                "overall": review.get("overall", 1.0),
                "summary": review.get("summary", ""),
                "style": review.get("style", {}),
                "country": review.get("country", "unknown"),
            }
            result = analyze_review(review_data, use_rag=req.use_rag)
            return {"index": idx, "status": "success", "data": result}
        except Exception as e:
            return {"index": idx, "status": "error", "error": str(e)}
    
    with ThreadPoolExecutor(max_workers=min(req.max_workers, len(req.reviews))) as pool:
        futures = {
            pool.submit(analyze_one, review, i): i 
            for i, review in enumerate(req.reviews)
        }
        for future in as_completed(futures):
            results.append(future.result())
    
    # 按索引排序
    results.sort(key=lambda x: x["index"])
    
    return {
        "status": "success",
        "data": {
            "total": len(req.reviews),
            "success": sum(1 for r in results if r["status"] == "success"),
            "error": sum(1 for r in results if r["status"] == "error"),
            "elapsed_seconds": round(time.time() - t0, 1),
            "results": results,
        }
    }


# ============================================================
# 启动入口
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)