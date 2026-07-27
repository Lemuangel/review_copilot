"""
评论上传接口
POST /reviews/upload — 上传CSV评论文件 → 保存 review 表
"""
import os
import json
import openai
from fastapi import APIRouter, UploadFile, File, HTTPException,Depends
from sqlalchemy.orm import Session
from ..database.database import get_db
from ..models import Review
from ..schemas import ReviewUploadResponse
from ..services.review_service import parse_csv, process_reviews
from ..services.prompt_service import customer_reply_prompt, operation_suggestion_prompt
from pydantic import BaseModel
import sys
from pathlib import Path
import jieba
from collections import Counter

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


@router.get("", summary="获取所有评论列表")
async def get_reviews(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    """
    获取所有评论列表，支持分页。
    """
    query = db.query(Review)
    total = query.count()
    reviews = query.offset(skip).limit(limit).all()

    result = []
    for r in reviews:
        result.append({
            "review_id": r.review_id,
            "product_id": r.product_id,
            "order_id": r.order_id,
            "reviewer_id": r.reviewer_id,
            "reviewer_name": r.reviewer_name,
            "asin": r.asin,
            "rating": r.rating,
            "review_text": r.review_text,
            "summary": r.summary,
            "language": r.language,
            "review_time": r.review_time.isoformat() if r.review_time else None,
            "label": r.label,
        })

    return {
        "code": 200,
        "data": result,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/wordcloud")
async def get_wordcloud(db: Session = Depends(get_db)):
    """生成词云数据：从所有差评中提取高频词"""
    # 1. 获取所有评论
    reviews = db.query(Review).all()
    if not reviews:
        return {"code": 200, "data": []}

    # 2. 拼接所有评论文本
    all_text = " ".join([r.review_text for r in reviews if r.review_text])

    # 3. 中文分词（同时处理英文和中文）
    words = []
    # 英文分词（按空格和标点分割）
    import re
    english_words = re.findall(r'\b[a-zA-Z]{3,}\b', all_text)
    words.extend([w.lower() for w in english_words])

    # 中文分词（如果文本包含中文）
    chinese_words = jieba.lcut(all_text)
    words.extend([w for w in chinese_words if len(w) > 1])

    # 4. 停用词过滤（去掉无意义的词）
    stopwords = {
        # 英文停用词（扩充）
        'a', 'an', 'the', 'and', 'or', 'but', 'for', 'nor', 'on', 'at', 'to', 'by',
        'in', 'of', 'off', 'out', 'over', 'under', 'with', 'without', 'after',
        'before', 'during', 'through', 'between', 'among', 'upon', 'about',
        'above', 'across', 'along', 'around', 'at', 'behind', 'below',
        'beneath', 'beside', 'beyond', 'down', 'from', 'into', 'near',
        'off', 'onto', 'toward', 'up', 'upon', 'within', 'without',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'us', 'them',
        'my', 'your', 'his', 'her', 'our', 'their', 'its', 'mine', 'yours',
        'hers', 'ours', 'theirs', 'am', 'is', 'are', 'was', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'must', 'shall',
        'this', 'that', 'these', 'those', 'then', 'now', 'than', 'so',
        'too', 'very', 'just', 'only', 'also', 'again', 'ever', 'never',
        'once', 'always', 'often', 'sometimes', 'usually', 'already',
        'yet', 'still', 'almost', 'quite', 'rather', 'really', 'actually',
        'basically', 'certainly', 'definitely', 'obviously', 'probably',
        'simply', 'suddenly', 'eventually', 'finally', 'soon', 'later',
        'earlier', 'else', 'something', 'anything', 'nothing', 'everything',
        'someone', 'anyone', 'no one', 'everyone', 'everybody', 'nobody',
        'somebody', 'anybody', 'everything', 'nothing', 'something',
        'for', 'with', 'without', 'like', 'as', 'than', 'that', 'which',
        'who', 'whom', 'whose', 'what', 'where', 'when', 'why', 'how','not','all',
        'one','two'
        # 常见缩写
        "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't",
        "haven't", "hasn't", "hadn't", "won't", "wouldn't", "couldn't",
        "shouldn't", "mightn't", "mustn't", "can't", "cannot", "i'll", "you'll",
        "he'll", "she'll", "it'll", "we'll", "they'll", "i'd", "you'd", "he'd",
        "she'd", "it'd", "we'd", "they'd", "i'm", "you're", "he's", "she's",
        "it's", "we're", "they're",
        # 中文停用词（保留）
        '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '个',
        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
        '能', '多', '更', '对', '可', '还', '之', '与', '或', '等', '后', '前', '等'
    }
    filtered_words = [w for w in words if w not in stopwords and len(w) > 1]

    # 5. 统计词频，取前 30 个
    word_counts = Counter(filtered_words).most_common(30)
    result = [{"name": w, "value": c} for w, c in word_counts]

    return {"code": 200, "data": result}

@router.get("/statistics")
async def get_statistics(db: Session = Depends(get_db)):
    """获取统计数据（总数、分类分布、星级分布）"""
    reviews = db.query(Review).all()

    total = len(reviews)
    categories = {}
    star_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    for r in reviews:
        # 分类统计
        label = r.label or "未分类"
        categories[label] = categories.get(label, 0) + 1

        # 星级统计
        if r.rating in star_distribution:
            star_distribution[r.rating] += 1

    return {
        "code": 200,
        "data": {
            "total": total,
            "categories": [{"name": k, "value": v} for k, v in categories.items()],
            "starDistribution": [{"star": k, "count": v} for k, v in star_distribution.items() if v > 0]
        }
    }


@router.get("/{review_id}")
async def get_review_by_id(review_id: int, db: Session = Depends(get_db)):
    """根据 ID 获取单条差评详情"""
    review = db.query(Review).filter(Review.review_id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="评论不存在")

    return {
        "review_id": review.review_id,
        "product_id": review.product_id,
        "order_id": review.order_id,
        "reviewer_id": review.reviewer_id,
        "reviewer_name": review.reviewer_name,
        "asin": review.asin,
        "rating": review.rating,
        "review_text": review.review_text,
        "summary": review.summary,
        "language": review.language,
        "review_time": review.review_time.isoformat() if review.review_time else None,
        "label": review.label,
    }

class GenerateRequest(BaseModel):
    review_id: int
    type: str

AI_MODULE_PATH = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(AI_MODULE_PATH))

# 从 ai_module 导入生成函数（假设你在 generator.py 中定义了这些函数）
from ai_module.app.generator import generate_reply, analyze_review

@router.post("/generate")
async def generate_ai_response(request: GenerateRequest, db: Session = Depends(get_db)):
    review = db.query(Review).filter(Review.review_id == request.review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="评论不存在")

    try:
        # 构建 review_data 字典（符合 analyze_review 的输入要求）
        review_data = {
            "asin": review.asin or "unknown",
            "reviewText": review.review_text,
            "overall": review.rating,
            "summary": review.summary or "",
            "style": {},
            "category": review.label or "未分类",
            "country": "US",  # 如果有 country 字段可从数据库获取
        }

        # 调用 analyze_review 获取完整分析结果（包含 analysis 和 similar_cases 等）
        result = analyze_review(review_data, use_rag=False)
        analysis = result.get("analysis", {})

        if request.type == 'reply':
            # 调用 generate_reply 生成客服回复
            # generate_reply 需要 analysis_result（字典）、review_text、target_language
            reply_dict = generate_reply(
                analysis_result=analysis,
                review_text=review.review_text,
                target_language="en"  # 可根据需要调整
            )
            # reply_dict 包含 subject, body, tone 等字段
            content = reply_dict.get("body", "回复生成失败")
        else:  # suggestion
            # 从分析结果中提取建议（例如 root_cause）
            root_cause = analysis.get("root_cause", "未识别到具体问题")
            tags = analysis.get("tags", [])
            # 可以组合生成更丰富的建议
            content = f"【运营建议】基于差评分析，建议重点关注：{root_cause}。相关标签：{', '.join(tags)}"

        return {"code": 200, "data": content}

    except Exception as e:
        print(f"AI 模块调用失败: {e}")
        import traceback
        traceback.print_exc()  # 打印完整堆栈，方便调试
        fallback = "【AI生成失败】请检查 ai_module 配置。"
        return {"code": 200, "data": fallback}

