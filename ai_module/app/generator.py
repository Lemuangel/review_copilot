"""
多语言翻译与文案生成器

包含：
1. 小语种翻译为英文的预处理
2. 基于物流状态的差异化回复生成
3. 结构化 JSON 输出解析

所有重依赖（langchain_openai, langchain_core.output_parsers）均 Lazy 导入。
"""
from __future__ import annotations

import json
import re
import hashlib
import time
from functools import lru_cache
from typing import Dict, Optional, List, Tuple, TYPE_CHECKING

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from app.prompts import (
    build_translation_prompt,
    build_reply_prompt,
    format_rag_context,
    sanitize_analysis_input,
)
from app.vector_store import get_vector_store

if TYPE_CHECKING:
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.runnables import RunnableSerializable


# ============================================================
# 1. LLM 初始化
# ============================================================
def init_llm(temperature: float = 0.3, streaming: bool = False):
    """初始化 DeepSeek LLM
    
    Args:
        temperature: 温度参数
        streaming: 是否启用流式输出（降低首字延迟）
    """
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=DEEPSEEK_MODEL,
        openai_api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=temperature,
        streaming=streaming,
    )


# ============================================================
# 1.5 分析结果缓存（LRU，减少重复API调用）
# ============================================================
_ANALYSIS_CACHE: Dict[str, Tuple[float, Dict]] = {}
_CACHE_MAX_SIZE = 200
_CACHE_TTL = 3600  # 1小时


def _cache_key(review_text: str) -> str:
    """生成缓存键"""
    return hashlib.md5(review_text.encode()).hexdigest()


def _get_cached(key: str) -> Optional[Dict]:
    """获取缓存结果"""
    if key in _ANALYSIS_CACHE:
        ts, result = _ANALYSIS_CACHE[key]
        if time.time() - ts < _CACHE_TTL:
            return result
        del _ANALYSIS_CACHE[key]
    return None


def _set_cache(key: str, result: Dict):
    """设置缓存"""
    if len(_ANALYSIS_CACHE) >= _CACHE_MAX_SIZE:
        # 移除最旧的条目
        oldest = min(_ANALYSIS_CACHE.items(), key=lambda x: x[1][0])
        del _ANALYSIS_CACHE[oldest[0]]
    _ANALYSIS_CACHE[key] = (time.time(), result)


# ============================================================
# 2. 小语种翻译
# ============================================================
def translate_to_english(review_text: str, llm=None) -> str:
    """
    将非英语评论翻译为英文

    简单策略：检测文本中的非ASCII字符比例，如果超过一定阈值则翻译

    Args:
        review_text: 原始评论文本
        llm: LLM 实例（可选）

    Returns:
        英文翻译文本
    """
    if not llm:
        llm = init_llm(temperature=0.0)

    # 检测是否需要翻译
    non_ascii_ratio = sum(1 for c in review_text if ord(c) > 127) / max(len(review_text), 1)

    if non_ascii_ratio < 0.05:
        # 已经是英文为主
        return review_text

    # 简单的大语言检测
    has_cjk = any('\u4e00' <= c <= '\u9fff' or '\u3040' <= c <= '\u30ff' for c in review_text)
    has_arabic = any('\u0600' <= c <= '\u06ff' for c in review_text)
    has_cyrillic = any('\u0400' <= c <= '\u04ff' for c in review_text)

    if not (has_cjk or has_arabic or has_cyrillic):
        # 非主要小语种，可能是特殊字符，保持原样
        return review_text

    # 翻译
    prompt = build_translation_prompt()
    chain = prompt | llm
    result = chain.invoke({"review_text": review_text})
    return result.content


# ============================================================
# 3. 物流状态模拟
# ============================================================
LOGISTICS_STATUSES = {
    "delivered": "已签收 - 包裹已送达，但买家对物流速度或包装不满意",
    "in_transit": "在途中 - 包裹仍在运输中，买家因等待时间过长不满",
    "abnormal": "异常 - 包裹丢失、海关扣件、破损退回等",
    "unknown": "未知 - 无法确定物流状态"
}


def get_logistics_status(review_text: str, llm=None) -> str:
    """
    从评论文本中推断物流状态

    实际项目中应调用物流 API 查询，这里用 LLM 从文本中推断

    Returns:
        "delivered" | "in_transit" | "abnormal" | "unknown"
    """
    if not llm:
        llm = init_llm(temperature=0.0)

    # 先进行关键词匹配快速判断
    delivered_keywords = ["received", "arrived", "came", "delivered", "收到了", "拿到了", "收到货"]
    in_transit_keywords = ["waiting", "wait", "still", "not yet", "还没到", "还在等", "在途", "还没收到"]
    abnormal_keywords = ["lost", "damaged", "broken", "crushed", "customs", "stuck",
                         "丢", "损坏", "海关", "退回", "破损", "碎了"]

    text_lower = review_text.lower()

    abnormal_count = sum(1 for kw in abnormal_keywords if kw in text_lower)
    in_transit_count = sum(1 for kw in in_transit_keywords if kw in text_lower)
    delivered_count = sum(1 for kw in delivered_keywords if kw in text_lower)

    if abnormal_count > 0:
        return "abnormal"
    elif in_transit_count > delivered_count:
        return "in_transit"
    elif delivered_count > 0:
        return "delivered"
    else:
        return "unknown"


