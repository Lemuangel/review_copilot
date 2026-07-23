"""
评论上传接口
POST /reviews/upload — 上传CSV评论文件 → 保存 review 表
"""

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.schemas import ReviewUploadResponse
from app.services.review_service import parse_csv, process_reviews

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
