"""
客服回复生成接口
POST /customer/reply — 生成客服回复 → 保存 customer_reply 表

调用链：
    customer.py → analysis_service.run_customer_reply()
        ├── ai_service.generate_reply()   → LCEL → reply
        └── 保存 customer_reply 表
"""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas import CustomerReplyRequest, CustomerReplyResponse
from app.services.analysis_service import run_customer_reply

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customer", tags=["客服回复"])


@router.post("/reply", response_model=CustomerReplyResponse, summary="生成客服回复并保存")
async def generate_customer_reply(request: CustomerReplyRequest):
    """
    基于差评内容生成专业客服回复，并保存到 customer_reply 表。

    入参可携带 review_id，用于关联数据库记录。
    """
    try:
        result = run_customer_reply(
            review_id=request.review_id or 0,
            review_text=request.review_text,
            save_to_db=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"客服回复生成失败: {e}")
        raise HTTPException(status_code=502, detail=f"AI 服务调用失败: {str(e)}")

    return CustomerReplyResponse(
        review_id=result["review_id"] or None,
        reply_id=result["reply_id"],
        reply_text=result["reply_text"],
    )
