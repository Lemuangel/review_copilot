"""
评论上传接口
POST /reviews/upload — 上传CSV评论文件 → 保存 review 表
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query

from app.schemas import ReviewUploadResponse, ReviewContextResponse, ReviewListItem
from app.services.review_service import parse_csv, process_reviews, get_review_context, get_review_list, get_review_detail

router = APIRouter(prefix="/reviews", tags=["评论管理"])


@router.post("/upload", response_model=ReviewUploadResponse, summary="上传CSV评论文件")
async def upload_reviews(file: UploadFile = File(..., description="CSV评论文件")):
    """
    上传包含评论数据的CSV文件，解析后写入 review 表。

    支持CSV列名（中英文兼容）：
    - product_id / 商品ID
    - order_id / 订单ID
    - rating / 评分
    - review_text / review_content / content / 评论内容
    - language / 语言

    返回：导入统计 + review_id 列表。
    """
    # 验证文件类型
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="仅支持上传 .csv 格式的文件")

    # 读取文件
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="文件读取失败")

    if not content:
        raise HTTPException(status_code=400, detail="上传的文件为空")

    # 解析CSV
    try:
        rows = parse_csv(content)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"CSV 解析失败: {str(e)}")

    if not rows:
        raise HTTPException(status_code=422, detail="CSV 文件中没有有效数据行")

    # 入库 review 表
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


@router.get("/{review_id}/context", response_model=ReviewContextResponse, summary="查询评论全链路上下文")
async def get_context(review_id: int):
    """
    根据评论ID查询完整业务上下文，包括：

    - review:    评论原文、评分、分类标签
    - product:   商品名称、类别、价格、ASIN
    - order:     订单编号、客户国家、金额、支付方式
    - logistics: 物流承运商、时效、延迟天数、异常原因
    - warehouse: 仓库名称、区域
    - inventory: 当前库存、可用库存

    用于 AI 分析时提供全链路决策依据。
    """
    try:
        context = get_review_context(review_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

    return ReviewContextResponse(**context)


@router.get("", response_model=dict, summary="评论列表（分页）")
async def list_reviews(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=200, description="每页条数"),
):
    """
    分页查询评论列表，返回前端兼容格式。

    响应：{ code: 200, data: [...], total: N }
    """
    try:
        reviews, total = get_review_list(page, size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

    return {"code": 200, "data": reviews, "total": total}


@router.get("/{review_id}", response_model=dict, summary="评论详情")
async def get_review(review_id: int):
    """
    查询单条评论详情，返回前端兼容格式。

    响应：{ code: 200, data: {...} }
    """
    try:
        detail = get_review_detail(review_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

    return {"code": 200, "data": detail}