# ============================================================
# 4. 回复文案生成
# ============================================================
def generate_reply(
    analysis_result: Dict,
    review_text: str,
    target_language: str = "en",
    llm=None,
) -> Dict:
    """
    生成多语言客服回复文案

    Args:
        analysis_result: 8维分析结果
        review_text: 原始评论文本
        target_language: 目标语言（en, zh, ja, es, ar, de, fr 等）
        llm: LLM 实例

    Returns:
        {
            "subject": "...",
            "body": "...",
            "tone": "...",
            "compensation_suggestion": "...",
            "follow_up_action": "..."
        }
    """
    if not llm:
        llm = init_llm(temperature=0.5)

    # 推断物流状态
    logistics_status = get_logistics_status(review_text, llm)

    # RAG 检索历史相似案例
    vs = get_vector_store()
    try:
        rag_results = vs.similarity_search(review_text, k=3)
        rag_context = format_rag_context(rag_results)
    except Exception as e:
        print(f"[WARN] RAG检索失败: {e}")
        rag_context = "无法检索历史案例（向量库未初始化）"

    # 生成回复
    prompt = build_reply_prompt()
    chain = prompt | llm

    result = chain.invoke({
        "analysis_result": json.dumps(analysis_result, ensure_ascii=False, indent=2),
        "rag_context": rag_context,
        "logistics_status": logistics_status,
        "target_language": target_language,
    })

    # 尝试解析 JSON
    content = result.content.strip()

    # 清理可能的 markdown 代码块标记
    if content.startswith("```"):
        content = re.sub(r'^```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```$', '', content)

    try:
        reply = json.loads(content)
    except json.JSONDecodeError:
        # 如果解析失败，返回原始文本
        reply = {
            "subject": "Customer Service Reply",
            "body": content,
            "tone": "apologetic",
            "compensation_suggestion": "视情况提供补偿",
            "follow_up_action": "人工审核后发送",
        }

    # 附加上下文信息
    reply["logistics_status"] = logistics_status
    reply["logistics_status_desc"] = LOGISTICS_STATUSES.get(logistics_status, "")

    return reply


# ============================================================
# 5. 主分析链路
# ============================================================
def analyze_review(
    review_data: Dict,
    llm=None,
    use_rag: bool = True,
    use_cache: bool = True,
) -> Dict:
    """
    完整的差评分析链路：
    翻译（如需要） → 8维分析 → RAG检索 → 生成回复建议

    Args:
        review_data: 包含 asin, reviewText, overall, summary, style, category, country 等字段
        llm: LLM 实例
        use_rag: 是否使用 RAG 检索
        use_cache: 是否使用分析缓存（默认开启）

    Returns:
        完整分析结果
    """
    original_text = review_data.get("reviewText", "")

    # Step 0: 输入清洗与边界情况检测
    cleaned_data, warnings = sanitize_analysis_input(review_data)
    original_text = cleaned_data["reviewText"]

    # Step 0.5: 检查缓存
    cache_key = _cache_key(original_text)
    if use_cache:
        cached = _get_cached(cache_key)
        if cached:
            cached["_from_cache"] = True
            return cached

    if not llm:
        llm = init_llm(temperature=0.3, streaming=True)

    # Step 1: 翻译（如需要）
    translated_text = translate_to_english(original_text, llm)

    # Step 2: 8维分析
    from app.prompts import build_analysis_prompt
    analysis_prompt = build_analysis_prompt()

    # 构建分析输入
    style = review_data.get("style", {})
    style_str = json.dumps(style, ensure_ascii=False) if style else "无"

    analysis_input = {
        "asin": review_data.get("asin", "unknown"),
        "category": review_data.get("category", "unknown"),
        "style": style_str,
        "country": review_data.get("country", "unknown"),
        "overall": str(review_data.get("overall", "")),
        "summary": review_data.get("summary", ""),
        "review_text": translated_text if translated_text != original_text else original_text,
    }

    chain = analysis_prompt | llm
    result = chain.invoke(analysis_input)

    # 解析 JSON
    content = result.content.strip()
    if content.startswith("```"):
        content = re.sub(r'^```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```$', '', content)

    try:
        analysis = json.loads(content)
    except json.JSONDecodeError:
        analysis = {
            "scores": {},
            "root_cause": "解析失败",
            "urgency": "中",
            "tags": [],
            "summary_cn": content,
            "raw_output": content,
        }

    result = {
        "analysis": analysis,
        "original_text": original_text,
        "translated_text": translated_text if translated_text != original_text else None,
    }

    # Step 3: RAG 检索（可选）
    if use_rag:
        try:
            vs = get_vector_store()
            rag_results = vs.similarity_search(original_text, k=3)
            result["similar_cases"] = [
                {
                    "content": doc.page_content[:200],
                    "score": round(score, 4),
                    "asin": doc.metadata.get("asin", ""),
                    "overall": doc.metadata.get("overall", 0),
                }
                for doc, score in rag_results
            ]
        except Exception as e:
            result["similar_cases"] = []
            result["rag_error"] = str(e)

    # 写入缓存
    if use_cache:
        _set_cache(cache_key, result)

    # 附上输入清洗警告
    if warnings:
        result["input_warnings"] = warnings

    return result