"""
差评分析接口
POST /analysis/review — 分析差评 → 保存 analysis_result + operation_suggestion

调用链：
    analysis.py → analysis_service.run_full_analysis()
        ├── ai_service.analyze_review_issues()   → LCEL → issues
        ├── 保存 analysis_result 表
        ├── ai_service.generate_suggestions()    → LCEL → suggestions
        └── 保存 operation_suggestion 表
"""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas import AnalysisRequest, AnalysisResponse
from app.services.analysis_service import run_full_analysis

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
        suggestions=result["suggestions"],
    )
