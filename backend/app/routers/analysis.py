"""
差评分析接口
POST /analysis/review — 分析差评 → 保存 analysis_result + operation_suggestion

调用链：
    analysis.py → analysis_service.run_full_analysis()
        ├── langchain_service.analyze_with_lcel()  → LCEL → issues
        ├── 保存 analysis_result 表
        ├── langchain_service.suggest_with_lcel()  → LCEL → suggestions
        └── 保存 operation_suggestion 表
"""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas import AnalysisRequest, AnalysisResponse, StatisticsResponse, FrontendStatsResponse, GenerateRequest
from app.services.analysis_service import run_full_analysis, get_statistics, get_frontend_statistics, run_generate
from app.database.import_data import import_from_csv
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["差评分析"])


@router.post("/review", response_model=AnalysisResponse, summary="分析差评并保存结果")
async def analyze_review(request: AnalysisRequest):
    """
    对一条差评执行完整分析流程：

    1. AI 识别问题分类 → 写入 analysis_result
    2. AI 生成运营建议 → 写入 operation_suggestion

    入参可携带 review_id，用于关联数据库记录。
    """
    try:
        result = run_full_analysis(
            review_id=request.review_id or 0,
            review_text=request.review_text,
            save_to_db=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"分析流程失败: {e}")
        raise HTTPException(status_code=502, detail=f"AI 服务调用失败: {str(e)}")

    return AnalysisResponse(
        review_id=result["review_id"] or None,
        analysis_id=result["analysis_id"],
        suggestion_id=result["suggestion_id"],
        issues=result["issues"],
        root_cause=result.get("root_cause", ""),
        evidence=result.get("evidence", []),
        suggestions=result["suggestions"],
        context_used=result.get("context_used", False),
    )


@router.get("/statistics", response_model=StatisticsResponse, summary="统计分析Dashboard")
async def get_dashboard_statistics():
    """
    聚合统计分析接口，返回：

    - total_reviews:      评论总数
    - negative_ratio:     差评占比
    - label_distribution: 问题分类分布（ProductQuality/Logistics/...）
    - severity_distribution: 严重程度分布（high/medium/low）
    - logistics_distribution: 物流状态分布（Delivered/In Transit/Exception）
    - analyzed_count:     已AI分析的评论数

    用于Dashboard展示，纯SQL聚合查询，不调用AI。
    """
    try:
        stats = get_statistics()
    except Exception as e:
        logger.error(f"统计查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"统计查询失败: {str(e)}")

    return StatisticsResponse(**stats)


# ============================================================
# 前端接口（无 /analysis 前缀，对齐 view.vue 调用）
# ============================================================

frontend_router = APIRouter(tags=["前端接口"])


@frontend_router.get("/statistics", response_model=dict, summary="前端Dashboard统计")
async def get_frontend_stats():
    """
    前端兼容的统计接口，返回格式对齐 data.js mock：
    { code: 200, data: { total, categories: [{name, value}], starDistribution: [{star, count}] } }
    """
    try:
        stats = get_frontend_statistics()
    except Exception as e:
        logger.error(f"前端统计查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"统计查询失败: {str(e)}")

    return {"code": 200, "data": stats}


@frontend_router.post("/generate", response_model=dict, summary="AI生成回复/建议")
async def generate_ai(request: GenerateRequest):
    """
    统一的 AI 生成接口，对齐前端 generateAIForReview()：
    - type=reply:    生成客服回复
    - type=suggestion: 生成运营建议

    响应：{ code: 200, data: "生成文本" }
    """
    try:
        review_id = int(request.reviewId)
    except ValueError:
        raise HTTPException(status_code=400, detail="reviewId 必须是数字")

    try:
        result = run_generate(review_id, request.type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"AI生成失败: {e}")
        raise HTTPException(status_code=502, detail=f"AI 服务调用失败: {str(e)}")

    return {"code": 200, "data": result}


@frontend_router.post("/sync", response_model=dict, summary="同步数据")
async def sync_data():
    """
    重新读取 full_dataset.csv 并导入 MySQL。

    同学更新 CSV 后，调用此接口即可完成数据同步，无需手动执行脚本。
    导入脚本自带去重，可安全重复执行。
    """
    # 直接读沈东阳 data/output/ 的输出
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    csv_path = os.path.join(base_dir, "..", "data", "output", "full_dataset.csv")
    csv_path = os.path.normpath(csv_path)

    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail=f"CSV 文件不存在: {csv_path}")

    try:
        stats = import_from_csv(csv_path)
    except Exception as e:
        logger.error(f"数据同步失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据导入失败: {str(e)}")

    # 同步到 Chroma
    chroma_count = 0
    try:
        from app.services.vector_service import sync_reviews_to_chroma, get_chroma_stats
        chroma_count = sync_reviews_to_chroma(stats.get("_new_reviews", []))
        chroma_stats = get_chroma_stats()
    except Exception as e:
        chroma_stats = {"error": str(e)}
        logger.warning(f"向量库同步失败: {e}")

    return {"code": 200, "data": {
        "message": "数据同步完成",
        "total_rows": stats["review"]["total"],
        "new_products": stats["product"]["new"],
        "new_orders": stats["orders"]["new"],
        "new_reviews": stats["review"]["new"],
        "chroma_vectors": chroma_stats.get("vector_count", 0),
        "chroma_new": chroma_count,
    }}


@frontend_router.post("/sync-vectors", response_model=dict, summary="全量同步向量库")
async def sync_all_vectors():
    """
    将 MySQL 中所有评论全量同步到 Chroma 向量库。

    用于首次初始化或修复向量库与 MySQL 不一致的情况。
    """
    from app.database.database import SessionLocal
    from app.models import Review
    from app.services.vector_service import sync_reviews_to_chroma, get_chroma_stats

    db = SessionLocal()
    try:
        reviews = db.query(Review).all()
    finally:
        db.close()

    if not reviews:
        raise HTTPException(status_code=404, detail="MySQL 中没有评论数据")

    try:
        count = sync_reviews_to_chroma(reviews)
        stats = get_chroma_stats()
    except Exception as e:
        logger.error(f"全量向量同步失败: {e}")
        raise HTTPException(status_code=500, detail=f"向量同步失败: {str(e)}")

    return {"code": 200, "data": {
        "message": "全量向量同步完成",
        "mysql_reviews": len(reviews),
        "chroma_vectors": stats.get("vector_count", 0),
        "synced": count,
    }}
