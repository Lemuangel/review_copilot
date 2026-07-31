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
import spacy
from collections import Counter

# spaCy 模型懒加载（避免启动时加载耗时）
_nlp = None

def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

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
    """生成词云数据：从所有差评中提取高频词（spaCy 英文分词）"""
    reviews = db.query(Review).all()
    if not reviews:
        return {"code": 200, "data": []}

    # 1. 拼接所有评论文本
    all_text = " ".join([r.review_text for r in reviews if r.review_text])

    # 2. spaCy 英文分词 + 词形还原 + 词性过滤
    nlp = _get_nlp()
    words = []

    # 领域停用词（Amazon 评论中无意义的常见词）
    domain_stopwords = {
        "product", "item", "buy", "bought", "purchase", "order", "amazon",
        "review", "star", "stars", "one", "two", "get", "got", "would",
        "could", "even", "much", "really", "use", "used", "using",
        "time", "day", "week", "month", "thing",
        "think", "try", "look", "give", "say", "little",
        "come", "turn", "know", "year", "go", "make", "take",
        "good", "unit", "need", "device",
    }

    for doc in nlp.pipe(all_text.split(". "), batch_size=50):
        for token in doc:
            # 只保留名词、形容词、动词、专有名词
            if token.pos_ not in ("NOUN", "ADJ", "VERB", "PROPN"):
                continue
            # 过滤停用词、标点、数字、短词
            if token.is_stop or token.is_punct or token.is_digit:
                continue
            lemma = token.lemma_.lower().strip()
            if len(lemma) < 3:
                continue
            if lemma in domain_stopwords:
                continue
            words.append(lemma)

    # 3. 统计词频，取前 30 个
    word_counts = Counter(words).most_common(30)

    # 英译中对照表
    en2zh = {
        "work": "运行/不工作", "screen": "屏幕", "return": "退货", "sound": "声音",
        "power": "电源", "quality": "质量", "fit": "尺寸/适配", "bad": "差/坏",
        "laptop": "笔记本", "cable": "线缆", "plug": "插头", "problem": "问题",
        "antenna": "天线", "break": "断裂/损坏", "money": "钱/不值",
        "support": "支持/支架", "charge": "充电", "protector": "保护套",
        "adapter": "适配器", "pay": "付款", "card": "卡", "light": "灯/光线",
        "volume": "音量", "plastic": "塑料", "pair": "配对", "touch": "触摸",
        "head": "耳机/头部", "send": "发货", "receive": "收到", "camera": "摄像头",
        "battery": "电池", "phone": "手机", "case": "手机壳", "button": "按钮",
        "speaker": "扬声器", "wire": "线", "connection": "连接", "bluetooth": "蓝牙",
        "mouse": "鼠标", "keyboard": "键盘", "fan": "风扇", "noise": "噪音",
        "temperature": "温度", "speed": "速度", "size": "尺寸", "color": "颜色",
        "material": "材质", "design": "设计", "price": "价格", "delivery": "配送",
        "package": "包装", "box": "盒子", "refund": "退款", "replace": "换货",
        "warranty": "保修", "service": "客服", "brand": "品牌", "market": "市场",
        "seller": "卖家", "shipping": "物流", "delay": "延迟", "damage": "损坏",
    }
    result = [{"name": en2zh.get(w, w), "value": c} for w, c in word_counts]

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

# 从 ai_module 导入 Agent（自动调度：分析→检索→回复）
from ai_module.app.agent import get_agent

@router.post("/generate")
async def generate_ai_response(request: GenerateRequest, db: Session = Depends(get_db)):
    review = db.query(Review).filter(Review.review_id == request.review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="评论不存在")

    try:
        review_data = {
            "asin": review.asin or "unknown",
            "reviewText": review.review_text,
            "overall": review.rating,
            "summary": review.summary or "",
            "style": {},
            "category": review.label or "未分类",
            "country": "US",
        }

        agent = get_agent()

        if request.type == 'reply':
            prompt = (
                f"【注意】RAG向量库暂不可用，请跳过历史案例检索。物流与差评内容无关时也跳过。\n"
                f"【任务】仅生成一段可直接发给顾客的英文客服回复文案，不要分析报告，不要表格，不要建议。\n"
                f"【差评数据】{json.dumps(review_data, ensure_ascii=False)}\n"
                f"【差评原文】{review.review_text}\n"
                f"【输出要求】只输出英文回复正文，100-200词，包含道歉+补偿方案+联系方式。不要其他内容。"
            )
        elif request.type == 'suggestion':
            prompt = (
                f"【注意】RAG跳过，物流无关时跳过。只输出运营建议，绝对不要客服回复文案。\n"
                f"【差评数据】{json.dumps(review_data, ensure_ascii=False)}\n"
                f"【差评原文】{review.review_text}\n"
                f"【输出要求】2-3句分析摘要 + 3-5条改进措施(P0/P1/P2)。纯文本，不要表格，不要客服回复，不要英文内容。"
            )
        else:  # full — 完整诊断
            prompt = (
                f"请对以下差评做完整诊断。\n"
                f"【差评数据】{json.dumps(review_data, ensure_ascii=False)}\n"
                f"【差评原文】{review.review_text}\n"
                f"【输出要求】用简洁格式（不用Markdown表格，用【】标注段落标题）：\n"
                f"【基本信息】ASIN/站点/星级/原文\n"
                f"【8维评分】每维度一行：维度名 分数/5 证据\n"
                f"【根因分析】2-3句话\n"
                f"【历史相似案例】RAG检索到的相似差评及处理策略（如有）\n"
                f"【物流状态】一句话\n"
                f"【英文客服回复】正文100-200词\n"
                f"【运营建议】3-5条 P0/P1/P2"
            )

        result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        messages = result.get("messages", [])
        ai_msgs = [m for m in messages if hasattr(m, "content") and type(m).__name__ == "AIMessage"]
        content = ai_msgs[-1].content if ai_msgs else "Agent 未返回结果"

        return {"code": 200, "data": content}

    except Exception as e:
        print(f"AI 模块调用失败: {e}")
        import traceback
        traceback.print_exc()
        fallback = "【AI生成失败】请检查 ai_module 配置。"
        return {"code": 200, "data": fallback}

