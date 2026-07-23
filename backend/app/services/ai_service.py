"""
AI 大模型调用服务 — LangChain 驱动

调用链：
    router → analyze_review_issues()   → LCEL chain → extract_json() → dict
    router → generate_suggestions()    → LCEL chain → extract_json() → dict
    router → generate_reply()          → LCEL chain → extract_json() → dict

全程使用 LangChain (ChatOpenAI + PromptTemplate + StrOutputParser)，
不存在任何 client.chat.completions.create() 直接调用。
"""

import json
import re
import logging

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from app.config import settings

logger = logging.getLogger(__name__)

# =========================================================================
# 统一模型实例
# =========================================================================

def get_llm() -> ChatOpenAI:
    """
    获取 LangChain ChatOpenAI 实例。

    所有 AI 调用必须经过此函数获取的 llm 对象，
    保证模型配置（API Key / Base URL / 参数）全局统一。
    """
    if not settings.MODEL_API_KEY:
        raise ValueError(
            "MODEL_API_KEY 未配置。请在 .env 文件中设置 MODEL_API_KEY。"
        )

    return ChatOpenAI(
        model=settings.MODEL_NAME,
        api_key=settings.MODEL_API_KEY,
        base_url=settings.MODEL_BASE_URL,
        temperature=settings.AI_TEMPERATURE,
        max_tokens=settings.AI_MAX_TOKENS,
    )


# =========================================================================
# JSON 提取（与 LangChain 解耦，纯文本后处理）
# =========================================================================

def extract_json(text: str) -> dict:
    """
    从 LangChain 返回的文本中提取 JSON。

    尝试顺序：
    1. 直接 json.loads
    2. 去除 ```json ... ``` 标记后解析
    3. 正则提取 { ... } 后解析

    返回: dict
    异常: ValueError — 文本无法解析为 JSON
    """
    # 尝试1：直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试2：去除 Markdown 代码块标记
    cleaned = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 尝试3：正则提取首个 JSON 对象
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"AI 返回内容无法解析为 JSON:\n{text[:500]}"
    )


# =========================================================================
# LCEL 链式调用（实际接口使用）
# =========================================================================

def analyze_review_issues(review_text: str) -> dict:
    """
    差评问题分析 — LCEL 链。

    内部: PromptTemplate | ChatOpenAI | StrOutputParser → extract_json

    参数:
        review_text: 用户差评原文

    返回:
        {"issues": [...], "sentiment": "...", "severity": "..."}
    """
    from app.services.prompt_service import review_analysis_prompt

    llm = get_llm()
    parser = StrOutputParser()

    # LCEL 链
    chain = review_analysis_prompt | llm | parser

    raw_output = chain.invoke({"review_text": review_text})
    logger.debug("LCEL review_analysis 原始输出: %s", raw_output[:300])

    return extract_json(raw_output)


def generate_suggestions(review_text: str, issues: list[str]) -> dict:
    """
    运营优化建议生成 — LCEL 链。

    内部: PromptTemplate | ChatOpenAI | StrOutputParser → extract_json

    参数:
        review_text: 用户差评原文
        issues:      已识别的问题列表

    返回:
        {"suggestions": [...], "priority": [...], "estimated_impact": "..."}
    """
    from app.services.prompt_service import operation_suggestion_prompt

    llm = get_llm()
    parser = StrOutputParser()

    issues_str = "\n".join(f"- {issue}" for issue in issues)

    # LCEL 链
    chain = operation_suggestion_prompt | llm | parser

    raw_output = chain.invoke({
        "review_text": review_text,
        "issues": issues_str,
    })
    logger.debug("LCEL suggestion 原始输出: %s", raw_output[:300])

    return extract_json(raw_output)


def generate_reply(review_text: str, language: str = "中文") -> dict:
    """
    客服回复生成 — LCEL 链。

    内部: PromptTemplate | ChatOpenAI | StrOutputParser → extract_json

    参数:
        review_text: 差评原文
        language:    回复语言，默认中文

    返回:
        {"reply": "客服回复文本"}
    """
    from app.services.prompt_service import customer_reply_prompt

    llm = get_llm()
    parser = StrOutputParser()

    # LCEL 链
    chain = customer_reply_prompt | llm | parser

    raw_output = chain.invoke({
        "review_text": review_text,
        "language": language,
    })
    logger.debug("LCEL customer_reply 原始输出: %s", raw_output[:300])

    return extract_json(raw_output)


# =========================================================================
# LLMChain 兼容函数（课程教学保留）
# =========================================================================

def analyze_with_llmchain(review_text: str) -> dict:
    """
    传统 LLMChain 风格的差评分析（教学保留）。

    LangChain 1.x 已移除 LLMChain 类，此函数手动复现其语义：
        LLMChain(llm=llm, prompt=prompt).run(review_text=...)

    等价于：
        1) prompt.format(...)   → 渲染提示词
        2) llm.invoke(...)      → 调用大模型
        3) extract_json(...)    → 解析 JSON

    实际生产接口 /analysis/review 使用 LCEL 链 (prompt | llm | parser)。

    参数:
        review_text: 用户差评原文

    返回:
        {"issues": [...], "sentiment": "...", "severity": "..."}
    """
    from app.services.prompt_service import review_analysis_prompt

    llm = get_llm()

    # 第1步：PromptTemplate 渲染（LLMChain 内部行为）
    formatted_prompt = review_analysis_prompt.format(review_text=review_text)

    # 第2步：直接调用 llm.invoke()（LLMChain 封装的底层行为）
    ai_message = llm.invoke(formatted_prompt)

    # 第3步：提取文本内容
    raw_output = ai_message.content if hasattr(ai_message, "content") else str(ai_message)

    logger.debug("LLMChain 风格原始输出: %s", raw_output[:300])

    return extract_json(raw_output)
