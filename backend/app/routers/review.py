"""
评论上传接口
POST /reviews/upload — 上传CSV评论文件 → 保存 review 表
GET  /reviews        — 评论列表（分页）
GET  /reviews/{id}   — 评论详情
GET  /reviews/{id}/context — 全链路上下文
GET  /reviews/statistics   — Dashboard统计
POST /reviews/generate     — AI生成回复/建议
GET  /reviews/wordcloud    — 词云数据
"""
import re
from collections import Counter

import jieba
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models import Review
from app.schemas import ReviewUploadResponse, ReviewContextResponse, ReviewListItem, GenerateRequest
from app.services.review_service import (
    parse_csv, process_reviews,
    get_review_context, get_review_list, get_review_detail,
)
from app.services.analysis_service import get_frontend_statistics, run_generate

router = APIRouter(prefix="/reviews", tags=["评论管理"])


@router.post("/upload", response_model=ReviewUploadResponse, summary="上传CSV评论文件")
async def upload_reviews(file: UploadFile = File(..., description="CSV评论文件")):
    """上传包含评论数据的CSV文件，解析后写入 review 表。"""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="仅支持上传 .csv 格式的文件")
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="文件读取失败")
    if not content:
        raise HTTPException(status_code=400, detail="上传的文件为空")
    try:
        rows = parse_csv(content)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"CSV 解析失败: {str(e)}")
    if not rows:
        raise HTTPException(status_code=422, detail="CSV 文件中没有有效数据行")
    try:
        imported_count, review_ids = process_reviews(rows, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据入库失败: {str(e)}")
    return ReviewUploadResponse(
        total_rows=len(rows),
        imported_count=imported_count,
        message=f"成功处理 {imported_count}/{len(rows)} 条评论",
        review_ids=review_ids,
    )


# ============================================================
# 评论上下文查询
# ============================================================

@router.get("/{review_id}/context", response_model=ReviewContextResponse, summary="查询评论全链路上下文")
async def get_context(review_id: int):
    """根据评论ID查询完整业务上下文：review + product + order + logistics + warehouse + inventory"""
    try:
        context = get_review_context(review_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
    return ReviewContextResponse(**context)


# ============================================================
# 前端接口：/statistics /generate /wordcloud 必须在 /{review_id} 前面
# ============================================================

@router.get("", response_model=dict, summary="评论列表（分页）")
async def list_reviews(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=200, description="每页条数"),
):
    try:
        reviews, total = get_review_list(page, size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
    return {"data": reviews, "total": total}


@router.get("/statistics", response_model=dict, summary="前端Dashboard统计")
async def get_frontend_stats():
    try:
        stats = get_frontend_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"统计查询失败: {str(e)}")
    return {"data": stats}


@router.post("/generate", response_model=dict, summary="AI生成回复/建议")
async def generate_ai(request: GenerateRequest):
    try:
        rid = int(request.review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="review_id 必须是数字")
    try:
        result = run_generate(rid, request.type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 服务调用失败: {str(e)}")
    return {"data": result}


@router.get("/wordcloud", summary="词云数据")
async def get_wordcloud(db: Session = Depends(get_db)):
    """生成词云数据：从所有差评中提取高频词"""
    reviews = db.query(Review).all()
    if not reviews:
        return {"code": 200, "data": []}
    all_text = " ".join([r.review_text for r in reviews if r.review_text])
    words = []
    english_words = re.findall(r'\b[a-zA-Z]{3,}\b', all_text)
    words.extend([w.lower() for w in english_words])
    chinese_words = jieba.lcut(all_text)
    words.extend([w for w in chinese_words if len(w) > 1])
    stopwords = {
        'a', 'an', 'the', 'and', 'or', 'but', 'for', 'nor', 'on', 'at', 'to', 'by',
        'in', 'of', 'off', 'out', 'over', 'under', 'with', 'without', 'after',
        'before', 'during', 'through', 'between', 'among', 'upon', 'about',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'us', 'them',
        'my', 'your', 'his', 'her', 'our', 'their', 'is', 'are', 'was', 'were',
        'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall',
        'this', 'that', 'these', 'those', 'then', 'now', 'not', 'so', 'too',
        'very', 'just', 'only', 'also', 'again', 'ever', 'never', 'all',
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
        '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着',
        '没有', '看', '好', '自己', '这', '他', '她', '它', '们',
    }
    filtered = [w for w in words if w.lower() not in stopwords]
    counter = Counter(filtered)
    result = [{"name": word, "value": count} for word, count in counter.most_common(100)]
    return {"code": 200, "data": result}


@router.get("/{review_id}", response_model=dict, summary="评论详情")
async def get_review(review_id: int):
    try:
        detail = get_review_detail(review_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
    return {"data": detail}
